from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


class UserLoginView(LoginView):
    template_name = 'login.html'


@login_required
def home(request):
    return render(request, 'home.html')


