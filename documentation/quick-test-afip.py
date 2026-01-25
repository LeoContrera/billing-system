"""
Script de prueba rápida para verificar integración AFIP.

Ejecutar:
    cd /home/lean/proyects/billing-system/src
    uv run python manage.py shell < ../documentation/quick-test-afip.py
"""

print("\n" + "=" * 70)
print("QUICK TEST: Integración AFIP")
print("=" * 70)

# Test 1: Verificar dependencias
print("\n[1/6] Verificando dependencias...")
try:
    import django_afip
    import reportlab
    from decimal import Decimal
    print("✅ django-afip y reportlab instalados correctamente")
except ImportError as e:
    print(f"❌ Error importando dependencias: {e}")
    exit(1)

# Test 2: Verificar modelos
print("\n[2/6] Verificando modelos...")
try:
    from products.models import Product, VATRate
    from customers.models import Customer, TaxCategory
    from sale.models import Sale, SaleLineItem
    from invoices.models import Invoice, InvoiceStatus
    from payments.models import PaymentMethod
    from users.models import User

    # Verificar campos críticos
    product = Product._meta.get_field('vat_rate')
    customer = Customer._meta.get_field('email')
    line_item = SaleLineItem._meta.get_field('vat_rate')

    print("✅ Todos los modelos y campos existen")
except Exception as e:
    print(f"❌ Error en modelos: {e}")
    exit(1)

# Test 3: Verificar configuración
print("\n[3/6] Verificando configuración...")
try:
    from django.conf import settings

    assert hasattr(settings, 'AFIP_DEBUG_MODE'), "AFIP_DEBUG_MODE no configurado"
    assert hasattr(settings, 'DEFAULT_FROM_EMAIL'), "DEFAULT_FROM_EMAIL no configurado"

    print(f"✅ AFIP_DEBUG_MODE = {settings.AFIP_DEBUG_MODE}")
    print(f"✅ EMAIL_BACKEND = {settings.EMAIL_BACKEND}")
    print(f"✅ DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}")
except AssertionError as e:
    print(f"❌ Error en configuración: {e}")
    exit(1)

# Test 4: Verificar datos básicos
print("\n[4/6] Verificando datos básicos...")
try:
    user_count = User.objects.count()
    payment_method_count = PaymentMethod.objects.filter(is_active=True).count()

    if user_count == 0:
        print("⚠️  No hay usuarios. Crear con: python manage.py createsuperuser")
    else:
        print(f"✅ Usuarios encontrados: {user_count}")

    if payment_method_count == 0:
        print("⚠️  No hay métodos de pago. Creando Efectivo...")
        PaymentMethod.objects.create(name='Efectivo', is_active=True)
        print("✅ Método de pago 'Efectivo' creado")
    else:
        print(f"✅ Métodos de pago activos: {payment_method_count}")

except Exception as e:
    print(f"❌ Error verificando datos: {e}")
    exit(1)

# Test 5: Test de servicios
print("\n[5/6] Verificando servicios...")
try:
    from invoices.services import InvoiceService

    # Test de determine_receipt_type
    receipt_type = InvoiceService.determine_receipt_type(
        TaxCategory.RESPONSABLE_INSCRIPTO,
        TaxCategory.CONSUMIDOR_FINAL
    )
    assert receipt_type == 'B', f"Expected 'B', got '{receipt_type}'"
    print("✅ InvoiceService.determine_receipt_type() funciona correctamente")

    # Test de calculate_taxes
    net_taxed, vat_amount, net_untaxed = InvoiceService.calculate_taxes(
        Decimal('121.00'),
        'A'
    )
    expected_net = Decimal('100.00')
    expected_vat = Decimal('21.00')
    assert net_taxed == expected_net, f"Net taxed: Expected {expected_net}, got {net_taxed}"
    assert vat_amount == expected_vat, f"VAT: Expected {expected_vat}, got {vat_amount}"
    print("✅ InvoiceService.calculate_taxes() funciona correctamente")

except Exception as e:
    print(f"❌ Error en servicios: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 6: Resumen
print("\n[6/6] Resumen de estado...")
try:
    invoice_count = Invoice.objects.count()
    sale_count = Sale.objects.count()
    product_count = Product.objects.count()
    customer_count = Customer.objects.count()

    print(f"\n📊 Base de datos:")
    print(f"   - Facturas: {invoice_count}")
    print(f"   - Ventas: {sale_count}")
    print(f"   - Productos: {product_count}")
    print(f"   - Clientes: {customer_count}")

except Exception as e:
    print(f"❌ Error obteniendo resumen: {e}")

# Resultado final
print("\n" + "=" * 70)
print("✅ QUICK TEST COMPLETADO EXITOSAMENTE")
print("=" * 70)
print("\n📖 Próximos pasos:")
print("   1. Ejecutar ejemplo completo:")
print("      exec(open('../documentation/example-afip-usage.py').read())")
print("      ejemplo_completo_facturacion()")
print("\n   2. Ver guía de testing:")
print("      cat ../documentation/AFIP-Testing-Guide.md")
print("\n   3. Ver estado del proyecto:")
print("      cat ../documentation/AFIP-Status-Report.md")
print("\n" + "=" * 70)
