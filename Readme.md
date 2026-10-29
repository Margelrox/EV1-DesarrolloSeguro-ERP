Repositorio Evaluación 1


26/10/26 Se añadio login, dashboard, app inventario y users, se utilizaron los paquetes de django para seguridad.

## Ejecución local

Con el entorno virtual activado:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abre http://127.0.0.1:8000/. La entrada dirige al login o al panel si ya hay sesión.

La matriz de roles y la preparación de cuentas de demostración están en
[docs/RBAC.md](docs/RBAC.md). Para ejecutar todas las pruebas:

```bash
python manage.py test
```

Los ajustes de presentación mantienen el diseño y la estructura de la base del equipo:
fondo, panel translúcido, tarjetas y formularios Django. No requieren nuevas migraciones.
