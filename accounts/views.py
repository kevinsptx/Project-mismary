from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required,user_passes_test
from django.shortcuts import render,redirect,get_object_or_404
from django.contrib.auth.models import User


class UserLoginView(LoginView):
    template_name = 'login.html'




def es_superusuario(user):
    return user.is_superuser

@user_passes_test(es_superusuario)
def list_usuario(request):
    usuarios = User.objects.all()

    return render(request, 'list_user.html', {
        'usuarios': usuarios
    })


@user_passes_test(es_superusuario)
def register_usuario(request):
    if request.method == 'POST':
        username = request.POST['username']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        password = request.POST['password']

        User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        return redirect('list_user')

    return render(request, 'register_user.html')


@user_passes_test(es_superusuario)
def usuario_update(request, id):
    usuario = get_object_or_404(User, id=id)

    if request.method == 'POST':
        usuario.username = request.POST['username']
        usuario.first_name = request.POST['first_name']
        usuario.last_name = request.POST['last_name']
        usuario.email = request.POST['email']
        usuario.save()

        return redirect('list_user')

    return render(request, 'user_update.html', {
        'usuario': usuario
    })

@user_passes_test(es_superusuario)
def usuario_details(request, id):
    usuario = get_object_or_404(User, id=id)

    return render(request, 'user_details.html', {
        'usuario': usuario
    })

@user_passes_test(es_superusuario)
def usuario_delete(request, id):
    usuario = get_object_or_404(User, id=id)
    usuario.delete()

    return redirect('list_user')
