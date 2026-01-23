"""
Vistas para gestión de productos.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from .services import ProductService


@login_required
@require_GET
def search_products(request):
    """
    Búsqueda de productos (typeahead para POS).

    GET /products/search/?q=<query>
    """
    query = request.GET.get("q", "")
    products = ProductService.search_products(query, limit=10)

    # Para HTMX: renderiza partial HTML
    if request.headers.get("HX-Request"):
        return render(request, "products/_search_results.html", {"products": products})

    # Para API/JS: retorna JSON
    return JsonResponse(
        {
            "products": [
                {"sku": p.sku, "name": p.name, "price": str(p.price)} for p in products
            ]
        }
    )


@login_required
@require_GET
def product_detail(request, sku):
    """
    Detalle de producto por SKU.

    GET /products/<sku>/
    """
    product = ProductService.get_product_info(sku)

    if not product:
        return JsonResponse({"error": "Producto no encontrado"}, status=404)

    return JsonResponse(
        {
            "sku": product.sku,
            "name": product.name,
            "price": str(product.price),
            "is_active": product.is_active,
        }
    )
