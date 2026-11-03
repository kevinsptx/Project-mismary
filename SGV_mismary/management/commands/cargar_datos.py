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
    python manage.py cargar_datos_demo
    python manage.py cargar_datos_demo --limpiar          (borra antes lo del negocio)
    python manage.py cargar_datos_demo --crear-usuarios   (crea admin_demo y usuario_demo)
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
    'Labiales', 'Bases y Correctores', 'Ojos', 'Cuidado de la Piel', 'Accesorios',
]

PROVEEDORES = [
    ('Distribuidora Belleza Total', '3101234567', 'ventas@bellezatotal.co', 'Cra 5 # 10-20, Ibagué'),
    ('Cosméticos del Valle', '3207654321', 'pedidos@cosmeticosvalle.co', 'Calle 15 # 8-45, Cali'),
]

# nombre: (categoría, precio de compra, precio de venta)
PRODUCTOS = {
    'Labial Mate Rojo':          ('Labiales', 6000, 12000),
    'Labial Mate Nude':          ('Labiales', 6000, 12000),
    'Brillo Labial Transparente': ('Labiales', 4000, 8500),
    'Base Líquida Tono Claro':   ('Bases y Correctores', 14000, 28000),
    'Corrector Cremoso':         ('Bases y Correctores', 9000, 18000),
    'Delineador Líquido Negro':  ('Ojos', 5000, 11000),
    'Máscara de Pestañas':       ('Ojos', 8000, 17000),
    'Paleta de Sombras':         ('Ojos', 18000, 35000),
    'Crema Hidratante Facial':   ('Cuidado de la Piel', 12000, 24000),
    'Protector Solar Facial':    ('Cuidado de la Piel', 15000, 30000),
    'Set de Brochas':            ('Accesorios', 20000, 40000),
    'Esponja de Maquillaje':     ('Accesorios', 3000, 7000),
}

# Producto registrado pero SIN pedido todavía (sin precio ni stock):
# así se ve cómo queda un producto recién creado.
PRODUCTO_SIN_PEDIDO = ('Rubor en Crema', 'Bases y Correctores')

CLIENTES = [
    ('Ana María Gómez',     '3001112233', 'Barrio La Pola, Ibagué'),
    ('Carlos Pérez',        '3012223344', 'Cra 4 # 15-30, Ibagué'),
    ('Laura Rodríguez',     '3023334455', 'Barrio Jordán, Ibagué'),
    ('Sofía Martínez',      '3034445566', 'Cádiz, Ibagué'),
    ('Juan David Torres',   '3045556677', 'El Salado, Ibagué'),
    ('Valentina Ríos',      '3056667788', 'Picaleña, Ibagué'),
    ('Camila Herrera',      '3067778899', 'Ambalá, Ibagué'),
    ('Andrés Castaño',      '3078889900', 'Calle 60 # 5-12, Ibagué'),
    ('Daniela Ospina',      '3089990011', 'Barrio Interlaken, Ibagué'),
    ('Mariana López',       '3090001122', 'Cra 3 # 22-40, Ibagué'),
]

# (días atrás del pedido, índice proveedor, estado, días atrás de recepción, líneas)
PEDIDOS = [
    (56, 0, 'Recibido', 53, [('Labial Mate Rojo', 8), ('Labial Mate Nude', 9),
                             ('Brillo Labial Transparente', 8), ('Delineador Líquido Negro', 6),
                             ('Máscara de Pestañas', 6)]),
    (36, 1, 'Recibido', 33, [('Base Líquida Tono Claro', 5), ('Corrector Cremoso', 3),
                             ('Crema Hidratante Facial', 5), ('Protector Solar Facial', 5)]),
    (22, 0, 'Cancelado', None, [('Set de Brochas', 4)]),
    (14, 0, 'Recibido', 10, [('Paleta de Sombras', 3), ('Set de Brochas', 2),
                             ('Esponja de Maquillaje', 8), ('Labial Mate Rojo', 4)]),
    (4,  1, 'Pendiente', None, [('Protector Solar Facial', 6), ('Base Líquida Tono Claro', 4)]),
]

# Cada venta:
#   dias:   días atrás de la venta
#   cliente: índice en CLIENTES
#   items:  [(producto, cantidad)]
#   pagado: lo que pagó al momento de la venta
#   forma:  forma de pago del pago inicial
#   abonos: [(días atrás, valor, forma)]  pagos posteriores
#   cancelada: None | ('Devuelto', días atrás de la devolución) | ('Solicitado', None)
VENTAS = [
    dict(dias=50, cliente=0, items=[('Labial Mate Rojo', 2), ('Brillo Labial Transparente', 1)], pagado=32500, forma='Efectivo'),
    dict(dias=48, cliente=1, items=[('Labial Mate Nude', 1), ('Delineador Líquido Negro', 1)], pagado=10000, forma='Nequi',
         abonos=[(40, 8000, 'Nequi'), (30, 5000, 'Efectivo')]),
    dict(dias=45, cliente=2, items=[('Máscara de Pestañas', 2), ('Labial Mate Rojo', 1)], pagado=46000, forma='Transferencia'),
    dict(dias=41, cliente=3, items=[('Labial Mate Nude', 2)], pagado=0, forma='Efectivo',
         abonos=[(20, 10000, 'Efectivo')]),
    dict(dias=38, cliente=4, items=[('Delineador Líquido Negro', 2), ('Brillo Labial Transparente', 2)], pagado=20000, forma='Daviplata',
         abonos=[(15, 9000, 'Daviplata')]),
    dict(dias=32, cliente=5, items=[('Base Líquida Tono Claro', 1), ('Corrector Cremoso', 1)], pagado=46000, forma='Nequi'),
    dict(dias=28, cliente=0, items=[('Crema Hidratante Facial', 1), ('Protector Solar Facial', 1)], pagado=30000, forma='Efectivo',
         abonos=[(12, 24000, 'Nequi')]),
    dict(dias=25, cliente=6, items=[('Labial Mate Rojo', 3), ('Labial Mate Nude', 2)], pagado=60000, forma='Efectivo',
         cancelada=('Devuelto', 23)),
    dict(dias=20, cliente=7, items=[('Base Líquida Tono Claro', 2), ('Máscara de Pestañas', 1)], pagado=40000, forma='Transferencia',
         abonos=[(8, 15000, 'Efectivo')]),
    dict(dias=16, cliente=8, items=[('Crema Hidratante Facial', 2)], pagado=48000, forma='Nequi'),
    dict(dias=13, cliente=9, items=[('Protector Solar Facial', 2), ('Corrector Cremoso', 1)], pagado=0, forma='Efectivo'),
    dict(dias=9,  cliente=1, items=[('Paleta de Sombras', 1), ('Esponja de Maquillaje', 2)], pagado=49000, forma='Efectivo'),
    dict(dias=7,  cliente=2, items=[('Set de Brochas', 1), ('Labial Mate Rojo', 2)], pagado=30000, forma='Nequi'),
    dict(dias=5,  cliente=3, items=[('Esponja de Maquillaje', 3), ('Brillo Labial Transparente', 2)], pagado=38000, forma='Efectivo',
         cancelada=('Solicitado', None)),
    dict(dias=3,  cliente=5, items=[('Paleta de Sombras', 2), ('Delineador Líquido Negro', 1)], pagado=81000, forma='Transferencia'),
    dict(dias=1,  cliente=4, items=[('Labial Mate Rojo', 2), ('Labial Mate Nude', 2), ('Brillo Labial Transparente', 1)], pagado=56500, forma='Efectivo'),
    dict(dias=0,  cliente=0, items=[('Máscara de Pestañas', 1)], pagado=17000, forma='Nequi'),
    dict(dias=31, cliente=8, items=[('Base Líquida Tono Claro', 1)], pagado=28000, forma='Nequi'),
    dict(dias=18, cliente=6, items=[('Crema Hidratante Facial', 1), ('Corrector Cremoso', 1)], pagado=42000, forma='Efectivo'),
    dict(dias=11, cliente=7, items=[('Protector Solar Facial', 1), ('Labial Mate Nude', 1)], pagado=42000, forma='Transferencia'),
    dict(dias=6,  cliente=9, items=[('Máscara de Pestañas', 1), ('Delineador Líquido Negro', 1)], pagado=28000, forma='Daviplata'),
]

# (días atrás, descripción, valor)
GASTOS_HORMIGA = [
    (50, 'Bolsas y papel de regalo', 8500),
    (44, 'Transporte para recoger pedido', 12000),
    (30, 'Cinta y etiquetas para empaques', 6000),
    (21, 'Publicidad en redes sociales', 30000),
    (11, 'Domicilios a clientes', 15000),
    (2,  'Papelería y marcadores', 9500),
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

        with transaction.atomic():
            productos = self.crear_catalogo()
            clientes = self.crear_clientes()
            self.crear_pedidos(productos)
            ventas = self.crear_ventas(productos, clientes)
            self.crear_gastos()

        if opciones['crear_usuarios']:
            self.crear_usuarios()

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

                reembolso = Reembolso.objects.create(
                    venta=venta, motivo='El cliente se arrepintió de la compra',
                    monto=pagado, metodo='Efectivo', estado='Solicitado',
                    observaciones='Dato de ejemplo.',
                )
                if estado_reembolso == 'Devuelto':
                    reembolso.estado = 'Devuelto'
                    reembolso.fecha_devolucion = self.momento(dias_devolucion, hora=11)
                    reembolso.save()

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