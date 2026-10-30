from django.db import migrations


def set_permissions(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    roles = Role.objects.using(schema_editor.connection.alias)
    roles.filter(role_name='Administrador').update(can_manage_warehouses=True, can_register_movements=True)
    roles.filter(role_name__in=['Jefe de bodega', 'Operador de bodega']).update(can_register_movements=True)


class Migration(migrations.Migration):
    dependencies = [('users', '0003_role_can_manage_warehouses_and_more')]
    operations = [migrations.RunPython(set_permissions, migrations.RunPython.noop)]
