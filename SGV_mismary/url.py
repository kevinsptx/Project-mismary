from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('register_cliente/', views.register_cliente, name='register_cliente'),
    path('list_cliente/', views.list_cliente, name='list_cliente'),
    path('details_cliente/<int:id>', views.cliente_details, name='details_cliente'),
    path('cliente_update/<int:id>', views.cliente_update, name='cliente_update'),
    path('cliente_delete/<int:id>', views.cliente_delete, name='cliente_delete'),
<<<<<<< HEAD
    path('register_producto/', views.register_producto, name='register_producto'),
    path('list_producto/', views.list_producto, name='list_producto'),
    path('productos/<int:id>/editar/', views.producto_update, name='producto_update'),
    path('productos/<int:id>/eliminar/', views.producto_delete, name='producto_delete'),
    path('productos_mas_vendidos/', views.productos_mas_vendidos, name='productos_mas_vendidos'),
]
=======
    path('register_venta/', views.register_venta, name='register_venta'),
    path('ventas/', views.list_venta, name='list_venta'),
    path('details_venta/<int:id>', views.venta_details, name='details_venta'),
    path('venta_update/<int:id>', views.venta_update, name='venta_update'),
    path('venta_delete/<int:id>', views.venta_delete, name='venta_delete'),
    path("inicio_abono/", views.inicio, name="inicio"),
    path("deuda/<int:deuda_id>/abono/", views.registrar_abono, name="registrar_abono"),
    path("deuda/<int:deuda_id>/", views.detalle_deuda, name="detalle_deuda"),
    path("abono/<int:abono_id>/editar/", views.editar_abono, name="editar_abono"),
    path("abono/<int:abono_id>/eliminar/", views.eliminar_abono, name="eliminar_abono"),
    path('ventas/pendientes/', views.ventas_pendientes, name='ventas_pendientes'),
    path('ventas/pendientes/<int:deuda_id>/', views.detalle_pendiente, name='detalle_pendiente'),
    path('ventas/pendientes/<int:deuda_id>/pagar/', views.marcar_pagada, name='marcar_pagada'),
]
>>>>>>> revision
