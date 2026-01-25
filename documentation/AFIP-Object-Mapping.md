# 🔄 Mapeo de Objetos: Sistema Local ↔️ Django-AFIP

## 📋 Índice
1. [Arquitectura General](#arquitectura-general)
2. [Mapeo de Modelos](#mapeo-de-modelos)
3. [Flujo de Datos](#flujo-de-datos)
4. [Relaciones entre Objetos](#relaciones-entre-objetos)
5. [Ejemplos de Código](#ejemplos-de-código)

---

## 1. Arquitectura General

### Diseño de Capas

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (POS)                       │
│              templates/sale/pos_index.html              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│               CAPA DE NEGOCIO (Local)                   │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐       │
│  │  Sale    │  │ Payment  │  │  Invoice (LOCAL) │       │
│  │  Models  │  │ Services │  │  + Services      │       │
│  └──────────┘  └──────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│          CAPA DE INTEGRACIÓN (django-afip)              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐       │
│  │ TaxPayer │  │  Point   │  │  Receipt + CAE   │       │
│  │          │  │  OfSales │  │  (AFIP Models)   │       │
│  └──────────┘  └──────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                 AFIP WEB SERVICES                       │
│          (Facturación Electrónica WSFE)                 │
└─────────────────────────────────────────────────────────┘
```

### Principios de Diseño

1. **Separación de Responsabilidades:**
   - **Modelos Locales:** Gestión interna del negocio (ventas, pagos, clientes)
   - **Modelos AFIP:** Solo para comunicación con AFIP (certificados, CAE)

2. **Desnormalización Intencional:**
   - Los datos críticos se copian desde AFIP a modelos locales
   - Garantiza historial inmutable incluso si AFIP falla

3. **Relación Loose Coupling:**
   - `Invoice.afip_receipt` usa `SET_NULL` (no `CASCADE`)
   - Si django-afip se elimina, el historial local persiste

---

## 2. Mapeo de Modelos

### 2.1 Empresa Emisora

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| `settings.ISSUER_TAX_CATEGORY` | `TaxPayer.cuit` | CUIT del emisor (empresa) |
| `InvoiceService.ISSUER_TAX_CATEGORY` | - | Categoría fiscal configurada en código |
| - | `TaxPayer.certificate` | Certificado SSL para AFIP |
| - | `TaxPayer.key` | Clave privada del certificado |
| - | `TaxPayer.is_sandboxed` | Modo de testing AFIP |

**Modelo django-afip:**
```python
class TaxPayer(models.Model):
    """Contribuyente (empresa emisora)"""
    name = models.CharField(max_length=128)
    cuit = models.BigIntegerField()  # CUIT de la empresa
    certificate = models.FileField()  # Certificado SSL (.crt)
    key = models.FileField()  # Clave privada (.key)
    is_sandboxed = models.BooleanField(default=True)
```

**Configuración Local:**
```python
# src/apps/invoices/services.py
class InvoiceService:
    ISSUER_TAX_CATEGORY = TaxCategory.RESPONSABLE_INSCRIPTO
```

**Mapeo:**
- **1 TaxPayer** = **1 Empresa** en tu sistema
- Se crea manualmente en Django Admin (solo producción)
- En modo DEBUG: No se usa TaxPayer

---

### 2.2 Punto de Venta

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| - | `PointOfSales.number` | Número de punto de venta (ej: 0001) |
| - | `PointOfSales.issuance_type` | Tipo de emisión ('CAE' = online) |
| - | `PointOfSales.owner` | FK a TaxPayer |

**Modelo django-afip:**
```python
class PointOfSales(models.Model):
    """Punto de venta autorizado por AFIP"""
    number = models.PositiveSmallIntegerField()  # 0001, 0002, etc.
    issuance_type = models.CharField(max_length=8)  # 'CAE'
    owner = models.ForeignKey(TaxPayer)
    blocked = models.BooleanField(default=False)
```

**Obtención:**
```bash
# Solo en producción
python manage.py afip_fetch_points_of_sales
```

**Mapeo:**
- **1 PointOfSales** = **1 Terminal POS** físico
- Se obtiene desde AFIP (no se crea manualmente)
- En modo DEBUG: No se usa PointOfSales

---

### 2.3 Cliente (Receptor)

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| `Customer.first_name` | - | Nombre del cliente |
| `Customer.last_name` | - | Apellido del cliente |
| `Customer.tax_id` | `Receipt.document_number` | CUIT/DNI del cliente |
| `Customer.tax_category` | - | CF, RI, MT, EX |
| `Customer.email` | - | Email para envío de factura |
| `Invoice.customer_name` | - | Desnormalizado para historial |
| `Invoice.customer_tax_id` | `Receipt.document_number` | Copiado a AFIP |
| `Invoice.customer_tax_category` | - | Solo en Invoice local |

**Mapeo:**
- Los datos del cliente se **copian** desde `Customer` a `Invoice` (desnormalización)
- Solo el `document_number` (CUIT/DNI) se envía a AFIP en `Receipt`
- El nombre completo NO se envía a AFIP (solo se guarda localmente)

**Razón:** AFIP solo requiere CUIT/DNI, no el nombre completo.

---

### 2.4 Venta

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| `Sale.total` | `Receipt.total_amount` | Monto total de la venta |
| `Sale.line_items` | - | Detalle de productos (NO se envía) |
| `Sale.customer` | `Receipt.document_number` | Relación indirecta |
| `Sale.status = COMPLETED` | - | Prerequisito para facturar |

**Modelo Local:**
```python
class Sale(models.Model):
    customer = models.ForeignKey(Customer)
    status = models.CharField(choices=STATUS_CHOICES)
    global_discount_amount = models.DecimalField()

    @property
    def total(self):
        return self.subtotal - self.global_discount_amount
```

**Mapeo:**
- **1 Sale** → **1 Invoice** → **1 Receipt** (AFIP)
- Los `line_items` NO se envían a AFIP (solo el total y alícuotas)
- AFIP no conoce los productos vendidos, solo importes

---

### 2.5 Factura (Comprobante)

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| `Invoice` (modelo local) | `Receipt` (modelo AFIP) | Comprobante fiscal |
| `Invoice.receipt_type` | `Receipt.receipt_type` | 'A', 'B', 'C' |
| `Invoice.total_amount` | `Receipt.total_amount` | Monto total |
| `Invoice.net_taxed` | `Receipt.net_taxed` | Neto gravado (solo Factura A) |
| `Invoice.vat_amount` | `Receipt.vat_amount` | Monto de IVA (solo Factura A) |
| `Invoice.net_untaxed` | `Receipt.net_untaxed` | Neto no gravado (Factura B/C) |
| `Invoice.cae` | `ReceiptValidation.cae` | CAE (copiado desde AFIP) |
| `Invoice.cae_expiration` | `ReceiptValidation.cae_expiration` | Vencimiento CAE |
| `Invoice.afip_receipt` | `Receipt` (FK) | Relación con modelo AFIP |

**Modelos:**

**Local:**
```python
class Invoice(models.Model):
    """Factura local (historial inmutable)"""
    sale = models.OneToOneField(Sale)
    afip_receipt = models.OneToOneField('django_afip.Receipt', null=True, on_delete=SET_NULL)

    receipt_type = models.CharField(choices=ReceiptType.choices)  # A, B, C
    status = models.CharField(choices=InvoiceStatus.choices)  # DRAFT, AUTHORIZED, etc.

    # Datos del cliente (desnormalizados)
    customer_name = models.CharField(max_length=200)
    customer_tax_id = models.CharField(max_length=20)
    customer_tax_category = models.CharField(max_length=2)

    # Montos
    net_taxed = models.DecimalField()
    vat_amount = models.DecimalField()
    net_untaxed = models.DecimalField()
    total_amount = models.DecimalField()

    # CAE (copiado desde AFIP)
    cae = models.CharField(max_length=14, blank=True)
    cae_expiration = models.DateField(null=True)
```

**Django-AFIP:**
```python
class Receipt(models.Model):
    """Comprobante enviado a AFIP"""
    point_of_sales = models.ForeignKey(PointOfSales)
    receipt_type = models.ForeignKey(ReceiptType)  # FK a catálogo AFIP

    # Datos fiscales
    document_number = models.BigIntegerField()  # CUIT/DNI del cliente
    issued_date = models.DateField()

    # Montos
    total_amount = models.DecimalField()
    net_untaxed = models.DecimalField()
    net_taxed = models.DecimalField()
    vat_amount = models.DecimalField()

    # Relación con validación
    # validation: ReceiptValidation (reverse FK)
```

**Flujo de Creación:**

```python
# 1. Crear Invoice local
invoice = Invoice.objects.create(
    sale=sale,
    receipt_type='B',
    total_amount=sale.total,
    customer_name=customer.full_name,
    # ...
)

# 2. Crear Receipt en django-afip (solo producción)
receipt = Receipt.objects.create(
    point_of_sales=pos,
    receipt_type=afip_receipt_type,
    total_amount=invoice.total_amount,
    net_taxed=invoice.net_taxed,
    # ...
)

# 3. Validar con AFIP
validation = receipt.validate()  # Llama a WSFE

# 4. Copiar CAE de vuelta al Invoice local
invoice.cae = validation.cae
invoice.cae_expiration = validation.cae_expiration
invoice.afip_receipt = receipt
invoice.save()
```

**Principio Clave:**
- `Invoice` (local) **existe siempre**, incluso sin internet
- `Receipt` (AFIP) **solo existe en producción**
- Los datos críticos (CAE, totales) se **copian** desde `Receipt` a `Invoice`

---

### 2.6 Tipo de Comprobante

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| `ReceiptType.FACTURA_A = 'A'` | `ReceiptType(code='1')` | Factura A |
| `ReceiptType.FACTURA_B = 'B'` | `ReceiptType(code='6')` | Factura B |
| `ReceiptType.FACTURA_C = 'C'` | `ReceiptType(code='11')` | Factura C |

**Modelo Local:**
```python
class ReceiptType(models.TextChoices):
    FACTURA_A = 'A', 'Factura A'
    FACTURA_B = 'B', 'Factura B'
    FACTURA_C = 'C', 'Factura C'
```

**Modelo Django-AFIP:**
```python
class ReceiptType(models.Model):
    """Catálogo oficial de tipos de comprobante AFIP"""
    code = models.CharField(max_length=3)  # '1', '6', '11', etc.
    description = models.CharField(max_length=250)
```

**Mapeo:**
```python
# En InvoiceService._emit_cae_production()
receipt_type_map = {
    'A': '1',   # Factura A → código AFIP 1
    'B': '6',   # Factura B → código AFIP 6
    'C': '11',  # Factura C → código AFIP 11
}

afip_receipt_type = ReceiptType.objects.get(
    code=receipt_type_map[invoice.receipt_type]
)
```

**Catálogo Completo AFIP:**
- `1`: Factura A
- `6`: Factura B
- `11`: Factura C
- `3`: Nota de Crédito A
- `8`: Nota de Crédito B
- ... (más de 200 tipos)

---

### 2.7 Alícuotas de IVA

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| `VATAliquot` (modelo local) | `Vat` (modelo AFIP) | Detalle de alícuotas IVA |
| `VATAliquot.invoice` | `Vat.receipt` | Relación con comprobante |
| `VATAliquot.vat_rate` | `Vat.vat_type` | Tasa de IVA (21%, 10.5%, etc.) |
| `VATAliquot.base_amount` | `Vat.base_amount` | Base imponible |
| `VATAliquot.vat_amount` | `Vat.amount` | Monto de IVA |

**Modelo Local:**
```python
class VATAliquot(models.Model):
    """Alícuota de IVA (solo Factura A)"""
    invoice = models.ForeignKey(Invoice, related_name='vat_aliquots')
    vat_rate = models.DecimalField()  # 21.00, 10.50, etc.
    base_amount = models.DecimalField()  # Neto sin IVA
    vat_amount = models.DecimalField()  # Monto de IVA
```

**Modelo Django-AFIP:**
```python
class Vat(models.Model):
    """Alícuota IVA enviada a AFIP"""
    receipt = models.ForeignKey(Receipt)
    vat_type = models.ForeignKey(VatType)  # FK a catálogo AFIP
    base_amount = models.DecimalField()
    amount = models.DecimalField()  # Monto de IVA
```

**Uso:** Solo para **Factura A** (IVA discriminado).

**Ejemplo:**

```python
# Factura A con 2 alícuotas
invoice = Invoice.objects.create(receipt_type='A', ...)

# Alícuota 1: IVA 21%
VATAliquot.objects.create(
    invoice=invoice,
    vat_rate=Decimal('21.00'),
    base_amount=Decimal('826.45'),  # Neto
    vat_amount=Decimal('173.55')   # IVA 21%
)

# Alícuota 2: IVA 10.5%
VATAliquot.objects.create(
    invoice=invoice,
    vat_rate=Decimal('10.50'),
    base_amount=Decimal('90.50'),
    vat_amount=Decimal('9.50')
)

# Total neto: 826.45 + 90.50 = 916.95
# Total IVA: 173.55 + 9.50 = 183.05
# Total factura: 1100.00
```

**En django-afip (producción):**
```python
# Mapeo de tasa a VatType
vat_type_map = {
    Decimal('21.00'): VatType.objects.get(code=5),   # IVA 21%
    Decimal('10.50'): VatType.objects.get(code=4),   # IVA 10.5%
}

for aliquot in invoice.vat_aliquots.all():
    Vat.objects.create(
        receipt=receipt,
        vat_type=vat_type_map[aliquot.vat_rate],
        base_amount=aliquot.base_amount,
        amount=aliquot.vat_amount
    )
```

---

### 2.8 CAE (Código de Autorización Electrónico)

| **Sistema Local** | **Django-AFIP** | **Descripción** |
|-------------------|-----------------|-----------------|
| `Invoice.cae` | `ReceiptValidation.cae` | Código de 14 dígitos |
| `Invoice.cae_expiration` | `ReceiptValidation.cae_expiration` | Fecha de vencimiento |
| `Invoice.status = AUTHORIZED` | `ReceiptValidation.result = 'A'` | Estado autorizado |
| `Invoice.notes` | `ReceiptValidation.observations` | Mensajes de AFIP |

**Modelo Django-AFIP:**
```python
class ReceiptValidation(models.Model):
    """Respuesta de AFIP al validar un comprobante"""
    receipt = models.OneToOneField(Receipt)
    result = models.CharField(max_length=1)  # 'A' = Aprobado, 'R' = Rechazado
    cae = models.CharField(max_length=14)  # Código de autorización
    cae_expiration = models.DateField()
    processed_date = models.DateTimeField()
    observations = models.CharField(max_length=1024)  # Errores/warnings
```

**Flujo:**

```python
# 1. Enviar comprobante a AFIP
receipt = Receipt.objects.create(...)
validation = receipt.validate()  # Llama a WSFE

# 2. AFIP responde con CAE
if validation.result == 'A':  # Aprobado
    # 3. Copiar CAE a Invoice local
    invoice.cae = validation.cae
    invoice.cae_expiration = validation.cae_expiration
    invoice.status = InvoiceStatus.AUTHORIZED
    invoice.save()
else:  # Rechazado
    invoice.status = InvoiceStatus.REJECTED
    invoice.notes = validation.observations
    invoice.save()
```

**Modo DEBUG:**
```python
# No se contacta AFIP, se genera CAE simulado
timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
invoice.cae = f"SIM{timestamp}"  # SIM20260125123456
invoice.cae_expiration = timezone.now().date() + timedelta(days=10)
invoice.status = InvoiceStatus.AUTHORIZED
```

---

## 3. Flujo de Datos

### 3.1 Flujo Completo: Venta → Factura → CAE

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CREACIÓN DE VENTA (Sistema Local)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
    Sale.objects.create(customer=customer, ...)
    SaleLineItem.objects.create(sale=sale, product=product, ...)
    Payment.objects.create(sale=sale, amount=total, ...)
    sale.status = COMPLETED
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. CREACIÓN DE INVOICE LOCAL                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
    InvoiceService.create_invoice_from_sale(sale_id, user)
        ├─ Determinar tipo: A, B, C
        ├─ Calcular impuestos
        ├─ Desnormalizar datos del cliente
        └─ Invoice.objects.create(...)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. EMISIÓN DE CAE                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
    InvoiceService.emit_cae(invoice_id)
                            ↓
    ┌────────────────┬──────────────────┐
    │  DEBUG MODE    │  PRODUCTION MODE │
    └────────────────┴──────────────────┘
           ↓                    ↓
    Generate simulated    Create Receipt
    CAE locally          Send to AFIP
           ↓                    ↓
    invoice.cae =        receipt.validate()
    "SIM20260125..."            ↓
           ↓            ReceiptValidation
    invoice.status =            ↓
    AUTHORIZED           Copy CAE back:
                        invoice.cae = validation.cae
                        invoice.afip_receipt = receipt
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. GENERACIÓN DE PDF                                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
    InvoiceService.generate_pdf(invoice)
                            ↓
    ┌────────────────┬──────────────────┐
    │  DEBUG MODE    │  PRODUCTION MODE │
    └────────────────┴──────────────────┘
           ↓                    ↓
    ReportLab PDF        receipt.as_pdf()
    (simple)            (con código de barras)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. ENVÍO DE EMAIL                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
    InvoiceService.send_invoice_email(invoice, pdf_buffer)
        └─ EmailMessage(to=[customer.email], attachment=pdf)
```

---

### 3.2 Mapeo de Estados

| **Evento** | **Invoice.status** | **Receipt** | **ReceiptValidation** |
|------------|-------------------|-------------|----------------------|
| Factura creada | `DRAFT` | - | - |
| CAE en proceso | `PENDING` | Receipt creado | - |
| CAE aprobado | `AUTHORIZED` | Receipt guardado | `result='A'`, CAE presente |
| CAE rechazado | `REJECTED` | Receipt guardado | `result='R'`, observations con error |

---

### 3.3 Desnormalización: ¿Por qué copiar datos?

**Problema:** Si AFIP falla o los datos se eliminan, perdemos el historial.

**Solución:** Copiar datos críticos a `Invoice` local.

**Datos copiados:**

```python
# Desde Customer → Invoice
invoice.customer_name = customer.full_name
invoice.customer_tax_id = customer.tax_id
invoice.customer_tax_category = customer.tax_category

# Desde ReceiptValidation → Invoice
invoice.cae = validation.cae
invoice.cae_expiration = validation.cae_expiration
```

**Beneficios:**
- ✅ Historial inmutable (aunque Customer se borre)
- ✅ Funciona sin conexión a AFIP
- ✅ Consultas rápidas (sin JOINs a django-afip)

---

## 4. Relaciones entre Objetos

### 4.1 Diagrama de Relaciones

```
SISTEMA LOCAL                    DJANGO-AFIP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Customer ─────┐
              ├─→ Sale ──→ Invoice ──→ Receipt ──→ ReceiptValidation
Product ──────┤              │           │               │
              │              │           │               ├─→ cae
SaleLineItem ─┘              │           │               └─→ cae_expiration
                             │           │
Payment ─────────────────────┘           ├─→ point_of_sales
                                         │
VATAliquot ──────────────────────────────┴─→ Vat (alícuotas IVA)


LEYENDA:
─→   Flujo de datos
──→  Foreign Key / OneToOne
```

---

### 4.2 Relaciones Detalladas

#### Sale → Invoice (OneToOne)
```python
# Modelos
class Sale(models.Model):
    pass  # No tiene FK a Invoice

class Invoice(models.Model):
    sale = models.OneToOneField(Sale, related_name='invoice')

# Uso
sale = Sale.objects.get(pk=1)
invoice = sale.invoice  # Acceso inverso
```

#### Invoice → Receipt (OneToOne, nullable)
```python
class Invoice(models.Model):
    afip_receipt = models.OneToOneField(
        'django_afip.Receipt',
        null=True,
        blank=True,
        on_delete=models.SET_NULL  # No CASCADE!
    )

# Uso
invoice = Invoice.objects.get(pk=1)
if invoice.afip_receipt:
    print(invoice.afip_receipt.receipt_number)
```

**⚠️ Importante:** `on_delete=SET_NULL` asegura que si se borra el `Receipt`, el `Invoice` local persiste.

#### Receipt → ReceiptValidation (OneToOne)
```python
# Creado automáticamente por django-afip
receipt = Receipt.objects.get(pk=1)
validation = receipt.validation  # Reverse FK
print(validation.cae)
```

---

## 5. Ejemplos de Código

### 5.1 Crear Factura en Modo DEBUG

```python
from invoices.services import InvoiceService
from sale.models import Sale
from users.models import User

# Venta completada
sale = Sale.objects.get(pk=1, status='COMPLETED')
user = User.objects.first()

# Crear Invoice local
invoice = InvoiceService.create_invoice_from_sale(sale.id, user)

print(f"Invoice creada: {invoice.id}")
print(f"Tipo: {invoice.get_receipt_type_display()}")
print(f"Total: ${invoice.total_amount}")
print(f"Status: {invoice.get_status_display()}")  # DRAFT

# Emitir CAE (simulado en DEBUG)
invoice = InvoiceService.emit_cae(invoice.id)

print(f"CAE: {invoice.cae}")  # SIM20260125123456
print(f"Status: {invoice.get_status_display()}")  # AUTHORIZED
print(f"Receipt AFIP: {invoice.afip_receipt}")  # None (no se usa en DEBUG)
```

---

### 5.2 Crear Factura en Modo PRODUCTION

```python
from django_afip.models import TaxPayer, PointOfSales, Receipt, ReceiptType, Vat
from invoices.services import InvoiceService

# Configuración previa (una sola vez)
taxpayer = TaxPayer.objects.get(cuit=30123456789)
pos = PointOfSales.objects.get(owner=taxpayer, number=1)

# Crear Invoice local
sale = Sale.objects.get(pk=1)
invoice = InvoiceService.create_invoice_from_sale(sale.id, user)

# Emitir CAE (contacta AFIP)
invoice = InvoiceService.emit_cae(invoice.id)
# Internamente:
#   1. Crea Receipt en django-afip
#   2. Llama receipt.validate() → WSFE
#   3. Copia CAE a Invoice local
#   4. Guarda relación Invoice.afip_receipt = receipt

# Verificar
print(f"CAE: {invoice.cae}")  # 12345678901234 (real de AFIP)
print(f"Receipt AFIP: {invoice.afip_receipt.id}")  # ID del Receipt
print(f"Punto de Venta: {invoice.afip_receipt.point_of_sales.number}")  # 0001
print(f"Número: {invoice.display_number}")  # 0001-00000123
```

---

### 5.3 Consultar Factura con Alícuotas

```python
from invoices.models import Invoice

# Obtener factura con relaciones
invoice = Invoice.objects.select_related(
    'sale',
    'sale__customer'
).prefetch_related(
    'vat_aliquots'
).get(pk=1)

# Datos locales
print(f"Cliente: {invoice.customer_name}")
print(f"Total: ${invoice.total_amount}")

# Datos AFIP (si existe)
if invoice.afip_receipt:
    print(f"Punto de Venta AFIP: {invoice.afip_receipt.point_of_sales.number}")
    print(f"Número AFIP: {invoice.afip_receipt.receipt_number}")

# Alícuotas (solo Factura A)
if invoice.receipt_type == 'A':
    print("\nAlícuotas de IVA:")
    for aliquot in invoice.vat_aliquots.all():
        print(f"  - IVA {aliquot.vat_rate}%:")
        print(f"    Base: ${aliquot.base_amount}")
        print(f"    IVA: ${aliquot.vat_amount}")
```

---

### 5.4 Mapeo Completo en Código

```python
# SISTEMA LOCAL → DJANGO-AFIP (producción)

# 1. Customer → Receipt.document_number
customer = sale.customer
receipt.document_number = int(customer.tax_id.replace('-', ''))

# 2. Invoice → Receipt (montos)
receipt.total_amount = invoice.total_amount
receipt.net_taxed = invoice.net_taxed
receipt.vat_amount = invoice.vat_amount
receipt.net_untaxed = invoice.net_untaxed

# 3. Invoice.receipt_type → Receipt.receipt_type
receipt_type_map = {'A': '1', 'B': '6', 'C': '11'}
afip_receipt_type = ReceiptType.objects.get(
    code=receipt_type_map[invoice.receipt_type]
)
receipt.receipt_type = afip_receipt_type

# 4. VATAliquot → Vat (alícuotas)
for aliquot in invoice.vat_aliquots.all():
    vat_type = VatType.objects.get(code=...)  # Mapeo según tasa
    Vat.objects.create(
        receipt=receipt,
        vat_type=vat_type,
        base_amount=aliquot.base_amount,
        amount=aliquot.vat_amount
    )

# 5. ReceiptValidation → Invoice (CAE)
validation = receipt.validate()
invoice.cae = validation.cae
invoice.cae_expiration = validation.cae_expiration
invoice.afip_receipt = receipt
invoice.save()
```

---

## 6. Resumen Visual

### Tabla de Mapeo Completo

| **Concepto** | **Sistema Local** | **Django-AFIP** | **Relación** |
|--------------|-------------------|-----------------|--------------|
| Empresa | `settings.ISSUER_TAX_CATEGORY` | `TaxPayer` | Configuración |
| Terminal POS | - | `PointOfSales` | Solo producción |
| Cliente | `Customer` | `Receipt.document_number` | Parcial (solo CUIT) |
| Venta | `Sale` | - | No se envía |
| Productos | `SaleLineItem` | - | No se envían |
| Factura | `Invoice` (local) | `Receipt` (AFIP) | OneToOne (nullable) |
| Tipo Comprobante | `'A'`, `'B'`, `'C'` | `ReceiptType(code)` | Mapeo de códigos |
| Alícuotas IVA | `VATAliquot` | `Vat` | Se crean en ambos |
| CAE | `Invoice.cae` (copiado) | `ReceiptValidation.cae` | Desnormalización |
| PDF | ReportLab (DEBUG) | `receipt.as_pdf()` (Prod) | Diferentes métodos |

---

## 🎯 Puntos Clave

1. **Separación clara:** Modelos locales para negocio, modelos AFIP solo para integración.

2. **Desnormalización intencional:** Datos críticos se copian para garantizar historial inmutable.

3. **Modo DEBUG simplifica:** No se usan modelos AFIP en desarrollo.

4. **Relación loose:** `on_delete=SET_NULL` protege historial local.

5. **AFIP no conoce productos:** Solo recibe totales y alícuotas, no line items.

6. **CAE es el objetivo:** Todo el flujo apunta a obtener y guardar el CAE.

---

**Para más detalles, ver:**
- `src/apps/invoices/services.py` → Lógica de mapeo
- `src/apps/invoices/models.py` → Modelos locales
- Django-AFIP docs: https://django-afip.readthedocs.io/
