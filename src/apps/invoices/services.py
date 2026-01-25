"""
Service layer para facturación electrónica.

Implementa la lógica de negocio para crear facturas y emitir CAE (AFIP).
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import logging
from datetime import datetime, timedelta

from customers.models import TaxCategory
from sale.models import Sale
from .models import Invoice, InvoiceStatus, ReceiptType, VATAliquot


logger = logging.getLogger('invoices')


class InvoiceService:
    """
    Servicio para gestión de facturas electrónicas.

    Métodos principales:
    - determine_receipt_type: Determina tipo de comprobante según categorías fiscales
    - calculate_taxes: Calcula IVA según tipo de comprobante
    - create_invoice_from_sale: Crea factura desde venta completada
    - emit_cae: Emite CAE (simulado o real según AFIP_DEBUG_MODE)
    """

    VAT_RATE_21 = Decimal('21.00')
    VAT_RATE_10_5 = Decimal('10.50')

    # Configurar según categoría fiscal de la empresa
    ISSUER_TAX_CATEGORY = TaxCategory.RESPONSABLE_INSCRIPTO

    @staticmethod
    def determine_receipt_type(issuer_tax_category: str, customer_tax_category: str) -> str:
        """
        Determina el tipo de comprobante según matriz ARCA.

        Matriz de decisión:
        - RI → RI: Factura A
        - RI → MT/CF/EX: Factura B
        - MT/CF/EX → cualquiera: Factura C

        Args:
            issuer_tax_category: Categoría fiscal del emisor (empresa)
            customer_tax_category: Categoría fiscal del cliente

        Returns:
            str: 'A', 'B', o 'C'
        """
        if issuer_tax_category == TaxCategory.RESPONSABLE_INSCRIPTO:
            if customer_tax_category == TaxCategory.RESPONSABLE_INSCRIPTO:
                return ReceiptType.FACTURA_A
            else:
                return ReceiptType.FACTURA_B
        else:
            return ReceiptType.FACTURA_C

    @staticmethod
    def calculate_taxes(total_amount: Decimal, receipt_type: str) -> tuple:
        """
        Calcula montos de IVA según tipo de comprobante.

        Factura A: IVA discriminado
            - net_taxed = total / 1.21
            - vat_amount = net_taxed * 0.21
            - net_untaxed = 0

        Factura B/C: IVA incluido
            - net_taxed = 0
            - vat_amount = 0
            - net_untaxed = total

        Args:
            total_amount: Monto total de la venta
            receipt_type: 'A', 'B', o 'C'

        Returns:
            tuple: (net_taxed, vat_amount, net_untaxed)
        """
        if receipt_type == ReceiptType.FACTURA_A:
            # IVA discriminado
            divisor = Decimal('1.21')
            net_taxed = (total_amount / divisor).quantize(Decimal('0.01'))
            vat_amount = (net_taxed * Decimal('0.21')).quantize(Decimal('0.01'))
            net_untaxed = Decimal('0.00')
        else:
            # IVA incluido (Factura B o C)
            net_taxed = Decimal('0.00')
            vat_amount = Decimal('0.00')
            net_untaxed = total_amount

        return net_taxed, vat_amount, net_untaxed

    @staticmethod
    @transaction.atomic
    def create_invoice_from_sale(sale_id: int, user) -> Invoice:
        """
        Crea una factura desde una venta completada.

        Validaciones:
        - Sale debe estar en estado COMPLETED
        - Sale no debe tener factura previa

        Proceso:
        1. Obtener datos del cliente (o usar "Consumidor Final")
        2. Determinar tipo de comprobante
        3. Calcular impuestos
        4. Crear Invoice en estado DRAFT
        5. Si Factura A: crear VATAliquot

        Args:
            sale_id: ID de la venta
            user: Usuario que crea la factura

        Returns:
            Invoice: Factura creada

        Raises:
            ValidationError: Si validaciones fallan
        """
        # Obtener venta con lock
        sale = Sale.objects.select_for_update().select_related('customer').get(pk=sale_id)

        # Validaciones
        if sale.status != Sale.COMPLETED:
            raise ValidationError("Solo se pueden facturar ventas completadas")

        if hasattr(sale, 'invoice'):
            raise ValidationError("Esta venta ya tiene una factura asociada")

        # Obtener datos del cliente
        if sale.customer:
            customer_name = sale.customer.full_name
            customer_tax_id = sale.customer.tax_id or ''
            customer_tax_category = sale.customer.tax_category
        else:
            customer_name = "Consumidor Final"
            customer_tax_id = ""
            customer_tax_category = TaxCategory.CONSUMIDOR_FINAL

        # Determinar tipo de comprobante
        receipt_type = InvoiceService.determine_receipt_type(
            InvoiceService.ISSUER_TAX_CATEGORY,
            customer_tax_category
        )

        # Calcular impuestos
        net_taxed, vat_amount, net_untaxed = InvoiceService.calculate_taxes(
            sale.total,
            receipt_type
        )

        # Crear factura
        invoice = Invoice.objects.create(
            sale=sale,
            receipt_type=receipt_type,
            status=InvoiceStatus.DRAFT,
            customer_name=customer_name,
            customer_tax_id=customer_tax_id,
            customer_tax_category=customer_tax_category,
            net_taxed=net_taxed,
            vat_amount=vat_amount,
            net_untaxed=net_untaxed,
            total_amount=sale.total,
            created_by=user
        )

        # Si es Factura A, crear alícuota de IVA 21%
        if receipt_type == ReceiptType.FACTURA_A:
            VATAliquot.objects.create(
                invoice=invoice,
                vat_rate=InvoiceService.VAT_RATE_21,
                base_amount=net_taxed,
                vat_amount=vat_amount
            )

        logger.info(
            f"Factura {invoice.id} creada - Tipo: {receipt_type} - "
            f"Total: {sale.total} - Cliente: {customer_name}"
        )

        return invoice

    @staticmethod
    @transaction.atomic
    def emit_cae(invoice_id: int) -> Invoice:
        """
        Emite CAE para una factura.

        Modo DEBUG (AFIP_DEBUG_MODE=True):
        - Genera CAE simulado: "SIM" + timestamp
        - No contacta AFIP
        - Actualiza status a AUTHORIZED

        Modo PRODUCTION (AFIP_DEBUG_MODE=False):
        - Crea Receipt en django_afip
        - Llama a receipt.validate()
        - Copia CAE desde ReceiptValidation
        - Maneja errores de AFIP

        Args:
            invoice_id: ID de la factura

        Returns:
            Invoice: Factura con CAE emitido

        Raises:
            ValidationError: Si factura no está en estado válido
        """
        invoice = Invoice.objects.select_for_update().get(pk=invoice_id)

        # Validaciones
        if invoice.status == InvoiceStatus.AUTHORIZED:
            raise ValidationError("Esta factura ya tiene CAE autorizado")

        if invoice.status == InvoiceStatus.REJECTED:
            # Permitir reintentos
            logger.info(f"Reintentando emisión de CAE para factura {invoice.id}")

        # Actualizar estado a PENDING
        invoice.status = InvoiceStatus.PENDING
        invoice.save()

        try:
            if settings.AFIP_DEBUG_MODE:
                # Modo DEBUG: CAE simulado
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                invoice.cae = f"SIM{timestamp}"
                invoice.cae_expiration = (timezone.now().date() + timedelta(days=10))
                invoice.status = InvoiceStatus.AUTHORIZED
                invoice.authorized_at = timezone.now()
                invoice.notes = "CAE simulado - Modo DEBUG"
                invoice.save()

                logger.info(f"CAE simulado emitido para factura {invoice.id}: {invoice.cae}")

            else:
                # Modo PRODUCTION: Integración real con AFIP
                invoice = InvoiceService._emit_cae_production(invoice)

        except Exception as e:
            # Error al emitir CAE
            invoice.status = InvoiceStatus.REJECTED
            invoice.notes = f"Error al emitir CAE: {str(e)}"
            invoice.save()
            logger.error(f"Error emitiendo CAE para factura {invoice.id}: {str(e)}")
            raise ValidationError(f"Error al emitir CAE: {str(e)}")

        return invoice

    @staticmethod
    def _emit_cae_production(invoice: Invoice) -> Invoice:
        """
        Emite CAE real contactando AFIP WSFE.

        Requiere:
        - TaxPayer configurado con certificados SSL
        - PointOfSales activo

        Args:
            invoice: Factura a autorizar

        Returns:
            Invoice: Factura actualizada con CAE

        Raises:
            ValidationError: Si configuración es inválida o AFIP rechaza
        """
        from django_afip.models import TaxPayer, PointOfSales, Receipt, ReceiptType as AfipReceiptType

        # Obtener TaxPayer
        try:
            taxpayer = TaxPayer.objects.filter(is_sandboxed=False).first()
            if not taxpayer:
                raise ValidationError(
                    "No hay TaxPayer configurado. "
                    "Configure certificados SSL en Django Admin."
                )
        except Exception as e:
            raise ValidationError(f"Error obteniendo TaxPayer: {str(e)}")

        # Obtener Punto de Venta
        try:
            pos = PointOfSales.objects.filter(
                owner=taxpayer,
                issuance_type='CAE'
            ).first()
            if not pos:
                raise ValidationError(
                    "No hay Punto de Venta configurado. "
                    "Ejecute: python manage.py afip_fetch_points_of_sales"
                )
        except Exception as e:
            raise ValidationError(f"Error obteniendo Punto de Venta: {str(e)}")

        # Mapear tipo de comprobante
        receipt_type_map = {
            ReceiptType.FACTURA_A: '1',  # Factura A
            ReceiptType.FACTURA_B: '6',  # Factura B
            ReceiptType.FACTURA_C: '11', # Factura C
        }

        # Crear Receipt
        afip_receipt_type = AfipReceiptType.objects.get(
            code=receipt_type_map[invoice.receipt_type]
        )

        receipt = Receipt.objects.create(
            point_of_sales=pos,
            receipt_type=afip_receipt_type,
            issued_date=timezone.now().date(),
            total_amount=invoice.total_amount,
            net_untaxed=invoice.net_untaxed,
            net_taxed=invoice.net_taxed,
            vat_amount=invoice.vat_amount
        )

        # Validar con AFIP
        validation = receipt.validate()

        if validation and validation.result == 'A':
            # CAE aprobado
            invoice.afip_receipt = receipt
            invoice.cae = validation.cae
            invoice.cae_expiration = validation.cae_expiration
            invoice.status = InvoiceStatus.AUTHORIZED
            invoice.authorized_at = timezone.now()
            invoice.notes = "CAE autorizado por AFIP"
            invoice.save()

            logger.info(
                f"CAE autorizado para factura {invoice.id}: {invoice.cae} - "
                f"Vencimiento: {invoice.cae_expiration}"
            )
        else:
            # CAE rechazado
            error_msg = validation.observations if validation else "Sin respuesta de AFIP"
            invoice.status = InvoiceStatus.REJECTED
            invoice.notes = f"Rechazado por AFIP: {error_msg}"
            invoice.save()
            raise ValidationError(f"AFIP rechazó el comprobante: {error_msg}")

        return invoice
