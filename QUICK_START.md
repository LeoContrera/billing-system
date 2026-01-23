# POS System - Quick Start Guide

## 🚀 System Status: ✅ OPERATIONAL

The complete Point of Sale system has been implemented and tested successfully.

---

## ⚡ Quick Start (3 Steps)

### 1. Start the Development Server

```bash
just run
```

Or directly:
```bash
uv run python src/manage.py runserver
```

### 2. Access the POS Interface

Open your browser and navigate to:
**http://localhost:8000/sale/create/**

### 3. Complete Your First Sale

1. **Add Products**
   - Enter product name, quantity, and price
   - Click "Agregar Producto"
   - Add as many products as needed

2. **Register Payment**
   - Select payment method (Efectivo, Débito, Crédito, Transferencia)
   - Enter the amount
   - Click "Registrar Pago"
   - Can split payment across multiple methods

3. **Finalize Sale**
   - Ensure balance shows $0 (or negative for overpayment)
   - Click "Finalizar Venta"
   - Success! Sale is complete

---

## 🔑 Admin Access

Access Django admin at: **http://localhost:8000/admin/**

Default credentials (if you created a superuser):
- Username: `admin` (or your chosen username)
- Password: (your password)

View:
- Customers
- Sales (with product details)
- Transactions
- Payment Methods

---

## 🧪 Test the System

Run the verification script:

```bash
cd src
uv run python test_system.py
```

This will:
- Create a test sale
- Add a product
- Register a payment
- Finalize the sale
- Verify all components work

---

## 📊 What's Included

### 4 Apps
1. **users** - User management (pre-existing)
2. **customers** - Customer database
3. **sale** - Sales and line items
4. **payments** - Payment methods and transactions

### 5 Models
- Customer
- PaymentMethod
- Transaction
- Sale
- SaleLineItem

### 3 Service Classes
- CustomerService (search, quick create)
- SaleService (6 methods for complete workflow)
- PaymentService (payment registration)

### 8 Views/Endpoints
- Customer search (HTMX)
- Create sale
- Set customer
- Add item
- Apply discounts (2 endpoints)
- Add payment
- Finalize sale

### 7 Templates
- Main POS interface
- 6 partial templates for HTMX swaps

---

## 🎯 Usage Tips

### Customer Search (Optional)
- Start typing in "Buscar Cliente"
- Results appear automatically (typeahead)
- Customer assignment is optional

### Multiple Payments
- You can split payment across methods
- Example: $100 cash + $50 card = $150 total
- System allows overpayment (e.g., customer pays $20 for $15 sale)

### Payment Validation
- System prevents finalizing unpaid sales
- Balance must be ≤ $0 to finalize
- All calculations are automatic

### Product Entry
- SKU is optional
- Quantity supports decimals (e.g., 1.5 kg)
- Prices support cents (e.g., 99.99)

---

## 🛠️ Development Commands

### Database
```bash
# Create migrations
uv run python src/manage.py makemigrations

# Apply migrations
uv run python src/manage.py migrate

# Access database shell
uv run python src/manage.py dbshell
```

### User Management
```bash
# Create superuser
uv run python src/manage.py createsuperuser

# Change user password
uv run python src/manage.py changepassword <username>
```

### CSS (if you modify styles)
```bash
# Watch mode (auto-rebuild on changes)
just watch-css

# Build for production
just build-css
```

### Python Shell
```bash
# Django shell
uv run python src/manage.py shell

# Test a sale programmatically
from sale.services import SaleService
from users.models import User
user = User.objects.first()
sale = SaleService.create_sale(user)
```

---

## 📁 Key Files

### Business Logic (Services)
- `src/apps/customers/services.py`
- `src/apps/sale/services.py`
- `src/apps/payments/services.py`

### Models (Database Schema)
- `src/apps/customers/models.py`
- `src/apps/sale/models.py`
- `src/apps/payments/models.py`

### Views (HTTP Endpoints)
- `src/apps/customers/views.py`
- `src/apps/sale/views.py`
- `src/apps/payments/views.py`

### Templates (UI)
- `templates/sale/sale_create.html` - Main interface
- `templates/sale/_*.html` - Partial templates for HTMX

### Configuration
- `src/core/settings.py` - Django settings
- `src/core/urls.py` - URL routing
- `src/core/db.py` - SQLite WAL configuration

---

## 🔒 Security Features

- ✅ All endpoints require authentication (`@login_required`)
- ✅ CSRF protection enabled for all forms
- ✅ HTMX automatically includes CSRF tokens
- ✅ Database uses pessimistic locking (prevents race conditions)
- ✅ Protects against accidental data deletion (`on_delete=PROTECT`)

---

## 🐛 Troubleshooting

### "Database is locked" error
✅ Already fixed! WAL mode is configured to prevent this.

### "No user found" error
Create a superuser:
```bash
uv run python src/manage.py createsuperuser
```

### Payment methods not showing
Load the fixture:
```bash
cd src
uv run python manage.py loaddata initial_payment_methods
```

### HTMX not working
Check browser console for errors. CSRF token should be configured automatically.

### Styles not loading
Rebuild CSS:
```bash
just build-css
```

---

## 📚 Learn More

### Architecture
See `IMPLEMENTATION_SUMMARY.md` for detailed technical documentation.

### Code Examples
All services have docstrings with usage examples:
- `CustomerService.search_customers()`
- `SaleService.create_sale()`
- `PaymentService.add_payment()`

### Django ORM Patterns
Check service files for comments explaining:
- `select_for_update()` - Pessimistic locking
- `select_related()` - Eager loading (FK)
- `prefetch_related()` - Eager loading (reverse FK)
- `@transaction.atomic` - ACID transactions

---

## ✅ System Verified

The test script confirmed:
- ✅ Database connection (SQLite WAL mode)
- ✅ User authentication ready
- ✅ Customer management operational
- ✅ Payment methods loaded (4 methods)
- ✅ Sale creation working
- ✅ Product addition working
- ✅ Payment registration working
- ✅ Sale finalization working
- ✅ All calculations correct

---

## 🎉 You're Ready!

The POS system is fully operational and ready for use.

Start the server and go to:
**http://localhost:8000/sale/create/**

Happy selling! 🛒
