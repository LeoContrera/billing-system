"""
Modelos para la gestión de clientes del sistema POS.

Este módulo define el modelo Customer que almacena información
de los clientes que realizan compras en el sistema.
"""

from django.db import models


class TaxCategory(models.TextChoices):
    """Categorías tributarias para clientes."""
    CONSUMIDOR_FINAL = 'CF', 'Consumidor Final'
    EXENTO = 'EX', 'Exento'
    RESPONSABLE_INSCRIPTO = 'RI', 'Responsable Inscripto'
    MONOTRIBUTO = 'MT', 'Monotributo'


class Customer(models.Model):
    """
    Cliente del sistema POS.

    Attributes:
        first_name: Nombre del cliente
        last_name: Apellido del cliente
        tax_id: DNI/CUIT (documento de identificación tributaria)
        email: Correo electrónico
        phone: Número de teléfono (celular)
        address: Dirección completa
        locality: Localidad/ciudad
        tax_category: Categoría tributaria (CF, EX, RI, MT)
        created_at: Fecha de creación del registro

    Meta:
        ordering: Ordenado por apellido y nombre
        indexes: Índices para optimizar búsquedas typeahead
    """
    first_name = models.CharField("Nombre", max_length=100)
    last_name = models.CharField("Apellido", max_length=100)
    tax_id = models.CharField("DNI/CUIT", max_length=20, unique=True, blank=True, null=True)
    email = models.EmailField("Email", blank=True)
    phone = models.CharField("Celular", max_length=20, blank=True)
    address = models.TextField("Dirección", blank=True)
    locality = models.CharField("Localidad", max_length=100, blank=True)
    tax_category = models.CharField(
        "Categoría Tributaria",
        max_length=2,
        choices=TaxCategory.choices,
        default=TaxCategory.CONSUMIDOR_FINAL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['last_name']),  # Para búsqueda typeahead
            models.Index(fields=['tax_id']),
        ]

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    @property
    def full_name(self):
        """Retorna el nombre completo del cliente."""
        return f"{self.first_name} {self.last_name}"
