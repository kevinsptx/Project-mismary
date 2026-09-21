from django.shortcuts import render,redirect,get_object_or_404
from .models import Cliente

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

def register_cliente(request):
    if request.method == 'POST':
        nombre = request.POST['nombre']
        telefono = request.POST['telefono']
        direccion = request.POST['direccion']

        Cliente.objects.create(nombre= nombre, telefono=telefono, direccion=direccion)
        return redirect('list_cliente')
    return render(request,'register_cliente.html')

def cliente_details(request,id):
    cliente=get_object_or_404(Cliente,id=id)
    return render(request,'cliente_details.html',{'cliente':cliente})

def cliente_update(request,id):
    cliente= get_object_or_404(Cliente,id=id)

    if request.method=='POST':
        cliente.nombre =request.POST['nombre']
        cliente.telefono = request.POST['telefono']
        cliente.direccion = request.POST['direccion']
        cliente.save()
    
        return redirect('list_cliente')
    return render(request,'cliente_update.html',{'cliente':cliente})

def cliente_delete(request,id):
    cliente=get_object_or_404(Cliente,id=id)
    cliente.delete()
    return redirect('list_cliente')
