---
name: project-context
description: Project structure, dependencies, and technical stack for the Django billing system
---

# Project Context Skill

This skill provides essential context about the project structure, dependencies, and technical stack.

## When to Use This Skill

Use this skill when you need to:
- Understand the project's directory structure
- Know which dependencies and versions are being used
- Understand the app organization and module paths
- Configure new features that need to integrate with existing structure

## Tech Stack

### Package Management
- **uv**: Python dependencies management
- **pnpm**: JavaScript dependencies management
- **Just**: Command runner (task automation)

### Backend
- **Python**: 3.13+
- **Django**: 5.2
- **Database**: SQLite with WAL mode enabled
- **Key Dependencies**:
  - `django-afip`: AFIP/ARCA integration for electronic invoicing
  - `ReportLab`: PDF generation

### Frontend
- **HTMX**: Server-driven dynamic interactions
- **Alpine.js**: Client-side reactivity (used in standalone pages like POS)
- **Tailwind CSS v4**: Utility-first CSS framework
- **Flowbite**: Pre-built component library

## Project Structure

```
billing-system/
├── src/                          # Django project root
│   ├── core/                     # Project configuration
│   │   ├── settings.py          # Django settings
│   │   ├── urls.py              # Main URL configuration
│   │   └── wsgi.py/asgi.py      # Server configuration
│   │
│   ├── apps/                     # All Django applications
│   │   ├── users/               # Custom user model (AbstractUser)
│   │   ├── customers/           # Customer management
│   │   ├── products/            # Product catalog
│   │   ├── sale/                # Sales management
│   │   ├── payments/            # Payment processing
│   │   └── invoices/            # Invoice & AFIP integration
│   │
│   ├── manage.py                # Django management script
│   └── db.sqlite3               # SQLite database
│
├── templates/                    # Global Django templates
│   ├── base.html                # Base template with navbar, HTMX, Flowbite
│   ├── sale/                    # Sale app templates
│   ├── products/                # Product app templates
│   └── ...
│
├── static/                       # Static assets
│   ├── css/
│   │   ├── input.css            # Tailwind source (imports + plugin)
│   │   └── output.css           # Compiled CSS (build artifact)
│   └── js/
│       ├── htmx.min.js
│       └── flowbite.min.js
│
└── documentation/                # Technical documentation
    ├── DJANGO_AFIP_INTEGRATION.md
    ├── SYSTEM_FEATURES.md
    └── example-afip-usage.py
```

## Settings Path Resolution

**Critical Configuration Detail:**

Apps are added to Python path via:
```python
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))
```

This means:
- ✅ Import apps directly: `import users`, `from sale.models import Sale`
- ❌ DO NOT use: `from apps import users`, `from apps.sale.models import Sale`
- Apps registered in `INSTALLED_APPS` as: `'users'`, `'sale'`, etc. (not `'apps.users'`)

## Django Apps Overview

### 1. customers/
**Purpose**: Customer/client management
**Key Models**: `Customer`
**Services**: `CustomerService` (search, quick create, full create)

### 2. products/
**Purpose**: Product catalog and inventory
**Key Models**: `Product`
**Services**: `InventoryService` (stock management)

### 3. sale/
**Purpose**: Sales/transaction management
**Key Models**: `Sale`, `SaleLineItem`
**Services**: `SaleService` (create, add items, discounts, finalize)

### 4. payments/
**Purpose**: Payment processing
**Key Models**: `PaymentMethod`, `Transaction`
**Services**: `PaymentService` (register payments)

### 5. invoices/
**Purpose**: Electronic invoicing with AFIP
**Key Models**: `Invoice`, `VATAliquot`
**Services**: `InvoiceService` (orchestrator for AFIP integration)

### 6. users/
**Purpose**: User authentication
**Key Models**: Custom `User` model (extends `AbstractUser`)

## Database Configuration

- **Engine**: SQLite
- **WAL Mode**: Enabled for better concurrency
- **Migrations**: Standard Django migrations for schema versioning

## Static Files Configuration

**Templates:**
- Global templates in `templates/` (configured via `BASE_DIR.parent / 'templates'`)
- App-specific templates can go in `apps/<app>/templates/`
- Base template includes HTMX CSRF token auto-configuration

**Static Files:**
- Served from `static/` directory
- Tailwind v4 uses new CSS import syntax in `input.css`
- Flowbite imported as plugin via `@plugin` directive

## Common Commands

### Development Server
```bash
just run
# or
uv run python src/manage.py runserver
```

### CSS Build
```bash
just watch-css      # Development mode with watch
just build-css      # Production build (minified)
```

### Database
```bash
uv run python src/manage.py migrate
uv run python src/manage.py makemigrations
uv run python src/manage.py shell
```

### Package Management
```bash
# Python dependencies
uv add <package>
uv sync

# JavaScript dependencies
pnpm add <package>
pnpm install
```

### Code Quality
```bash
uv run ruff check    # Lint
uv run ruff format   # Format
```

## Key Dependencies Reference

When adding new features, be aware of these critical dependencies:

- **django-afip**: Used for AFIP web services integration
- **ReportLab**: Used for PDF generation
- **HTMX**: Handles AJAX requests without JavaScript
- **Alpine.js**: Used ONLY in complex standalone pages (like POS)
- **Tailwind CSS v4**: All styling uses utility classes
- **Flowbite**: Component library (buttons, modals, forms)

## Additional Resources

For detailed business logic and integration patterns, see:
- [project-best-practices](../project-best-practices/SKILL.md) - Philosophy and design patterns
- [django-backend](../django-backend/SKILL.md) - Backend implementation patterns
- [frontend-design](../frontend-design/SKILL.md) - Frontend patterns and guidelines
- [afip-integration](../afip-integration/SKILL.md) - AFIP integration specifics