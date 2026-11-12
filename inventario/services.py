"""Operaciones del inventario; stock y auditoría se guardan juntos."""
from ipaddress import ip_address

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from .models import AuditEntry, Movement, Product, Warehouse, WarehouseStock


MAX_STOCK = 2147483647


def record_audit(request, accion, objeto, anterior=None, nuevo=None):
    # REMOTE_ADDR es la conexión observada; no confiar en un X-Forwarded-For enviado por el cliente.
    try:
        address = str(ip_address(request.META.get('REMOTE_ADDR', '')))
    except ValueError:
        address = None
    return AuditEntry.objects.create(
        usuario=request.user, ip=address, accion=accion, objeto=str(objeto)[:250],
        anterior=anterior or {}, nuevo=nuevo or {},
    )


def product_values(product):
    return {field.name: str(getattr(product, field.name))
            for field in product._meta.fields}


def warehouse_values(warehouse):
    return {'codigo': warehouse.codigo, 'nombre': warehouse.nombre, 'activa': warehouse.activa}


@transaction.atomic
def register_movement(request, *, producto, bodega, tipo, cantidad, concepto):
    if tipo not in dict(Movement.TIPOS) or not isinstance(cantidad, int) or not 1 <= cantidad <= MAX_STOCK:
        raise ValidationError('Indica un tipo válido y una cantidad entera mayor que cero.')
    concepto = concepto.strip()
    if not concepto or len(concepto) > 200:
        raise ValidationError('Indica un concepto de hasta 200 caracteres.')
    # La primera escritura bloquea la bodega, también en SQLite, donde FOR UPDATE no tiene efecto.
    # Una desactivación concurrente espera; si ya estaba inactiva, no se registra nada.
    if not Warehouse.objects.filter(pk=bodega.pk, activa=True).update(activa=F('activa')):
        raise ValidationError('La bodega está inactiva; no admite nuevos movimientos.')
    Product.objects.filter(pk=producto.pk).update(stock=F('stock'))
    producto = Product.objects.get(pk=producto.pk)
    balance, _ = WarehouseStock.objects.get_or_create(producto=producto, bodega=bodega)
    before = balance.cantidad
    delta = cantidad if tipo == Movement.ENTRADA else -cantidad
    after = before + delta
    total_after = producto.stock + delta
    if after < 0:
        raise ValidationError(f'Stock insuficiente en esta bodega. Disponible: {before}.')
    if not 0 <= total_after <= MAX_STOCK or after > MAX_STOCK:
        raise ValidationError('El movimiento supera los límites de stock permitidos.')
    updated = WarehouseStock.objects.filter(pk=balance.pk, cantidad=before).update(cantidad=F('cantidad') + delta)
    if not updated:
        raise ValidationError('El stock cambió. Recarga e intenta nuevamente.')
    Product.objects.filter(pk=producto.pk).update(stock=F('stock') + delta)
    movement = Movement.objects.create(
        producto=producto, bodega=bodega, tipo=tipo, cantidad=cantidad, concepto=concepto,
        usuario=request.user, stock_anterior=before, stock_nuevo=after,
    )
    record_audit(request, 'movimiento_creado', f'movimiento:{movement.pk}',
                 {'stock_bodega': before, 'stock_total': producto.stock},
                 {'stock_bodega': after, 'stock_total': total_after, 'producto': producto.pk,
                  'bodega': bodega.pk, 'tipo': tipo, 'cantidad': cantidad, 'concepto': concepto})
    return movement
