"""
Capa de servicio para gestión de productos.

Este módulo implementa el Service Layer Pattern con validaciones
de negocio para operaciones de productos.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q, QuerySet

from .models import PriceChangeReason, PriceHistory, Product


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
        update_product: Actualiza producto (registra cambios de precio)
        deactivate_product: Desactiva producto (soft delete)
        bulk_update_prices: Actualización masiva de precios
        record_price_change: Registra cambio de precio en historial
        get_price_history: Obtiene historial de cambios de precios
    """

    @staticmethod
    def record_price_change(
        product: Product,
        old_price: Decimal,
        new_price: Decimal,
        reason: str,
        user=None,
        notes: str = "",
        bulk_operation_id: str = "",
    ) -> PriceHistory:
        """
        Registra un cambio de precio en el historial.

        Args:
            product: Producto cuyo precio cambió
            old_price: Precio anterior
            new_price: Precio nuevo
            reason: Razón del cambio (ver PriceChangeReason)
            user: Usuario que realizó el cambio (opcional)
            notes: Notas adicionales (opcional)
            bulk_operation_id: ID para agrupar operaciones masivas

        Returns:
            PriceHistory: Registro creado

        Nota:
            El porcentaje de cambio se calcula automáticamente
        """
        # Calcular porcentaje de cambio
        if old_price > 0:
            change_percentage = ((new_price - old_price) / old_price) * 100
        else:
            change_percentage = Decimal('0')

        return PriceHistory.objects.create(
            product=product,
            old_price=old_price,
            new_price=new_price,
            change_percentage=change_percentage,
            reason=reason,
            changed_by=user,
            notes=notes,
            bulk_operation_id=bulk_operation_id,
        )

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
        category: str = "OTHER",
        description: str = "",
        cost: Optional[Decimal] = None,
    ) -> Product:
        """
        Crea nuevo producto.

        Args:
            sku: Código SKU único
            name: Nombre del producto
            price: Precio de venta
            category: Categoría del producto
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
            category=category,
            description=description,
            cost=cost,
        )

    @staticmethod
    @transaction.atomic
    def update_product(
        sku: str,
        name: Optional[str] = None,
        category: Optional[str] = None,
        price: Optional[Decimal] = None,
        description: Optional[str] = None,
        cost: Optional[Decimal] = None,
        user=None,
    ) -> Product:
        """
        Actualiza un producto existente.

        Args:
            sku: SKU del producto a actualizar
            name: Nuevo nombre (opcional)
            category: Nueva categoría (opcional)
            price: Nuevo precio (opcional)
            description: Nueva descripción (opcional)
            cost: Nuevo costo (opcional)
            user: Usuario que realiza la actualización (para historial)

        Returns:
            Product: Producto actualizado

        Raises:
            ValidationError: Si el producto no existe o datos inválidos

        Nota:
            Si el precio cambia, se registra automáticamente en el historial
        """
        try:
            product = Product.objects.select_for_update().get(sku=sku)
        except Product.DoesNotExist:
            raise ValidationError(f"Producto con SKU '{sku}' no encontrado")

        # Guardar precio anterior para historial
        old_price = product.price

        if name is not None:
            product.name = name

        if category is not None:
            product.category = category

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

        # Registrar cambio de precio si hubo modificación
        if price is not None and price != old_price:
            ProductService.record_price_change(
                product=product,
                old_price=old_price,
                new_price=price,
                reason=PriceChangeReason.MANUAL_EDIT,
                user=user,
                notes=f"Actualización manual del producto {product.sku}",
            )

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

    @staticmethod
    def get_price_history(
        product_sku: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        reason: Optional[str] = None,
        bulk_operation_id: Optional[str] = None,
        limit: int = 100,
    ) -> QuerySet[PriceHistory]:
        """
        Obtiene historial de cambios de precios con filtros.

        Args:
            product_sku: Filtrar por SKU de producto (opcional)
            start_date: Fecha inicial (opcional)
            end_date: Fecha final (opcional)
            reason: Filtrar por razón del cambio (opcional)
            bulk_operation_id: Filtrar por operación masiva específica (opcional)
            limit: Cantidad máxima de resultados (default: 100)

        Returns:
            QuerySet con historial de precios ordenado por fecha descendente

        Patrones ORM:
            - select_related para optimizar queries (evitar N+1)
            - Filtros dinámicos basados en parámetros
            - Ordenamiento por fecha descendente

        Ejemplo:
            # Historial de un producto específico
            history = ProductService.get_price_history(product_sku='ABC123', limit=50)

            # Historial de operaciones masivas
            history = ProductService.get_price_history(reason='BULK_UPDATE')
        """
        queryset = PriceHistory.objects.select_related(
            'product',
            'changed_by'
        ).all()

        # Filtrar por producto
        if product_sku:
            queryset = queryset.filter(product__sku=product_sku)

        # Filtrar por rango de fechas
        if start_date:
            queryset = queryset.filter(changed_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(changed_at__lte=end_date)

        # Filtrar por razón
        if reason:
            queryset = queryset.filter(reason=reason)

        # Filtrar por operación masiva
        if bulk_operation_id:
            queryset = queryset.filter(bulk_operation_id=bulk_operation_id)

        # Ordenar por fecha descendente y limitar
        return queryset.order_by('-changed_at')[:limit]

    @staticmethod
    def get_bulk_operations() -> list[dict]:
        """
        Obtiene un resumen de todas las operaciones masivas realizadas.

        Returns:
            Lista de operaciones masivas con información agregada

        Ejemplo de retorno:
            [
                {
                    'bulk_operation_id': 'bulk_20250127_...',
                    'changed_at': datetime(...),
                    'changed_by': User(...),
                    'products_affected': 15,
                    'notes': 'Actualización masiva: +10% aplicado a Electrónica'
                },
                ...
            ]
        """
        # Obtener operaciones masivas únicas
        bulk_operations = (
            PriceHistory.objects.filter(reason=PriceChangeReason.BULK_UPDATE)
            .exclude(bulk_operation_id='')
            .values('bulk_operation_id')
            .distinct()
        )

        result = []
        for op in bulk_operations:
            bulk_id = op['bulk_operation_id']

            # Obtener información de la operación
            first_record = (
                PriceHistory.objects.filter(bulk_operation_id=bulk_id)
                .select_related('changed_by')
                .first()
            )

            if first_record:
                # Contar productos afectados
                products_count = PriceHistory.objects.filter(
                    bulk_operation_id=bulk_id
                ).count()

                result.append({
                    'bulk_operation_id': bulk_id,
                    'changed_at': first_record.changed_at,
                    'changed_by': first_record.changed_by,
                    'products_affected': products_count,
                    'notes': first_record.notes,
                    'change_percentage': first_record.change_percentage,
                })

        # Ordenar por fecha descendente
        result.sort(key=lambda x: x['changed_at'], reverse=True)

        return result

    @staticmethod
    @transaction.atomic
    def bulk_update_prices(
        percentage_adjustment: Decimal,
        category: Optional[str] = None,
        only_active: bool = True,
        user=None,
    ) -> dict:
        """
        Actualización masiva de precios con ajuste porcentual.

        Args:
            percentage_adjustment: Porcentaje de ajuste (ej: 10 para +10%, -5 para -5%)
            category: Categoría de productos a actualizar (None = todos)
            only_active: Si True, solo actualiza productos activos
            user: Usuario que realiza la actualización (para historial)

        Returns:
            dict: Información sobre la actualización (productos afectados, etc.)

        Raises:
            ValidationError: Si los parámetros son inválidos

        Patrones ORM:
            - F() expressions para actualizaciones atómicas a nivel de DB
            - Filtros dinámicos basados en parámetros
            - transaction.atomic para garantizar consistencia
            - Registro automático en historial

        Ejemplo:
            # Aumentar 10% precios de Electrónica
            result = ProductService.bulk_update_prices(10, category='ELECTRONICS', user=request.user)
            # result = {'updated_count': 15, 'category': 'ELECTRONICS', 'adjustment': 10, 'bulk_id': '...'}
        """
        # Validar porcentaje
        if percentage_adjustment == 0:
            raise ValidationError("El porcentaje de ajuste no puede ser 0")

        if percentage_adjustment < -100:
            raise ValidationError("El porcentaje de ajuste no puede ser menor a -100%")

        # Construir queryset base
        queryset = Product.objects.all()

        # Filtrar por estado activo
        if only_active:
            queryset = queryset.filter(is_active=True)

        # Filtrar por categoría
        if category:
            queryset = queryset.filter(category=category)

        # Contar productos antes de actualizar
        affected_count = queryset.count()

        if affected_count == 0:
            raise ValidationError("No hay productos que coincidan con los criterios de filtrado")

        # Calcular multiplicador (ej: 10% = 1.10, -5% = 0.95)
        multiplier = Decimal('1') + (percentage_adjustment / Decimal('100'))

        # Generar ID único para esta operación masiva
        bulk_operation_id = f"bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

        # PASO 1: Obtener productos con precios actuales ANTES de actualizar
        # Usamos list() para forzar evaluación y evitar que F() expressions afecten los valores
        products_snapshot = list(queryset.values('id', 'sku', 'price'))

        # PASO 2: Actualización atómica usando F() expressions
        # F('price') * multiplier calcula el nuevo precio en la base de datos
        queryset.update(price=F('price') * multiplier)

        # PASO 3: Crear registros de historial para cada producto
        # Preparar notas descriptivas
        category_text = dict(Product._meta.get_field('category').choices).get(category) if category else "todas las categorías"
        notes = f"Actualización masiva: {percentage_adjustment:+.2f}% aplicado a {category_text}"

        # Crear registros de historial en batch
        history_records = []
        for snapshot in products_snapshot:
            old_price = snapshot['price']
            new_price = old_price * multiplier

            # Calcular porcentaje de cambio
            change_percentage = percentage_adjustment

            history_records.append(
                PriceHistory(
                    product_id=snapshot['id'],
                    old_price=old_price,
                    new_price=new_price,
                    change_percentage=change_percentage,
                    reason=PriceChangeReason.BULK_UPDATE,
                    changed_by=user,
                    notes=notes,
                    bulk_operation_id=bulk_operation_id,
                )
            )

        # Inserción masiva de registros de historial
        PriceHistory.objects.bulk_create(history_records)

        return {
            'updated_count': affected_count,
            'category': category,
            'category_display': category_text,
            'percentage_adjustment': float(percentage_adjustment),
            'multiplier': float(multiplier),
            'bulk_operation_id': bulk_operation_id,
        }
