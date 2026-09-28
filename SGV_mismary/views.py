from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Cliente, Venta, Abono, Deuda
from .forms import AbonoForm


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

    return render(request, 'list_cliente.html', {'clientes': clientes,'buscar': buscar})


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
def register_venta(request):
    if request.method == 'POST':
        cliente_id = request.POST['cliente']
        valor_total = Decimal(request.POST['valor_total'])
        valor_pagado = Decimal(request.POST.get('valor_pagado') or 0)
        fecha = request.POST['fecha']

        # Lo pagado no puede ser mayor que el total
        if valor_pagado > valor_total:
            messages.error(request, "Lo pagado no puede ser mayor que el valor total.")
            return redirect('register_venta')

        cliente = get_object_or_404(Cliente, id=cliente_id)

        with transaction.atomic():
            Venta.objects.create(
                cliente=cliente,
                valor_total=valor_total,
                fecha=fecha
            )

            # Cuánto falta por pagar
            saldo = valor_total - valor_pagado

            # Si falta plata, se crea la deuda pendiente
            if saldo > 0:
                Deuda.objects.create(
                    cliente=cliente,
                    valor_total=valor_total,
                    saldo=saldo,
                    estado="Pendiente"
                )

        return redirect('list_venta')

    clientes = Cliente.objects.all()

    return render(request, 'register_venta.html', {'clientes': clientes})


@login_required
def list_venta(request):
    buscar = request.GET.get('buscar')

    if buscar:
        ventas = Venta.objects.filter(
            cliente__nombre__icontains=buscar
        )
    else:
        ventas = Venta.objects.all()

    return render(request, 'list_ventas.html', {'ventas': ventas,'buscar': buscar})


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

    return render(request, 'venta_update.html', {'venta': venta,'clientes': clientes})


@login_required
def venta_delete(request, id):
    venta = get_object_or_404(Venta, id=id)
    venta.delete()

    return redirect('list_venta')


@login_required
def inicio(request):
    deudas = Deuda.objects.all()

    abonos = Abono.objects.select_related(
        "deuda__cliente"
    ).order_by("-fecha")

    ventas_filtradas = None
    fecha_inicio = request.GET.get("fecha_inicio")
    fecha_fin = request.GET.get("fecha_fin")

    if fecha_inicio and fecha_fin:
        ventas_filtradas = Venta.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin
        ).select_related("cliente").order_by("-fecha")

    if request.method == "POST":
        deuda_id = request.POST.get("deuda_id")

        deuda = get_object_or_404(Deuda, id=deuda_id)

        form = AbonoForm(request.POST)

        if form.is_valid():
            valor_abono = form.cleaned_data["valor"]

            if valor_abono <= 0:
                messages.error(
                    request,
                    "El valor del abono debe ser mayor que cero."
                )
                return redirect("inicio")

            if valor_abono > deuda.saldo:
                messages.error(
                    request,
                    "El abono no puede ser mayor que el saldo pendiente."
                )
                return redirect("inicio")

            with transaction.atomic():
                abono = form.save(commit=False)
                abono.deuda = deuda
                abono.save()

                deuda.saldo = deuda.saldo - valor_abono

                if deuda.saldo == 0:
                    deuda.estado = "Pagada"
                else:
                    deuda.estado = "Pendiente"

                deuda.save()

            messages.success(
                request,
                f"Abono de ${valor_abono} registrado correctamente."
            )

            return redirect("inicio")

        else:
            messages.error(
                request,
                "Por favor, ingresa un valor válido."
            )
            return redirect("inicio")

    return render(
        request,
        "inicio.html",
        {
            "deudas": deudas,
            "abonos": abonos,
            "ventas_filtradas": ventas_filtradas,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }
    )

def registrar_abono(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == "POST":
        form = AbonoForm(request.POST)

        if form.is_valid():
            valor_abono = form.cleaned_data["valor"]

            if valor_abono <= 0:
                form.add_error(
                    "valor",
                    "El valor del abono debe ser mayor que cero."
                )

            elif valor_abono > deuda.saldo:
                form.add_error(
                    "valor",
                    "El abono no puede ser mayor que el saldo pendiente."
                )

            else:
                with transaction.atomic():
                    abono = form.save(commit=False)
                    abono.deuda = deuda
                    abono.save()

                    # Descontar el abono
                    deuda.saldo = deuda.saldo - valor_abono

                    # Cambiar estado
                    if deuda.saldo == 0:
                        deuda.estado = "Pagada"
                    else:
                        deuda.estado = "Pendiente"

                    deuda.save()

                messages.success(
                    request,
                    "Abono registrado correctamente."
                )

                return redirect("inicio")

    else:
        form = AbonoForm()

    return render(request, "registrar_abono.html", {"form": form,"deuda": deuda})


def detalle_deuda(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)

    abonos = deuda.abonos.all().order_by("-fecha")

    return render(request, "detalle_deuda.html", {"deuda": deuda,"abonos": abonos})


def editar_abono(request, abono_id):
    abono = get_object_or_404(Abono, id=abono_id)

    deuda = abono.deuda

    if request.method == "POST":
        form = AbonoForm(request.POST)

        if form.is_valid():
            nuevo_valor = form.cleaned_data["valor"]

            if nuevo_valor <= 0:
                form.add_error(
                    "valor",
                    "El valor del abono debe ser mayor que cero."
                )

            else:
                # Saldo que tendría la deuda si quitamos
                # temporalmente el abono anterior
                saldo_anterior = deuda.saldo + abono.valor

                if nuevo_valor > saldo_anterior:
                    form.add_error(
                        "valor",
                        "El nuevo valor no puede ser mayor que la deuda pendiente."
                    )

                else:
                    with transaction.atomic():
                        # Diferencia entre el nuevo y el anterior
                        diferencia = nuevo_valor - abono.valor

                        # Actualizar abono
                        abono.valor = nuevo_valor
                        abono.save()

                        # Actualizar saldo
                        deuda.saldo = deuda.saldo - diferencia

                        if deuda.saldo == 0:
                            deuda.estado = "Pagada"
                        else:
                            deuda.estado = "Pendiente"

                        deuda.save()

                    messages.success(
                        request,
                        "Abono actualizado correctamente."
                    )

                    return redirect("inicio")

    else:
        form = AbonoForm(instance=abono)

    return render(request, "editar_abono.html", {"form": form,"abono": abono})


def eliminar_abono(request, abono_id):
    abono = get_object_or_404(Abono, id=abono_id)

    deuda = abono.deuda

    if request.method == "POST":
        with transaction.atomic():
            deuda.saldo = deuda.saldo + abono.valor

            if deuda.saldo == 0:
                deuda.estado = "Pagada"
            else:
                deuda.estado = "Pendiente"

            deuda.save()

            abono.delete()

        messages.success(
            request,
            "Abono eliminado correctamente."
        )

        return redirect("inicio")

    return render(request, "eliminar_abono.html", {"abono": abono})


@login_required
def ventas_pendientes(request):
    deudas = Deuda.objects.filter(estado="Pendiente").select_related("cliente")

    return render(request, "ventas_pendientes.html", {"deudas": deudas})


@login_required
def detalle_pendiente(request, deuda_id):
    deuda = get_object_or_404(Deuda.objects.select_related("cliente"), id=deuda_id)

    abonos = deuda.abonos.all().order_by("-fecha")

    return render(request, "detalle_pendiente.html", {"deuda": deuda,"abonos": abonos})


@login_required
def marcar_pagada(request, deuda_id):
    deuda = get_object_or_404(Deuda, id=deuda_id)

    if request.method == "POST":
        deuda.saldo = 0
        deuda.estado = "Pagada"
        deuda.save()

        messages.success(request, "La venta fue marcada como pagada.")

        return redirect("ventas_pendientes")

    return redirect("detalle_pendiente", deuda_id=deuda.id)