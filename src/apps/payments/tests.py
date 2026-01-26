"""
Tests para el módulo de pagos.

Cubre:
    - Cálculo de intereses
    - Validación de datos de pago
    - Creación de transacciones
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import PaymentMethod, Transaction
from .services import PaymentService
from sale.models import Sale, SaleLineItem

User = get_user_model()


class InterestCalculationTests(TestCase):
    """
    Tests para cálculo de intereses.
    """

    def test_no_interest_single_installment(self):
        """
        Sin interés cuando hay 1 cuota.
        """
        amount = Decimal('10000.00')
        total = PaymentService.calculate_interest(
            amount=amount,
            installments=1,
            interest_rate=Decimal('5.00')
        )
        self.assertEqual(total, amount)

    def test_no_interest_zero_rate(self):
        """
        Sin interés cuando tasa es 0%.
        """
        amount = Decimal('10000.00')
        total = PaymentService.calculate_interest(
            amount=amount,
            installments=6,
            interest_rate=Decimal('0.00')
        )
        self.assertEqual(total, amount)

    def test_compound_interest_calculation(self):
        """
        Cálculo correcto de interés compuesto.

        Fórmula: Total = Amount * (1 + rate/100)^installments
        Ejemplo: 100,000 * (1.05)^6 = 134,009.56
        """
        amount = Decimal('100000.00')
        total = PaymentService.calculate_interest(
            amount=amount,
            installments=6,
            interest_rate=Decimal('5.00')
        )

        # Verificar que el resultado está cerca del esperado
        # (1.05^6 = 1.340095640625)
        expected = Decimal('134009.56')
        self.assertEqual(total, expected)

    def test_interest_with_3_installments(self):
        """
        Cálculo con 3 cuotas.
        """
        amount = Decimal('50000.00')
        total = PaymentService.calculate_interest(
            amount=amount,
            installments=3,
            interest_rate=Decimal('3.50')
        )

        # (1.035^3 = 1.108717875)
        expected = Decimal('55435.89')
        self.assertEqual(total, expected)


class PaymentValidationTests(TestCase):
    """
    Tests para validación de datos de pago.
    """

    def setUp(self):
        """
        Configuración inicial para tests.
        """
        self.cash_method = PaymentMethod.objects.create(
            name='Efectivo',
            method_type=PaymentMethod.CASH,
            is_active=True
        )
        self.credit_method = PaymentMethod.objects.create(
            name='Tarjeta de Crédito',
            method_type=PaymentMethod.CREDIT_CARD,
            is_active=True
        )
        self.debit_method = PaymentMethod.objects.create(
            name='Tarjeta de Débito',
            method_type=PaymentMethod.DEBIT_CARD,
            is_active=True
        )

    def test_validate_positive_amount(self):
        """
        Monto debe ser positivo.
        """
        with self.assertRaises(ValidationError) as ctx:
            PaymentService.validate_payment_data(
                payment_method=self.cash_method,
                amount=Decimal('0.00')
            )
        self.assertIn('amount', str(ctx.exception))

    def test_validate_negative_amount(self):
        """
        Monto negativo debe fallar.
        """
        with self.assertRaises(ValidationError):
            PaymentService.validate_payment_data(
                payment_method=self.cash_method,
                amount=Decimal('-100.00')
            )

    def test_validate_card_type_required_for_credit(self):
        """
        Tipo de tarjeta requerido para tarjeta de crédito.
        """
        with self.assertRaises(ValidationError) as ctx:
            PaymentService.validate_payment_data(
                payment_method=self.credit_method,
                amount=Decimal('1000.00'),
                card_type=None
            )
        self.assertIn('card_type', str(ctx.exception))

    def test_validate_card_type_required_for_debit(self):
        """
        Tipo de tarjeta requerido para tarjeta de débito.
        """
        with self.assertRaises(ValidationError) as ctx:
            PaymentService.validate_payment_data(
                payment_method=self.debit_method,
                amount=Decimal('1000.00'),
                card_type=None
            )
        self.assertIn('card_type', str(ctx.exception))

    def test_validate_card_type_not_required_for_cash(self):
        """
        Tipo de tarjeta no requerido para efectivo.
        """
        # No debe lanzar excepción
        PaymentService.validate_payment_data(
            payment_method=self.cash_method,
            amount=Decimal('1000.00'),
            card_type=None
        )

    def test_validate_minimum_installments(self):
        """
        Cuotas deben ser al menos 1.
        """
        with self.assertRaises(ValidationError) as ctx:
            PaymentService.validate_payment_data(
                payment_method=self.credit_method,
                amount=Decimal('1000.00'),
                card_type='VISA',
                installments=0
            )
        self.assertIn('installments', str(ctx.exception))

    def test_validate_negative_interest_rate(self):
        """
        Tasa de interés no puede ser negativa.
        """
        with self.assertRaises(ValidationError) as ctx:
            PaymentService.validate_payment_data(
                payment_method=self.credit_method,
                amount=Decimal('1000.00'),
                card_type='VISA',
                interest_rate=Decimal('-5.00')
            )
        self.assertIn('interest_rate', str(ctx.exception))


class TransactionCreationTests(TestCase):
    """
    Tests para creación de transacciones.
    """

    def setUp(self):
        """
        Configuración inicial para tests.
        """
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        self.cash_method = PaymentMethod.objects.create(
            name='Efectivo',
            method_type=PaymentMethod.CASH,
            is_active=True
        )

        self.credit_method = PaymentMethod.objects.create(
            name='Tarjeta de Crédito',
            method_type=PaymentMethod.CREDIT_CARD,
            is_active=True
        )

        # Crear una venta pendiente
        self.sale = Sale.objects.create(
            status=Sale.PENDING,
            created_by=self.user
        )

        # Agregar line items para que la venta tenga un total
        # Total: (2 * 10000) + (3 * 10000) = 50,000
        SaleLineItem.objects.create(
            sale=self.sale,
            product_name='Producto Test 1',
            sku='TEST001',
            quantity=Decimal('2.000'),
            unit_price=Decimal('10000.00'),
            discount_amount=Decimal('0.00')
        )
        SaleLineItem.objects.create(
            sale=self.sale,
            product_name='Producto Test 2',
            sku='TEST002',
            quantity=Decimal('3.000'),
            unit_price=Decimal('10000.00'),
            discount_amount=Decimal('0.00')
        )

    def test_create_cash_payment(self):
        """
        Crear pago en efectivo simple.
        """
        transaction = PaymentService.add_payment(
            sale_id=self.sale.id,
            payment_method_id=self.cash_method.id,
            amount=Decimal('10000.00'),
            user=self.user
        )

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('10000.00'))
        self.assertEqual(transaction.total_amount, Decimal('10000.00'))
        self.assertEqual(transaction.installments, 1)
        self.assertEqual(transaction.interest_rate, Decimal('0.00'))
        self.assertIsNone(transaction.card_type)

    def test_create_credit_payment_with_installments(self):
        """
        Crear pago con tarjeta de crédito en cuotas.
        """
        transaction = PaymentService.add_payment(
            sale_id=self.sale.id,
            payment_method_id=self.credit_method.id,
            amount=Decimal('30000.00'),
            user=self.user,
            card_type='VISA',
            installments=6,
            interest_rate=Decimal('5.00')
        )

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('30000.00'))
        self.assertEqual(transaction.card_type, 'VISA')
        self.assertEqual(transaction.installments, 6)
        self.assertEqual(transaction.interest_rate, Decimal('5.00'))

        # Verificar cálculo de interés
        # 30,000 * (1.05^6) = 40,202.87
        expected_total = Decimal('40202.87')
        self.assertEqual(transaction.total_amount, expected_total)

    def test_cannot_add_payment_to_completed_sale(self):
        """
        No se puede agregar pago a venta completada.
        """
        self.sale.status = Sale.COMPLETED
        self.sale.save()

        with self.assertRaises(ValidationError) as ctx:
            PaymentService.add_payment(
                sale_id=self.sale.id,
                payment_method_id=self.cash_method.id,
                amount=Decimal('10000.00'),
                user=self.user
            )

        self.assertIn('completada', str(ctx.exception))

    def test_transaction_belongs_to_sale(self):
        """
        Transacción se asocia correctamente a la venta.
        """
        transaction = PaymentService.add_payment(
            sale_id=self.sale.id,
            payment_method_id=self.cash_method.id,
            amount=Decimal('10000.00'),
            user=self.user
        )

        self.assertEqual(transaction.sale, self.sale)
        self.assertIn(transaction, self.sale.transactions.all())
