from django.db import migrations


def initialize_stock(apps, schema_editor):
    Product = apps.get_model('inventario', 'Product')
    Warehouse = apps.get_model('inventario', 'Warehouse')
    Stock = apps.get_model('inventario', 'WarehouseStock')
    alias = schema_editor.connection.alias
    if Product.objects.using(alias).filter(stock__lt=0).exists():
        raise ValueError('Hay productos con stock negativo previo. Revisa esos datos antes de migrar.')
    products = Product.objects.using(alias).filter(stock__gt=0)
    if products.exists():
        warehouse = Warehouse.objects.using(alias).create(codigo='INICIAL', nombre='Existencias anteriores a bodegas')
        for product in products.iterator():
            Stock.objects.using(alias).create(producto_id=product.pk, bodega_id=warehouse.pk, cantidad=product.stock)


def protect_history(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        raise ValueError('Esta protección de historial requiere SQLite. Implementa los triggers del motor de destino antes de migrar.')
    for model in ('auditentry', 'movement'):
        for operation in ('UPDATE', 'DELETE'):
            schema_editor.execute(
                f'CREATE TRIGGER inventario_{model}_no_{operation.lower()} '
                f'BEFORE {operation} ON inventario_{model} '
                "BEGIN SELECT RAISE(ABORT, 'El historial de inventario no se puede modificar ni borrar'); END;"
            )


def unprotect_history(apps, schema_editor):
    for model in ('auditentry', 'movement'):
        for operation in ('update', 'delete'):
            schema_editor.execute(f'DROP TRIGGER IF EXISTS inventario_{model}_no_{operation}')


class Migration(migrations.Migration):
    dependencies = [('inventario', '0002_warehouse_product_codigo_barras_and_more')]
    operations = [
        migrations.RunPython(initialize_stock, migrations.RunPython.noop),
        migrations.RunPython(protect_history, unprotect_history),
    ]
