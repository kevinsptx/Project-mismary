from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register_cliente/', views.register_cliente, name='register_cliente'),
    path('list_cliente/', views.list_cliente, name='list_cliente'),
    path('details_cliente/<int:id>', views.cliente_details, name='details_cliente'),
    path('cliente_update/<int:id>', views.cliente_update, name='cliente_update'),
    path('cliente_delete/<int:id>', views.cliente_delete, name='cliente_delete'),
    path('register_producto/', views.register_producto, name='register_producto'),
    path('list_producto/', views.list_producto, name='list_producto'),
    path('productos/<int:id>/editar/', views.producto_update, name='producto_update'),
    path('productos/<int:id>/eliminar/', views.producto_delete, name='producto_delete'),
    path('productos_mas_vendidos/', views.productos_mas_vendidos, name='productos_mas_vendidos'),
]
