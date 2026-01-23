"""
Modelos para la gestión de inventario del sistema POS.

Este módulo define los modelos Stock (niveles de inventario) y
Movement (registro de movimientos de stock).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Stock(models.Model):
    """
    Nivel de inventario de un producto.

    Attributes:
        product: Producto al que pertenece este registro de stock
        current_qty: Cantidad actual en inventario
        min_qty: Cantidad mínima (punto de reorden)
        max_qty: Cantidad máxima (capacidad de almacenamiento)
        location: Ubicación física del stock

    Properties:
        is_below_minimum: Indica si el stock está bajo el mínimo
        needs_reorder: Alias de is_below_minimum

    Meta:
        unique_together: Un producto tiene un único registro de stock por ubicación

    Patrones ORM:
        - FK con PROTECT para evitar borrado accidental de productos con stock
        - unique_together para multi-ubicación futura
    """

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name="stocks",
        verbose_name="Producto",
    )
    current_qty = models.DecimalField(
        "Cantidad Actual",
        max_digits=10,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
    )
    min_qty = models.DecimalField(
        "Cantidad Mínima",
        max_digits=10,
        decimal_places=3,
        default=Decimal("0.000"),
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Punto de reorden",
    )
    max_qty = models.DecimalField(
        "Cantidad Máxima",
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.000"))],
        help_text="Capacidad máxima de almacenamiento",
    )
    location = models.CharField(
        "Ubicación",
        max_length=100,
        default="PRINCIPAL",
        help_text="Ubicación física del stock (ej: PRINCIPAL, DEPOSITO)",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["product", "location"]
        ordering = ["product__name"]
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        indexes = [
            models.Index(fields=["product", "location"]),
        ]

    def __str__(self):
        return f"{self.product.sku} @ {self.location}: {self.current_qty}"

    @property
    def is_below_minimum(self):
        """Indica si el stock está bajo el mínimo."""
        return self.current_qty < self.min_qty

    @property
    def needs_reorder(self):
        """Alias de is_below_minimum para legibilidad."""
        return self.is_below_minimum


class Movement(models.Model):
    """
    Registro de movimiento de inventario.

    Attributes:
        stock: Registro de stock afectado
        movement_type: Tipo de movimiento (entrada/salida/ajuste)
        delta_qty: Cambio en cantidad (positivo o negativo)
        previous_qty: Cantidad antes del movimiento (auditoría)
        reference: Referencia externa (ID de venta, orden de compra, etc.)
        notes: Notas adicionales
        created_at: Fecha y hora del movimiento
        created_by: Usuario que registró el movimiento

    Types:
        SALE: Salida por venta (delta negativo)
        PURCHASE: Entrada por compra (delta positivo)
        ADJUSTMENT_IN: Ajuste de entrada (delta positivo)
        ADJUSTMENT_OUT: Ajuste de salida (delta negativo)
        TRANSFER_IN: Transferencia entrante (delta positivo)
        TRANSFER_OUT: Transferencia saliente (delta negativo)
        RETURN: Devolución de cliente (delta positivo)

    Patrones ORM:
        - Patrón Event Sourcing ligero: cada cambio de stock se registra
        - reference permite trazabilidad con otros módulos (ventas, compras)
        - previous_qty para auditoría y reconstrucción de historial
    """

    SALE = "SALE"
    PURCHASE = "PURCHASE"
    ADJUSTMENT_IN = "ADJ_IN"
    ADJUSTMENT_OUT = "ADJ_OUT"
    TRANSFER_IN = "TRANS_IN"
    TRANSFER_OUT = "TRANS_OUT"
    RETURN = "RETURN"

    MOVEMENT_CHOICES = [
        (SALE, "Venta"),
        (PURCHASE, "Compra"),
        (ADJUSTMENT_IN, "Ajuste Entrada"),
        (ADJUSTMENT_OUT, "Ajuste Salida"),
        (TRANSFER_IN, "Transferencia Entrada"),
        (TRANSFER_OUT, "Transferencia Salida"),
        (RETURN, "Devolución"),
    ]

    stock = models.ForeignKey(
        Stock,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="Stock",
    )
    movement_type = models.CharField(
        "Tipo",
        max_length=20,
        choices=MOVEMENT_CHOICES,
    )
    delta_qty = models.DecimalField(
        "Cambio de Cantidad",
        max_digits=10,
        decimal_places=3,
        help_text="Positivo para entradas, negativo para salidas",
    )
    previous_qty = models.DecimalField(
        "Cantidad Anterior",
        max_digits=10,
        decimal_places=3,
        help_text="Stock antes del movimiento (para auditoría)",
    )
    reference = models.CharField(
        "Referencia",
        max_length=100,
        blank=True,
        help_text="ID de venta, orden de compra, etc.",
    )
    notes = models.TextField("Notas", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Registrado por",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Movimiento"
        verbose_name_plural = "Movimientos"
        indexes = [
            models.Index(fields=["stock", "-created_at"]),
            models.Index(fields=["movement_type"]),
            models.Index(fields=["reference"]),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.delta_qty} ({self.stock.product.sku})"

    @property
    def resulting_qty(self):
        """Cantidad resultante después del movimiento."""
        return self.previous_qty + self.delta_qty
