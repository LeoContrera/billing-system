"""
Capa de servicio para gestión de productos.

Este módulo implementa el Service Layer Pattern con validaciones
de negocio para operaciones de productos.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet

from .models import Product


@dataclass
class ProductData:
    """
    Data Transfer Object para información de producto.

    Usado para transferir datos entre capas sin exponer el modelo directamente.
    """

    id: int
    sku: str
    name: str
    price: Decimal
    is_active: bool


class ProductService:
    """
    Lógica de negocio para gestión de productos.

    Métodos:
        validate_sku: Valida SKU y retorna datos del producto
        get_product_info: Obtiene información completa de producto
        search_products: Búsqueda de productos por nombre o SKU
        create_product: Crea nuevo producto
        deactivate_product: Desactiva producto (soft delete)
    """

    @staticmethod
    def validate_sku(sku: str) -> ProductData:
        """
        Valida SKU y retorna datos del producto si es válido.

        Args:
            sku: Código SKU del producto

        Returns:
            ProductData: Datos del producto validado

        Raises:
            ValidationError: Si el SKU no existe o el producto está inactivo

        Uso en POS:
            product_data = ProductService.validate_sku("ABC123")
            # Ahora puedes usar product_data.name, product_data.price
        """
        if not sku:
            raise ValidationError("El SKU es requerido")

        try:
            product = Product.objects.only(
                "id", "sku", "name", "price", "is_active"
            ).get(sku=sku)
        except Product.DoesNotExist:
            raise ValidationError(f"Producto con SKU '{sku}' no encontrado")

        if not product.is_active:
            raise ValidationError(
                f"El producto '{product.name}' no está disponible para venta"
            )

        return ProductData(
            id=product.id,
            sku=product.sku,
            name=product.name,
            price=product.price,
            is_active=product.is_active,
        )

    @staticmethod
    def get_product_info(sku: str) -> Optional[Product]:
        """
        Obtiene información completa del producto.

        Args:
            sku: Código SKU del producto

        Returns:
            Product o None si no existe

        Patrones ORM:
            - Retorna modelo completo para casos donde se necesita toda la info
        """
        try:
            return Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            return None

    @staticmethod
    def get_product_by_id(product_id: int) -> Optional[Product]:
        """
        Obtiene producto por ID.

        Args:
            product_id: ID del producto

        Returns:
            Product o None si no existe
        """
        try:
            return Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return None

    @staticmethod
    def search_products(query: str, limit: int = 20) -> QuerySet[Product]:
        """
        Búsqueda de productos por nombre o SKU.

        Args:
            query: Texto de búsqueda
            limit: Cantidad máxima de resultados

        Returns:
            QuerySet con productos que coinciden

        Patrones ORM:
            - Q objects para consultas OR
            - icontains para búsqueda case-insensitive
            - filter(is_active=True) para mostrar solo productos activos
        """
        if not query:
            return Product.objects.filter(is_active=True)[:limit]

        return Product.objects.filter(
            Q(is_active=True) & (Q(sku__icontains=query) | Q(name__icontains=query))
        ).only("id", "sku", "name", "price")[:limit]

    @staticmethod
    @transaction.atomic
    def create_product(
        sku: str,
        name: str,
        price: Decimal,
        description: str = "",
        cost: Optional[Decimal] = None,
    ) -> Product:
        """
        Crea nuevo producto.

        Args:
            sku: Código SKU único
            name: Nombre del producto
            price: Precio de venta
            description: Descripción opcional
            cost: Costo de adquisición opcional

        Returns:
            Product: Producto creado

        Raises:
            ValidationError: Si el SKU ya existe o datos inválidos
        """
        if Product.objects.filter(sku=sku).exists():
            raise ValidationError(f"Ya existe un producto con SKU '{sku}'")

        if price < 0:
            raise ValidationError("El precio no puede ser negativo")

        return Product.objects.create(
            sku=sku,
            name=name,
            price=price,
            description=description,
            cost=cost,
        )

    @staticmethod
    @transaction.atomic
    def update_product(
        sku: str,
        name: Optional[str] = None,
        price: Optional[Decimal] = None,
        description: Optional[str] = None,
        cost: Optional[Decimal] = None,
    ) -> Product:
        """
        Actualiza un producto existente.

        Args:
            sku: SKU del producto a actualizar
            name: Nuevo nombre (opcional)
            price: Nuevo precio (opcional)
            description: Nueva descripción (opcional)
            cost: Nuevo costo (opcional)

        Returns:
            Product: Producto actualizado

        Raises:
            ValidationError: Si el producto no existe o datos inválidos
        """
        try:
            product = Product.objects.select_for_update().get(sku=sku)
        except Product.DoesNotExist:
            raise ValidationError(f"Producto con SKU '{sku}' no encontrado")

        if name is not None:
            product.name = name

        if price is not None:
            if price < 0:
                raise ValidationError("El precio no puede ser negativo")
            product.price = price

        if description is not None:
            product.description = description

        if cost is not None:
            if cost < 0:
                raise ValidationError("El costo no puede ser negativo")
            product.cost = cost

        product.save()
        return product

    @staticmethod
    @transaction.atomic
    def toggle_active(sku: str) -> Product:
        """
        Alterna el estado activo/inactivo de un producto.

        Args:
            sku: SKU del producto

        Returns:
            Product: Producto con estado actualizado

        Raises:
            ValidationError: Si el producto no existe

        Nota:
            Se usa soft delete porque los productos pueden estar
            referenciados en ventas históricas.
        """
        try:
            product = Product.objects.select_for_update().get(sku=sku)
        except Product.DoesNotExist:
            raise ValidationError(f"Producto con SKU '{sku}' no encontrado")

        product.is_active = not product.is_active
        product.save(update_fields=["is_active", "updated_at"])

        return product

    @staticmethod
    @transaction.atomic
    def deactivate_product(sku: str) -> Product:
        """
        Desactiva producto (soft delete).

        Args:
            sku: SKU del producto a desactivar

        Returns:
            Product: Producto desactivado

        Raises:
            ValidationError: Si el producto no existe

        Nota:
            Se usa soft delete porque los productos pueden estar
            referenciados en ventas históricas.
        """
        try:
            product = Product.objects.select_for_update().get(sku=sku)
        except Product.DoesNotExist:
            raise ValidationError(f"Producto con SKU '{sku}' no encontrado")

        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])

        return product

    @staticmethod
    def list_products(
        search_query: str = "",
        order_by: str = "name",
        show_inactive: bool = False,
    ) -> QuerySet[Product]:
        """
        Lista productos con filtros y ordenamiento.

        Args:
            search_query: Texto de búsqueda por SKU o nombre
            order_by: Campo de ordenamiento (name, -name, sku, -sku, price, -price, created_at, -created_at)
            show_inactive: Si True, incluye productos inactivos

        Returns:
            QuerySet con productos filtrados y ordenados

        Patrones ORM:
            - Q objects para consultas OR complejas
            - Ordenamiento dinámico con order_by()
            - Filter condicional basado en show_inactive
        """
        queryset = Product.objects.all()

        # Filtrar por estado activo/inactivo
        if not show_inactive:
            queryset = queryset.filter(is_active=True)

        # Búsqueda por SKU o nombre
        if search_query:
            queryset = queryset.filter(
                Q(sku__icontains=search_query) | Q(name__icontains=search_query)
            )

        # Validar campo de ordenamiento
        valid_order_fields = [
            "name", "-name",
            "sku", "-sku",
            "price", "-price",
            "created_at", "-created_at"
        ]
        if order_by in valid_order_fields:
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by("name")

        return queryset
