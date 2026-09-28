from django import forms
from .models import Cliente, Categoria, Producto


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
