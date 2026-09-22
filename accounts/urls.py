from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import UserLoginView, home


urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),

    path('logout/', LogoutView.as_view(), name='logout'),

    path('', home, name='home'),
]
