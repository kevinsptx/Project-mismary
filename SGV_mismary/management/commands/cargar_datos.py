"""
Carga datos de EJEMPLO GRANDES con un flujo completo y coherente.

Genera, de forma automática (y repetible), unos ~4 meses de negocio:

  1. Categorías, proveedores, clientes y un catálogo de ~47 productos.
  2. Pedidos a proveedores: uno inicial por proveedor y reposiciones cuando
     el stock se agota (recibidos), más uno cancelado y uno pendiente.
  3. Cientos de ventas repartidas por días (más movimiento en fines de
     semana): pagadas, con abonos, con deuda, canceladas con reembolso y
     con reembolso parcial. Siempre hay ventas de hoy y de ayer.
  4. Gastos hormiga repartidos en todo el período.

El stock se simula día por día: nunca se vende algo que todavía no ha
llegado ni queda stock negativo.
Las fechas se calculan desde HOY, así los reportes siempre se ven vivos.

Uso:
    python manage.py cargar_datos
    python manage.py cargar_datos --limpiar            (borra antes lo del negocio)
    python manage.py cargar_datos --crear-usuarios     (crea admin_demo y usuario_demo)
    python manage.py cargar_datos --dias 180           (cuántos días de historial)
    python manage.py cargar_datos --semilla 7          (otro juego de datos distinto)
"""
import random
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from SGV_mismary.models import (
    Abono, Categoria, Cliente, DetallePedido, DetalleVenta, Deuda, Gasto,
    Pago, Pedido, Producto, Proveedor, Reembolso, Venta, DetalleReembolso,
)

from .limpiar_datos import borrar_datos_negocio, hacer_respaldo


# ------------------------------------------------------------------
# DATOS BASE
# ------------------------------------------------------------------

CATEGORIAS = [
    'Maquillaje', 'Cejas y Pestañas', 'Cuidado Facial', 'Cabello',
    'Uñas', 'Accesorios', 'Perfumería', 'Cuidado Corporal',
]

PROVEEDORES = [
    ('Distribuciones Aurora', '3112345678', 'ventas@aurora.co', 'Cra 3 # 12-40, Ibagué'),
    ('Beauty Import Colombia', '3159876543', 'pedidos@beautyimport.co', 'Calle 72 # 10-34, Bogotá'),
    ('Mayorista La Belleza', '3004561230', 'info@mayoristabelleza.co', 'Av. 30 de Agosto # 45-10, Pereira'),
    ('Fragancias del Valle', '3187654321', 'comercial@fragancias.co', 'Cra 100 # 5-20, Cali'),
    ('Importadora Glamour', '3203334455', 'ventas@glamour.co', 'Cra 43A # 1-50, Medellín'),
]

# Qué proveedores (por posición en la lista de arriba) surten cada categoría
PROV_POR_CATEGORIA = {
    'Maquillaje':        [0, 4],
    'Cejas y Pestañas':  [0, 1],
    'Cuidado Facial':    [1],
    'Cabello':           [2],
    'Uñas':              [0, 4],
    'Accesorios':        [2, 4],
    'Perfumería':        [3],
    'Cuidado Corporal':  [1, 3],
}

# nombre: (categoría, precio de compra, precio de venta)
PRODUCTOS = {
    # Maquillaje
    'Labial Líquido Coral':        ('Maquillaje', 7000, 15000),
    'Labial Mate Vino':            ('Maquillaje', 7000, 15000),
    'Rubor en Polvo Rosa':         ('Maquillaje', 8000, 17000),
    'Polvo Compacto Natural':      ('Maquillaje', 9000, 19000),
    'Base Líquida Tono Medio':     ('Maquillaje', 14000, 29000),
    'Corrector Cobertura Alta':    ('Maquillaje', 8000, 17000),
    'Iluminador Dorado':           ('Maquillaje', 9000, 20000),
    'Paleta de Sombras Nude':      ('Maquillaje', 16000, 34000),
    'Delineador Líquido Negro':    ('Maquillaje', 5000, 11000),
    'Spray Fijador de Maquillaje': ('Maquillaje', 11000, 24000),
    # Cejas y Pestañas
    'Pestañina Waterproof':        ('Cejas y Pestañas', 8500, 18000),
    'Gel Fijador de Cejas':        ('Cejas y Pestañas', 5000, 11000),
    'Lápiz de Cejas Castaño':      ('Cejas y Pestañas', 4000, 9000),
    'Pestañas Postizas Naturales': ('Cejas y Pestañas', 6000, 13000),
    # Cuidado Facial
    'Limpiador Facial Espuma':     ('Cuidado Facial', 11000, 23000),
    'Sérum Vitamina C':            ('Cuidado Facial', 18000, 38000),
    'Mascarilla de Arcilla':       ('Cuidado Facial', 6000, 13000),
    'Crema Hidratante Día':        ('Cuidado Facial', 15000, 32000),
    'Protector Solar FPS 50':      ('Cuidado Facial', 17000, 36000),
    'Agua Micelar':                ('Cuidado Facial', 12000, 25000),
    'Contorno de Ojos':            ('Cuidado Facial', 13000, 28000),
    # Cabello
    'Shampoo de Keratina':         ('Cabello', 13000, 26000),
    'Mascarilla Capilar':          ('Cabello', 12000, 25000),
    'Aceite de Argán':             ('Cabello', 15000, 32000),
    'Acondicionador Sin Sal':      ('Cabello', 11000, 23000),
    'Crema para Peinar':           ('Cabello', 9000, 19000),
    'Tratamiento Anticaída':       ('Cabello', 19000, 40000),
    # Uñas
    'Esmalte Gel Rojo':            ('Uñas', 4000, 9000),
    'Esmalte Gel Nude':            ('Uñas', 4000, 9000),
    'Set de Limas':                ('Uñas', 3000, 7000),
    'Removedor de Esmalte':        ('Uñas', 3000, 7000),
    'Kit de Manicure':             ('Uñas', 10000, 22000),
    # Accesorios
    'Espejo de Mano':              ('Accesorios', 6000, 14000),
    'Neceser Floral':              ('Accesorios', 10000, 22000),
    'Set de Brochas x8':           ('Accesorios', 18000, 39000),
    'Esponja Beauty Blender':      ('Accesorios', 5000, 12000),
    'Cintillo para Maquillarse':   ('Accesorios', 3000, 8000),
    'Organizador de Maquillaje':   ('Accesorios', 15000, 33000),
    # Perfumería
    'Splash Corporal Vainilla':    ('Perfumería', 12000, 26000),
    'Perfume Floral 50 ml':        ('Perfumería', 28000, 59000),
    'Perfume Cítrico 50 ml':       ('Perfumería', 27000, 57000),
    'Colonia Infantil':            ('Perfumería', 10000, 22000),
    # Cuidado Corporal
    'Crema Corporal de Karité':    ('Cuidado Corporal', 10000, 21000),
    'Exfoliante de Café':          ('Cuidado Corporal', 9000, 19000),
    'Aceite Corporal de Almendras': ('Cuidado Corporal', 13000, 28000),
    'Desodorante en Crema':        ('Cuidado Corporal', 7000, 15000),
}

# Producto registrado pero SIN pedido todavía (sin precio ni stock):
# así se ve cómo queda un producto recién creado.
PRODUCTO_SIN_PEDIDO = ('Kit de Pinceles Mini', 'Accesorios')

NOMBRES = [
    'Paula Andrea', 'Esteban', 'Natalia', 'Felipe', 'Luisa Fernanda', 'Santiago',
    'Karen', 'Julián', 'Valentina', 'Camilo', 'Daniela', 'Andrés', 'Mariana',
    'Sebastián', 'Laura', 'Juan Pablo', 'Carolina', 'Mateo', 'Juliana', 'David',
    'Sofía', 'Nicolás', 'Alejandra', 'Brayan', 'Ximena', 'Cristian', 'Tatiana',
    'Oscar', 'Manuela', 'Diego',
]

APELLIDOS = [
    'Vargas', 'Molina', 'Cárdenas', 'Giraldo', 'Mejía', 'Rincón', 'Beltrán',
    'Arias', 'Ramírez', 'Gómez', 'Torres', 'Ospina', 'Castaño', 'Herrera',
    'Rojas', 'Quintero', 'Salazar', 'Morales', 'Duque', 'Parra', 'Londoño',
    'Mora', 'Cruz', 'Prieto',
]

BARRIOS = [
    'Barrio La Pola', 'Jordán', 'Cádiz', 'El Salado', 'Picaleña', 'Ambalá',
    'Mirolindo', 'El Vergel', 'Interlaken', 'Piedra Pintada', 'Belén',
    'Santa Ana', 'Gaitán', 'La Francia', 'Calambeo',
]

CANTIDAD_CLIENTES = 32

# (descripción, valor mínimo, valor máximo)
TIPOS_GASTO_HORMIGA = [
    ('Bolsas de papel kraft', 6000, 12000),
    ('Pasaje para recoger mercancía', 4000, 9000),
    ('Etiquetas y stickers para empaques', 8000, 14000),
    ('Impulso de publicaciones en Instagram', 15000, 35000),
    ('Domicilio a clientes', 8000, 18000),
    ('Tijeras y cinta de embalaje', 5000, 10000),
    ('Papel de seda para regalos', 4000, 9000),
    ('Tarjetas de agradecimiento', 7000, 13000),
    ('Recarga de datos del celular', 10000, 20000),
    ('Fotocopias del catálogo', 3000, 8000),
    ('Cajas de cartón para envíos', 9000, 16000),
    ('Almuerzo en día de entregas', 8000, 15000),
]

FORMAS_PAGO = ['Efectivo', 'Nequi', 'Daviplata', 'Transferencia']
PESOS_FORMA = [35, 32, 12, 21]


# ------------------------------------------------------------------
# GENERADOR DE DATOS (todo sale de una semilla: siempre igual)
# ------------------------------------------------------------------

def redondear_mil(valor):
    return int(round(valor / 1000.0)) * 1000


def generar_clientes(semilla):
    rng = random.Random(semilla + 1)
    clientes, usados, telefonos = [], set(), set()

    while len(clientes) < CANTIDAD_CLIENTES:
        nombre = f'{rng.choice(NOMBRES)} {rng.choice(APELLIDOS)}'
        telefono = '3' + ''.join(str(rng.randint(0, 9)) for _ in range(9))

        if nombre in usados or telefono in telefonos:
            continue
        usados.add(nombre)
        telefonos.add(telefono)

        if rng.random() < 0.5:
            direccion = f'{rng.choice(BARRIOS)}, Ibagué'
        else:
            direccion = f'Cra {rng.randint(1, 15)} # {rng.randint(1, 60)}-{rng.randint(1, 50)}, Ibagué'

        clientes.append((nombre, telefono, direccion))

    return clientes


def generar_plan(hoy, dias_total, semilla):
    """
    Simula el negocio día por día y devuelve todo lo que hay que cargar:
    clientes, pedidos, ventas y gastos. El stock se controla en memoria
    para que los datos nunca queden incoherentes.
    """
    rng = random.Random(semilla)
    clientes = generar_clientes(semilla)

    nombres = list(PRODUCTOS)
    precio_venta = {n: PRODUCTOS[n][2] for n in nombres}
    popularidad = {n: rng.uniform(0.3, 3.0) for n in nombres}

    # Cada producto lo surte siempre el mismo proveedor
    proveedor_de = {n: rng.choice(PROV_POR_CATEGORIA[PRODUCTOS[n][0]]) for n in nombres}

    stock = {n: 0 for n in nombres}
    entrante = {n: 0 for n in nombres}          # pedido en camino
    recepciones = defaultdict(list)             # día -> [(producto, cantidad)]
    pedidos, ventas = [], []

    def cantidad_inicial(n):
        # Lo caro se compra en menos cantidad
        return rng.randint(8, 14) if precio_venta[n] >= 35000 else rng.randint(14, 26)

    def colocar_pedido(dias, idx_prov, lineas, estado, demora=3):
        dias_recep = None

        if estado == 'Recibido':
            dias_recep = dias - demora
            if dias_recep < 0:               # todavía no llega
                estado, dias_recep = 'Pendiente', None
            else:
                recepciones[dias_recep].extend(lineas)
                for n, c in lineas:
                    entrante[n] += c

        pedidos.append((dias, idx_prov, estado, dias_recep, lineas))

    # --- Pedidos iniciales: un pedido por proveedor con todo su catálogo ---
    for idx_prov in range(len(PROVEEDORES)):
        lineas = [(n, cantidad_inicial(n)) for n in nombres if proveedor_de[n] == idx_prov]
        if lineas:
            colocar_pedido(dias_total, idx_prov, lineas, 'Recibido', rng.randint(2, 4))

    dia_cancelado_1 = int(dias_total * 0.62)
    dia_cancelado_2 = int(dias_total * 0.25)

    # --- Simulación día por día, desde el más antiguo hasta hoy ---
    for d in range(dias_total, -1, -1):

        # 1. Llegan los pedidos que estaban en camino
        for n, c in recepciones.pop(d, []):
            stock[n] += c
            entrante[n] -= c

        # 2. Reposición: cada 9 días se pide lo que se está agotando
        if 6 <= d <= dias_total - 10 and d % 9 == 0:
            for idx_prov in range(len(PROVEEDORES)):
                bajos = [n for n in nombres
                         if proveedor_de[n] == idx_prov and stock[n] + entrante[n] < 6]
                if bajos:
                    rng.shuffle(bajos)
                    lineas = [(n, rng.randint(10, 20) if precio_venta[n] < 35000 else rng.randint(6, 10))
                              for n in bajos[:8]]
                    colocar_pedido(d, idx_prov, lineas, 'Recibido', rng.randint(2, 4))

        # 3. Un par de pedidos cancelados y uno pendiente reciente
        if d in (dia_cancelado_1, dia_cancelado_2):
            idx_prov = rng.randrange(len(PROVEEDORES))
            candidatos = [n for n in nombres if proveedor_de[n] == idx_prov] or nombres
            lineas = [(n, rng.randint(4, 8)) for n in rng.sample(candidatos, min(2, len(candidatos)))]
            pedidos.append((d, idx_prov, 'Cancelado', None, lineas))

        if d == 3:
            idx_prov = 1
            candidatos = [n for n in nombres if proveedor_de[n] == idx_prov]
            lineas = [(n, rng.randint(8, 14)) for n in rng.sample(candidatos, min(3, len(candidatos)))]
            colocar_pedido(d, idx_prov, lineas, 'Pendiente', 0)

        # 4. Ventas del día (más en viernes y sábado)
        dia_semana = (hoy - timedelta(days=d)).weekday()
        cuantas = rng.choices([0, 1, 2, 3, 4], [8, 25, 32, 25, 10])[0]
        if dia_semana in (4, 5) and rng.random() < 0.5:
            cuantas += 1
        if d <= 1:
            cuantas = max(cuantas, 2)        # siempre hay ventas de hoy y de ayer

        for _ in range(cuantas):
            disponibles = [n for n in nombres if stock[n] > 0]
            if not disponibles:
                break

            # Qué se vende
            n_lineas = min(len(disponibles), rng.choices([1, 2, 3, 4], [35, 40, 20, 5])[0])
            pool = disponibles[:]
            items = []
            for _l in range(n_lineas):
                n = rng.choices(pool, [popularidad[x] for x in pool])[0]
                pool.remove(n)
                cant = min(stock[n], rng.choices([1, 2, 3], [65, 25, 10])[0])
                stock[n] -= cant
                items.append((n, cant))

            total = sum(precio_venta[n] * c for n, c in items)

            # Los primeros 8 clientes compran más seguido
            cliente = rng.choices(range(len(clientes)),
                                  [4 if i < 8 else 1 for i in range(len(clientes))])[0]
            forma = rng.choices(FORMAS_PAGO, PESOS_FORMA)[0]

            venta = dict(dias=d, cliente=cliente, items=items, forma=forma)
            suerte = rng.random()

            if suerte < 0.62:
                # Pagada completa
                venta['pagado'] = total

            elif suerte < 0.80:
                # Pagó una parte; puede ir abonando
                pagado = redondear_mil(total * rng.uniform(0.3, 0.7))
                venta['pagado'] = max(1000, min(pagado, total - 1000))
                venta['abonos'] = generar_abonos(rng, d, total - venta['pagado'], 0.6)

            elif suerte < 0.90:
                # No pagó nada todavía
                venta['pagado'] = 0
                venta['abonos'] = generar_abonos(rng, d, total, 0.5)

            elif suerte < 0.95 and d >= 2:
                # Venta cancelada con reembolso de lo que había pagado
                if rng.random() < 0.7:
                    venta['pagado'] = total
                else:
                    venta['pagado'] = max(1000, min(redondear_mil(total * 0.5), total - 1000))
                venta['cancelada'] = ('Devuelto', max(0, d - rng.randint(1, 2)))

            elif suerte >= 0.95 and d >= 2 and (len(items) > 1 or items[0][1] > 1):
                # Reembolso parcial: se devuelve 1 unidad de un producto
                venta['pagado'] = total
                producto_dev = rng.choice(items)[0]
                venta['parcial'] = (max(0, d - rng.randint(1, 2)), [(producto_dev, 1)])

            else:
                venta['pagado'] = total

            ventas.append(venta)

    # --- Gastos hormiga repartidos en todo el período ---
    gastos = []
    for _ in range(max(8, dias_total // 4)):
        descripcion, minimo, maximo = rng.choice(TIPOS_GASTO_HORMIGA)
        valor = int(round(rng.randint(minimo, maximo) / 500.0)) * 500
        gastos.append((rng.randint(0, dias_total), descripcion, valor))

    pedidos.sort(key=lambda p: -p[0])
    ventas.sort(key=lambda v: -v['dias'])
    gastos.sort(key=lambda g: -g[0])

    return dict(clientes=clientes, pedidos=pedidos, ventas=ventas, gastos=gastos)


def generar_abonos(rng, dias_venta, saldo, probabilidad):
    """Pagos posteriores a la venta: nunca superan lo que se debe."""
    if dias_venta < 3 or saldo <= 0 or rng.random() > probabilidad:
        return []

    posibles = list(range(max(0, dias_venta - 35), dias_venta))   # días posteriores a la venta
    cantidad = min(len(posibles), rng.choice([1, 1, 2]))
    dias_abonos = sorted(rng.sample(posibles, cantidad), reverse=True)

    abonos, restante = [], saldo

    for i, dia in enumerate(dias_abonos):
        if restante <= 0:
            break

        es_ultimo = i == len(dias_abonos) - 1
        if es_ultimo and rng.random() < 0.65:
            valor = restante                                      # termina de pagar
        else:
            valor = max(1000, redondear_mil(restante * rng.uniform(0.3, 0.6)))

        valor = min(valor, restante)
        abonos.append((dia, valor, rng.choices(FORMAS_PAGO, PESOS_FORMA)[0]))
        restante -= valor

    return abonos


# ------------------------------------------------------------------
# COMANDO
# ------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Carga datos de ejemplo grandes con un flujo completo y coherente.'

    def add_arguments(self, parser):
        parser.add_argument('--limpiar', action='store_true',
                            help='Borra antes los datos del negocio (hace respaldo).')
        parser.add_argument('--crear-usuarios', action='store_true',
                            help='Crea admin_demo y usuario_demo (clave: demo1234).')
        parser.add_argument('--dias', type=int, default=120,
                            help='Cuántos días de historial generar (por defecto 120).')
        parser.add_argument('--semilla', type=int, default=2026,
                            help='Cambia este número para obtener otro juego de datos.')

    # ------------------------------------------------------------
    def handle(self, *args, **opciones):
        self.hoy = timezone.localdate()

        if opciones['dias'] < 30:
            raise CommandError('Usa al menos --dias 30 para que los datos tengan sentido.')

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

        plan = generar_plan(self.hoy, opciones['dias'], opciones['semilla'])

        with transaction.atomic():
            productos = self.crear_catalogo()
            clientes = self.crear_clientes(plan['clientes'])
            self.crear_pedidos(productos, plan['pedidos'])
            self.crear_ventas(productos, clientes, plan['ventas'])
            self.crear_gastos(plan['gastos'])

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

    def crear_clientes(self, datos_clientes):
        return [
            Cliente.objects.create(nombre=n, telefono=t, direccion=d)
            for n, t, d in datos_clientes
        ]

    # ------------------------------------------------------------
    # 2. Pedidos a proveedores
    # ------------------------------------------------------------
    def crear_pedidos(self, productos, plan_pedidos):
        proveedores = list(Proveedor.objects.order_by('id'))
        tiene_fecha_recepcion = 'fecha_recepcion' in [f.name for f in Pedido._meta.fields]

        for dias, idx_prov, estado, dias_recep, lineas in plan_pedidos:
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
    def crear_ventas(self, productos, clientes, plan_ventas):
        for datos in plan_ventas:
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
                    cliente=cliente, venta=venta, valor_total=total, saldo=saldo,
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
                Deuda.objects.filter(venta=venta).update(estado='Cancelada', saldo=0)
                venta.save(update_fields=['estado'])

                metodo = datos['forma'] if datos['forma'] in ('Efectivo', 'Nequi', 'Daviplata', 'Transferencia') else 'Otro'
                reembolso = Reembolso.objects.create(
                    venta=venta, motivo='El cliente se arrepintió de la compra',
                    monto=pagado, metodo=metodo, estado='Devuelto',
                    fecha_devolucion=self.momento(dias_devolucion, hora=11),
                    observaciones='Reembolso realizado al cancelar la venta (dato de ejemplo).',
                    registrado_por=self.quien,
                )
                for linea in venta.detalles.all():
                    DetalleReembolso.objects.create(
                        reembolso=reembolso, producto=linea.producto,
                        cantidad=linea.cantidad, precio=linea.precio,
                    )
                    linea.cantidad_reembolsada = linea.cantidad
                    linea.save(update_fields=['cantidad_reembolsada'])
                Reembolso.objects.filter(pk=reembolso.pk).update(
                    fecha_solicitud=reembolso.fecha_devolucion
                )

            # Reembolso PARCIAL: solo algunos productos; la venta sigue activa
            if datos.get('parcial'):
                dias_dev, productos_dev = datos['parcial']
                recibido = pagado + sum(a[1] for a in datos.get('abonos', []))
                valor_dev = Decimal('0')
                lineas = []
                for nombre, cant in productos_dev:
                    linea = venta.detalles.get(producto=productos[nombre])
                    lineas.append((linea, cant))
                    valor_dev += linea.precio * cant

                monto = max(Decimal('0'), Decimal(recibido) - (venta.valor_total - valor_dev))
                metodo = datos['forma'] if datos['forma'] in ('Efectivo', 'Nequi', 'Daviplata', 'Transferencia') else 'Otro'
                reembolso = Reembolso.objects.create(
                    venta=venta, motivo='Reembolso de productos de la venta',
                    monto=monto, metodo=metodo,
                    estado='Devuelto' if monto > 0 else 'No aplica',
                    fecha_devolucion=self.momento(dias_dev, hora=11) if monto > 0 else None,
                    observaciones='Reembolso parcial (dato de ejemplo).',
                    registrado_por=self.quien,
                )
                Reembolso.objects.filter(pk=reembolso.pk).update(
                    fecha_solicitud=self.momento(dias_dev, hora=11)
                )
                for linea, cant in lineas:
                    DetalleReembolso.objects.create(
                        reembolso=reembolso, producto=linea.producto,
                        cantidad=cant, precio=linea.precio,
                    )
                    linea.cantidad_reembolsada = cant
                    linea.save(update_fields=['cantidad_reembolsada'])

                # la deuda de la venta queda con el nuevo valor
                nuevo_valor = venta.valor_total - valor_dev
                saldo = max(Decimal('0'), nuevo_valor - (Decimal(recibido) - monto))
                Deuda.objects.filter(venta=venta).update(
                    valor_total=nuevo_valor, saldo=saldo,
                    estado='Pagada' if saldo == 0 else 'Pendiente',
                )

    # ------------------------------------------------------------
    # 4. Gastos hormiga
    # ------------------------------------------------------------
    def crear_gastos(self, plan_gastos):
        for dias, descripcion, valor in plan_gastos:
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
                          f'Clientes: {Cliente.objects.count()}   Productos: {Producto.objects.count()} '
                          f'(sin stock: {Producto.objects.filter(cantidad_disponible=0).count()})')
        self.stdout.write(f'  Pedidos: {Pedido.objects.count()} '
                          f'(recibidos {Pedido.objects.filter(estado="Recibido").count()}, '
                          f'pendientes {Pedido.objects.filter(estado="Pendiente").count()}, '
                          f'cancelados {Pedido.objects.filter(estado="Cancelado").count()})')
        self.stdout.write(f'  Ventas: {Venta.objects.count()}   Deudas pendientes: '
                          f'{Deuda.objects.filter(estado="Pendiente").count()}   '
                          f'Abonos: {Abono.objects.count()}   '
                          f'Reembolsos: {Reembolso.objects.count()}   Gastos hormiga: {Gasto.objects.count()}')