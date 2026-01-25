"""
Vistas para gestión de productos.
"""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .services import ProductService


@login_required
@require_GET
def product_list(request):
    """
    Vista principal: lista de productos con búsqueda y filtrado.

    GET /products/
    """
    search_query = request.GET.get("search", "")
    show_inactive = request.GET.get("show_inactive", "") == "on"
    order_by = request.GET.get("order_by", "name")

    products = ProductService.get_all_products(
        search_query=search_query,
        show_inactive=show_inactive,
        order_by=order_by
    )

    context = {
        "products": products,
        "search_query": search_query,
        "show_inactive": show_inactive,
        "order_by": order_by,
    }

    # Si es petición HTMX, solo devolver la tabla
    if request.headers.get("HX-Request"):
        return render(request, "products/_product_table.html", context)

    return render(request, "products/index.html", context)


@login_required
@require_POST
def product_create(request):
    """
    Crea un nuevo producto.

    POST /products/create/
    """
    try:
        sku = request.POST.get("sku", "").strip()
        name = request.POST.get("name", "").strip()
        price_str = request.POST.get("price", "0")
        cost_str = request.POST.get("cost", "")
        description = request.POST.get("description", "").strip()

        # Validar campos requeridos
        if not sku or not name:
            raise ValidationError("SKU y Nombre son requeridos")

        # Parsear precio
        try:
            price = Decimal(price_str)
        except (InvalidOperation, ValueError):
            raise ValidationError("Precio inválido")

        # Parsear costo (opcional)
        cost = None
        if cost_str:
            try:
                cost = Decimal(cost_str)
            except (InvalidOperation, ValueError):
                raise ValidationError("Costo inválido")

        # Crear producto
        ProductService.create_product(
            sku=sku,
            name=name,
            price=price,
            description=description,
            cost=cost
        )

        messages.success(request, f"Producto '{name}' creado exitosamente")

    except ValidationError as e:
        messages.error(request, str(e))

    # Redirigir a la lista
    return redirect("products:list")


@login_required
@require_POST
def product_update(request, sku):
    """
    Actualiza un producto existente.

    POST /products/<sku>/update/
    """
    try:
        name = request.POST.get("name", "").strip()
        price_str = request.POST.get("price", "")
        cost_str = request.POST.get("cost", "")
        description = request.POST.get("description", "").strip()

        # Parsear precio
        price = None
        if price_str:
            try:
                price = Decimal(price_str)
            except (InvalidOperation, ValueError):
                raise ValidationError("Precio inválido")

        # Parsear costo
        cost = None
        if cost_str:
            try:
                cost = Decimal(cost_str)
            except (InvalidOperation, ValueError):
                raise ValidationError("Costo inválido")

        # Actualizar producto
        ProductService.update_product(
            sku=sku,
            name=name if name else None,
            price=price,
            description=description if description else None,
            cost=cost
        )

        messages.success(request, f"Producto actualizado exitosamente")

    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("products:list")


@login_required
@require_POST
def product_toggle_active(request, sku):
    """
    Activa/desactiva un producto.

    POST /products/<sku>/toggle-active/
    """
    try:
        product = ProductService.get_product_info(sku)
        if not product:
            raise ValidationError("Producto no encontrado")

        if product.is_active:
            ProductService.deactivate_product(sku)
            messages.success(request, f"Producto '{product.name}' desactivado")
        else:
            ProductService.reactivate_product(sku)
            messages.success(request, f"Producto '{product.name}' reactivado")

    except ValidationError as e:
        messages.error(request, str(e))

    return redirect("products:list")


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
            "cost": str(product.cost) if product.cost else None,
            "description": product.description,
            "is_active": product.is_active,
        }
    )
