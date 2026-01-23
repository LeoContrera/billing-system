"""
Capa de servicio para procesamiento de pagos.

Este módulo implementa la lógica de negocio para registrar pagos
asociados a ventas.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import PaymentMethod, Transaction
from sale.models import Sale


class PaymentService:
    """
    Lógica de negocio para procesamiento de pagos.

    Métodos:
        get_active_payment_methods: Obtiene métodos de pago activos
        add_payment: Registra pago parcial o total
    """

    @staticmethod
    def get_active_payment_methods():
        """
        Obtiene métodos de pago activos para UI.

        Returns:
            QuerySet con métodos de pago activos

        Uso:
            payment_methods = PaymentService.get_active_payment_methods()
            for method in payment_methods:
                print(method.name)
        """
        return PaymentMethod.objects.filter(is_active=True)

    @staticmethod
    @transaction.atomic
    def add_payment(
        sale_id: int,
        payment_method_id: int,
        amount: Decimal,
        user
    ) -> Transaction:
        """
        Registra pago parcial o total.

        Args:
            sale_id: ID de la venta
            payment_method_id: ID del método de pago
            amount: Monto del pago
            user: Usuario que registra el pago

        Returns:
            Transaction: Transacción de pago creada

        Raises:
            ValidationError: Si venta ya está completada o monto <= 0

        Patrones:
            - Validación de monto positivo
            - Lock de Sale durante registro
            - Permitir sobrepagos (decisión de negocio)
        """
        sale = Sale.objects.select_for_update().get(pk=sale_id)

        if sale.status != Sale.PENDING:
            raise ValidationError("No se pueden agregar pagos a venta completada")

        if amount <= 0:
            raise ValidationError("El monto debe ser mayor a cero")

        payment_method = PaymentMethod.objects.get(pk=payment_method_id)

        return Transaction.objects.create(
            sale=sale,
            payment_method=payment_method,
            amount=amount,
            created_by=user
        )
