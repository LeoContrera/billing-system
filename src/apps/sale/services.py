"""
Capa de servicio para gestión de ventas.

Este módulo implementa el Service Layer Pattern con transacciones atómicas
para garantizar la integridad de las operaciones de venta.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from cash_session.services import CashSessionService
from customers.models import Customer
from inventory.services import InventoryService
from products.models import Product
from products.services import ProductService

from .models import Sale, SaleLineItem


class SaleService:
    """
    Lógica de negocio para gestión de ventas.

    Métodos:
        create_sale: Crea nueva venta en estado PENDING
        set_customer: Asigna cliente a venta
        add_line_item: Agrega producto a la venta
        apply_global_discount: Aplica descuento global
        apply_line_discount: Aplica descuento a línea específica
        finalize_sale: Finaliza venta (transacción atómica crítica)
    """

    @staticmethod
    @transaction.atomic
    def create_sale(user) -> Sale:
        """
        Crea nueva venta en estado PENDING.

        Args:
            user: Usuario que crea la venta (cajero)

        Returns:
            Sale: Nueva venta creada

        Raises:
            ValidationError: Si no se puede obtener o crear una sesión de caja

        Patrón: Factory Method

        Nota: Obtiene o crea automáticamente una sesión de caja abierta
        para el usuario. Si no existe una sesión activa, crea una nueva
        con balance inicial de 0.
        """
        # Obtener sesión de caja activa del usuario
        cash_session = CashSessionService.get_active_session(user)

        # Si no existe, crear una nueva sesión automáticamente
        if not cash_session:
            cash_session = CashSessionService.open_session(user)

        return Sale.objects.create(
            cash_session=cash_session,
            created_by=user,
            status=Sale.PENDING
        )

    @staticmethod
    @transaction.atomic
    def set_customer(sale_id: int, customer_id: int) -> Sale:
        """
        Asigna cliente a venta.

        Args:
            sale_id: ID de la venta
            customer_id: ID del cliente

        Returns:
            Sale: Venta actualizada

        Raises:
            ValidationError: Si la venta no está en estado PENDING

        Patrones ORM:
            - select_for_update() previene race conditions
        """
        sale = Sale.objects.select_for_update().get(pk=sale_id)

        if sale.status != Sale.PENDING:
            raise ValidationError("Solo se puede modificar ventas pendientes")

        sale.customer = Customer.objects.get(pk=customer_id)
        sale.save(update_fields=['customer'])
        return sale

    @staticmethod
    @transaction.atomic
    def add_line_item(
        sale_id: int,
        sku: str,
        quantity: Decimal,
    ) -> SaleLineItem:
        """
        Agrega producto a la venta con validación de producto e inventario.

        Args:
            sale_id: ID de la venta
            sku: Código SKU del producto
            quantity: Cantidad a vender

        Returns:
            SaleLineItem: Línea de producto creada

        Raises:
            ValidationError: Si la venta no está PENDING, producto inválido,
                            o stock insuficiente

        Flujo (Steps 3-7 del diagrama de secuencia):
            1. Lock de la venta, validar que esté PENDING
            2. ProductService.validate_sku(sku) - obtener datos del producto
            3. InventoryService.check_availability(sku, qty) - verificar stock
            4. Si no hay stock: raise ValidationError("Stock insuficiente")
            5. Si hay stock: crear SaleLineItem con datos del producto

        Patrones:
            - Validación de negocio (sale debe estar PENDING)
            - select_for_update() para lock pesimista
            - Integración con ProductService e InventoryService
        """
        # 1. Lock de la venta
        sale = Sale.objects.select_for_update().get(pk=sale_id)

        if sale.status != Sale.PENDING:
            raise ValidationError("No se pueden agregar items a venta completada")

        if quantity <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero")

        # 2. Validar producto (Step 3 del diagrama)
        product_data = ProductService.validate_sku(sku)

        # 3. Verificar disponibilidad de stock (Steps 4-5)
        if not InventoryService.check_availability(sku, quantity):
            # Step 7: Stock insuficiente
            stock_level = InventoryService.get_stock_level(sku)
            raise ValidationError(
                f"Stock insuficiente para '{product_data.name}'. "
                f"Disponible: {stock_level or 0}, Solicitado: {quantity}"
            )

        # Step 6: Agregar al carrito con datos del producto
        product = Product.objects.get(pk=product_data.id)

        return SaleLineItem.objects.create(
            sale=sale,
            product=product,
            product_name=product_data.name,
            sku=product_data.sku,
            quantity=quantity,
            unit_price=product_data.price,
            vat_rate=product.vat_rate,  # Desnormalizar para historial fiscal
        )

    @staticmethod
    @transaction.atomic
    def apply_global_discount(sale_id: int, discount_amount: Decimal) -> Sale:
        """
        Aplica descuento global a la venta.

        Args:
            sale_id: ID de la venta
            discount_amount: Monto del descuento

        Returns:
            Sale: Venta actualizada

        Raises:
            ValidationError: Si descuento es negativo o excede el subtotal

        Validaciones:
            - Descuento no puede ser negativo
            - Descuento no puede exceder subtotal
        """
        sale = (Sale.objects
                .select_for_update()
                .select_related('customer')
                .prefetch_related('line_items')
                .get(pk=sale_id))

        if sale.status != Sale.PENDING:
            raise ValidationError("Solo se puede descontar en ventas pendientes")

        if discount_amount < 0:
            raise ValidationError("El descuento no puede ser negativo")

        if discount_amount > sale.subtotal:
            raise ValidationError(f"El descuento no puede exceder el subtotal (${sale.subtotal})")

        sale.global_discount_amount = discount_amount
        sale.save(update_fields=['global_discount_amount'])
        return sale

    @staticmethod
    @transaction.atomic
    def apply_line_discount(line_item_id: int, discount_amount: Decimal) -> SaleLineItem:
        """
        Aplica descuento a línea específica.

        Args:
            line_item_id: ID de la línea de producto
            discount_amount: Monto del descuento

        Returns:
            SaleLineItem: Línea actualizada

        Raises:
            ValidationError: Si descuento es negativo o excede el máximo

        Patrones ORM:
            - select_related() para fetch del Sale en una sola query
        """
        line_item = (SaleLineItem.objects
                     .select_related('sale')
                     .select_for_update()
                     .get(pk=line_item_id))

        if line_item.sale.status != Sale.PENDING:
            raise ValidationError("Solo se puede descontar en ventas pendientes")

        if discount_amount < 0:
            raise ValidationError("El descuento no puede ser negativo")

        max_discount = line_item.quantity * line_item.unit_price
        if discount_amount > max_discount:
            raise ValidationError(f"El descuento no puede exceder ${max_discount}")

        line_item.discount_amount = discount_amount
        line_item.save(update_fields=['discount_amount'])
        return line_item

    @staticmethod
    @transaction.atomic
    def finalize_sale(sale_id: int, user) -> Sale:
        """
        Finaliza venta (transacción atómica crítica).

        Args:
            sale_id: ID de la venta
            user: Usuario que finaliza (para registro de movimientos)

        Returns:
            Sale: Venta finalizada

        Raises:
            ValidationError: Si venta ya está completada, no está pagada,
                            o hay stock insuficiente para algún item

        Patrones:
            - @transaction.atomic garantiza que todo se ejecuta o nada
            - select_for_update() previene concurrencia
            - Validaciones de negocio complejas
            - Descuento de inventario integrado

        Flujo:
            1. Lock de la venta
            2. Validar que esté pagada
            3. Descontar inventario (register_sale_movements)
            4. Actualizar estado a COMPLETED
            5. Registrar timestamp
        """
        from django.utils import timezone

        sale = (Sale.objects
                .select_for_update()
                .select_related('customer', 'created_by')
                .prefetch_related('line_items', 'transactions__payment_method')
                .get(pk=sale_id))

        if sale.status == Sale.COMPLETED:
            raise ValidationError("Esta venta ya está finalizada")

        if not sale.is_fully_paid:
            raise ValidationError(
                f"La venta no está completamente pagada. "
                f"Falta: ${sale.remaining_balance}"
            )

        # Descontar inventario para todos los items con SKU
        # Si algún item no tiene stock suficiente, se hace rollback de todo
        line_items_with_sku = sale.line_items.filter(sku__isnull=False).exclude(sku='')
        if line_items_with_sku.exists():
            InventoryService.register_sale_movements(
                sale_id=sale.id,
                line_items=line_items_with_sku,
                user=user,
            )

        sale.status = Sale.COMPLETED
        sale.completed_at = timezone.now()
        sale.save(update_fields=['status', 'completed_at'])

        return sale
