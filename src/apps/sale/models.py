"""
Modelos para la gestión de ventas del sistema POS.

Este módulo define los modelos Sale (venta) y SaleLineItem (línea de producto).
"""

from django.db import models
from django.conf import settings
from decimal import Decimal


class Sale(models.Model):
    """
    Venta en el sistema POS.

    Attributes:
        customer: Cliente asociado a la venta (opcional)
        created_by: Usuario que creó la venta (cajero)
        status: Estado de la venta (PENDING o COMPLETED)
        global_discount_amount: Descuento aplicado al total de la venta
        created_at: Fecha de creación
        completed_at: Fecha de finalización

    Properties:
        subtotal: Suma de subtotales de todos los line items
        total: Subtotal menos descuento global
        total_paid: Suma de todos los pagos registrados
        remaining_balance: Saldo pendiente (puede ser negativo si hay sobrepago)
        is_fully_paid: Verifica si la venta está completamente pagada

    Meta:
        ordering: Ordenado por fecha descendente

    Patrones:
        - Properties calculadas (no se guardan en BD)
        - select_related y prefetch_related necesarios en servicios
    """
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'

    STATUS_CHOICES = [
        (PENDING, 'Pendiente'),
        (COMPLETED, 'Completada'),
    ]

    customer = models.ForeignKey(
        'customers.Customer',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name="Cliente"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Cajero"
    )
    status = models.CharField(
        "Estado",
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )
    global_discount_amount = models.DecimalField(
        "Descuento Global",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Venta #{self.pk} - {self.get_status_display()}"

    @property
    def subtotal(self):
        """Suma de subtotales de todos los line items."""
        return sum(item.subtotal for item in self.line_items.all())

    @property
    def total(self):
        """Subtotal menos descuento global."""
        return self.subtotal - self.global_discount_amount

    @property
    def total_paid(self):
        """Suma de todos los pagos registrados."""
        return sum(t.amount for t in self.transactions.all())

    @property
    def remaining_balance(self):
        """Saldo pendiente (puede ser negativo si hay sobrepago)."""
        return self.total - self.total_paid

    @property
    def is_fully_paid(self):
        """Verifica si la venta está completamente pagada."""
        return self.remaining_balance <= 0


class SaleLineItem(models.Model):
    """
    Línea de producto en una venta.

    Attributes:
        sale: Venta a la que pertenece este item
        product: Referencia al producto (opcional, para trazabilidad)
        product_name: Nombre del producto (desnormalizado para historial)
        sku: Código SKU del producto
        quantity: Cantidad vendida
        unit_price: Precio unitario
        discount_amount: Descuento aplicado a esta línea

    Properties:
        subtotal: Fórmula: (cantidad × precio) - descuento

    Meta:
        ordering: Ordenado por ID

    Patrones:
        - CASCADE: Si se borra venta, se borran items (relación compositiva)
        - Desnormalización: product_name se guarda para mantener historial
        - SET_NULL para product: mantiene historial aunque producto se elimine
    """
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,  # Si se borra venta, se borran items
        related_name='line_items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_line_items',
        verbose_name="Producto",
        help_text="Referencia al producto (se mantiene desnormalización)"
    )
    product_name = models.CharField(
        "Producto",
        max_length=200,
        help_text="Nombre desnormalizado para historial"
    )
    sku = models.CharField("SKU", max_length=50, blank=True)
    quantity = models.DecimalField("Cantidad", max_digits=10, decimal_places=3)
    unit_price = models.DecimalField("Precio Unitario", max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(
        "Descuento",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    @property
    def subtotal(self):
        """Fórmula: (cantidad × precio) - descuento."""
        return (self.quantity * self.unit_price) - self.discount_amount
