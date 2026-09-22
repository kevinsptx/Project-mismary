from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import UserLoginView
from . import views


urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('usuarios/', views.list_usuario, name='list_user'),
    path('usuarios/crear/', views.register_usuario, name='register_user'),
    path('usuarios/editar/<int:id>/', views.usuario_update, name='user_update'),
    path('usuarios/eliminar/<int:id>/', views.usuario_delete, name='user_delete'),
    path('usuarios/detalle/<int:id>/', views.usuario_details, name='user_details'),
]
