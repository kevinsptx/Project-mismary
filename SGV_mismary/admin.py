from django.contrib import admin
from .models import (
    Cliente,
    Categoria,
    Producto,
    Venta,
    DetalleVenta,
    Deuda,
    Abono,
    Gasto
)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nombre",
        "telefono"
    )


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nombre"
    )


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nombre",
        "precio_venta",
        "cantidad_disponible",
        "categoria"
    )


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "cliente",
        "valor_total",
        "fecha"
    )


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "venta",
        "producto",
        "cantidad",
        "precio"
    )


@admin.register(Deuda)
class DeudaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "cliente",
        "valor_total",
        "saldo",
        "estado"
    )


@admin.register(Abono)
class AbonoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "deuda",
        "valor",
        "fecha"
    )


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "descripcion",
        "valor",
        "fecha"
    )