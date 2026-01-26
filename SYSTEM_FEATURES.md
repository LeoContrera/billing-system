# Sistema de Facturación - Resumen de Funcionalidades

## 📋 Descripción General

Sistema de punto de venta (POS) y facturación electrónica construido con Django 6, integrado con AFIP (Administración Federal de Ingresos Públicos) para emisión de comprobantes fiscales en Argentina.

**Stack Tecnológico:**
- Backend: Django 6.0.1 + Python 3.13+
- Frontend: HTMX + Alpine.js + Tailwind CSS v4 + Flowbite
- Base de datos: SQLite con modo WAL
- Dependencias clave: django-afip, ReportLab

---

## 🏗️ Arquitectura del Sistema

### Apps Principales

#### 1. **customers/** - Gestión de Clientes
- **Modelos**: `Customer`
- **Campos clave**:
  - Datos personales: nombre, apellido, email, teléfono
  - Datos fiscales: `tax_id` (CUIT/DNI), `tax_category` (RI/CF/MT/EX)
  - Ubicación: dirección, localidad
- **Servicios**: `CustomerService`
  - `search()` - Búsqueda por nombre o tax_id
  - `get_or_create_quick()` - Creación rápida desde POS
  - `create_customer()` - Creación completa con validaciones
- **Endpoints**:
  - `GET /customers/search/?q=<query>` - Búsqueda HTMX
  - `POST /customers/create/` - Crear cliente

#### 2. **products/** - Catálogo de Productos
- **Modelos**: `Product`
- **Campos clave**:
  - Identificación: `sku` (único), `name`, `description`
  - Precio: `price` (Decimal)
  - IVA: `vat_rate` (21%, 10.5%, 27%, 5%, 2.5%, 0%)
- **Servicios**: `InventoryService`
  - `get_stock_level()` - Consultar stock
  - `adjust_stock()` - Ajustar inventario con registro de movimientos

#### 3. **sale/** - Gestión de Ventas
- **Modelos**:
  - `Sale` - Venta principal
  - `SaleLineItem` - Items de la venta (productos)
- **Campos Sale**:
  - Relaciones: `customer` (FK opcional), `created_by` (FK User)
  - Estado: `status` (PENDING, COMPLETED)
  - Montos: `global_discount_amount`
  - Fechas: `created_at`, `completed_at`
- **Campos SaleLineItem**:
  - `product` (FK), `quantity`, `unit_price`
  - `discount_amount` - Descuento individual por item
  - `vat_rate` - Desnormalizado desde Product
- **Servicios**: `SaleService`
  - `create_sale()` - Factory method
  - `set_customer()` - Asignar cliente
  - `add_line_item()` - Agregar productos
  - `apply_global_discount()` - Descuento global
  - `apply_line_discount()` - Descuento por item
  - `finalize_sale()` - Completar venta (atomic transaction)

#### 4. **payments/** - Procesamiento de Pagos
- **Modelos**:
  - `PaymentMethod` - Métodos de pago (Efectivo, Débito, Crédito, Transferencia)
  - `Transaction` - Registro de pagos
- **Servicios**: `PaymentService`
  - `get_active_payment_methods()` - Listar métodos activos
  - `add_payment()` - Registrar pago con validaciones
- **Fixtures**: 4 métodos de pago precargados

#### 5. **invoices/** - Facturación Electrónica (★ Core)
- **Modelos**:
  - `Invoice` - Factura local (historial inmutable)
  - `VATAliquot` - Alícuotas de IVA (solo Factura A)
- **Servicios**: `InvoiceService` (ver sección AFIP)

---

## 💻 Interfaz POS (Point of Sale)

### Template: `templates/sale/pos_index.html`

Interface standalone de una sola página optimizada para cajeros, construida con **Alpine.js**.

### Flujo de Venta Completo

#### Fase 0: Identificación de Cliente (Opcional)
- **Sin cliente**: Venta rápida → genera Ticket (Factura C)
- **Con cliente**:
  - Búsqueda por nombre o DNI/CUIT
  - Creación rápida con datos básicos
  - Determinación automática del tipo de comprobante según categoría fiscal

#### Fase 1: Productos
- Búsqueda de productos por SKU o nombre
- Entrada de cantidad y precio unitario
- Tabla dinámica con actualización en tiempo real
- Cálculo automático de subtotales

#### Fase 2: Descuentos
- **Descuento Global**: Porcentaje sobre el total de la venta
- **Descuento Unitario**: Por producto individual
- Vista previa de impacto en totales

#### Fase 3: Pagos
- Múltiples métodos de pago soportados
- **Pagos Parciales**: Permite dividir el pago en varios métodos
- **Detalles de Tarjeta** (si aplica):
  - Tipo: VISA, Mastercard, Amex, etc.
  - Cuotas con cálculo de interés compuesto
- Tracking de saldo restante en tiempo real

#### Fase 4: Finalización
- Validación de pago completo (saldo = 0)
- Transacción atómica (todo o nada)
- Cambio de estado a COMPLETED
- **Integración AFIP**: Emisión automática de CAE y envío de email

---

## 📊 Cálculos y Lógica de Negocio

### Cálculo de Totales
```
Subtotal = Σ (quantity × unit_price - discount_amount) de cada line item
Descuento Global = Subtotal × (global_discount_percentage / 100)
Total = Subtotal - Descuento Global
```

### Validaciones
- **Pre-finalización**:
  - ✅ Al menos 1 producto en la venta
  - ✅ Total pagado >= Total de venta
  - ✅ Métodos de pago válidos
- **Finalización**:
  - ✅ Atomic transaction con `@transaction.atomic`
  - ✅ Timestamp de `completed_at`
  - ✅ Estado COMPLETED inmutable

---

## 🎨 Diseño y UX

### Sistema de Diseño

**Tipografía:**
- UI Text: Plus Jakarta Sans (400-800)
- Números/Monospace: IBM Plex Mono (400-700)

**Paleta de Colores:**
- Primary (Azul): `#2563eb` - Acciones principales
- Secondary (Ámbar): `#f59e0b` - Descuentos, advertencias
- Success (Verde): `#10b981` - Pagos completados
- Danger (Rojo): `#ef4444` - Acciones destructivas

**Componentes:**
- Cards con `shadow-float`
- Buttons con estados hover/disabled
- Forms con validación visual
- Modals con overlay y animaciones

### Patrones Alpine.js

**Estado reactivo:**
```javascript
{
  lineItems: [],
  payments: [],
  get subtotal() { return this.lineItems.reduce(...) },
  get total() { return this.subtotal - this.globalDiscount },
  get remaining() { return this.total - this.totalPaid }
}
```

**Formateo de moneda:**
```javascript
formatCurrency(value) {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS'
  }).format(value);
}
```

---

## 🔐 Seguridad

- `@login_required` en todos los endpoints de venta
- CSRF protection (auto-configurado para HTMX)
- `on_delete=PROTECT` previene eliminación accidental de datos
- Validadores a nivel de modelo (MinValueValidator)
- Transaction locks (`select_for_update()`) para prevenir race conditions

---

## 🗄️ Base de Datos

### Configuración
- SQLite con modo **WAL** (Write-Ahead Logging) para mejor concurrencia
- Migraciones Django para control de versiones de schema

### Schema Principal

```
Customer (opcional)
  ├─ id, first_name, last_name
  ├─ tax_id (unique), tax_category
  └─ email, phone, address

Product
  ├─ sku (unique), name, price
  └─ vat_rate (21%, 10.5%, etc.)

Sale
  ├─ customer_id (FK nullable)
  ├─ created_by_id (FK User)
  ├─ status (PENDING/COMPLETED)
  ├─ global_discount_amount
  └─ created_at, completed_at

SaleLineItem
  ├─ sale_id (FK CASCADE)
  ├─ product_id (FK)
  ├─ quantity, unit_price
  ├─ discount_amount
  └─ vat_rate (desnormalizado)

PaymentMethod
  ├─ name, method_type
  └─ is_active

Transaction
  ├─ sale_id (FK)
  ├─ payment_method_id (FK)
  ├─ amount
  └─ created_at, created_by_id
```

---

## 🛠️ Patrones de Diseño Implementados

### Gang of Four Patterns
- **Service Layer Pattern**: Lógica de negocio separada en servicios
- **Factory Method**: `create_sale()`, `create_invoice()`
- **Repository Pattern**: Django ORM (implícito)
- **Strategy Pattern**: Modo DEBUG vs PRODUCTION para AFIP
- **Template Method**: Flujos orquestados con pasos definidos

### Django Best Practices
- **ORM-First**: Zero raw SQL
- **Transaction Safety**: `@transaction.atomic` en operaciones críticas
- **Desnormalización**: Campos como `vat_rate` copiados para historial inmutable
- **Thin Controllers**: Views solo manejan request/response
- **Service Layer**: Business logic en `services.py`

### Optimización ORM
- `select_related()` - Eager loading (1-to-1, FK)
- `prefetch_related()` - Eager loading (M2M, reverse FK)
- `select_for_update()` - Pessimistic locking
- `Q()` objects - Consultas complejas
- `F()` expressions - Actualizaciones atómicas

---

## 🚀 Comandos de Desarrollo

### Servidor
```bash
just run
# o
uv run python src/manage.py runserver
```

### CSS (Tailwind)
```bash
just watch-css      # Modo desarrollo
just build-css      # Producción (minificado)
```

### Base de Datos
```bash
uv run python src/manage.py migrate
uv run python src/manage.py makemigrations
uv run python src/manage.py shell
```

### Fixtures
```bash
# Cargar métodos de pago
uv run python src/manage.py loaddata payments/fixtures/initial_payment_methods.json
```

---

## 📝 Datos de Prueba

### Métodos de Pago (Precargados)
- Efectivo (CASH)
- Tarjeta de Débito (DEBIT)
- Tarjeta de Crédito (CREDIT)
- Transferencia (TRANSFER)

### Cliente de Prueba
```python
Customer.objects.create(
    first_name='Juan',
    last_name='Pérez',
    tax_id='20-12345678-9',
    tax_category='CF',  # Consumidor Final
    email='juan@example.com',
    phone='1234567890'
)
```

---

## 🎯 Características Clave

### ✅ Sistema POS Completo
- Interface moderna y responsive
- Workflow de 5 fases optimizado para cajeros
- Soporte para múltiples productos y pagos
- Sistema de descuentos flexible

### ✅ Gestión de Clientes
- Búsqueda rápida
- Creación desde POS
- Datos fiscales completos

### ✅ Control de Inventario
- Productos con SKU único
- Precios y tasas de IVA configurables
- Gestión de stock (en desarrollo)

### ✅ Procesamiento de Pagos
- Múltiples métodos
- Pagos parciales
- Tracking de balance

### ✅ Integración AFIP (Ver documento separado)
- Facturación electrónica A/B/C
- Emisión automática de CAE
- Generación y envío de PDF

---

## 📚 Documentación Relacionada

- **DJANGO_AFIP_INTEGRATION.md**: Detalles de integración con AFIP
- **CLAUDE.md**: Instrucciones completas para desarrollo
- **IMPLEMENTATION_SUMMARY.md**: Resumen de implementación del POS
- **INVOICE_INTEGRATION_TEST.md**: Guía de testing de integración AFIP

---

**Última actualización**: Enero 2026
**Estado**: ✅ Sistema POS operativo + Integración AFIP completada
