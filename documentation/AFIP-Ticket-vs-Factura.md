# Ticket vs Factura - Sistema de Facturación AFIP

## Resumen

Este documento explica la diferencia entre **Ticket** (sin identificación) y **Factura** (con identificación) en el sistema POS, siguiendo la normativa ARCA/AFIP.

## Conceptos Clave

### Ticket (Factura C sin identificación)

- **Uso**: Ventas menores al tope ARCA (aprox. **$190.000**)
- **Identificación**: NO requiere datos del cliente
- **Destinatario**: "Consumidor Final" genérico
- **Email**: No se envía (no hay destinatario)
- **Validez**: Comprobante fiscal válido para la transacción
- **Limitación**: El cliente NO puede usar este comprobante para crédito fiscal

### Factura B (con identificación)

- **Uso**: Cuando el cliente solicita factura con sus datos
- **Identificación**: Requiere nombre, apellido, DNI/CUIT
- **Destinatario**: Cliente específico
- **Email**: Se envía PDF automáticamente
- **Validez**: Comprobante fiscal válido y nominado
- **Limitación**: No genera crédito fiscal IVA (cliente CF/MT/EX)

### Factura A (discrimina IVA)

- **Uso**: Ventas entre Responsables Inscriptos
- **Identificación**: Requiere CUIT obligatorio
- **Destinatario**: Cliente RI específico
- **Email**: Se envía PDF automáticamente
- **Validez**: Comprobante fiscal válido
- **Ventaja**: El cliente PUEDE usar el IVA como crédito fiscal

## Matriz de Decisión (Emisor RI)

```
┌─────────────────────────────────────────────────────────────────┐
│                     EMISOR: RESPONSABLE INSCRIPTO               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┬──────────────────┬─────────────────────────┐
│  CLIENTE         │  IDENTIFICADO    │  COMPROBANTE            │
├──────────────────┼──────────────────┼─────────────────────────┤
│  Sin asignar     │  NO              │  Ticket (Factura C)     │
│  (venta < $190k) │                  │  Sin datos del cliente  │
├──────────────────┼──────────────────┼─────────────────────────┤
│  Consumidor Final│  SÍ (datos)      │  Factura B              │
│  Monotributo     │  DNI/CUIT        │  Con identificación     │
│  Exento          │                  │  (IVA incluido)         │
├──────────────────┼──────────────────┼─────────────────────────┤
│  Responsable     │  SÍ (obligatorio)│  Factura A              │
│  Inscripto       │  CUIT            │  Con identificación     │
│                  │                  │  (IVA discriminado)     │
└──────────────────┴──────────────────┴─────────────────────────┘
```

## Cuándo Usar Cada Opción

### Usar Ticket (Sin Cliente)

✅ **Cuando:**
- Venta menor a $190.000
- Cliente no solicita factura con sus datos
- Compra rápida (café, snack, producto barato)
- Cliente paga y se retira inmediatamente

❌ **NO usar cuando:**
- Cliente necesita crédito fiscal
- Monto supera el tope ARCA
- Cliente solicita factura a su nombre
- Empresa requiere comprobante para contabilidad

### Usar Factura B (Con Cliente CF/MT/EX)

✅ **Cuando:**
- Cliente solicita factura con sus datos
- Monto supera el tope ARCA (~$190k)
- Cliente necesita comprobante para su contabilidad
- Se requiere enviar comprobante por email

❌ **NO usar cuando:**
- Cliente es Responsable Inscripto (debe ser Factura A)
- Venta rápida sin necesidad de identificación

### Usar Factura A (Con Cliente RI)

✅ **Cuando:**
- Cliente es Responsable Inscripto
- Cliente necesita crédito fiscal IVA
- Venta B2B (empresa a empresa)

❌ **NO usar cuando:**
- Cliente NO es Responsable Inscripto
- Cliente no tiene CUIT

## Flujo en el POS

### Opción 1: Venta con Ticket (Rápida)

```
1. Agregar productos al carrito
2. Agregar métodos de pago
3. Finalizar venta (sin asignar cliente)
   ↓
   Sistema genera: TICKET (Factura C)
   ↓
   - CAE obtenido
   - Cliente: "Consumidor Final"
   - PDF disponible para impresión
   - NO se envía email
```

**Pantalla POS muestra**: "Ticket"

### Opción 2: Venta con Factura B (Con Identificación)

```
1. Agregar productos al carrito
2. Buscar o crear cliente:
   - Nombre: Juan Pérez
   - Email: juan@example.com
   - Categoría: Consumidor Final
   - DNI: 12345678
3. Agregar métodos de pago
4. Finalizar venta
   ↓
   Sistema genera: FACTURA B
   ↓
   - CAE obtenido
   - Cliente: "Juan Pérez"
   - PDF generado
   - Email enviado a: juan@example.com
```

**Pantalla POS muestra**: "Factura B"

### Opción 3: Venta con Factura A (B2B)

```
1. Agregar productos al carrito
2. Buscar o crear cliente:
   - Nombre: Empresa SA
   - Email: contabilidad@empresa.com
   - Categoría: Responsable Inscripto
   - CUIT: 30-12345678-9 (obligatorio)
3. Agregar métodos de pago
4. Finalizar venta
   ↓
   Sistema genera: FACTURA A
   ↓
   - CAE obtenido
   - Cliente: "Empresa SA"
   - IVA discriminado en PDF
   - Email enviado a: contabilidad@empresa.com
```

**Pantalla POS muestra**: "Factura A"

## Implementación Técnica

### Backend: `InvoiceService.determine_receipt_type()`

```python
def determine_receipt_type(
    issuer_tax_category: str,
    customer_tax_category: str,
    customer_identified: bool = True
) -> str:
    """
    Determina el tipo de comprobante.

    Parámetros:
        issuer_tax_category: Categoría del emisor (ej: RI)
        customer_tax_category: Categoría del cliente (ej: CF)
        customer_identified: Si hay datos del cliente (True/False)

    Retorna:
        'A', 'B', o 'C'
    """
```

**Lógica:**
- `customer_identified = False` → Ticket (Factura C)
- `customer_identified = True` + `customer = CF/MT/EX` → Factura B
- `customer_identified = True` + `customer = RI` → Factura A

### Frontend: Determinación Reactiva

```javascript
getCurrentReceiptType() {
    if (this.customer.id) {
        // Cliente asignado → usar su categoría
        return this.determineReceiptType(this.customer.taxCategory, true);
    } else if (this.customerMode === 'create') {
        // Vista previa mientras crea cliente
        return this.determineReceiptType(this.newCustomer.taxCategory, true);
    } else {
        // Sin cliente → Ticket
        return this.determineReceiptType(null, false);
    }
}
```

**Resultado en pantalla:**
- Sin cliente: "Ticket"
- Con cliente CF: "Factura B"
- Con cliente RI: "Factura A"

## Tope ARCA ($190.000)

### ¿Qué es el Tope?

Es el monto máximo de venta que permite emitir un Ticket sin identificación del cliente. Este valor es actualizado periódicamente por ARCA/AFIP.

**Valores de referencia (2024-2026):**
- Pagos electrónicos: ~$190.000
- Efectivo: Montos menores

### ¿Qué pasa si se supera el tope?

❌ **NO se puede emitir Ticket**: El sistema debe rechazar la operación o requerir identificación del cliente.

✅ **Solución**: Asignar un cliente con sus datos antes de finalizar la venta.

### Implementación (Futuro)

```python
# Validación de tope (a implementar)
if not sale.customer and sale.total > settings.ARCA_TICKET_LIMIT:
    raise ValidationError(
        f"Ventas mayores a ${settings.ARCA_TICKET_LIMIT} "
        "requieren identificación del cliente"
    )
```

## Preguntas Frecuentes

### ¿Puedo emitir Ticket para cualquier monto?

**No.** Solo para montos menores al tope ARCA (aprox. $190.000). Por encima de este valor, se requiere identificación obligatoria del cliente.

### ¿El Ticket es válido fiscalmente?

**Sí.** El Ticket es un comprobante fiscal válido (Factura C) autorizado por AFIP con CAE.

### ¿Por qué no se envía email en Tickets?

Porque no hay un cliente identificado con email asociado. El Ticket se genera para "Consumidor Final" genérico.

### ¿Puedo convertir un Ticket en Factura después?

**No.** Una vez emitido el CAE, no se puede modificar el comprobante. Si el cliente necesita factura, debe solicitarlo ANTES de finalizar la venta.

### ¿Qué pasa si el cliente pide factura después de emitir el Ticket?

Es necesario:
1. Emitir una Nota de Crédito para anular el Ticket
2. Crear una nueva venta con los datos del cliente
3. Emitir Factura B con identificación

(Esta funcionalidad no está implementada actualmente)

## Referencias

- [Normativa AFIP - Facturación Electrónica](https://www.afip.gob.ar/facturacion/)
- [Resolución General ARCA - Comprobantes](https://www.arca.gob.ar/)
- Documentación interna: `AFIP-Integration-Guide.md`
- Implementación: `AFIP-POS-Implementation.md`

## Cambios en el Sistema

### Antes (Incorrecto)

- Selector manual de tipo de comprobante
- Cliente obligatorio
- Siempre Factura B para Consumidor Final

### Ahora (Correcto)

- ✅ Tipo de comprobante determinado automáticamente
- ✅ Cliente opcional (permite Tickets)
- ✅ Diferencia entre Ticket (sin identificar) y Factura B (identificado)
- ✅ Reactivo: muestra vista previa al seleccionar categoría
- ✅ Cumple con normativa ARCA sobre topes

## Roadmap Futuro

1. **Validación de Tope ARCA**: Rechazar Tickets > $190k sin cliente
2. **Notas de Crédito**: Permitir anular comprobantes
3. **Conversión Ticket → Factura**: Flujo para solicitar factura post-venta
4. **Alertas**: Notificar cuando el monto se acerca al tope
5. **Configuración**: Permitir ajustar el tope desde settings
