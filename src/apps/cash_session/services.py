"""
Capa de servicio para gestión de sesiones de caja.

Este módulo implementa el Service Layer Pattern con transacciones atómicas
para garantizar la integridad de las operaciones de caja.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import CashSession, CashSessionStatus


class CashSessionService:
    """
    Lógica de negocio para gestión de sesiones de caja.

    Métodos:
        open_session: Abre nueva sesión de caja para un usuario
        get_active_session: Obtiene la sesión activa de un usuario
    """

    @staticmethod
    @transaction.atomic
    def open_session(user, opening_balance: Decimal = Decimal('0.00')) -> CashSession:
        """
        Abre nueva sesión de caja para un usuario.

        Args:
            user: Usuario (cajero) que abre la sesión
            opening_balance: Balance inicial de efectivo en caja

        Returns:
            CashSession: Nueva sesión creada

        Raises:
            ValidationError: Si el usuario ya tiene una sesión abierta

        Patrón: Factory Method + Guard Clause
        """
        # Verificar si el usuario ya tiene una sesión abierta
        existing_session = CashSession.objects.filter(
            user=user,
            status=CashSessionStatus.OPEN
        ).first()

        if existing_session:
            raise ValidationError(
                "Ya tienes una caja abierta. Debes cerrarla antes de abrir una nueva."
            )

        # Crear nueva sesión
        session = CashSession.objects.create(
            user=user,
            opening_balance=opening_balance,
            status=CashSessionStatus.OPEN
        )

        return session

    @staticmethod
    def get_active_session(user) -> CashSession | None:
        """
        Obtiene la sesión activa de un usuario.

        Args:
            user: Usuario cuya sesión activa se busca

        Returns:
            CashSession | None: Sesión activa o None si no existe
        """
        return CashSession.objects.filter(
            user=user,
            status=CashSessionStatus.OPEN
        ).first()
