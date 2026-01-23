"""
Vistas para gestión de clientes.

Este módulo implementa vistas delgadas (thin controllers) que delegan
la lógica de negocio a la capa de servicios.
"""

from django.http import JsonResponse
from .services import CustomerService


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
        }
        for c in customers
    ]

    return JsonResponse(data, safe=False)
