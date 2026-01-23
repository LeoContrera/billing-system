"""
Capa de servicio para gestión de clientes.

Este módulo implementa el Service Layer Pattern, separando la lógica
de negocio de las vistas (controllers).
"""

from django.db.models import Q, QuerySet
from .models import Customer


class CustomerService:
    """
    Lógica de negocio para gestión de clientes.

    Métodos:
        search_customers: Búsqueda typeahead por nombre o DNI
        get_or_create_quick: Creación rápida durante venta
    """

    @staticmethod
    def search_customers(query: str, limit: int = 10) -> QuerySet[Customer]:
        """
        Búsqueda de clientes por nombre o DNI (typeahead).

        Args:
            query: Texto de búsqueda
            limit: Cantidad máxima de resultados (default: 10)

        Returns:
            QuerySet con clientes que coinciden con la búsqueda

        Patrones ORM usados:
            - Q objects para consultas OR complejas
            - icontains para búsqueda case-insensitive
            - only() para fetch optimizado (solo campos necesarios)
        """
        if not query:
            return Customer.objects.none()

        # Búsqueda por apellido, nombre o DNI
        return Customer.objects.filter(
            Q(last_name__icontains=query) |
            Q(first_name__icontains=query) |
            Q(tax_id__icontains=query)
        ).only('id', 'first_name', 'last_name', 'tax_id')[:limit]

    @staticmethod
    def get_or_create_quick(first_name: str, last_name: str, **kwargs) -> tuple[Customer, bool]:
        """
        Crea cliente rápido durante venta.

        Args:
            first_name: Nombre del cliente
            last_name: Apellido del cliente
            **kwargs: Campos adicionales (email, phone, etc.)

        Returns:
            Tupla (customer, created) donde created es True si se creó nuevo

        Ejemplo:
            customer, created = CustomerService.get_or_create_quick(
                first_name="Juan",
                last_name="Pérez",
                phone="123456789"
            )
        """
        return Customer.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            defaults=kwargs
        )
