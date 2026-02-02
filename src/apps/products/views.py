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

from .models import PriceChangeReason, ProductCategory
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
        category = request.POST.get("category", "OTHER").strip()
        price_str = request.POST.get("price", "0")
        cost_str = request.POST.get("cost", "")
        description = request.POST.get("description", "").strip()

        # Validar campos requeridos
        if not sku:
            raise ValidationError("El SKU es requerido")
        if not name:
            raise ValidationError("El nombre es requerido")

        # Validar categoría
        if category not in dict(ProductCategory.choices):
            raise ValidationError("Categoría inválida")

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
            category=category,
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
        category = request.POST.get("category", "").strip()
        price_str = request.POST.get("price")
        cost_str = request.POST.get("cost", "")
        description = request.POST.get("description", "").strip()

        # Validar campos requeridos
        if not name:
            raise ValidationError("El nombre es requerido")

        # Validar categoría si se proporciona
        if category and category not in dict(ProductCategory.choices):
            raise ValidationError("Categoría inválida")

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
            category=category if category else None,
            price=price,
            description=description,
            cost=cost,
            user=request.user,
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


@login_required
@require_GET
def bulk_price_update_view(request):
    """
    Vista principal para actualización masiva de precios.

    GET /products/actualizar-precios/

    Renderiza la página con el formulario de actualización masiva
    y la vista previa de productos que serán afectados.
    """
    # Obtener todas las categorías disponibles
    categories = ProductCategory.choices

    # Obtener productos activos por defecto
    category_filter = request.GET.get("category", "")
    products = ProductService.list_products(
        show_inactive=False,
        order_by="name"
    )

    # Aplicar filtro de categoría si existe
    if category_filter:
        products = products.filter(category=category_filter)

    context = {
        "categories": categories,
        "products": products,
        "selected_category": category_filter,
    }

    return render(request, "products/bulk_price_update.html", context)


@login_required
@require_GET
def bulk_price_update_filter(request):
    """
    Filtrado dinámico de productos para actualización masiva (HTMX).

    GET /products/actualizar-precios/filtrar/?category=<category>

    Retorna partial HTML con la tabla de productos filtrados.
    """
    category_filter = request.GET.get("category", "")

    # Obtener productos activos
    products = ProductService.list_products(
        show_inactive=False,
        order_by="name"
    )

    # Aplicar filtro de categoría si existe
    if category_filter:
        products = products.filter(category=category_filter)

    context = {
        "products": products,
        "selected_category": category_filter,
    }

    return render(request, "products/_bulk_price_table.html", context)


@login_required
@require_POST
def bulk_price_update_submit(request):
    """
    Procesa la actualización masiva de precios.

    POST /products/actualizar-precios/aplicar/

    Form data:
        - percentage_adjustment: Porcentaje de ajuste (puede ser negativo)
        - category: Categoría a actualizar (opcional, vacío = todas)
    """
    try:
        # Obtener datos del formulario
        percentage_str = request.POST.get("percentage_adjustment", "0")
        category = request.POST.get("category", "").strip()

        # Convertir porcentaje
        try:
            percentage_adjustment = Decimal(percentage_str)
        except (InvalidOperation, ValueError):
            raise ValidationError("Porcentaje de ajuste inválido")

        # Validar categoría
        if category and category not in dict(ProductCategory.choices):
            raise ValidationError("Categoría inválida")

        # Aplicar actualización masiva
        result = ProductService.bulk_update_prices(
            percentage_adjustment=percentage_adjustment,
            category=category if category else None,
            only_active=True,
            user=request.user,
        )

        # Mensaje de éxito
        category_text = result['category_display'] if result['category'] else "todas las categorías"
        adjustment_text = f"+{percentage_adjustment}%" if percentage_adjustment > 0 else f"{percentage_adjustment}%"

        messages.success(
            request,
            f"Actualización exitosa: {result['updated_count']} producto(s) de {category_text} "
            f"ajustados en {adjustment_text}"
        )

    except ValidationError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, f"Error al actualizar precios: {str(e)}")

    return redirect("products:bulk_price_update")


@login_required
@require_GET
def price_history_view(request):
    """
    Vista principal del historial de cambios de precios.

    GET /products/historial-precios/
    GET /products/historial-precios/?sku=<sku>&reason=<reason>&limit=<limit>

    Muestra todos los cambios de precios con filtros opcionales.
    """
    # Obtener parámetros de filtro
    product_sku = request.GET.get("sku", "").strip()
    reason = request.GET.get("reason", "").strip()
    limit_str = request.GET.get("limit", "100")

    # Convertir limit
    try:
        limit = int(limit_str)
        if limit < 1 or limit > 500:
            limit = 100
    except ValueError:
        limit = 100

    # Obtener historial filtrado
    history = ProductService.get_price_history(
        product_sku=product_sku if product_sku else None,
        reason=reason if reason else None,
        limit=limit,
    )

    # Obtener lista de razones disponibles para el filtro
    reasons = PriceChangeReason.choices

    # Obtener producto si se filtró por SKU
    product = None
    if product_sku:
        product = ProductService.get_product_info(product_sku)

    context = {
        "history": history,
        "reasons": reasons,
        "selected_sku": product_sku,
        "selected_reason": reason,
        "limit": limit,
        "product": product,
    }

    return render(request, "products/price_history.html", context)


@login_required
@require_GET
def price_history_filter(request):
    """
    Filtrado dinámico de historial (HTMX).

    GET /products/historial-precios/filtrar/?sku=<sku>&reason=<reason>&limit=<limit>

    Retorna partial HTML con la tabla de historial filtrada.
    """
    # Obtener parámetros de filtro
    product_sku = request.GET.get("sku", "").strip()
    reason = request.GET.get("reason", "").strip()
    limit_str = request.GET.get("limit", "100")

    # Convertir limit
    try:
        limit = int(limit_str)
        if limit < 1 or limit > 500:
            limit = 100
    except ValueError:
        limit = 100

    # Obtener historial filtrado
    history = ProductService.get_price_history(
        product_sku=product_sku if product_sku else None,
        reason=reason if reason else None,
        limit=limit,
    )

    context = {
        "history": history,
    }

    return render(request, "products/_price_history_table.html", context)


@login_required
@require_GET
def bulk_operations_view(request):
    """
    Vista de operaciones masivas realizadas.

    GET /products/operaciones-masivas/

    Muestra un resumen de todas las operaciones masivas de actualización de precios.
    """
    # Obtener resumen de operaciones masivas
    bulk_operations = ProductService.get_bulk_operations()

    context = {
        "bulk_operations": bulk_operations,
    }

    return render(request, "products/bulk_operations.html", context)


@login_required
@require_GET
def bulk_operation_detail(request, bulk_id):
    """
    Detalle de una operación masiva específica.

    GET /products/operaciones-masivas/<bulk_id>/

    Muestra todos los cambios de precios de una operación masiva.
    """
    # Obtener historial de la operación masiva
    history = ProductService.get_price_history(
        bulk_operation_id=bulk_id,
        limit=500,
    )

    if not history:
        messages.error(request, "Operación masiva no encontrada")
        return redirect("products:bulk_operations")

    # Información general de la operación
    first_record = history.first()

    context = {
        "history": history,
        "bulk_operation": {
            "id": bulk_id,
            "changed_at": first_record.changed_at,
            "changed_by": first_record.changed_by,
            "notes": first_record.notes,
            "products_count": history.count(),
            "change_percentage": first_record.change_percentage,
        }
    }

    return render(request, "products/bulk_operation_detail.html", context)
