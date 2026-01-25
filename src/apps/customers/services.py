"""
Capa de servicio para gestión de clientes.

Este módulo implementa el Service Layer Pattern, separando la lógica
de negocio de las vistas (controllers).
"""

from django.db.models import Q, QuerySet
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Customer, TaxCategory


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

    @staticmethod
    @transaction.atomic
    def create_customer(
        first_name: str,
        last_name: str,
        phone: str = '',
        locality: str = '',
        address: str = '',
        tax_category: str = TaxCategory.CONSUMIDOR_FINAL,
        tax_id: str = ''
    ) -> Customer:
        """
        Crea un nuevo cliente con validación.

        Args:
            first_name: Nombre del cliente (requerido)
            last_name: Apellido del cliente (requerido)
            phone: Número de celular
            locality: Localidad/ciudad
            address: Dirección completa
            tax_category: Categoría tributaria (CF, EX, RI, MT)
            tax_id: DNI/CUIT (opcional para CF, requerido para RI)

        Returns:
            Customer: Cliente creado

        Raises:
            ValidationError: Si los datos son inválidos

        Ejemplo:
            customer = CustomerService.create_customer(
                first_name="Juan",
                last_name="Pérez",
                phone="123456789",
                locality="Buenos Aires",
                tax_category=TaxCategory.RESPONSABLE_INSCRIPTO,
                tax_id="20-12345678-9"
            )
        """
        # Validaciones
        if not first_name or not last_name:
            raise ValidationError("Nombre y apellido son requeridos")

        # Si es Responsable Inscripto, CUIT es obligatorio
        if tax_category == TaxCategory.RESPONSABLE_INSCRIPTO and not tax_id:
            raise ValidationError("CUIT es obligatorio para Responsable Inscripto")

        # Verificar si ya existe cliente con mismo tax_id (si se provee)
        if tax_id:
            existing = Customer.objects.filter(tax_id=tax_id).first()
            if existing:
                raise ValidationError(f"Ya existe un cliente con DNI/CUIT {tax_id}")

        # Crear cliente
        customer = Customer.objects.create(
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=phone.strip(),
            locality=locality.strip(),
            address=address.strip(),
            tax_category=tax_category,
            tax_id=tax_id.strip() if tax_id else None
        )

        return customer
