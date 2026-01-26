"""
Vistas para gestión de productos.
"""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .services import ProductService


@login_required
@require_GET
def product_list(request):
    """
    Lista de productos con filtros y búsqueda.

    GET /products/
    GET /products/?search=<query>&order_by=<field>&show_inactive=on

    Esta vista maneja tanto la carga inicial como las peticiones HTMX
    para actualizar la tabla dinámicamente.
    """
    # Obtener parámetros de búsqueda y filtros
    search_query = request.GET.get("search", "").strip()
    order_by = request.GET.get("order_by", "name")
    show_inactive = request.GET.get("show_inactive") == "on"

    # Obtener productos filtrados
    products = ProductService.list_products(
        search_query=search_query,
        order_by=order_by,
        show_inactive=show_inactive,
    )

    context = {
        "products": products,
        "search_query": search_query,
        "order_by": order_by,
        "show_inactive": show_inactive,
    }

    # Si es petición HTMX, solo renderizar la tabla
    if request.headers.get("HX-Request"):
        return render(request, "products/_product_table.html", context)

    # Carga inicial: renderizar página completa
    return render(request, "products/index.html", context)


@login_required
@require_POST
def product_create(request):
    """
    Crea un nuevo producto.

    POST /products/create/

    Form data:
        - sku: Código único del producto
        - name: Nombre del producto
        - price: Precio de venta
        - cost: Costo (opcional)
        - description: Descripción (opcional)
    """
    try:
        sku = request.POST.get("sku", "").strip().upper()
        name = request.POST.get("name", "").strip()
        price_str = request.POST.get("price", "0")
        cost_str = request.POST.get("cost", "")
        description = request.POST.get("description", "").strip()

        # Validar campos requeridos
        if not sku:
            raise ValidationError("El SKU es requerido")
        if not name:
            raise ValidationError("El nombre es requerido")

        # Convertir precio
        try:
            price = Decimal(price_str)
        except (InvalidOperation, ValueError):
            raise ValidationError("Precio inválido")

        # Convertir costo (opcional)
        cost = None
        if cost_str:
            try:
                cost = Decimal(cost_str)
            except (InvalidOperation, ValueError):
                raise ValidationError("Costo inválido")

        # Crear producto usando el servicio
        product = ProductService.create_product(
            sku=sku,
            name=name,
            price=price,
            description=description,
            cost=cost,
        )

        messages.success(
            request,
            f'Producto "{product.name}" creado exitosamente',
        )

    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error al crear producto: {str(e)}")

    return redirect("products:list")


@login_required
@require_POST
def product_update(request, sku):
    """
    Actualiza un producto existente.

    POST /products/<sku>/update/

    Form data:
        - name: Nombre del producto
        - price: Precio de venta
        - cost: Costo (opcional)
        - description: Descripción (opcional)
    """
    try:
        name = request.POST.get("name", "").strip()
        price_str = request.POST.get("price")
        cost_str = request.POST.get("cost", "")
        description = request.POST.get("description", "").strip()

        # Validar campos requeridos
        if not name:
            raise ValidationError("El nombre es requerido")

        # Convertir precio
        price = None
        if price_str:
            try:
                price = Decimal(price_str)
            except (InvalidOperation, ValueError):
                raise ValidationError("Precio inválido")

        # Convertir costo (opcional)
        cost = None
        if cost_str:
            try:
                cost = Decimal(cost_str)
            except (InvalidOperation, ValueError):
                raise ValidationError("Costo inválido")

        # Actualizar producto usando el servicio
        product = ProductService.update_product(
            sku=sku,
            name=name,
            price=price,
            description=description,
            cost=cost,
        )

        messages.success(
            request,
            f'Producto "{product.name}" actualizado exitosamente',
        )

    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error al actualizar producto: {str(e)}")

    return redirect("products:list")


@login_required
@require_POST
def toggle_active(request, sku):
    """
    Alterna el estado activo/inactivo de un producto.

    POST /products/<sku>/toggle-active/
    """
    try:
        product = ProductService.toggle_active(sku)

        status_text = "activado" if product.is_active else "desactivado"
        messages.success(
            request,
            f'Producto "{product.name}" {status_text} exitosamente',
        )

    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error al cambiar estado: {str(e)}")

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

    GET /products/<sku>/detail/
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
