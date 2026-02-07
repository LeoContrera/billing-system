"""
Servicios para el dashboard.

Encapsula la lógica de negocio para obtener datos del dashboard.
"""

from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone

from cash_session.models import CashSession
from sale.models import Sale


class DashboardService:
    """Servicio para obtener datos del dashboard."""

    @staticmethod
    def get_weekly_performance():
        """
        Obtiene el rendimiento semanal del negocio.

        Returns:
            dict: Datos de rendimiento incluyendo ventas, sesiones, etc.
        """
        # Obtener fecha de hace 7 días
        seven_days_ago = timezone.now() - timedelta(days=7)

        # Ventas de la última semana (con line_items precargados para calcular totales)
        weekly_sales = Sale.objects.filter(
            created_at__gte=seven_days_ago,
            status='COMPLETED'
        ).prefetch_related('line_items', 'transactions')

        total_sales = weekly_sales.count()

        # Calcular ingresos totales usando la propiedad total de cada venta
        total_revenue = sum(sale.total for sale in weekly_sales) if total_sales > 0 else Decimal('0.00')

        # Sesiones de caja de la última semana
        weekly_sessions = CashSession.objects.filter(
            opening_timestamp__gte=seven_days_ago
        )

        total_sessions = weekly_sessions.count()
        closed_sessions = weekly_sessions.filter(status='CLOSED').count()

        return {
            'total_sales': total_sales,
            'total_revenue': total_revenue,
            'total_sessions': total_sessions,
            'closed_sessions': closed_sessions,
            'average_sale': total_revenue / total_sales if total_sales > 0 else Decimal('0.00'),
        }

    @staticmethod
    def get_daily_breakdown():
        """
        Obtiene el desglose diario de ventas para la última semana.

        Returns:
            list: Lista de diccionarios con datos por día
        """
        seven_days_ago = timezone.now() - timedelta(days=7)
        daily_data = []

        for i in range(7):
            day_start = seven_days_ago + timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            daily_sales = Sale.objects.filter(
                created_at__gte=day_start,
                created_at__lt=day_end,
                status='COMPLETED'
            ).prefetch_related('line_items')

            count = daily_sales.count()
            # Calcular total usando la propiedad total de cada venta
            total = sum(sale.total for sale in daily_sales) if count > 0 else Decimal('0.00')

            daily_data.append({
                'date': day_start.strftime('%d/%m'),
                'day_name': day_start.strftime('%a'),
                'sales_count': count,
                'total_revenue': total,
            })

        return daily_data

    @staticmethod
    def get_recent_cash_sessions(limit=10):
        """
        Obtiene las últimas sesiones de caja.

        Args:
            limit (int): Número de sesiones a retornar

        Returns:
            QuerySet: Últimas sesiones de caja
        """
        return CashSession.objects.select_related('user').order_by('-opening_timestamp')[:limit]
