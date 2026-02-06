"""Script para crear productos de prueba con diferentes niveles de stock."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from products.models import Product
from inventory.models import Stock
from decimal import Decimal

def create_test_stocks():
    """Crea stocks de prueba con diferentes niveles para testing."""

    # Verificar que exista al menos un producto
    productos = list(Product.objects.filter(is_active=True))

    if not productos:
        print("WARNING: No hay productos activos. Crea productos primero.")
        return

    print(f"\nConfigurando stocks de prueba para {len(productos)} producto(s)...\n")

    # Configuraciones de prueba
    configs = [
        {'qty': Decimal('5'), 'min': Decimal('10'), 'max': Decimal('100'), 'status': 'CRITICO'},
        {'qty': Decimal('12'), 'min': Decimal('10'), 'max': Decimal('100'), 'status': 'WARNING'},
        {'qty': Decimal('50'), 'min': Decimal('10'), 'max': Decimal('200'), 'status': 'NORMAL'},
    ]

    for idx, producto in enumerate(productos[:3]):  # Máximo 3 productos para prueba
        config = configs[idx % len(configs)]

        stock, created = Stock.objects.update_or_create(
            product=producto,
            location='PRINCIPAL',
            defaults={
                'current_qty': config['qty'],
                'min_qty': config['min'],
                'max_qty': config['max']
            }
        )

        action = "CREADO" if created else "ACTUALIZADO"
        print(f"[{action}] {producto.sku} - {producto.name}")
        print(f"  {config['status']} Stock: {stock.current_qty} (Min: {stock.min_qty})")
        print()

    # Resumen
    from inventory.services import InventoryService
    low_stock = InventoryService.get_products_below_minimum()

    print("=" * 50)
    print(f"Configuracion completada")
    print(f"Productos con stock bajo: {len(low_stock)}")
    for stock in low_stock:
        print(f"   - {stock.product.sku}: {stock.current_qty}/{stock.min_qty}")
    print("=" * 50)

if __name__ == '__main__':
    create_test_stocks()
