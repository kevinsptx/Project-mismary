
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404


User = get_user_model()


class UserLoginView(LoginView):
    template_name = 'login.html'


def es_superusuario(user):
    return user.is_authenticated and user.is_superuser


def solo_superusuario(view_func):
    return user_passes_test(es_superusuario, login_url='login')(view_func)



@solo_superusuario
def list_usuario(request):
    usuarios = User.objects.all().order_by('username')

    return render(request, 'list_user.html', {
        'usuarios': usuarios
    })




@login_required
@solo_superusuario
def register_usuario(request):
    grupos = Group.objects.all().order_by('name')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        grupo_id = request.POST.get('grupo_id', '').strip()

        if not all([username, first_name, last_name, email, password, grupo_id]):
            messages.error(request, 'Completa todos los campos y selecciona un rol.')
            return render(request, 'register_usuario.html', {'grupos': grupos})

        if User.objects.filter(username=username).exists():
            messages.error(request, f'El usuario "{username}" ya existe. Escribe otro nombre.')
            return render(request, 'register_usuario.html', {'grupos': grupos})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Ese correo ya está registrado.')
            return render(request, 'register_usuario.html', {'grupos': grupos})

        grupo = get_object_or_404(Group, id=grupo_id)

        usuario = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        usuario.groups.add(grupo)

        messages.success(request, f'Usuario creado y asignado al grupo {grupo.name}.')
        return redirect('list_user')

    return render(request, 'register_usuario.html', {'grupos': grupos})


@solo_superusuario
def usuario_update(request, id):
    usuario = get_object_or_404(User, id=id)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()

        if not username:
            messages.error(request, 'El nombre de usuario es obligatorio.')
            return redirect('user_update', id=usuario.id)

        if User.objects.filter(username=username).exclude(id=usuario.id).exists():
            messages.error(request, 'Ese nombre de usuario ya está registrado.')
            return redirect('user_update', id=usuario.id)

        usuario.username = username
        usuario.first_name = request.POST.get('first_name', '').strip()
        usuario.last_name = request.POST.get('last_name', '').strip()
        usuario.email = request.POST.get('email', '').strip()
        usuario.save()

        messages.success(request, 'Usuario actualizado correctamente.')
        return redirect('list_user')

    return render(request, 'user_update.html', {
        'usuario': usuario
    })


@solo_superusuario
def usuario_details(request, id):
    usuario = get_object_or_404(User, id=id)

    return render(request, 'user_details.html', {
        'usuario': usuario,
        'grupos': usuario.groups.all()
    })


@solo_superusuario
def usuario_delete(request, id):
    usuario = get_object_or_404(User, id=id)

    if usuario.is_superuser:
        messages.error(request, 'No puedes eliminar un superadministrador desde esta opción.')
        return redirect('list_user')

    if request.method == 'POST':
        usuario.delete()
        messages.success(request, 'Usuario eliminado correctamente.')

    return redirect('list_user')


# =========================
# GRUPOS
# =========================

@solo_superusuario
def list_grupos(request):
    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'crear':
            nombre = request.POST.get('nombre', '').strip()

            if not nombre:
                messages.error(request, 'Escribe el nombre del grupo.')
            elif Group.objects.filter(name__iexact=nombre).exists():
                messages.error(request, 'Ya existe un grupo con ese nombre.')
            else:
                grupo = Group.objects.create(name=nombre)
                messages.success(request, f'El grupo "{grupo.name}" fue creado.')
                return redirect('list_grupos')

        elif accion == 'crear_rol':
            nombre = request.POST.get('nombre', '').strip()

            if nombre not in ['Administrador', 'Usuario']:
                messages.error(request, 'Ese rol no es válido.')
            else:
                grupo, creado = Group.objects.get_or_create(name=nombre)

                if creado:
                    messages.success(request, f'Se creó el grupo {nombre}.')
                else:
                    messages.info(request, f'El grupo {nombre} ya existe.')

                return redirect('list_grupos')

    grupos = Group.objects.all().order_by('name')

    return render(request, 'grupos.html', {
        'grupos': grupos
    })


@solo_superusuario
def grupo_detalle(request, id):
    grupo = get_object_or_404(Group, id=id)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'agregar_usuario':
            user_id = request.POST.get('user_id')
            usuario = get_object_or_404(User, id=user_id)

            if usuario.is_superuser:
                messages.error(request, 'El superadministrador no necesita agregarse a un grupo.')
            else:
                grupo.user_set.add(usuario)
                messages.success(request, f'{usuario.username} fue agregado al grupo.')

            return redirect('grupo_detalle', id=grupo.id)

        elif accion == 'quitar_usuario':
            user_id = request.POST.get('user_id')
            usuario = get_object_or_404(User, id=user_id)

            if usuario.is_superuser:
                messages.error(request, 'No puedes quitar al superadministrador.')
            else:
                grupo.user_set.remove(usuario)
                messages.success(request, f'{usuario.username} fue retirado del grupo.')

            return redirect('grupo_detalle', id=grupo.id)

        elif accion == 'guardar_permisos':
            permisos_ids = request.POST.getlist('permisos')
            permisos = Permission.objects.filter(id__in=permisos_ids)
            grupo.permissions.set(permisos)

            messages.success(request, 'Los permisos del grupo fueron actualizados.')
            return redirect('grupo_detalle', id=grupo.id)

    busqueda = request.GET.get('q', '').strip()

    integrantes = grupo.user_set.all().order_by('username')
    disponibles = User.objects.filter(is_superuser=False).exclude(
        groups=grupo
    ).distinct().order_by('username')

    if busqueda:
        integrantes = integrantes.filter(
            Q(username__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda) |
            Q(email__icontains=busqueda)
        )

        disponibles = disponibles.filter(
            Q(username__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda) |
            Q(email__icontains=busqueda)
        )

    permisos = Permission.objects.select_related(
        'content_type'
    ).order_by('content_type__app_label', 'content_type__model', 'codename')

    permisos_asignados = set(
        grupo.permissions.values_list('id', flat=True)
    )

    return render(request, 'grupo_detalle.html', {
        'grupo': grupo,
        'integrantes': integrantes,
        'disponibles': disponibles,
        'busqueda': busqueda,
        'permisos': permisos,
        'permisos_asignados': permisos_asignados,
    })


@solo_superusuario
def eliminar_grupo(request, id):
    grupo = get_object_or_404(Group, id=id)

    if request.method == 'POST':
        if grupo.name == 'Superadministrador':
            messages.error(request, 'El superadministrador no se administra como grupo.')
        else:
            nombre = grupo.name
            grupo.delete()
            messages.success(request, f'El grupo "{nombre}" fue eliminado.')

    return redirect('list_grupos')
