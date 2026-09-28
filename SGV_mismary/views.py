from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum

from .models import Cliente, Categoria, Producto, DetalleVenta
from .forms import ProductoForm


@login_required
def home(request):

    return render(
        request,
        'home.html'
    )


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

    return render(
        request,
        'list_cliente.html',
        {
            'clientes': clientes,
            'buscar': buscar
        }
    )


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

    return render(
        request,
        'register_cliente.html'
    )


@login_required
def cliente_details(request, id):

    cliente = get_object_or_404(
        Cliente,
        id=id
    )

    return render(
        request,
        'cliente_details.html',
        {
            'cliente': cliente
        }
    )


@login_required
def cliente_update(request, id):

    cliente = get_object_or_404(
        Cliente,
        id=id
    )

    if request.method == 'POST':

        cliente.nombre = request.POST['nombre']
        cliente.telefono = request.POST['telefono']
        cliente.direccion = request.POST['direccion']

        cliente.save()

        return redirect('list_cliente')

    return render(
        request,
        'cliente_update.html',
        {
            'cliente': cliente
        }
    )


@login_required
def cliente_delete(request, id):

    cliente = get_object_or_404(
        Cliente,
        id=id
    )

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

    return render(
        request,
        'register_producto.html',
        {
            'form': form
        }
    )


@login_required
def list_producto(request):

    buscar = request.GET.get('buscar')
    categoria_id = request.GET.get('categoria')

    categorias = Categoria.objects.all()

    productos = Producto.objects.all()

    if buscar:

        productos = productos.filter(
            nombre__icontains=buscar
        )

    if categoria_id:

        productos = productos.filter(
            categoria_id=categoria_id
        )

    return render(
        request,
        'list_producto.html',
        {
            'productos': productos,
            'buscar': buscar,
            'categorias': categorias,
            'categoria_id': categoria_id
        }
    )


@login_required
def producto_update(request, id):

    producto = get_object_or_404(
        Producto,
        id=id
    )

    if request.method == 'POST':

        form = ProductoForm(
            request.POST,
            instance=producto
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                'Producto actualizado correctamente.'
            )

            return redirect('list_producto')

    else:

        form = ProductoForm(
            instance=producto
        )

    return render(
        request,
        'producto_update.html',
        {
            'form': form,
            'producto': producto
        }
    )


@login_required
def producto_delete(request, id):

    producto = get_object_or_404(
        Producto,
        id=id
    )

    if request.method == 'POST':

        nombre_producto = producto.nombre

        producto.delete()

        messages.success(
            request,
            f'El producto "{nombre_producto}" fue eliminado correctamente.'
        )

        return redirect('list_producto')

    return render(
        request,
        'producto_delete.html',
        {
            'producto': producto
        }
    )


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
                venta__fecha__date__gte=fecha_inicio
            )

        if fecha_fin:

            productos_vendidos = productos_vendidos.filter(
                venta__fecha__date__lte=fecha_fin
            )

        productos_vendidos = productos_vendidos.values(
            'producto__nombre'
        ).annotate(
            total_vendido=Sum('cantidad')
        ).order_by(
            '-total_vendido'
        )

    return render(
        request,
        'productos_mas_vendidos.html',
        {
            'productos_vendidos': productos_vendidos,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin
        }
    )