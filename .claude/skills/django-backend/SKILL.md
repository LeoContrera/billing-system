---
name: django-backend
description: Backend implementation patterns, model design, and service layer examples for the Django billing system
---

# Django Backend Skill

This skill provides concrete patterns and examples for implementing backend functionality in the Django billing system.

## When to Use This Skill

Use this skill when you need to:
- Create or modify Django models
- Implement service layer business logic
- Design database relationships
- Create API endpoints or views
- Handle transactions and data integrity

## Model Design Patterns

### Core Model Structure

Every model should follow this template:

```python
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class MyModel(models.Model):
    """Brief description of what this model represents."""
    
    # 1. Foreign Keys and relationships first
    related_model = models.ForeignKey(
        'app.RelatedModel',
        on_delete=models.CASCADE,  # or PROTECT, SET_NULL
        related_name='my_models'
    )
    
    # 2. Core data fields
    name = models.CharField(max_length=200)
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # 3. Status/state fields
    is_active = models.BooleanField(default=True)
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT
    )
    
    # 4. Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'My Model'
        verbose_name_plural = 'My Models'
    
    def __str__(self):
        return f"{self.name} ({self.id})"
```

### Using TextChoices for Status Fields

```python
from django.db import models

class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Borrador'
    PENDING = 'PENDING', 'Pendiente'
    AUTHORIZED = 'AUTHORIZED', 'Autorizada'
    REJECTED = 'REJECTED', 'Rechazada'

class Invoice(models.Model):
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT
    )
```

### ForeignKey on_delete Strategies

Choose based on business requirements:

```python
# CASCADE: Delete children when parent deleted
sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
# Use for: Line items, sub-records that don't make sense without parent

# PROTECT: Prevent deletion of parent if children exist
product = models.ForeignKey(Product, on_delete=models.PROTECT)
# Use for: Master data that shouldn't be deleted if referenced

# SET_NULL: Keep child record but clear reference
afip_receipt = models.ForeignKey(
    'django_afip.Receipt',
    null=True,
    blank=True,
    on_delete=models.SET_NULL
)
# Use for: Historical references that should persist even if source deleted
```

### Decimal Fields for Money

ALWAYS use `DecimalField` for monetary amounts:

```python
from decimal import Decimal
from django.core.validators import MinValueValidator

class Sale(models.Model):
    total_amount = models.DecimalField(
        max_digits=12,  # Total digits (e.g., 9999999999.99)
        decimal_places=2,  # Decimal places
        validators=[MinValueValidator(Decimal('0.00'))]
    )
```

❌ **NEVER** use `FloatField` for money (floating point arithmetic errors!)

### Denormalization for History

Copy critical data to preserve historical accuracy:

```python
class SaleLineItem(models.Model):
    """Line item for a sale."""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    # Snapshot product data at sale time
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # Price at sale time
    vat_rate = models.DecimalField(max_digits=5, decimal_places=2)     # VAT rate at sale time
    
    # Calculated at creation
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
```

**Why?** If product price or VAT rate changes tomorrow, historical sale records remain accurate.

## Service Layer Implementation

### Basic Service Structure

```python
# apps/myapp/services.py
from django.db import transaction
from django.utils import timezone
from .models import MyModel

class MyService:
    """Business logic for MyApp."""
    
    @staticmethod
    @transaction.atomic
    def create_with_related(user, data):
        """
        Create main record with related records atomically.
        
        Args:
            user: User performing the action
            data: Dictionary with creation data
        
        Returns:
            Created MyModel instance
        
        Raises:
            ValueError: If validation fails
        """
        # Validation
        if not data.get('required_field'):
            raise ValueError("required_field is mandatory")
        
        # Create main record
        instance = MyModel.objects.create(
            name=data['name'],
            created_by=user
        )
        
        # Create related records
        for item in data.get('items', []):
            RelatedModel.objects.create(
                parent=instance,
                **item
            )
        
        return instance
```

### Real Example: SaleService

```python
# apps/sale/services.py
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from .models import Sale, SaleLineItem, SaleStatus
from products.models import Product

class SaleService:
    """Business logic for sales management."""
    
    @staticmethod
    @transaction.atomic
    def create_sale(user, customer=None):
        """
        Factory method to create a new sale.
        
        Args:
            user: User creating the sale
            customer: Optional customer for the sale
        
        Returns:
            New Sale instance in PENDING status
        """
        return Sale.objects.create(
            customer=customer,
            created_by=user,
            status=SaleStatus.PENDING
        )
    
    @staticmethod
    @transaction.atomic
    def add_line_item(sale_id, product_id, quantity, unit_price=None):
        """
        Add a product to a sale.
        
        Args:
            sale_id: ID of the sale
            product_id: ID of the product
            quantity: Quantity to add
            unit_price: Optional override price (uses product price if None)
        
        Returns:
            Created SaleLineItem instance
        
        Raises:
            ValueError: If sale is already completed or product not found
        """
        # Get sale with lock (prevents concurrent modifications)
        sale = Sale.objects.select_for_update().get(pk=sale_id)
        
        if sale.status == SaleStatus.COMPLETED:
            raise ValueError("Cannot modify completed sale")
        
        # Get product with its current data
        product = Product.objects.get(pk=product_id)
        
        # Use product price if not overridden
        price = unit_price if unit_price is not None else product.price
        
        # Create line item with denormalized data
        line_item = SaleLineItem.objects.create(
            sale=sale,
            product=product,
            quantity=quantity,
            unit_price=price,
            vat_rate=product.vat_rate  # Snapshot VAT rate
        )
        
        return line_item
    
    @staticmethod
    @transaction.atomic
    def apply_global_discount(sale_id, discount_percentage):
        """
        Apply percentage discount to entire sale.
        
        Args:
            sale_id: ID of the sale
            discount_percentage: Discount percentage (e.g., 10.5 for 10.5%)
        
        Raises:
            ValueError: If discount invalid or sale completed
        """
        sale = Sale.objects.select_for_update().get(pk=sale_id)
        
        if sale.status == SaleStatus.COMPLETED:
            raise ValueError("Cannot modify completed sale")
        
        if not (0 <= discount_percentage <= 100):
            raise ValueError("Discount must be between 0 and 100")
        
        # Calculate discount amount
        subtotal = sale.calculate_subtotal()  # Assuming method exists
        discount_amount = subtotal * (Decimal(str(discount_percentage)) / 100)
        
        sale.global_discount_amount = discount_amount.quantize(Decimal('0.01'))
        sale.save()
    
    @staticmethod
    @transaction.atomic
    def finalize_sale(sale_id, user):
        """
        Complete a sale transaction.
        
        Validates payment, updates status, records completion time.
        
        Args:
            sale_id: ID of the sale to finalize
            user: User performing the finalization
        
        Returns:
            Completed Sale instance
        
        Raises:
            ValueError: If sale cannot be completed
        """
        # Lock sale record
        sale = Sale.objects.select_for_update().get(pk=sale_id)
        
        # Validation
        if sale.status == SaleStatus.COMPLETED:
            raise ValueError("Sale already completed")
        
        if not sale.line_items.exists():
            raise ValueError("Cannot finalize empty sale")
        
        # Verify payment (assuming transactions related to sale)
        total_paid = sum(
            t.amount for t in sale.transactions.all()
        )
        if total_paid < sale.calculate_total():
            raise ValueError(
                f"Insufficient payment: {total_paid} < {sale.calculate_total()}"
            )
        
        # Update sale status
        sale.status = SaleStatus.COMPLETED
        sale.completed_at = timezone.now()
        sale.completed_by = user
        sale.save()
        
        return sale
    
    @staticmethod
    def validate_sale_for_completion(sale):
        """
        Validate that a sale can be completed.
        
        Non-transactional validation method.
        
        Returns:
            dict with 'valid' (bool) and 'errors' (list)
        """
        errors = []
        
        if sale.status == SaleStatus.COMPLETED:
            errors.append("Sale already completed")
        
        if not sale.line_items.exists():
            errors.append("Sale has no items")
        
        total_paid = sum(t.amount for t in sale.transactions.all())
        if total_paid < sale.calculate_total():
            errors.append(f"Payment incomplete: {total_paid}/{sale.calculate_total()}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
```

### Complex Orchestrator Example: InvoiceService

```python
# apps/invoices/services.py
from django.db import transaction
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class InvoiceService:
    """Orchestrator for AFIP invoice processing."""
    
    @staticmethod
    @transaction.atomic
    def procesar_venta_afip(sale_id, user):
        """
        Complete invoice workflow: create, emit CAE, generate PDF, send email.
        
        This is a Template Method pattern - orchestrates multiple steps.
        
        Args:
            sale_id: ID of completed sale
            user: User processing the invoice
        
        Returns:
            dict with invoice details and status
        
        Raises:
            ValueError: If sale cannot be invoiced
        """
        logger.info(f"Starting AFIP process for sale {sale_id}")
        
        # Step 1: Create local invoice
        logger.info("Step 1: Creating local invoice")
        invoice = InvoiceService.create_invoice_from_sale(sale_id, user)
        
        # Step 2: Emit CAE (authorization code)
        logger.info(f"Step 2: Emitting CAE for invoice {invoice.id}")
        invoice = InvoiceService.emit_cae(invoice.id)
        
        # Step 3: Generate PDF
        logger.info(f"Step 3: Generating PDF for invoice {invoice.id}")
        pdf_buffer = InvoiceService.generate_pdf(invoice)
        
        # Step 4: Send email (non-critical - don't fail if this fails)
        email_sent = False
        try:
            logger.info(f"Step 4: Sending email for invoice {invoice.id}")
            InvoiceService.send_invoice_email(invoice, pdf_buffer)
            email_sent = True
        except Exception as e:
            logger.warning(f"Email failed for invoice {invoice.id}: {e}")
            # Don't raise - invoice is already authorized with AFIP
        
        logger.info(
            f"AFIP process completed - Invoice: {invoice.id}, "
            f"CAE: {invoice.cae}, Email sent: {email_sent}"
        )
        
        return {
            'success': True,
            'invoice': invoice,
            'invoice_id': invoice.id,
            'receipt_type': invoice.get_receipt_type_display(),
            'cae': invoice.cae,
            'cae_expiration': invoice.cae_expiration,
            'total_amount': str(invoice.total_amount),
            'email_sent': email_sent
        }
```

## View Layer Patterns

### Basic HTMX View

```python
# apps/myapp/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .services import MyService

@login_required
def my_htmx_view(request):
    """
    HTMX endpoint returning HTML fragment.
    
    Returns partial template for HTMX to swap into page.
    """
    try:
        # Get data from service
        items = MyService.get_active_items()
        
        # Return partial template
        return render(request, 'myapp/_items_list.html', {
            'items': items
        })
    
    except Exception as e:
        # Return error fragment
        return render(request, 'myapp/_error.html', {
            'error': str(e)
        }, status=400)
```

### JSON API View

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@login_required
@require_http_methods(["POST"])
def create_item_api(request):
    """
    JSON API endpoint for creating items.
    
    Expects JSON payload, returns JSON response.
    """
    try:
        # Parse JSON data
        import json
        data = json.loads(request.body)
        
        # Validate
        if not data.get('name'):
            return JsonResponse({
                'success': False,
                'error': 'name is required'
            }, status=400)
        
        # Create via service
        item = MyService.create_item(
            user=request.user,
            name=data['name'],
            amount=data.get('amount', 0)
        )
        
        # Return success
        return JsonResponse({
            'success': True,
            'item_id': item.id,
            'name': item.name
        })
    
    except ValueError as e:
        # Business logic error
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
    except Exception as e:
        # Unexpected error
        logger.exception("Error creating item")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)
```

### Search View with HTMX

```python
@login_required
def search_customers(request):
    """
    Customer search for HTMX autocomplete.
    
    Query params:
        q: Search query (name or tax_id)
    
    Returns HTML fragment with customer list.
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        # Return empty state
        return render(request, 'customers/_search_results.html', {
            'customers': [],
            'message': 'Enter at least 2 characters'
        })
    
    # Search via service
    customers = CustomerService.search(query)
    
    return render(request, 'customers/_search_results.html', {
        'customers': customers
    })
```

## URL Configuration Patterns

```python
# apps/myapp/urls.py
from django.urls import path
from . import views

app_name = 'myapp'

urlpatterns = [
    # Main views
    path('', views.index, name='index'),
    path('create/', views.create, name='create'),
    
    # Detail views
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    
    # Actions
    path('<int:pk>/finalize/', views.finalize, name='finalize'),
    
    # HTMX endpoints (prefix with 'htmx-' by convention)
    path('htmx-search/', views.search_htmx, name='htmx-search'),
    path('htmx-load-more/', views.load_more_htmx, name='htmx-load-more'),
    
    # API endpoints (prefix with 'api-')
    path('api-create/', views.create_api, name='api-create'),
    path('api-update/<int:pk>/', views.update_api, name='api-update'),
]
```

## Query Optimization Patterns

### Example: Optimize Invoice Detail View

```python
def invoice_detail(request, invoice_id):
    """Get invoice with all related data in minimal queries."""
    
    # ❌ BAD: Multiple queries (N+1 problem)
    invoice = Invoice.objects.get(pk=invoice_id)
    customer_name = invoice.sale.customer.first_name  # Query 1
    line_items = invoice.sale.line_items.all()  # Query 2
    for item in line_items:
        product_name = item.product.name  # Query 3, 4, 5... (N queries)
    
    # ✅ GOOD: Single query with JOINs
    invoice = Invoice.objects.select_related(
        'sale__customer',  # JOIN customer
        'afip_receipt'     # JOIN AFIP receipt
    ).prefetch_related(
        'sale__line_items__product',  # Prefetch items and their products
        'vat_aliquots'                # Prefetch VAT aliquots
    ).get(pk=invoice_id)
    
    # Now all related data is loaded - no additional queries
    customer_name = invoice.sale.customer.first_name
    for item in invoice.sale.line_items.all():
        product_name = item.product.name  # Already loaded
```

### Aggregation Example

```python
from django.db.models import Sum, Count, Avg

class ReportService:
    @staticmethod
    def get_sales_summary(start_date, end_date):
        """Get sales summary for date range."""
        summary = Sale.objects.filter(
            completed_at__gte=start_date,
            completed_at__lte=end_date,
            status=SaleStatus.COMPLETED
        ).aggregate(
            total_sales=Sum('total_amount'),
            sale_count=Count('id'),
            average_sale=Avg('total_amount')
        )
        
        return summary
```

### Subquery Example

```python
from django.db.models import Subquery, OuterRef

# Get customers with their last purchase date
from django.db.models import Max

customers_with_last_purchase = Customer.objects.annotate(
    last_purchase_date=Max('sale__completed_at')
).filter(
    last_purchase_date__isnull=False
).order_by('-last_purchase_date')
```

## Transaction Patterns

### Basic Atomic Transaction

```python
from django.db import transaction

@transaction.atomic
def create_sale_with_items(user, customer, items):
    """Create sale and items in single transaction."""
    # If ANY operation fails, ALL rollback
    sale = Sale.objects.create(customer=customer, created_by=user)
    
    for item in items:
        SaleLineItem.objects.create(sale=sale, **item)
    
    return sale
```

### Nested Transactions with Savepoints

```python
@transaction.atomic
def complex_operation():
    """Complex operation with nested savepoints."""
    # Outer transaction
    main_record = MainModel.objects.create(name="Main")
    
    try:
        # Inner savepoint
        with transaction.atomic():
            risky_operation()
    except Exception:
        # Inner savepoint rolled back, outer continues
        logger.warning("Risky operation failed, continuing...")
    
    # Outer transaction commits
    return main_record
```

### Manual Transaction Control

```python
from django.db import transaction

def manual_transaction_example():
    """Manual transaction control (rarely needed)."""
    with transaction.atomic():
        # Start transaction
        sale = Sale.objects.create(...)
        
        # Explicit savepoint
        sid = transaction.savepoint()
        
        try:
            risky_update()
            transaction.savepoint_commit(sid)
        except Exception:
            transaction.savepoint_rollback(sid)
```

## Common Model Methods

### Calculated Properties

```python
class Sale(models.Model):
    # ... fields ...
    
    def calculate_subtotal(self):
        """Calculate subtotal from line items."""
        return sum(
            item.quantity * item.unit_price - item.discount_amount
            for item in self.line_items.all()
        )
    
    def calculate_total(self):
        """Calculate final total with global discount."""
        subtotal = self.calculate_subtotal()
        return subtotal - self.global_discount_amount
    
    @property
    def display_number(self):
        """Format invoice number for display."""
        return f"{self.point_of_sale:04d}-{self.number:08d}"
```

### Custom Managers

```python
from django.db import models

class ActiveManager(models.Manager):
    """Manager that filters to active records only."""
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)

class Product(models.Model):
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    
    # Default manager (all records)
    objects = models.Manager()
    
    # Custom manager (active only)
    active = ActiveManager()

# Usage:
all_products = Product.objects.all()
active_products = Product.active.all()
```

## Security Patterns

### Permission Checks

```python
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('sale.delete_sale', raise_exception=True)
def delete_sale(request, sale_id):
    """Only users with delete_sale permission can access."""
    SaleService.delete_sale(sale_id)
    return JsonResponse({'success': True})
```

### Object-Level Permissions

```python
@login_required
def edit_sale(request, sale_id):
    """Users can only edit their own sales."""
    sale = Sale.objects.get(pk=sale_id)
    
    # Check ownership
    if sale.created_by != request.user:
        return JsonResponse({
            'success': False,
            'error': 'You can only edit your own sales'
        }, status=403)
    
    # Process...
```

## Additional Resources

For related information, see:
- [project-best-practices](../project-best-practices/SKILL.md) - Design patterns and philosophy
- [project-context](../project-context/SKILL.md) - Project structure
- [afip-integration](../afip-integration/SKILL.md) - Complex integration example