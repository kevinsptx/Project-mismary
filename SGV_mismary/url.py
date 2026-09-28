from django.urls import path
from . import views

urlpatterns = [

    path(
        "",
        views.inicio,
        name="inicio"
    ),

    path(
        "deuda/<int:deuda_id>/abono/",
        views.registrar_abono,
        name="registrar_abono"
    ),

    path(
        "deuda/<int:deuda_id>/",
        views.detalle_deuda,
        name="detalle_deuda"
    ),

    path(
        "abono/<int:abono_id>/editar/",
        views.editar_abono,
        name="editar_abono"
    ),

    path(
    "abono/<int:abono_id>/eliminar/",
    views.eliminar_abono,
    name="eliminar_abono"
),

]