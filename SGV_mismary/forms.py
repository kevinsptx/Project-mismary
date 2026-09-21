from django import forms

from .models import Venta


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "valor_total", "fecha"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }