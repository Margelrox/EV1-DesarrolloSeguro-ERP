from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import Role, User, UserRole


ROLE_DEFAULTS = {
    'Administrador': {'inventory': 2, 'can_change_prices': True, 'can_manage_roles': True},
    'Jefe de bodega': {'inventory': 2},
    'Operador de bodega': {'inventory': 1},
    'Vendedor': {'inventory': 1},
}
DEMO_USERS = {
    'demo_admin': 'Administrador',
    'demo_jefe': 'Jefe de bodega',
    'demo_operador': 'Operador de bodega',
    'demo_vendedor': 'Vendedor',
    'demo_sin_rol': None,
}


class Command(BaseCommand):
    help = 'Crea roles básicos y, opcionalmente, usuarios ficticios sin reemplazar datos existentes.'

    def add_arguments(self, parser):
        parser.add_argument('--usuarios-demo', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        for name, defaults in ROLE_DEFAULTS.items():
            role, created = Role.objects.get_or_create(role_name=name, defaults=defaults)
            state = 'creado' if created else 'existente, se conserva su configuración'
            self.stdout.write(f'{name}: {state}; inventario={role.inventory}, '
                              f'precios={role.can_change_prices}, roles={role.can_manage_roles}')

        if not options['usuarios_demo']:
            return
        password = getpass('Contraseña local para los usuarios demo nuevos: ')
        if password != getpass('Repite la contraseña: '):
            raise CommandError('Las contraseñas no coinciden.')
        try:
            for username in DEMO_USERS:
                validate_password(password, user=User(username=username))
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc

        for username, role_name in DEMO_USERS.items():
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'{username}: ya existe, no se modifica.')
                continue
            user = User.objects.create_user(
                username=username, password=password, is_staff=(username == 'demo_admin')
            )
            if role_name:
                UserRole.objects.create(user_id=user, role_id=role_name)
            self.stdout.write(self.style.SUCCESS(f'{username}: creado (superusuario=False).'))
