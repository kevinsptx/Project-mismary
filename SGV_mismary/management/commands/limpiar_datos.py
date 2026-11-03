"""
Borra los datos del NEGOCIO (clientes, productos, ventas, pedidos, gastos...).

NO borra usuarios, grupos ni permisos, así que puedes seguir entrando con
tu cuenta. Antes de borrar hace una copia de seguridad de db.sqlite3.

Uso:
    python manage.py limpiar_datos          (pide confirmación)
    python manage.py limpiar_datos --si     (sin preguntar)
"""
import shutil
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from SGV_mismary.models import (
    Abono, Categoria, Cliente, DetallePedido, DetalleVenta, Deuda, Gasto,
    Pago, Pedido, Producto, Proveedor, Reembolso, Venta,
)

# Orden: primero lo que depende de otras tablas, al final lo "principal".
MODELOS_EN_ORDEN = [
    Reembolso, Abono, Pago, DetalleVenta, Deuda, Venta,
    DetallePedido, Pedido, Gasto,
    Producto, Categoria, Cliente, Proveedor,
]


def borrar_datos_negocio():
    """Borra todo lo del negocio y reinicia los contadores de id (SQLite)."""
    with transaction.atomic():
        for modelo in MODELOS_EN_ORDEN:
            modelo.objects.all().delete()

        if connection.vendor == 'sqlite':
            tablas = [m._meta.db_table for m in MODELOS_EN_ORDEN]
            marcas = ', '.join(['%s'] * len(tablas))
            with connection.cursor() as cursor:
                cursor.execute(
                    f'DELETE FROM sqlite_sequence WHERE name IN ({marcas})',
                    tablas,
                )


def hacer_respaldo():
    """Copia db.sqlite3 antes de borrar. Devuelve la ruta (o None)."""
    base = settings.DATABASES['default']
    if base['ENGINE'] != 'django.db.backends.sqlite3':
        return None

    origen = str(base['NAME'])
    sello = datetime.now().strftime('%Y%m%d-%H%M%S')
    destino = f'{origen}.respaldo-{sello}'
    shutil.copy2(origen, destino)
    return destino


class Command(BaseCommand):
    help = 'Borra los datos del negocio (deja intactos usuarios y grupos).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--si', action='store_true',
            help='No pedir confirmación.',
        )

    def handle(self, *args, **opciones):
        if not opciones['si']:
            self.stdout.write(self.style.WARNING(
                'Esto borrará clientes, productos, ventas, pedidos, abonos, '
                'deudas y gastos. Los usuarios y grupos NO se borran.'
            ))
            respuesta = input('Escribe "si" para continuar: ').strip().lower()
            if respuesta != 'si':
                raise CommandError('Cancelado. No se borró nada.')

        respaldo = hacer_respaldo()
        if respaldo:
            self.stdout.write(f'Respaldo guardado en: {respaldo}')

        borrar_datos_negocio()
        self.stdout.write(self.style.SUCCESS('Listo: los datos del negocio quedaron en blanco.'))