# Integración django-afip - Emisión de Comprobantes Fiscales

## 📋 Descripción General

Integración completa con AFIP (Administración Federal de Ingresos Públicos) para emisión de comprobantes electrónicos (Facturas A/B/C) con CAE (Código de Autorización Electrónico), generación de PDF y envío automático por email.

**Características principales:**
- ✅ Determinación automática de tipo de comprobante según normativa ARCA
- ✅ Cálculo de IVA discriminado (Factura A) o incluido (Factura B/C)
- ✅ Emisión de CAE (modo DEBUG simulado / PRODUCTION real)
- ✅ Generación de PDF con ReportLab
- ✅ Envío automático por email con PDF adjunto
- ✅ Modo DEBUG para desarrollo sin certificados AFIP

---

## 🏗️ Arquitectura de Integración

### Diseño de Capas

```
┌─────────────────────────────────────┐
│   Frontend (POS)                    │
│   templates/sale/pos_index.html     │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   CAPA DE NEGOCIO (Local)           │
│                                     │
│   Invoice (modelo local)            │
│   InvoiceService (orquestador)      │
│   VATAliquot (alícuotas IVA)        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   CAPA AFIP (django-afip)           │
│                                     │
│   Receipt (comprobante AFIP)        │
│   ReceiptValidation (CAE)           │
│   TaxPayer, PointOfSales            │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   AFIP Web Services (WSFE)          │
└─────────────────────────────────────┘
```

### Principios de Diseño

1. **Separación de Responsabilidades**:
   - **Modelos Locales**: Gestión interna (historial inmutable)
   - **Modelos AFIP**: Solo comunicación con AFIP

2. **Desnormalización Intencional**:
   - Datos críticos (CAE, cliente, montos) se copian a modelos locales
   - Garantiza historial incluso si AFIP falla

3. **Loose Coupling**:
   - `Invoice.afip_receipt` usa `SET_NULL` (no `CASCADE`)
   - Si django-afip se elimina, historial local persiste

---

## 📊 Modelos de Datos

### Invoice (Modelo Local)

```python
class Invoice(models.Model):
    # Relaciones
    sale = OneToOneField(Sale)
    afip_receipt = OneToOneField('django_afip.Receipt',
                                  null=True, on_delete=SET_NULL)

    # Tipo y estado
    receipt_type = CharField(choices=ReceiptType.choices)  # A, B, C
    status = CharField(choices=InvoiceStatus.choices)

    # Datos del cliente (desnormalizados para historial)
    customer_name = CharField(max_length=200)
    customer_tax_id = CharField(max_length=20)
    customer_tax_category = CharField(max_length=2)

    # Montos fiscales
    net_taxed = DecimalField()      # Base imponible (sin IVA)
    vat_amount = DecimalField()     # IVA discriminado
    net_untaxed = DecimalField()    # Monto no gravado
    total_amount = DecimalField()   # Total final

    # CAE (copiado desde AFIP)
    cae = CharField(max_length=14)
    cae_expiration = DateField()

    # Metadata
    notes = TextField()             # Observaciones/errores
    created_at = DateTimeField()
    authorized_at = DateTimeField()
```

**Estados de Invoice:**
- `DRAFT` - Creada, pendiente de validar
- `PENDING` - Enviada a AFIP, esperando respuesta
- `AUTHORIZED` - CAE obtenido exitosamente
- `REJECTED` - AFIP rechazó el comprobante

### VATAliquot (Alícuotas de IVA)

```python
class VATAliquot(models.Model):
    invoice = ForeignKey(Invoice)
    vat_rate = DecimalField()       # 21.00, 10.50, etc.
    base_amount = DecimalField()    # Neto sin IVA
    vat_amount = DecimalField()     # Monto de IVA
```

**Uso**: Solo para **Factura A** (IVA discriminado). Permite agrupar productos con diferentes tasas de IVA.

### ReceiptType (Tipos de Comprobante)

```python
class ReceiptType(models.TextChoices):
    FACTURA_A = 'A', 'Factura A'
    FACTURA_B = 'B', 'Factura B'
    FACTURA_C = 'C', 'Factura C'
```

---

## 🔄 Flujo de Facturación Completo

### 1. Finalizar Venta
```python
# POS Frontend → SaleService
sale = SaleService.finalize_sale(sale_id, user)
# Sale.status = COMPLETED
```

### 2. Procesar Facturación (Orquestador)
```python
# POS Frontend → InvoiceService
result = InvoiceService.procesar_venta_afip(sale_id, user)
```

**Este método orquesta 4 pasos:**

#### Paso 1: Crear Invoice Local
```python
invoice = InvoiceService.create_invoice_from_sale(sale_id, user)
```
- Determina tipo de comprobante (A/B/C)
- Calcula impuestos según tipo
- Desnormaliza datos del cliente
- Crea VATAliquot si es Factura A
- Estado: `DRAFT`

#### Paso 2: Emitir CAE
```python
invoice = InvoiceService.emit_cae(invoice_id)
```

**Modo DEBUG** (`AFIP_DEBUG_MODE=True`):
```python
# Genera CAE simulado
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
invoice.cae = f"SIM{timestamp}"  # SIM20260125123456
invoice.cae_expiration = today + timedelta(days=10)
invoice.status = AUTHORIZED
```

**Modo PRODUCTION** (`AFIP_DEBUG_MODE=False`):
```python
# 1. Crear Receipt en django-afip
receipt = Receipt.objects.create(
    point_of_sales=pos,
    receipt_type=afip_receipt_type,
    total_amount=invoice.total_amount,
    # ...
)

# 2. Validar con AFIP (llama WSFE)
validation = receipt.validate()

# 3. Copiar CAE a Invoice local
if validation.result == 'A':  # Aprobado
    invoice.cae = validation.cae
    invoice.cae_expiration = validation.cae_expiration
    invoice.status = AUTHORIZED
    invoice.afip_receipt = receipt
else:  # Rechazado
    invoice.status = REJECTED
    invoice.notes = validation.observations
```

#### Paso 3: Generar PDF
```python
pdf_buffer = InvoiceService.generate_pdf(invoice)
```

**Modo DEBUG**: PDF básico con ReportLab
**Modo PRODUCTION**: `invoice.afip_receipt.as_pdf()` (PDF oficial AFIP)

#### Paso 4: Enviar Email
```python
InvoiceService.send_invoice_email(invoice, pdf_buffer)
```

- Valida que cliente tenga email
- Adjunta PDF
- Envía via SMTP configurado (o console en DEBUG)

**⚠️ CRÍTICO**: Si el email falla después de obtener CAE:
- El CAE ya está autorizado en AFIP (NO se puede deshacer)
- Sistema loguea advertencia
- Retorna `email_sent=False` pero `success=True`

### Respuesta del Orquestador

```python
{
    'success': True,
    'invoice': Invoice instance,
    'invoice_id': 42,
    'receipt_type': 'Factura B',
    'cae': '12345678901234',
    'cae_expiration': '2026-02-05',
    'display_number': '0001-00000042',
    'total_amount': '2450.00',
    'email_sent': True
}
```

---

## 🧮 Lógica de Negocio - Determinación de Comprobante

### Matriz de Decisión ARCA

```
Emisor        Cliente         Comprobante
─────────────────────────────────────────
RI            RI              Factura A
RI            MT/CF/EX        Factura B
MT/CF/EX      Cualquiera      Factura C
Sin cliente   -               Ticket (Factura C)
```

**Categorías fiscales:**
- **RI**: Responsable Inscripto
- **MT**: Monotributo
- **CF**: Consumidor Final
- **EX**: Exento

### Implementación

```python
@staticmethod
def determine_receipt_type(
    issuer_tax_category: str,
    customer_tax_category: str
) -> str:
    """
    Determina tipo de comprobante según normativa ARCA.

    Returns: 'A', 'B', o 'C'
    """
    if issuer_tax_category == TaxCategory.RESPONSABLE_INSCRIPTO:
        if customer_tax_category == TaxCategory.RESPONSABLE_INSCRIPTO:
            return ReceiptType.FACTURA_A
        else:
            return ReceiptType.FACTURA_B
    else:
        return ReceiptType.FACTURA_C
```

---

## 💰 Cálculo de Impuestos

### Factura A (IVA Discriminado)

**Cliente ve:**
```
Neto Gravado:     $ 826.45
IVA 21%:          $ 173.55
───────────────────────────
Total:            $1000.00
```

**Fórmulas:**
```python
# Por cada line item
item_total = (quantity × unit_price) - discount_amount
base_amount = item_total / (1 + vat_rate/100)
vat_amount = base_amount × (vat_rate/100)
```

**Agregación por alícuota:**
```python
vat_aliquots = InvoiceService.calculate_vat_aliquots_from_line_items(sale)

# Ejemplo con múltiples tasas:
{
    '21.00': {
        'base_amount': Decimal('1239.67'),  # Items con IVA 21%
        'vat_amount': Decimal('260.33')
    },
    '10.50': {
        'base_amount': Decimal('90.50'),    # Items con IVA 10.5%
        'vat_amount': Decimal('9.50')
    }
}

# Se crean múltiples VATAliquot en Invoice
```

### Factura B/C (IVA Incluido)

**Cliente ve:**
```
Total:            $1000.00
```

**Cálculo:**
```python
invoice.net_untaxed = total_amount
invoice.net_taxed = Decimal('0.00')
invoice.vat_amount = Decimal('0.00')
invoice.total_amount = total_amount
```

No se discrimina el IVA, está incluido en el precio.

---

## 🗺️ Mapeo: Sistema Local ↔️ django-afip

### Datos que se Envían a AFIP

| Sistema Local | django-afip Receipt | Descripción |
|--------------|---------------------|-------------|
| `invoice.receipt_type` | `receipt.receipt_type` | Código AFIP: A='1', B='6', C='11' |
| `invoice.total_amount` | `receipt.total_amount` | Monto total |
| `invoice.net_taxed` | `receipt.net_taxed` | Base imponible (Factura A) |
| `invoice.vat_amount` | `receipt.vat_amount` | Monto IVA (Factura A) |
| `invoice.net_untaxed` | `receipt.net_untaxed` | Monto no gravado (Factura B/C) |
| `customer.tax_id` | `receipt.document_number` | CUIT/DNI del cliente |
| `VATAliquot` | `Vat` | Alícuotas de IVA (Factura A) |

### Datos que se Reciben de AFIP

| django-afip ReceiptValidation | Sistema Local Invoice | Descripción |
|-------------------------------|----------------------|-------------|
| `validation.cae` | `invoice.cae` | Código de 14 dígitos |
| `validation.cae_expiration` | `invoice.cae_expiration` | Fecha vencimiento |
| `validation.result` | `invoice.status` | 'A'=AUTHORIZED, 'R'=REJECTED |
| `validation.observations` | `invoice.notes` | Errores/advertencias |

### Datos que NO se Envían a AFIP

- ❌ Detalle de productos (`SaleLineItem`) - Solo totales y alícuotas
- ❌ Nombre del cliente - Solo CUIT/DNI
- ❌ Métodos de pago - AFIP no los requiere
- ❌ Descuentos individuales - Solo total final

---

## ⚙️ Configuración

### 1. Settings Django

```python
# src/core/settings.py

# Modo DEBUG (desarrollo sin certificados AFIP)
AFIP_DEBUG_MODE = True

# Email (desarrollo: console, producción: SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'facturacion@tuempresa.com.ar'

# En producción:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'tu-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'app-password'
```

### 2. Categoría Fiscal del Emisor

```python
# src/apps/invoices/services.py

class InvoiceService:
    # Configurar según tu empresa
    ISSUER_TAX_CATEGORY = TaxCategory.RESPONSABLE_INSCRIPTO
```

### 3. Modo Producción (AFIP Real)

**Requisitos:**
1. Certificados SSL AFIP (`.crt` y `.key`)
2. TaxPayer configurado en Django Admin
3. Puntos de Venta obtenidos de AFIP

**Pasos:**

```bash
# 1. Crear TaxPayer en Django Admin
# URL: /admin/django_afip/taxpayer/
# - Subir certificado .crt
# - Subir clave .key
# - CUIT de la empresa

# 2. Obtener Puntos de Venta desde AFIP
uv run python src/manage.py afip_fetch_points_of_sales

# 3. Desactivar modo DEBUG
# En settings.py:
AFIP_DEBUG_MODE = False
```

---

## 🔌 Endpoints API

### POST `/invoices/process-sale/<sale_id>/`

Orquestador completo: crea Invoice + emite CAE + genera PDF + envía email.

**Request:**
```http
POST /invoices/process-sale/123/
Content-Type: application/json
X-CSRFToken: <token>
```

**Response (Éxito):**
```json
{
  "success": true,
  "invoice_id": 42,
  "receipt_type": "Factura B",
  "cae": "72345678901234",
  "cae_expiration": "2026-02-05",
  "display_number": "0001-00000042",
  "total_amount": "2450.00",
  "email_sent": true
}
```

**Response (Error):**
```json
{
  "success": false,
  "error": "Solo se pueden facturar ventas completadas"
}
```

**Response (Warning - Email falló):**
```json
{
  "success": true,
  "invoice_id": 42,
  "cae": "72345678901234",
  "email_sent": false,
  "error": "Cliente no tiene email registrado"
}
```

---

## 🧪 Testing

### Script de Ejemplo Completo

```bash
cd /home/lean/proyects/billing-system/src
uv run python manage.py shell
```

```python
# Cargar funciones de ejemplo
exec(open('../documentation/example-afip-usage.py').read())

# Ejecutar flujo completo
ejemplo_completo_facturacion()
```

**Output esperado:**
```
✓ Cliente: Juan Pérez
✓ Venta creada: ID 79
✓ Productos agregados con stock
✓ Pago registrado: Efectivo $2450.00
✓ Venta finalizada

📄 FACTURA GENERADA:
   Tipo: Factura B
   Número: 0001-00000004
   CAE: SIM20260125190138
   Total: $2450.00

📧 EMAIL ENVIADO: ✓
```

### Testing Manual (Paso a Paso)

```python
from invoices.services import InvoiceService
from sale.services import SaleService
from customers.models import Customer, TaxCategory

# 1. Crear cliente
customer = Customer.objects.create(
    first_name='Test',
    last_name='User',
    email='test@example.com',
    tax_category=TaxCategory.CONSUMIDOR_FINAL
)

# 2. Crear venta (asumiendo que ya tienes productos y pagos)
sale = SaleService.finalize_sale(sale_id=1, user=request.user)

# 3. Procesar facturación
result = InvoiceService.procesar_venta_afip(sale.id, user)

# 4. Verificar resultado
print(f"Success: {result['success']}")
print(f"CAE: {result['cae']}")
print(f"Email sent: {result['email_sent']}")
```

### Test de Factura A (RI → RI)

```python
# Cliente Responsable Inscripto (genera Factura A)
customer_ri = Customer.objects.create(
    first_name='Empresa',
    last_name='SA',
    email='empresa@example.com',
    tax_id='30-12345678-9',
    tax_category=TaxCategory.RESPONSABLE_INSCRIPTO
)

# Procesar venta
result = InvoiceService.procesar_venta_afip(sale_id, user)

# Verificar tipo
invoice = result['invoice']
assert invoice.receipt_type == 'A'
assert invoice.vat_aliquots.exists()  # Debe tener alícuotas

# Ver alícuotas
for aliquot in invoice.vat_aliquots.all():
    print(f"IVA {aliquot.vat_rate}%: Base ${aliquot.base_amount} - IVA ${aliquot.vat_amount}")
```

---

## 🐛 Debugging: Errores Comunes

### Error: "Solo se pueden facturar ventas completadas"

**Causa**: Sale no está en estado COMPLETED

**Solución:**
```python
from sale.services import SaleService
sale = SaleService.finalize_sale(sale_id, user)
```

### Error: "Esta venta ya tiene una factura asociada"

**Causa**: Ya existe Invoice para esta Sale

**Solución**: Verificar invoice existente o usar otra venta
```python
if hasattr(sale, 'invoice'):
    print(f"Invoice ID: {sale.invoice.id}")
```

### Error: "Cliente no tiene email registrado"

**Causa**: Customer.email vacío

**Solución:**
```python
customer.email = 'cliente@example.com'
customer.save()
```

### Warning: Email no enviado (pero CAE autorizado)

**Comportamiento esperado**: El CAE ya fue registrado en AFIP

**Solución**: Reenviar manualmente
```python
from invoices.services import InvoiceService

invoice = Invoice.objects.get(pk=invoice_id)
pdf_buffer = InvoiceService.generate_pdf(invoice)
InvoiceService.send_invoice_email(invoice, pdf_buffer)
```

---

## 📧 Template de Email

```
Asunto: Su Factura Electrónica Factura B - 0001-00000042

Estimado/a Juan Pérez,

Adjuntamos su comprobante electrónico autorizado por AFIP.

Detalle del comprobante:
- Tipo: Factura B
- Número: 0001-00000042
- CAE: 72345678901234
- Vencimiento CAE: 2026-02-05
- Total: $2.450,00

Este comprobante tiene plena validez legal según normativa AFIP.

Saludos cordiales,
[Nombre de la Empresa]

───────────────────────────
Adjunto: Factura_B_42_72345678901234.pdf
```

---

## 📊 Logs y Monitoreo

### Configuración de Logs

```python
# settings.py
LOGGING = {
    'loggers': {
        'invoices': {
            'handlers': ['console'],
            'level': 'INFO',  # o 'DEBUG' para más detalle
        },
    },
}
```

### Logs Generados

```
INFO invoices - Factura 42 creada - Tipo: B - Total: 2450.00 - Cliente: Juan Pérez
INFO invoices - Emitiendo CAE para factura 42
INFO invoices - CAE simulado emitido para factura 42: SIM20260125190138
INFO invoices - PDF simulado generado para factura 42
INFO invoices - Email enviado exitosamente para factura 42 a juan@example.com
INFO invoices - Proceso AFIP completado para venta 123 - Factura 42 - CAE: SIM20260125190138 - Email enviado: True
```

---

## 🎯 Puntos Clave de la Implementación

### ✅ Características Implementadas

1. **Determinación automática de comprobante** según matriz ARCA
2. **Cálculo de IVA** discriminado (A) o incluido (B/C)
3. **Agregación de alícuotas** por tasa de IVA
4. **Modo DEBUG** para desarrollo sin AFIP
5. **Generación de PDF** con ReportLab
6. **Envío de email** con PDF adjunto
7. **Desnormalización** de datos críticos para historial inmutable
8. **Transacciones atómicas** con rollback en errores
9. **Logging completo** para trazabilidad
10. **Manejo robusto de errores** con diferentes estrategias

### 🔒 Validaciones

**Pre-facturación:**
- ✅ Sale en estado COMPLETED
- ✅ Sale sin factura previa
- ✅ Line items presentes
- ✅ Cliente con email (opcional, warning si falta)

**Cálculo de impuestos:**
- ✅ Agregación matemática correcta por alícuota
- ✅ Redondeo a 2 decimales
- ✅ Validación: `net_taxed + vat_amount == total_amount` (Factura A)

### 🏛️ Normativa ARCA/AFIP

**Tope para Tickets**: ~$190.000 (actualizado periódicamente)
- Por debajo: Ticket sin identificación (Factura C genérica)
- Por encima: Requiere identificación del cliente

**Tipos de comprobante:**
- Factura A: RI → RI (IVA discriminado)
- Factura B: RI → MT/CF/EX (IVA incluido)
- Factura C / Ticket: MT/CF/EX → Cualquiera (IVA incluido)

---

## 🚀 Próximos Pasos Opcionales

1. **Notas de Crédito**: Anulación de facturas
2. **Batch Processing**: Facturar múltiples ventas
3. **Task Queue (Celery)**: Emails asíncronos
4. **Dashboard**: Vista admin de facturas
5. **Reportes Fiscales**: Exportación a ARCA
6. **Validación CUIT**: Consulta en tiempo real con AFIP
7. **QR Code**: Código QR oficial AFIP en PDF

---

## 📚 Referencias

- **Documentación oficial**: https://django-afip.readthedocs.io/
- **AFIP Web Services**: https://www.afip.gob.ar/ws/
- **Normativa ARCA**: https://www.arca.gob.ar/

**Archivos relacionados:**
- `src/apps/invoices/services.py` - Lógica principal
- `src/apps/invoices/models.py` - Modelos locales
- `documentation/example-afip-usage.py` - Scripts de prueba
- `documentation/AFIP-Testing-Guide.md` - Guía de testing completa

---

**Última actualización**: Enero 2026
**Estado**: ✅ 100% Funcional en modo DEBUG / Listo para producción
