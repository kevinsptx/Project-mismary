from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render


from .forms import VentaForm


@staff_member_required
def registrar_venta(request):
    """HU-010: el administrador registra una venta por catálogo."""
    if request.method == "POST":
        form = VentaForm(request.POST)
        if form.is_valid():
            venta = form.save()
            messages.success(request, f"Venta #{venta.pk} registrada correctamente.")
            return redirect("registrar_venta")
    else:
        form = VentaForm()

    return render(request, "registrar_venta.html", {"form": form})  