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
└── billing-skills/           # Claude Code skills (this directory)
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

**Read [frontend-design](./billing-skills/frontend-design/SKILL.md) first!**

- Use HTMX for server interactions
- NO Alpine.js (unless adding complex POS-like page)
- Use Tailwind utility classes
- Create partial templates for HTMX responses

### Working with AFIP Integration

**Read [afip-integration](./billing-skills/afip-integration/SKILL.md) first!**

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
# Development
just run                                    # Run server
just watch-css                              # Watch Tailwind CSS

# Database
uv run python src/manage.py makemigrations  # Create migrations
uv run python src/manage.py migrate         # Apply migrations
uv run python src/manage.py shell           # Django shell

# Code Quality
uv run ruff check                           # Lint
uv run ruff format                          # Format

# Packages
uv add <package>                            # Add Python package
pnpm add <package>                          # Add JS package
```

## Remember

- **Always read relevant skills before implementing**
- **ORM-first, service layer, dumb templates** - these are non-negotiable
- **Alpine.js only for POS** - don't add it to regular HTMX templates
- **Transaction safety** - use `@transaction.atomic` for multi-record ops
- **Code should teach** - write clear, documented, example-worthy code

---

**For detailed implementation patterns, consult the skill files in `./.claude/skills/`**