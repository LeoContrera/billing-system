"""
Modelos para el procesamiento de pagos del sistema POS.

Este módulo define los modelos PaymentMethod (métodos de pago disponibles)
y Transaction (registro de pagos realizados).
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from decimal import Decimal


class PaymentMethod(models.Model):
    """
    Métodos de pago disponibles (Efectivo, Tarjeta, etc.).

    Attributes:
        name: Nombre descriptivo del método de pago
        method_type: Tipo de método (CASH, DEBIT, CREDIT, TRANSFER)
        is_active: Indica si el método está activo para usar

    Meta:
        ordering: Ordenado por nombre
    """
    CASH = 'CASH'
    DEBIT_CARD = 'DEBIT'
    CREDIT_CARD = 'CREDIT'
    TRANSFER = 'TRANSFER'

    METHOD_CHOICES = [
        (CASH, 'Efectivo'),
        (DEBIT_CARD, 'Tarjeta de Débito'),
        (CREDIT_CARD, 'Tarjeta de Crédito'),
        (TRANSFER, 'Transferencia'),
    ]

    name = models.CharField("Nombre", max_length=50)
    method_type = models.CharField("Tipo", max_length=20, choices=METHOD_CHOICES)
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """
    Registro de pago asociado a una venta.

    Attributes:
        sale: Venta a la que pertenece este pago
        payment_method: Método de pago utilizado
        amount: Monto base del pago (debe ser positivo)
        card_type: Tipo de tarjeta (VISA, Mastercard, etc.) si aplica
        installments: Número de cuotas para tarjetas de crédito
        interest_rate: Tasa de interés mensual (%) para financiación
        total_amount: Monto total incluyendo intereses
        created_at: Fecha y hora del registro
        created_by: Usuario que registró el pago

    Meta:
        ordering: Ordenado por fecha descendente

    Patrones ORM:
        - on_delete=PROTECT previene borrado accidental de datos críticos
        - MinValueValidator valida monto positivo a nivel de BD
        - Campos opcionales (null=True, blank=True) para tarjetas
    """
    CARD_TYPE_CHOICES = [
        ('VISA', 'VISA'),
        ('MASTERCARD', 'Mastercard'),
        ('AMEX', 'American Express'),
        ('CABAL', 'Cabal'),
        ('NARANJA', 'Naranja'),
        ('MAESTRO', 'Maestro'),
        ('OTHER', 'Otra'),
    ]

    sale = models.ForeignKey(
        'sale.Sale',
        on_delete=models.PROTECT,
        related_name='transactions',
        verbose_name="Venta"
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        verbose_name="Método de Pago"
    )
    amount = models.DecimalField(
        "Monto Base",
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monto del pago sin incluir intereses"
    )
    card_type = models.CharField(
        "Tipo de Tarjeta",
        max_length=20,
        choices=CARD_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Requerido para pagos con tarjeta"
    )
    installments = models.PositiveIntegerField(
        "Número de Cuotas",
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Número de cuotas para tarjetas de crédito"
    )
    interest_rate = models.DecimalField(
        "Tasa de Interés (%)",
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tasa de interés mensual aplicada"
    )
    total_amount = models.DecimalField(
        "Monto Total",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Monto total incluyendo intereses"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Registrado por"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.installments > 1:
            return f"{self.payment_method.name} - ${self.amount} ({self.installments}x)"
        return f"{self.payment_method.name} - ${self.amount}"
