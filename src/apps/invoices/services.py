"""
Service layer para facturación electrónica.

Implementa la lógica de negocio para crear facturas y emitir CAE (AFIP).
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from django.core.mail import EmailMessage
from decimal import Decimal
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from io import BytesIO

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
    def calculate_vat_aliquots_from_line_items(sale) -> dict:
        """
        Agrupa line items por tasa de IVA y calcula base y monto por alícuota.

        Para Factura A: IVA discriminado
            - base_amount = (quantity * unit_price - discount_amount) / (1 + vat_rate/100)
            - vat_amount = base_amount * (vat_rate / 100)

        Args:
            sale: Instancia de Sale con line_items prefetched

        Returns:
            dict: {
                'vat_rate': {
                    'base_amount': Decimal,
                    'vat_amount': Decimal
                }
            }

        Ejemplo:
            {
                '21.00': {'base_amount': Decimal('826.45'), 'vat_amount': Decimal('173.55')},
                '10.50': {'base_amount': Decimal('90.50'), 'vat_amount': Decimal('9.50')}
            }
        """
        vat_groups = defaultdict(lambda: {'base_amount': Decimal('0.00'), 'vat_amount': Decimal('0.00')})

        for item in sale.line_items.all():
            vat_rate = Decimal(item.vat_rate)
            item_total = (item.quantity * item.unit_price) - item.discount_amount

            # Calcular base imponible (neto sin IVA)
            divisor = Decimal('1.00') + (vat_rate / Decimal('100.00'))
            base_amount = (item_total / divisor).quantize(Decimal('0.01'))
            vat_amount = (base_amount * vat_rate / Decimal('100.00')).quantize(Decimal('0.01'))

            vat_groups[str(vat_rate)]['base_amount'] += base_amount
            vat_groups[str(vat_rate)]['vat_amount'] += vat_amount

        return dict(vat_groups)

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

        # Calcular impuestos según tipo de comprobante
        if receipt_type == ReceiptType.FACTURA_A:
            # Factura A: IVA discriminado - agregar alícuotas reales desde line items
            vat_aliquots = InvoiceService.calculate_vat_aliquots_from_line_items(sale)

            # Sumar totales
            net_taxed = sum(v['base_amount'] for v in vat_aliquots.values())
            vat_amount = sum(v['vat_amount'] for v in vat_aliquots.values())
            net_untaxed = Decimal('0.00')
        else:
            # Factura B/C: IVA incluido
            net_taxed = Decimal('0.00')
            vat_amount = Decimal('0.00')
            net_untaxed = sale.total
            vat_aliquots = {}

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

        # Si es Factura A, crear alícuotas de IVA reales
        if receipt_type == ReceiptType.FACTURA_A:
            for vat_rate_str, amounts in vat_aliquots.items():
                VATAliquot.objects.create(
                    invoice=invoice,
                    vat_rate=Decimal(vat_rate_str),
                    base_amount=amounts['base_amount'],
                    vat_amount=amounts['vat_amount']
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

    @staticmethod
    def generate_pdf(invoice: Invoice) -> BytesIO:
        """
        Genera PDF de factura usando django-afip.

        Modo DEBUG: Genera PDF simulado con texto básico
        Modo PRODUCTION: Usa invoice.afip_receipt.as_pdf()

        Args:
            invoice: Factura autorizada con CAE

        Returns:
            BytesIO: Buffer con PDF generado

        Raises:
            ValidationError: Si factura no está autorizada
        """
        if not invoice.is_authorized:
            raise ValidationError("Solo se puede generar PDF de facturas autorizadas")

        if settings.AFIP_DEBUG_MODE:
            # Modo DEBUG: PDF simulado usando ReportLab
            try:
                from reportlab.lib.pagesizes import A4
                from reportlab.pdfgen import canvas
            except ImportError:
                raise ValidationError(
                    "ReportLab no instalado. Ejecute: uv add reportlab"
                )

            buffer = BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=A4)
            pdf.setTitle(f"Factura {invoice.receipt_type} - {invoice.id}")

            # Header
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(50, 800, f"FACTURA {invoice.receipt_type} - MODO DEBUG")

            # Datos básicos
            pdf.setFont("Helvetica", 12)
            y = 750
            pdf.drawString(50, y, f"CAE: {invoice.cae}")
            y -= 20
            pdf.drawString(50, y, f"Vencimiento CAE: {invoice.cae_expiration}")
            y -= 20
            pdf.drawString(50, y, f"Número: {invoice.display_number}")
            y -= 40

            pdf.drawString(50, y, f"Cliente: {invoice.customer_name}")
            y -= 20
            pdf.drawString(50, y, f"CUIT/DNI: {invoice.customer_tax_id or 'N/A'}")
            y -= 40

            pdf.drawString(50, y, f"Subtotal: ${invoice.net_taxed + invoice.net_untaxed}")
            y -= 20
            pdf.drawString(50, y, f"IVA: ${invoice.vat_amount}")
            y -= 20
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(50, y, f"TOTAL: ${invoice.total_amount}")

            pdf.showPage()
            pdf.save()
            buffer.seek(0)

            logger.info(f"PDF simulado generado para factura {invoice.id}")
            return buffer

        else:
            # Modo PRODUCTION: Usar django-afip
            if not invoice.afip_receipt:
                raise ValidationError("Factura no tiene Receipt de AFIP asociado")

            try:
                pdf_buffer = BytesIO()
                pdf_data = invoice.afip_receipt.as_pdf()
                pdf_buffer.write(pdf_data)
                pdf_buffer.seek(0)

                logger.info(f"PDF AFIP generado para factura {invoice.id}")
                return pdf_buffer

            except Exception as e:
                logger.error(f"Error generando PDF AFIP para factura {invoice.id}: {str(e)}")
                raise ValidationError(f"Error generando PDF: {str(e)}")

    @staticmethod
    def send_invoice_email(invoice: Invoice, pdf_buffer: BytesIO) -> bool:
        """
        Envía email con PDF de factura adjunto al cliente.

        Args:
            invoice: Factura autorizada
            pdf_buffer: Buffer con PDF generado

        Returns:
            bool: True si envío exitoso

        Raises:
            ValidationError: Si cliente no tiene email o envío falla
        """
        # Validar que cliente tenga email
        if not invoice.sale.customer or not invoice.sale.customer.email:
            raise ValidationError(
                "El cliente no tiene email registrado. "
                "No se puede enviar la factura electrónica."
            )

        customer_email = invoice.sale.customer.email

        # Construir mensaje
        subject = f"Su Factura Electrónica {invoice.get_receipt_type_display()} - {invoice.display_number}"

        body = f"""
Estimado/a {invoice.customer_name},

Adjuntamos su comprobante electrónico autorizado por AFIP.

Detalle del comprobante:
- Tipo: {invoice.get_receipt_type_display()}
- Número: {invoice.display_number}
- CAE: {invoice.cae}
- Vencimiento CAE: {invoice.cae_expiration}
- Total: ${invoice.total_amount}

Este comprobante tiene plena validez legal según normativa AFIP.

Muchas gracias por su compra.

---
Este es un email automático generado por el sistema de facturación.
"""

        try:
            # Crear email con adjunto
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[customer_email],
            )

            # Adjuntar PDF
            filename = f"Factura_{invoice.receipt_type}_{invoice.id}_{invoice.cae}.pdf"
            email.attach(filename, pdf_buffer.read(), 'application/pdf')

            # Enviar
            email.send(fail_silently=False)

            logger.info(
                f"Email enviado exitosamente para factura {invoice.id} "
                f"a {customer_email}"
            )

            return True

        except Exception as e:
            logger.error(
                f"Error enviando email para factura {invoice.id} "
                f"a {customer_email}: {str(e)}"
            )
            raise ValidationError(f"Error enviando email: {str(e)}")

    @staticmethod
    @transaction.atomic
    def procesar_venta_afip(sale_id: int, user) -> dict:
        """
        Método orquestador completo para procesar venta con AFIP.

        Flujo:
        1. Crear Invoice desde Sale
        2. Validar con AFIP (obtener CAE)
        3. Generar PDF
        4. Enviar email al cliente

        IMPORTANTE: Si falla el envío de email, se loguea el error pero
        NO se hace rollback del CAE (ya fue autorizado por AFIP).

        Args:
            sale_id: ID de la venta completada
            user: Usuario que procesa la facturación

        Returns:
            dict: {
                'success': bool,
                'invoice': Invoice,
                'cae': str,
                'display_number': str,
                'email_sent': bool,
                'error': str (opcional)
            }

        Raises:
            ValidationError: Si falla creación de invoice o emisión de CAE
        """
        result = {
            'success': False,
            'invoice': None,
            'cae': None,
            'display_number': None,
            'email_sent': False,
            'error': None
        }

        try:
            # Paso 1: Crear Invoice
            logger.info(f"Iniciando proceso AFIP para venta {sale_id}")
            invoice = InvoiceService.create_invoice_from_sale(sale_id, user)
            result['invoice'] = invoice

            # Paso 2: Emitir CAE (validar con AFIP)
            logger.info(f"Emitiendo CAE para factura {invoice.id}")
            invoice = InvoiceService.emit_cae(invoice.id)

            if not invoice.is_authorized:
                raise ValidationError(
                    f"No se pudo obtener CAE. Status: {invoice.get_status_display()}"
                )

            result['cae'] = invoice.cae
            result['display_number'] = invoice.display_number

            logger.info(
                f"CAE obtenido exitosamente para factura {invoice.id}: {invoice.cae}"
            )

            # Paso 3: Generar PDF
            logger.info(f"Generando PDF para factura {invoice.id}")
            pdf_buffer = InvoiceService.generate_pdf(invoice)

            # Paso 4: Enviar email (fuera de transacción principal)
            # Si falla, loguear error pero no hacer rollback del CAE
            try:
                logger.info(f"Enviando email para factura {invoice.id}")
                email_sent = InvoiceService.send_invoice_email(invoice, pdf_buffer)
                result['email_sent'] = email_sent

            except ValidationError as email_error:
                # Email falló, pero CAE ya fue autorizado
                error_msg = str(email_error)
                logger.warning(
                    f"CAE autorizado pero email NO enviado para factura {invoice.id}: "
                    f"{error_msg}"
                )
                result['error'] = f"Factura autorizada pero email no enviado: {error_msg}"
                result['email_sent'] = False

                # Registrar en notes de la factura
                invoice.notes += f"\n[ADVERTENCIA] Email no enviado: {error_msg}"
                invoice.save(update_fields=['notes'])

            result['success'] = True

            logger.info(
                f"Proceso AFIP completado para venta {sale_id} - "
                f"Factura {invoice.id} - CAE: {invoice.cae} - "
                f"Email enviado: {result['email_sent']}"
            )

            return result

        except ValidationError as e:
            # Error crítico en creación de invoice o emisión de CAE
            error_msg = str(e)
            logger.error(f"Error procesando venta {sale_id} con AFIP: {error_msg}")
            result['error'] = error_msg
            raise

        except Exception as e:
            # Error inesperado
            error_msg = f"Error inesperado: {str(e)}"
            logger.error(f"Error inesperado procesando venta {sale_id}: {error_msg}")
            result['error'] = error_msg
            raise ValidationError(error_msg)
