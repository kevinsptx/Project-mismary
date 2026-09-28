from django import forms
from .models import Abono


class AbonoForm(forms.ModelForm):

    class Meta:
        model = Abono
        fields = ["valor"]

        widgets = {
            "valor": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingrese el valor del abono",
                    "min": "1",
                    "step": "0.01"
                }
            )
        }

        labels = {
            "valor": "Valor del abono"
        }