# Sistema de Facturación - Resumen de Funcionalidades

## 📋 Descripción General

Sistema de punto de venta (POS) y facturación electrónica construido con Django 5.2, integrado con ARCA (ex-afip) para emisión de comprobantes fiscales en Argentina.

**Stack Tecnológico:**
- Gestión de paquetes: uv (python dependencies), pnpm (JavaScript dependencies).
- Runner de comandos: Just
- Backend: Django 5.2 + Python 3.13+
- Frontend: HTMX + Alpine.js + Tailwind CSS v4 + Flowbite
- Base de datos: SQLite con modo WAL
- Dependencias clave: django-afip, ReportLab

## Development Philosophy

**Target Audience:** This project is designed as a learning resource for Django development.

**Core Principles:**
- **ORM-First Approach:** All database interactions MUST use Django's ORM (`MyModel.objects...`). Never write raw SQL in views or services.
- **Clean & Pedagogical Code:** Code should be "Pythonic", readable, and serve as a teaching example.
- **Modular Architecture:** Business logic separated into distinct apps with clear responsibilities.
- **Design Patterns:** Apply Gang of Four design patterns where appropriate.
- **Service Layer Pattern:** Business logic lives in `services.py` files, not in views or models.
- **Transaction Safety:** Use `transaction.atomic()` for operations that modify multiple records.
**Settings Path Resolution:**
- Apps are added to Python path via `sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))`
- This allows importing apps directly: `import users` instead of `from apps import users`
- Apps are registered in INSTALLED_APPS as `'users'`, `'sale'`, etc.

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

#### 5. **invoices/** - Facturación Electrónica
- **Modelos**:
  - `Invoice` - Factura local (historial inmutable)
  - `VATAliquot` - Alícuotas de IVA (solo Factura A)
- **Servicios**: `InvoiceService` (ver sección AFIP)

---

### Directory Structure

- `src/` - Django project root
  - `core/` - Project settings, main URLs, WSGI/ASGI config
  - `apps/` - Django applications (modular architecture)
    - `users/` - Custom user model (extends AbstractUser)
    - `sale/` - Sales module
      - Models: `Sale`, `SaleLineItem`
      - Business logic in `services.py`
    - `payments/` - Payment processing module
      - Models: `PaymentMethod`, `Transaction`
      - Business logic in `services.py`
  - `manage.py` - Django management script
  - `db.sqlite3` - SQLite database (WAL mode enabled)

- `templates/` - Django templates (global)
  - `sale/` - sale App templates
  - `products/` - products App templates
  - `base.html` - Base template with navbar, HTMX, Flowbite integration

- `static/` - Static assets
  - `css/` - Tailwind CSS files
    - `input.css` - Source CSS (imports Tailwind + Flowbite plugin)
    - `output.css` - Compiled CSS (build artifact)
  - `js/` - JavaScript libraries
    - `htmx.min.js` - HTMX for dynamic interactions
    - `flowbite.min.js` - Flowbite components

- `documentation/` - PlantUML diagrams and technical docs





### Backend Code Organization Patterns

**Service Layer Pattern:**
- Business logic lives in `services.py` files within each app
- Views should be thin - they only handle request/response
- Services use `transaction.atomic()` for database operations
- All database access uses Django ORM exclusively

**Example Service Structure:**
```python
# apps/sale/services.py
from django.db import transaction

class SaleService:
    @transaction.atomic
    def create_sale(self, user, items):
        # Business logic using Django ORM
        sale = Sale.objects.create(...)
        for item in items:
            SaleLineItem.objects.create(sale=sale, ...)
        return sale
```

**Design Patterns:**
- Apply Gang of Four patterns where beneficial
- Service Layer for business logic
- Repository pattern implicit through Django ORM
- Consider Factory, Strategy, or Observer patterns as needed

**ORM Best Practices:**
- Use `select_related()` and `prefetch_related()` to optimize queries
- Use `F()` expressions for atomic updates
- Use `Q()` objects for complex queries
- Always use `transaction.atomic()` for multi-model operations
- Never write raw SQL - use ORM query methods

## 💻 Interfaz POS (Point of Sale)

### Template: `templates/sale/pos_index.html`

Interface standalone de una sola página optimizada para cajeros, construida con **Alpine.js**.

### Flujo de Venta Completo

#### Fase 0: Identificación de Cliente (Opcional)
- **Sin cliente**: Venta rápida → genera Ticket
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

### Frontend Development Pattern

This project uses a minimal JavaScript approach:
- HTMX handles dynamic interactions for server-driven UIs
- Alpine.js for client-side reactivity in standalone pages (e.g., POS)
- Flowbite provides pre-built components
- Tailwind handles styling with utility classes
- Write server-side views that return HTML fragments for HTMX to swap

When adding new views that use HTMX, ensure they return partial HTML templates that can be swapped into the page.

### Key config consideration for frontend

**Templates:**
- Global templates in `templates/` (configured via `BASE_DIR.parent / 'templates'`)
- App-specific templates can go in `apps/<app>/templates/`
- Base template includes HTMX CSRF token configuration

**Static Files:**
- Static files served from `static/` directory
- Tailwind v4 uses new CSS import syntax in `input.css`
- Flowbite imported as plugin via `@plugin` directive

**Frontend Stack:**
- Tailwind CSS v4 (CSS-first configuration via `@import`)
- Flowbite components for UI
- HTMX for dynamic interactions without JavaScript
- CSRF token automatically added to HTMX requests in base template
  
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
### Django Management Commands

```bash
# Create superuser
uv run python src/manage.py createsuperuser

# Django shell
uv run python src/manage.py shell

# Run tests
uv run python src/manage.py test
```

### Package Management
```bash
# Python dependencies (via uv)
uv add <package>
uv sync

# JavaScript dependencies (via pnpm)
pnpm add <package>
pnpm install
```

### Code Quality
```bash
# Format and lint Python code
uv run ruff check
uv run ruff format
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

---

**Última actualización**: Enero 2026
**Estado**: ✅ Sistema POS operativo + Integración AFIP completada
