"""
Capa de servicio para procesamiento de pagos.

Este módulo implementa la lógica de negocio para registrar pagos
asociados a ventas, incluyendo cálculo de intereses y validaciones.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from typing import Optional, Dict, Any
from .models import PaymentMethod, Transaction
from sale.models import Sale


class PaymentService:
    """
    Lógica de negocio para procesamiento de pagos.

    Métodos:
        get_active_payment_methods: Obtiene métodos de pago activos
        calculate_interest: Calcula intereses para financiación
        validate_payment_data: Valida datos de pago según método
        add_payment: Registra pago con cálculo automático de intereses
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
    def calculate_interest(
        amount: Decimal,
        installments: int,
        interest_rate: Decimal
    ) -> Decimal:
        """
        Calcula el monto total con interés compuesto.

        Formula: Total = Amount * (1 + rate/100)^installments

        Args:
            amount: Monto base del pago
            installments: Número de cuotas
            interest_rate: Tasa de interés mensual (%)

        Returns:
            Decimal: Monto total con intereses

        Ejemplos:
            >>> PaymentService.calculate_interest(
            ...     amount=Decimal('100000'),
            ...     installments=6,
            ...     interest_rate=Decimal('5.00')
            ... )
            Decimal('134009.56')  # Total con interés compuesto
        """
        if installments <= 1 or interest_rate <= 0:
            return amount

        # Convertir a float para el cálculo de potencia
        amount_float = float(amount)
        rate_decimal = float(interest_rate) / 100

        # Fórmula de interés compuesto: Total = Amount * (1 + rate)^installments
        total_with_interest = amount_float * pow(1 + rate_decimal, installments)

        # Convertir de vuelta a Decimal y redondear a 2 decimales
        return Decimal(str(round(total_with_interest, 2)))

    @staticmethod
    def validate_payment_data(
        payment_method: PaymentMethod,
        amount: Decimal,
        card_type: Optional[str] = None,
        installments: int = 1,
        interest_rate: Decimal = Decimal('0.00')
    ) -> Dict[str, Any]:
        """
        Valida datos de pago según el método seleccionado.

        Args:
            payment_method: Método de pago seleccionado
            amount: Monto base del pago
            card_type: Tipo de tarjeta (requerido para tarjetas)
            installments: Número de cuotas
            interest_rate: Tasa de interés mensual

        Returns:
            Dict con errores de validación (vacío si es válido)

        Raises:
            ValidationError: Si los datos son inválidos

        Validaciones:
            - Monto > 0
            - Card type requerido para tarjetas de débito/crédito
            - Installments >= 1
            - Interest rate >= 0
        """
        errors = {}

        # Validar monto positivo
        if amount <= 0:
            errors['amount'] = "El monto debe ser mayor a cero"

        # Validar tipo de tarjeta para pagos con tarjeta
        if payment_method.method_type in [PaymentMethod.DEBIT_CARD, PaymentMethod.CREDIT_CARD]:
            if not card_type:
                errors['card_type'] = "El tipo de tarjeta es requerido"

        # Validar cuotas
        if installments < 1:
            errors['installments'] = "El número de cuotas debe ser al menos 1"

        # Validar tasa de interés
        if interest_rate < 0:
            errors['interest_rate'] = "La tasa de interés no puede ser negativa"

        if errors:
            raise ValidationError(errors)

        return errors

    @staticmethod
    @transaction.atomic
    def add_payment(
        sale_id: int,
        payment_method_id: int,
        amount: Decimal,
        user,
        card_type: Optional[str] = None,
        installments: int = 1,
        interest_rate: Decimal = Decimal('0.00')
    ) -> Transaction:
        """
        Registra pago con cálculo automático de intereses.

        Args:
            sale_id: ID de la venta
            payment_method_id: ID del método de pago
            amount: Monto base del pago
            user: Usuario que registra el pago
            card_type: Tipo de tarjeta (VISA, Mastercard, etc.)
            installments: Número de cuotas
            interest_rate: Tasa de interés mensual (%)

        Returns:
            Transaction: Transacción de pago creada

        Raises:
            ValidationError: Si venta ya está completada o datos inválidos

        Patrones:
            - Validación completa de datos
            - Cálculo automático de intereses
            - Lock de Sale durante registro
            - Transaction safety con @transaction.atomic

        Uso:
            # Pago en efectivo
            PaymentService.add_payment(
                sale_id=1,
                payment_method_id=1,
                amount=Decimal('10000'),
                user=request.user
            )

            # Pago con tarjeta de crédito en cuotas
            PaymentService.add_payment(
                sale_id=1,
                payment_method_id=3,
                amount=Decimal('50000'),
                user=request.user,
                card_type='VISA',
                installments=6,
                interest_rate=Decimal('5.00')
            )
        """
        # Obtener sale con lock para evitar race conditions
        sale = Sale.objects.select_for_update().get(pk=sale_id)

        if sale.status != Sale.PENDING:
            raise ValidationError("No se pueden agregar pagos a venta completada")

        # Obtener método de pago
        payment_method = PaymentMethod.objects.get(pk=payment_method_id)

        # Validar datos del pago
        PaymentService.validate_payment_data(
            payment_method=payment_method,
            amount=amount,
            card_type=card_type,
            installments=installments,
            interest_rate=interest_rate
        )

        # Calcular monto total con intereses
        total_amount = PaymentService.calculate_interest(
            amount=amount,
            installments=installments,
            interest_rate=interest_rate
        )

        # Crear transacción
        return Transaction.objects.create(
            sale=sale,
            payment_method=payment_method,
            amount=amount,
            card_type=card_type,
            installments=installments,
            interest_rate=interest_rate,
            total_amount=total_amount,
            created_by=user
        )
