# Guía de Integración AFIP - Facturación Electrónica

Esta guía documenta la integración completa con AFIP para emisión de facturas electrónicas, generación de PDF y envío automático por email.

## 📋 Tabla de Contenidos

1. [Arquitectura](#arquitectura)
2. [Modelos de Datos](#modelos-de-datos)
3. [Service Layer](#service-layer)
4. [Flujo de Facturación](#flujo-de-facturación)
5. [Configuración](#configuración)
6. [Uso](#uso)
7. [Testing](#testing)

## 🏗️ Arquitectura

### Componentes Principales

```
┌─────────────┐
│   Sale      │ 1:1 relación
│  (Venta)    ├──────────┐
└─────────────┘          │
                         ▼
                   ┌──────────────┐
                   │   Invoice    │ 1:1 relación (opcional)
                   │  (Factura)   ├──────────────────┐
                   └──────────────┘                  │
                         │                           ▼
                         │ 1:N                 ┌────────────────┐
                         ▼                     │ django_afip    │
                   ┌──────────────┐            │   Receipt      │
                   │ VATAliquot   │            └────────────────┘
                   │ (Alícuota)   │
                   └──────────────┘
```

### Patrones Aplicados

- **Service Layer Pattern**: Toda la lógica de negocio en `InvoiceService`
- **Transaction Safety**: `@transaction.atomic` garantiza consistencia
- **Factory Method**: Creación de facturas encapsulada
- **Strategy Pattern**: Modo DEBUG vs PRODUCTION para AFIP
- **Error Handling**: Manejo robusto de errores AFIP y email

## 📊 Modelos de Datos

### Product

```python
class Product(models.Model):
    sku = CharField(max_length=50, unique=True)
    name = CharField(max_length=200)
    price = DecimalField(max_digits=10, decimal_places=2)
    vat_rate = CharField(
        max_length=5,
        choices=VATRate.choices,
        default=VATRate.VAT_21  # 21.00%
    )
```

**Tasas de IVA disponibles:**
- `21.00%` - IVA General (default)
- `10.50%` - IVA Reducido
- `27.00%` - IVA Incrementado
- `5.00%` - IVA Mínimo
- `2.50%` - IVA Muy Reducido
- `0.00%` - Exento

### SaleLineItem

```python
class SaleLineItem(models.Model):
    sale = ForeignKey(Sale)
    product = ForeignKey(Product)
    quantity = DecimalField(max_digits=10, decimal_places=3)
    unit_price = DecimalField(max_digits=10, decimal_places=2)
    discount_amount = DecimalField(max_digits=10, decimal_places=2)
    vat_rate = CharField(max_length=5)  # Desnormalizado para historial
```

**Desnormalización**: El campo `vat_rate` se copia desde `Product` al crear el line item para mantener un historial fiscal inmutable.

### Invoice

```python
class Invoice(models.Model):
    sale = OneToOneField(Sale)
    receipt_type = CharField(choices=ReceiptType.choices)  # A, B, C
    status = CharField(choices=InvoiceStatus.choices)

    # Datos del cliente (desnormalizados)
    customer_name = CharField(max_length=200)
    customer_tax_id = CharField(max_length=20)
    customer_tax_category = CharField(max_length=2)

    # Montos fiscales
    net_taxed = DecimalField()      # Base imponible (sin IVA)
    vat_amount = DecimalField()     # IVA discriminado
    net_untaxed = DecimalField()    # Monto no gravado
    total_amount = DecimalField()   # Total final

    # CAE (Código de Autorización Electrónico)
    cae = CharField(max_length=14)
    cae_expiration = DateField()
```

### VATAliquot

```python
class VATAliquot(models.Model):
    invoice = ForeignKey(Invoice)
    vat_rate = DecimalField(max_digits=5, decimal_places=2)  # 21.00
    base_amount = DecimalField(max_digits=10, decimal_places=2)
    vat_amount = DecimalField(max_digits=10, decimal_places=2)
```

**Uso**: Una Invoice de tipo Factura A puede tener múltiples alícuotas (ej: productos con 21% y otros con 10.5%).

## 🔧 Service Layer

### InvoiceService - Métodos Principales

#### 1. `determine_receipt_type(issuer_tax_category, customer_tax_category)`

Determina el tipo de comprobante según matriz ARCA.

**Matriz de decisión:**

| Emisor      | Cliente     | Comprobante |
|-------------|-------------|-------------|
| RI          | RI          | Factura A   |
| RI          | MT/CF/EX    | Factura B   |
| MT/CF/EX    | Cualquiera  | Factura C   |

**Ejemplo:**
```python
receipt_type = InvoiceService.determine_receipt_type(
    TaxCategory.RESPONSABLE_INSCRIPTO,  # Emisor RI
    TaxCategory.CONSUMIDOR_FINAL        # Cliente CF
)
# Resultado: ReceiptType.FACTURA_B
```

#### 2. `calculate_vat_aliquots_from_line_items(sale)`

Agrupa line items por tasa de IVA y calcula base imponible y monto de IVA.

**Fórmula (Factura A - IVA discriminado):**
```
item_total = (quantity × unit_price) - discount_amount
base_amount = item_total / (1 + vat_rate/100)
vat_amount = base_amount × (vat_rate/100)
```

**Ejemplo:**
```python
# Venta con 3 items:
# - Item 1: $1000 con IVA 21%
# - Item 2: $500 con IVA 21%
# - Item 3: $100 con IVA 10.5%

vat_aliquots = InvoiceService.calculate_vat_aliquots_from_line_items(sale)

# Resultado:
{
    '21.00': {
        'base_amount': Decimal('1239.67'),  # (1000+500)/1.21
        'vat_amount': Decimal('260.33')     # 1239.67 * 0.21
    },
    '10.50': {
        'base_amount': Decimal('90.50'),    # 100/1.105
        'vat_amount': Decimal('9.50')       # 90.50 * 0.105
    }
}
```

#### 3. `create_invoice_from_sale(sale_id, user)`

Crea factura en estado DRAFT.

**Flujo:**
1. Validar que Sale esté en estado COMPLETED
2. Validar que no tenga factura previa
3. Obtener datos del cliente (o usar "Consumidor Final")
4. Determinar tipo de comprobante
5. Calcular impuestos según tipo
6. Crear Invoice
7. Si Factura A: crear VATAliquot por cada tasa

**Validaciones:**
- Sale debe estar COMPLETED
- Sale no puede tener invoice previa
- Cliente puede ser null (se usa "Consumidor Final")

#### 4. `emit_cae(invoice_id)`

Valida comprobante con AFIP y obtiene CAE.

**Modo DEBUG** (`AFIP_DEBUG_MODE=True`):
- Genera CAE simulado: `SIM` + timestamp
- No contacta AFIP
- Útil para desarrollo y testing

**Modo PRODUCTION** (`AFIP_DEBUG_MODE=False`):
- Crea `Receipt` en django_afip
- Llama a `receipt.validate()` (Web Service AFIP)
- Copia CAE desde `ReceiptValidation`
- Maneja errores AFIP

**Estados:**
- `DRAFT` → `PENDING` → `AUTHORIZED` (éxito)
- `DRAFT` → `PENDING` → `REJECTED` (error)

#### 5. `generate_pdf(invoice)`

Genera PDF del comprobante.

**Modo DEBUG**:
- Usa ReportLab para PDF básico
- Incluye: CAE, cliente, montos

**Modo PRODUCTION**:
- Usa `invoice.afip_receipt.as_pdf()`
- PDF oficial con layout AFIP

#### 6. `send_invoice_email(invoice, pdf_buffer)`

Envía email con PDF adjunto al cliente.

**Validaciones:**
- Cliente debe tener email registrado
- Factura debe estar autorizada

**Template de Email:**
```
Asunto: Su Factura Electrónica [Tipo] - [Número]

Estimado/a [Cliente],

Adjuntamos su comprobante electrónico autorizado por AFIP.

Detalle del comprobante:
- Tipo: Factura A / B / C
- Número: 0001-00000123
- CAE: 12345678901234
- Vencimiento CAE: 2026-02-05
- Total: $1.234,56

Este comprobante tiene plena validez legal según normativa AFIP.
```

**Configuración Email** (ver `settings.py`):
```python
# Desarrollo: Console backend (imprime en terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Producción: SMTP real
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'tu-email@gmail.com'
EMAIL_HOST_PASSWORD = 'tu-contraseña-o-app-password'
DEFAULT_FROM_EMAIL = 'facturacion@tuempresa.com.ar'
```

#### 7. `procesar_venta_afip(sale_id, user)` - MÉTODO ORQUESTADOR

Método principal que orquesta el flujo completo.

**Flujo:**
1. Crear Invoice desde Sale
2. Emitir CAE (validar con AFIP)
3. Generar PDF
4. Enviar email al cliente

**Manejo de Errores:**

| Paso            | Error                    | Acción                                      |
|-----------------|--------------------------|---------------------------------------------|
| Crear Invoice   | ValidationError          | Rollback completo (no se crea nada)         |
| Emitir CAE      | AFIP rechaza             | Rollback completo (Invoice → REJECTED)      |
| Generar PDF     | Error técnico            | Rollback completo                           |
| Enviar Email    | Cliente sin email / SMTP | **NO rollback** - CAE ya autorizado, loguear error |

**CRÍTICO**: Si el email falla, el CAE ya fue autorizado por AFIP y NO se puede deshacer. El sistema:
- Loguea advertencia
- Guarda nota en `invoice.notes`
- Retorna `email_sent=False` pero `success=True`

**Respuesta:**
```python
{
    'success': True,
    'invoice': Invoice instance,
    'cae': '12345678901234',
    'display_number': '0001-00000123',
    'email_sent': True,  # o False si falló
    'error': None  # o mensaje de error si email falló
}
```

## 🔄 Flujo de Facturación

### Diagrama de Secuencia

```
Usuario          SaleService       InvoiceService       AFIP          Email
   |                  |                    |              |             |
   |-- finalize_sale -|                    |              |             |
   |                  |                    |              |             |
   |                  |-- procesar_venta_afip()           |             |
   |                  |                    |              |             |
   |                  |                    |-- create_invoice()         |
   |                  |                    |<- Invoice(DRAFT)           |
   |                  |                    |              |             |
   |                  |                    |-- emit_cae() |             |
   |                  |                    |------------->|             |
   |                  |                    |<-- CAE ------|             |
   |                  |                    |              |             |
   |                  |                    |-- generate_pdf()           |
   |                  |                    |<- PDF buffer |             |
   |                  |                    |              |             |
   |                  |                    |-- send_email()------------>|
   |                  |                    |              |             |
   |                  |<- Result (success, CAE, email_sent)             |
   |<- Sale COMPLETED |                    |              |             |
```

### Ejemplo de Uso

```python
from invoices.services import InvoiceService
from sale.services import SaleService

# Paso 1: Finalizar venta (marcar como COMPLETED)
sale = SaleService.finalize_sale(sale_id=123, user=request.user)

# Paso 2: Procesar facturación AFIP
result = InvoiceService.procesar_venta_afip(
    sale_id=sale.id,
    user=request.user
)

if result['success']:
    print(f"✓ Factura autorizada")
    print(f"  CAE: {result['cae']}")
    print(f"  Número: {result['display_number']}")
    print(f"  Email enviado: {result['email_sent']}")

    if not result['email_sent']:
        print(f"  ⚠ Advertencia: {result['error']}")
else:
    print(f"✗ Error: {result['error']}")
```

### Integración en Views

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from sale.services import SaleService
from invoices.services import InvoiceService

@require_POST
def finalize_sale_view(request):
    sale_id = request.POST.get('sale_id')

    try:
        # Finalizar venta
        sale = SaleService.finalize_sale(sale_id, request.user)

        # Procesar facturación
        result = InvoiceService.procesar_venta_afip(sale_id, request.user)

        return JsonResponse({
            'success': True,
            'sale_id': sale.id,
            'invoice_id': result['invoice'].id,
            'cae': result['cae'],
            'display_number': result['display_number'],
            'email_sent': result['email_sent']
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
```

## ⚙️ Configuración

### 1. Migrar Base de Datos

```bash
# Aplicar migraciones
uv run python src/manage.py migrate products
uv run python src/manage.py migrate sale
uv run python src/manage.py migrate invoices
```

### 2. Configurar Categoría Fiscal de la Empresa

Editar `src/apps/invoices/services.py`:

```python
class InvoiceService:
    # Configurar según tu empresa
    ISSUER_TAX_CATEGORY = TaxCategory.RESPONSABLE_INSCRIPTO  # o MONOTRIBUTO
```

### 3. Configurar Email (Producción)

Crear archivo `.env`:

```bash
# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=facturacion@tuempresa.com.ar
EMAIL_HOST_PASSWORD=tu-app-password
DEFAULT_FROM_EMAIL=facturacion@tuempresa.com.ar
```

Cargar en `settings.py`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND')
EMAIL_HOST = os.getenv('EMAIL_HOST')
# ... etc
```

### 4. Configurar AFIP (Producción)

**Requisitos:**
1. Certificado SSL AFIP (`.crt` y `.key`)
2. Registrar TaxPayer en Django Admin
3. Obtener Puntos de Venta

**Comandos:**

```bash
# 1. Crear TaxPayer en Django Admin
# Path: /admin/django_afip/taxpayer/

# 2. Fetch Puntos de Venta desde AFIP
uv run python src/manage.py afip_fetch_points_of_sales

# 3. Desactivar modo DEBUG
export AFIP_DEBUG_MODE=False
```

**Certificados AFIP:**
- Generar CSR en AFIP Web Service
- Descargar certificado
- Subir `.crt` y `.key` al TaxPayer en Django Admin

### 5. Instalar Dependencias Adicionales

```bash
# Para generación de PDF en modo DEBUG
uv add reportlab

# Para cargar .env (opcional)
uv add python-dotenv
```

## 🧪 Testing

### Modo DEBUG (sin contactar AFIP)

```python
# settings.py
AFIP_DEBUG_MODE = True
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

**Ventajas:**
- No requiere certificados AFIP
- CAE simulado generado al instante
- Email impreso en consola
- Ideal para desarrollo

### Test Manual

```bash
# Shell de Django
uv run python src/manage.py shell
```

```python
from sale.services import SaleService
from invoices.services import InvoiceService
from customers.models import Customer, TaxCategory
from users.models import User

# Crear usuario de prueba
user = User.objects.first()

# Crear venta de prueba
sale = SaleService.create_sale(user)
SaleService.add_line_item(sale.id, sku='TEST-001', quantity=2)

# Crear cliente con email
customer = Customer.objects.create(
    first_name='Juan',
    last_name='Pérez',
    email='juan.perez@example.com',
    tax_category=TaxCategory.CONSUMIDOR_FINAL
)
SaleService.set_customer(sale.id, customer.id)

# Agregar pago
from payments.services import PaymentService
payment_method = PaymentMethod.objects.first()
PaymentService.add_payment(sale.id, payment_method.id, sale.total)

# Finalizar venta
sale = SaleService.finalize_sale(sale.id, user)

# Procesar facturación
result = InvoiceService.procesar_venta_afip(sale.id, user)

print(f"Success: {result['success']}")
print(f"CAE: {result['cae']}")
print(f"Email sent: {result['email_sent']}")
```

### Test Unitarios

```python
# tests/test_invoices.py
from django.test import TestCase
from invoices.services import InvoiceService
from customers.models import TaxCategory
from invoices.models import ReceiptType

class InvoiceServiceTest(TestCase):
    def test_determine_receipt_type_ri_to_ri(self):
        """RI → RI debe generar Factura A"""
        receipt_type = InvoiceService.determine_receipt_type(
            TaxCategory.RESPONSABLE_INSCRIPTO,
            TaxCategory.RESPONSABLE_INSCRIPTO
        )
        self.assertEqual(receipt_type, ReceiptType.FACTURA_A)

    def test_determine_receipt_type_ri_to_cf(self):
        """RI → CF debe generar Factura B"""
        receipt_type = InvoiceService.determine_receipt_type(
            TaxCategory.RESPONSABLE_INSCRIPTO,
            TaxCategory.CONSUMIDOR_FINAL
        )
        self.assertEqual(receipt_type, ReceiptType.FACTURA_B)

    def test_calculate_vat_aliquots(self):
        """Test agregación de IVA por alícuota"""
        # ... (crear sale con line items de diferentes tasas)
        vat_aliquots = InvoiceService.calculate_vat_aliquots_from_line_items(sale)

        self.assertIn('21.00', vat_aliquots)
        self.assertIn('10.50', vat_aliquots)
```

## 📚 Referencias

- [django-afip Documentation](https://django-afip.readthedocs.io/)
- [AFIP Web Services Documentation](https://www.afip.gob.ar/ws/)
- [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Django Email Documentation](https://docs.djangoproject.com/en/stable/topics/email/)

## 🔍 Troubleshooting

### Error: "Cliente no tiene email registrado"

**Solución**: Agregar email al Customer antes de facturar.

```python
customer = Customer.objects.get(pk=customer_id)
customer.email = 'cliente@example.com'
customer.save()
```

### Error: "No hay TaxPayer configurado"

**Solución**: Crear TaxPayer en Django Admin con certificados AFIP.

### Error: "AFIP rechazó el comprobante"

**Solución**: Revisar `invoice.notes` para detalles del error AFIP.

Errores comunes:
- Certificado vencido
- CUIT de cliente inválido
- Monto con redondeo incorrecto
- Punto de venta inactivo

### Email no enviado pero CAE autorizado

**Comportamiento esperado**: El CAE ya fue registrado en AFIP y no se puede deshacer.

**Solución**: Reenviar email manualmente o configurar tarea asíncrona.

```python
# Reenviar email manualmente
from invoices.services import InvoiceService

invoice = Invoice.objects.get(pk=invoice_id)
pdf_buffer = InvoiceService.generate_pdf(invoice)
InvoiceService.send_invoice_email(invoice, pdf_buffer)
```

## 📝 Notas Finales

- Todos los montos fiscales se almacenan con 2 decimales (`Decimal('0.01')`)
- Validación matemática: `net_taxed + vat_amount == total_amount` (para Factura A)
- Desnormalización: `vat_rate`, `customer_name`, `customer_tax_id` se copian para historial
- Transacciones atómicas: Garantizan consistencia en operaciones críticas
- Modo DEBUG útil para desarrollo sin certificados AFIP
