"""
Modelos para la gestión de productos del sistema POS.

Este módulo define el modelo Product que almacena información
de los productos disponibles para venta.
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class VATRate(models.TextChoices):
    """Alícuotas de IVA disponibles."""
    VAT_21 = '21.00', 'IVA 21%'
    VAT_10_5 = '10.50', 'IVA 10.5%'
    VAT_27 = '27.00', 'IVA 27%'
    VAT_5 = '5.00', 'IVA 5%'
    VAT_2_5 = '2.50', 'IVA 2.5%'
    VAT_0 = '0.00', 'IVA 0% (Exento)'


class ProductCategory(models.TextChoices):
    """Categorías de productos."""
    ELECTRONICS = 'ELECTRONICS', 'Electrónica'
    FOOD = 'FOOD', 'Alimentos'
    BEVERAGES = 'BEVERAGES', 'Bebidas'
    CLOTHING = 'CLOTHING', 'Indumentaria'
    HARDWARE = 'HARDWARE', 'Ferretería'
    STATIONERY = 'STATIONERY', 'Librería'
    HEALTH = 'HEALTH', 'Salud'
    OTHER = 'OTHER', 'Otros'


class Product(models.Model):
    """
    Producto disponible para venta en el sistema POS.

    Attributes:
        sku: Código único del producto (Stock Keeping Unit)
        name: Nombre descriptivo del producto
        description: Descripción detallada (opcional)
        price: Precio de venta unitario
        cost: Costo de adquisición (opcional, para reportes)
        vat_rate: Tasa de IVA aplicable (21%, 10.5%, 27%, etc.)
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
        help_text="Precio de venta unitario (máx: 9.999.999.999.999,99)",
    )
    cost = models.DecimalField(
        "Costo",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text="Costo de adquisición (opcional, máx: 9.999.999.999.999,99)",
    )
    vat_rate = models.CharField(
        "Tasa de IVA",
        max_length=5,
        choices=VATRate.choices,
        default=VATRate.VAT_21,
        help_text="Alícuota de IVA aplicable al producto"
    )
    category = models.CharField(
        "Categoría",
        max_length=20,
        choices=ProductCategory.choices,
        default=ProductCategory.OTHER,
        help_text="Categoría del producto para clasificación"
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
            models.Index(fields=["category"]),
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


class PriceChangeReason(models.TextChoices):
    """Razones para cambio de precio."""
    BULK_UPDATE = 'BULK_UPDATE', 'Actualización masiva'
    MANUAL_EDIT = 'MANUAL_EDIT', 'Edición manual'
    INITIAL_PRICE = 'INITIAL_PRICE', 'Precio inicial'
    CORRECTION = 'CORRECTION', 'Corrección'
    PROMOTION = 'PROMOTION', 'Promoción'
    COST_ADJUSTMENT = 'COST_ADJUSTMENT', 'Ajuste por costos'


class PriceHistory(models.Model):
    """
    Historial de cambios de precios de productos.

    Attributes:
        product: Producto al que pertenece el cambio
        old_price: Precio anterior
        new_price: Precio nuevo
        change_percentage: Porcentaje de cambio calculado
        reason: Razón del cambio (bulk update, manual, etc.)
        changed_by: Usuario que realizó el cambio
        changed_at: Fecha y hora del cambio
        notes: Notas adicionales (opcional)
        bulk_operation_id: ID para agrupar cambios de operaciones masivas

    Meta:
        ordering: Ordenado por fecha descendente (más recientes primero)
        indexes: Índices para optimizar búsquedas

    Patrones:
        - Denormalización: Guardamos old_price y new_price para mantener historial
        - SET_NULL en changed_by: Preservar historial aunque usuario se elimine
        - CASCADE en product: Si producto se elimina, su historial también
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name="Producto"
    )
    old_price = models.DecimalField(
        "Precio Anterior",
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    new_price = models.DecimalField(
        "Precio Nuevo",
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))]
    )
    change_percentage = models.DecimalField(
        "Porcentaje de Cambio",
        max_digits=8,
        decimal_places=2,
        help_text="Porcentaje de cambio (positivo = aumento, negativo = disminución)"
    )
    reason = models.CharField(
        "Razón del Cambio",
        max_length=20,
        choices=PriceChangeReason.choices,
        default=PriceChangeReason.MANUAL_EDIT
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='price_changes',
        verbose_name="Modificado por"
    )
    changed_at = models.DateTimeField(
        "Fecha de Cambio",
        auto_now_add=True
    )
    notes = models.TextField(
        "Notas",
        blank=True,
        help_text="Información adicional sobre el cambio"
    )
    bulk_operation_id = models.CharField(
        "ID de Operación Masiva",
        max_length=50,
        blank=True,
        db_index=True,
        help_text="ID para agrupar cambios de una misma operación masiva"
    )

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['product', '-changed_at']),
            models.Index(fields=['-changed_at']),
            models.Index(fields=['bulk_operation_id']),
            models.Index(fields=['changed_by']),
        ]
        verbose_name = "Historial de Precio"
        verbose_name_plural = "Historial de Precios"

    def __str__(self):
        return f"{self.product.sku}: ${self.old_price} → ${self.new_price} ({self.changed_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def price_difference(self):
        """Calcula la diferencia de precio."""
        return self.new_price - self.old_price

    @property
    def is_increase(self):
        """Indica si fue un aumento de precio."""
        return self.new_price > self.old_price

    @property
    def is_decrease(self):
        """Indica si fue una disminución de precio."""
        return self.new_price < self.old_price
