# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A billing system built with Django 6, Tailwind CSS v4, Flowbite, and HTMX. Uses Python 3.13+ with uv for dependency management and pnpm for JavaScript dependencies.

## Development Philosophy

**Target Audience:** This project is designed as a learning resource for Django development.

**Core Principles:**
- **ORM-First Approach:** All database interactions MUST use Django's ORM (`MyModel.objects...`). Never write raw SQL in views or services.
- **Clean & Pedagogical Code:** Code should be "Pythonic", readable, and serve as a teaching example.
- **Modular Architecture:** Business logic separated into distinct apps with clear responsibilities.
- **Design Patterns:** Apply Gang of Four design patterns where appropriate.
- **Service Layer Pattern:** Business logic lives in `services.py` files, not in views or models.
- **Transaction Safety:** Use `transaction.atomic()` for operations that modify multiple records.

## Development Commands

### Running the Development Server
```bash
just run
# or directly:
uv run python src/manage.py runserver
```

### CSS Development
```bash
# Watch mode (during development)
just watch-css

# Build for production (minified)
just build-css
```

### Django Management Commands
```bash
# Run migrations
uv run python src/manage.py migrate

# Create migrations
uv run python src/manage.py makemigrations

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

## Architecture

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
  - `base.html` - Base template with navbar, HTMX, Flowbite integration

- `static/` - Static assets
  - `css/` - Tailwind CSS files
    - `input.css` - Source CSS (imports Tailwind + Flowbite plugin)
    - `output.css` - Compiled CSS (build artifact)
  - `js/` - JavaScript libraries
    - `htmx.min.js` - HTMX for dynamic interactions
    - `flowbite.min.js` - Flowbite components

- `documentation/` - PlantUML diagrams and technical docs

### Key Configuration Details

**Settings Path Resolution:**
- Apps are added to Python path via `sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))`
- This allows importing apps directly: `import users` instead of `from apps import users`
- Apps are registered in INSTALLED_APPS as `'users'`, `'sale'`, etc.

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

**Database:**
- SQLite for development (located at `src/db.sqlite3`)
- WAL mode (`PRAGMA journal_mode = WAL`) configured automatically via signal in `apps.py` or `db.py`
- This configuration is abstracted - interact with database only through Django ORM
- Custom User model: `users.User` (extends Django's AbstractUser)

### Code Organization Patterns

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

### Frontend Development Pattern

This project uses a minimal JavaScript approach:
- HTMX handles dynamic interactions for server-driven UIs
- Alpine.js for client-side reactivity in standalone pages (e.g., POS)
- Flowbite provides pre-built components
- Tailwind handles styling with utility classes
- Write server-side views that return HTML fragments for HTMX to swap

When adding new views that use HTMX, ensure they return partial HTML templates that can be swapped into the page.

## Design System

### Typography

**Font Stack:**
- **Headings & UI Text**: `Plus Jakarta Sans` (Google Fonts)
  - Modern, geometric sans-serif
  - Weights: 400 (Regular), 500 (Medium), 600 (Semi-Bold), 700 (Bold), 800 (Extra Bold)
- **Numbers & Monospace**: `IBM Plex Mono` (Google Fonts)
  - Perfect for financial data, SKUs, prices
  - Weights: 400 (Regular), 600 (Semi-Bold), 700 (Bold)
  - Use `font-mono` class with `font-variant-numeric: tabular-nums` for aligned columns

**Usage Guidelines:**
```html
<!-- Headings -->
<h1 class="text-3xl font-black">Title</h1>

<!-- Body text -->
<p class="text-sm font-medium text-gray-700">Regular text</p>

<!-- Financial/numeric data -->
<span class="font-mono text-lg font-bold">$123.456,78</span>

<!-- SKU codes -->
<span class="font-mono text-sm text-amber-600">ABC123</span>
```

### Color Palette (Light Theme)

**CSS Custom Properties:**
```css
:root {
    --primary: #2563eb;        /* Blue 600 - Primary actions */
    --primary-dark: #1d4ed8;   /* Blue 700 - Hover states */
    --secondary: #f59e0b;      /* Amber 500 - Secondary/Warning */
    --secondary-dark: #d97706; /* Amber 600 - Hover states */
    --success: #10b981;        /* Emerald 500 - Success states */
    --danger: #ef4444;         /* Red 500 - Destructive actions */

    /* Neutral grays */
    --gray-50: #f9fafb;
    --gray-100: #f3f4f6;
    --gray-200: #e5e7eb;
    --gray-300: #d1d5db;
    --gray-400: #9ca3af;
    --gray-500: #6b7280;
    --gray-700: #374151;
    --gray-900: #111827;
}
```

**Color Usage:**
- **Primary (Blue)**: Main CTAs, important highlights, section headers
- **Secondary (Amber)**: Discounts, warnings, financial highlights
- **Success (Green)**: Completed payments, success states, positive values
- **Danger (Red)**: Delete actions, errors, negative states
- **Gray Scale**: Text hierarchy, borders, backgrounds

**Examples:**
```html
<!-- Primary button -->
<button class="bg-blue-600 hover:bg-blue-700 text-white">Action</button>

<!-- Success indicator -->
<span class="text-green-600 font-semibold">✓ Pagado</span>

<!-- Discount badge -->
<span class="text-amber-600 bg-amber-50 border-amber-200">Descuento</span>

<!-- Danger action -->
<button class="text-red-600 hover:text-red-700">Eliminar</button>
```

### Component Library

**1. Cards (`card` class):**
```html
<section class="card p-6 shadow-float">
    <!-- Content -->
</section>

<!-- Styles -->
.card {
    background: white;
    border: 1px solid var(--gray-200);
    border-radius: 12px;
}
```

**2. Buttons:**
```html
<!-- Primary -->
<button class="btn py-3 px-6 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold">
    Primary Action
</button>

<!-- Secondary -->
<button class="btn py-3 px-6 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50">
    Secondary
</button>

<!-- Destructive -->
<button class="btn py-3 px-6 bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold">
    Delete
</button>

<!-- Disabled state -->
<button class="btn py-3 px-6 bg-gray-300 text-gray-500 rounded-lg font-semibold cursor-not-allowed" disabled>
    Disabled
</button>
```

**3. Form Inputs:**
```html
<!-- Text input -->
<div>
    <label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
        Label
    </label>
    <input
        type="text"
        class="w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm transition-all text-gray-900"
        placeholder="Placeholder">
</div>

<!-- Select -->
<select class="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 text-sm text-gray-900">
    <option>Option</option>
</select>

<!-- Number input with prefix -->
<div class="relative">
    <span class="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-mono font-semibold">$</span>
    <input
        type="number"
        class="w-full bg-white border border-gray-300 rounded-lg px-4 py-3 pl-8 text-sm font-mono text-gray-900"
        placeholder="0.00">
</div>
```

**4. Tables:**
```html
<div class="overflow-x-auto">
    <table class="w-full">
        <thead>
            <tr class="table-header">
                <th class="px-6 py-4 text-left text-xs font-bold uppercase tracking-wider text-gray-700">
                    Header
                </th>
            </tr>
        </thead>
        <tbody class="bg-white">
            <tr class="table-row">
                <td class="px-6 py-4">Content</td>
            </tr>
        </tbody>
    </table>
</div>

<!-- Styles -->
.table-header {
    background: var(--gray-100);
    border-bottom: 2px solid var(--primary);
}

.table-row {
    border-bottom: 1px solid var(--gray-200);
    transition: background 0.15s;
}

.table-row:hover {
    background: var(--gray-50);
}
```

**5. Modals:**
```html
<div
    x-show="showModal"
    x-cloak
    @click.self="showModal = false"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    style="display: none;">

    <div class="card p-8 max-w-md w-full animate-slide-in shadow-float-lg" @click.stop>
        <h3 class="text-xl font-bold mb-6 text-blue-600">Modal Title</h3>

        <div class="space-y-4">
            <!-- Modal content -->
        </div>

        <div class="flex gap-3 mt-6">
            <button @click="showModal = false" class="btn flex-1 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold text-sm hover:bg-gray-50">
                Cancelar
            </button>
            <button class="btn flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-sm">
                Confirmar
            </button>
        </div>
    </div>
</div>
```

**6. Badges & Pills:**
```html
<!-- Status badge -->
<span class="text-xs px-3 py-1 rounded-full bg-gray-100 text-gray-600 border border-gray-200">
    Status
</span>

<!-- Success badge -->
<span class="text-xs px-3 py-1 rounded-full bg-green-100 text-green-700 border border-green-200 font-medium">
    ✓ Success
</span>

<!-- Warning badge -->
<span class="text-xs px-3 py-1 rounded-full bg-amber-100 text-amber-700 border border-amber-200 font-medium">
    Warning
</span>
```

**7. Shadow System:**
```css
.shadow-float {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.shadow-float-lg {
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}
```

### Animation System

**Slide-in animation:**
```css
@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-slide-in {
    animation: slideIn 0.3s ease-out;
}
```

**Button hover effects:**
```css
.btn {
    font-weight: 600;
    letter-spacing: 0.025em;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn:hover:not(:disabled) {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.btn:active:not(:disabled) {
    transform: translateY(0);
}
```

### Alpine.js Patterns (for Reactive UIs)

**State Management:**
```javascript
function appComponent() {
    return {
        // State
        items: [],
        showModal: false,

        // Computed properties
        get total() {
            return this.items.reduce((sum, item) => sum + item.subtotal, 0);
        },

        // Methods
        addItem(item) {
            this.items.push(item);
        },

        removeItem(index) {
            this.items.splice(index, 1);
        },

        // Currency formatting
        formatCurrency(value) {
            return new Intl.NumberFormat('es-AR', {
                style: 'currency',
                currency: 'ARS',
                minimumFractionDigits: 2
            }).format(value);
        }
    }
}
```

**Conditional Rendering:**
```html
<!-- Show/hide -->
<div x-show="condition" class="animate-slide-in">Content</div>

<!-- Conditional classes -->
<button :class="isActive ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'">
    Toggle
</button>

<!-- Disabled state -->
<button :disabled="!canSubmit()">Submit</button>
```

**Form Validation Pattern:**
```javascript
isFormValid() {
    const amount = parseFloat(this.formData.amount) || 0;
    if (amount <= 0) return false;

    // Additional validations
    if (this.requiresCard && !this.formData.cardType) {
        return false;
    }

    return true;
}
```

### UX Patterns

**1. Modal Workflows:**
- Always provide Cancel + Confirm buttons
- Confirm button on the right (primary position)
- Cancel resets form state
- Use `x-cloak` to prevent flash of unstyled content
- Click outside modal to close (`@click.self`)

**2. Form Input States:**
```css
input:focus, textarea:focus, select:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}
```

**3. Disabled States:**
```html
<button
    :disabled="!canProceed()"
    :class="canProceed() ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-300 text-gray-500 cursor-not-allowed'"
    class="btn">
    Action
</button>
```

**4. Empty States:**
```html
<div x-show="items.length === 0" class="text-center py-12 text-gray-500 text-sm">
    No hay items para mostrar
</div>
```

**5. Loading States (future):**
```html
<button class="btn" :disabled="isLoading">
    <span x-show="!isLoading">Guardar</span>
    <span x-show="isLoading">Guardando...</span>
</button>
```

### Financial Data Display

**Currency Formatting:**
```javascript
// Always use Intl.NumberFormat for consistency
formatCurrency(value) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2
    }).format(value);
}
```

**Visual Hierarchy for Amounts:**
```html
<!-- Large total -->
<div class="font-mono text-5xl font-black text-gray-900">
    $ 1.234.567,89
</div>

<!-- Medium subtotal -->
<span class="font-mono text-base font-bold text-gray-900">
    $ 123.456,78
</span>

<!-- Small supporting amount -->
<span class="font-mono text-sm text-gray-700">
    $ 12.345,67
</span>

<!-- Positive/success amount -->
<span class="font-mono text-lg font-bold text-green-600">
    $ 100.000,00
</span>

<!-- Discount/warning amount -->
<span class="font-mono text-sm font-semibold text-amber-600">
    -$ 5.000,00
</span>
```

### Responsive Design

**Mobile-first approach:**
```html
<!-- Stack on mobile, side-by-side on desktop -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <div>Column 1</div>
    <div>Column 2</div>
</div>

<!-- Hide on mobile -->
<div class="hidden md:block">Desktop only</div>

<!-- Full width on mobile, fixed width on desktop -->
<div class="w-full md:w-96">Content</div>
```

### Accessibility Guidelines

- Use semantic HTML elements
- Provide descriptive labels for all form inputs
- Use `aria-label` for icon-only buttons
- Ensure sufficient color contrast (WCAG AA minimum)
- Keyboard navigation support (tab order)
- Focus states must be visible

## POS System Architecture

This is a local Point of Sale (POS) system with the following modular structure:

**App: `sale`**
- Handles sales transactions and line items
- Models: `Sale`, `SaleLineItem`
- Contains sale creation, modification, and finalization logic
- **Views**:
  - `pos_index`: Standalone POS interface (Alpine.js-powered)
  - `create_sale`: HTMX-based sale creation (admin interface)

**App: `payments`**
- Manages payment methods and transactions
- Models: `PaymentMethod`, `Transaction`
- Handles payment processing and tracking
- **Services**:
  - `PaymentService.add_payment()`: Registers payments with validation
  - `PaymentService.get_active_payment_methods()`: Returns active payment options

**App: `customers`**
- Customer management
- Models: `Customer`
- Used for optional customer assignment in sales

### POS Interface Features

**Reference Implementation:** `templates/sale/pos_index.html`

The POS is a standalone, single-page application optimized for cashier workflows:

**Key Features:**
1. **Receipt Type Selection**: Ticket Común, Factura A/B/C
2. **Customer Assignment** (optional): Name, surname, phone
3. **Product Line Items**:
   - SKU, description, quantity, unit price
   - Individual discounts (percentage-based)
   - Real-time subtotal calculation
4. **Discount System**:
   - **Global Discount**: Apply percentage to entire sale
   - **Unit Discount**: Select products + apply percentage
5. **Payment Processing**:
   - Multiple payment methods (Cash, Debit, Credit, Transfer)
   - **Card Details**: Type (VISA, Mastercard, etc.), installments, interest rate
   - Automatic interest calculation for credit cards
   - Real-time balance tracking
6. **Sale Finalization**:
   - Validates full payment
   - Resets interface for next sale

**State Management (Alpine.js):**
```javascript
{
    receiptType: 'Ticket Común',
    customer: { firstName, lastName, phone },
    lineItems: [{ sku, description, quantity, unitPrice, discountAmount }],
    globalDiscountPercentage: 0,
    payments: [{ method, amount, totalAmount, cardType, installments, interestRate }],
    // ... computed properties and methods
}
```

**Calculation Logic:**
```javascript
// Subtotal = Sum of all line items (after item discounts)
subtotal = lineItems.reduce((sum, item) => sum + item.subtotal, 0)

// Global discount applied to subtotal
globalDiscount = subtotal * (globalDiscountPercentage / 100)

// Total
total = subtotal - globalDiscount

// Total paid (uses base amount, not amount + interest)
totalPaid = payments.reduce((sum, p) => sum + p.amount, 0)

// Remaining balance
remaining = total - totalPaid

// Can finalize when: items exist AND remaining <= 0
canFinalize = lineItems.length > 0 && remaining <= 0
```

**Interest Calculation (Credit Cards):**
```javascript
// Compound interest formula
totalAmount = amount * Math.pow(1 + (interestRate / 100), installments)

// Example: $100,000 at 5% monthly for 6 installments
// Total: $134,009.56
// Each installment: $22,334.93
```

**Key Implementation Guidelines:**
1. **Strict ORM Usage:** All database operations must use Django ORM methods
2. **Service Layer:** Implement business logic in `services.py` files
3. **Atomic Transactions:** Wrap multi-step operations in `transaction.atomic()`
4. **No Raw SQL:** Database configuration (like WAL mode) is abstracted; application code uses only ORM
5. **Educational Focus:** Code should demonstrate Django best practices
6. **UI Consistency**: Follow the Design System documented above for all new interfaces

**Transaction Safety Example:**
```python
from django.db import transaction

@transaction.atomic
def process_payment(sale, amount, method):
    # Multiple database operations guaranteed to succeed or fail together
    transaction = Transaction.objects.create(...)
    remaining = calculate_remaining(sale)
    if remaining == 0:
        sale.status = 'PAID'
        sale.save()
        update_inventory(sale)
    return remaining
```

### POS UX Patterns

**Modal Workflows:**
1. **Payment Modal**:
   - Conditional fields based on payment method
   - Real-time interest preview for credit cards
   - Pre-fill amount with remaining balance
   - Validation before submission

2. **Discount Modals**:
   - Global: Input percentage, show calculated amount
   - Unit: Select products (checkboxes) + percentage
   - Visual feedback on selected items

**Visual Feedback:**
- Disabled states for unavailable actions
- Success indicators (green) for completed payments
- Warning indicators (amber) for discounts
- Error indicators (red) for deletions
- Real-time balance updates

**Data Persistence Pattern:**
```javascript
// Frontend state (Alpine.js)
lineItems: [{ discountAmount: 5000 }]

// Backend persistence (Django)
SaleLineItem.objects.create(
    sale=sale,
    discount_amount=5000  # Stored in database
)
```

## Replicating Design Across Apps

### Creating Reusable Components

**Option 1: Django Template Includes**

Create reusable HTML snippets in `templates/components/`:

```django
{# templates/components/card.html #}
<section class="card p-6 shadow-float">
    {{ content }}
</section>

{# templates/components/modal.html #}
<div
    x-show="show{{ modal_id }}"
    x-cloak
    @click.self="show{{ modal_id }} = false"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
    style="display: none;">
    <div class="card p-8 max-w-md w-full animate-slide-in shadow-float-lg" @click.stop>
        {{ content }}
    </div>
</div>

{# Usage in templates #}
{% include 'components/card.html' with content=sale_info %}
```

**Option 2: CSS Component Classes**

Add to `static/css/input.css`:

```css
/* Button variants */
.btn-primary {
    @apply btn bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold;
}

.btn-secondary {
    @apply btn bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold hover:bg-gray-50;
}

.btn-danger {
    @apply btn bg-red-600 hover:bg-red-700 text-white rounded-lg font-semibold;
}

/* Form input base */
.input-base {
    @apply w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm transition-all text-gray-900;
}

.input-base:focus {
    @apply border-blue-600 ring-4 ring-blue-100;
}
```

**Option 3: Alpine.js Component Library**

Create shared Alpine components in `static/js/components.js`:

```javascript
// Currency formatter (reusable across apps)
window.formatCurrency = function(value) {
    return new Intl.NumberFormat('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2
    }).format(value);
};

// Modal mixin
window.modalMixin = {
    showModal: false,
    openModal() {
        this.showModal = true;
    },
    closeModal() {
        this.showModal = false;
    }
};
```

### Checklist for New App UIs

When creating a new app interface, ensure:

**Design Consistency:**
- [ ] Use Plus Jakarta Sans for UI text
- [ ] Use IBM Plex Mono for numbers/financial data
- [ ] Apply color palette (blue primary, amber secondary, etc.)
- [ ] Use `shadow-float` and `shadow-float-lg` for elevation
- [ ] Apply `card` class for content sections
- [ ] Use `animate-slide-in` for dynamic elements

**Components:**
- [ ] Buttons follow `.btn` + variant pattern
- [ ] Form inputs use consistent styling with focus states
- [ ] Modals use standard structure (title, content, actions)
- [ ] Tables use `table-header` and `table-row` classes
- [ ] Empty states provide helpful messaging

**Interactions:**
- [ ] Loading states for async operations
- [ ] Disabled states with visual feedback
- [ ] Hover states on interactive elements
- [ ] Success/error feedback after actions
- [ ] Confirm dialogs for destructive actions

**Alpine.js (if used):**
- [ ] Clear state management structure
- [ ] Computed properties for derived values
- [ ] Validation functions before submission
- [ ] Proper cleanup on modal close
- [ ] Currency formatting for all monetary values

**Accessibility:**
- [ ] Semantic HTML elements
- [ ] Labels for all form inputs
- [ ] Keyboard navigation support
- [ ] Sufficient color contrast
- [ ] Focus indicators visible

### Example: Creating a New Customer Form

```html
<!-- templates/customers/customer_form.html -->
<!DOCTYPE html>
<html lang="es" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nuevo Cliente</title>

    <script src="https://cdn.tailwindcss.com"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">

    <link rel="stylesheet" href="{% static 'css/output.css' %}">
</head>
<body class="bg-gray-50 font-sans" x-data="customerForm()">
    <div class="max-w-2xl mx-auto p-8">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-black text-gray-900">Nuevo Cliente</h1>
            <p class="text-sm text-gray-600 mt-2">Complete los datos del cliente</p>
        </div>

        <!-- Form Card -->
        <section class="card p-6 shadow-float">
            <form @submit.prevent="submitForm()">
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                            Nombre
                        </label>
                        <input
                            type="text"
                            x-model="customer.firstName"
                            required
                            class="w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm transition-all text-gray-900">
                    </div>

                    <div>
                        <label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
                            Apellido
                        </label>
                        <input
                            type="text"
                            x-model="customer.lastName"
                            required
                            class="w-full bg-white border border-gray-300 rounded-lg px-4 py-2.5 text-sm transition-all text-gray-900">
                    </div>
                </div>

                <!-- Submit -->
                <div class="mt-6 flex gap-3">
                    <a href="{% url 'customers:list' %}"
                       class="btn flex-1 py-3 bg-white border-2 border-gray-300 text-gray-700 rounded-lg font-semibold text-sm hover:bg-gray-50 text-center">
                        Cancelar
                    </a>
                    <button
                        type="submit"
                        :disabled="!isFormValid()"
                        class="btn flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-bold text-sm disabled:opacity-50 disabled:cursor-not-allowed">
                        Guardar Cliente
                    </button>
                </div>
            </form>
        </section>
    </div>

    <script>
        function customerForm() {
            return {
                customer: {
                    firstName: '',
                    lastName: ''
                },

                isFormValid() {
                    return this.customer.firstName.trim() !== '' &&
                           this.customer.lastName.trim() !== '';
                },

                submitForm() {
                    if (this.isFormValid()) {
                        // Submit logic here
                    }
                }
            }
        }
    </script>
</body>
</html>
```

### Migration Strategy

When updating existing UIs to the new design system:

1. **Audit Current UI**: Identify components to migrate
2. **Start with Colors**: Update color palette first
3. **Typography Pass**: Swap font families
4. **Component by Component**: Migrate one section at a time
5. **Test Interactions**: Ensure Alpine.js state management works
6. **Accessibility Check**: Verify keyboard navigation and focus states
7. **Responsive Test**: Check mobile/tablet layouts

### Current Branch: sale-app

The repository is currently on branch `sale-app`, which appears to be developing the sales functionality based on the PlantUML diagram in documentation.
