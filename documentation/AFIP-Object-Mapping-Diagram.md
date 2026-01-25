# 📊 Diagramas Visuales: Mapeo de Objetos AFIP

## 1. Arquitectura de 3 Capas

```
┌────────────────────────────────────────────────────────────────┐
│                      CAPA PRESENTACIÓN                         │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │   POS UI     │  │  Admin UI    │  │   API REST       │    │
│  │ (pos_index)  │  │  (Django)    │  │  (opcional)      │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
│           │                 │                  │              │
└───────────┼─────────────────┼──────────────────┼──────────────┘
            │                 │                  │
            ↓                 ↓                  ↓
┌────────────────────────────────────────────────────────────────┐
│                      CAPA DE NEGOCIO                           │
│                      (Sistema Local)                           │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  MODELOS                                                │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │  │
│  │  │ Customer │  │   Sale   │  │      Invoice         │  │  │
│  │  │          │  │          │  │    (Factura Local)   │  │  │
│  │  │ - name   │  │ - total  │  │  - receipt_type      │  │  │
│  │  │ - tax_id │  │ - status │  │  - cae (copiado)     │  │  │
│  │  │ - email  │  │          │  │  - total_amount      │  │  │
│  │  └──────────┘  └──────────┘  │  - afip_receipt (FK) │  │  │
│  │       │             │         └──────────────────────┘  │  │
│  │       └─────────────┼──────────────────┬──────────────┐ │  │
│  │                     │                  │              │ │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐ │ │  │
│  │  │ Product  │  │SaleLine  │  │    VATAliquot        │ │ │  │
│  │  │          │  │   Item   │  │  (solo Factura A)    │ │ │  │
│  │  │ - price  │  │          │  │  - vat_rate          │ │ │  │
│  │  │ - vat_   │  │ - qty    │  │  - base_amount       │ │ │  │
│  │  │   rate   │  │ - vat_   │  │  - vat_amount        │ │ │  │
│  │  └──────────┘  │   rate   │  └──────────────────────┘ │ │  │
│  │                └──────────┘                            │ │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  SERVICIOS                                              │  │
│  │  - InvoiceService.create_invoice_from_sale()           │  │
│  │  - InvoiceService.emit_cae()                           │  │
│  │  - InvoiceService.generate_pdf()                       │  │
│  │  - InvoiceService.send_invoice_email()                 │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
            │
            │  (Solo en Modo PRODUCTION)
            ↓
┌────────────────────────────────────────────────────────────────┐
│                   CAPA DE INTEGRACIÓN                          │
│                     (Django-AFIP)                              │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  MODELOS AFIP                                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │  │
│  │  │TaxPayer  │  │  Point   │  │      Receipt         │  │  │
│  │  │(Empresa) │  │ OfSales  │  │   (Comprobante)      │  │  │
│  │  │          │  │          │  │                      │  │  │
│  │  │ - cuit   │  │ - number │  │  - total_amount      │  │  │
│  │  │ - cert   │  │ - type   │  │  - net_taxed         │  │  │
│  │  │ - key    │  │          │  │  - document_number   │  │  │
│  │  └──────────┘  └──────────┘  └──────────────────────┘  │  │
│  │       │             │                  │                │  │
│  │       │             │                  ↓                │  │
│  │       │             │         ┌─────────────────────┐  │  │
│  │       │             │         │ ReceiptValidation   │  │  │
│  │       │             │         │   (Respuesta AFIP)  │  │  │
│  │       │             │         │                     │  │  │
│  │       │             │         │  - cae              │  │  │
│  │       │             │         │  - cae_expiration   │  │  │
│  │       │             │         │  - result ('A'/'R') │  │  │
│  │       │             │         └─────────────────────┘  │  │
│  │       │             │                  │                │  │
│  │       │             ↓                  │                │  │
│  │       │         ┌──────────┐          │                │  │
│  │       │         │   Vat    │          │                │  │
│  │       │         │(Alícuota)│          │                │  │
│  │       │         │          │          │                │  │
│  │       │         │ - base   │          │                │  │
│  │       │         │ - amount │          │                │  │
│  │       │         └──────────┘          │                │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                           │                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  CLIENTE WSFE (Web Services)                            │  │
│  │  - receipt.validate() → Llama a AFIP                    │  │
│  │  - Autenticación con certificados SSL                   │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
            │
            ↓
┌────────────────────────────────────────────────────────────────┐
│                       AFIP WEB SERVICES                        │
│              (Facturación Electrónica - WSFE)                  │
│                                                                │
│  - Validación de comprobantes                                 │
│  - Emisión de CAE                                             │
│  - Consulta de estado tributario                              │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Flujo de Creación de Factura

### Modo DEBUG (Desarrollo)

```
┌──────────┐
│  Usuario │
│  (POS)   │
└────┬─────┘
     │
     │ 1. Crear venta
     ↓
┌──────────────────┐
│      Sale        │
│  status=PENDING  │
└────┬─────────────┘
     │
     │ 2. Agregar productos
     ↓
┌──────────────────┐
│  SaleLineItem    │
│  (productos)     │
└────┬─────────────┘
     │
     │ 3. Registrar pago
     ↓
┌──────────────────┐
│    Payment       │
└────┬─────────────┘
     │
     │ 4. Finalizar venta
     ↓
┌──────────────────┐
│      Sale        │
│ status=COMPLETED │
└────┬─────────────┘
     │
     │ 5. Crear Invoice
     │    InvoiceService.create_invoice_from_sale()
     ↓
┌──────────────────────────────┐
│         Invoice              │
│  - receipt_type = 'B'        │
│  - status = DRAFT            │
│  - customer_name (copiado)   │
│  - total_amount (copiado)    │
└────┬─────────────────────────┘
     │
     │ 6. Emitir CAE (DEBUG)
     │    InvoiceService.emit_cae()
     ↓
┌──────────────────────────────┐
│         Invoice              │
│  - cae = "SIM20260125..."    │ ← Generado localmente
│  - status = AUTHORIZED       │
│  - afip_receipt = None       │ ← No se usa en DEBUG
└────┬─────────────────────────┘
     │
     │ 7. Generar PDF
     │    InvoiceService.generate_pdf()
     ↓
┌──────────────────────────────┐
│       PDF (ReportLab)        │
│  - Factura simple            │
│  - Sin código de barras      │
└────┬─────────────────────────┘
     │
     │ 8. Enviar email
     │    InvoiceService.send_invoice_email()
     ↓
┌──────────────────────────────┐
│     Email (Console)          │
│  - Impreso en terminal       │
│  - PDF adjunto               │
└──────────────────────────────┘
```

---

### Modo PRODUCTION (Producción)

```
┌──────────┐
│  Usuario │
│  (POS)   │
└────┬─────┘
     │
     │ 1-4. Crear venta (igual que DEBUG)
     ↓
┌──────────────────┐
│      Sale        │
│ status=COMPLETED │
└────┬─────────────┘
     │
     │ 5. Crear Invoice
     ↓
┌──────────────────────────────┐
│         Invoice              │
│  - receipt_type = 'B'        │
│  - status = DRAFT            │
└────┬─────────────────────────┘
     │
     │ 6. Emitir CAE (PRODUCTION)
     │    InvoiceService.emit_cae()
     ↓
┌──────────────────────────────┐
│   Crear Receipt (AFIP)       │
│   Receipt.objects.create()   │
│                              │
│   - point_of_sales           │ ← Configurado en Admin
│   - receipt_type             │ ← Código AFIP (6='B')
│   - total_amount             │ ← Copiado de Invoice
│   - document_number          │ ← CUIT del cliente
└────┬─────────────────────────┘
     │
     │ 7. Validar con AFIP
     │    receipt.validate()
     ↓
┌──────────────────────────────┐
│   🌐 LLAMADA A AFIP WSFE    │
│   (Web Service)              │
│                              │
│   Envía:                     │
│   - Certificado SSL          │
│   - Datos del comprobante    │
│   - Alícuotas de IVA         │
└────┬─────────────────────────┘
     │
     │ 8. Respuesta AFIP
     ↓
┌──────────────────────────────┐
│    ReceiptValidation         │
│  - result = 'A' ✅          │
│  - cae = "12345678901234"    │ ← CAE real de AFIP
│  - cae_expiration            │
└────┬─────────────────────────┘
     │
     │ 9. Copiar CAE a Invoice
     ↓
┌──────────────────────────────┐
│         Invoice              │
│  - cae = "12345678901234"    │ ← Copiado desde AFIP
│  - status = AUTHORIZED       │
│  - afip_receipt = receipt    │ ← FK a Receipt
└────┬─────────────────────────┘
     │
     │ 10. Generar PDF
     │     receipt.as_pdf()
     ↓
┌──────────────────────────────┐
│     PDF (Django-AFIP)        │
│  - Formato oficial           │
│  - Código de barras          │
│  - Homologado por AFIP       │
└────┬─────────────────────────┘
     │
     │ 11. Enviar email
     ↓
┌──────────────────────────────┐
│     Email (SMTP Real)        │
│  - Enviado a cliente         │
│  - PDF adjunto               │
└──────────────────────────────┘
```

---

## 3. Mapeo de Datos: Sale → Invoice → Receipt

```
┌─────────────────────────────────────────────────────────────────┐
│                          SALE                                   │
│                                                                 │
│  id: 1                                                          │
│  customer: Customer(id=1, name="Juan Pérez",                    │
│                      tax_id="20-12345678-9",                    │
│                      tax_category="CF")                         │
│  status: COMPLETED                                              │
│  global_discount: $50.00                                        │
│                                                                 │
│  line_items:                                                    │
│    - Product 1: 2 × $1000.00 = $2000.00 (IVA 21%)              │
│    - Product 2: 1 × $500.00  = $500.00  (IVA 10.5%)            │
│                                                                 │
│  Subtotal: $2500.00                                             │
│  Descuento: -$50.00                                             │
│  ───────────────────                                            │
│  TOTAL: $2450.00                                                │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ InvoiceService.create_invoice_from_sale()
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INVOICE (Local)                              │
│                                                                 │
│  id: 4                                                          │
│  sale: Sale(id=1)                                               │
│  receipt_type: 'B'  ← Determinado: RI → CF = Factura B        │
│  status: DRAFT → AUTHORIZED                                     │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DATOS DESNORMALIZADOS (copiados desde Customer)        │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ customer_name: "Juan Pérez"                             │   │
│  │ customer_tax_id: "20-12345678-9"                        │   │
│  │ customer_tax_category: "CF"                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ MONTOS (calculados según tipo B)                       │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ net_untaxed: $2450.00  ← Total con IVA incluido        │   │
│  │ net_taxed: $0.00       ← No discrimina IVA (tipo B)    │   │
│  │ vat_amount: $0.00      ← IVA incluido en total         │   │
│  │ total_amount: $2450.00                                  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ CAE (copiado después de validación AFIP)               │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ cae: "SIM20260125190138" (DEBUG)                        │   │
│  │      "12345678901234"    (PRODUCTION)                   │   │
│  │ cae_expiration: 2026-02-04                              │   │
│  │ afip_receipt: None (DEBUG) / Receipt(id=1) (PROD)       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  vat_aliquots: []  ← Vacío (solo Factura A tiene alícuotas)   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ InvoiceService.emit_cae() [PRODUCTION]
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    RECEIPT (Django-AFIP)                        │
│                                                                 │
│  id: 1                                                          │
│  point_of_sales: PointOfSales(number=1)  ← Config. Admin      │
│  receipt_type: ReceiptType(code='6')     ← '6' = Factura B     │
│  concept: 1  (Productos)                                        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ DATOS DEL CLIENTE (solo CUIT)                          │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ document_type: 96  (CUIT)                               │   │
│  │ document_number: 20123456789  ← Sin guiones            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ MONTOS (copiados desde Invoice)                        │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ total_amount: 2450.00                                   │   │
│  │ net_untaxed: 2450.00                                    │   │
│  │ net_taxed: 0.00                                         │   │
│  │ vat_amount: 0.00                                        │   │
│  │ exempt_amount: 0.00                                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  issued_date: 2026-01-25                                        │
│  receipt_number: 123  ← Asignado por AFIP                      │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ receipt.validate() → AFIP WSFE
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│              RECEIPT VALIDATION (Respuesta AFIP)                │
│                                                                 │
│  id: 1                                                          │
│  receipt: Receipt(id=1)                                         │
│  result: 'A'  ← Aprobado (o 'R' si rechazado)                  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ CAE (generado por AFIP)                                 │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ cae: "12345678901234"                                   │   │
│  │ cae_expiration: 2026-02-04                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  processed_date: 2026-01-25 19:01:38                            │
│  observations: ""  (vacío si aprobado)                          │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ Copiar CAE de vuelta
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INVOICE (Actualizado)                        │
│                                                                 │
│  cae: "12345678901234"      ← COPIADO desde ReceiptValidation │
│  cae_expiration: 2026-02-04 ← COPIADO                          │
│  status: AUTHORIZED         ← Cambiado de PENDING              │
│  afip_receipt: Receipt(1)   ← FK guardado                      │
│  authorized_at: 2026-01-25 19:01:38                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Ejemplo: Factura A con Alícuotas

```
┌─────────────────────────────────────────────────────────────────┐
│                          SALE                                   │
│                                                                 │
│  Cliente: Empresa SA (CUIT: 30-12345678-9, RI)                 │
│                                                                 │
│  line_items:                                                    │
│    - Producto 1: 2 × $121.00 = $242.00 (IVA 21%)               │
│      → Neto: $200.00, IVA: $42.00                              │
│                                                                 │
│    - Producto 2: 1 × $110.50 = $110.50 (IVA 10.5%)             │
│      → Neto: $100.00, IVA: $10.50                              │
│                                                                 │
│  TOTAL: $352.50                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    INVOICE (Factura A)                          │
│                                                                 │
│  receipt_type: 'A'  ← RI → RI = Factura A                      │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ MONTOS (IVA discriminado)                               │   │
│  ├─────────────────────────────────────────────────────────┤   │
│  │ net_taxed: $300.00    ← Suma de netos                   │   │
│  │ vat_amount: $52.50    ← Suma de IVA                     │   │
│  │ net_untaxed: $0.00    ← No hay exentos                  │   │
│  │ total_amount: $352.50 ← Neto + IVA                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  vat_aliquots: ┌─────────────────────────────────────────┐     │
│                │ VATAliquot 1:                           │     │
│                │  - vat_rate: 21.00                      │     │
│                │  - base_amount: $200.00                 │     │
│                │  - vat_amount: $42.00                   │     │
│                └─────────────────────────────────────────┘     │
│                ┌─────────────────────────────────────────┐     │
│                │ VATAliquot 2:                           │     │
│                │  - vat_rate: 10.50                      │     │
│                │  - base_amount: $100.00                 │     │
│                │  - vat_amount: $10.50                   │     │
│                └─────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ↓ [PRODUCTION]
┌─────────────────────────────────────────────────────────────────┐
│                    RECEIPT (Django-AFIP)                        │
│                                                                 │
│  receipt_type: ReceiptType(code='1')  ← '1' = Factura A        │
│                                                                 │
│  total_amount: 352.50                                           │
│  net_taxed: 300.00                                              │
│  vat_amount: 52.50                                              │
│                                                                 │
│  vats: ┌───────────────────────────────────────────────────┐   │
│        │ Vat 1:                                            │   │
│        │  - vat_type: VatType(code=5)  ← IVA 21%          │   │
│        │  - base_amount: 200.00                            │   │
│        │  - amount: 42.00                                  │   │
│        └───────────────────────────────────────────────────┘   │
│        ┌───────────────────────────────────────────────────┐   │
│        │ Vat 2:                                            │   │
│        │  - vat_type: VatType(code=4)  ← IVA 10.5%        │   │
│        │  - base_amount: 100.00                            │   │
│        │  - amount: 10.50                                  │   │
│        └───────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. Estados y Transiciones

```
┌──────────────────────────────────────────────────────────────┐
│              ESTADOS DE INVOICE                              │
└──────────────────────────────────────────────────────────────┘

    CREATE
      │
      ↓
┌───────────┐
│   DRAFT   │  ← Invoice creado, datos locales guardados
└─────┬─────┘
      │
      │ emit_cae() llamado
      ↓
┌───────────┐
│  PENDING  │  ← Esperando respuesta AFIP (solo PRODUCTION)
└─────┬─────┘
      │
      ├────── AFIP responde 'A' (Aprobado)
      │       │
      │       ↓
      │   ┌─────────────┐
      │   │ AUTHORIZED  │  ← CAE obtenido, factura válida ✅
      │   └─────────────┘
      │
      └────── AFIP responde 'R' (Rechazado)
              │
              ↓
          ┌──────────┐
          │ REJECTED │  ← Error en AFIP, ver notes ❌
          └──────────┘
              │
              │ Corregir error y reintentar
              │
              ↓
          ┌───────────┐
          │  PENDING  │  ← Reintento
          └───────────┘
```

---

## 6. Resumen del Flujo de Datos

```
USER INPUT          LOCAL MODELS         DJANGO-AFIP         AFIP WEB
──────────────────────────────────────────────────────────────────────

Crear venta    →    Sale
                    SaleLineItem
                    Payment

Finalizar      →    Sale.status =
venta               COMPLETED

Facturar       →    Invoice.create()
                     ├─ Determinar tipo (A/B/C)
                     ├─ Calcular impuestos
                     ├─ Copiar datos cliente
                     └─ VATAliquot (si A)

                                    [SOLO PRODUCTION]

Emitir CAE     →    Invoice.status   →   Receipt.create()
                    = PENDING             ├─ point_of_sales
                                          ├─ receipt_type
                                          ├─ montos
                                          └─ Vat (alícuotas)

                                          Receipt.validate() → WSFE API
                                                                 ↓
                                                            ┌─────────┐
                                                            │  AFIP   │
                                                            │ valida  │
                                                            │ y emite │
                                                            │   CAE   │
                                                            └─────────┘
                                                                 ↓
                                          ReceiptValidation  ← Response
                                          ├─ result = 'A'
                                          ├─ cae
                                          └─ cae_expiration

Copiar CAE     ←    Invoice.cae      ←   validation.cae
                    Invoice.status =
                    AUTHORIZED

Generar PDF    →    PDF (ReportLab)  →   receipt.as_pdf()
                                          (oficial AFIP)

Enviar email   →    EmailMessage
                    (PDF adjunto)
```

---

## 🎯 Puntos Clave Visualizados

1. **Separación clara:** LOCAL (negocio) ↔️ DJANGO-AFIP (integración) ↔️ AFIP (externo)

2. **Flujo unidireccional:** Sale → Invoice → Receipt → Validation → CAE (copiado) → Invoice

3. **Desnormalización:** Datos críticos (CAE, customer_name) se copian para inmutabilidad

4. **Modo DEBUG simplifica:** Salta toda la capa DJANGO-AFIP

5. **Relación loose:** `afip_receipt` puede ser NULL, protege historial local

---

**Ver también:**
- `AFIP-Object-Mapping.md` - Explicación detallada de cada mapeo
- `AFIP-Integration-Guide.md` - Guía técnica completa
