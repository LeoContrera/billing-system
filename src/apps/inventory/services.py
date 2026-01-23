"""
Capa de servicio para gestión de inventario.

Este módulo implementa el Service Layer Pattern con transacciones atómicas
y locking pesimista para garantizar la integridad del inventario.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from products.models import Product

from .models import Movement, Stock


@dataclass
class MovementResult:
    """
    Resultado de un movimiento de inventario.
    """

    success: bool
    movement: Optional[Movement]
    previous_qty: Decimal
    new_qty: Decimal
    message: str


class InventoryService:
    """
    Lógica de negocio para gestión de inventario.

    Métodos:
        check_availability: Verifica disponibilidad de stock
        register_movement: Registra movimiento de inventario
        register_sale_movements: Registra movimientos para una venta completa
        get_stock_level: Obtiene nivel actual de stock
        get_products_below_minimum: Lista productos bajo mínimo
        adjust_stock: Ajusta stock a cantidad específica
    """

    @staticmethod
    def check_availability(
        sku: str, quantity: Decimal, location: str = "PRINCIPAL"
    ) -> bool:
        """
        Verifica si hay stock disponible para la cantidad solicitada.

        Args:
            sku: SKU del producto
            quantity: Cantidad requerida
            location: Ubicación del stock (default: PRINCIPAL)

        Returns:
            bool: True si hay stock suficiente, False en caso contrario

        Uso en POS (Steps 3-5):
            if not InventoryService.check_availability("ABC123", qty):
                raise ValidationError("Stock insuficiente")

        Nota:
            Este método NO bloquea el registro. Para operaciones que modifican
            stock, usar register_movement() que incluye select_for_update().
        """
        if quantity <= 0:
            return False

        try:
            stock = (
                Stock.objects.select_related("product")
                .only("current_qty", "product__sku")
                .get(product__sku=sku, location=location)
            )
            return stock.current_qty >= quantity
        except Stock.DoesNotExist:
            return False

    @staticmethod
    def get_stock_level(sku: str, location: str = "PRINCIPAL") -> Optional[Decimal]:
        """
        Obtiene el nivel actual de stock de un producto.

        Args:
            sku: SKU del producto
            location: Ubicación del stock

        Returns:
            Decimal: Cantidad actual o None si no existe registro
        """
        try:
            stock = Stock.objects.only("current_qty").get(
                product__sku=sku, location=location
            )
            return stock.current_qty
        except Stock.DoesNotExist:
            return None

    @staticmethod
    @transaction.atomic
    def register_movement(
        sku: str,
        movement_type: str,
        quantity: Decimal,
        user,
        reference: str = "",
        notes: str = "",
        location: str = "PRINCIPAL",
    ) -> MovementResult:
        """
        Registra un movimiento de inventario.

        Args:
            sku: SKU del producto
            movement_type: Tipo de movimiento (SALE, PURCHASE, etc.)
            quantity: Cantidad del movimiento (siempre positiva)
            user: Usuario que registra el movimiento
            reference: Referencia externa (ej: "SALE-123")
            notes: Notas adicionales
            location: Ubicación del stock

        Returns:
            MovementResult: Resultado de la operación

        Raises:
            ValidationError: Si el producto no existe o tipo inválido

        Patrones ORM:
            - select_for_update() para locking pesimista
            - @transaction.atomic para integridad
            - F() expression para actualización atómica de cantidad

        Uso en finalize_sale():
            for item in sale.line_items.all():
                InventoryService.register_movement(
                    sku=item.sku,
                    movement_type=Movement.SALE,
                    quantity=item.quantity,
                    user=user,
                    reference=f"SALE-{sale.id}"
                )
        """
        valid_types = [choice[0] for choice in Movement.MOVEMENT_CHOICES]
        if movement_type not in valid_types:
            raise ValidationError(f"Tipo de movimiento inválido: {movement_type}")

        if quantity <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero")

        outgoing_types = [Movement.SALE, Movement.ADJUSTMENT_OUT, Movement.TRANSFER_OUT]
        is_outgoing = movement_type in outgoing_types

        try:
            product = Product.objects.get(sku=sku)
        except Product.DoesNotExist:
            raise ValidationError(f"Producto con SKU '{sku}' no encontrado")

        stock, created = Stock.objects.select_for_update().get_or_create(
            product=product,
            location=location,
            defaults={"current_qty": Decimal("0.000")},
        )

        previous_qty = stock.current_qty
        delta = -quantity if is_outgoing else quantity

        if is_outgoing and stock.current_qty < quantity:
            return MovementResult(
                success=False,
                movement=None,
                previous_qty=previous_qty,
                new_qty=previous_qty,
                message=f"Stock insuficiente. Disponible: {stock.current_qty}, Requerido: {quantity}",
            )

        Stock.objects.filter(pk=stock.pk).update(current_qty=F("current_qty") + delta)
        stock.refresh_from_db()

        movement = Movement.objects.create(
            stock=stock,
            movement_type=movement_type,
            delta_qty=delta,
            previous_qty=previous_qty,
            reference=reference,
            notes=notes,
            created_by=user,
        )

        return MovementResult(
            success=True,
            movement=movement,
            previous_qty=previous_qty,
            new_qty=stock.current_qty,
            message="Movimiento registrado exitosamente",
        )

    @staticmethod
    @transaction.atomic
    def register_sale_movements(
        sale_id: int, line_items, user, location: str = "PRINCIPAL"
    ) -> List[MovementResult]:
        """
        Registra movimientos de venta para múltiples items.

        Args:
            sale_id: ID de la venta
            line_items: Lista de SaleLineItem (con sku y quantity)
            user: Usuario que registra
            location: Ubicación del stock

        Returns:
            List[MovementResult]: Resultados de cada movimiento

        Raises:
            ValidationError: Si algún item no tiene stock suficiente

        Uso en finalize_sale():
            results = InventoryService.register_sale_movements(
                sale_id=sale.id,
                line_items=sale.line_items.all(),
                user=request.user
            )
        """
        results = []

        for item in line_items:
            if not item.sku:
                continue

            result = InventoryService.register_movement(
                sku=item.sku,
                movement_type=Movement.SALE,
                quantity=item.quantity,
                user=user,
                reference=f"SALE-{sale_id}",
                location=location,
            )

            if not result.success:
                raise ValidationError(
                    f"Stock insuficiente para '{item.product_name}' ({item.sku}). "
                    f"Disponible: {result.previous_qty}, Requerido: {item.quantity}"
                )

            results.append(result)

        return results

    @staticmethod
    def get_products_below_minimum(location: str = "") -> List[Stock]:
        """
        Lista productos con stock bajo el mínimo.

        Args:
            location: Filtrar por ubicación (vacío = todas)

        Returns:
            List[Stock]: Registros de stock bajo mínimo
        """
        queryset = Stock.objects.select_related("product").filter(
            current_qty__lt=F("min_qty")
        )

        if location:
            queryset = queryset.filter(location=location)

        return list(queryset)

    @staticmethod
    @transaction.atomic
    def adjust_stock(
        sku: str,
        new_quantity: Decimal,
        user,
        notes: str = "",
        location: str = "PRINCIPAL",
    ) -> MovementResult:
        """
        Ajusta el stock a una cantidad específica (inventario físico).

        Args:
            sku: SKU del producto
            new_quantity: Nueva cantidad después del conteo físico
            user: Usuario que realiza el ajuste
            notes: Notas del ajuste
            location: Ubicación del stock

        Returns:
            MovementResult: Resultado de la operación

        Uso:
            # Conteo físico muestra 50 unidades, sistema tiene 45
            result = InventoryService.adjust_stock("ABC123", Decimal("50"), user)
            # Crea movimiento ADJ_IN por 5 unidades
        """
        if new_quantity < 0:
            raise ValidationError("La cantidad no puede ser negativa")

        current_qty = InventoryService.get_stock_level(sku, location)

        if current_qty is None:
            return InventoryService.register_movement(
                sku=sku,
                movement_type=Movement.ADJUSTMENT_IN,
                quantity=new_quantity,
                user=user,
                notes=f"Stock inicial. {notes}".strip(),
                location=location,
            )

        difference = new_quantity - current_qty

        if difference == 0:
            return MovementResult(
                success=True,
                movement=None,
                previous_qty=current_qty,
                new_qty=current_qty,
                message="Sin diferencia de inventario",
            )

        if difference > 0:
            movement_type = Movement.ADJUSTMENT_IN
            quantity = difference
        else:
            movement_type = Movement.ADJUSTMENT_OUT
            quantity = abs(difference)

        return InventoryService.register_movement(
            sku=sku,
            movement_type=movement_type,
            quantity=quantity,
            user=user,
            notes=f"Ajuste de inventario. Diferencia: {difference}. {notes}".strip(),
            location=location,
        )
