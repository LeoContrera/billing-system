"""Script para crear stocks iniciales de productos."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.models import Product
from inventory.models import Stock
from decimal import Decimal

def create_initial_stocks():
    """Crea stocks iniciales para productos activos."""
    productos = Product.objects.filter(is_active=True)
    print(f"\nProductos activos encontrados: {productos.count()}\n")

    created_count = 0
    updated_count = 0

    for producto in productos:
        stock, created = Stock.objects.get_or_create(
            product=producto,
            location='PRINCIPAL',
            defaults={
                'current_qty': Decimal('50'),
                'min_qty': Decimal('10'),
                'max_qty': Decimal('200')
            }
        )

        if created:
            print(f"[CREADO] {producto.sku} - {producto.name}")
            print(f"  Stock: {stock.current_qty} (Min: {stock.min_qty}, Max: {stock.max_qty})")
            created_count += 1
        else:
            print(f"[EXISTE]  {producto.sku} - {producto.name}")
            print(f"  Stock actual: {stock.current_qty}")
            updated_count += 1

    print(f"\n=== Resumen ===")
    print(f"Stocks creados: {created_count}")
    print(f"Stocks existentes: {updated_count}")
    print(f"Total: {created_count + updated_count}")

if __name__ == '__main__':
    create_initial_stocks()
