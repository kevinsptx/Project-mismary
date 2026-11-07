import csv
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.db import transaction
from django.db.models import ProtectedError
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.urls import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ProductoForm, ProductoRegistroForm, AbonoForm, ClienteForm, GastoForm, ProveedorForm
from .models import Cliente, Venta, Abono, Deuda, Categoria,Producto, DetalleVenta, Gasto, Pago,DetallePedido, Pedido, Proveedor, Reembolso

METODOS_VALIDOS = ['Efectivo', 'Nequi', 'Daviplata', 'Transferencia', 'Otro']
ESTADOS_PEDIDO = ['Pendiente', 'Recibido', 'Cancelado']


def requiere_permisos(*permisos):
    def decorador(vista):
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            if request.user.is_superuser:
                return vista(request, *args, **kwargs)
            app_label = Cliente._meta.app_label
            permisos_completos = [f"{app_label}.{permiso}" for permiso in permisos]
            if not request.user.has_perms(permisos_completos):
                raise PermissionDenied
            return vista(request, *args, **kwargs)
        return envoltura
    return decorador


def permiso_pedido(vista):
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied
        if not request.user.is_superuser:
            app_label = Pedido._meta.app_label
            permiso = 'change_pedido' if request.method == 'POST' else 'view_pedido'
            if not request.user.has_perm(f'{app_label}.{permiso}'):
                raise PermissionDenied
        return vista(request, *args, **kwargs)
    return envoltura


def int_cop(valor):
    if valor is None:
        return "$ 0"
    return f"$ {int(round(float(valor))):,}"


def limpiar_numero(texto):
    return texto.replace('.', '').replace(',', '').strip()


def filtrar_por_fecha(consulta, fecha_inicio, fecha_fin):

    if fecha_inicio:
        consulta = consulta.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        consulta = consulta.filter(fecha__lte=fecha_fin)

    return consulta


# ============================================================
# 3. INICIO
# ============================================================

@login_required
def home(request):
    """Dashboard: cada tarjeta muestra un dato real (solo si el usuario tiene permiso)."""
    hoy = timezone.localdate()
    inicio_mes = hoy.replace(day=1)
    u = request.user
    stats = {}

    if u.has_perm('SGV_mismary.view_venta'):
        v = (Venta.objects.exclude(estado='Cancelada')
             .filter(fecha=hoy)
             .aggregate(n=Count('id'), t=Sum('valor_total')))
        stats['ventas_hoy'] = v['n']
        stats['ventas_hoy_total'] = v['t'] or 0

    if u.has_perm('SGV_mismary.view_pedido'):
        stats['pedidos_pendientes'] = Pedido.objects.filter(estado='Pendiente').count()

    if u.has_perm('SGV_mismary.view_cliente'):
        stats['clientes'] = Cliente.objects.count()

    if u.has_perm('SGV_mismary.view_producto'):
        stats['productos'] = Producto.objects.count()
        stats['sin_stock'] = Producto.objects.filter(cantidad_disponible=0).count()

    if u.has_perm('SGV_mismary.view_reembolso'):
        stats['reembolsos_mes'] = Reembolso.objects.filter(
            fecha_solicitud__date__gte=inicio_mes
        ).count()

    if u.has_perm('SGV_mismary.view_proveedor'):
        stats['proveedores'] = Proveedor.objects.count()

    if u.has_perm('SGV_mismary.view_deuda'):
        stats['por_cobrar'] = datos_clientes_deuda()['total_saldo']

    if u.has_perm('SGV_mismary.view_gasto'):
        stats['gastos_mes'] = (Gasto.objects.filter(fecha__gte=inicio_mes, fecha__lte=hoy)
                               .aggregate(t=Sum('valor'))['t'] or 0)

    return render(request, 'home.html', {'stats': stats})


# ============================================================
# 4. CLIENTES
# ============================================================

@login_required
@requiere_permisos('add_cliente')
def registrar_cliente(request):

    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('list_cliente')
    else:
        form = ClienteForm()

    return render(request, 'registrar_cliente.html', {'form': form})


@login_required
@requiere_permisos('add_cliente')
def register_cliente(request):

    if request.method == 'POST':
        Cliente.objects.create(
            nombre=request.POST['nombre'],
            telefono=request.POST['telefono'],
            direccion=request.POST['direccion']
        )
        return redirect('list_cliente')

    return render(request, 'register_cliente.html')


@login_required
@requiere_permisos('view_cliente')
def list_cliente(request):
    buscar = request.GET.get('buscar')

    if buscar:
        clientes = Cliente.objects.filter(
            Q(nombre__icontains=buscar) | Q(telefono__icontains=buscar)
        )
    else:
        clientes = Cliente.objects.all()

    return render(request, 'list_cliente.html', {
        'clientes': clientes,
        'buscar': buscar
    })


@login_required
@requiere_permisos('view_cliente')
def cliente_details(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    tiene_deuda = Deuda.objects.filter(cliente=cliente, estado='Pendiente', saldo__gt=0).exists()

    return render(request, 'cliente_details.html', {
        'cliente': cliente,
        'tiene_deuda': tiene_deuda
    })


@login_required
@requiere_permisos('change_cliente')
def cliente_update(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if request.method == 'POST':
        cliente.nombre = request.POST['nombre']
        cliente.telefono = request.POST['telefono']
        cliente.direccion = request.POST['direccion']
        cliente.save()
        return redirect('list_cliente')

    return render(request, 'cliente_update.html', {'cliente': cliente})


@login_required
@require_POST
@requiere_permisos('delete_cliente')
def cliente_delete(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if cliente.ventas.exists():
        messages.error(
            request,
            f'No se puede eliminar a {cliente.nombre} porque tiene ventas registradas. '
            'Elimina primero las ventas asociadas si corresponde.'
        )
        return redirect('list_cliente')

    if cliente.deudas.filter(estado='Pendiente', saldo__gt=0).exists():
        messages.error(
            request,
            f'No se puede eliminar a {cliente.nombre} porque tiene una deuda pendiente.'
        )
        return redirect('list_cliente')

    if cliente.deudas.exists():
        messages.error(
            request,
            f'No se puede eliminar a {cliente.nombre} porque tiene registros de deudas y abonos.'
        )
        return redirect('list_cliente')

    cliente.delete()
    messages.success(request, f'El cliente {cliente.nombre} fue eliminado correctamente.')
    return redirect('list_cliente')


@login_required
@requiere_permisos('view_cliente', 'view_venta', 'view_abono', 'view_deuda')
def cliente_historial(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    ventas = Venta.objects.filter(cliente=cliente).order_by('-fecha')
    abonos = Abono.objects.filter(deuda__cliente=cliente).order_by('-fecha')

    saldo_pendiente = Deuda.objects.filter(
        cliente=cliente,
        estado='Pendiente'
    ).aggregate(total=Sum('saldo'))['total'] or 0

    ver = request.GET.get('ver', 'ventas')
    if ver not in ('ventas', 'abonos'):
        ver = 'ventas'

    return render(request, 'cliente_historial.html', {
        'ver': ver,
        'cliente': cliente,
        'ventas': ventas,
        'abonos': abonos,
        'saldo_pendiente': saldo_pendiente
    })


# ============================================================
# 5. PRODUCTOS
# ============================================================

@login_required
@requiere_permisos('add_producto', 'view_categoria')
def register_producto(request):

    if request.method == 'POST':
        form = ProductoRegistroForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Producto registrado. Agrega su precio y stock al registrar un pedido.'
            )
            return redirect('list_producto')
    else:
        form = ProductoRegistroForm()

    return render(request, 'register_producto.html', {'form': form})


@login_required
@requiere_permisos('view_producto', 'view_categoria')
def list_producto(request):

    buscar = request.GET.get('buscar')
    categoria_id = request.GET.get('categoria')

    categorias = Categoria.objects.all()
    productos = Producto.objects.all()

    if buscar:
        productos = productos.filter(nombre__icontains=buscar)

    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    return render(request, 'list_producto.html', {
        'productos': productos,
        'buscar': buscar,
        'categorias': categorias,
        'categoria_id': categoria_id
    })


@login_required
@requiere_permisos('change_producto')
def producto_update(request, id):

    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        datos = request.POST.copy()


        precio = datos.get('precio_venta', '').strip()
        datos['precio_venta'] = precio.replace('.', '')

        form = ProductoForm(datos, instance=producto)

        if form.is_valid():
            form.save()
            messages.success(request, 'Producto actualizado correctamente.')
            return redirect('list_producto')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'producto_update.html', {
        'form': form,
        'producto': producto
    })


@login_required
@requiere_permisos('delete_producto')
def producto_delete(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        nombre_producto = producto.nombre

        # Con ventas o pedidos registrados NO se borra: se perdería el historial.
        if DetalleVenta.objects.filter(producto=producto).exists():
            messages.error(
                request,
                f'No se puede eliminar "{nombre_producto}" porque ya tiene ventas '
                f'registradas. Si ya no lo vendes, déjalo en stock 0.'
            )
            return redirect('list_producto')

        try:
            producto.delete()
        except ProtectedError:
            messages.error(
                request,
                f'No se puede eliminar "{nombre_producto}" porque ya está en pedidos a proveedores.'
            )
            return redirect('list_producto')

        messages.success(request, f'El producto "{nombre_producto}" fue eliminado correctamente.')
        return redirect('list_producto')

    return render(request, 'producto_delete.html', {'producto': producto})


@login_required
@requiere_permisos('view_detalleventa')
def productos_mas_vendidos(request):

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    productos_vendidos = DetalleVenta.objects.exclude(venta__estado='Cancelada')


    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        messages.error(
            request,
            'La fecha inicial no puede ser posterior a la fecha final.'
        )
        productos_vendidos = DetalleVenta.objects.none()
    else:
        if fecha_inicio:
            productos_vendidos = productos_vendidos.filter(venta__fecha__gte=fecha_inicio)

        if fecha_fin:
            productos_vendidos = productos_vendidos.filter(venta__fecha__lte=fecha_fin)


        productos_vendidos = (
            productos_vendidos.values('producto__nombre')
            .annotate(total_vendido=Sum('cantidad'))
            .order_by('-total_vendido')
        )

    return render(request, 'productos_mas_vendidos.html', {
        'productos_vendidos': productos_vendidos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })


# ============================================================
# 6. VENTAS
# ============================================================

class ErrorEnVenta(Exception):
    """Error propio: lo usamos para cancelar la venta y mostrar un mensaje."""
    pass


@login_required
@requiere_permisos('add_venta', 'add_detalleventa', 'add_pago', 'add_deuda', 'add_abono', 'view_cliente', 'view_producto')
def register_venta(request):
    """Registra una venta: descuenta stock, guarda pago y crea la deuda si hace falta."""
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        fecha = request.POST.get('fecha')
        producto_ids = request.POST.getlist('producto_id')
        cantidades = request.POST.getlist('cantidad')

        # --- Paso 1: validar lo que pagó el cliente ---
        try:
            valor_pagado = Decimal(request.POST.get('valor_pagado') or '0')
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'El valor pagado no es válido.')
            return redirect('register_venta')

        if not valor_pagado.is_finite() or valor_pagado < 0:
            messages.error(request, 'El valor pagado no puede ser negativo.')
            return redirect('register_venta')

        cliente = get_object_or_404(Cliente, id=cliente_id)

        # --- Paso 2: armar el pedido {id_producto: cantidad} ---
        # Si el mismo producto viene repetido, se suman las cantidades.
        pedidos = {}

        for pid, cant in zip(producto_ids, cantidades):
            if not pid:
                continue

            try:
                cantidad = int(cant)
                pid = int(pid)
            except (TypeError, ValueError):
                messages.error(request, 'Hay un producto o cantidad no válidos.')
                return redirect('register_venta')

            if cantidad <= 0:
                messages.error(request, 'La cantidad debe ser mayor que cero.')
                return redirect('register_venta')

            pedidos[pid] = pedidos.get(pid, 0) + cantidad

        if not pedidos:
            messages.error(request, 'Debes agregar al menos un producto a la venta.')
            return redirect('register_venta')

        # --- Paso 3: guardar todo (si algo falla, no se guarda nada) ---
        try:
            with transaction.atomic():
                # select_for_update bloquea los productos mientras vendemos
                productos = {
                    p.id: p
                    for p in Producto.objects.select_for_update().filter(
                        id__in=pedidos.keys()
                    )
                }

                if len(productos) != len(pedidos):
                    raise ErrorEnVenta('Uno de los productos ya no existe.')

                # Calcular el total y revisar que haya stock
                valor_total = Decimal('0')

                for pid, cantidad in pedidos.items():
                    producto = productos[pid]

                    if cantidad > producto.cantidad_disponible:
                        raise ErrorEnVenta(
                            f'No hay suficiente stock de "{producto.nombre}". '
                            f'Disponible: {producto.cantidad_disponible}.'
                        )

                    valor_total += producto.precio_venta * cantidad

                if valor_pagado > valor_total:
                    raise ErrorEnVenta('Lo pagado no puede ser mayor que el valor total.')

                # Crear la venta
                venta = Venta.objects.create(
                    cliente=cliente,
                    valor_total=valor_total,
                    fecha=fecha
                )

                # Guardar el pago inicial (si pagó algo)
                if valor_pagado > 0:
                    Pago.objects.create(venta=venta, valor=valor_pagado)

                # Guardar cada producto vendido y descontar el stock
                for pid, cantidad in pedidos.items():
                    producto = productos[pid]

                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto,
                        cantidad=cantidad,
                        precio=producto.precio_venta
                    )

                    producto.cantidad_disponible -= cantidad
                    producto.save(update_fields=['cantidad_disponible'])

                # Crear la deuda (lo que falta por pagar)
                saldo = valor_total - valor_pagado

                if saldo > 0 or valor_pagado > 0:
                    estado = 'Pagada' if saldo == 0 else 'Pendiente'

                    deuda = Deuda.objects.create(
                        cliente=cliente,
                        venta=venta,
                        valor_total=valor_total,
                        saldo=saldo,
                        estado=estado
                    )

                    if valor_pagado > 0:
                        Abono.objects.create(
                            deuda=deuda,
                            valor=valor_pagado,
                            fecha=fecha
                        )

        except ErrorEnVenta as e:
            messages.error(request, str(e))
            return redirect('register_venta')

        messages.success(request, 'Venta registrada correctamente.')
        return redirect('list_venta')

    # Si entra por GET: mostramos el formulario con clientes y productos con stock
    clientes = Cliente.objects.all()
    productos = Producto.objects.filter(cantidad_disponible__gt=0).order_by('nombre')

    return render(request, 'register_venta.html', {
        'clientes': clientes,
        'productos': productos,
    })


@login_required
@requiere_permisos('view_venta')
def list_venta(request):

    buscar = request.GET.get('buscar')

    if buscar:
        ventas = Venta.objects.filter(cliente__nombre__icontains=buscar)
    else:
        ventas = Venta.objects.all()

    ventas = ventas.select_related('cliente', 'reembolso').order_by('-fecha')

    return render(request, 'list_ventas.html', {
        'ventas': ventas,
        'buscar': buscar
    })


@login_required
@requiere_permisos('view_venta', 'view_detalleventa')
def venta_details(request, id):
    """Muestra el detalle de una venta (productos vendidos)."""
    venta = get_object_or_404(Venta, id=id)
    detalles = venta.detalles.select_related('producto').all()

    return render(request, 'venta_details.html', {
        'venta': venta,
        'detalles': detalles,
        'deuda': None,
    })


@login_required
@require_POST
@requiere_permisos('delete_venta')
def venta_delete(request, id):
    """Elimina una venta con todo lo suyo: pagos, deuda, abonos y reembolso."""
    venta = get_object_or_404(Venta, id=id)

    with transaction.atomic():
        # 1. Devolver los productos al stock (solo si la venta seguía activa;
        #    si estaba reembolsada, el stock ya se manejó al reembolsar)
        if venta.estado == 'Activa':
            for detalle in venta.detalles.select_related('producto'):
                producto = detalle.producto

                if producto:
                    producto.cantidad_disponible += detalle.cantidad
                    producto.save(update_fields=['cantidad_disponible'])

        # 2. Borrar lo que depende de la venta
        Reembolso.objects.filter(venta=venta).delete()
        venta.pagos.all().delete()
        venta.deudas.all().delete()          # sus abonos se borran con ella

        # 3. Borrar la venta
        venta.delete()

    messages.success(request, 'La venta y sus deudas/abonos asociados fueron eliminados.')
    return redirect('list_venta')


@login_required
@requiere_permisos('view_deuda')
def ventas_pendientes(request):
    """Lista las deudas que todavía están pendientes."""
    deudas = Deuda.objects.filter(estado='Pendiente').select_related('cliente')

    return render(request, 'ventas_pendientes.html', {'deudas': deudas})


# ============================================================
# 7. ABONOS Y DEUDAS
# ============================================================

@login_required
@requiere_permisos('view_abono')
def lista_abonos(request):
    """Lista los abonos de las deudas que aún tienen saldo."""
    abonos = Abono.objects.filter(
        deuda__saldo__gt=0
    ).select_related('deuda__cliente').order_by('-fecha')

    return render(request, 'abonos.html', {'abonos': abonos})


@login_required
@requiere_permisos('add_abono', 'view_deuda')
def registrar_abono(request, deuda_id):
    """Registra un abono a una deuda y le resta el valor al saldo."""
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == 'POST':
        form = AbonoForm(request.POST)

        if form.is_valid():
            valor_abono = form.cleaned_data['valor']

            if valor_abono <= 0:
                form.add_error('valor', 'El valor del abono debe ser mayor que cero.')
            elif valor_abono > deuda.saldo:
                form.add_error('valor', 'El abono no puede ser mayor que el saldo pendiente.')
            else:
                with transaction.atomic():
                    abono = form.save(commit=False)
                    abono.deuda = deuda
                    abono.save()

                    deuda.saldo -= valor_abono
                    deuda.estado = 'Pagada' if deuda.saldo == 0 else 'Pendiente'
                    deuda.save()

                messages.success(request, 'Abono registrado correctamente.')
                return redirect('ventas_pendientes')
    else:
        form = AbonoForm()

    return render(request, 'registrar_abono.html', {
        'form': form,
        'deuda': deuda
    })


@login_required
@requiere_permisos('change_abono')
def editar_abono(request, abono_id):
    """Cambia el valor de un abono y ajusta el saldo de la deuda."""
    abono = get_object_or_404(Abono, id=abono_id)
    deuda = abono.deuda

    if request.method == 'POST':
        form = AbonoForm(request.POST)

        if form.is_valid():
            nuevo_valor = form.cleaned_data['valor']

            if nuevo_valor <= 0:
                form.add_error('valor', 'El valor del abono debe ser mayor que cero.')
            else:
                # Saldo que habría si este abono no existiera
                saldo_sin_este_abono = deuda.saldo + abono.valor

                if nuevo_valor > saldo_sin_este_abono:
                    form.add_error(
                        'valor',
                        'El nuevo valor no puede ser mayor que la deuda pendiente.'
                    )
                else:
                    with transaction.atomic():
                        diferencia = nuevo_valor - abono.valor

                        abono.valor = nuevo_valor
                        abono.save()

                        deuda.saldo -= diferencia
                        deuda.estado = 'Pagada' if deuda.saldo == 0 else 'Pendiente'
                        deuda.save()

                    messages.success(request, 'Abono actualizado correctamente.')
                    return redirect('lista_abonos')
    else:
        form = AbonoForm(instance=abono)

    return render(request, 'editar_abono.html', {
        'form': form,
        'abono': abono
    })


@login_required
@require_POST
@requiere_permisos('delete_abono')
def eliminar_abono(request, abono_id):
    """Elimina un abono y le devuelve ese valor al saldo de la deuda."""
    abono = get_object_or_404(Abono, id=abono_id)
    deuda = abono.deuda

    if request.method == 'POST':
        with transaction.atomic():
            deuda.saldo += abono.valor
            deuda.estado = 'Pagada' if deuda.saldo == 0 else 'Pendiente'
            deuda.save()
            abono.delete()

        messages.success(request, 'Abono eliminado correctamente.')
        return redirect('lista_abonos')

    return render(request, 'eliminar_abono.html', {'abono': abono})


@login_required
@requiere_permisos('view_deuda', 'view_abono')
def detalle_deuda(request, deuda_id):
    """Muestra una deuda con todos sus abonos."""
    deuda = get_object_or_404(Deuda, id=deuda_id)
    abonos = deuda.abonos.all().order_by('-fecha')

    return render(request, 'detalle_deuda.html', {
        'deuda': deuda,
        'abonos': abonos
    })


@login_required
@requiere_permisos('view_deuda', 'view_abono')
def detalle_pendiente(request, deuda_id):
    """Muestra una deuda pendiente con sus abonos (incluye datos del cliente)."""
    deuda = get_object_or_404(
        Deuda.objects.select_related('cliente'),
        id=deuda_id
    )
    abonos = deuda.abonos.all().order_by('-fecha')

    return render(request, 'detalle_pendiente.html', {
        'deuda': deuda,
        'abonos': abonos
    })


@login_required
@requiere_permisos('add_abono')
def marcar_pagada(request, deuda_id):
    """Marca una deuda como pagada (saldo en 0)."""
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == 'POST':
        with transaction.atomic():
            # Lo que faltaba por pagar entra como un abono, para que
            # el reporte de ingresos cuente esa plata.
            if deuda.saldo > 0:
                Abono.objects.create(deuda=deuda, valor=deuda.saldo)

            deuda.saldo = 0
            deuda.estado = 'Pagada'
            deuda.save()

        messages.success(request, 'La venta fue marcada como pagada.')
        return redirect('ventas_pendientes')

    return redirect('detalle_pendiente', deuda_id=deuda.id)


@login_required
@require_POST
@requiere_permisos('delete_deuda')
def eliminar_pendiente(request, deuda_id):
    """Elimina una deuda, su venta, sus abonos y devuelve el stock."""
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == 'POST':
        with transaction.atomic():
            ventas = Venta.objects.filter(
                cliente=deuda.cliente,
                valor_total=deuda.valor_total
            )

            for venta in ventas:
                # Devolver los productos al stock
                for detalle in venta.detalles.select_related('producto'):
                    if detalle.producto:
                        detalle.producto.cantidad_disponible += detalle.cantidad
                        detalle.producto.save(update_fields=['cantidad_disponible'])

                venta.delete()

            deuda.abonos.all().delete()
            deuda.delete()

        messages.success(request, 'La deuda y sus registros asociados fueron eliminados.')
        return redirect('ventas_pendientes')

    return redirect('detalle_pendiente', deuda_id=deuda.id)


# ============================================================
# 8. GASTOS
# ============================================================

@login_required
@requiere_permisos('add_gasto')
def registrar_gasto(request):
    """Registra un gasto hormiga."""
    if request.method == 'POST':
        form = GastoForm(request.POST)

        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.tipo = 'Hormiga'
            gasto.save()
            messages.success(request, 'Gasto registrado correctamente.')
            return redirect('reporte_gastos_hormiga')
    else:
        form = GastoForm(initial={'fecha': timezone.localdate()})

    return render(request, 'registrar_gasto.html', {'form': form})


@login_required
@requiere_permisos('change_gasto')
def editar_gasto(request, gasto_id):
    """Edita un gasto hormiga."""
    gasto = get_object_or_404(Gasto.objects.exclude(tipo='Pedido'), pk=gasto_id)

    if request.method == 'POST':
        form = GastoForm(request.POST, instance=gasto)

        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto actualizado correctamente.')
            return redirect('reporte_gastos_hormiga')
    else:
        form = GastoForm(instance=gasto)

    return render(request, 'registrar_gasto.html', {
        'form': form,
        'titulo': 'Editar gasto',
        'subtitulo': 'Corrige los datos del gasto',
        'boton': 'Guardar cambios',
    })


@login_required
@requiere_permisos('delete_gasto')
def eliminar_gasto(request, gasto_id):
    """Elimina un gasto hormiga (pide confirmación una vez)."""
    gasto = get_object_or_404(Gasto.objects.exclude(tipo='Pedido'), pk=gasto_id)

    if request.method == 'POST':
        gasto.delete()
        messages.success(request, 'Gasto eliminado correctamente.')
        return redirect('reporte_gastos_hormiga')

    return render(request, 'eliminar_gasto.html', {'gasto': gasto})


# ============================================================
# 9. REPORTES
# ============================================================
#
# REGLAS (todo se cuenta cuando el dinero REALMENTE se mueve):
#
#  - INGRESOS: solo cuenta la plata que ya entró (abonos y pagos de los
#    clientes). Si una venta es de $3.000 y el cliente solo pagó $1.000,
#    el ingreso es $1.000 y los otros $2.000 quedan en "Por cobrar".
#    Las devoluciones ya hechas (reembolsos "Devuelto") se restan.
#
#  - COSTOS: solo cuentan los pedidos ya RECIBIDOS (desde el día en que
#    llegaron) más los gastos hormiga. Un pedido pendiente o cancelado
#    todavía no es un costo; se muestra aparte como "Por recibir".
#
#  - BALANCE: ingresos netos recibidos - costos.

def parsear_fecha(texto):
    """Convierte 'AAAA-MM-DD' en fecha. Si viene vacío o mal escrito, None."""
    if not texto:
        return None

    try:
        return date.fromisoformat(texto)
    except ValueError:
        return None


def rango_fechas(request):
    """Lee Desde/Hasta del filtro. Si vienen al revés, las intercambia."""
    inicio = parsear_fecha(request.GET.get('fecha_inicio'))
    fin = parsear_fecha(request.GET.get('fecha_fin'))

    if inicio and fin and inicio > fin:
        messages.warning(
            request,
            'La fecha inicial era posterior a la final, así que las intercambiamos.'
        )
        inicio, fin = fin, inicio

    return inicio, fin


def contexto_filtro(inicio, fin):
    """Datos comunes del filtro de fechas y de los atajos (hoy, mes...)."""
    hoy = timezone.localdate()
    primero_este_mes = hoy.replace(day=1)
    ultimo_mes_pasado = primero_este_mes - timedelta(days=1)
    primero_mes_pasado = ultimo_mes_pasado.replace(day=1)

    return {
        'fecha_inicio': inicio.isoformat() if inicio else '',
        'fecha_fin': fin.isoformat() if fin else '',
        'atajos': [
            ('Hoy', hoy.isoformat(), hoy.isoformat()),
            ('Este mes', primero_este_mes.isoformat(), hoy.isoformat()),
            ('Mes pasado', primero_mes_pasado.isoformat(), ultimo_mes_pasado.isoformat()),
        ],
    }


def datos_ingresos(inicio, fin):
    """Dinero recibido (abonos) menos devoluciones, por día."""

    # --- Dinero que entró: cada abono (el pago inicial también es un abono) ---
    abonos = Abono.objects.all()

    if inicio:
        abonos = abonos.filter(fecha__date__gte=inicio)
    if fin:
        abonos = abonos.filter(fecha__date__lte=fin)

    recibido_por_dia = {
        fila['dia']: fila['total']
        for fila in abonos.annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(total=Sum('valor'))
    }

    por_forma_pago = list(
        abonos.values('forma_pago')
        .annotate(total=Sum('valor'), cantidad=Count('id'))
        .order_by('-total')
    )

    # --- Dinero que salió: reembolsos ya devueltos ---
    devoluciones = (
        Reembolso.objects.filter(estado='Devuelto')
        .annotate(momento=Coalesce('fecha_devolucion', 'fecha_solicitud'))
        .annotate(dia=TruncDate('momento'))
    )

    if inicio:
        devoluciones = devoluciones.filter(dia__gte=inicio)
    if fin:
        devoluciones = devoluciones.filter(dia__lte=fin)

    devuelto_por_dia = {
        fila['dia']: fila['total']
        for fila in devoluciones.values('dia').annotate(total=Sum('monto'))
    }

    # --- Una fila por día ---
    filas = []

    for dia in sorted(set(recibido_por_dia) | set(devuelto_por_dia)):
        recibido = recibido_por_dia.get(dia, Decimal('0'))
        devuelto = devuelto_por_dia.get(dia, Decimal('0'))

        filas.append({
            'fecha': dia,
            'recibido': recibido,
            'devuelto': devuelto,
            'neto': recibido - devuelto,
        })

    total_recibido = sum(recibido_por_dia.values(), Decimal('0'))
    total_devuelto = sum(devuelto_por_dia.values(), Decimal('0'))

    # --- Lo vendido en el período (para comparar con lo recibido) ---
    ventas = Venta.objects.exclude(estado='Cancelada')
    ventas = filtrar_por_fecha(ventas, inicio, fin)
    # Ingreso neto: lo que se ganó con cada producto vendido
    # = (precio de venta - precio de compra) x cantidad, sumado.
    detalles = DetalleVenta.objects.exclude(venta__estado='Cancelada')
    if inicio:
        detalles = detalles.filter(venta__fecha__gte=inicio)
    if fin:
        detalles = detalles.filter(venta__fecha__lte=fin)

    ganancia_productos = detalles.aggregate(
        total=Sum(
            (F('precio') - F('producto__precio_compra')) * F('cantidad'),
            output_field=DecimalField(max_digits=14, decimal_places=2)
        )
    )['total'] or Decimal('0')

    resumen_ventas = ventas.aggregate(total=Sum('valor_total'), cantidad=Count('id'))
    total_vendido = resumen_ventas['total'] or Decimal('0')

    return {
        'filas': filas,
        'por_forma_pago': por_forma_pago,
        'total_recibido': total_recibido,
        'total_devuelto': total_devuelto,
        'total_neto': total_recibido - total_devuelto,
        'total_vendido': total_vendido,
        'ganancia_productos': ganancia_productos,
        'cantidad_ventas': resumen_ventas['cantidad'],
    }


def datos_gastos(inicio, fin):
    """Costos: pedidos RECIBIDOS + gastos hormiga. Los pendientes van aparte."""

    # --- Pedidos que ya llegaron (cuentan desde el día de recepción) ---
    recibidos = (
        Pedido.objects.filter(estado='Recibido')
        .select_related('proveedor')
        .annotate(fecha_costo=Coalesce('fecha_recepcion', 'fecha'))
    )

    if inicio:
        recibidos = recibidos.filter(fecha_costo__gte=inicio)
    if fin:
        recibidos = recibidos.filter(fecha_costo__lte=fin)

    movimientos = []

    for pedido in recibidos:
        proveedor = pedido.proveedor.nombre if pedido.proveedor else (pedido.proveedor_texto or 'Sin proveedor')

        movimientos.append({
            'fecha': pedido.fecha_costo,
            'concepto': f'Pedido #{pedido.id} · {proveedor}',
            'tipo': 'Pedido',
            'valor': pedido.costo_total,
            'pedido_id': pedido.id,
        })

    total_pedidos = sum((m['valor'] for m in movimientos), Decimal('0'))

    # --- Gastos hormiga (los gastos viejos "Pedido" se ignoran: ahora se
    #     calculan desde los pedidos recibidos, para no contarlos dos veces) ---
    hormiga = filtrar_por_fecha(Gasto.objects.exclude(tipo='Pedido'), inicio, fin)

    for gasto in hormiga:
        movimientos.append({
            'fecha': gasto.fecha,
            'concepto': gasto.descripcion,
            'tipo': 'Hormiga',
            'valor': gasto.valor,
            'pedido_id': None,
        })

    total_hormiga = sum(
        (m['valor'] for m in movimientos if m['tipo'] == 'Hormiga'),
        Decimal('0')
    )

    movimientos.sort(key=lambda m: (m['fecha'], m['concepto']))

    # --- Pedidos que todavía no llegan (NO se cuentan como costo) ---
    pendientes = list(
        Pedido.objects.filter(estado='Pendiente')
        .select_related('proveedor')
        .order_by('fecha', 'id')
    )

    total_pendientes = sum((p.costo_total for p in pendientes), Decimal('0'))

    return {
        'movimientos': movimientos,
        'total_pedidos': total_pedidos,
        'total_hormiga': total_hormiga,
        'total': total_pedidos + total_hormiga,
        'pendientes': pendientes,
        'total_pendientes': total_pendientes,
    }


def datos_clientes_deuda():
    """Lo que los clientes todavía NO han pagado (por cobrar)."""
    deudas = Deuda.objects.filter(
        estado='Pendiente',
        saldo__gt=0
    ).select_related('cliente')

    # Si una venta se canceló, su deuda ya no se cobra.
    # (La deuda y la venta se relacionan por cliente + valor total.)
    canceladas = set(
        Venta.objects.filter(estado='Cancelada')
        .values_list('cliente_id', 'valor_total')
    )
    activas = set(
        Venta.objects.exclude(estado='Cancelada')
        .values_list('cliente_id', 'valor_total')
    )

    por_cliente = {}

    for deuda in deudas:
        clave = (deuda.cliente_id, deuda.valor_total)

        if clave in canceladas and clave not in activas:
            continue

        fila = por_cliente.setdefault(deuda.cliente_id, {
            'cliente': deuda.cliente,
            'deudas': 0,
            'total': Decimal('0'),
            'abonado': Decimal('0'),
            'saldo': Decimal('0'),
        })

        fila['deudas'] += 1
        fila['total'] += deuda.valor_total
        fila['abonado'] += deuda.valor_total - deuda.saldo
        fila['saldo'] += deuda.saldo

    filas = sorted(por_cliente.values(), key=lambda f: f['saldo'], reverse=True)

    return {
        'filas': filas,
        'total_saldo': sum((f['saldo'] for f in filas), Decimal('0')),
        'total_abonado': sum((f['abonado'] for f in filas), Decimal('0')),
        'total_ventas': sum((f['total'] for f in filas), Decimal('0')),
    }


# ---------- Pestañas: cada una es una página aparte ----------

PESTANAS_REPORTE = {
    'ingresos': [
        ('Resumen', 'reporte_ingresos', 'resumen'),
        ('Por día', 'reporte_ingresos_dias', 'dias'),
        ('Por forma de pago', 'reporte_ingresos_pagos', 'pagos'),
    ],
    'costos': [
        ('Resumen', 'reporte_gastos', 'resumen'),
        ('Detalle', 'reporte_gastos_detalle', 'detalle'),
        ('Gastos hormiga', 'reporte_gastos_hormiga', 'hormiga'),
        ('Por recibir', 'reporte_gastos_pendientes', 'pendientes'),
    ],
}


def contexto_pestanas(request, grupo, activa):
    """Pestañas del reporte; conservan las fechas del filtro al cambiar de página."""
    consulta = request.GET.urlencode()
    pestanas = []

    for etiqueta, nombre, clave in PESTANAS_REPORTE[grupo]:
        url = reverse(nombre)
        if consulta:
            url += '?' + consulta
        pestanas.append((etiqueta, url, clave))

    return {'pestanas': pestanas, 'pestana_activa': activa}


# ---------- Pantallas de reportes ----------

@login_required
@requiere_permisos('view_pago', 'view_gasto', 'view_deuda')
def reportes(request):
    """Menú principal de reportes."""
    return render(request, 'reportes.html')


def _reporte_ingresos(request, plantilla, activa):
    inicio, fin = rango_fechas(request)

    contexto = {'ingresos': datos_ingresos(inicio, fin)}
    contexto.update(contexto_filtro(inicio, fin))
    contexto.update(contexto_pestanas(request, 'ingresos', activa))

    return render(request, plantilla, contexto)


@login_required
@requiere_permisos('view_pago', 'view_abono')
def reporte_ingresos(request):
    """Ingresos: resumen del dinero que ya entró."""
    return _reporte_ingresos(request, 'reporte_ingresos.html', 'resumen')


@login_required
@requiere_permisos('view_pago', 'view_abono')
def reporte_ingresos_dias(request):
    """Ingresos día por día."""
    return _reporte_ingresos(request, 'reporte_ingreso_dia.html', 'dias')


@login_required
@requiere_permisos('view_pago', 'view_abono')
def reporte_ingresos_pagos(request):
    """Ingresos por forma de pago."""
    return _reporte_ingresos(request, 'reporte_ingreso_pagos.html', 'pagos')


def _reporte_gastos(request, plantilla, activa):
    inicio, fin = rango_fechas(request)

    contexto = {
        'gastos': datos_gastos(inicio, fin),
        'por_cobrar': datos_clientes_deuda()['total_saldo'],
    }
    contexto.update(contexto_filtro(inicio, fin))
    contexto.update(contexto_pestanas(request, 'costos', activa))

    return render(request, plantilla, contexto)


@login_required
@requiere_permisos('view_gasto')
def reporte_gastos(request):
    """Costos: resumen."""
    return _reporte_gastos(request, 'reporte_gastos.html', 'resumen')


@login_required
@requiere_permisos('view_gasto')
def reporte_gastos_detalle(request):
    """Costos: cada movimiento del período."""
    return _reporte_gastos(request, 'reporte_gatos_detalle.html', 'detalle')


@login_required
@requiere_permisos('view_gasto')
def reporte_gastos_pendientes(request):
    """Pedidos que todavía no llegan."""
    return _reporte_gastos(request, 'reporte_gatos_pendientes.html', 'pendientes')


@login_required
@requiere_permisos('view_gasto')
def reporte_gastos_hormiga(request):
    """Gastos hormiga: lista para editar o eliminar."""
    inicio, fin = rango_fechas(request)

    gastos = filtrar_por_fecha(
        Gasto.objects.exclude(tipo='Pedido').order_by('-fecha', '-id'),
        inicio, fin
    )
    total = gastos.aggregate(t=Sum('valor'))['t'] or Decimal('0')

    contexto = {'gastos': gastos, 'total': total}
    contexto.update(contexto_filtro(inicio, fin))
    contexto.update(contexto_pestanas(request, 'costos', 'hormiga'))

    return render(request, 'reporte_gato_hormiga.html', contexto)


@login_required
@requiere_permisos('view_cliente', 'view_deuda')
def reporte_clientes_deuda(request):
    """Clientes que todavía deben dinero."""
    return render(request, 'reporte_clientes_deuda.html', {
        'deudas': datos_clientes_deuda()
    })


@login_required
@requiere_permisos('view_pago', 'view_abono', 'view_gasto')
def reporte_balance(request):
    """Balance = ingresos netos recibidos - costos."""
    inicio, fin = rango_fechas(request)

    ingresos = datos_ingresos(inicio, fin)
    gastos = datos_gastos(inicio, fin)

    contexto = {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': ingresos['total_neto'] - gastos['total'],
    }
    contexto.update(contexto_filtro(inicio, fin))

    return render(request, 'reporte_balance.html', contexto)


@login_required
@requiere_permisos('view_venta', 'view_abono')
def consultar_por_fecha(request):
    """Muestra las ventas y abonos entre dos fechas."""
    fecha_inicio = parsear_fecha(request.GET.get('fecha_inicio'))
    fecha_fin = parsear_fecha(request.GET.get('fecha_fin'))

    ventas = None
    abonos = None

    if fecha_inicio and fecha_fin:
        ventas = Venta.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('cliente')

        abonos = Abono.objects.filter(
            fecha__date__gte=fecha_inicio,
            fecha__date__lte=fecha_fin
        ).select_related('deuda__cliente')

    return render(request, 'consultar_por_fecha.html', {
        'fecha_inicio': request.GET.get('fecha_inicio'),
        'fecha_fin': request.GET.get('fecha_fin'),
        'ventas': ventas,
        'abonos': abonos,
    })


@login_required
@requiere_permisos('view_pago', 'view_abono', 'view_gasto', 'view_cliente', 'view_deuda')
def descargar_reporte(request):
    """Descarga un reporte en formato CSV (se abre en Excel)."""
    tipo = request.GET.get('tipo')

    # Sin tipo: mostramos la pantalla para elegir
    if not tipo:
        return render(request, 'descargar_reporte.html')

    if tipo not in ['ingresos', 'gastos', 'clientes_deuda', 'balance']:
        messages.error(request, 'Selecciona un tipo de reporte válido.')
        return redirect('descargar_reporte')

    inicio, fin = rango_fechas(request)

    # Preparamos el archivo CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo}.csv"'
    response.write('\ufeff')  # Para que Excel lea bien las tildes

    writer = csv.writer(response)

    if tipo == 'ingresos':
        datos = datos_ingresos(inicio, fin)

        writer.writerow(['Fecha', 'Recibido', 'Devoluciones', 'Ingreso neto'])
        for fila in datos['filas']:
            writer.writerow([
                fila['fecha'],
                int_cop(fila['recibido']),
                int_cop(fila['devuelto']),
                int_cop(fila['neto']),
            ])
        writer.writerow([
            'TOTAL',
            int_cop(datos['total_recibido']),
            int_cop(datos['total_devuelto']),
            int_cop(datos['total_neto']),
        ])

    elif tipo == 'gastos':
        datos = datos_gastos(inicio, fin)

        writer.writerow(['Fecha', 'Tipo', 'Concepto', 'Valor'])
        for mov in datos['movimientos']:
            writer.writerow([
                mov['fecha'], mov['tipo'], mov['concepto'], int_cop(mov['valor'])
            ])
        writer.writerow(['', '', 'Pedidos recibidos', int_cop(datos['total_pedidos'])])
        writer.writerow(['', '', 'Gastos hormiga', int_cop(datos['total_hormiga'])])
        writer.writerow(['', '', 'TOTAL COSTOS', int_cop(datos['total'])])

    elif tipo == 'clientes_deuda':
        datos = datos_clientes_deuda()

        writer.writerow(['Cliente', 'Total de ventas', 'Abonado', 'Saldo pendiente'])
        for fila in datos['filas']:
            writer.writerow([
                fila['cliente'].nombre,
                int_cop(fila['total']),
                int_cop(fila['abonado']),
                int_cop(fila['saldo']),
            ])
        writer.writerow([
            'TOTAL',
            int_cop(datos['total_ventas']),
            int_cop(datos['total_abonado']),
            int_cop(datos['total_saldo']),
        ])

    elif tipo == 'balance':
        ingresos = datos_ingresos(inicio, fin)
        gastos = datos_gastos(inicio, fin)

        writer.writerow(['Concepto', 'Valor'])
        writer.writerow(['Dinero recibido', int_cop(ingresos['total_recibido'])])
        writer.writerow(['Devoluciones', int_cop(ingresos['total_devuelto'])])
        writer.writerow(['Ingresos netos', int_cop(ingresos['total_neto'])])
        writer.writerow(['Pedidos recibidos', int_cop(gastos['total_pedidos'])])
        writer.writerow(['Gastos hormiga', int_cop(gastos['total_hormiga'])])
        writer.writerow(['Total costos', int_cop(gastos['total'])])
        writer.writerow(['Balance final', int_cop(ingresos['total_neto'] - gastos['total'])])

    return response


# ============================================================
# 10. PEDIDOS (compras a proveedores)
# ============================================================

@login_required
@requiere_permisos('view_pedido')
def list_pedido(request):
    """Lista los pedidos, del más reciente al más antiguo."""
    pedidos = Pedido.objects.select_related('proveedor').order_by('-id')

    return render(request, 'list_pedido.html', {'pedidos': pedidos})


@login_required
@requiere_permisos('add_pedido', 'add_detallepedido', 'add_gasto', 'view_producto', 'view_proveedor')
def register_pedido(request):
    """Registra un pedido a un proveedor (queda Pendiente, sin costo todavía)."""
    productos = Producto.objects.all()
    proveedores = Proveedor.objects.order_by('nombre')

    if request.method == 'POST':
        proveedor_id = request.POST.get('proveedor')
        fecha = request.POST.get('fecha')

        # --- Paso 1: buscar el proveedor ---
        proveedor = None
        if proveedor_id and str(proveedor_id).isdigit():
            proveedor = Proveedor.objects.filter(pk=proveedor_id).first()

        if not proveedor:
            messages.error(request, 'Debes seleccionar un proveedor.')
            return redirect('register_pedido')

        productos_ids = request.POST.getlist('producto_id[]')
        cantidades = request.POST.getlist('cantidad[]')
        costos = request.POST.getlist('costo_unitario[]')
        precios_venta = request.POST.getlist('precio_venta[]')

        # --- Paso 2: validar TODAS las filas antes de guardar nada ---
        lineas = []
        try:
            for i in range(len(productos_ids)):
                cant = int(cantidades[i])
                costo = Decimal(limpiar_numero(costos[i]))
                precio_venta = Decimal(limpiar_numero(precios_venta[i]))

                if cant < 1 or costo < 0 or precio_venta <= 0:
                    raise ValueError
                if not costo.is_finite() or not precio_venta.is_finite():
                    raise ValueError

                producto = Producto.objects.get(id=int(productos_ids[i]))

                lineas.append((producto, cant, costo, precio_venta))
        except (ValueError, InvalidOperation, IndexError, Producto.DoesNotExist):
            messages.error(
                request,
                'Revisa los productos: cantidad, precio de compra y '
                'precio de venta deben ser valores válidos.'
            )
            return redirect('register_pedido')

        if not lineas:
            messages.error(request, 'Agrega al menos un producto al pedido.')
            return redirect('register_pedido')

        # --- Paso 3: guardar todo ---
        with transaction.atomic():
            # 3.1 Crear el pedido principal
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha=fecha,
                estado='Pendiente',
                costo_total=0
            )

            costo_total_acumulado = Decimal('0')

            # 3.2 Guardar cada producto del pedido
            for producto, cant, costo, precio_venta in lineas:
                costo_total_acumulado += cant * costo

                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cant,
                    costo_unitario=costo
                )

                # Actualizamos los precios en el producto
                producto.precio_compra = costo
                producto.precio_venta = precio_venta
                producto.save(update_fields=['precio_compra', 'precio_venta'])

            # 3.3 Guardar el costo total del pedido
            pedido.costo_total = costo_total_acumulado
            pedido.save()

            # El costo NO se registra aquí: el pedido empieza "Pendiente" y
            # solo cuenta como costo en los reportes cuando se marque "Recibido".

        messages.success(
            request,
            'Pedido registrado. Se contará como costo cuando lo marques como Recibido.'
        )
        return redirect('list_pedido')

    return render(request, 'register_pedido.html', {
        'productos': productos,
        'proveedores': proveedores,
    })


@login_required
@permiso_pedido
def pedido_details(request, pedido_id):
    """Muestra un pedido y permite cambiar su estado (actualiza el stock)."""
    pedido = get_object_or_404(Pedido, id=pedido_id)
    detalles = DetallePedido.objects.filter(pedido=pedido)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')

        if nuevo_estado not in ESTADOS_PEDIDO:
            messages.error(request, 'Selecciona un estado válido.')
            return redirect('pedido_details', pedido_id=pedido.id)

        with transaction.atomic():
            # Pasa a Recibido -> sumamos el stock
            if nuevo_estado == 'Recibido' and pedido.estado != 'Recibido':
                for detalle in detalles:
                    detalle.producto.cantidad_disponible += detalle.cantidad
                    detalle.producto.save()

                # Desde hoy el pedido cuenta como costo en los reportes
                pedido.fecha_recepcion = timezone.localdate()

            # Estaba Recibido y cambia a otro estado -> quitamos el stock
            elif pedido.estado == 'Recibido' and nuevo_estado != 'Recibido':
                for detalle in detalles:
                    detalle.producto.cantidad_disponible -= detalle.cantidad
                    detalle.producto.save()

                # Ya no cuenta como costo
                pedido.fecha_recepcion = None

            pedido.estado = nuevo_estado
            pedido.save()

        messages.success(request, f'Estado del pedido actualizado a {nuevo_estado}.')
        return redirect('pedido_details', pedido_id=pedido.id)

    return render(request, 'pedido_details.html', {
        'pedido': pedido,
        'detalles': detalles
    })


@login_required
@require_POST
@requiere_permisos('delete_pedido')
def eliminar_pedido(request, pedido_id):
    """Elimina un pedido. Los pedidos ya recibidos no se pueden eliminar."""
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        # Un pedido recibido ya sumó su stock y puede que ya se haya vendido.
        if pedido.estado == 'Recibido':
            messages.error(
                request,
                'No se puede eliminar este pedido porque ya fue recibido '
                'y su stock ya se sumó al inventario.'
            )
            return redirect('pedido_details', pedido_id=pedido.id)

        with transaction.atomic():
            # Borramos el gasto de ESTE pedido (si existe).
            # (endswith evita que "Pedido #1" borre también "#10", "#11"...)
            Gasto.objects.filter(
                descripcion__endswith=f"(Pedido #{pedido.id})"
            ).delete()

            pedido.delete()

        messages.success(request, 'Pedido eliminado correctamente.')
        return redirect('list_pedido')

    return redirect('pedido_details', pedido_id=pedido.id)


# ============================================================
# 11. PROVEEDORES
# ============================================================

@login_required
@requiere_permisos('view_proveedor')
def list_proveedor(request):
    buscar = request.GET.get('buscar')

    proveedores = Proveedor.objects.annotate(total_pedidos=Count('pedidos'))

    if buscar:
        proveedores = proveedores.filter(
            Q(nombre__icontains=buscar)
            | Q(telefono__icontains=buscar)
            | Q(correo__icontains=buscar)
        )

    return render(request, 'list_proveedor.html', {
        'proveedores': proveedores,
        'buscar': buscar
    })


@login_required
@requiere_permisos('add_proveedor')
def register_proveedor(request):
    siguiente = request.POST.get('next') or request.GET.get('next')

    if request.method == 'POST':
        form = ProveedorForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor registrado correctamente.')

            if siguiente == 'pedido':
                return redirect('register_pedido')
            return redirect('list_proveedor')
    else:
        form = ProveedorForm()

    return render(request, 'register_proveedor.html', {
        'form': form,
        'siguiente': siguiente,
    })


@login_required
@requiere_permisos('view_proveedor', 'view_pedido')
def proveedor_details(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    pedidos = proveedor.pedidos.order_by('-id')

    total_comprado = pedidos.exclude(estado='Cancelado').aggregate(
        total=Sum('costo_total')
    )['total'] or 0

    # Cuántos pedidos hay en cada estado (para los tres cuadros de colores)
    resumen = {
        'recibidos': pedidos.filter(estado='Recibido').count(),
        'pendientes': pedidos.filter(estado='Pendiente').count(),
        'cancelados': pedidos.filter(estado='Cancelado').count(),
    }

    return render(request, 'proveedor_details.html', {
        'proveedor': proveedor,
        'pedidos': pedidos,
        'total_comprado': total_comprado,
        'resumen': resumen,
    })


@login_required
@requiere_permisos('change_proveedor')
def proveedor_update(request, proveedor_id):

    proveedor = get_object_or_404(Proveedor, id=proveedor_id)

    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)

        if form.is_valid():
            form.save()
            messages.success(request, 'Proveedor actualizado correctamente.')
            return redirect('proveedor_details', proveedor_id=proveedor.id)
    else:
        form = ProveedorForm(instance=proveedor)

    return render(request, 'proveedor_update.html', {
        'form': form,
        'proveedor': proveedor,
    })


@login_required
@requiere_permisos('delete_proveedor')
def proveedor_delete(request, proveedor_id):

    proveedor = get_object_or_404(Proveedor, id=proveedor_id)

    if request.method == 'POST':
        if proveedor.pedidos.exists():
            messages.error(
                request,
                f'No se puede eliminar a {proveedor.nombre} porque tiene pedidos registrados.'
            )
            return redirect('proveedor_details', proveedor_id=proveedor.id)

        nombre = proveedor.nombre
        proveedor.delete()
        messages.success(request, f'El proveedor {nombre} fue eliminado correctamente.')
        return redirect('list_proveedor')

    return redirect('proveedor_details', proveedor_id=proveedor.id)


# ============================================================
# 12. CANCELACIÓN DE VENTAS Y REEMBOLSOS
# ============================================================

def dinero_recibido_de_venta(venta):
    """
    Dinero que MisMary realmente recibió por esta venta (lo que se devuelve).
    Cuenta el pago inicial y todos los abonos posteriores de la deuda de la venta.
    """
    deudas = venta.deudas.all()

    if deudas.exists():
        total = Abono.objects.filter(deuda__in=deudas).aggregate(t=Sum('valor'))['t']
    else:
        # ventas viejas sin deuda ligada: solo se conoce el pago inicial
        total = venta.pagos.aggregate(t=Sum('valor'))['t']

    return total or Decimal('0')


def crear_reembolso_automatico(venta, usuario=None, metodo=None):
    """
    Crea el reembolso ya HECHO (una sola confirmación).
    Devuelve lo que el cliente realmente pagó y deja registrado
    quién lo hizo y cuándo.
    """
    if venta.estado != 'Cancelada':
        return None, False

    if metodo not in METODOS_VALIDOS:
        metodo = getattr(venta, 'forma_pago', 'Otro') or 'Otro'
        if metodo not in METODOS_VALIDOS:
            metodo = 'Otro'

    monto = dinero_recibido_de_venta(venta)
    ahora = timezone.now()

    if monto > 0:
        estado, fecha_dev = 'Devuelto', ahora
        obs = 'Reembolso realizado al cancelar la venta.'
    else:
        estado, fecha_dev = 'No aplica', None
        obs = 'El cliente no había pagado nada, no hay dinero que devolver.'

    reembolso, creado = Reembolso.objects.get_or_create(
        venta=venta,
        defaults={
            'motivo': 'Reembolso generado por cancelación de venta',
            'monto': monto,
            'metodo': metodo,
            'estado': estado,
            'fecha_devolucion': fecha_dev,
            'observaciones': obs,
            'registrado_por': usuario,
        }
    )

    return reembolso, creado


@login_required
@requiere_permisos('change_venta')
def cancelar_venta(request, venta_id):
    venta = get_object_or_404(
        Venta.objects.select_related('cliente'), pk=venta_id
    )

    if venta.estado == 'Cancelada':
        messages.info(request, f'La venta #{venta.id} ya estaba reembolsada.')
        reembolso = Reembolso.objects.filter(venta=venta).first()
        if reembolso:
            return redirect('details_reembolso', reembolso_id=reembolso.id)
        return redirect('list_venta')

    if request.method == 'GET':
        metodo_sugerido = venta.forma_pago if venta.forma_pago in METODOS_VALIDOS else 'Otro'
        return render(request, 'cancelar_venta.html', {
            'venta': venta,
            'detalles': venta.detalles.select_related('producto'),
            'monto_devolver': dinero_recibido_de_venta(venta),
            'metodos': METODOS_VALIDOS,
            'metodo_sugerido': metodo_sugerido,
        })

    if request.method != 'POST':
        return redirect('list_venta')

    metodo = request.POST.get('metodo', '')
    if metodo not in METODOS_VALIDOS:
        messages.error(request, 'Selecciona la forma en que se devuelve el dinero.')
        return redirect('cancelar_venta', venta_id=venta.id)

    devolver_stock = request.POST.get('devolver_stock') == 'on'

    with transaction.atomic():
        venta.estado = 'Cancelada'
        venta.save(update_fields=['estado'])
        reembolso, creado = crear_reembolso_automatico(
            venta, usuario=request.user, metodo=metodo
        )

        # La deuda de esta venta ya no se cobra: queda cancelada y sin saldo
        venta.deudas.update(estado='Cancelada', saldo=0)

        # Opcional: los productos vuelven al inventario
        if devolver_stock:
            for detalle in venta.detalles.select_related('producto'):
                producto = detalle.producto

                if producto:
                    producto.cantidad_disponible += detalle.cantidad
                    producto.save(update_fields=['cantidad_disponible'])

    if reembolso.estado == 'Devuelto':
        messages.success(
            request,
            f'Reembolso realizado: se devolvieron $ {reembolso.monto:,.0f} '
            f'de la venta #{venta.id}.'
        )
    else:
        messages.success(
            request,
            f'La venta #{venta.id} fue cancelada. El cliente no había pagado nada, '
            f'así que no hubo dinero que devolver.'
        )

    return redirect('details_reembolso', reembolso_id=reembolso.id)


@login_required
@requiere_permisos('view_reembolso')
def lista_reembolsos(request):
    reembolsos = (
        Reembolso.objects
        .select_related('venta', 'venta__cliente', 'registrado_por')
        .prefetch_related('venta__detalles__producto')
        .order_by('-fecha_solicitud')
    )

    return render(request, 'list_reembolsos.html', {'reembolsos': reembolsos})


@login_required
@requiere_permisos('add_reembolso', 'view_venta')
def solicitar_reembolso(request, venta_id):

    venta = get_object_or_404(Venta, pk=venta_id, estado='Cancelada')

    existente = Reembolso.objects.filter(venta=venta).first()

    if existente:
        return redirect('details_reembolso', reembolso_id=existente.id)

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        metodo = request.POST.get('metodo', 'Efectivo')
        observaciones = request.POST.get('observaciones', '').strip()

        try:
            monto = Decimal(request.POST.get('monto', '0'))
        except (InvalidOperation, TypeError, ValueError):
            monto = Decimal('0')

        if not motivo:
            messages.error(request, 'Escribe el motivo del reembolso.')

        elif not monto.is_finite() or monto <= 0 or monto > venta.valor_total:
            messages.error(
                request,
                'El importe debe ser mayor que cero y no superar el total de la venta.'
            )

        elif metodo not in METODOS_VALIDOS:
            messages.error(request, 'Selecciona un método válido.')

        else:
            reembolso = Reembolso.objects.create(
                venta=venta,
                motivo=motivo,
                monto=monto,
                metodo=metodo,
                observaciones=observaciones,
                estado='Solicitado'
            )

            messages.success(request, 'La solicitud de reembolso se registró correctamente.')
            return redirect('details_reembolso', reembolso_id=reembolso.id)

    return render(request, 'solicitar_reembolso.html', {'venta': venta})


@login_required
@requiere_permisos('view_reembolso')
def details_reembolso(request, reembolso_id):

    reembolso = get_object_or_404(
        Reembolso.objects.select_related('venta', 'venta__cliente', 'registrado_por'),
        pk=reembolso_id
    )

    return render(request, 'details_reembolso.html', {
        'reembolso': reembolso,
        'detalles': reembolso.venta.detalles.select_related('producto'),
    })


@login_required
@requiere_permisos('view_reembolso')
def details_reembolso_venta(request, venta_id):

    reembolso = get_object_or_404(Reembolso, venta_id=venta_id)

    return redirect('details_reembolso', reembolso_id=reembolso.id)


@login_required
@requiere_permisos('change_reembolso')
def registrar_devolucion(request, reembolso_id):

    reembolso = get_object_or_404(Reembolso, pk=reembolso_id)

    if request.method != 'POST':
        return redirect('details_reembolso', reembolso_id=reembolso.id)

    if reembolso.estado == 'Devuelto':
        messages.info(request, 'Este reembolso ya aparece como devuelto.')
        return redirect('details_reembolso', reembolso_id=reembolso.id)

    metodo = request.POST.get('metodo', reembolso.metodo)

    if metodo not in METODOS_VALIDOS:
        messages.error(request, 'Selecciona un método válido.')
        return redirect('details_reembolso', reembolso_id=reembolso.id)

    reembolso.metodo = metodo
    reembolso.estado = 'Devuelto'
    reembolso.fecha_devolucion = timezone.now()
    reembolso.registrado_por = request.user
    reembolso.save(update_fields=['metodo', 'estado', 'fecha_devolucion', 'registrado_por'])

    messages.success(request, 'La devolución quedó registrada.')
    return redirect('details_reembolso', reembolso_id=reembolso.id)