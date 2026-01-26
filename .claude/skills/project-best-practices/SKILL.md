---
name: project-best-practices
description: Development philosophy, principles, and design patterns for the Django billing system
---

# Project Best Practices Skill

This skill defines the development philosophy, architectural principles, and design patterns that guide all code in this project.

## When to Use This Skill

Use this skill when you need to:
- Understand the project's design philosophy
- Make architectural decisions
- Implement new features following project conventions
- Review or refactor existing code
- Apply appropriate design patterns

## Development Philosophy

### Target Audience

**This project is designed as a learning resource for Django development.**

All code should be:
- Clean and readable ("Pythonic")
- Well-documented for teaching purposes
- Example-worthy for best practices
- Pedagogically sound

### Core Principles

#### 1. ORM-First Approach

**CRITICAL RULE**: All database interactions MUST use Django's ORM.

✅ **CORRECT:**
```python
# Query using ORM
customers = Customer.objects.filter(tax_category='RI')

# Complex queries with Q objects
from django.db.models import Q
results = Product.objects.filter(
    Q(price__gte=100) | Q(sku__startswith='PREM')
)

# Aggregations
from django.db.models import Sum
total = Sale.objects.aggregate(total=Sum('total_amount'))

# Atomic updates with F expressions
from django.db.models import F
Product.objects.filter(category='electronics').update(
    price=F('price') * 1.10
)
```

❌ **NEVER DO THIS:**
```python
# Raw SQL in views or services
cursor.execute("SELECT * FROM customers WHERE tax_category = 'RI'")

# String interpolation in queries
Customer.objects.raw(f"SELECT * FROM customers WHERE id = {customer_id}")
```

**Exception**: Raw SQL is ONLY acceptable in:
- Database migrations
- Performance-critical operations after ORM optimization attempts
- Must be documented with reasoning

#### 2. Clean & Pedagogical Code

Code should serve as a teaching example:

```python
# ✅ Clear, self-documenting
def calculate_total_with_discount(subtotal: Decimal, discount_rate: Decimal) -> Decimal:
    """
    Calculate final total after applying percentage discount.
    
    Args:
        subtotal: Pre-discount amount
        discount_rate: Discount percentage (e.g., 10.5 for 10.5%)
    
    Returns:
        Final total rounded to 2 decimal places
    """
    discount_amount = subtotal * (discount_rate / 100)
    return (subtotal - discount_amount).quantize(Decimal('0.01'))

# ❌ Unclear, no documentation
def calc(s, d):
    return (s - s * d / 100).quantize(Decimal('0.01'))
```

#### 3. Modular Architecture

Each Django app has a single, clear responsibility:

```
customers/  → Customer data and fiscal info
products/   → Product catalog and inventory
sale/       → Sales transactions and line items
payments/   → Payment processing and methods
invoices/   → AFIP integration and fiscal documents
users/      → Authentication and user management
```

**App Boundaries:**
- Apps should be loosely coupled
- Cross-app communication via services, not direct model access
- Use ForeignKeys thoughtfully (consider `on_delete` implications)

#### 4. Service Layer Pattern

**Business logic NEVER lives in views or models.**

```python
# ✅ CORRECT: Business logic in services.py
# apps/sale/services.py
class SaleService:
    @staticmethod
    @transaction.atomic
    def finalize_sale(sale_id: int, user) -> Sale:
        """Complete a sale transaction."""
        sale = Sale.objects.select_for_update().get(pk=sale_id)
        
        if sale.status == SaleStatus.COMPLETED:
            raise ValueError("Sale already completed")
        
        # Business logic here
        sale.status = SaleStatus.COMPLETED
        sale.completed_at = timezone.now()
        sale.completed_by = user
        sale.save()
        
        return sale

# apps/sale/views.py
def finalize_sale_view(request, sale_id):
    """View only handles request/response."""
    try:
        sale = SaleService.finalize_sale(sale_id, request.user)
        return JsonResponse({'success': True, 'sale_id': sale.id})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
```

❌ **WRONG: Business logic in views**
```python
def finalize_sale_view(request, sale_id):
    # DON'T put business logic here!
    sale = Sale.objects.get(pk=sale_id)
    sale.status = SaleStatus.COMPLETED
    sale.completed_at = timezone.now()
    sale.save()
    return JsonResponse({'success': True})
```

#### 5. Transaction Safety

Use `@transaction.atomic` for operations that modify multiple records:

```python
from django.db import transaction

class SaleService:
    @staticmethod
    @transaction.atomic
    def create_sale_with_items(user, customer_id, items):
        """Create sale and line items atomically."""
        # If any operation fails, ALL will rollback
        sale = Sale.objects.create(
            customer_id=customer_id,
            created_by=user
        )
        
        for item in items:
            SaleLineItem.objects.create(
                sale=sale,
                product_id=item['product_id'],
                quantity=item['quantity'],
                unit_price=item['price']
            )
        
        return sale
```

**When to use `@transaction.atomic`:**
- Creating parent + child records (Sale + SaleLineItems)
- Multi-step processes (Invoice creation + AFIP submission)
- Financial operations (Payment + Sale status update)
- Any operation where partial success is unacceptable

## Design Patterns (Gang of Four)

### 1. Factory Method Pattern

Used for object creation with complex initialization:

```python
class SaleService:
    @staticmethod
    def create_sale(user, customer=None):
        """Factory method for Sale creation."""
        return Sale.objects.create(
            customer=customer,
            created_by=user,
            status=SaleStatus.PENDING
        )
```

### 2. Strategy Pattern

Used for interchangeable algorithms:

```python
# AFIP integration modes
class InvoiceService:
    @staticmethod
    def emit_cae(invoice_id: int):
        if settings.AFIP_DEBUG_MODE:
            return InvoiceService._emit_simulated_cae(invoice_id)
        else:
            return InvoiceService._emit_production_cae(invoice_id)
```

### 3. Template Method Pattern

Used for orchestrating multi-step processes:

```python
class InvoiceService:
    @staticmethod
    @transaction.atomic
    def procesar_venta_afip(sale_id: int, user):
        """Template method orchestrating invoice workflow."""
        # Step 1: Create local invoice
        invoice = InvoiceService.create_invoice_from_sale(sale_id, user)
        
        # Step 2: Emit CAE
        invoice = InvoiceService.emit_cae(invoice.id)
        
        # Step 3: Generate PDF
        pdf_buffer = InvoiceService.generate_pdf(invoice)
        
        # Step 4: Send email
        email_sent = InvoiceService.send_invoice_email(invoice, pdf_buffer)
        
        return {
            'success': True,
            'invoice': invoice,
            'email_sent': email_sent
        }
```

### 4. Repository Pattern (Implicit via ORM)

Django's ORM naturally implements the repository pattern:

```python
# The ORM acts as a repository
Customer.objects.filter(tax_category='RI')  # Repository query interface
```

## ORM Best Practices

### Query Optimization

#### 1. Use select_related() for ForeignKey/OneToOne

```python
# ✅ CORRECT: Single query with JOIN
sale = Sale.objects.select_related('customer', 'created_by').get(pk=sale_id)
# Now sale.customer and sale.created_by don't trigger additional queries

# ❌ WRONG: N+1 query problem
sale = Sale.objects.get(pk=sale_id)
customer_name = sale.customer.first_name  # Triggers separate query!
```

#### 2. Use prefetch_related() for M2M/Reverse FK

```python
# ✅ CORRECT: Prefetch line items
sales = Sale.objects.prefetch_related('line_items').filter(status='COMPLETED')
for sale in sales:
    for item in sale.line_items.all():  # No additional queries
        print(item.product.name)

# ❌ WRONG: N+1 queries
sales = Sale.objects.filter(status='COMPLETED')
for sale in sales:
    for item in sale.line_items.all():  # Separate query for each sale!
        print(item.product.name)
```

#### 3. Use Q() Objects for Complex Queries

```python
from django.db.models import Q

# Complex OR conditions
results = Product.objects.filter(
    Q(price__lte=100) | Q(category='sale') | Q(sku__startswith='DISC')
)

# Complex AND/OR combinations
results = Customer.objects.filter(
    Q(tax_category='RI') & (Q(email__isnull=False) | Q(phone__isnull=False))
)
```

#### 4. Use F() Expressions for Atomic Updates

```python
from django.db.models import F

# ✅ CORRECT: Atomic database-level update
Product.objects.filter(category='sale').update(price=F('price') * 0.9)

# ❌ WRONG: Loads all records into memory, race condition possible
products = Product.objects.filter(category='sale')
for product in products:
    product.price = product.price * 0.9
    product.save()
```

#### 5. Use select_for_update() for Locking

```python
from django.db import transaction

@transaction.atomic
def process_payment(sale_id, amount):
    # Lock the sale record to prevent race conditions
    sale = Sale.objects.select_for_update().get(pk=sale_id)
    
    if sale.status != SaleStatus.PENDING:
        raise ValueError("Cannot process payment for non-pending sale")
    
    # Process payment...
    sale.status = SaleStatus.COMPLETED
    sale.save()
```

## Code Organization Patterns

### Service File Structure

```python
# apps/sale/services.py
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

class SaleService:
    """Business logic for sales management."""
    
    # Factory methods first
    @staticmethod
    @transaction.atomic
    def create_sale(user, customer=None):
        """Create a new sale."""
        pass
    
    # Core operations
    @staticmethod
    @transaction.atomic
    def add_line_item(sale_id, product_id, quantity, unit_price):
        """Add a product to the sale."""
        pass
    
    # Validation methods
    @staticmethod
    def validate_sale_for_completion(sale):
        """Validate that sale can be completed."""
        pass
    
    # Helper methods (private)
    @staticmethod
    def _calculate_line_total(quantity, unit_price, discount):
        """Calculate line item total."""
        pass
```

### View File Structure

```python
# apps/sale/views.py
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .services import SaleService

@login_required
def create_sale_view(request):
    """Create a new sale (thin controller)."""
    try:
        # Extract data from request
        customer_id = request.POST.get('customer_id')
        
        # Delegate to service
        sale = SaleService.create_sale(
            user=request.user,
            customer_id=customer_id
        )
        
        # Return response
        return JsonResponse({
            'success': True,
            'sale_id': sale.id
        })
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
```

## Data Integrity Patterns

### 1. Intentional Denormalization

Copy critical data to maintain immutable history:

```python
class Invoice(models.Model):
    """Local invoice with denormalized data."""
    # Foreign key with SET_NULL (loose coupling)
    afip_receipt = models.OneToOneField(
        'django_afip.Receipt',
        null=True,
        on_delete=models.SET_NULL  # History persists even if AFIP data deleted
    )
    
    # Denormalized customer data (frozen at invoice creation)
    customer_name = models.CharField(max_length=200)
    customer_tax_id = models.CharField(max_length=20)
    customer_tax_category = models.CharField(max_length=2)
    
    # Denormalized amounts (frozen calculation results)
    net_taxed = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
```

**Why denormalize?**
- Historical accuracy (prices/taxes change over time)
- Audit trails (who was the customer at transaction time?)
- System resilience (local data persists even if external system fails)

### 2. Cascade vs. Protect

Choose `on_delete` behavior carefully:

```python
class SaleLineItem(models.Model):
    # CASCADE: When sale deleted, items deleted too (expected behavior)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    
    # PROTECT: Cannot delete product if used in sales (data integrity)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
```

## Error Handling Patterns

### Service Layer Exceptions

```python
class SaleService:
    @staticmethod
    @transaction.atomic
    def finalize_sale(sale_id, user):
        try:
            sale = Sale.objects.select_for_update().get(pk=sale_id)
        except Sale.DoesNotExist:
            raise ValueError(f"Sale {sale_id} not found")
        
        if sale.status == SaleStatus.COMPLETED:
            raise ValueError("Sale already completed")
        
        if not sale.line_items.exists():
            raise ValueError("Cannot finalize empty sale")
        
        # Process...
        return sale
```

### View Layer Error Handling

```python
@login_required
def finalize_sale_view(request, sale_id):
    try:
        sale = SaleService.finalize_sale(sale_id, request.user)
        return JsonResponse({'success': True, 'sale_id': sale.id})
    
    except ValueError as e:
        # Business logic errors (400 Bad Request)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    except Exception as e:
        # Unexpected errors (500 Internal Server Error)
        logger.exception(f"Error finalizing sale {sale_id}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)
```

## Validation Patterns

### Model-Level Validation

```python
from django.core.validators import MinValueValidator, MaxValueValidator

class Product(models.Model):
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
```

### Service-Level Validation

```python
class SaleService:
    @staticmethod
    def validate_payment_amount(sale, total_paid):
        """Validate payment covers sale total."""
        if total_paid < sale.total_amount:
            raise ValueError(
                f"Insufficient payment: {total_paid} < {sale.total_amount}"
            )
```

## Testing Philosophy

Write tests that verify business logic:

```python
from django.test import TestCase
from .services import SaleService

class SaleServiceTests(TestCase):
    def test_cannot_finalize_empty_sale(self):
        """Empty sales should not be finalizable."""
        sale = SaleService.create_sale(user=self.user)
        
        with self.assertRaises(ValueError) as ctx:
            SaleService.finalize_sale(sale.id, self.user)
        
        self.assertIn("empty sale", str(ctx.exception))
```

## Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

class InvoiceService:
    @staticmethod
    def procesar_venta_afip(sale_id, user):
        logger.info(f"Processing AFIP invoice for sale {sale_id}")
        
        try:
            # Process...
            logger.info(f"Invoice created: {invoice.id} - CAE: {invoice.cae}")
            return result
        
        except Exception as e:
            logger.exception(f"Failed to process AFIP for sale {sale_id}")
            raise
```

## Additional Resources

For implementation details, see:
- [project-context](../project-context/SKILL.md) - Project structure and dependencies
- [django-backend](../django-backend/SKILL.md) - Backend implementation examples
- [afip-integration](../afip-integration/SKILL.md) - Complex integration example