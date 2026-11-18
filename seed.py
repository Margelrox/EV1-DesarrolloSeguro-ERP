#!/usr/bin/env python3
"""Seed de roles y usuarios de la aplicación ERP.

Crea los cuatro roles que define la aplicación (ver
``users/management/commands/preparar_rbac.py``) y una cuenta de acceso por rol
con la contraseña indicada (por defecto ``123456``).

Uso:
    python3 seed.py                 # roles + usuarios con clave 123456
    python3 seed.py --solo-roles    # crea/actualiza únicamente los roles
    SEED_PASSWORD=otra clave python3 seed.py

Es idempotente: puede ejecutarse varias veces. Los roles se actualizan a la
definición de la aplicación y las cuentas recuperan la contraseña del seed.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sitio.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from users.models import Role, User, UserRole  # noqa: E402

DEFAULT_PASSWORD = "123456"

# Permisos por rol tal como los establece la aplicación.
# Campos de módulo: 0 = No access, 1 = View only, 2 = Create and modify.
ROLES = {
    "Administrador": {
        "inventory": 2,
        "can_change_prices": True,
        "can_manage_roles": True,
        "can_manage_warehouses": True,
        "can_register_movements": True,
    },
    "Jefe de bodega": {
        "inventory": 2,
        "can_register_movements": True,
    },
    "Operador de bodega": {
        "inventory": 1,
        "can_register_movements": True,
    },
    "Vendedor": {
        "inventory": 1,
    },
}

# Una cuenta por rol. El nombre sigue el prefijo demo_ que usa la app para
# publicar las pistas de acceso en el login (users/permissions.py).
USERS = {
    "demo_admin": {"role": "Administrador", "is_staff": True},
    "demo_jefe": {"role": "Jefe de bodega", "is_staff": False},
    "demo_operador": {"role": "Operador de bodega", "is_staff": False},
    "demo_vendedor": {"role": "Vendedor", "is_staff": False},
    "demo_sin_rol": {"role": None, "is_staff": False},
}


def seed_roles():
    """Inserta o actualiza los roles con sus permisos por defecto."""
    created, updated = 0, 0
    for name, defaults in ROLES.items():
        role, was_created = Role.objects.update_or_create(
            role_name=name, defaults=defaults
        )
        created += was_created
        updated += not was_created
        print(
            f"  [rol] {role.role_name:<18} inventario={role.inventory} "
            f"precios={int(role.can_change_prices)} "
            f"roles={int(role.can_manage_roles)} "
            f"bodegas={int(role.can_manage_warehouses)} "
            f"movimientos={int(role.can_register_movements)}"
        )
    return created, updated


def seed_users(password):
    """Crea/actualiza las cuentas demo y les asigna su rol."""
    created, updated = 0, 0
    for username, data in USERS.items():
        user, was_created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": data["is_staff"], "is_active": True},
        )
        if was_created:
            created += 1
        else:
            updated += 1
            user.is_staff = data["is_staff"]
            user.is_active = True

        user.set_password(password)
        user.save()

        if data["role"]:
            UserRole.objects.get_or_create(user_id=user, role_id=data["role"])
        else:
            UserRole.objects.filter(user_id=user).delete()
        print(f"  [usuario] {username:<15} rol={data['role'] or 'sin rol'}")
    return created, updated


def main():
    if not Role._meta.db_table:  # pragma: no cover - salvaguarda
        raise SystemExit("El modelo Role no está disponible.")

    password = os.environ.get("SEED_PASSWORD", DEFAULT_PASSWORD)
    solo_roles = "--solo-roles" in sys.argv[1:]

    print("Sembrando roles de la aplicación...")
    with transaction.atomic():
        r_created, r_updated = seed_roles()

        if solo_roles:
            print(f"\nRoles: {r_created} creados, {r_updated} actualizados.")
            return

        print(f"\nSembrando usuarios (contraseña: {'*' * len(password)})...")
        u_created, u_updated = seed_users(password)

    print(
        f"\nListo. Roles: {r_created} creados, {r_updated} actualizados. "
        f"Usuarios: {u_created} creados, {u_updated} actualizados."
    )
    print("Cuentas disponibles: " + ", ".join(USERS))
    print(f"Contraseña de todas las cuentas: {password}")


if __name__ == "__main__":
    main()
