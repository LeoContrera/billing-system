# Refactorización de POS App.js

## Problema Identificado

**App.js era un God Object** con 824 líneas y múltiples responsabilidades:
- Gestión de clientes
- Gestión de productos
- Gestión de pagos
- Gestión de descuentos
- Cálculos financieros
- Determinación de tipos de comprobante
- Facturación

**Violación de principios del proyecto:**
- ❌ Lógica de negocio duplicada en frontend (`determineReceiptType()`, `calculateVATBreakdown()`)
- ❌ Violación del principio "Backend-First"
- ❌ Múltiples responsabilidades en un solo archivo
- ❌ Difícil de mantener y testear

## Solución Implementada

### 1. Movimiento de Lógica de Negocio al Backend

**Nuevo endpoint creado:** `/sale/preview-receipt-type/`
- Determina tipo de comprobante (A/B/C/Ticket) según categoría fiscal del cliente
- Única fuente de verdad: `InvoiceService.determine_receipt_type()`
- Frontend solo consume el resultado

**Eliminado del frontend:**
- `determineReceiptType()` - Ahora se obtiene del backend
- `calculateVATBreakdown()` - Ya existe en `InvoiceService.calculate_taxes()`

### 2. Modularización de App.js

**Estructura anterior:**
```
static/js/pos/
└── app.js (824 líneas - God Object)
```

**Estructura nueva:**
```
static/js/pos/
├── modules/
│   ├── calculator-module.js    (90 líneas)  - Cálculos simples
│   ├── customer-module.js      (237 líneas) - Gestión de clientes
│   ├── product-module.js       (159 líneas) - Gestión de productos
│   ├── payment-module.js       (237 líneas) - Gestión de pagos
│   ├── discount-module.js      (134 líneas) - Gestión de descuentos
│   └── invoice-module.js       (118 líneas) - Finalización y facturación
└── app.js                       (270 líneas) - Orquestador
```

**Reducción:** 824 líneas → 270 líneas (67% reducción en archivo principal)

### 3. Módulos Creados

#### calculator-module.js
- **Responsabilidad:** Cálculos aritméticos simples
- **NO contiene lógica de negocio:** Solo suma/resta valores del backend
- Métodos: `calculateSubtotal()`, `calculateTotal()`, `formatCurrency()`

#### customer-module.js
- **Responsabilidad:** Gestión de clientes
- **Delegación al backend:**
  - Búsqueda: `/customers/search/`
  - Asignación: `/sale/set-customer/`
  - Creación: `/customers/create/`
  - Tipo de comprobante: `/sale/preview-receipt-type/` ✨ NUEVO
- Validaciones: Solo UI, backend valida de nuevo

#### product-module.js
- **Responsabilidad:** Gestión de productos
- **Delegación al backend:**
  - Búsqueda: `/products/search/`
  - Stock: `/inventory/check/{sku}/`
  - Agregar: `/sale/add-item/`

#### payment-module.js
- **Responsabilidad:** Gestión de pagos
- **Delegación al backend:**
  - Preview de intereses: `/payments/preview-interest/` (backend genera HTML)
  - Registro: `/payments/add/`
- Sin cálculos de intereses en frontend

#### discount-module.js
- **Responsabilidad:** Gestión de descuentos
- **Delegación al backend:**
  - Descuento global: `/sale/discount-global/`
  - Descuento unitario: `/sale/discount-item/`

#### invoice-module.js
- **Responsabilidad:** Finalización y facturación
- **Delegación al backend:**
  - Finalizar venta: `/sale/finalize/`
  - Procesar AFIP: `/invoices/process-sale/{id}/`
  - PDF: `/invoices/{id}/pdf/`

### 4. App.js como Orquestador

**Responsabilidades exclusivas:**
- ✅ Recibir initialData del backend
- ✅ Crear instancias de módulos
- ✅ Inyectar dependencias (fetchAPI, showSuccess, showError)
- ✅ Componer módulos en un objeto Alpine.js
- ✅ Gestión de loading state
- ✅ Gestión de mensajes (success/error)

**NO contiene:**
- ❌ Lógica de negocio
- ❌ Cálculos complejos
- ❌ Validaciones de negocio
- ❌ Determinación de tipos de comprobante

## Beneficios de la Refactorización

### 1. Cumplimiento de Principios del Proyecto

✅ **Backend-First:** Toda lógica de negocio en Django
✅ **Single Responsibility:** Cada módulo tiene una responsabilidad clara
✅ **DRY:** Lógica de negocio en un solo lugar (backend)

### 2. Mantenibilidad

- **Archivos pequeños:** Cada módulo ~90-240 líneas
- **Cohesión alta:** Cada módulo agrupa funcionalidad relacionada
- **Acoplamiento bajo:** Módulos se comunican vía dependencias inyectadas
- **Fácil de testear:** Cada módulo es independiente

### 3. Escalabilidad

- **Agregar features:** Solo modificar módulo relevante
- **Reusar módulos:** Pueden usarse en otras páginas
- **Paralelizar desarrollo:** Equipos pueden trabajar en módulos diferentes

### 4. Única Fuente de Verdad

- **Tipo de comprobante:** `InvoiceService.determine_receipt_type()`
- **Cálculos de IVA:** `InvoiceService.calculate_taxes()`
- **Validaciones:** Todas en servicios Django
- **Frontend:** Solo consume y muestra datos

## Archivos Modificados

### Backend
- ✅ `src/apps/sale/views.py` - Agregado `preview_receipt_type()`
- ✅ `src/apps/sale/urls.py` - Agregada ruta `/preview-receipt-type/`

### Frontend
- ✅ `static/js/pos/app.js` - Refactorizado como orquestador (824→270 líneas)
- ✅ `static/js/pos/modules/calculator-module.js` - Creado
- ✅ `static/js/pos/modules/customer-module.js` - Creado
- ✅ `static/js/pos/modules/product-module.js` - Creado
- ✅ `static/js/pos/modules/payment-module.js` - Creado
- ✅ `static/js/pos/modules/discount-module.js` - Creado
- ✅ `static/js/pos/modules/invoice-module.js` - Creado

### Templates
- ✅ `templates/sale/pos_index.html` - Actualizado para cargar módulos

## Próximos Pasos (Opcional)

1. **Testing:** Agregar tests unitarios para cada módulo
2. **Endpoints faltantes:**
   - `/sale/remove-item/{id}/` - Eliminar línea de venta
   - `/payments/delete/{id}/` - Eliminar pago
3. **Optimización:** Lazy loading de módulos si es necesario
4. **Documentación:** JSDoc para cada módulo

## Comandos para Probar

```bash
# Iniciar servidor
just run

# Acceder al POS
# http://localhost:8000/sale/pos/

# Verificar que no hay errores en consola del navegador
# Probar flujo completo: agregar cliente, productos, pagos, finalizar
```

## Notas Técnicas

### Patrón de Inyección de Dependencias

Cada módulo es una función factory que acepta dependencias:

```javascript
function createCustomerModule({ saleId, csrfToken, fetchAPI, showSuccess, showError }) {
    return {
        // propiedades y métodos
    };
}
```

**Beneficios:**
- Testeable (puedes inyectar mocks)
- Desacoplado (no depende de globals)
- Explícito (dependencias visibles en firma)

### Composición en App.js

```javascript
const customer = createCustomerModule({ ... });
const product = createProductModule({ ... });

return {
    // Exponer propiedades de módulos
    customer: customer.customer,
    searchCustomers: customer.searchCustomers.bind(customer),
    // ...
};
```

**Alpine.js puede acceder a todo vía `this` en la template.**

---

**Refactorización completada el:** 2026-01-31
**Tiempo estimado de desarrollo:** ~2 horas
**Líneas de código refactorizadas:** ~1200
**Archivos creados:** 7
**Archivos modificados:** 3
