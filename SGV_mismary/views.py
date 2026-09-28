from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction

from .models import Cliente, Deuda, Abono
from .forms import AbonoForm


# =========================================================
# INICIO
# =========================================================

def inicio(request):

    deudas = Deuda.objects.all()

    abonos = Abono.objects.select_related(
        "deuda__cliente"
    ).order_by("-fecha")


    # =====================================================
    # REGISTRAR ABONO
    # =====================================================

    if request.method == "POST":

        deuda_id = request.POST.get("deuda_id")

        deuda = get_object_or_404(
            Deuda,
            id=deuda_id
        )

        form = AbonoForm(request.POST)


        if form.is_valid():

            valor_abono = form.cleaned_data["valor"]


            # -------------------------------------------------
            # VALIDAR QUE EL ABONO SEA MAYOR QUE CERO
            # -------------------------------------------------

            if valor_abono <= 0:

                messages.error(
                    request,
                    "El valor del abono debe ser mayor que cero."
                )

                return redirect("inicio")


            # -------------------------------------------------
            # VALIDAR QUE NO SUPERE EL SALDO
            # -------------------------------------------------

            if valor_abono > deuda.saldo:

                messages.error(
                    request,
                    "El abono no puede ser mayor que el saldo pendiente."
                )

                return redirect("inicio")


            # -------------------------------------------------
            # GUARDAR ABONO Y ACTUALIZAR DEUDA
            # -------------------------------------------------

            with transaction.atomic():

                abono = form.save(commit=False)

                abono.deuda = deuda

                abono.save()


                # Descontar el abono del saldo

                deuda.saldo = deuda.saldo - valor_abono


                # -------------------------------------------------
                # CAMBIAR ESTADO
                # -------------------------------------------------

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


    # =========================================================
    # MOSTRAR INICIO
    # =========================================================

    return render(
        request,
        "inicio.html",
        {
            "deudas": deudas,
            "abonos": abonos
        }
    )


# =========================================================
# REGISTRAR ABONO
# =========================================================

def registrar_abono(request, deuda_id):

    deuda = get_object_or_404(
        Deuda,
        id=deuda_id
    )


    if request.method == "POST":

        form = AbonoForm(request.POST)


        if form.is_valid():

            valor_abono = form.cleaned_data["valor"]


            # -------------------------------------------------
            # VALIDAR VALOR
            # -------------------------------------------------

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


    return render(
        request,
        "registrar_abono.html",
        {
            "form": form,
            "deuda": deuda
        }
    )


# =========================================================
# DETALLE DE DEUDA
# =========================================================

def detalle_deuda(request, deuda_id):

    deuda = get_object_or_404(
        Deuda,
        id=deuda_id
    )


    abonos = deuda.abonos.all().order_by(
        "-fecha"
    )


    return render(
        request,
        "detalle_deuda.html",
        {
            "deuda": deuda,
            "abonos": abonos
        }
    )


# =========================================================
# EDITAR ABONO
# =========================================================

def editar_abono(request, abono_id):

    abono = get_object_or_404(
        Abono,
        id=abono_id
    )

    deuda = abono.deuda


    if request.method == "POST":

        form = AbonoForm(request.POST)


        if form.is_valid():

            nuevo_valor = form.cleaned_data["valor"]


            # -------------------------------------------------
            # VALIDAR QUE SEA MAYOR QUE CERO
            # -------------------------------------------------

            if nuevo_valor <= 0:

                form.add_error(
                    "valor",
                    "El valor del abono debe ser mayor que cero."
                )


            else:

                # Saldo que tendría la deuda si quitamos
                # temporalmente el abono anterior

                saldo_anterior = (
                    deuda.saldo + abono.valor
                )


                # -------------------------------------------------
                # VALIDAR NUEVO VALOR
                # -------------------------------------------------

                if nuevo_valor > saldo_anterior:

                    form.add_error(
                        "valor",
                        "El nuevo valor no puede ser mayor que la deuda pendiente."
                    )


                else:

                    with transaction.atomic():

                        # Diferencia entre el nuevo y el anterior

                        diferencia = (
                            nuevo_valor - abono.valor
                        )


                        # Actualizar abono

                        abono.valor = nuevo_valor

                        abono.save()


                        # Actualizar saldo

                        deuda.saldo = (
                            deuda.saldo - diferencia
                        )


                        # -------------------------------------------------
                        # ACTUALIZAR ESTADO
                        # -------------------------------------------------

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

        form = AbonoForm(
            instance=abono
        )


    return render(
        request,
        "editar_abono.html",
        {
            "form": form,
            "abono": abono
        }
    )


# =========================================================
# ELIMINAR ABONO
# =========================================================

def eliminar_abono(request, abono_id):

    abono = get_object_or_404(
        Abono,
        id=abono_id
    )

    deuda = abono.deuda


    if request.method == "POST":

        with transaction.atomic():

            # -------------------------------------------------
            # DEVOLVER EL VALOR DEL ABONO AL SALDO
            # -------------------------------------------------

            deuda.saldo = (
                deuda.saldo + abono.valor
            )


            # -------------------------------------------------
            # ACTUALIZAR ESTADO
            # -------------------------------------------------

            if deuda.saldo == 0:

                deuda.estado = "Pagada"

            else:

                deuda.estado = "Pendiente"


            deuda.save()


            # -------------------------------------------------
            # ELIMINAR ABONO
            # -------------------------------------------------

            abono.delete()


        messages.success(
            request,
            "Abono eliminado correctamente."
        )


        return redirect("inicio")


    return render(
        request,
        "eliminar_abono.html",
        {
            "abono": abono
        }
    )