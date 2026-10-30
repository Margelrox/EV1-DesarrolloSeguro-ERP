# Inventario básico · DSE-35 / DSE-36 / DSE-37

Rama: `DSE-35-36-37-inventario`. Base: `main`, commit
`2c1311d45b55af46a4a56c6f30f670bd66a1091e` (PR #6 integrado).
Se conserva Django, SQLite, Product, Role/UserRole y la presentación del equipo.
No se agregan dependencias. La entrega no incluye commit ni Pull Request.

## Ejecutar

Con los cambios aplicados y desde la carpeta del proyecto:

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py preparar_rbac
python manage.py test
python manage.py runserver
```

Antes de migrar una base con datos importantes, guarda una copia de `db.sqlite3`
con el servidor detenido. No incluyas esa copia en Git.

`preparar_rbac` crea los roles que falten, sin cambiar contraseñas o asignaciones
existentes. Las migraciones habilitan los permisos nuevos en los roles base ya
existentes: Administrador administra bodegas y registra movimientos; Jefe de
bodega y Operador de bodega registran movimientos. Los demás permisos previos
se conservan. Roles personalizados parten con ambos permisos nuevos desactivados;
un superusuario puede configurarlos en `/admin/users/role/`.
No se cambia la autenticación ni la autoría de Git por iniciar sesión en VS Code.

## Qué se implementa

- **DSE-35:** alta y edición de ficha, vista de detalle, grupos/subgrupos como
  texto, código de barras, enlace a fotografía, ficha técnica como texto,
  impuesto porcentual y nivel óptimo. Los campos adicionales son opcionales.
  Los códigos nuevos admiten únicamente letras ASCII y números, hasta 20 caracteres,
  con rechazo de duplicados y errores visibles. El código no se cambia al editar.
  Se conserva el campo original de 50 caracteres en la base para no romper códigos
  antiguos; por ejemplo, `ANT-01` sigue siendo consultable y editable.
  Precio continúa como operación separada del administrador, y stock se calcula
  mediante movimientos. La fotografía es una URL http/https; no se suben archivos.
- **DSE-36:** crear, editar y desactivar bodegas sin borrarlas ni limitar su cantidad.
  Administrador ve activas e inactivas; los demás perfiles de inventario consultan
  las activas. Los códigos de bodega son únicos y alfanuméricos, de hasta 20 caracteres.
- **DSE-37:** entradas/salidas de unidades enteras por producto y bodega, concepto,
  usuario y fecha/hora. Detalle del stock anterior/nuevo, historial y existencias
  por bodega; el stock total del producto también se actualiza. Una salida no usa
  existencias de otra bodega. No se aceptan cantidades cero, negativas, fraccionarias,
  superiores al límite de entero, stock insuficiente ni bodegas inactivas.

## Permisos

Se consultan los permisos guardados en Role en cada petición; los nombres de
usuario y campos enviados por el navegador no conceden acceso.

| Operación | Administrador | Jefe | Operador | Vendedor | Sin rol |
|---|---|---|---|---|---|
| Consultar catálogo, bodegas activas, movimientos y stock | Sí | Sí | Sí | Sí | No |
| Crear/editar ficha general | Sí | Sí | No | No | No |
| Cambiar precio | Sí | No | No | No | No |
| Administrar bodegas y consultar auditoría | Sí | No | No | No | No |
| Registrar movimientos | Sí | Sí | Sí | No | No |

Bodegas requiere `can_manage_warehouses` e inventario >= 1; movimientos requiere
`can_register_movements` e inventario >= 1. Se mantiene la agregación de varios
roles. Un usuario autenticado sin permiso recibe 403 y se registra el intento;
un visitante es dirigido al login. Los formularios conservan CSRF.

## Persistencia y auditoría

Stock por bodega, total del producto, movimiento y auditoría se guardan en una
misma transacción. La operación bloquea la bodega activa con una escritura antes
de leer stock y serializa la modificación del producto. Usa actualizaciones con
`F()` y una condición sobre el stock anterior. Si falla la auditoría, se revierte
la operación completa. SQLite puede rechazar un escritor concurrente; el formulario
muestra un mensaje para consultar el historial y reintentar, sin confirmar la escritura.

Si había productos con stock positivo, la migración los asigna a una bodega
`INICIAL` (Existencias anteriores a bodegas). Mantiene los totales previos y no
inventa movimientos históricos. Si encuentra stock previo negativo, detiene la
migración para que el equipo revise esos datos antes de continuar.

Cada creación/edición de ficha, cambio de precio, creación/edición/desactivación
de bodega y movimiento registra usuario, fecha, IP observada y valores anterior/nuevo.
Los accesos denegados registran ruta y permiso, sin copiar contraseñas o formularios.
Solo el administrador de bodegas puede consultar los últimos 200 registros en
`/inventario/auditoria/`. No hay endpoints de edición/eliminación del historial.
Los triggers de SQLite rechazan UPDATE/DELETE de auditoría y movimientos,
incluso vía ORM o SQL normal. Esto protege el historial dentro de la aplicación;
no impide que alguien con control del archivo SQLite quite los triggers o sustituya
la base. No equivale a almacenamiento WORM ni a auditoría externa certificada.
La migración de triggers requiere SQLite; otro motor necesita su implementación
antes de migrar.

## Validación realizada y límites

- Suite completa: 42 pruebas aprobadas, incluidas las 27 de la base anterior.
- Validación servidor, duplicados, matriz de permisos, escrituras rechazadas,
  revocación, stock por bodega, conservación del historial y rollback si falla auditoría.
- Rechazo real de UPDATE/DELETE SQL sobre auditoría y movimientos.
- Prueba de actualización desde el esquema anterior con datos existentes.
- Prueba con dos conexiones: salidas simultáneas de 7 sobre stock 10 dejan stock 3,
  con una sola salida registrada.

No se configura HTTPS ni cifrado de base/respaldos en esta implementación local;
esos criterios de DSE-35 continúan pendientes de infraestructura y evidencia.
Tampoco se ha ejecutado SonarQube. No marcar los tickets como terminados hasta
la revisión, integración y aceptación de los criterios pendientes por el equipo.
No se implementan compras, ventas, traslados, ajustes de inventario, borrado de
productos ni cálculo automático de impuestos sobre precios.

## Recorrido de comprobación

1. Administrador: crea dos bodegas activas desde Inventario → Bodegas.
2. Jefe: crea un producto con código `PROD001`; abre su ficha y edítala.
3. Operador: registra entrada de 10 en una bodega y salida de 3; verifica stock 7
   en la ficha, el listado de existencias y el detalle del movimiento.
4. Intenta salida de 8; debe mostrar error y conservar stock 7.
5. Administrador: desactiva esa bodega; el historial permanece y ya no admite movimientos.
6. Vendedor: consulta el historial y abre directamente `/inventario/movimientos/crear/`;
   debe recibir 403. Administrador verifica el intento en Auditoría.
7. Captura la salida real de `python manage.py test` en tu equipo para el informe.
