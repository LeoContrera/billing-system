# ✅ Checklist de Implementación AFIP

## 📋 Pre-requisitos

### Base de Datos
- [ ] Migraciones aplicadas: `uv run python src/manage.py migrate products`
- [ ] Migraciones aplicadas: `uv run python src/manage.py migrate sale`
- [ ] Verificar campo `Product.vat_rate` existe
- [ ] Verificar campo `SaleLineItem.vat_rate` existe
- [ ] Verificar campo `Customer.email` existe

### Dependencias
- [ ] django-afip instalado: `django_afip` en `INSTALLED_APPS`
- [ ] ReportLab instalado (opcional): `uv add reportlab`

### Configuración
- [ ] `AFIP_DEBUG_MODE` configurado en `settings.py`
- [ ] Email backend configurado en `settings.py`
- [ ] `DEFAULT_FROM_EMAIL` definido
- [ ] Logger `'invoices'` configurado

## 🔧 Configuración Empresa

### Categoría Fiscal
- [ ] Editar `src/apps/invoices/services.py`
- [ ] Verificar: `ISSUER_TAX_CATEGORY = TaxCategory.RESPONSABLE_INSCRIPTO`
- [ ] Cambiar a `MONOTRIBUTO` si corresponde

### AFIP Producción (Solo si vas a producción)
- [ ] Certificados SSL obtenidos de AFIP
- [ ] TaxPayer creado en Django Admin
- [ ] Punto de Venta configurado: `python manage.py afip_fetch_points_of_sales`
- [ ] `AFIP_DEBUG_MODE = False` en producción

### Email Producción (Solo si vas a producción)
- [ ] Crear archivo `.env` con credenciales SMTP
- [ ] Configurar `EMAIL_HOST` (ej: smtp.gmail.com)
- [ ] Configurar `EMAIL_HOST_USER` y `EMAIL_HOST_PASSWORD`
- [ ] Probar envío de email

## 🧪 Testing

### Test 1: Verificar Modelos
```bash
uv run python src/manage.py shell
```

```python
# Verificar Product.vat_rate
from products.models import Product, VATRate
product = Product.objects.first()
print(f"VAT Rate: {product.vat_rate}")  # Debe mostrar: 21.00

# Verificar Customer.email
from customers.models import Customer
customer = Customer.objects.first()
print(f"Email: {customer.email}")  # Debe mostrar email o cadena vacía

# Verificar SaleLineItem.vat_rate
from sale.models import SaleLineItem
item = SaleLineItem.objects.first()
print(f"VAT Rate: {item.vat_rate}")  # Debe mostrar: 21.00 u otra tasa
```

**Resultado esperado:**
- [ ] ✅ Todos los campos existen sin errores

### Test 2: Crear Producto con IVA
```python
from products.models import Product, VATRate
from decimal import Decimal

product = Product.objects.create(
    sku='TEST-001',
    name='Producto de prueba',
    price=Decimal('1000.00'),
    vat_rate=VATRate.VAT_21,  # IVA 21%
    is_active=True
)

print(f"✓ Producto creado: {product.name} - IVA {product.vat_rate}%")
```

**Resultado esperado:**
- [ ] ✅ Producto creado sin errores
- [ ] ✅ Campo `vat_rate` guardado correctamente

### Test 3: Crear Cliente con Email
```python
from customers.models import Customer, TaxCategory

customer = Customer.objects.create(
    first_name='Juan',
    last_name='Pérez',
    email='juan.perez@example.com',  # IMPORTANTE
    tax_category=TaxCategory.CONSUMIDOR_FINAL
)

print(f"✓ Cliente creado: {customer.full_name} - Email: {customer.email}")
```

**Resultado esperado:**
- [ ] ✅ Cliente creado sin errores
- [ ] ✅ Email guardado correctamente

### Test 4: Proceso Completo de Facturación

```python
# Ejecutar script de ejemplo
exec(open('documentation/example-afip-usage.py').read())
ejemplo_completo_facturacion()
```

**Resultado esperado:**
```
============================================================
CREANDO VENTA
============================================================
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

**Verificaciones:**
- [ ] ✅ Venta creada
- [ ] ✅ Productos agregados
- [ ] ✅ Pago registrado
- [ ] ✅ Venta finalizada (COMPLETED)
- [ ] ✅ Invoice creada
- [ ] ✅ CAE emitido (simulado o real)
- [ ] ✅ PDF generado
- [ ] ✅ Email enviado (o impreso en consola)

### Test 5: Verificar Invoice en Base de Datos

```python
from invoices.models import Invoice

invoice = Invoice.objects.select_related('sale').prefetch_related('vat_aliquots').last()

print(f"Invoice ID: {invoice.id}")
print(f"Tipo: {invoice.get_receipt_type_display()}")
print(f"Estado: {invoice.get_status_display()}")
print(f"CAE: {invoice.cae}")
print(f"Total: ${invoice.total_amount}")

if invoice.receipt_type == 'A':
    print("\nAlícuotas de IVA:")
    for aliquot in invoice.vat_aliquots.all():
        print(f"  - IVA {aliquot.vat_rate}%: Base ${aliquot.base_amount} - IVA ${aliquot.vat_amount}")
```

**Resultado esperado:**
- [ ] ✅ Invoice existe en base de datos
- [ ] ✅ Status = AUTHORIZED
- [ ] ✅ CAE no vacío
- [ ] ✅ Total correcto
- [ ] ✅ Si Factura A: alícuotas creadas

### Test 6: API Endpoint

```bash
# Crear venta de prueba y obtener ID
# Reemplazar <sale_id> con ID real

curl -X POST http://localhost:8000/invoices/process-sale/<sale_id>/ \
  -H "Content-Type: application/json" \
  -H "Cookie: sessionid=<tu-session-id>"
```

**Resultado esperado:**
```json
{
  "success": true,
  "invoice_id": 1,
  "receipt_type": "Factura B",
  "cae": "SIM20260125123456",
  "cae_expiration": "2026-02-04",
  "display_number": "0001-00000001",
  "total_amount": "2450.00",
  "email_sent": true
}
```

**Verificaciones:**
- [ ] ✅ Response 200 OK
- [ ] ✅ `success: true`
- [ ] ✅ CAE presente
- [ ] ✅ `email_sent: true` (o `false` con error si falló)

## 🔍 Verificaciones Adicionales

### Logs
- [ ] Verificar logs en consola (logger `'invoices'`)
- [ ] Logs contienen: "Factura X creada", "CAE emitido", "Email enviado"

### Email
- [ ] Si backend es `console`: Email impreso en terminal
- [ ] Si backend es SMTP: Email recibido en buzón
- [ ] PDF adjunto presente
- [ ] Template de email correcto

### Base de Datos
```python
from invoices.models import Invoice

# Contar facturas
count = Invoice.objects.count()
print(f"Total facturas: {count}")

# Últimas facturas
invoices = Invoice.objects.order_by('-created_at')[:5]
for inv in invoices:
    print(f"#{inv.id} - {inv.get_receipt_type_display()} - {inv.get_status_display()}")
```

**Verificaciones:**
- [ ] ✅ Facturas se guardan correctamente
- [ ] ✅ Estados correctos (DRAFT → PENDING → AUTHORIZED)

## 🚨 Troubleshooting

### Error: "No module named 'reportlab'"
```bash
uv add reportlab
```

### Error: "No hay TaxPayer configurado"
- Solo aplica en modo PRODUCTION (`AFIP_DEBUG_MODE=False`)
- En DEBUG: Ignorar este error

### Error: "Cliente no tiene email registrado"
```python
from customers.models import Customer
customer = Customer.objects.get(pk=1)
customer.email = 'cliente@example.com'
customer.save()
```

### Error: "AFIP rechazó el comprobante"
- Verificar certificados SSL vigentes
- Verificar CUIT de cliente válido
- Revisar `invoice.notes` para detalles

### Email no enviado pero CAE autorizado
- **Comportamiento normal**: CAE ya fue registrado en AFIP
- Ver sección "Reintento de Email" en documentación
- Reenviar manualmente si es necesario

## ✅ Checklist Final de Go-Live

### Pre-Producción
- [ ] Todos los tests pasaron sin errores
- [ ] Email de prueba enviado y recibido
- [ ] PDF generado y visualizado correctamente
- [ ] Logs revisados sin errores críticos

### Producción (Solo cuando sea necesario)
- [ ] Certificados AFIP válidos y vigentes
- [ ] TaxPayer configurado en Django Admin
- [ ] Puntos de Venta sincronizados
- [ ] `AFIP_DEBUG_MODE = False`
- [ ] Email SMTP configurado con credenciales de producción
- [ ] Backup de base de datos realizado
- [ ] Plan de rollback definido

### Post-Producción
- [ ] Monitoreo de logs activo
- [ ] Primera factura emitida exitosamente
- [ ] Email recibido por cliente
- [ ] CAE verificado en portal AFIP
- [ ] Proceso documentado para equipo

---

## 🎉 ¡Implementación Completa!

Si todos los checkboxes están marcados, la integración AFIP está **100% funcional**.

### Próximos Pasos
1. Integrar en template POS (ver `AFIP-Implementation-Summary.md`)
2. Capacitar equipo en proceso de facturación
3. Configurar monitoreo de errores (opcional)
4. Implementar dashboard de reportes (opcional)

### Soporte
- Ver documentación técnica: `AFIP-Integration-Guide.md`
- Ver ejemplos de código: `example-afip-usage.py`
- Ver resumen ejecutivo: `AFIP-Implementation-Summary.md`

**¿Dudas o problemas?** Revisar sección "🔍 Troubleshooting" en la guía técnica.
