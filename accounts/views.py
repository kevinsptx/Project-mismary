from functools import wraps

from django.apps import apps
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

User = get_user_model()


class UserLoginView(LoginView):
    template_name = 'login.html'


def solo_superusuario(vista):
    @wraps(vista)
    @login_required(login_url='login')
    def envoltura(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return envoltura


def obtener_app_negocio():
    for config in apps.get_app_configs():
        if config.name.lower().endswith('sgv_mismary'):
            return config
    return None


def obtener_permisos_negocio():
    app = obtener_app_negocio()
    if app is None:
        return Permission.objects.none()
    return Permission.objects.filter(
        content_type__app_label=app.label
    ).select_related('content_type').order_by('content_type__model', 'codename')


def crear_roles_base(forzar=False):

    app = obtener_app_negocio()
    if app is None:
        return

    permisos = obtener_permisos_negocio()
    permisos_usuario = permisos.filter(
        Q(codename__startswith='view_') |
        Q(codename__startswith='add_')
    )

    for nombre, permisos_base in (
        ('Administrador', permisos),
        ('Usuario', permisos_usuario),
    ):
        grupo, _ = Group.objects.get_or_create(name=nombre)
        permisos_actuales = grupo.permissions.filter(
            content_type__app_label=app.label
        )

        if forzar:
            # Agrega lo que falte
            grupo.permissions.add(*permisos_base)

            # "Usuario" nunca debe poder editar ni eliminar
            if nombre == 'Usuario':
                grupo.permissions.remove(*permisos_actuales.exclude(
                    id__in=permisos_base.values_list('id', flat=True)
                ))
        elif not permisos_actuales.exists():
            grupo.permissions.add(*permisos_base)


def permisos_del_grupo(grupo, app):
    if app is None:
        return set()
    return set(grupo.permissions.filter(
        content_type__app_label=app.label
    ).values_list('id', flat=True))


@solo_superusuario
def list_usuario(request):
    usuarios = User.objects.filter(is_superuser=False).order_by('username')
    return render(request, 'list_user.html', {'usuarios': usuarios})


@solo_superusuario
def register_usuario(request):
    crear_roles_base()
    grupos = Group.objects.exclude(name__iexact='Superadministrador').order_by('name')

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

        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'Ese nombre de usuario ya está registrado.')
            return render(request, 'register_usuario.html', {'grupos': grupos})

        if User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Ese correo ya está registrado.')
            return render(request, 'register_usuario.html', {'grupos': grupos})

        grupo = get_object_or_404(
            Group.objects.exclude(name__iexact='Superadministrador'),
            id=grupo_id
        )
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
    usuario = get_object_or_404(User, id=id, is_superuser=False)
    crear_roles_base()
    grupos = Group.objects.exclude(name__iexact='Superadministrador').order_by('name')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        grupo_id = request.POST.get('grupo_id', '').strip()

        if not username or not email or not grupo_id:
            messages.error(request, 'El usuario, correo y rol son obligatorios.')
            return render(request, 'user_update.html', {'usuario': usuario, 'grupos': grupos})

        if User.objects.filter(username__iexact=username).exclude(id=usuario.id).exists():
            messages.error(request, 'Ese nombre de usuario ya está registrado.')
            return render(request, 'user_update.html', {'usuario': usuario, 'grupos': grupos})

        if User.objects.filter(email__iexact=email).exclude(id=usuario.id).exists():
            messages.error(request, 'Ese correo ya está registrado.')
            return render(request, 'user_update.html', {'usuario': usuario, 'grupos': grupos})

        grupo = get_object_or_404(
            Group.objects.exclude(name__iexact='Superadministrador'),
            id=grupo_id
        )
        usuario.username = username
        usuario.first_name = request.POST.get('first_name', '').strip()
        usuario.last_name = request.POST.get('last_name', '').strip()
        usuario.email = email
        usuario.save()
        usuario.groups.set([grupo])
        messages.success(request, 'Usuario y rol actualizados correctamente.')
        return redirect('list_user')

    return render(request, 'user_update.html', {
        'usuario': usuario,
        'grupos': grupos,
        'grupo_actual': usuario.groups.first()
    })


@solo_superusuario
def usuario_details(request, id):
    usuario = get_object_or_404(User, id=id)
    return render(request, 'user_details.html', {
        'usuario': usuario,
        'grupos': usuario.groups.all()
    })


@solo_superusuario
@require_POST
def usuario_delete(request, id):
    usuario = get_object_or_404(User, id=id)
    if usuario.is_superuser or usuario.id == request.user.id:
        messages.error(request, 'No puedes eliminar una cuenta de superadministrador ni tu propia cuenta.')
    else:
        usuario.delete()
        messages.success(request, 'Usuario eliminado correctamente.')
    return redirect('list_user')


@solo_superusuario
def list_grupos(request):
    crear_roles_base()

    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if not nombre:
            messages.error(request, 'Escribe el nombre del grupo.')
        elif nombre.lower() == 'superadministrador':
            messages.error(request, 'Ese nombre está reservado para la cuenta principal.')
        elif Group.objects.filter(name__iexact=nombre).exists():
            messages.error(request, 'Ese grupo ya existe.')
        else:
            Group.objects.create(name=nombre)
            messages.success(request, f'El grupo "{nombre}" fue creado.')
            return redirect('list_grupos')

    grupos = Group.objects.all().order_by('name')
    return render(request, 'grupos.html', {'grupos': grupos})


@solo_superusuario
def grupo_details(request, grupo_id):
    grupo = get_object_or_404(Group, id=grupo_id)
    if grupo.name.lower() == 'superadministrador':
        raise PermissionDenied

    app = obtener_app_negocio()
    permisos = obtener_permisos_negocio()

    if request.method == 'POST':
        ids = request.POST.getlist('permisos')
        seleccionados = permisos.filter(id__in=ids)
        permisos_de_otros_modulos = grupo.permissions.exclude(
            content_type__app_label=app.label if app else ''
        )
        grupo.permissions.set(list(permisos_de_otros_modulos) + list(seleccionados))
        messages.success(request, f'Permisos del grupo "{grupo.name}" actualizados.')
        return redirect('grupo_details', grupo_id=grupo.id)

    return render(request, 'grupo_details.html', {
        'grupo': grupo,
        'permisos': permisos,
        'permisos_asignados': permisos_del_grupo(grupo, app)
    })


@solo_superusuario
@require_POST
def grupo_delete(request, grupo_id):
    grupo = get_object_or_404(Group, id=grupo_id)
    if grupo.name in ['Administrador', 'Usuario', 'Superadministrador']:
        messages.error(request, 'No puedes eliminar los roles principales.')
    else:
        grupo.delete()
        messages.success(request, f'El grupo "{grupo.name}" fue eliminado.')
    return redirect('list_grupos')


def buscar_usuarios(usuarios, texto):
    if not texto:
        return usuarios
    return usuarios.filter(
        Q(username__icontains=texto) |
        Q(first_name__icontains=texto) |
        Q(last_name__icontains=texto) |
        Q(email__icontains=texto)
    )
