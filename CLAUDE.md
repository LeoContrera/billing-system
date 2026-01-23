# Django Billing System - Claude Code Instructions

This document provides high-level guidance for Claude Code when working on the billing system project. Detailed implementation patterns are organized into specialized skills.

## Project Overview

A point of sale (POS) and electronic invoicing system built with Django 5.2, integrated with ARCA (ex-AFIP) for fiscal compliance in Argentina.

**Key Technologies:**
- Backend: Django 5.2 + Python 3.13+
- Frontend: HTMX + Alpine.js (POS only) + Tailwind CSS v4
- Database: SQLite with WAL mode
- Package Management: uv (Python), pnpm (JavaScript)
- Task Runner: Just

## Skills Reference

This project uses a modular skill system. **Always read the relevant skills before starting work.**

### Available Skills

#### 1. [project-context](./.claude/skills/project-context/SKILL.md)
**Use when:** You need to understand project structure, dependencies, or configuration
- Directory structure and app organization
- Tech stack and versions
- Package management commands
- Path resolution and import patterns

#### 2. [project-best-practices](./.claude/skills/project-best-practices/SKILL.md)
**Use when:** Making architectural decisions or implementing core patterns
- Development philosophy and principles
- ORM-first approach (mandatory)
- Service layer pattern
- Design patterns (Factory, Strategy, Template Method)
- Transaction safety with `@transaction.atomic`

#### 3. [django-backend](./.claude/skills/django-backend/SKILL.md)
**Use when:** Creating models, services, or views
- Model design patterns
- Service layer implementation examples
- View patterns (HTMX endpoints, JSON APIs)
- Query optimization techniques
- Transaction patterns

#### 4. [frontend-design](./.claude/skills/frontend-design/SKILL.md)
**Use when:** Working on templates or frontend components
- **CRITICAL**: Alpine.js usage rules (POS ONLY!)
- HTMX interaction patterns
- Template structure ("dumb templates")
- Tailwind CSS patterns
- Responsive design

#### 5. [afip-integration](./.claude/skills/afip-integration/SKILL.md)
**Use when:** Working with invoicing or AFIP integration
- Invoice workflow orchestration
- Receipt type determination (A/B/C)
- Tax calculations (discriminated/included VAT)
- CAE emission (DEBUG/PRODUCTION modes)
- PDF generation and email delivery

## Core Principles (Quick Reference)

### 🔴 Mandatory Rules

1. **ORM-First**: NEVER write raw SQL in views or services
   ```python
   # ✅ DO THIS
   customers = Customer.objects.filter(tax_category='RI')
   
   # ❌ NEVER THIS
   cursor.execute("SELECT * FROM customers WHERE tax_category = 'RI'")
   ```

2. **Service Layer**: Business logic ONLY in `services.py`, never in views
   ```python
   # ✅ DO THIS
   # services.py
   class SaleService:
       @transaction.atomic
       def finalize_sale(sale_id, user):
           # Business logic here
   
   # views.py
   def finalize_view(request, sale_id):
       sale = SaleService.finalize_sale(sale_id, request.user)
       return JsonResponse({'success': True})
   
   # ❌ NEVER THIS
   # views.py - business logic in view
   def finalize_view(request, sale_id):
       sale = Sale.objects.get(pk=sale_id)
       sale.status = 'COMPLETED'
       sale.save()
   ```

3. **Alpine.js ONLY for POS**: Regular templates should be "dumb"
   ```html
   <!-- ✅ DO THIS (regular template) -->
   <button hx-get="/endpoint" hx-target="#result">Load</button>
   
   <!-- ❌ NEVER THIS (Alpine.js in regular template) -->
   <div x-data="{ open: false }">
       <button @click="open = !open">Toggle</button>
   </div>
   ```

4. **Transaction Safety**: Use `@transaction.atomic` for multi-record operations
   ```python
   @transaction.atomic
   def create_sale_with_items(user, items):
       sale = Sale.objects.create(created_by=user)
       for item in items:
           SaleLineItem.objects.create(sale=sale, **item)
       return sale
   ```

### 📁 Project Structure

```
billing-system/
├── src/
│   ├── core/                 # Settings, main URLs
│   ├── apps/                 # All Django apps
│   │   ├── customers/        # Customer management
│   │   ├── products/         # Product catalog
│   │   ├── sale/             # Sales transactions
│   │   ├── payments/         # Payment processing
│   │   ├── invoices/         # AFIP integration
│   │   └── users/            # Authentication
│   └── manage.py
├── templates/                # Global templates
├── static/                   # CSS, JavaScript
├── documentation/            # Technical docs
└── .claude/skills/           # Claude Code skills (this directory)
```

**Important**: Apps import directly (not via `apps.` prefix):
```python
# ✅ CORRECT
from sale.models import Sale
from customers.services import CustomerService

# ❌ WRONG
from apps.sale.models import Sale
```

## Common Tasks

### Creating a New Feature

1. **Read relevant skills first** (usually 2-3 skills)
2. **Design**: Follow service layer pattern
3. **Implement**: 
   - Model changes in `models.py`
   - Business logic in `services.py`
   - Views in `views.py` (thin controllers)
   - Templates in `templates/` (dumb templates with HTMX)
4. **Test**: Create test sales/invoices in shell

### Adding a New Endpoint

```python
# 1. Service (business logic)
# apps/myapp/services.py
class MyService:
    @staticmethod
    @transaction.atomic
    def do_something(data):
        # Business logic here
        pass

# 2. View (thin controller)
# apps/myapp/views.py
@login_required
def my_view(request):
    try:
        result = MyService.do_something(request.POST)
        return JsonResponse({'success': True, 'data': result})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

# 3. URL
# apps/myapp/urls.py
urlpatterns = [
    path('do-something/', views.my_view, name='do-something'),
]
```

### Modifying Templates

**Read [frontend-design](./.claude/skills/frontend-design/SKILL.md) first!**

- Use HTMX for server interactions
- NO Alpine.js (unless adding complex POS-like page)
- Use Tailwind utility classes
- Create partial templates for HTMX responses

### Working with AFIP Integration

**Read [afip-integration](./.claude/skills/afip-integration/SKILL.md) first!**

The invoice workflow is already implemented. Key points:
- Automatic receipt type determination (A/B/C)
- DEBUG mode for development (simulated CAE)
- Production mode requires AFIP certificates
- Email failures don't invalidate CAE

## Development Workflow

### Setup
```bash
# Install dependencies
uv sync
pnpm install

# Run migrations
uv run python src/manage.py migrate

# Load fixtures
uv run python src/manage.py loaddata payments/fixtures/initial_payment_methods.json
```

### Running
```bash
# Development server
just run

# Watch CSS (separate terminal)
just watch-css

# Django shell
uv run python src/manage.py shell
```

### Testing AFIP
```bash
# Load example script
cd src
uv run python manage.py shell

# In shell:
exec(open('../documentation/example-afip-usage.py').read())
ejemplo_completo_facturacion()
```

## Code Quality Standards

### Python
- Use type hints where helpful (not mandatory)
- Use Decimal for money (NEVER float)
- Document complex business logic
- Use docstrings for public methods

### Templates
- "Dumb" templates (data in, HTML out)
- HTMX for interactions
- Tailwind for styling
- NO JavaScript logic (except POS)

### Database
- ORM only (no raw SQL)
- Use `select_related()` / `prefetch_related()` for optimization
- Use `@transaction.atomic` for data integrity
- Denormalize when needed for history

## Getting Help

When uncertain about implementation:

1. **Read the relevant skill(s)** - most questions are answered there
2. **Check existing code** - apps/sale/, apps/invoices/ have good examples
3. **Django shell** - test queries and business logic interactively

## Quick Command Reference

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
- HTMX handles dynamic interactions
- Flowbite provides pre-built components
- Tailwind handles styling with utility classes
- Write server-side views that return HTML fragments for HTMX to swap

When adding new views that use HTMX, ensure they return partial HTML templates that can be swapped into the page.

## POS System Architecture

This is a local Point of Sale (POS) system with the following modular structure:

**App: `sale`**
- Handles sales transactions and line items
- Models: `Sale`, `SaleLineItem`
- Contains sale creation, modification, and finalization logic

**App: `payments`**
- Manages payment methods and transactions
- Models: `PaymentMethod`, `Transaction`
- Handles payment processing and tracking

**Key Implementation Guidelines:**
1. **Strict ORM Usage:** All database operations must use Django ORM methods
2. **Service Layer:** Implement business logic in `services.py` files
3. **Atomic Transactions:** Wrap multi-step operations in `transaction.atomic()`
4. **No Raw SQL:** Database configuration (like WAL mode) is abstracted; application code uses only ORM
5. **Educational Focus:** Code should demonstrate Django best practices

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

### Current Branch: sale-app

The repository is currently on branch `sale-app`, which appears to be developing the sales functionality based on the PlantUML diagram in documentation.
