"""
Capa de servicio para gestión de ventas.

Este módulo implementa el Service Layer Pattern con transacciones atómicas
para garantizar la integridad de las operaciones de venta.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Sale, SaleLineItem
from customers.models import Customer


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

        Patrón: Factory Method
        """
        return Sale.objects.create(
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
        product_name: str,
        quantity: Decimal,
        unit_price: Decimal,
        sku: str = ''
    ) -> SaleLineItem:
        """
        Agrega producto a la venta.

        Args:
            sale_id: ID de la venta
            product_name: Nombre del producto
            quantity: Cantidad
            unit_price: Precio unitario
            sku: Código SKU (opcional)

        Returns:
            SaleLineItem: Línea de producto creada

        Raises:
            ValidationError: Si la venta no está PENDING, cantidad <= 0, o precio < 0

        Patrones:
            - Validación de negocio (sale debe estar PENDING)
            - select_for_update() para lock pesimista
        """
        sale = Sale.objects.select_for_update().get(pk=sale_id)

        if sale.status != Sale.PENDING:
            raise ValidationError("No se pueden agregar items a venta completada")

        if quantity <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero")

        if unit_price < 0:
            raise ValidationError("El precio no puede ser negativo")

        return SaleLineItem.objects.create(
            sale=sale,
            product_name=product_name,
            sku=sku,
            quantity=quantity,
            unit_price=unit_price
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
    def finalize_sale(sale_id: int) -> Sale:
        """
        Finaliza venta (transacción atómica crítica).

        Args:
            sale_id: ID de la venta

        Returns:
            Sale: Venta finalizada

        Raises:
            ValidationError: Si venta ya está completada o no está pagada

        Patrones:
            - @transaction.atomic garantiza que todo se ejecuta o nada
            - select_for_update() previene concurrencia
            - Validaciones de negocio complejas

        Flujo:
            1. Lock de la venta
            2. Validar que esté pagada
            3. Actualizar estado a COMPLETED
            4. Registrar timestamp
            5. (Futuro) Descontar inventario
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

        sale.status = Sale.COMPLETED
        sale.completed_at = timezone.now()
        sale.save(update_fields=['status', 'completed_at'])

        return sale
