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
