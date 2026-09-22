from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Cliente, Venta


@login_required
def home(request):
    return render(request, 'home.html')


@login_required
def list_cliente(request):
    buscar = request.GET.get('buscar')

    if buscar:
        clientes = Cliente.objects.filter(
            nombre__icontains=buscar
        ) | Cliente.objects.filter(
            telefono__icontains=buscar
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

    return render(request, 'cliente_details.html', {
        'cliente': cliente
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

    return render(request, 'cliente_update.html', {
        'cliente': cliente
    })


@login_required
def cliente_delete(request, id):
    cliente = get_object_or_404(Cliente, id=id)
    cliente.delete()

    return redirect('list_cliente')


@login_required
def register_venta(request):
    if request.method == 'POST':
        cliente_id = request.POST['cliente']
        valor_total = request.POST['valor_total']
        fecha = request.POST['fecha']

        cliente = get_object_or_404(Cliente, id=cliente_id)

        Venta.objects.create(
            cliente=cliente,
            valor_total=valor_total,
            fecha=fecha
        )

        return redirect('list_venta')

    clientes = Cliente.objects.all()

    return render(request, 'register_venta.html', {
        'clientes': clientes
    })


@login_required
def list_venta(request):
    buscar = request.GET.get('buscar')

    if buscar:
        ventas = Venta.objects.filter(
            cliente__nombre__icontains=buscar
        )
    else:
        ventas = Venta.objects.all()

    return render(request, 'list_ventas.html', {
        'ventas': ventas,
        'buscar': buscar
    })
@login_required
def venta_details(request, id):
    venta = get_object_or_404(Venta, id=id)

    return render(request, 'venta_details.html', {
        'venta': venta
    })


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

    return render(request, 'venta_update.html', {
        'venta': venta,
        'clientes': clientes
    })


@login_required
def venta_delete(request, id):
    venta = get_object_or_404(Venta, id=id)
    venta.delete()

    return redirect('list_venta')