from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class InvoiceStatus(models.TextChoices):
    """Estados del proceso de facturación."""
    DRAFT = 'DRAFT', 'Borrador'
    PENDING = 'PENDING', 'Pendiente de Autorización'
    AUTHORIZED = 'AUTHORIZED', 'Autorizada (CAE obtenido)'
    REJECTED = 'REJECTED', 'Rechazada por AFIP'


class ReceiptType(models.TextChoices):
    """Tipos de comprobante fiscal."""
    FACTURA_A = 'A', 'Factura A'
    FACTURA_B = 'B', 'Factura B'
    FACTURA_C = 'C', 'Factura C'


class Invoice(models.Model):
    """
    Factura electrónica local.

    Relaciones:
        - OneToOne con Sale (1:1)
        - OneToOne con django_afip.Receipt (SET_NULL para mantener historial)

    Campos clave:
        - receipt_type: A, B, C (determinado automáticamente)
        - status: DRAFT → PENDING → AUTHORIZED/REJECTED
        - CAE: Código de autorización (copiado desde afip_receipt.validation)
        - Montos: net_taxed, vat_amount, total_amount (calculados desde Sale)
        - Datos cliente: desnormalizados para historial
    """

    sale = models.OneToOneField(
        'sale.Sale',
        on_delete=models.PROTECT,
        related_name='invoice'
    )

    # Temporarily commented out - will add after django_afip is migrated
    # afip_receipt = models.OneToOneField(
    #     'django_afip.Receipt',
    #     on_delete=models.SET_NULL,
    #     null=True, blank=True,
    #     related_name='local_invoice'
    # )

    receipt_type = models.CharField(max_length=3, choices=ReceiptType.choices)
    status = models.CharField(max_length=20, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT)

    # Datos del receptor (desnormalizados)
    customer_name = models.CharField(max_length=200)
    customer_tax_id = models.CharField(max_length=20, blank=True)
    customer_tax_category = models.CharField(max_length=2)  # CF, RI, MT, EX

    # Montos
    net_untaxed = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    net_taxed = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])

    # CAE (copiado desde ReceiptValidation)
    cae = models.CharField(max_length=14, blank=True)
    cae_expiration = models.DateField(null=True, blank=True)

    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notes = models.TextField(blank=True, help_text="Errores AFIP u observaciones")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cae']),
            models.Index(fields=['sale']),
        ]

    def __str__(self):
        return f"Invoice {self.id} - {self.get_receipt_type_display()} - {self.get_status_display()}"

    @property
    def is_authorized(self):
        return self.status == InvoiceStatus.AUTHORIZED and bool(self.cae)

    @property
    def display_number(self):
        """Formato: 0001-00000123"""
        # Temporarily commented out - will activate after django_afip is migrated
        # if self.afip_receipt and self.afip_receipt.receipt_number:
        #     pos = str(self.afip_receipt.point_of_sales.number).zfill(4)
        #     num = str(self.afip_receipt.receipt_number).zfill(8)
        #     return f"{pos}-{num}"

        # Modo DEBUG: Generar número simulado
        if self.is_authorized:
            pos = "0001"  # Punto de venta simulado
            num = str(self.id).zfill(8)  # Usar ID de la factura
            return f"{pos}-{num}"
        return "Sin autorizar"


class VATAliquot(models.Model):
    """Alícuota de IVA para Facturas A."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='vat_aliquots')
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2)  # 21.00, 10.50, 27.00
    base_amount = models.DecimalField(max_digits=10, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"VAT {self.vat_rate}% - Base: {self.base_amount} - VAT: {self.vat_amount}"
