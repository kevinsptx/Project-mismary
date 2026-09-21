from django.urls import path

from . import views

urlpatterns = [
    path("ventas/registrar/", views.registrar_venta, name="registrar_venta"),
]