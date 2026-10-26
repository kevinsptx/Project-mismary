import csv
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .forms import (
    ProductoForm, AbonoForm, ClienteForm, GastoForm, ProveedorForm
)
from .models import (
    Cliente, Venta, Abono, Deuda, Categoria,
    Producto, DetalleVenta, Gasto, Pago,
    DetallePedido, Pedido, Proveedor,Reembolso
)


def int_cop(valor):
    """Formatea montos a pesos colombianos sin decimales."""
    if valor is None:
        return "$ 0"
    return f"$ {int(round(float(valor))):,}"


@login_required
def home(request):
    return render(request, 'home.html')


# ============================================================
# CLIENTES
# ============================================================

@login_required
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
def list_cliente(request):
    buscar = request.GET.get('buscar')

    if buscar:
        clientes = (
            Cliente.objects.filter(nombre__icontains=buscar)
            | Cliente.objects.filter(telefono__icontains=buscar)
        )
    else:
        clientes = Cliente.objects.all()

    return render(request, 'list_cliente.html', {
        'clientes': clientes,
        'buscar': buscar
    })


@login_required
def register_cliente(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']

        Cliente.objects.create(
            nombre=nombre,
            telefono=telefono,
            direccion=direccion
        )
        return redirect('list_cliente')

    return render(request, 'register_cliente.html')


@login_required
def cliente_details(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    tiene_deuda = Deuda.objects.filter(
        cliente=cliente, estado='Pendiente', saldo__gt=0
    ).exists()
    return render(request, 'cliente_details.html', {
        'cliente': cliente,
        'tiene_deuda': tiene_deuda
    })


@login_required
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
def cliente_delete(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    if cliente.ventas.exists():
        messages.error(request, f'No se puede eliminar a {cliente.nombre} porque tiene ventas registradas. Elimina primero las ventas asociadas si corresponde.')
        return redirect('list_cliente')

    if cliente.deudas.filter(estado='Pendiente', saldo__gt=0).exists():
        messages.error(request, f'No se puede eliminar a {cliente.nombre} porque tiene una deuda pendiente.')
        return redirect('list_cliente')

    if cliente.deudas.exists():
        messages.error(request, f'No se puede eliminar a {cliente.nombre} porque tiene registros de deudas y abonos.')
        return redirect('list_cliente')

    cliente.delete()
    messages.success(request, f'El cliente {cliente.nombre} fue eliminado correctamente.')
    return redirect('list_cliente')


# ============================================================
# PRODUCTOS
# ============================================================

@login_required
def register_producto(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('list_producto')
    else:
        form = ProductoForm()

    return render(request, 'register_producto.html', {'form': form})


@login_required
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
def producto_update(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        datos = request.POST.copy()
        precio = datos.get('precio_venta', '').strip()

        # Quitar únicamente los puntos usados como separadores de miles.
        datos['precio_venta'] = precio.replace('.', '')

        form = ProductoForm(datos, instance=producto)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Producto actualizado correctamente.'
            )
            return redirect('list_producto')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'producto_update.html', {
        'form': form,
        'producto': producto
    })




@login_required
def producto_delete(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        nombre_producto = producto.nombre

        with transaction.atomic():
            DetalleVenta.objects.filter(producto=producto).delete()
            producto.delete()

        messages.success(
            request,
            f'El producto "{nombre_producto}" y su historial fueron eliminados correctamente.'
        )
        return redirect('list_producto')

    return render(request, 'producto_delete.html', {'producto': producto})


@login_required
def productos_mas_vendidos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    productos_vendidos = DetalleVenta.objects.all()

    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        messages.error(
            request,
            'La fecha inicial no puede ser posterior a la fecha final.'
        )
        productos_vendidos = DetalleVenta.objects.none()
    else:
        if fecha_inicio:
            productos_vendidos = productos_vendidos.filter(
                venta__fecha__gte=fecha_inicio
            )

        if fecha_fin:
            productos_vendidos = productos_vendidos.filter(
                venta__fecha__lte=fecha_fin
            )

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
# VENTAS
# ============================================================

class StockInsuficiente(Exception):
    pass


@login_required
def register_venta(request):
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente')
        fecha = request.POST.get('fecha')

        producto_ids = request.POST.getlist('producto_id')
        cantidades = request.POST.getlist('cantidad')

        try:
            valor_pagado = Decimal(request.POST.get('valor_pagado') or '0')
        except (InvalidOperation, TypeError, ValueError):
            messages.error(request, 'El valor pagado no es válido.')
            return redirect('register_venta')

        if not valor_pagado.is_finite() or valor_pagado < 0:
            messages.error(request, 'El valor pagado no puede ser negativo.')
            return redirect('register_venta')

        cliente = get_object_or_404(Cliente, id=cliente_id)
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

        try:
            with transaction.atomic():
                productos = {
                    p.id: p
                    for p in Producto.objects.select_for_update().filter(
                        id__in=pedidos.keys()
                    )
                }

                if len(productos) != len(pedidos):
                    raise StockInsuficiente('Uno de los productos ya no existe.')

                valor_total = Decimal('0')

                for pid, cantidad in pedidos.items():
                    producto = productos[pid]

                    if cantidad > producto.cantidad_disponible:
                        raise StockInsuficiente(
                            f'No hay suficiente stock de "{producto.nombre}". '
                            f'Disponible: {producto.cantidad_disponible}.'
                        )

                    valor_total += producto.precio_venta * cantidad

                if valor_pagado > valor_total:
                    raise StockInsuficiente(
                        'Lo pagado no puede ser mayor que el valor total.'
                    )

                venta = Venta.objects.create(
                    cliente=cliente,
                    valor_total=valor_total,
                    fecha=fecha
                )

                if valor_pagado > 0:
                    Pago.objects.create(
                        venta=venta,
                        valor=valor_pagado
                    )

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

                saldo = valor_total - valor_pagado

                if saldo > 0 or valor_pagado > 0:
                    estado = 'Pagada' if saldo == 0 else 'Pendiente'

                    deuda = Deuda.objects.create(
                        cliente=cliente,
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

        except StockInsuficiente as e:
            messages.error(request, str(e))
            return redirect('register_venta')

        messages.success(request, 'Venta registrada correctamente.')
        return redirect('list_venta')

    clientes = Cliente.objects.all()
    productos = Producto.objects.filter(
        cantidad_disponible__gt=0
    ).order_by('nombre')

    return render(request, 'register_venta.html', {
        'clientes': clientes,
        'productos': productos,
    })


@login_required
def list_venta(request):
    buscar = request.GET.get('buscar')

    if buscar:
        ventas = Venta.objects.filter(cliente__nombre__icontains=buscar)
    else:
        ventas = Venta.objects.all()

    return render(request, 'list_ventas.html', {
        'ventas': ventas,
        'buscar': buscar
    })


@login_required
def venta_details(request, id):
    venta = get_object_or_404(Venta, id=id)

    detalles = venta.detalles.select_related('producto').all()

    return render(request, 'venta_details.html', {
        'venta': venta,
        'detalles': detalles,
        'deuda': None,
    })


@login_required
def venta_delete(request, id):
    venta = get_object_or_404(Venta, id=id)

    with transaction.atomic():
        for detalle in venta.detalles.select_related('producto'):
            producto = detalle.producto

            if producto:
                producto.cantidad_disponible += detalle.cantidad
                producto.save(update_fields=['cantidad_disponible'])

        deudas = Deuda.objects.filter(
            cliente=venta.cliente,
            valor_total=venta.valor_total
        )

        for deuda in deudas:
            deuda.abonos.all().delete()
            deuda.delete()

        venta.delete()

    messages.success(
        request,
        'La venta y sus deudas/abonos asociados fueron eliminados.'
    )
    return redirect('list_venta')


@login_required
def ventas_pendientes(request):
    deudas = Deuda.objects.filter(
        estado='Pendiente'
    ).select_related('cliente')

    return render(request, 'ventas_pendientes.html', {'deudas': deudas})


@login_required
def consultar_por_fecha(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    ventas = None
    abonos = None

    if fecha_inicio and fecha_fin:
        ventas = Venta.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('cliente')

        abonos = Abono.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('deuda__cliente')

    return render(request, 'consultar_por_fecha.html', {
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'ventas': ventas,
        'abonos': abonos,
    })


# ============================================================
# ABONOS Y DEUDAS
# ============================================================

@login_required
def lista_abonos(request):
    abonos = Abono.objects.filter(
        deuda__saldo__gt=0
    ).select_related(
        'deuda__cliente'
    ).order_by('-fecha')

    return render(request, 'abonos.html', {
        'abonos': abonos
    })

@login_required
def registrar_abono(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == 'POST':
        form = AbonoForm(request.POST)

        if form.is_valid():
            valor_abono = form.cleaned_data['valor']

            if valor_abono <= 0:
                form.add_error(
                    'valor',
                    'El valor del abono debe ser mayor que cero.'
                )
            elif valor_abono > deuda.saldo:
                form.add_error(
                    'valor',
                    'El abono no puede ser mayor que el saldo pendiente.'
                )
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
def eliminar_pendiente(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == 'POST':
        with transaction.atomic():
            ventas = Venta.objects.filter(
                cliente=deuda.cliente,
                valor_total=deuda.valor_total
            )

            for venta in ventas:
                for detalle in venta.detalles.select_related('producto'):
                    if detalle.producto:
                        detalle.producto.cantidad_disponible += detalle.cantidad
                        detalle.producto.save(
                            update_fields=['cantidad_disponible']
                        )

                venta.delete()

            deuda.abonos.all().delete()
            deuda.delete()

        messages.success(
            request,
            'La deuda y sus registros asociados fueron eliminados.'
        )
        return redirect('ventas_pendientes')

    return redirect('detalle_pendiente', deuda_id=deuda.id)


@login_required
def detalle_deuda(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)
    abonos = deuda.abonos.all().order_by('-fecha')

    return render(request, 'detalle_deuda.html', {
        'deuda': deuda,
        'abonos': abonos
    })


@login_required
def editar_abono(request, abono_id):
    abono = get_object_or_404(Abono, id=abono_id)
    deuda = abono.deuda

    if request.method == 'POST':
        form = AbonoForm(request.POST)

        if form.is_valid():
            nuevo_valor = form.cleaned_data['valor']

            if nuevo_valor <= 0:
                form.add_error(
                    'valor',
                    'El valor del abono debe ser mayor que cero.'
                )
            else:
                saldo_anterior = deuda.saldo + abono.valor

                if nuevo_valor > saldo_anterior:
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

                    messages.success(
                        request,
                        'Abono actualizado correctamente.'
                    )
                    return redirect('lista_abonos')
    else:
        form = AbonoForm(instance=abono)

    return render(request, 'editar_abono.html', {
        'form': form,
        'abono': abono
    })


@login_required
def eliminar_abono(request, abono_id):
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
def detalle_pendiente(request, deuda_id):
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
def marcar_pagada(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == 'POST':
        deuda.saldo = 0
        deuda.estado = 'Pagada'
        deuda.save()

        messages.success(request, 'La venta fue marcada como pagada.')
        return redirect('ventas_pendientes')

    return redirect('detalle_pendiente', deuda_id=deuda.id)


@login_required
def cliente_historial(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    ventas = Venta.objects.filter(cliente=cliente).order_by('-fecha')
    abonos = Abono.objects.filter(
        deuda__cliente=cliente
    ).order_by('-fecha')

    saldo_pendiente = Deuda.objects.filter(
        cliente=cliente,
        estado='Pendiente'
    ).aggregate(total=Sum('saldo'))['total'] or 0

    return render(request, 'cliente_historial.html', {
        'cliente': cliente,
        'ventas': ventas,
        'abonos': abonos,
        'saldo_pendiente': saldo_pendiente
    })


# ============================================================
# REPORTES
# ============================================================

def filtrar_por_fecha(consulta, fecha_inicio, fecha_fin):
    if fecha_inicio:
        consulta = consulta.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        consulta = consulta.filter(fecha__lte=fecha_fin)

    return consulta


def datos_ingresos(fecha_inicio, fecha_fin):
    pagos = Pago.objects.all()

    if fecha_inicio:
        pagos = pagos.filter(fecha__date__gte=fecha_inicio)

    if fecha_fin:
        pagos = pagos.filter(fecha__date__lte=fecha_fin)

    pagos_por_fecha = (
        pagos.annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(total=Sum('valor'))
        .order_by('dia')
    )

    abonos = Abono.objects.all()

    if fecha_inicio:
        abonos = abonos.filter(fecha__date__gte=fecha_inicio)

    if fecha_fin:
        abonos = abonos.filter(fecha__date__lte=fecha_fin)

    abonos_por_fecha = (
        abonos.annotate(dia=TruncDate('fecha'))
        .values('dia')
        .annotate(total=Sum('valor'))
        .order_by('dia')
    )

    totales = {}

    for fila in pagos_por_fecha:
        dia = fila['dia']
        totales[dia] = totales.get(dia, Decimal('0')) + fila['total']

    for fila in abonos_por_fecha:
        dia = fila['dia']
        totales[dia] = totales.get(dia, Decimal('0')) + fila['total']

    ingresos_por_fecha = [
        {'fecha': dia, 'total': total}
        for dia, total in sorted(totales.items())
    ]

    total_ingresos = sum(totales.values(), Decimal('0'))

    return ingresos_por_fecha, total_ingresos


def datos_gastos(fecha_inicio, fecha_fin):
    gastos = filtrar_por_fecha(
        Gasto.objects.all(),
        fecha_inicio,
        fecha_fin
    )

    por_fecha = (
        gastos.values('fecha')
        .annotate(total=Sum('valor'))
        .order_by('fecha')
    )

    total = gastos.aggregate(total=Sum('valor'))['total'] or 0

    return por_fecha, total


def datos_clientes_deuda():
    clientes = Cliente.objects.filter(
        deudas__estado='Pendiente',
        deudas__saldo__gt=0
    ).annotate(
        saldo_pendiente=Sum('deudas__saldo')
    ).distinct()

    total = Deuda.objects.filter(
        estado='Pendiente',
        saldo__gt=0
    ).aggregate(total=Sum('saldo'))['total'] or 0

    return clientes, total


@login_required
def reportes(request):
    return render(request, 'reportes.html')


@login_required
def reporte_ingresos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    ingresos_por_fecha, total_ingresos = datos_ingresos(
        fecha_inicio,
        fecha_fin
    )

    return render(request, 'reporte_ingresos.html', {
        'ingresos_por_fecha': ingresos_por_fecha,
        'total_ingresos': total_ingresos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })


@login_required
def reporte_clientes_deuda(request):
    clientes, total_deuda = datos_clientes_deuda()

    return render(request, 'reporte_clientes_deuda.html', {
        'clientes': clientes,
        'total_deuda': total_deuda
    })


@login_required
def registrar_gasto(request):
    if request.method == 'POST':
        form = GastoForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Gasto registrado correctamente.')
            return redirect('reporte_gastos')
    else:
        form = GastoForm()

    return render(request, 'registrar_gasto.html', {'form': form})


@login_required
def reporte_gastos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    gastos_por_fecha, total_gastos = datos_gastos(
        fecha_inicio,
        fecha_fin
    )

    return render(request, 'reporte_gastos.html', {
        'gastos_por_fecha': gastos_por_fecha,
        'total_gastos': total_gastos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })


@login_required
def reporte_balance(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    total_ingresos = datos_ingresos(fecha_inicio, fecha_fin)[1]
    total_gastos = datos_gastos(fecha_inicio, fecha_fin)[1]
    balance = total_ingresos - total_gastos

    return render(request, 'reporte_balance.html', {
        'total_ingresos': total_ingresos,
        'total_gastos': total_gastos,
        'balance': balance,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })


@login_required
def descargar_reporte(request):
    tipo = request.GET.get('tipo')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if not tipo:
        return render(request, 'descargar_reporte.html')

    if tipo not in ['ingresos', 'gastos', 'clientes_deuda', 'balance']:
        messages.error(request, 'Selecciona un tipo de reporte válido.')
        return redirect('descargar_reporte')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="reporte_{tipo}.csv"'
    )
    response.write('\ufeff')

    writer = csv.writer(response)

    if tipo == 'ingresos':
        por_fecha, total = datos_ingresos(fecha_inicio, fecha_fin)

        writer.writerow(['Fecha', 'Total vendido'])

        for fila in por_fecha:
            writer.writerow([fila['fecha'], int_cop(fila['total'])])

        writer.writerow(['TOTAL', int_cop(total)])

    elif tipo == 'gastos':
        por_fecha, total = datos_gastos(fecha_inicio, fecha_fin)

        writer.writerow(['Fecha', 'Total gastado'])

        for fila in por_fecha:
            writer.writerow([fila['fecha'], int_cop(fila['total'])])

        writer.writerow(['TOTAL', int_cop(total)])

    elif tipo == 'clientes_deuda':
        clientes, total = datos_clientes_deuda()

        writer.writerow(['Cliente', 'Saldo pendiente'])

        for cliente in clientes:
            writer.writerow([
                cliente.nombre,
                int_cop(cliente.saldo_pendiente)
            ])

        writer.writerow(['TOTAL', int_cop(total)])

    elif tipo == 'balance':
        ingresos = datos_ingresos(fecha_inicio, fecha_fin)[1]
        gastos = datos_gastos(fecha_inicio, fecha_fin)[1]

        writer.writerow(['Concepto', 'Valor'])
        writer.writerow(['Ingresos', int_cop(ingresos)])
        writer.writerow(['Gastos', int_cop(gastos)])
        writer.writerow(['Balance final', int_cop(ingresos - gastos)])

    return response


# ============================================================
# PEDIDOS
# ============================================================

@login_required
def list_pedido(request):
    # Trae todos los pedidos ordenados del más reciente al más antiguo
    pedidos = Pedido.objects.select_related('proveedor').order_by('-id')
    return render(request, 'list_pedido.html', {'pedidos': pedidos})


@login_required
def register_pedido(request):
    productos = Producto.objects.all()
    proveedores = Proveedor.objects.order_by('nombre')

    if request.method == 'POST':
        proveedor_id = request.POST.get('proveedor')
        fecha = request.POST.get('fecha')

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

        # Se validan todas las filas ANTES de guardar nada.
        lineas = []
        try:
            for i in range(len(productos_ids)):
                cant = int(cantidades[i])
                costo = Decimal(costos[i])
                precio_venta = Decimal(precios_venta[i])

                if cant < 1 or costo < 0 or precio_venta <= 0:
                    raise ValueError
                if not costo.is_finite() or not precio_venta.is_finite():
                    raise ValueError

                lineas.append((productos_ids[i], cant, costo, precio_venta))
        except (ValueError, InvalidOperation, IndexError):
            messages.error(
                request,
                'Revisa los productos: cantidad, precio de compra y '
                'precio de venta deben ser valores válidos.'
            )
            return redirect('register_pedido')

        if not lineas:
            messages.error(request, 'Agrega al menos un producto al pedido.')
            return redirect('register_pedido')

        with transaction.atomic():
            # 1. Creamos el pedido principal
            pedido = Pedido.objects.create(
                proveedor=proveedor,
                fecha=fecha,
                estado='Pendiente',
                costo_total=0
            )

            costo_total_acumulado = Decimal('0')

            # 2. Recorremos los productos agregados
            for p_id, cant, costo, precio_venta in lineas:
                costo_total_acumulado += cant * costo

                producto = get_object_or_404(Producto, id=p_id)
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=cant,
                    costo_unitario=costo
                )

                # El precio de compra y de venta del pedido quedan en el
                # producto para mostrarlos en la tabla de productos.
                producto.precio_compra = costo
                producto.precio_venta = precio_venta
                producto.save(update_fields=['precio_compra', 'precio_venta'])

            # 3. Guardamos el costo total del pedido
            pedido.costo_total = costo_total_acumulado
            pedido.save()

            # 4. Sincronización automática con Gastos
            Gasto.objects.create(
                descripcion=f"Pedido a proveedor: {proveedor.nombre} (Pedido #{pedido.id})",
                valor=costo_total_acumulado,
                fecha=fecha,
                tipo='Pedido'
            )

        messages.success(request, 'Pedido registrado y sincronizado en gastos correctamente.')
        return redirect('list_pedido')

    return render(request, 'register_pedido.html', {
        'productos': productos,
        'proveedores': proveedores,
    })


@login_required
def pedido_details(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    detalles = DetallePedido.objects.filter(pedido=pedido)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')

        # Si el pedido no estaba recibido y ahora se marca como Recibido, sumamos el stock
        if nuevo_estado == 'Recibido' and pedido.estado != 'Recibido':
            for detalle in detalles:
                detalle.producto.cantidad_disponible += detalle.cantidad
                detalle.producto.save()

        # Si estaba Recibido y se vuelve a poner Pendiente o Cancelado, quitamos el stock sumado
        elif pedido.estado == 'Recibido' and nuevo_estado != 'Recibido':
            for detalle in detalles:
                detalle.producto.cantidad_disponible -= detalle.cantidad
                detalle.producto.save()

        pedido.estado = nuevo_estado
        pedido.save()

        messages.success(request, f'Estado del pedido actualizado a {nuevo_estado}.')
        return redirect('pedido_details', pedido_id=pedido.id)

    return render(request, 'pedido_details.html', {
        'pedido': pedido,
        'detalles': detalles
    })


@login_required
def eliminar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if request.method == 'POST':
        detalles = DetallePedido.objects.filter(pedido=pedido)

        # Restar stock si ya se había recibido
        if pedido.estado == 'Recibido':
            for detalle in detalles:
                detalle.producto.cantidad_disponible -= detalle.cantidad
                detalle.producto.save()

        # Eliminar el gasto asociado a ESTE pedido (endswith evita que
        # "Pedido #1" borre también los gastos de "Pedido #10", "#11", etc.)
        Gasto.objects.filter(
            descripcion__endswith=f"(Pedido #{pedido.id})"
        ).delete()

        pedido.delete()
        messages.success(request, 'Pedido y su gasto asociado eliminados correctamente.')
        return redirect('list_pedido')

    return redirect('pedido_details', pedido_id=pedido.id)


# ============================================================
# PROVEEDORES
# ============================================================

@login_required
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
def register_proveedor(request):
    # Si venimos desde "Registrar pedido", al guardar regresamos allá
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
def proveedor_details(request, proveedor_id):
    proveedor = get_object_or_404(Proveedor, id=proveedor_id)
    pedidos = proveedor.pedidos.order_by('-id')

    total_comprado = pedidos.exclude(estado='Cancelado').aggregate(
        total=Sum('costo_total')
    )['total'] or 0

    return render(request, 'proveedor_details.html', {
        'proveedor': proveedor,
        'pedidos': pedidos,
        'total_comprado': total_comprado,
    })


@login_required
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
# CANCELACIÓN DE VENTAS Y REEMBOLSOS
# ============================================================

def crear_reembolso_automatico(venta):
    """Crea un reembolso para una venta cancelada si aún no existe."""
    if venta.estado != 'Cancelada':
        return None, False

    metodo_pago = getattr(venta, 'forma_pago', 'Otro') or 'Otro'

    if metodo_pago not in ['Efectivo', 'Transferencia', 'Otro']:
        metodo_pago = 'Otro'

    reembolso, creado = Reembolso.objects.get_or_create(
        venta=venta,
        defaults={
            'motivo': 'Reembolso generado por cancelación de venta',
            'monto': venta.valor_total,
            'metodo': metodo_pago,
            'estado': 'Solicitado',
            'observaciones': (
                'Registro generado automáticamente al cancelar la venta.'
            ),
        }
    )

    return reembolso, creado


@login_required
def cancelar_venta(request, venta_id):
    venta = get_object_or_404(Venta, pk=venta_id)

    if request.method == 'GET':
        return render(
            request,
            'cancelar_venta.html',
            {'venta': venta}
        )

    if request.method != 'POST':
        return redirect('list_venta')

    with transaction.atomic():
        if venta.estado != 'Cancelada':
            venta.estado = 'Cancelada'
            venta.save(update_fields=['estado'])

        reembolso, creado = crear_reembolso_automatico(venta)

    if creado:
        messages.success(
            request,
            f'La venta #{venta.id} fue cancelada y su reembolso quedó registrado.'
        )
    else:
        messages.info(
            request,
            f'La venta #{venta.id} ya estaba cancelada o ya tenía un reembolso.'
        )

    return redirect('list_venta')


@login_required
def lista_reembolsos(request):
    # Crea los reembolsos que falten para las ventas canceladas anteriormente.
    ventas_canceladas = Venta.objects.filter(estado='Cancelada')

    for venta in ventas_canceladas.iterator():
        crear_reembolso_automatico(venta)

    reembolsos = (
        Reembolso.objects
        .select_related('venta', 'venta__cliente')
        .order_by('-fecha_solicitud')
    )

    return render(
        request,
        'list_reembolsos.html',
        {'reembolsos': reembolsos}
    )


@login_required
def solicitar_reembolso(request, venta_id):
    venta = get_object_or_404(
        Venta,
        pk=venta_id,
        estado='Cancelada'
    )

    existente = Reembolso.objects.filter(venta=venta).first()

    if existente:
        return redirect(
            'details_reembolso',
            reembolso_id=existente.id
        )

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()
        metodo = request.POST.get('metodo', 'Efectivo')
        observaciones = request.POST.get('observaciones', '').strip()

        try:
            monto = Decimal(request.POST.get('monto', '0'))
        except (InvalidOperation, TypeError, ValueError):
            monto = Decimal('0')

        metodos_validos = [
            'Efectivo',
            'Transferencia',
            'Otro'
        ]

        if not motivo:
            messages.error(
                request,
                'Escribe el motivo del reembolso.'
            )

        elif (
            not monto.is_finite()
            or monto <= 0
            or monto > venta.valor_total
        ):
            messages.error(
                request,
                'El importe debe ser mayor que cero y no superar el total de la venta.'
            )

        elif metodo not in metodos_validos:
            messages.error(
                request,
                'Selecciona un método válido.'
            )

        else:
            reembolso = Reembolso.objects.create(
                venta=venta,
                motivo=motivo,
                monto=monto,
                metodo=metodo,
                observaciones=observaciones,
                estado='Solicitado'
            )

            messages.success(
                request,
                'La solicitud de reembolso se registró correctamente.'
            )

            return redirect(
                'details_reembolso',
                reembolso_id=reembolso.id
            )

    return render(
        request,
        'solicitar_reembolso.html',
        {'venta': venta}
    )


@login_required
def details_reembolso(request, reembolso_id):
    reembolso = get_object_or_404(
        Reembolso.objects.select_related(
            'venta',
            'venta__cliente'
        ),
        pk=reembolso_id
    )

    return render(
        request,
        'details_reembolso.html',
        {'reembolso': reembolso}
    )


@login_required
def details_reembolso_venta(request, venta_id):
    reembolso = get_object_or_404(
        Reembolso,
        venta_id=venta_id
    )

    return redirect(
        'details_reembolso',
        reembolso_id=reembolso.id
    )


@login_required
def registrar_devolucion(request, reembolso_id):
    reembolso = get_object_or_404(
        Reembolso,
        pk=reembolso_id
    )

    if request.method != 'POST':
        return redirect(
            'details_reembolso',
            reembolso_id=reembolso.id
        )

    if reembolso.estado == 'Devuelto':
        messages.info(
            request,
            'Este reembolso ya aparece como devuelto.'
        )

        return redirect(
            'details_reembolso',
            reembolso_id=reembolso.id
        )

    metodo = request.POST.get(
        'metodo',
        reembolso.metodo
    )

    if metodo not in ['Efectivo', 'Transferencia', 'Otro']:
        messages.error(
            request,
            'Selecciona un método válido.'
        )

        return redirect(
            'details_reembolso',
            reembolso_id=reembolso.id
        )

    reembolso.metodo = metodo
    reembolso.estado = 'Devuelto'
    reembolso.fecha_devolucion = timezone.now()

    reembolso.save(
        update_fields=[
            'metodo',
            'estado',
            'fecha_devolucion'
        ]
    )

    messages.success(
        request,
        'La devolución quedó registrada.'
    )

    return redirect(
        'details_reembolso',
        reembolso_id=reembolso.id
    )