"""
Modelos para la gestión de sesiones de caja del sistema POS.

Este módulo define el modelo CashSession que rastrea los turnos de cajero,
incluyendo apertura, cierre y balance de efectivo.
"""

from django.db import models
from django.conf import settings
from decimal import Decimal


class CashSessionStatus(models.TextChoices):
    """Estados de la sesión de caja."""
    OPEN = 'OPEN', 'Abierta'
    CLOSED = 'CLOSED', 'Cerrada'


class CashSession(models.Model):
    """
    Sesión de caja (turno de cajero).

    Attributes:
        user: Usuario (cajero) responsable de la sesión
        opening_timestamp: Fecha y hora de apertura de la sesión
        closing_timestamp: Fecha y hora de cierre de la sesión (null si está abierta)
        opening_balance: Balance inicial de efectivo en caja
        closing_balance: Balance final de efectivo en caja (null si está abierta)
        status: Estado de la sesión (OPEN o CLOSED)

    Properties:
        expected_closing_balance: Balance esperado basado en transacciones (futuro)
        variance: Diferencia entre balance real y esperado (futuro)

    Meta:
        ordering: Ordenado por fecha de apertura descendente
        indexes: Índices para optimizar búsquedas por usuario y estado

    Patrones:
        - PROTECT en user: no se puede eliminar usuario con sesiones
        - Solo una sesión abierta por usuario a la vez (validar en servicio)
        - Closing fields null=True hasta que se cierra la sesión
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cash_sessions',
        verbose_name="Cajero",
        help_text="Usuario responsable de esta sesión de caja"
    )
    opening_timestamp = models.DateTimeField(
        "Fecha de Apertura",
        auto_now_add=True,
        help_text="Fecha y hora en que se abrió la sesión"
    )
    closing_timestamp = models.DateTimeField(
        "Fecha de Cierre",
        null=True,
        blank=True,
        help_text="Fecha y hora en que se cerró la sesión"
    )
    opening_balance = models.DecimalField(
        "Balance de Apertura",
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Efectivo inicial en caja al abrir el turno"
    )
    closing_balance = models.DecimalField(
        "Balance de Cierre",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Efectivo final en caja al cerrar el turno"
    )
    status = models.CharField(
        "Estado",
        max_length=10,
        choices=CashSessionStatus.choices,
        default=CashSessionStatus.OPEN
    )

    class Meta:
        ordering = ['-opening_timestamp']
        indexes = [
            models.Index(fields=['user', 'status']),  # Para buscar sesiones activas por usuario
            models.Index(fields=['status']),  # Para listar sesiones abiertas
        ]
        verbose_name = "Sesión de Caja"
        verbose_name_plural = "Sesiones de Caja"

    def __str__(self):
        return f"Sesión #{self.pk} - {self.user.username} - {self.get_status_display()}"

    @property
    def duration(self):
        """
        Duración de la sesión.

        Returns:
            timedelta si está cerrada, None si está abierta
        """
        if self.closing_timestamp:
            return self.closing_timestamp - self.opening_timestamp
        return None

    @property
    def is_open(self):
        """Verifica si la sesión está abierta."""
        return self.status == CashSessionStatus.OPEN

    @property
    def is_closed(self):
        """Verifica si la sesión está cerrada."""
        return self.status == CashSessionStatus.CLOSED
