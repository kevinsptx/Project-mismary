"""
Arregla los roles "Administrador" y "Usuario" y muestra a quién le falta algo.

    Administrador -> todos los permisos del negocio.
    Usuario       -> solo VER y REGISTRAR (view_ y add_). Nunca editar ni eliminar.

Uso:
    python manage.py arreglar_roles
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.views import crear_roles_base, obtener_app_negocio


class Command(BaseCommand):
    help = 'Deja los roles Administrador y Usuario con sus permisos correctos.'

    def handle(self, *args, **opciones):
        crear_roles_base(forzar=True)
        app = obtener_app_negocio()
        User = get_user_model()

        self.stdout.write(self.style.SUCCESS('Roles arreglados.\n'))
        self.stdout.write('Usuarios y sus roles:')

        for u in User.objects.order_by('username'):
            if u.is_superuser:
                self.stdout.write(f'  {u.username:<18} SUPERUSUARIO (puede todo)')
                continue

            grupos = ', '.join(g.name for g in u.groups.all()) or '-- SIN ROL --'
            permisos = len([p for p in u.get_all_permissions() if p.startswith(app.label + '.')])
            self.stdout.write(f'  {u.username:<18} rol: {grupos:<16} permisos: {permisos}')

            if not u.groups.exists():
                self.stdout.write(self.style.WARNING(
                    f'    -> {u.username} no tiene rol: por eso ve error 403. '
                    f'Asígnale uno en Usuarios > Editar.'
                ))