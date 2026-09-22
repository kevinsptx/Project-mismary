from django import forms
from .models import Abono


class AbonoForm(forms.ModelForm):

    class Meta:
        model = Abono
        fields = ['valor']

        widgets = {
            'valor': forms.NumberInput(
                attrs={
                    'placeholder': 'Ingrese el valor del abono',
                    'min': '0.01',
                    'step': '0.01'
                }
            )
        }
