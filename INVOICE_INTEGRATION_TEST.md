# Guía de Prueba: Integración de Facturación en POS

## ✅ Cambios Implementados

### 1. Advertencias del Servidor Django - SOLUCIONADAS ✓
**Archivo:** `/home/lean/proyects/billing-system/src/core/settings.py`

Se agregó la configuración `DEFAULT_AUTO_FIELD` para eliminar todas las advertencias sobre claves primarias:

```python
# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
```

**Resultado:** `python manage.py check` ahora retorna **0 issues**.

---

### 2. Integración de Facturación en POS - IMPLEMENTADA ✓
**Archivo:** `/home/lean/proyects/billing-system/templates/sale/pos_index.html`

#### 2.1 Estado de Alpine.js (línea ~1039)
Se agregaron nuevas variables al estado:

```javascript
// Modal states
showInvoiceModal: false,  // ← NUEVO

// Invoice data
invoice: {                 // ← NUEVO
    id: null,
    receiptType: '',
    cae: '',
    caeExpiration: '',
    displayNumber: '',
    totalAmount: 0
}
```

#### 2.2 Modificación de `finalizeSale()` (línea ~1620)
La función ahora ejecuta 3 pasos:

**ANTES:**
```javascript
async finalizeSale() {
    // Solo finalizaba la venta
    // Redirigía inmediatamente al POS
}
```

**DESPUÉS:**
```javascript
async finalizeSale() {
    // PASO 1: Finalizar venta
    const response = await this.fetchAPI('/sale/finalize/', {...});

    // PASO 2: Crear factura
    const invoiceResponse = await this.fetchAPI(`/invoices/create/${this.saleId}/`, {...});

    // PASO 3: Emitir CAE
    const caeResponse = await this.fetchAPI(`/invoices/${invoiceData.invoice_id}/emit-cae/`, {...});

    // Guardar datos de la factura
    this.invoice = {...caeData};

    // Mostrar modal con comprobante
    this.showInvoiceModal = true;
}
```

#### 2.3 Nuevo Método `closeInvoiceModal()` (línea ~1664)
```javascript
closeInvoiceModal() {
    this.showInvoiceModal = false;
    // Redirige a nueva venta después de cerrar
    setTimeout(() => {
        window.location.href = '/sale/pos/';
    }, 300);
}
```

#### 2.4 Nuevo Modal de Factura (línea ~920)
Se agregó un modal profesional que muestra:

- ✅ Tipo de Comprobante (Factura A/B/C)
- ✅ CAE (Código de Autorización Electrónica)
- ✅ Fecha de Vencimiento del CAE
- ✅ Número de Comprobante
- ✅ Total de la Venta
- ✅ Botones: "Imprimir" y "Nueva Venta"

**Diseño:**
- Fondo oscuro con overlay (z-index: 50)
- Card blanco con animación de entrada
- Ícono de éxito (checkmark verde)
- Campos con formato monetario (font-mono)
- Botones con diseño consistente del sistema

---

## 🧪 Cómo Probar la Integración

### Opción 1: Prueba desde Django Shell (Verificar Backend)

```bash
uv run python src/manage.py shell
```

```python
from sale.models import Sale
from invoices.services import InvoiceService
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.first()

# Obtener venta completada
sale = Sale.objects.filter(status='COMPLETED').first()

if sale:
    # Crear factura
    invoice = InvoiceService.create_invoice_from_sale(sale.id, user)
    print(f"✓ Factura creada: ID={invoice.id}, Tipo={invoice.get_receipt_type_display()}")

    # Emitir CAE (simulado en modo DEBUG)
    invoice = InvoiceService.emit_cae(invoice.id)
    print(f"✓ CAE emitido: {invoice.cae}")
    print(f"✓ Vence: {invoice.cae_expiration}")
    print(f"✓ Autorizada: {invoice.is_authorized}")
else:
    print("⚠ No hay ventas completadas. Crear una desde el POS primero.")
```

### Opción 2: Prueba desde el POS (Verificar Frontend + Backend)

#### Paso 1: Iniciar el servidor
```bash
just run
# o
uv run python src/manage.py runserver
```

#### Paso 2: Acceder al POS
Abrir en el navegador: `http://127.0.0.1:8000/sale/pos/`

#### Paso 3: Crear una venta completa
1. **Agregar productos** (botón "Agregar Producto")
   - Buscar o crear productos
   - Agregar al menos 1 producto

2. **Agregar pagos** (botón "Agregar Pago")
   - Seleccionar método (Efectivo/Débito/Crédito)
   - Ingresar monto hasta cubrir el total

3. **Finalizar venta** (botón "Finalizar Venta")
   - El botón debe estar habilitado (verde)
   - Confirmar el diálogo

#### Paso 4: Verificar el Modal de Factura
Deberías ver automáticamente:

```
┌─────────────────────────────────────────┐
│        ✓ ¡Comprobante Generado!        │
│   La venta se finalizó correctamente    │
│                                         │
│  Tipo de Comprobante:     Factura B    │
│  ─────────────────────────────────────  │
│  CAE: SIM20260125123456                │
│  ─────────────────────────────────────  │
│  Vencimiento CAE: 2026-02-04           │
│  ─────────────────────────────────────  │
│  Número: Sin autorizar                 │
│  ─────────────────────────────────────  │
│  Total: $ 12.345,67                    │
│                                         │
│  [Imprimir]     [Nueva Venta]          │
└─────────────────────────────────────────┘
```

**Datos del CAE en modo DEBUG:**
- **Formato CAE:** `SIM` + timestamp (ej: `SIM20260125123456`)
- **Vencimiento:** Fecha actual + 10 días
- **Status:** Siempre AUTHORIZED
- **Notas:** "CAE simulado - Modo DEBUG"

---

## 🔍 Verificar en Django Admin

### Ver Facturas Creadas
1. Acceder a: `http://127.0.0.1:8000/admin/`
2. Ir a: **Invoices** → **Invoices**
3. Verificar:
   - ID de factura
   - Tipo (A/B/C)
   - Status: AUTHORIZED
   - CAE generado
   - Cliente
   - Montos (net_taxed, vat_amount, total_amount)
   - Fecha de creación

### Ver Alícuotas de IVA (solo Factura A)
1. Acceder a: **Invoices** → **VAT Aliquots**
2. Ver breakdown de IVA 21%

---

## 📊 Flujo Completo de la Facturación

```
Usuario hace click en "Finalizar Venta"
           ↓
[1] POST /sale/finalize/
    → Sale.status = COMPLETED
           ↓
[2] POST /invoices/create/{sale_id}/
    → InvoiceService.create_invoice_from_sale()
    → Determina tipo: A/B/C (según categoría fiscal)
    → Calcula IVA discriminado o incluido
    → Crea Invoice (status=DRAFT)
    → Si es Factura A: crea VATAliquot
           ↓
[3] POST /invoices/{invoice_id}/emit-cae/
    → InvoiceService.emit_cae()
    → Modo DEBUG: genera CAE simulado
    → Invoice.status = AUTHORIZED
    → Guarda CAE y fecha de vencimiento
           ↓
[4] Frontend muestra modal
    → Renderiza datos del comprobante
    → Usuario puede imprimir o ir a nueva venta
```

---

## 🎯 Tipo de Comprobante Generado

El tipo se determina automáticamente según:

**Configuración Actual:**
- **Emisor (Empresa):** Responsable Inscripto (RI)
  - Configurado en: `InvoiceService.ISSUER_TAX_CATEGORY`

**Matriz de Decisión:**

| Cliente              | Comprobante | IVA          |
|---------------------|-------------|--------------|
| Responsable Inscripto | Factura A   | Discriminado |
| Monotributo          | Factura B   | Incluido     |
| Consumidor Final     | Factura B   | Incluido     |
| Exento               | Factura B   | Incluido     |

**Ejemplo:**
- Si la venta NO tiene cliente → Cliente = "Consumidor Final" → **Factura B**
- Si el cliente es RI → **Factura A** (con alícuota IVA 21%)

---

## 🐛 Troubleshooting

### Problema: Modal no aparece
**Causa:** Error en alguna de las 3 llamadas API
**Solución:**
1. Abrir Developer Tools (F12) → Console
2. Buscar errores JavaScript
3. Verificar en Network tab las respuestas de:
   - `/sale/finalize/`
   - `/invoices/create/{id}/`
   - `/invoices/{id}/emit-cae/`

### Problema: CAE no se genera
**Causa:** Error en InvoiceService.emit_cae()
**Solución:**
1. Verificar que AFIP_DEBUG_MODE=True en .env
2. Revisar logs en terminal del servidor
3. Verificar Invoice.notes para mensajes de error

### Problema: "Solo ventas completadas"
**Causa:** Sale.status != COMPLETED
**Solución:**
1. Asegurarse de llamar `/sale/finalize/` antes de crear invoice
2. El POS ya lo hace automáticamente (Paso 1 de finalizeSale)

---

## 📝 Archivos Modificados

1. `/home/lean/proyects/billing-system/src/core/settings.py`
   - Agregado: `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'`

2. `/home/lean/proyects/billing-system/templates/sale/pos_index.html`
   - Agregado: Variables de estado `showInvoiceModal` e `invoice`
   - Modificado: Método `finalizeSale()` (3 pasos)
   - Agregado: Método `closeInvoiceModal()`
   - Agregado: Modal HTML completo (~70 líneas)

---

## ✨ Próximas Mejoras Opcionales

1. **Impresión de Comprobante:**
   - Implementar template de impresión con logo
   - Incluir QR code de AFIP (cuando se use modo producción)

2. **Envío por Email:**
   - Agregar botón "Enviar por Email"
   - Enviar PDF del comprobante al cliente

3. **Modo Producción:**
   - Descomentar campo `afip_receipt` en models.py
   - Configurar TaxPayer con certificados SSL
   - Ejecutar `afip_fetch_points_of_sales`
   - Cambiar AFIP_DEBUG_MODE=False

4. **Notas de Crédito:**
   - Extender ReceiptType para NC A/B/C
   - Implementar anulación de facturas

---

## 🎉 Estado Actual

✅ **COMPLETAMENTE FUNCIONAL EN MODO DEBUG**

- Advertencias del servidor: **RESUELTAS**
- Integración POS: **IMPLEMENTADA**
- Emisión de CAE simulado: **FUNCIONANDO**
- Modal de comprobante: **IMPLEMENTADO**
- Base de datos: **MIGRADA**
- Metadatos AFIP: **CARGADOS**

**¡Listo para probar!** 🚀
