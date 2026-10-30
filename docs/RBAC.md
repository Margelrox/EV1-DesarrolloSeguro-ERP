# RBAC básico · DSE-59 / DSE-65 / DSE-66

## Base y alcance

Se conserva el trabajo de Juan: User, Role, UserRole, autenticación, dashboard,
niveles de acceso por módulo (0: sin acceso, 1: lectura, 2: crear/modificar)
y el modelo Product. La base de esta rama es main en el commit 2079531 (PR #5).

El repositorio contiene la estructura de roles, pero no la base de datos local
de Juan ni un listado de sus asignaciones. Por eso no se puede afirmar desde
Git qué roles o usuarios tiene creados en su equipo.

Se añaden dos permisos booleanos a Role, inicialmente desactivados:
can_change_prices y can_manage_roles. No se reemplazan roles existentes.
El nombre del rol es descriptivo: el servidor decide con sus permisos guardados,
no con un nombre enviado en el formulario ni con el nombre de usuario.

## Matriz básica preparada por el comando

| Acción | Administrador | Jefe de bodega | Operador de bodega | Vendedor | Sin rol |
|---|---|---|---|---|---|
| Consultar productos, precio y stock | Sí | Sí | Sí | Sí | No |
| Crear ficha de producto | Sí | Sí | No | No | No |
| Editar ficha general | Sí | Sí | No | No | No |
| Consultar bodegas activas, existencias y movimientos | Sí | Sí | Sí | Sí | No |
| Crear, editar y desactivar bodegas; consultar auditoría | Sí | No | No | No | No |
| Registrar entradas y salidas | Sí | Sí | Sí | No | No |
| Cambiar precios | Sí | No | No | No | No |
| Asignar/retirar roles desde Django Admin | Sí, con is_staff | No | No | No | No |
| Editar usuarios, definir permisos de Role o editar Group | Solo superusuario de preparación | No | No | No | No |

El producto se crea con precio 0 y stock 0. El administrador configura el precio
en una operación separada; la ficha general nunca modifica precio ni stock.
El código solo se define al crear. La ampliación DSE-35/36/37 añade bodegas y
movimientos; consulta [INVENTARIO.md](INVENTARIO.md). No hay eliminación de
productos ni edición directa del stock.

## Descargar y ejecutar

Desde tu copia del repositorio, guarda primero cualquier cambio local pendiente.
Después, cuando esta rama esté publicada:

```bash
git fetch origin
git switch --track origin/DSE-65-rbac-basico
```

Si ya tienes esa rama local:

```bash
git switch DSE-65-rbac-basico
git pull --ff-only origin DSE-65-rbac-basico
```

Activa tu entorno virtual existente. Si aún no tienes uno:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Luego:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py preparar_rbac --usuarios-demo
python manage.py runserver
```

El comando pide una contraseña local y su confirmación; no la muestra ni la
almacena en Git. Aplica las validaciones de contraseñas de Django. Las cuentas
nuevas son demo_admin, demo_jefe, demo_operador, demo_vendedor y demo_sin_rol.
Todas son cuentas normales: ninguna es superusuario. Solo demo_admin tiene
is_staff para acceder al administrador de Django y gestionar UserRole.

IMPORTANTE: si un rol o usuario ya existe, el comando conserva su configuración,
contraseña y asignaciones. Lee los mensajes del comando. Si los roles de Juan
tienen otros permisos, usa un superusuario de preparación para revisarlos en
/admin/users/role/ y comparar con la matriz. No supongas que se sobrescribieron.

Para crear ese superusuario, si no tienes uno:

```bash
python manage.py createsuperuser
```

El superusuario administra las cuentas y las definiciones de roles. Para las
pruebas funcionales utiliza las cuentas normales; en inventario, incluso un
superusuario necesita un Role asignado. Se usan los permisos de Role/UserRole,
no los permisos nativos Group/Permission, para autorizar inventario.

Abre http://127.0.0.1:8000/inicio/login/ e inicia sesión.
Desde el dashboard puedes acceder a Productos; demo_admin también ve Asignar roles.
La entrada a Django Admin exige además is_staff: una cuenta común recibe una
redirección al login del admin, mientras un staff sin permiso recibe 403.

## Rutas implementadas

| Ruta | Método | Permiso |
|---|---|---|
| /inventario/productos/ | GET | inventory >= 1 |
| /inventario/productos/crear/ | GET, POST | inventory >= 2 |
| /inventario/productos/<codigo>/editar/ | GET, POST | inventory >= 2 |
| /inventario/productos/<codigo>/precio/ | GET, POST | Un rol con inventory >= 2 y can_change_prices |
| /admin/users/userrole/ y sus operaciones | GET, POST según Django Admin | is_staff y can_manage_roles; o superusuario |

Los niveles de varios roles se combinan tomando el máximo, conservando el
comportamiento de Juan. Los permisos se consultan de nuevo en cada petición:
retirar un rol o su permiso afecta la siguiente petición sin cerrar sesión.
Un usuario autenticado sin permiso recibe 403 en las rutas de inventario.
Sin sesión se exige login. Ocultar botones es solo una ayuda visual.

## Pruebas automatizadas

```bash
python manage.py test users inventario -v 2
python manage.py check
python manage.py makemigrations --check --dry-run
```

Se cubren: matriz GET de cinco perfiles; creación/edición y cambio de precios;
POST rechazados sin cambios en BD; intento de enviar precio en la ficha general;
stock, código y rol enviados como campos extra sin adquirir privilegios;
revocación en la siguiente petición; POST con CSRF válido; gestión de roles por
un administrador normal; bloqueo de autoasignación y elevación a superusuario;
comando repetible que conserva datos existentes.

## Capturas para E02/E12 e informe

1. Inicia con demo_jefe. Inserta una captura de Productos donde se vean usuario,
   rol y botón Crear producto, sin botón Cambiar precio. Crea un producto de prueba.
2. Entra con demo_vendedor. Inserta una captura del listado sin botones de escritura.
3. Con demo_vendedor abre directamente /inventario/productos/crear/.
   Inserta una captura de la URL y del mensaje 403 Acceso denegado.
4. Con demo_jefe abre /inventario/productos/CODIGO/precio/. Reemplaza CODIGO
   por el código de un producto existente.
   Inserta una captura de la URL y del rechazo 403.
5. Con demo_admin cambia el precio desde el enlace autorizado. Inserta el listado
   con el nuevo precio y la identificación de la cuenta; no uses superusuario.
6. Con demo_admin entra en Asignar roles, asigna Vendedor a demo_sin_rol y prueba
   su acceso en otra sesión. Retira la asignación y prueba otra petición:
   inventario debe responder 403. Captura asignación/retiro y resultado.
7. Ejecuta los tests del bloque anterior e inserta una captura de la terminal
   donde se vean los casos ejecutados, cantidad de tests y resultado real.
   Los tests verifican que los POST rechazados no cambian los registros; una
   captura de un GET 403 por sí sola no demuestra que una escritura fue bloqueada.
8. Registra la versión probada con git rev-parse HEAD. Adjunta el SHA y la salida
   real de tests a tu tabla de pruebas. La ejecución en este entorno no reemplaza
   las capturas de tu instalación local.

No incluyas contraseñas, cookies, tokens o datos personales reales en capturas.

## Texto base para el informe

ASC-02, autorización: cada operación implementada consulta en el servidor los
roles persistidos de la cuenta autenticada. Se conserva Role/UserRole y se
separa la modificación de precios de la ficha general. La ausencia de permiso
deniega el acceso; los campos admitidos se definen explícitamente en formularios.
El control aborda la amenaza A2, elevación de privilegios, y se verifica mediante
pruebas permitidas y rechazadas con comprobación del estado de la base de datos.

La base RBAC se integró en main mediante el PR #6. La ampliación DSE-35/36/37
añade permisos de bodegas/movimientos y auditoría protegida mediante triggers
en SQLite. Los permisos nuevos y sus límites están en INVENTARIO.md.
Pendiente: revisión del equipo, capturas locales, despliegue con HTTPS y cifrado,
y línea base SonarQube. La ampliación se entrega sin commit ni PR; no cerrar sus
tickets antes de revisar e integrar los cambios.
