# 🧪 Guía de Testing AFIP - Paso a Paso

## 📖 Índice
1. [Preparación del Entorno](#preparación-del-entorno)
2. [Ejecutar el Script de Ejemplo](#ejecutar-el-script-de-ejemplo)
3. [Interpretar Resultados](#interpretar-resultados)
4. [Debugging: Errores Comunes](#debugging-errores-comunes)
5. [Testing Manual con Shell](#testing-manual-con-shell)

---

## 1. Preparación del Entorno

### Verificar dependencias instaladas
```bash
uv run python -c "import django_afip; import reportlab; print('✓ Dependencias OK')"
```

### Verificar migraciones aplicadas
```bash
cd /home/lean/proyects/billing-system/src
uv run python manage.py migrate
```

### Crear superusuario (si no existe)
```bash
uv run python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: admin123
```

### Crear método de pago (si no existe)
```bash
uv run python manage.py shell
```
```python
from payments.models import PaymentMethod
PaymentMethod.objects.get_or_create(
    name='Efectivo',
    defaults={'is_active': True}
)
exit()
```

---

## 2. Ejecutar el Script de Ejemplo

### Paso 1: Abrir Django Shell
```bash
cd /home/lean/proyects/billing-system/src
uv run python manage.py shell
```

### Paso 2: Cargar el script
```python
exec(open('../documentation/example-afip-usage.py').read())
```

### Paso 3: Ejecutar ejemplo completo
```python
ejemplo_completo_facturacion()
```

### Output Esperado
```
============================================================
CREANDO VENTA
============================================================
✓ Cliente creado: Juan Pérez (juan.perez@example.com)
✓ Productos listos: Producto de prueba 1, Producto de prueba 2
✓ Venta creada: ID 1
✓ Cliente asignado: Juan Pérez
✓ Producto agregado: Producto de prueba 1 x2 - $1000.00 - IVA 21.00%
✓ Producto agregado: Producto de prueba 2 x1 - $500.00 - IVA 10.50%
✓ Descuento global aplicado: $50.00

📊 TOTALES:
   Subtotal: $2500.00
   Descuento: $50.00
   TOTAL: $2450.00

============================================================
REGISTRANDO PAGO
============================================================
✓ Pago registrado: $2450.00 via Efectivo
✓ Total pagado: $2450.00
✓ Saldo restante: $0.00

============================================================
FINALIZANDO VENTA
============================================================
✓ Venta finalizada: Estado = Completada
✓ Fecha de finalización: 2026-01-25 12:34:56

============================================================
PROCESANDO FACTURACIÓN AFIP
============================================================
✓ FACTURACIÓN EXITOSA

📄 DATOS DEL COMPROBANTE:
   Factura ID: 1
   Tipo: Factura B
   Número: Sin autorizar (modo DEBUG: usar display_number simulado)
   CAE: SIM20260125123456
   Vencimiento CAE: 2026-02-04
   Total: $2450.00

📧 EMAIL:
   ✓ Email enviado exitosamente a juan.perez@example.com
   (o mensaje impreso en consola si backend es console)

============================================================
PROCESO COMPLETO
============================================================
```

---

## 3. Interpretar Resultados

### ✅ Resultado Exitoso

**Indicadores de éxito:**
1. ✅ Venta creada con ID único
2. ✅ Status = "Completada"
3. ✅ Invoice creada
4. ✅ CAE emitido (formato: `SIM20260125123456` en DEBUG)
5. ✅ Email enviado o impreso en consola
6. ✅ No hay excepciones ni errores

**Verificación en consola:**
- Deberías ver el email completo impreso con el asunto y cuerpo
- El PDF está adjunto (se menciona en el log)

**Verificación en base de datos:**
```python
from invoices.models import Invoice
invoice = Invoice.objects.last()
print(f"Status: {invoice.get_status_display()}")
print(f"CAE: {invoice.cae}")
print(f"Autorizada: {invoice.is_authorized}")
```

**Expected output:**
```
Status: Autorizada (CAE obtenido)
CAE: SIM20260125123456
Autorizada: True
```

---

### ⚠️ Warnings Esperables (No son errores)

#### Warning 1: "Sin autorizar" en display_number
```
Número: Sin autorizar (modo DEBUG: usar display_number simulado)
```

**Razón:** El campo `afip_receipt` está comentado en el modelo (modo DEBUG).
**Impacto:** Solo afecta el formato del número, el CAE es válido.
**Solución:** En producción se descomentará y mostrará `0001-00000001`.

#### Warning 2: Email impreso en consola
```
Content-Type: text/plain; charset="utf-8"
...
```

**Razón:** EMAIL_BACKEND = 'console' en desarrollo.
**Impacto:** Ninguno, es el comportamiento esperado.
**Solución:** En producción configurar SMTP real.

---

## 4. Debugging: Errores Comunes

### Error 1: No hay usuarios
```
ERROR: No hay usuarios en el sistema
```

**Solución:**
```bash
uv run python manage.py createsuperuser
```

---

### Error 2: No hay métodos de pago
```
ERROR: No hay métodos de pago activos
```

**Solución:**
```python
from payments.models import PaymentMethod
PaymentMethod.objects.create(name='Efectivo', is_active=True)
```

---

### Error 3: "Solo se pueden facturar ventas completadas"
```
ValidationError: Solo se pueden facturar ventas completadas
```

**Razón:** La venta no está en estado COMPLETED.
**Debugging:**
```python
from sale.models import Sale
sale = Sale.objects.get(pk=1)  # Reemplazar con ID de tu venta
print(f"Status: {sale.status}")
print(f"Total pagado: {sale.total_paid}")
print(f"Total: {sale.total}")
print(f"Fully paid: {sale.is_fully_paid}")
```

**Solución:**
```python
from sale.services import SaleService
from users.models import User
user = User.objects.first()
sale = SaleService.finalize_sale(sale.id, user)
```

---

### Error 4: "Esta venta ya tiene una factura asociada"
```
ValidationError: Esta venta ya tiene una factura asociada
```

**Razón:** Ya llamaste `create_invoice_from_sale()` para esta venta.
**Debugging:**
```python
from sale.models import Sale
sale = Sale.objects.get(pk=1)
if hasattr(sale, 'invoice'):
    print(f"Invoice ID: {sale.invoice.id}")
    print(f"CAE: {sale.invoice.cae}")
```

**Solución:** Usar otra venta o reintentar con `ejemplo_completo_facturacion()` que crea una nueva.

---

### Error 5: "El cliente no tiene email registrado"
```
ValidationError: El cliente no tiene email registrado
```

**Razón:** El Customer no tiene email.
**Debugging:**
```python
from customers.models import Customer
customer = Customer.objects.get(pk=1)
print(f"Email: {customer.email}")  # Debería estar vacío
```

**Solución:**
```python
customer.email = 'cliente@example.com'
customer.save()
```

---

### Error 6: ImportError de ReportLab
```
ValidationError: ReportLab no instalado
```

**Solución:**
```bash
uv add reportlab
```

---

### Error 7: Product sin vat_rate
```
AttributeError: 'Product' object has no attribute 'vat_rate'
```

**Razón:** Migraciones no aplicadas.
**Solución:**
```bash
uv run python manage.py migrate products
```

---

## 5. Testing Manual con Shell

### Test A: Verificar campos de modelos
```python
from products.models import Product, VATRate
from customers.models import Customer
from sale.models import SaleLineItem

# Crear producto de prueba
product = Product.objects.create(
    sku='TEST-001',
    name='Test Product',
    price='1000.00',
    vat_rate=VATRate.VAT_21
)
print(f"✓ Product.vat_rate: {product.vat_rate}")

# Crear cliente de prueba
customer = Customer.objects.create(
    first_name='Test',
    last_name='Customer',
    email='test@example.com'
)
print(f"✓ Customer.email: {customer.email}")
```

### Test B: Consultar factura existente
```python
from invoices.models import Invoice

# Última factura creada
invoice = Invoice.objects.select_related('sale').last()

if invoice:
    print(f"Invoice ID: {invoice.id}")
    print(f"Tipo: {invoice.get_receipt_type_display()}")
    print(f"Status: {invoice.get_status_display()}")
    print(f"Cliente: {invoice.customer_name}")
    print(f"Total: ${invoice.total_amount}")
    print(f"CAE: {invoice.cae}")
    print(f"Vencimiento: {invoice.cae_expiration}")

    # Si es Factura A, mostrar alícuotas
    if invoice.receipt_type == 'A':
        print("\nAlícuotas de IVA:")
        for aliquot in invoice.vat_aliquots.all():
            print(f"  - IVA {aliquot.vat_rate}%: Base ${aliquot.base_amount} - IVA ${aliquot.vat_amount}")
else:
    print("No hay facturas en la base de datos")
```

### Test C: Reintentar envío de email
```python
from invoices.models import Invoice
from invoices.services import InvoiceService

invoice = Invoice.objects.get(pk=1)  # Reemplazar con ID real

if invoice.is_authorized:
    # Generar PDF
    pdf_buffer = InvoiceService.generate_pdf(invoice)

    # Reenviar email
    try:
        InvoiceService.send_invoice_email(invoice, pdf_buffer)
        print("✓ Email reenviado exitosamente")
    except Exception as e:
        print(f"✗ Error: {e}")
else:
    print("Invoice no está autorizada")
```

### Test D: Crear Factura A (RI → RI)
```python
from customers.models import Customer, TaxCategory
from sale.services import SaleService
from payments.services import PaymentService
from invoices.services import InvoiceService
from products.models import Product
from payments.models import PaymentMethod
from users.models import User
from decimal import Decimal

# Cliente Responsable Inscripto
customer = Customer.objects.create(
    first_name='Empresa',
    last_name='SA',
    email='empresa@example.com',
    tax_id='30-12345678-9',
    tax_category=TaxCategory.RESPONSABLE_INSCRIPTO  # Clave para Factura A
)

# Crear venta
user = User.objects.first()
sale = SaleService.create_sale(user)
sale = SaleService.set_customer(sale.id, customer.id)

# Agregar productos
product = Product.objects.first()
SaleService.add_line_item(sale.id, product.sku, Decimal('1'))

# Pagar
payment_method = PaymentMethod.objects.first()
sale = Sale.objects.prefetch_related('line_items').get(pk=sale.id)
PaymentService.add_payment(sale.id, payment_method.id, sale.total, user)

# Finalizar
sale = SaleService.finalize_sale(sale.id, user)

# Facturar
result = InvoiceService.procesar_venta_afip(sale.id, user)

# Verificar que es Factura A
invoice = result['invoice']
print(f"Tipo: {invoice.get_receipt_type_display()}")  # Debe ser "Factura A"
print(f"Net Taxed: ${invoice.net_taxed}")
print(f"VAT Amount: ${invoice.vat_amount}")
print(f"Total: ${invoice.total_amount}")

# Verificar alícuotas
for aliquot in invoice.vat_aliquots.all():
    print(f"Alícuota IVA {aliquot.vat_rate}%: Base ${aliquot.base_amount} - IVA ${aliquot.vat_amount}")
```

---

## 6. Verificar Logs

### Ver logs en tiempo real
Los logs se imprimen en la consola donde ejecutas el shell. Busca:

```
INFO invoices - Factura X creada - Tipo: B - Total: 2450.00 - Cliente: Juan Pérez
INFO invoices - CAE simulado emitido para factura X: SIM20260125123456
INFO invoices - PDF simulado generado para factura X
INFO invoices - Email enviado exitosamente para factura X a juan.perez@example.com
INFO invoices - Proceso AFIP completado para venta X - Factura X - CAE: SIM20260125123456 - Email enviado: True
```

### Nivel de detalle
- **INFO**: Operaciones normales
- **WARNING**: Email no enviado (pero CAE autorizado)
- **ERROR**: Fallos críticos en emisión de CAE

---

## 7. Cleanup (Limpiar datos de prueba)

Si quieres resetear la base de datos:

```bash
# CUIDADO: Esto borra TODOS los datos
cd /home/lean/proyects/billing-system/src
rm db.sqlite3
uv run python manage.py migrate
uv run python manage.py createsuperuser
```

O borrar solo facturas de prueba:

```python
from invoices.models import Invoice
Invoice.objects.all().delete()

from sale.models import Sale
Sale.objects.all().delete()
```

---

## 8. Próximos Pasos

1. ✅ Ejecutar `ejemplo_completo_facturacion()` exitosamente
2. Probar diferentes escenarios:
   - Factura A (RI → RI)
   - Factura B (RI → CF)
   - Productos con diferentes IVA (21%, 10.5%)
   - Descuentos globales y unitarios
3. Verificar cálculos de IVA en Factura A
4. Probar reintentos de email
5. Integrar en template POS (siguiente fase)

---

## 📞 Soporte

**Documentación relacionada:**
- `AFIP-Integration-Guide.md` - Guía técnica completa
- `AFIP-Checklist.md` - Checklist de implementación
- `AFIP-Status-Report.md` - Estado actual del proyecto
- `example-afip-usage.py` - Scripts de ejemplo

**Errores comunes resueltos:** Ver sección 4 de este documento.

---

¡Buena suerte con el testing! 🚀
