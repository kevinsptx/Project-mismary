"""
Carga datos de EJEMPLO con un flujo completo y coherente:

  1. Se registran categorías, proveedores, clientes y productos.
  2. Se hacen pedidos a proveedores (unos recibidos, uno pendiente y
     uno cancelado). Al recibirlos entra el stock.
  3. Se hacen ventas (pagadas, con abonos, con deuda) con fechas repartidas
     en los últimos ~50 días, una venta de hoy, dos cancelaciones con
     reembolso y varios gastos hormiga.

Las fechas se calculan desde HOY, así los reportes siempre se ven vivos.

Uso:
    python manage.py cargar_datos
    python manage.py cargar_datos --limpiar          (borra antes lo del negocio)
    python manage.py cargar_datos --crear-usuarios   (crea admin_demo y usuario_demo)
"""
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from SGV_mismary.models import (
    Abono, Categoria, Cliente, DetallePedido, DetalleVenta, Deuda, Gasto,
    Pago, Pedido, Producto, Proveedor, Reembolso, Venta,
)

from .limpiar_datos import borrar_datos_negocio, hacer_respaldo


# ------------------------------------------------------------------
# DATOS DE EJEMPLO
# ------------------------------------------------------------------

CATEGORIAS = [
    'Maquillaje', 'Cuidado Facial', 'Cabello', 'Uñas', 'Accesorios',
]

PROVEEDORES = [
    ('Distribuciones Aurora', '3112345678', 'ventas@aurora.co', 'Cra 3 # 12-40, Ibagué'),
    ('Beauty Import Colombia', '3159876543', 'pedidos@beautyimport.co', 'Calle 72 # 10-34, Bogotá'),
    ('Mayorista La Belleza', '3004561230', 'info@mayoristabelleza.co', 'Av. 30 de Agosto # 45-10, Pereira'),
]

# nombre: (categoría, precio de compra, precio de venta)
PRODUCTOS = {
    'Labial Líquido Coral':     ('Maquillaje', 7000, 15000),
    'Rubor en Polvo Rosa':      ('Maquillaje', 8000, 17000),
    'Polvo Compacto Natural':   ('Maquillaje', 9000, 19000),
    'Pestañina Waterproof':     ('Maquillaje', 8500, 18000),
    'Gel Fijador de Cejas':     ('Maquillaje', 5000, 11000),
    'Limpiador Facial Espuma':  ('Cuidado Facial', 11000, 23000),
    'Sérum Vitamina C':         ('Cuidado Facial', 18000, 38000),
    'Mascarilla de Arcilla':    ('Cuidado Facial', 6000, 13000),
    'Shampoo de Keratina':      ('Cabello', 13000, 26000),
    'Mascarilla Capilar':       ('Cabello', 12000, 25000),
    'Aceite de Argán':          ('Cabello', 15000, 32000),
    'Esmalte Gel Rojo':         ('Uñas', 4000, 9000),
    'Set de Limas':             ('Uñas', 3000, 7000),
    'Espejo de Mano':           ('Accesorios', 6000, 14000),
    'Neceser Floral':           ('Accesorios', 10000, 22000),
}

# Producto registrado pero SIN pedido todavía (sin precio ni stock):
# así se ve cómo queda un producto recién creado.
PRODUCTO_SIN_PEDIDO = ('Kit de Pinceles Mini', 'Accesorios')

CLIENTES = [
    ('Paula Andrea Vargas',   '3101112233', 'Barrio La Pola, Ibagué'),
    ('Esteban Molina',        '3112223344', 'Cra 5 # 20-15, Ibagué'),
    ('Natalia Cárdenas',      '3123334455', 'Barrio Jordán, Ibagué'),
    ('Felipe Giraldo',        '3134445566', 'Cádiz, Ibagué'),
    ('Luisa Fernanda Mejía',  '3145556677', 'El Salado, Ibagué'),
    ('Santiago Rincón',       '3156667788', 'Picaleña, Ibagué'),
    ('Karen Beltrán',         '3167778899', 'Ambalá, Ibagué'),
    ('Julián Arias',          '3178889900', 'Calle 42 # 3-18, Ibagué'),
]

# (días atrás del pedido, índice proveedor, estado, días atrás de recepción, líneas)
PEDIDOS = [
    (60, 0, 'Recibido', 57, [('Labial Líquido Coral', 7), ('Rubor en Polvo Rosa', 4),
                             ('Polvo Compacto Natural', 4), ('Pestañina Waterproof', 6),
                             ('Esmalte Gel Rojo', 8), ('Set de Limas', 4),
                             ('Limpiador Facial Espuma', 4)]),
    (42, 1, 'Recibido', 39, [('Sérum Vitamina C', 4), ('Mascarilla de Arcilla', 3),
                             ('Shampoo de Keratina', 3), ('Mascarilla Capilar', 4),
                             ('Aceite de Argán', 3)]),
    (30, 2, 'Cancelado', None, [('Neceser Floral', 5)]),
    (18, 2, 'Recibido', 15, [('Espejo de Mano', 4), ('Neceser Floral', 3),
                             ('Gel Fijador de Cejas', 4), ('Labial Líquido Coral', 3)]),
    (3,  1, 'Pendiente', None, [('Sérum Vitamina C', 6), ('Shampoo de Keratina', 4)]),
]

# Cada venta:
#   dias:   días atrás de la venta
#   cliente: índice en CLIENTES
#   items:  [(producto, cantidad)]
#   pagado: lo que pagó al momento de la venta
#   forma:  forma de pago del pago inicial
#   abonos: [(días atrás, valor, forma)]  pagos posteriores
#   cancelada: None | ('Devuelto', días atrás de la devolución)
VENTAS = [
    dict(dias=54, cliente=0, items=[('Labial Líquido Coral', 2), ('Esmalte Gel Rojo', 1)], pagado=39000, forma='Efectivo'),
    dict(dias=51, cliente=1, items=[('Rubor en Polvo Rosa', 1), ('Pestañina Waterproof', 1)], pagado=15000, forma='Nequi',
         abonos=[(44, 10000, 'Nequi'), (35, 10000, 'Efectivo')]),
    dict(dias=47, cliente=2, items=[('Polvo Compacto Natural', 2), ('Set de Limas', 2)], pagado=52000, forma='Transferencia'),
    dict(dias=43, cliente=3, items=[('Limpiador Facial Espuma', 1), ('Labial Líquido Coral', 1)], pagado=0, forma='Efectivo',
         abonos=[(25, 15000, 'Efectivo')]),
    dict(dias=41, cliente=4, items=[('Esmalte Gel Rojo', 3), ('Pestañina Waterproof', 1)], pagado=20000, forma='Daviplata',
         abonos=[(20, 25000, 'Daviplata')]),
    dict(dias=36, cliente=5, items=[('Sérum Vitamina C', 1), ('Mascarilla de Arcilla', 1)], pagado=51000, forma='Nequi'),
    dict(dias=33, cliente=6, items=[('Shampoo de Keratina', 1), ('Mascarilla Capilar', 1)], pagado=25000, forma='Efectivo',
         abonos=[(14, 26000, 'Nequi')]),
    dict(dias=29, cliente=7, items=[('Labial Líquido Coral', 3), ('Rubor en Polvo Rosa', 1)], pagado=62000, forma='Efectivo',
         cancelada=('Devuelto', 27)),
    dict(dias=26, cliente=0, items=[('Aceite de Argán', 1), ('Esmalte Gel Rojo', 1)], pagado=41000, forma='Transferencia'),
    dict(dias=22, cliente=1, items=[('Sérum Vitamina C', 2)], pagado=40000, forma='Nequi',
         abonos=[(9, 20000, 'Efectivo')]),
    dict(dias=19, cliente=2, items=[('Pestañina Waterproof', 2), ('Limpiador Facial Espuma', 1)], pagado=59000, forma='Efectivo'),
    dict(dias=14, cliente=3, items=[('Espejo de Mano', 1), ('Neceser Floral', 1)], pagado=0, forma='Efectivo'),
    dict(dias=12, cliente=4, items=[('Gel Fijador de Cejas', 2), ('Labial Líquido Coral', 1)], pagado=37000, forma='Nequi'),
    dict(dias=10, cliente=5, items=[('Polvo Compacto Natural', 1), ('Rubor en Polvo Rosa', 1), ('Set de Limas', 1)], pagado=43000, forma='Efectivo'),
    dict(dias=8,  cliente=6, items=[('Neceser Floral', 1), ('Espejo de Mano', 1)], pagado=36000, forma='Daviplata',
         cancelada=('Devuelto', 7)),
    dict(dias=6,  cliente=7, items=[('Shampoo de Keratina', 1), ('Aceite de Argán', 1), ('Mascarilla de Arcilla', 1)], pagado=71000, forma='Transferencia'),
    dict(dias=4,  cliente=2, items=[('Sérum Vitamina C', 1), ('Limpiador Facial Espuma', 1)], pagado=30000, forma='Efectivo',
         abonos=[(1, 15000, 'Nequi')]),
    dict(dias=2,  cliente=0, items=[('Labial Líquido Coral', 2), ('Esmalte Gel Rojo', 2)], pagado=48000, forma='Nequi'),
    dict(dias=1,  cliente=1, items=[('Mascarilla Capilar', 2), ('Espejo de Mano', 1)], pagado=64000, forma='Efectivo'),
    dict(dias=0,  cliente=3, items=[('Pestañina Waterproof', 1), ('Gel Fijador de Cejas', 1)], pagado=29000, forma='Nequi'),
]

# (días atrás, descripción, valor)
GASTOS_HORMIGA = [
    (52, 'Bolsas de papel kraft', 9000),
    (46, 'Pasaje para recoger mercancía', 7500),
    (38, 'Etiquetas y stickers para empaques', 11000),
    (27, 'Impulso de publicaciones en Instagram', 25000),
    (16, 'Domicilio a clientes', 14000),
    (9,  'Tijeras y cinta de embalaje', 8000),
    (1,  'Papel de seda para regalos', 6500),
]


class Command(BaseCommand):
    help = 'Carga datos de ejemplo con un flujo completo y coherente.'

    def add_arguments(self, parser):
        parser.add_argument('--limpiar', action='store_true',
                            help='Borra antes los datos del negocio (hace respaldo).')
        parser.add_argument('--crear-usuarios', action='store_true',
                            help='Crea admin_demo y usuario_demo (clave: demo1234).')

    # ------------------------------------------------------------
    def handle(self, *args, **opciones):
        self.hoy = timezone.localdate()

        if opciones['limpiar']:
            respaldo = hacer_respaldo()
            if respaldo:
                self.stdout.write(f'Respaldo guardado en: {respaldo}')
            borrar_datos_negocio()
        elif Cliente.objects.exists() or Producto.objects.exists() or Venta.objects.exists():
            raise CommandError(
                'Ya hay datos del negocio. Usa --limpiar para empezar de cero '
                '(se hace un respaldo automático).'
            )

        if opciones['crear_usuarios']:
            self.crear_usuarios()

        # Usuario que queda como "quien hizo el reembolso" en los datos de ejemplo
        User = get_user_model()
        self.quien = (User.objects.filter(is_superuser=True).first()
                      or User.objects.filter(username='admin_demo').first()
                      or User.objects.first())

        with transaction.atomic():
            productos = self.crear_catalogo()
            clientes = self.crear_clientes()
            self.crear_pedidos(productos)
            ventas = self.crear_ventas(productos, clientes)
            self.crear_gastos()

        self.resumen()

    # ------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------
    def dia(self, dias_atras):
        return self.hoy - timedelta(days=dias_atras)

    def momento(self, dias_atras, hora=10):
        """Fecha y hora (con zona horaria) para campos auto_now_add."""
        return timezone.make_aware(datetime.combine(self.dia(dias_atras), time(hora, 30)))

    # ------------------------------------------------------------
    # 1. Catálogo
    # ------------------------------------------------------------
    def crear_catalogo(self):
        categorias = {n: Categoria.objects.create(nombre=n) for n in CATEGORIAS}

        for nombre, telefono, correo, direccion in PROVEEDORES:
            Proveedor.objects.create(nombre=nombre, telefono=telefono, correo=correo, direccion=direccion)

        # Los productos nacen como en la app: solo nombre y categoría
        # (precio 0 y stock 0). Los precios y el stock llegan con los pedidos.
        productos = {}
        for nombre, (cat, _compra, _venta) in PRODUCTOS.items():
            productos[nombre] = Producto.objects.create(
                nombre=nombre, categoria=categorias[cat],
                precio_compra=0, precio_venta=0, cantidad_disponible=0,
            )

        nombre, cat = PRODUCTO_SIN_PEDIDO
        productos[nombre] = Producto.objects.create(
            nombre=nombre, categoria=categorias[cat],
            precio_compra=0, precio_venta=0, cantidad_disponible=0,
        )
        return productos

    def crear_clientes(self):
        return [
            Cliente.objects.create(nombre=n, telefono=t, direccion=d)
            for n, t, d in CLIENTES
        ]

    # ------------------------------------------------------------
    # 2. Pedidos a proveedores
    # ------------------------------------------------------------
    def crear_pedidos(self, productos):
        proveedores = list(Proveedor.objects.order_by('id'))
        tiene_fecha_recepcion = 'fecha_recepcion' in [f.name for f in Pedido._meta.fields]

        for dias, idx_prov, estado, dias_recep, lineas in PEDIDOS:
            pedido = Pedido.objects.create(
                proveedor=proveedores[idx_prov], fecha=self.dia(dias),
                estado='Pendiente', costo_total=0,
            )

            costo_total = Decimal('0')
            for nombre, cantidad in lineas:
                _cat, compra, venta = PRODUCTOS[nombre]
                DetallePedido.objects.create(
                    pedido=pedido, producto=productos[nombre],
                    cantidad=cantidad, costo_unitario=compra,
                )
                costo_total += cantidad * compra

                # Igual que la app: al registrar el pedido se actualizan los precios
                productos[nombre].precio_compra = compra
                productos[nombre].precio_venta = venta
                productos[nombre].save(update_fields=['precio_compra', 'precio_venta'])

            pedido.costo_total = costo_total
            pedido.estado = estado

            if estado == 'Recibido':
                # Al recibir, entra el stock y el pedido empieza a contar como costo
                for nombre, cantidad in lineas:
                    productos[nombre].cantidad_disponible += cantidad
                    productos[nombre].save(update_fields=['cantidad_disponible'])
                if tiene_fecha_recepcion:
                    pedido.fecha_recepcion = self.dia(dias_recep)

            pedido.save()

    # ------------------------------------------------------------
    # 3. Ventas, pagos, abonos, deudas y reembolsos
    # ------------------------------------------------------------
    def crear_ventas(self, productos, clientes):
        for datos in VENTAS:
            cliente = clientes[datos['cliente']]
            pagado = Decimal(datos['pagado'])

            # Total con el precio actual de cada producto
            total = sum(
                (productos[n].precio_venta * c for n, c in datos['items']),
                Decimal('0'),
            )
            if pagado > total:
                raise CommandError(f'Datos de ejemplo mal armados: se pagó más del total ({cliente}).')

            venta = Venta.objects.create(
                cliente=cliente, valor_total=total, fecha=self.dia(datos['dias']),
                forma_pago=datos['forma'] if pagado > 0 else 'Efectivo',
            )

            # Productos vendidos y descuento de stock (igual que register_venta)
            for nombre, cantidad in datos['items']:
                producto = productos[nombre]
                if cantidad > producto.cantidad_disponible:
                    raise CommandError(f'Datos de ejemplo mal armados: sin stock de {nombre}.')

                DetalleVenta.objects.create(
                    venta=venta, producto=producto,
                    cantidad=cantidad, precio=producto.precio_venta,
                )
                producto.cantidad_disponible -= cantidad
                producto.save(update_fields=['cantidad_disponible'])

            # Pago inicial, deuda y primer abono
            saldo = total - pagado
            if pagado > 0:
                pago = Pago.objects.create(venta=venta, valor=pagado)
                Pago.objects.filter(pk=pago.pk).update(fecha=self.momento(datos['dias']))

            deuda = None
            if saldo > 0 or pagado > 0:
                deuda = Deuda.objects.create(
                    cliente=cliente, valor_total=total, saldo=saldo,
                    estado='Pagada' if saldo == 0 else 'Pendiente',
                )
                if pagado > 0:
                    abono = Abono.objects.create(deuda=deuda, valor=pagado, forma_pago=datos['forma'])
                    Abono.objects.filter(pk=abono.pk).update(fecha=self.momento(datos['dias']))

            # Pagos posteriores
            for dias_abono, valor, forma in datos.get('abonos', []):
                valor = Decimal(valor)
                abono = Abono.objects.create(deuda=deuda, valor=valor, forma_pago=forma)
                Abono.objects.filter(pk=abono.pk).update(fecha=self.momento(dias_abono, hora=16))
                deuda.saldo -= valor
                deuda.estado = 'Pagada' if deuda.saldo == 0 else 'Pendiente'
                deuda.save()

            # Cancelación y reembolso (por lo que el cliente ya había pagado)
            if datos.get('cancelada'):
                estado_reembolso, dias_devolucion = datos['cancelada']
                venta.estado = 'Cancelada'
                venta.save(update_fields=['estado'])

                metodo = datos['forma'] if datos['forma'] in ('Efectivo', 'Nequi', 'Daviplata', 'Transferencia') else 'Otro'
                reembolso = Reembolso.objects.create(
                    venta=venta, motivo='El cliente se arrepintió de la compra',
                    monto=pagado, metodo=metodo, estado='Devuelto',
                    fecha_devolucion=self.momento(dias_devolucion, hora=11),
                    observaciones='Reembolso realizado al cancelar la venta (dato de ejemplo).',
                    registrado_por=self.quien,
                )

    # ------------------------------------------------------------
    # 4. Gastos hormiga
    # ------------------------------------------------------------
    def crear_gastos(self):
        for dias, descripcion, valor in GASTOS_HORMIGA:
            Gasto.objects.create(
                descripcion=descripcion, valor=valor,
                fecha=self.dia(dias), tipo='Hormiga',
            )

    # ------------------------------------------------------------
    # 5. Usuarios de prueba (opcional)
    # ------------------------------------------------------------
    def crear_usuarios(self):
        from accounts.views import crear_roles_base

        crear_roles_base(forzar=True)
        User = get_user_model()

        for username, grupo in (('admin_demo', 'Administrador'), ('usuario_demo', 'Usuario')):
            usuario, creado = User.objects.get_or_create(
                username=username,
                defaults={'first_name': username.split('_')[0].title(), 'last_name': 'Demo',
                          'email': f'{username}@mismary.co'},
            )
            if creado:
                usuario.set_password('demo1234')
                usuario.save()
            usuario.groups.set([Group.objects.get(name=grupo)])

    # ------------------------------------------------------------
    def resumen(self):
        self.stdout.write(self.style.SUCCESS('Datos de ejemplo cargados:'))
        self.stdout.write(f'  Categorías: {Categoria.objects.count()}   Proveedores: {Proveedor.objects.count()}   '
                          f'Clientes: {Cliente.objects.count()}   Productos: {Producto.objects.count()}')
        self.stdout.write(f'  Pedidos: {Pedido.objects.count()} '
                          f'(recibidos {Pedido.objects.filter(estado="Recibido").count()}, '
                          f'pendientes {Pedido.objects.filter(estado="Pendiente").count()}, '
                          f'cancelados {Pedido.objects.filter(estado="Cancelado").count()})')
        self.stdout.write(f'  Ventas: {Venta.objects.count()}   Deudas pendientes: '
                          f'{Deuda.objects.filter(estado="Pendiente").count()}   '
                          f'Reembolsos: {Reembolso.objects.count()}   Gastos hormiga: {Gasto.objects.count()}')