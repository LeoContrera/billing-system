"""
Vistas para gestión de clientes.

Este módulo implementa vistas delgadas (thin controllers) que delegan
la lógica de negocio a la capa de servicios.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError
from .services import CustomerService
from .models import TaxCategory


def search_customers(request):
    """
    Endpoint HTMX para typeahead de clientes.

    GET /customers/search/?q=<query>

    Returns:
        JsonResponse con lista de clientes que coinciden con la búsqueda

    Formato de respuesta:
        [
            {
                "id": 1,
                "full_name": "Pérez, Juan",
                "tax_id": "20123456789"
            },
            ...
        ]
    """
    query = request.GET.get('q', '')
    customers = CustomerService.search_customers(query, limit=10)

    # Formato JSON para HTMX
    data = [
        {
            'id': c.id,
            'full_name': c.full_name,
            'tax_id': c.tax_id or '',
            'tax_category': c.tax_category,
            'tax_category_display': c.get_tax_category_display()
        }
        for c in customers
    ]

    return JsonResponse(data, safe=False)


@require_POST
def create_customer(request):
    """
    Endpoint para crear un nuevo cliente desde el POS.

    POST /customers/create/

    Parámetros POST:
        - first_name: Nombre del cliente
        - last_name: Apellido del cliente
        - phone: Celular
        - locality: Localidad
        - address: Dirección
        - tax_category: Categoría tributaria (CF, EX, RI, MT)
        - tax_id: DNI/CUIT (opcional)

    Returns:
        JsonResponse con datos del cliente creado o error
    """
    try:
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        locality = request.POST.get('locality', '').strip()
        address = request.POST.get('address', '').strip()
        tax_category = request.POST.get('tax_category', TaxCategory.CONSUMIDOR_FINAL)
        tax_id = request.POST.get('tax_id', '').strip()

        customer = CustomerService.create_customer(
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            locality=locality,
            address=address,
            tax_category=tax_category,
            tax_id=tax_id
        )

        return JsonResponse({
            'success': True,
            'customer': {
                'id': customer.id,
                'full_name': customer.full_name,
                'tax_id': customer.tax_id or '',
                'phone': customer.phone,
                'locality': customer.locality,
                'address': customer.address,
                'tax_category': customer.tax_category,
                'tax_category_display': customer.get_tax_category_display()
            }
        })

    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al crear cliente: {str(e)}'
        }, status=500)
