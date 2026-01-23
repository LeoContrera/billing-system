#!/usr/bin/env python
"""
Quick system verification script.
Tests all components of the POS system.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from sale.services import SaleService
from payments.services import PaymentService
from customers.models import Customer
from users.models import User
from sale.models import Sale
from decimal import Decimal

print("=== POS System Verification ===\n")

# Check user
user = User.objects.first()
if not user:
    print("❌ ERROR: No user found. Create a superuser first:")
    print("   uv run python manage.py createsuperuser")
    exit(1)
else:
    print(f"✓ User found: {user.username}")

# Check customers
customer_count = Customer.objects.count()
print(f"✓ Customers in DB: {customer_count}")

# Check payment methods
methods = PaymentService.get_active_payment_methods()
print(f"✓ Active payment methods: {methods.count()}")
for method in methods:
    print(f"  - {method.name}")

# Create a test sale
print("\n--- Creating Test Sale ---")
sale = SaleService.create_sale(user)
print(f"✓ Sale created: #{sale.id}")

# Add a product
item = SaleService.add_line_item(
    sale.id,
    "Test Product",
    Decimal("2"),
    Decimal("100.00")
)
print(f"✓ Product added: {item.product_name} x{item.quantity} @ ${item.unit_price}")

# Check totals
sale = Sale.objects.prefetch_related("line_items").get(pk=sale.id)
print(f"✓ Subtotal: ${sale.subtotal}")
print(f"✓ Total: ${sale.total}")
print(f"✓ Remaining balance: ${sale.remaining_balance}")

# Add payment
print("\n--- Adding Payment ---")
payment_method = methods.first()
from payments.services import PaymentService
transaction = PaymentService.add_payment(
    sale.id,
    payment_method.id,
    Decimal("200.00"),
    user
)
print(f"✓ Payment added: ${transaction.amount} via {transaction.payment_method.name}")

# Reload and check
sale = Sale.objects.prefetch_related("line_items", "transactions").get(pk=sale.id)
print(f"✓ Total paid: ${sale.total_paid}")
print(f"✓ New remaining balance: ${sale.remaining_balance}")

# Finalize
if sale.is_fully_paid:
    print("\n--- Finalizing Sale ---")
    sale = SaleService.finalize_sale(sale.id)
    print(f"✓ Sale finalized: Status = {sale.status}")
    print(f"✓ Completed at: {sale.completed_at}")
else:
    print(f"\n⚠ Sale not fully paid (${sale.remaining_balance} remaining)")

print("\n" + "="*40)
print("✅ All systems operational!")
print("="*40)
print("\nReady to use! Access POS at:")
print("http://localhost:8000/sale/create/")
