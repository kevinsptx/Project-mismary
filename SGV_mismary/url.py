from django.urls import path
from . import views

urlpatterns = [
    path('',views.home, name='home'),
    path('register_cliente/', views.register_cliente, name='register_cliente'),
    path('list_cliente/', views.list_cliente, name='list_cliente'),
    path('details_cliente/<int:id>', views.cliente_details, name='details_cliente'),
    path('cliente_update/<int:id>',views.cliente_update,name='cliente_update'),
    path('cliente_delete/<int:id>',views.cliente_delete,name='cliente_delete')
]