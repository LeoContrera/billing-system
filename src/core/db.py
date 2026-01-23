"""
Configuración de base de datos SQLite para el sistema POS.

Este módulo configura SQLite con optimizaciones para un sistema local
que requiere concurrencia entre lecturas y escrituras.
"""

from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def configure_sqlite(sender, connection, **kwargs):
    """
    Configura SQLite para mejor concurrencia en POS local.

    WAL Mode (Write-Ahead Logging):
    - Permite lecturas concurrentes durante escrituras
    - Mejora el rendimiento en aplicaciones con múltiples operaciones simultáneas

    Synchronous NORMAL:
    - Balance entre seguridad y velocidad
    - Adecuado para sistemas POS locales

    Busy Timeout:
    - Espera hasta 5 segundos si la BD está bloqueada
    - Previene errores de "database is locked"
    """
    if connection.vendor == 'sqlite':
        cursor = connection.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('PRAGMA synchronous=NORMAL;')
        cursor.execute('PRAGMA busy_timeout=5000;')
