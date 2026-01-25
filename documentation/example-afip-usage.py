"""
Ejemplo de uso completo de la integración AFIP.

Este script demuestra cómo usar el servicio de facturación electrónica
completo, desde la creación de una venta hasta el envío del email con PDF.

NOTA: Este es un script de ejemplo didáctico. Para uso en producción,
ejecutar en el contexto del shell de Django o desde views.
"""

from decimal import Decimal
from django.db import transaction

# Importar servicios
from sale.services import SaleService
from payments.services import PaymentService
from invoices.services import InvoiceService
from customers.models import Customer, TaxCategory
from products.models import Product
from payments.models import PaymentMethod
from users.models import User


def ejemplo_completo_facturacion():
    """
    Ejemplo completo: Crear venta, agregar productos, pagar y facturar.
    """

    # ========================================
    # PASO 1: PREPARACIÓN DE DATOS
    # ========================================

    # Obtener usuario cajero
    user = User.objects.first()
    if not user:
        print("ERROR: No hay usuarios en el sistema")
        return

    # Obtener método de pago
    payment_method = PaymentMethod.objects.filter(is_active=True).first()
    if not payment_method:
        print("ERROR: No hay métodos de pago activos")
        return

    # Crear o obtener cliente con email
    customer, created = Customer.objects.get_or_create(
        tax_id='20-12345678-9',
        defaults={
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan.perez@example.com',  # IMPORTANTE: Email requerido
            'phone': '3512345678',
            'locality': 'Córdoba',
            'address': 'Av. Colón 123',
            'tax_category': TaxCategory.CONSUMIDOR_FINAL
        }
    )

    if created:
        print(f"✓ Cliente creado: {customer.full_name} ({customer.email})")
    else:
        print(f"✓ Cliente existente: {customer.full_name} ({customer.email})")

    # Obtener productos (o crearlos para el ejemplo)
    product1, _ = Product.objects.get_or_create(
        sku='PROD-001',
        defaults={
            'name': 'Producto de prueba 1',
            'description': 'Producto con IVA 21%',
            'price': Decimal('1000.00'),
            'vat_rate': '21.00',  # IVA 21%
            'is_active': True
        }
    )

    product2, _ = Product.objects.get_or_create(
        sku='PROD-002',
        defaults={
            'name': 'Producto de prueba 2',
            'description': 'Producto con IVA 10.5%',
            'price': Decimal('500.00'),
            'vat_rate': '10.50',  # IVA 10.5%
            'is_active': True
        }
    )

    print(f"✓ Productos listos: {product1.name}, {product2.name}")

    # ========================================
    # PASO 2: CREAR VENTA Y AGREGAR PRODUCTOS
    # ========================================

    print("\n" + "=" * 60)
    print("CREANDO VENTA")
    print("=" * 60)

    # Crear nueva venta
    sale = SaleService.create_sale(user)
    print(f"✓ Venta creada: ID {sale.id}")

    # Asignar cliente
    sale = SaleService.set_customer(sale.id, customer.id)
    print(f"✓ Cliente asignado: {customer.full_name}")

    # Agregar productos
    item1 = SaleService.add_line_item(sale.id, product1.sku, Decimal('2'))
    print(f"✓ Producto agregado: {item1.product_name} x{item1.quantity} - ${item1.unit_price} - IVA {item1.vat_rate}%")

    item2 = SaleService.add_line_item(sale.id, product2.sku, Decimal('1'))
    print(f"✓ Producto agregado: {item2.product_name} x{item2.quantity} - ${item2.unit_price} - IVA {item2.vat_rate}%")

    # Aplicar descuento global (opcional)
    discount = Decimal('50.00')
    sale = SaleService.apply_global_discount(sale.id, discount)
    print(f"✓ Descuento global aplicado: ${discount}")

    # Refrescar sale para calcular totales
    from sale.models import Sale
    sale = Sale.objects.prefetch_related('line_items').get(pk=sale.id)

    print(f"\n📊 TOTALES:")
    print(f"   Subtotal: ${sale.subtotal}")
    print(f"   Descuento: ${sale.global_discount_amount}")
    print(f"   TOTAL: ${sale.total}")

    # ========================================
    # PASO 3: REGISTRAR PAGO
    # ========================================

    print("\n" + "=" * 60)
    print("REGISTRANDO PAGO")
    print("=" * 60)

    # Agregar pago por el total
    transaction = PaymentService.add_payment(
        sale_id=sale.id,
        payment_method_id=payment_method.id,
        amount=sale.total,
        user=user
    )
    print(f"✓ Pago registrado: ${transaction.amount} via {transaction.payment_method.name}")

    # Refrescar sale
    sale = Sale.objects.prefetch_related('transactions').get(pk=sale.id)
    print(f"✓ Total pagado: ${sale.total_paid}")
    print(f"✓ Saldo restante: ${sale.remaining_balance}")

    # ========================================
    # PASO 4: FINALIZAR VENTA
    # ========================================

    print("\n" + "=" * 60)
    print("FINALIZANDO VENTA")
    print("=" * 60)

    sale = SaleService.finalize_sale(sale.id, user)
    print(f"✓ Venta finalizada: Estado = {sale.get_status_display()}")
    print(f"✓ Fecha de finalización: {sale.completed_at}")

    # ========================================
    # PASO 5: FACTURACIÓN AFIP (ORQUESTADOR)
    # ========================================

    print("\n" + "=" * 60)
    print("PROCESANDO FACTURACIÓN AFIP")
    print("=" * 60)

    # Llamar al método orquestador completo
    result = InvoiceService.procesar_venta_afip(sale.id, user)

    # Mostrar resultado
    if result['success']:
        print(f"✓ FACTURACIÓN EXITOSA")
        print(f"\n📄 DATOS DEL COMPROBANTE:")
        print(f"   Factura ID: {result['invoice'].id}")
        print(f"   Tipo: {result['invoice'].get_receipt_type_display()}")
        print(f"   Número: {result['display_number']}")
        print(f"   CAE: {result['cae']}")
        print(f"   Vencimiento CAE: {result['invoice'].cae_expiration}")
        print(f"   Total: ${result['invoice'].total_amount}")

        # Detalle de IVA (si es Factura A)
        if result['invoice'].receipt_type == 'A':
            print(f"\n💵 DETALLE FISCAL:")
            print(f"   Neto gravado: ${result['invoice'].net_taxed}")
            print(f"   IVA: ${result['invoice'].vat_amount}")

            # Alícuotas
            vat_aliquots = result['invoice'].vat_aliquots.all()
            if vat_aliquots:
                print(f"\n   Alícuotas de IVA:")
                for aliquot in vat_aliquots:
                    print(f"     - IVA {aliquot.vat_rate}%: Base ${aliquot.base_amount} - IVA ${aliquot.vat_amount}")

        # Email
        print(f"\n📧 EMAIL:")
        if result['email_sent']:
            print(f"   ✓ Email enviado exitosamente a {customer.email}")
        else:
            print(f"   ⚠ Email NO enviado")
            if result.get('error'):
                print(f"   Error: {result['error']}")

    else:
        print(f"✗ ERROR EN FACTURACIÓN")
        print(f"   {result['error']}")

    print("\n" + "=" * 60)
    print("PROCESO COMPLETO")
    print("=" * 60)


def ejemplo_flujo_paso_a_paso():
    """
    Ejemplo del flujo legacy (paso a paso): create_invoice + emit_cae.

    Este flujo sigue siendo útil si necesitas control granular o
    procesar pasos de forma asíncrona.
    """

    print("\n" + "=" * 60)
    print("FLUJO PASO A PASO (LEGACY)")
    print("=" * 60)

    # Asumir que sale_id ya existe y está COMPLETED
    sale_id = 1  # Reemplazar con ID real
    user = User.objects.first()

    try:
        # Paso 1: Crear Invoice
        print("Paso 1: Creando invoice...")
        invoice = InvoiceService.create_invoice_from_sale(sale_id, user)
        print(f"✓ Invoice creada: ID {invoice.id} - Tipo {invoice.get_receipt_type_display()}")

        # Paso 2: Emitir CAE
        print("\nPaso 2: Emitiendo CAE...")
        invoice = InvoiceService.emit_cae(invoice.id)
        print(f"✓ CAE emitido: {invoice.cae}")

        # Paso 3: Generar PDF
        print("\nPaso 3: Generando PDF...")
        pdf_buffer = InvoiceService.generate_pdf(invoice)
        print(f"✓ PDF generado: {len(pdf_buffer.getvalue())} bytes")

        # Paso 4: Enviar email
        print("\nPaso 4: Enviando email...")
        email_sent = InvoiceService.send_invoice_email(invoice, pdf_buffer)
        print(f"✓ Email enviado: {email_sent}")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


def ejemplo_reintentar_envio_email():
    """
    Ejemplo de cómo reenviar email si falló en el proceso inicial.
    """

    print("\n" + "=" * 60)
    print("REINTENTAR ENVÍO DE EMAIL")
    print("=" * 60)

    invoice_id = 1  # Reemplazar con ID real

    try:
        from invoices.models import Invoice

        # Obtener invoice autorizada
        invoice = Invoice.objects.get(pk=invoice_id)

        if not invoice.is_authorized:
            print("✗ Error: Invoice no está autorizada")
            return

        print(f"✓ Invoice autorizada: {invoice.cae}")

        # Generar PDF
        print("Generando PDF...")
        pdf_buffer = InvoiceService.generate_pdf(invoice)
        print(f"✓ PDF generado")

        # Reenviar email
        print("Reenviando email...")
        email_sent = InvoiceService.send_invoice_email(invoice, pdf_buffer)

        if email_sent:
            print(f"✓ Email enviado exitosamente a {invoice.sale.customer.email}")
        else:
            print("✗ Error enviando email")

    except Exception as e:
        print(f"✗ Error: {str(e)}")


def ejemplo_consultar_factura():
    """
    Ejemplo de cómo consultar detalles de una factura.
    """

    print("\n" + "=" * 60)
    print("CONSULTAR FACTURA")
    print("=" * 60)

    invoice_id = 1  # Reemplazar con ID real

    try:
        from invoices.models import Invoice

        # Obtener invoice con relaciones
        invoice = Invoice.objects.select_related('sale', 'sale__customer').prefetch_related('vat_aliquots').get(pk=invoice_id)

        print(f"📄 FACTURA #{invoice.id}")
        print(f"   Tipo: {invoice.get_receipt_type_display()}")
        print(f"   Estado: {invoice.get_status_display()}")
        print(f"   Cliente: {invoice.customer_name}")
        print(f"   CUIT/DNI: {invoice.customer_tax_id or 'N/A'}")
        print(f"   Total: ${invoice.total_amount}")

        if invoice.is_authorized:
            print(f"\n✓ AUTORIZADA")
            print(f"   CAE: {invoice.cae}")
            print(f"   Vencimiento: {invoice.cae_expiration}")
            print(f"   Número: {invoice.display_number}")

            if invoice.receipt_type == 'A':
                print(f"\n💵 DETALLE FISCAL:")
                print(f"   Neto gravado: ${invoice.net_taxed}")
                print(f"   IVA: ${invoice.vat_amount}")
                print(f"\n   Alícuotas:")
                for aliquot in invoice.vat_aliquots.all():
                    print(f"     - IVA {aliquot.vat_rate}%: ${aliquot.vat_amount}")
        else:
            print(f"\n⚠ NO AUTORIZADA")
            print(f"   Notas: {invoice.notes}")

    except Invoice.DoesNotExist:
        print(f"✗ Error: Factura {invoice_id} no encontrada")
    except Exception as e:
        print(f"✗ Error: {str(e)}")


if __name__ == '__main__':
    """
    Para ejecutar estos ejemplos, usar el shell de Django:

    uv run python src/manage.py shell

    Luego:
    >>> exec(open('documentation/example-afip-usage.py').read())
    >>> ejemplo_completo_facturacion()
    """

    print("\n" + "=" * 60)
    print("EJEMPLOS DE USO - INTEGRACIÓN AFIP")
    print("=" * 60)
    print("\nPara ejecutar, usar el shell de Django:")
    print("  uv run python src/manage.py shell")
    print("\nLuego ejecutar:")
    print("  >>> exec(open('documentation/example-afip-usage.py').read())")
    print("  >>> ejemplo_completo_facturacion()")
    print("\nOtros ejemplos disponibles:")
    print("  - ejemplo_flujo_paso_a_paso()")
    print("  - ejemplo_reintentar_envio_email()")
    print("  - ejemplo_consultar_factura()")
    print("\n" + "=" * 60)
