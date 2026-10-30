# Usuarios de prueba — Inventario

Contraseña común: `ClaveDS!`

| Usuario | Rol | Acceso |
|---|---|---|
| demo_admin | Administrador | Crear y editar productos, cambiar precios y asignar roles |
| demo_jefe | Jefe de bodega | Consultar, crear y editar fichas; sin cambiar precios |
| demo_operador | Operador de bodega | Solo consultar |
| demo_vendedor | Vendedor | Solo consultar |
| demo_sin_rol | Sin rol | Sin acceso al inventario |

Login: http://127.0.0.1:8000/inicio/login

## Estado verificado

Las cinco cuentas existen en la base local (`db.sqlite3`), no son superusuario y
tienen la contraseña de arriba. Solo `demo_admin` tiene `is_staff` para entrar a
Django Admin y gestionar `UserRole`.

Comprobado contra la base local (Django 5.2.17, rama `DSE-65-rbac-basico`):

| Usuario | `login` | `GET /inventario/productos/` | `GET /inventario/productos/crear/` |
|---|---|---|---|
| demo_admin | OK | 200 | 200 |
| demo_jefe | OK | 200 | 200 |
| demo_operador | OK | 200 | 403 |
| demo_vendedor | OK | 200 | 403 |
| demo_sin_rol | OK | 403 | 403 |

`demo_jefe` recibe 403 en `/inventario/productos/<codigo>/precio/` porque su rol
tiene `can_change_prices = False`; `demo_admin` sí puede cambiar precios.

## Si hay que volver a fijar la clave

La clave no se recibe por argumento de línea de comandos (evita dejarla en el
historial del shell). Desde la raíz del repo, con el entorno virtual activo:

```bash
python manage.py shell -c "
import getpass
from django.contrib.auth.password_validation import validate_password
from users.models import User
DEMO = ['demo_admin','demo_jefe','demo_operador','demo_vendedor','demo_sin_rol']
p = getpass.getpass('Nueva clave local: ')
if p != getpass.getpass('Repite la clave: '):
    raise SystemExit('no coinciden')
for u in User.objects.filter(username__in=DEMO):
    validate_password(p, user=u)
for u in User.objects.filter(username__in=DEMO):
    u.set_password(p); u.save(update_fields=['password']); print(u.username, 'actualizado')
"
```

Si las cuentas no existieran todavía, se crean con roles incluidos:

```bash
python manage.py preparar_rbac --usuarios-demo
```

Ese comando no modifica cuentas ni roles que ya existen: si cambias la clave con
el bloque anterior, `preparar_rbac` no la sobrescribe.

## Alcance

Este archivo es para la instancia local de desarrollo/demostración. No reutilices
esta clave en otros entornos ni la incluyas en capturas, informes publicados o
despliegues; ver la advertencia de `docs/RBAC.md`.
