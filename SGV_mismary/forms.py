from django import forms
from .models import Cliente, Categoria, Producto, Abono, Gasto
from django import forms
from .models import Cliente
import re


def capitalizar_nombre(texto):
    if not texto:
        return texto

    texto = re.sub(r'\s+', ' ', texto.strip()).lower()

    return re.sub(
        r'(^|\s)([a-záéíóúüñ])',
        lambda m: m.group(1) + m.group(2).upper(),
        texto
    )


class ClienteForm(forms.ModelForm):

    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono', 'direccion']

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre']
        return capitalizar_nombre(nombre)



# ===== FORMATO DE NOMBRES PROPIOS =====

def formato_nombre(valor):
    if not valor:
        return valor

    return ' '.join(valor.strip().split()).title()


# ===== FORMULARIO DE CLIENTES =====

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['nombre', 'telefono', 'direccion']

        labels = {
            'nombre': 'Nombre',
            'telefono': 'Teléfono',
            'direccion': 'Dirección',
        }

        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre del cliente'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el teléfono'
            }),
            'direccion': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese la dirección'
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '')
        return formato_nombre(nombre)


# ===== FORMULARIO DE CATEGORÍAS =====

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']

        labels = {
            'nombre': 'Nombre de la categoría',
        }

        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Labiales, Perfumes, Maquillaje'
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '')
        return formato_nombre(nombre)


# ===== FORMULARIO DE PRODUCTOS =====

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto

        # Datos del producto
        fields = [
            'nombre',
            'precio_venta',
            'cantidad_disponible',
            'categoria'
        ]

        labels = {
            'nombre': 'Nombre del producto',
            'precio_venta': 'Precio de venta',
            'cantidad_disponible': 'Cantidad disponible',
            'categoria': 'Categoría',
        }

        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Labial Mate Rojo'
            }),

            'precio_venta': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 35000',
                'min': '0.01',
                'step': '0.01'
            }),

            'cantidad_disponible': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: 20',
                'min': '0',
                'step': '1'
            }),

            'categoria': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '')
        return formato_nombre(nombre)

    def clean_precio_venta(self):
        precio = self.cleaned_data.get('precio_venta')

        if precio is None:
            raise forms.ValidationError(
                'El precio de venta es obligatorio.'
            )

        if precio <= 0:
            raise forms.ValidationError(
                'El precio de venta debe ser mayor que cero.'
            )

        return precio

    def clean_cantidad_disponible(self):
        cantidad = self.cleaned_data.get('cantidad_disponible')

        if cantidad is None:
            raise forms.ValidationError(
                'La cantidad disponible es obligatoria.'
            )

        if cantidad < 0:
            raise forms.ValidationError(
                'La cantidad disponible no puede ser negativa.'
            )

        return cantidad


# ===== FORMULARIO DE ABONOS =====


class AbonoForm(forms.ModelForm):
    class Meta:
        model = Abono
        fields = ["valor", "forma_pago"]

        widgets = {
            "valor": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ingrese el valor del abono",
                    "min": "1",
                    "step": "0.01"
                }
            ),
            "forma_pago": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),
        }

        labels = {
            "valor": "Valor del abono",
            "forma_pago": "Forma de pago",
        }



class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ["descripcion", "valor", "fecha"]

        labels = {
            "descripcion": "Titulo del gasto",
            "valor": "Valor del gasto",
            "fecha": "Fecha del gasto",
        }

        widgets = {
            "descripcion": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Compra de materiales",
            }),
            "valor": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese el valor",
                "min": "1",
                "step": "1",
            }),
            "fecha": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
        }

    def clean_valor(self):
        valor = self.cleaned_data["valor"]

        if valor <= 0:
            raise forms.ValidationError(
                "El valor del gasto debe ser mayor que cero."
            )

        return valor
