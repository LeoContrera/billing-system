"""
Modelos para la gestión de productos del sistema POS.

Este módulo define el modelo Product que almacena información
de los productos disponibles para venta.
"""

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    """
    Producto disponible para venta en el sistema POS.

    Attributes:
        sku: Código único del producto (Stock Keeping Unit)
        name: Nombre descriptivo del producto
        description: Descripción detallada (opcional)
        price: Precio de venta unitario
        cost: Costo de adquisición (opcional, para reportes)
        is_active: Indica si el producto está disponible para venta
        created_at: Fecha de creación del registro
        updated_at: Fecha de última modificación

    Meta:
        ordering: Ordenado por nombre
        indexes: Índices para optimizar búsquedas por SKU y nombre

    Patrones ORM:
        - SKU como unique constraint (identificador principal)
        - is_active para soft-delete (no eliminar productos con historial)
    """

    sku = models.CharField(
        "SKU",
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Código único del producto",
    )
    name = models.CharField("Nombre", max_length=200)
    description = models.TextField("Descripción", blank=True)
    price = models.DecimalField(
        "Precio de Venta",
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Precio máximo: 9.999.999.999.999,99",
    )
    cost = models.DecimalField(
        "Costo",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Costo de adquisición (opcional)",
    )
    is_active = models.BooleanField(
        "Activo",
        default=True,
        help_text="Solo productos activos pueden venderse",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sku"]),
            models.Index(fields=["name"]),
            models.Index(fields=["is_active"]),
        ]
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"{self.sku} - {self.name}"

    @property
    def margin(self):
        """Calcula el margen de ganancia si hay costo registrado."""
        if self.cost and self.cost > 0:
            return self.price - self.cost
        return None

    @property
    def margin_percentage(self):
        """Calcula el porcentaje de margen si hay costo registrado."""
        if self.cost and self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return None
