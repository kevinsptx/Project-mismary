from django.contrib import admin
from .models import Cliente, Deuda, Abono


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "nombre",
        "telefono"
    )


@admin.register(Deuda)
class DeudaAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "cliente",
        "valor_total",
        "saldo"
    )


@admin.register(Abono)
class AbonoAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "deuda",
        "valor",
        "fecha"
    )