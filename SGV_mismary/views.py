from django.db.models import Sum
from .forms import ProductoForm, AbonoForm
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Cliente, Venta, Abono, Deuda, Categoria, Producto, DetalleVenta, Gasto
import csv
from django.http import HttpResponse


@login_required
def home(request):
    return render(request, 'home.html')


@login_required
def list_cliente(request):
    buscar = request.GET.get('buscar')

    if buscar:
        clientes = Cliente.objects.filter(nombre__icontains=buscar) | Cliente.objects.filter(telefono__icontains=buscar)
    else:
        clientes = Cliente.objects.all()

    return render(request, 'list_cliente.html', {'clientes': clientes, 'buscar': buscar})


@login_required
def register_cliente(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']

        Cliente.objects.create(nombre=nombre, telefono=telefono, direccion=direccion)

        return redirect('list_cliente')

    return render(request, 'register_cliente.html')


@login_required
def cliente_details(request, id):
    cliente = get_object_or_404(Cliente, id=id)

    return render(request, 'cliente_details.html', {'cliente': cliente})


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
    cliente.delete()

    return redirect('list_cliente')


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
        form = ProductoForm(request.POST, instance=producto)

        if form.is_valid():
            form.save()

            messages.success(request, 'Producto actualizado correctamente.')

            return redirect('list_producto')
    else:
        form = ProductoForm(instance=producto)

    return render(request, 'producto_update.html', {'form': form, 'producto': producto})


@login_required
def producto_delete(request, id):
    producto = get_object_or_404(Producto, id=id)

    if request.method == 'POST':
        nombre_producto = producto.nombre
        producto.delete()

        messages.success(request, f'El producto "{nombre_producto}" fue eliminado correctamente.')

        return redirect('list_producto')

    return render(request, 'producto_delete.html', {'producto': producto})


@login_required
def productos_mas_vendidos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    productos_vendidos = DetalleVenta.objects.all()

    if fecha_inicio and fecha_fin and fecha_inicio > fecha_fin:
        messages.error(request, 'La fecha inicial no puede ser posterior a la fecha final.')
        productos_vendidos = DetalleVenta.objects.none()
    else:
        if fecha_inicio:
            productos_vendidos = productos_vendidos.filter(venta__fecha__date__gte=fecha_inicio)

        if fecha_fin:
            productos_vendidos = productos_vendidos.filter(venta__fecha__date__lte=fecha_fin)

        productos_vendidos = productos_vendidos.values('producto__nombre').annotate(
            total_vendido=Sum('cantidad')
        ).order_by('-total_vendido')

    return render(request, 'productos_mas_vendidos.html', {
        'productos_vendidos': productos_vendidos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })


@login_required
def register_venta(request):
    if request.method == 'POST':
        cliente_id = request.POST['cliente']
        valor_total = Decimal(request.POST['valor_total'])
        valor_pagado = Decimal(request.POST.get('valor_pagado') or 0)
        fecha = request.POST['fecha']

        if valor_pagado > valor_total:
            messages.error(request, 'Lo pagado no puede ser mayor que el valor total.')
            return redirect('register_venta')

        cliente = get_object_or_404(Cliente, id=cliente_id)

        with transaction.atomic():
            Venta.objects.create(cliente=cliente, valor_total=valor_total, fecha=fecha)

            saldo = valor_total - valor_pagado

            if saldo > 0:
                Deuda.objects.create(
                    cliente=cliente,
                    valor_total=valor_total,
                    saldo=saldo,
                    estado='Pendiente'
                )

        return redirect('list_venta')

    clientes = Cliente.objects.all()

    return render(request, 'register_venta.html', {'clientes': clientes})


@login_required
def list_venta(request):
    buscar = request.GET.get('buscar')

    if buscar:
        ventas = Venta.objects.filter(cliente__nombre__icontains=buscar)
    else:
        ventas = Venta.objects.all()

    return render(request, 'list_ventas.html', {'ventas': ventas, 'buscar': buscar})


@login_required
def venta_details(request, id):
    venta = get_object_or_404(Venta, id=id)

    return render(request, 'venta_details.html', {'venta': venta})


@login_required
def venta_update(request, id):
    venta = get_object_or_404(Venta, id=id)

    if request.method == 'POST':
        cliente_id = request.POST['cliente']
        valor_total = request.POST['valor_total']
        fecha = request.POST['fecha']

        cliente = get_object_or_404(Cliente, id=cliente_id)

        venta.cliente = cliente
        venta.valor_total = valor_total
        venta.fecha = fecha
        venta.save()

        return redirect('list_venta')

    clientes = Cliente.objects.all()

    return render(request, 'venta_update.html', {'venta': venta, 'clientes': clientes})


@login_required
def venta_delete(request, id):
    venta = get_object_or_404(Venta, id=id)
    venta.delete()

    return redirect('list_venta')


@login_required
def inicio(request):
    deudas = Deuda.objects.all()
    abonos = Abono.objects.select_related('deuda__cliente').order_by('-fecha')

    ventas_filtradas = None
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        ventas_filtradas = Venta.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related('cliente').order_by('-fecha')

    if request.method == 'POST':
        deuda_id = request.POST.get('deuda_id')
        deuda = get_object_or_404(Deuda, id=deuda_id)

        form = AbonoForm(request.POST)

        if form.is_valid():
            valor_abono = form.cleaned_data['valor']

            if valor_abono <= 0:
                messages.error(request, 'El valor del abono debe ser mayor que cero.')
                return redirect('inicio')

            if valor_abono > deuda.saldo:
                messages.error(request, 'El abono no puede ser mayor que el saldo pendiente.')
                return redirect('inicio')

            with transaction.atomic():
                abono = form.save(commit=False)
                abono.deuda = deuda
                abono.save()

                deuda.saldo = deuda.saldo - valor_abono

                if deuda.saldo == 0:
                    deuda.estado = 'Pagada'
                else:
                    deuda.estado = 'Pendiente'

                deuda.save()

            messages.success(request, f'Abono de ${valor_abono} registrado correctamente.')

            return redirect('inicio')
        else:
            messages.error(request, 'Por favor, ingresa un valor válido.')
            return redirect('inicio')

    return render(request, 'inicio.html', {
        'deudas': deudas,
        'abonos': abonos,
        'ventas_filtradas': ventas_filtradas,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    })


def registrar_abono(request, deuda_id):
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

                    deuda.saldo = deuda.saldo - valor_abono

                    if deuda.saldo == 0:
                        deuda.estado = 'Pagada'
                    else:
                        deuda.estado = 'Pendiente'

                    deuda.save()

                messages.success(request, 'Abono registrado correctamente.')

                return redirect('inicio')
    else:
        form = AbonoForm()

    return render(request, 'registrar_abono.html', {'form': form, 'deuda': deuda})


def detalle_deuda(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)
    abonos = deuda.abonos.all().order_by('-fecha')

    return render(request, 'detalle_deuda.html', {'deuda': deuda, 'abonos': abonos})


def editar_abono(request, abono_id):
    abono = get_object_or_404(Abono, id=abono_id)
    deuda = abono.deuda

    if request.method == 'POST':
        form = AbonoForm(request.POST)

        if form.is_valid():
            nuevo_valor = form.cleaned_data['valor']

            if nuevo_valor <= 0:
                form.add_error('valor', 'El valor del abono debe ser mayor que cero.')
            else:
                saldo_anterior = deuda.saldo + abono.valor

                if nuevo_valor > saldo_anterior:
                    form.add_error('valor', 'El nuevo valor no puede ser mayor que la deuda pendiente.')
                else:
                    with transaction.atomic():
                        diferencia = nuevo_valor - abono.valor

                        abono.valor = nuevo_valor
                        abono.save()

                        deuda.saldo = deuda.saldo - diferencia

                        if deuda.saldo == 0:
                            deuda.estado = 'Pagada'
                        else:
                            deuda.estado = 'Pendiente'

                        deuda.save()

                    messages.success(request, 'Abono actualizado correctamente.')

                    return redirect('inicio')
    else:
        form = AbonoForm(instance=abono)

    return render(request, 'editar_abono.html', {'form': form, 'abono': abono})


def eliminar_abono(request, abono_id):
    abono = get_object_or_404(Abono, id=abono_id)
    deuda = abono.deuda

    if request.method == 'POST':
        with transaction.atomic():
            deuda.saldo = deuda.saldo + abono.valor

            if deuda.saldo == 0:
                deuda.estado = 'Pagada'
            else:
                deuda.estado = 'Pendiente'

            deuda.save()
            abono.delete()

        messages.success(request, 'Abono eliminado correctamente.')

        return redirect('inicio')

    return render(request, 'eliminar_abono.html', {'abono': abono})


@login_required
def ventas_pendientes(request):
    deudas = Deuda.objects.filter(estado='Pendiente').select_related('cliente')

    return render(request, 'ventas_pendientes.html', {'deudas': deudas})


@login_required
def detalle_pendiente(request, deuda_id):
    deuda = get_object_or_404(Deuda.objects.select_related('cliente'), id=deuda_id)
    abonos = deuda.abonos.all().order_by('-fecha')

    return render(request, 'detalle_pendiente.html', {'deuda': deuda, 'abonos': abonos})


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
    abonos = Abono.objects.filter(deuda__cliente=cliente).order_by('-fecha')

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


def filtrar_por_fecha(consulta, fecha_inicio, fecha_fin):
    if fecha_inicio:
        consulta = consulta.filter(fecha__gte=fecha_inicio)

    if fecha_fin:
        consulta = consulta.filter(fecha__lte=fecha_fin)

    return consulta


def datos_ingresos(fecha_inicio, fecha_fin):
    ventas = filtrar_por_fecha(Venta.objects.all(), fecha_inicio, fecha_fin)

    por_fecha = ventas.values('fecha').annotate(total=Sum('valor_total')).order_by('fecha')
    total = ventas.aggregate(total=Sum('valor_total'))['total'] or 0

    return por_fecha, total


def datos_gastos(fecha_inicio, fecha_fin):
    gastos = filtrar_por_fecha(Gasto.objects.all(), fecha_inicio, fecha_fin)

    por_fecha = gastos.values('fecha').annotate(total=Sum('valor')).order_by('fecha')
    total = gastos.aggregate(total=Sum('valor'))['total'] or 0

    return por_fecha, total


def datos_clientes_deuda():
    clientes = Cliente.objects.filter(
        deudas__estado='Pendiente'
    ).annotate(
        saldo_pendiente=Sum('deudas__saldo')
    )

    total = Deuda.objects.filter(
        estado='Pendiente'
    ).aggregate(total=Sum('saldo'))['total'] or 0

    return clientes, total


@login_required
def reportes(request):
    return render(request, 'reportes.html')


@login_required
def reporte_ingresos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    ingresos_por_fecha, total_ingresos = datos_ingresos(fecha_inicio, fecha_fin)

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
def reporte_gastos(request):
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    gastos_por_fecha, total_gastos = datos_gastos(fecha_inicio, fecha_fin)

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
    response['Content-Disposition'] = f'attachment; filename="reporte_{tipo}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)

    if tipo == 'ingresos':
        por_fecha, total = datos_ingresos(fecha_inicio, fecha_fin)

        writer.writerow(['Fecha', 'Total vendido'])

        for fila in por_fecha:
            writer.writerow([fila['fecha'], fila['total']])

        writer.writerow(['TOTAL', total])

    elif tipo == 'gastos':
        por_fecha, total = datos_gastos(fecha_inicio, fecha_fin)

        writer.writerow(['Fecha', 'Total gastado'])

        for fila in por_fecha:
            writer.writerow([fila['fecha'], fila['total']])

        writer.writerow(['TOTAL', total])

    elif tipo == 'clientes_deuda':
        clientes, total = datos_clientes_deuda()

        writer.writerow(['Cliente', 'Saldo pendiente'])

        for cliente in clientes:
            writer.writerow([cliente.nombre, cliente.saldo_pendiente])

        writer.writerow(['TOTAL', total])

    elif tipo == 'balance':
        ingresos = datos_ingresos(fecha_inicio, fecha_fin)[1]
        gastos = datos_gastos(fecha_inicio, fecha_fin)[1]

        writer.writerow(['Concepto', 'Valor'])
        writer.writerow(['Ingresos', ingresos])
        writer.writerow(['Gastos', gastos])
        writer.writerow(['Balance final', ingresos - gastos])

    return response