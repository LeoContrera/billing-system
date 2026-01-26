---
name: afip-integration
description: AFIP/ARCA electronic invoicing integration patterns, business rules, and implementation details
---

# AFIP Integration Skill

This skill provides comprehensive guidance for AFIP (Administración Federal de Ingresos Públicos) electronic invoicing integration.

## When to Use This Skill

Use this skill when you need to:
- Understand AFIP invoicing workflow
- Implement invoice creation and CAE emission
- Calculate taxes according to ARCA regulations
- Generate fiscal PDFs and send emails
- Debug AFIP-related issues

## Overview

The AFIP integration enables electronic invoicing (Facturas A/B/C) with:
- ✅ Automatic receipt type determination based on fiscal categories
- ✅ VAT calculation (discriminated for A, included for B/C)
- ✅ CAE (Electronic Authorization Code) emission
- ✅ PDF generation and email delivery
- ✅ DEBUG mode for development without AFIP certificates

## Architecture

### Layer Design

```
┌─────────────────────────────────────┐
│   Frontend (POS)                    │
│   Initiates invoice process         │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   LOCAL BUSINESS LAYER              │
│   Invoice (local model)             │
│   InvoiceService (orchestrator)     │
│   VATAliquot (VAT breakdown)        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   AFIP INTEGRATION LAYER            │
│   django-afip package               │
│   Receipt, ReceiptValidation        │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   AFIP Web Services (WSFE)          │
└─────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**:
   - Local models: Internal business logic and immutable history
   - AFIP models: Only for communication with AFIP services

2. **Intentional Denormalization**:
   - Critical data (CAE, customer info, amounts) copied to local models
   - Ensures history persists even if AFIP integration fails or is removed

3. **Loose Coupling**:
   - `Invoice.afip_receipt` uses `SET_NULL` (not `CASCADE`)
   - Local invoice history persists independently of AFIP data

4. **Strategy Pattern**:
   - DEBUG mode: Simulated CAE for development
   - PRODUCTION mode: Real AFIP web service calls

## Data Models

### Invoice (Local Model)

```python
# apps/invoices/models.py
from django.db import models
from decimal import Decimal

class ReceiptType(models.TextChoices):
    FACTURA_A = 'A', 'Factura A'
    FACTURA_B = 'B', 'Factura B'
    FACTURA_C = 'C', 'Factura C'

class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Borrador'
    PENDING = 'PENDING', 'Pendiente'
    AUTHORIZED = 'AUTHORIZED', 'Autorizada'
    REJECTED = 'REJECTED', 'Rechazada'

class Invoice(models.Model):
    """Local invoice record with denormalized data for immutable history."""
    
    # Relationships
    sale = models.OneToOneField('sale.Sale', on_delete=models.CASCADE)
    afip_receipt = models.OneToOneField(
        'django_afip.Receipt',
        null=True,
        blank=True,
        on_delete=models.SET_NULL  # Loose coupling
    )
    
    # Receipt type and status
    receipt_type = models.CharField(
        max_length=1,
        choices=ReceiptType.choices
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT
    )
    
    # Denormalized customer data (frozen at invoice time)
    customer_name = models.CharField(max_length=200)
    customer_tax_id = models.CharField(max_length=20)
    customer_tax_category = models.CharField(max_length=2)
    
    # Tax amounts
    net_taxed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Taxable base (without VAT)"
    )
    vat_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total VAT amount"
    )
    net_untaxed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Untaxed amount"
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Final total"
    )
    
    # CAE (copied from AFIP response)
    cae = models.CharField(max_length=14, blank=True)
    cae_expiration = models.DateField(null=True, blank=True)
    
    # Metadata
    notes = models.TextField(blank=True, help_text="Observations or errors")
    created_at = models.DateTimeField(auto_now_add=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Invoice {self.id} - {self.receipt_type} - {self.customer_name}"
```

### VATAliquot (VAT Breakdown)

```python
class VATAliquot(models.Model):
    """VAT breakdown by tax rate (Factura A only)."""
    
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='vat_aliquots'
    )
    vat_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="VAT rate (e.g., 21.00, 10.50)"
    )
    base_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Taxable base for this rate"
    )
    vat_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="VAT amount for this rate"
    )
    
    class Meta:
        ordering = ['-vat_rate']
```

**Note**: VATAliquot is ONLY created for Factura A (discriminated VAT).

## Business Rules - Receipt Type Determination

### ARCA Matrix

```
Issuer        Customer         Receipt Type
─────────────────────────────────────────────
RI            RI               Factura A
RI            MT/CF/EX         Factura B
MT/CF/EX      Any              Factura C
No customer   —                Ticket (Factura C)
```

**Tax Categories:**
- **RI**: Responsable Inscripto (Registered Taxpayer)
- **MT**: Monotributo (Simplified Tax Regime)
- **CF**: Consumidor Final (Final Consumer)
- **EX**: Exento (Exempt)

### Implementation

```python
# apps/invoices/services.py
from customers.models import TaxCategory

class InvoiceService:
    @staticmethod
    def determine_receipt_type(
        issuer_tax_category: str,
        customer_tax_category: str
    ) -> str:
        """
        Determine receipt type according to ARCA regulations.
        
        Args:
            issuer_tax_category: Tax category of issuing company
            customer_tax_category: Tax category of customer
        
        Returns:
            'A', 'B', or 'C'
        """
        if issuer_tax_category == TaxCategory.RESPONSABLE_INSCRIPTO:
            if customer_tax_category == TaxCategory.RESPONSABLE_INSCRIPTO:
                return ReceiptType.FACTURA_A
            else:
                return ReceiptType.FACTURA_B
        else:
            # Monotributo or other categories always issue C
            return ReceiptType.FACTURA_C
```

## Tax Calculations

### Factura A (Discriminated VAT)

VAT is shown separately on the invoice:

```
Net Taxable:      $826.45
VAT 21%:          $173.55
────────────────────────
Total:            $1000.00
```

**Calculation for each line item:**

```python
item_total = (quantity × unit_price) - discount_amount
base_amount = item_total / (1 + vat_rate/100)
vat_amount = base_amount × (vat_rate/100)
```

**Aggregation by VAT rate:**

```python
@staticmethod
def calculate_vat_aliquots_from_line_items(sale):
    """
    Aggregate line items by VAT rate.
    
    Returns:
        dict: {vat_rate: {'base_amount': Decimal, 'vat_amount': Decimal}}
    """
    from collections import defaultdict
    
    aliquots = defaultdict(lambda: {
        'base_amount': Decimal('0.00'),
        'vat_amount': Decimal('0.00')
    })
    
    for item in sale.line_items.all():
        # Calculate item total
        item_total = (
            item.quantity * item.unit_price - item.discount_amount
        ).quantize(Decimal('0.01'))
        
        # Calculate base and VAT
        vat_divisor = 1 + (item.vat_rate / 100)
        base_amount = (item_total / vat_divisor).quantize(Decimal('0.01'))
        vat_amount = (item_total - base_amount).quantize(Decimal('0.01'))
        
        # Aggregate by rate
        rate_key = str(item.vat_rate)
        aliquots[rate_key]['base_amount'] += base_amount
        aliquots[rate_key]['vat_amount'] += vat_amount
    
    return dict(aliquots)
```

### Factura B/C (Included VAT)

VAT is included in the price, not shown separately:

```
Total:            $1000.00
```

The invoice shows only the final total, but internally we still calculate the VAT portion for AFIP reporting:

```python
# For internal calculations (not shown on B/C invoices)
total_amount = Σ (item.quantity × item.unit_price - item.discount_amount)
```

## Invoice Workflow

### Complete Orchestrated Flow

```python
# apps/invoices/services.py
import logging
from django.db import transaction
from django.conf import settings

logger = logging.getLogger(__name__)

class InvoiceService:
    @staticmethod
    @transaction.atomic
    def procesar_venta_afip(sale_id: int, user):
        """
        Orchestrate complete invoice workflow.
        
        Steps:
        1. Create local invoice
        2. Emit CAE (authorization code)
        3. Generate PDF
        4. Send email
        
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
        invoice = InvoiceService.create_invoice_from_sale(sale_id, user)
        logger.info(f"Invoice {invoice.id} created - Type: {invoice.receipt_type}")
        
        # Step 2: Emit CAE
        invoice = InvoiceService.emit_cae(invoice.id)
        logger.info(f"CAE emitted: {invoice.cae}")
        
        # Step 3: Generate PDF
        pdf_buffer = InvoiceService.generate_pdf(invoice)
        logger.info(f"PDF generated for invoice {invoice.id}")
        
        # Step 4: Send email (non-critical)
        email_sent = False
        try:
            InvoiceService.send_invoice_email(invoice, pdf_buffer)
            email_sent = True
            logger.info(f"Email sent for invoice {invoice.id}")
        except Exception as e:
            logger.warning(f"Email failed for invoice {invoice.id}: {e}")
            # Don't fail the transaction - CAE is already authorized
        
        return {
            'success': True,
            'invoice': invoice,
            'invoice_id': invoice.id,
            'receipt_type': invoice.get_receipt_type_display(),
            'cae': invoice.cae,
            'cae_expiration': invoice.cae_expiration.isoformat(),
            'display_number': f"{invoice.point_of_sale:04d}-{invoice.number:08d}",
            'total_amount': str(invoice.total_amount),
            'email_sent': email_sent
        }
```

### Step 1: Create Invoice

```python
@staticmethod
@transaction.atomic
def create_invoice_from_sale(sale_id: int, user):
    """
    Create local invoice from completed sale.
    
    Determines receipt type, calculates taxes, denormalizes data.
    """
    from sale.models import Sale, SaleStatus
    from django_afip.models import TaxPayer
    
    # Validate sale
    sale = Sale.objects.select_related('customer').get(pk=sale_id)
    
    if sale.status != SaleStatus.COMPLETED:
        raise ValueError("Only completed sales can be invoiced")
    
    if hasattr(sale, 'invoice'):
        raise ValueError("Sale already has an invoice")
    
    if not sale.line_items.exists():
        raise ValueError("Sale has no items")
    
    # Get issuer (company)
    taxpayer = TaxPayer.objects.first()
    if not taxpayer:
        raise ValueError("No taxpayer configured")
    
    # Determine receipt type
    customer_tax_category = (
        sale.customer.tax_category if sale.customer
        else TaxCategory.CONSUMIDOR_FINAL
    )
    receipt_type = InvoiceService.determine_receipt_type(
        taxpayer.tax_category,
        customer_tax_category
    )
    
    # Calculate amounts based on receipt type
    if receipt_type == ReceiptType.FACTURA_A:
        # Discriminated VAT
        vat_aliquots = InvoiceService.calculate_vat_aliquots_from_line_items(sale)
        net_taxed = sum(a['base_amount'] for a in vat_aliquots.values())
        vat_amount = sum(a['vat_amount'] for a in vat_aliquots.values())
        total_amount = net_taxed + vat_amount
    else:
        # Included VAT (B/C)
        total_amount = sum(
            item.quantity * item.unit_price - item.discount_amount
            for item in sale.line_items.all()
        )
        net_taxed = Decimal('0.00')
        vat_amount = Decimal('0.00')
    
    # Apply global discount
    if sale.global_discount_amount:
        total_amount -= sale.global_discount_amount
    
    # Create invoice
    invoice = Invoice.objects.create(
        sale=sale,
        receipt_type=receipt_type,
        status=InvoiceStatus.DRAFT,
        customer_name=(
            f"{sale.customer.first_name} {sale.customer.last_name}"
            if sale.customer else "Consumidor Final"
        ),
        customer_tax_id=(
            sale.customer.tax_id if sale.customer else ""
        ),
        customer_tax_category=customer_tax_category,
        net_taxed=net_taxed.quantize(Decimal('0.01')),
        vat_amount=vat_amount.quantize(Decimal('0.01')),
        total_amount=total_amount.quantize(Decimal('0.01'))
    )
    
    # Create VAT aliquots (Factura A only)
    if receipt_type == ReceiptType.FACTURA_A:
        for rate, amounts in vat_aliquots.items():
            VATAliquot.objects.create(
                invoice=invoice,
                vat_rate=Decimal(rate),
                base_amount=amounts['base_amount'],
                vat_amount=amounts['vat_amount']
            )
    
    return invoice
```

### Step 2: Emit CAE

```python
@staticmethod
@transaction.atomic
def emit_cae(invoice_id: int):
    """
    Emit CAE (Electronic Authorization Code).
    
    Uses DEBUG mode (simulated) or PRODUCTION mode (real AFIP).
    """
    invoice = Invoice.objects.select_for_update().get(pk=invoice_id)
    
    if invoice.status == InvoiceStatus.AUTHORIZED:
        raise ValueError("Invoice already authorized")
    
    # Update status
    invoice.status = InvoiceStatus.PENDING
    invoice.save()
    
    # Choose strategy based on mode
    if settings.AFIP_DEBUG_MODE:
        return InvoiceService._emit_simulated_cae(invoice)
    else:
        return InvoiceService._emit_production_cae(invoice)

@staticmethod
def _emit_simulated_cae(invoice):
    """DEBUG mode: Generate simulated CAE."""
    from django.utils import timezone
    from datetime import timedelta
    
    # Generate fake CAE
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    invoice.cae = f"SIM{timestamp}"
    invoice.cae_expiration = timezone.now().date() + timedelta(days=10)
    invoice.status = InvoiceStatus.AUTHORIZED
    invoice.authorized_at = timezone.now()
    invoice.save()
    
    logger.info(f"Simulated CAE: {invoice.cae}")
    return invoice

@staticmethod
def _emit_production_cae(invoice):
    """PRODUCTION mode: Call real AFIP web services."""
    from django_afip.models import Receipt, TaxPayer, PointOfSales
    from django.utils import timezone
    
    # Get AFIP models
    taxpayer = TaxPayer.objects.first()
    pos = PointOfSales.objects.filter(is_active=True).first()
    
    if not pos:
        raise ValueError("No active point of sale configured")
    
    # Map receipt type to AFIP codes
    afip_receipt_type_map = {
        'A': 1,  # Factura A
        'B': 6,  # Factura B
        'C': 11  # Factura C
    }
    
    # Create AFIP receipt
    receipt = Receipt.objects.create(
        point_of_sales=pos,
        receipt_type_id=afip_receipt_type_map[invoice.receipt_type],
        concept=1,  # Products (1=Products, 2=Services, 3=Both)
        total_amount=invoice.total_amount,
        net_taxed=invoice.net_taxed,
        vat_amount=invoice.vat_amount,
        net_untaxed=invoice.net_untaxed,
        issued_date=timezone.now().date()
    )
    
    # Validate with AFIP
    validation = receipt.validate()
    
    if validation.result == 'A':  # Approved
        invoice.cae = validation.cae
        invoice.cae_expiration = validation.cae_expiration
        invoice.status = InvoiceStatus.AUTHORIZED
        invoice.authorized_at = timezone.now()
        invoice.afip_receipt = receipt
        invoice.save()
        
        logger.info(f"AFIP CAE authorized: {invoice.cae}")
        return invoice
    else:  # Rejected
        invoice.status = InvoiceStatus.REJECTED
        invoice.notes = f"AFIP rejection: {validation.observations}"
        invoice.save()
        
        logger.error(f"AFIP rejected invoice {invoice.id}: {validation.observations}")
        raise ValueError(f"AFIP rejected: {validation.observations}")
```

### Step 3: Generate PDF

```python
@staticmethod
def generate_pdf(invoice):
    """
    Generate PDF invoice.
    
    DEBUG mode: Simple ReportLab PDF
    PRODUCTION mode: Official AFIP PDF
    """
    if settings.AFIP_DEBUG_MODE:
        return InvoiceService._generate_simple_pdf(invoice)
    else:
        return InvoiceService._generate_afip_pdf(invoice)

@staticmethod
def _generate_simple_pdf(invoice):
    """Generate simple PDF with ReportLab."""
    from io import BytesIO
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 750, f"FACTURA {invoice.receipt_type}")
    
    # CAE info
    p.setFont("Helvetica", 12)
    p.drawString(100, 720, f"CAE: {invoice.cae}")
    p.drawString(100, 700, f"Vencimiento: {invoice.cae_expiration}")
    
    # Customer
    p.drawString(100, 670, f"Cliente: {invoice.customer_name}")
    p.drawString(100, 650, f"CUIT/DNI: {invoice.customer_tax_id}")
    
    # Amounts
    y = 600
    if invoice.receipt_type == 'A':
        p.drawString(100, y, f"Neto Gravado: ${invoice.net_taxed}")
        p.drawString(100, y-20, f"IVA: ${invoice.vat_amount}")
        y -= 40
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, y, f"TOTAL: ${invoice.total_amount}")
    
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer

@staticmethod
def _generate_afip_pdf(invoice):
    """Generate official AFIP PDF."""
    if not invoice.afip_receipt:
        raise ValueError("No AFIP receipt associated")
    
    # Use django-afip's built-in PDF generation
    pdf_buffer = invoice.afip_receipt.as_pdf()
    return pdf_buffer
```

### Step 4: Send Email

```python
@staticmethod
def send_invoice_email(invoice, pdf_buffer):
    """
    Send invoice email with PDF attachment.
    
    Raises:
        ValueError: If customer has no email
    """
    from django.core.mail import EmailMessage
    from django.conf import settings
    
    # Validate
    if not invoice.sale.customer or not invoice.sale.customer.email:
        raise ValueError("Customer has no email address")
    
    # Prepare email
    subject = f"Su Factura Electrónica {invoice.get_receipt_type_display()} - {invoice.display_number}"
    
    body = f"""
Estimado/a {invoice.customer_name},

Adjuntamos su comprobante electrónico autorizado por AFIP.

Detalle del comprobante:
- Tipo: {invoice.get_receipt_type_display()}
- Número: {invoice.display_number}
- CAE: {invoice.cae}
- Vencimiento CAE: {invoice.cae_expiration}
- Total: ${invoice.total_amount:,.2f}

Este comprobante tiene plena validez legal según normativa AFIP.

Saludos cordiales,
{settings.COMPANY_NAME}
"""
    
    # Create email
    email = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invoice.sale.customer.email]
    )
    
    # Attach PDF
    filename = f"Factura_{invoice.receipt_type}_{invoice.id}_{invoice.cae}.pdf"
    email.attach(filename, pdf_buffer.getvalue(), 'application/pdf')
    
    # Send
    email.send()
    logger.info(f"Email sent to {invoice.sale.customer.email}")
```

## Configuration

### Settings

```python
# settings.py

# AFIP Configuration
AFIP_DEBUG_MODE = True  # Set to False for production

# Email Configuration (for invoice sending)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # DEBUG
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # PRODUCTION
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'facturacion@yourcompany.com'

COMPANY_NAME = 'Your Company Name'
```

### Production Setup

```bash
# 1. Configure django-afip in Django admin
# - Upload certificate (.crt)
# - Upload private key (.key)
# - Enter company CUIT

# 2. Fetch points of sale from AFIP
uv run python src/manage.py afip_fetch_points_of_sales

# 3. Disable DEBUG mode
# In settings.py:
AFIP_DEBUG_MODE = False
```

## Error Handling

### Common Errors

**"Only completed sales can be invoiced"**
- Cause: Sale not in COMPLETED status
- Solution: Finalize sale first via `SaleService.finalize_sale()`

**"Sale already has an invoice"**
- Cause: Invoice already exists for this sale
- Solution: Check existing invoice or use different sale

**"Customer has no email address"**
- Cause: Customer email is empty
- Solution: Update customer email or handle gracefully (CAE still authorized)

### Critical: Email Failure After CAE

If email fails AFTER CAE is authorized:
- CAE is already registered with AFIP (cannot be undone)
- System logs warning but returns success
- Manual resend available:

```python
invoice = Invoice.objects.get(pk=invoice_id)
pdf_buffer = InvoiceService.generate_pdf(invoice)
InvoiceService.send_invoice_email(invoice, pdf_buffer)
```

## Testing

### Example Flow

```python
# In Django shell
from invoices.services import InvoiceService
from sale.services import SaleService

# 1. Create and finalize sale (assuming sale exists)
sale = SaleService.finalize_sale(sale_id=1, user=request.user)

# 2. Process AFIP
result = InvoiceService.procesar_venta_afip(sale.id, user)

# 3. Check result
print(f"Success: {result['success']}")
print(f"CAE: {result['cae']}")
print(f"Email sent: {result['email_sent']}")
```

### Test Factura A (RI → RI)

```python
# Create RI customer
from customers.models import Customer, TaxCategory

customer_ri = Customer.objects.create(
    first_name='Empresa',
    last_name='SA',
    email='empresa@example.com',
    tax_id='30-12345678-9',
    tax_category=TaxCategory.RESPONSABLE_INSCRIPTO
)

# Process sale with RI customer
result = InvoiceService.procesar_venta_afip(sale_id, user)

# Should generate Factura A with VAT aliquots
invoice = result['invoice']
assert invoice.receipt_type == 'A'
assert invoice.vat_aliquots.exists()
```

## Additional Resources

For related information, see:
- [project-best-practices](../project-best-practices/SKILL.md) - Service layer patterns
- [django-backend](../django-backend/SKILL.md) - Transaction handling
- [project-context](../project-context/SKILL.md) - Django-afip dependency info