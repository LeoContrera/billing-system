# Implementación de Integración AFIP en POS

## Resumen de Cambios

Se ha implementado la integración completa con AFIP en el sistema POS siguiendo la arquitectura definida en `AFIP-Integration-Guide.md`.

## Cambios Implementados

### 1. Frontend - POS Interface (`templates/sale/pos_index.html`)

#### Eliminación del Selector Manual de Tipo de Comprobante
- **Antes**: El cajero seleccionaba manualmente el tipo de comprobante (Ticket, Factura A/B/C)
- **Ahora**: El tipo de comprobante se determina automáticamente según la matriz AFIP:
  - **Emisor RI + Cliente RI** → Factura A
  - **Emisor RI + Cliente MT/CF/EX** → Factura B
  - **Emisor MT/CF/EX** → Factura C (siempre)

#### Nuevo Formulario de Cliente con Categoría Fiscal
Se agregó al formulario de creación de cliente:
- **Selector de Categoría Tributaria**: CF (Consumidor Final), RI (Responsable Inscripto), MT (Monotributo), EX (Exento)
- **Campo Email**: Obligatorio para el envío automático del comprobante electrónico
- **Validaciones**:
  - Email obligatorio con formato válido
  - CUIT obligatorio para RI y MT
  - DNI opcional para CF y EX

#### Flujo de Finalización de Venta Simplificado
Se reemplazó el flujo de 3 pasos por una llamada única al orquestador:
- **Antes**:
  1. POST `/sale/finalize/`
  2. POST `/invoices/create/<sale_id>/`
  3. POST `/invoices/<invoice_id>/emit-cae/`
- **Ahora**:
  1. POST `/sale/finalize/`
  2. POST `/invoices/process-sale/<sale_id>/` (orquestador completo)

El orquestador ejecuta automáticamente:
- Creación de Invoice
- Emisión de CAE (AFIP o simulado en DEBUG)
- Generación de PDF
- Envío de email al cliente

#### Modal de Éxito Mejorado
Ahora muestra:
- Tipo de comprobante generado
- CAE (Código de Autorización Electrónica)
- Vencimiento del CAE
- Número de comprobante (formato: 0001-00000123)
- Estado de envío de email:
  - ✓ Enviado (verde)
  - No enviado (ámbar con mensaje de error si aplicable)
- Total del comprobante

### 2. Backend - Customer Service (`src/apps/customers/services.py`)

#### Método `create_customer()` Actualizado
Se agregó el parámetro `email`:
```python
def create_customer(
    first_name: str,
    last_name: str,
    email: str = '',  # NUEVO
    phone: str = '',
    locality: str = '',
    address: str = '',
    tax_category: str = TaxCategory.CONSUMIDOR_FINAL,
    tax_id: str = ''
) -> Customer:
```

### 3. Backend - Customer Views (`src/apps/customers/views.py`)

#### Endpoint `POST /customers/create/` Actualizado
Ahora acepta y procesa el campo `email`:
- Parámetro POST: `email` (string)
- Retorna en respuesta JSON: `customer.email`

## Flujo Completo de Facturación

### Caso A: Venta con Ticket (Sin Identificación)

**Escenario**: Compra menor a $190.000, cliente no requiere factura identificada.

1. **Agregar productos** sin asignar cliente
2. **Registrar pagos** hasta cubrir el total
3. **Finalizar venta**:
   - Sistema genera **Ticket** (Factura C)
   - CAE se emite sin datos del cliente
   - No se envía email (no hay destinatario)
   - Comprobante disponible para impresión

**Tipo de comprobante mostrado**: "Ticket"

### Caso B: Venta con Factura Identificada

**Escenario**: Cliente requiere factura con sus datos (monto alto, necesita crédito fiscal, etc.)

### Paso 1: Asignar Cliente (Obligatorio para Factura)
El cajero puede:
1. **Buscar cliente existente**: Busca por nombre o DNI
2. **Crear nuevo cliente**: Completa formulario con:
   - Nombre, Apellido (obligatorios)
   - Email (obligatorio para AFIP)
   - Categoría Tributaria (CF, RI, MT, EX)
   - DNI/CUIT (obligatorio para RI/MT)
   - Teléfono, Localidad, Dirección (opcionales)

El sistema determina automáticamente el tipo de comprobante según:
- Categoría fiscal del emisor (configurado: RI)
- Categoría fiscal del cliente (seleccionada en formulario)

### Paso 2: Agregar Productos
Sin cambios. El cajero agrega productos normalmente.

### Paso 3: Registrar Pagos
Sin cambios. El cajero registra métodos de pago hasta cubrir el total.

### Paso 4: Finalizar Venta (AFIP Integrado)
Al presionar "Finalizar Venta":
1. Se finaliza la venta (marca como COMPLETED)
2. Se ejecuta el orquestador AFIP:
   - Crea Invoice con montos calculados
   - Determina tipo de comprobante automáticamente
   - Emite CAE (AFIP real o simulado según modo)
   - Genera PDF del comprobante
   - Envía email al cliente con PDF adjunto
3. Se muestra modal de éxito con datos del comprobante

## Matriz de Determinación de Comprobante

| Emisor | Cliente | Identificado | Comprobante | Notas |
|--------|---------|--------------|-------------|-------|
| RI     | Sin cliente | No | Ticket (Factura C) | Venta < tope ARCA (~$190k) |
| RI     | CF/MT/EX | Sí | Factura B | Cliente con datos completos |
| RI     | RI | Sí (obligatorio) | Factura A | CUIT obligatorio |
| MT/CF/EX | * | * | Factura C | Siempre |

### Notas Importantes:

1. **Ticket vs Factura C**: Un "Ticket" es técnicamente una Factura C, pero sin identificación del cliente.

2. **Tope ARCA**: Para ventas menores a ~$190.000 (valor actualizado periódicamente por ARCA), no es necesario identificar al cliente. Por encima de este monto, la identificación es obligatoria.

3. **Identificación Obligatoria**: Para clientes Responsables Inscriptos, siempre se requiere CUIT sin importar el monto.

4. **Cliente Opcional**: El sistema permite procesar ventas sin asignar un cliente específico, emitiendo un Ticket genérico.

## Modos de Operación

### Modo DEBUG (`AFIP_DEBUG_MODE=True`)
- **CAE simulado**: "SIM" + timestamp
- **No contacta AFIP**: Ideal para desarrollo
- **PDF básico**: Generado con ReportLab
- **Email**: Impreso en consola (console backend)

### Modo PRODUCTION (`AFIP_DEBUG_MODE=False`)
- **CAE real**: Obtenido desde AFIP WSFE
- **Requiere**:
  - Certificados SSL AFIP (.crt y .key)
  - TaxPayer configurado en Django Admin
  - Punto de Venta activo
- **PDF oficial**: Layout AFIP via django-afip
- **Email**: Enviado via SMTP configurado

## Validaciones Implementadas

### Frontend (JavaScript)
- Email con formato válido (regex)
- CUIT obligatorio para RI y MT
- Nombre y apellido no vacíos
- Total de venta > 0 con balance cubierto

### Backend (Django)
- Sale en estado COMPLETED
- Sale sin factura previa
- Cliente con email registrado
- Categoría fiscal válida

## Manejo de Errores

### Email Fallido
**Comportamiento especial**: Si el email falla después de obtener el CAE:
- ✅ El CAE ya está autorizado en AFIP (NO se puede deshacer)
- ✅ La factura se marca como AUTHORIZED
- ⚠️ Se retorna `email_sent: false` con mensaje de error
- ⚠️ Se loguea advertencia en servidor
- ✅ El modal de éxito muestra "Email no enviado"

**Solución**: Reenviar manualmente o configurar tarea asíncrona.

### AFIP Rechaza
- Factura se marca como REJECTED
- Se retorna error al frontend
- Usuario recibe mensaje de error específico
- No se muestra modal de éxito

### Cliente sin Email
- Advertencia en modal de éxito
- CAE ya autorizado (no se deshace)
- Opción de imprimir comprobante

## Testing

### Modo DEBUG - Test Rápido
```bash
# 1. Iniciar servidor
just run

# 2. Crear venta en POS
# URL: http://localhost:8000/sale/pos/

# 3. Crear cliente con email
# - Categoría: Consumidor Final
# - Email: test@ejemplo.com

# 4. Agregar productos y pagos

# 5. Finalizar venta
# - Verifica CAE simulado (SIM...)
# - Verifica tipo comprobante (Factura B)
# - Verifica email en consola del servidor
```

### Verificación Manual
```python
# Django shell
uv run python src/manage.py shell

from invoices.models import Invoice
from sale.models import Sale

# Ver última factura
invoice = Invoice.objects.last()
print(f"CAE: {invoice.cae}")
print(f"Tipo: {invoice.get_receipt_type_display()}")
print(f"Total: {invoice.total_amount}")
print(f"Autorizada: {invoice.is_authorized}")
```

## Endpoints Utilizados

### Nuevos
- `POST /invoices/process-sale/<sale_id>/` - Orquestador completo

### Existentes (no modificados)
- `GET /customers/search/?q=<query>` - Búsqueda de clientes
- `POST /customers/create/` - Crear cliente (actualizado con email)
- `POST /sale/finalize/` - Finalizar venta
- `POST /sale/set-customer/` - Asignar cliente a venta

## Archivos Modificados

### Frontend
- `templates/sale/pos_index.html` - Interface completa del POS

### Backend
- `src/apps/customers/services.py` - Agregado email a create_customer()
- `src/apps/customers/views.py` - Actualizado endpoint create_customer

### Documentación
- `documentation/AFIP-POS-Implementation.md` - Este archivo

## Próximos Pasos (Futuras Mejoras)

1. **Validación en tiempo real** de CUIT con AFIP
2. **Impresión automática** de comprobante
3. **Reenvío de email** desde interfaz de administración
4. **Tarea asíncrona** (Celery) para envío de emails
5. **Visualización de PDF** en modal antes de finalizar
6. **Historial de comprobantes** emitidos
7. **Anulación de comprobantes** (Notas de Crédito)

## Referencias

- Guía completa: `documentation/AFIP-Integration-Guide.md`
- Arquitectura del sistema: `CLAUDE.md`
- Modelos de Invoice: `src/apps/invoices/models.py`
- Servicios AFIP: `src/apps/invoices/services.py`
