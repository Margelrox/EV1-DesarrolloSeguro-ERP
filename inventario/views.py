from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib import messages
from django.db import IntegrityError, OperationalError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from users.permissions import get_user_access, inventory_permission_required
from .forms import (ProductCreateForm, ProductEditForm, ProductPriceForm,
                    WarehouseForm, MovementForm)
from .models import AuditEntry, Movement, Product, Warehouse, WarehouseStock
from .services import product_values, record_audit, register_movement, warehouse_values


def form_page(request, form, title, help_text='', cancel_url='inventario:product_list'):
    return render(request, 'inventario/product_form.html', {
        'form': form, 'title': title, 'help_text': help_text, 'cancel_url': cancel_url,
    })


def reject_price_field(request):
    if request.method == 'POST' and 'precio' in request.POST:
        record_audit(request, 'acceso_denegado', request.path, nuevo={'permiso': 'change_prices'})
        raise PermissionDenied('El precio se cambia en la operación de precios.')


@inventory_permission_required('view_products')
@require_GET
def product_list(request):
    return render(request, 'inventario/product_list.html', {
        'products': Product.objects.order_by('codigo'), 'access': get_user_access(request.user),
    })


@inventory_permission_required('view_products')
@require_GET
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'inventario/product_detail.html', {
        'product': product, 'balances': WarehouseStock.objects.filter(producto=product).select_related('bodega'),
        'access': get_user_access(request.user),
    })


@inventory_permission_required('edit_products')
@require_http_methods(['GET', 'POST'])
def product_create(request):
    reject_price_field(request)
    form = ProductCreateForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                product = form.save()
                record_audit(request, 'producto_creado', product.pk, nuevo=product_values(product))
        except IntegrityError:
            form.add_error(None, 'No se pudo guardar. Revisa si el código ya existe.')
        else:
            messages.success(request, 'Producto creado correctamente.')
            return redirect('inventario:product_detail', pk=product.pk)
    return form_page(request, form, 'Crear producto',
                     'Código: hasta 20 letras o números. Precio y stock iniciales: 0. La fotografía se indica mediante una URL.')


@inventory_permission_required('edit_products')
@require_http_methods(['GET', 'POST'])
def product_edit(request, pk):
    reject_price_field(request)
    # No guardar los campos de stock/precio de una instancia antigua si hay movimientos concurrentes.
    with transaction.atomic():
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        before = product_values(product)
        form = ProductEditForm(request.POST if request.method == 'POST' else None, instance=product)
        if request.method == 'POST' and form.is_valid():
            product = form.save(commit=False)
            product.save(update_fields=form._meta.fields)
            record_audit(request, 'producto_editado', product.pk, before, product_values(product))
            messages.success(request, 'Ficha actualizada correctamente.')
            return redirect('inventario:product_detail', pk=product.pk)
    return form_page(request, form, f'Editar producto {product.codigo}',
                     'El código, el precio y el stock se conservan.')


@inventory_permission_required('change_prices')
@require_http_methods(['GET', 'POST'])
def product_price(request, pk):
    with transaction.atomic():
        product = get_object_or_404(Product.objects.select_for_update(), pk=pk)
        before = product_values(product)
        form = ProductPriceForm(request.POST if request.method == 'POST' else None, instance=product)
        if request.method == 'POST' and form.is_valid():
            product = form.save(commit=False)
            product.save(update_fields=['precio'])
            record_audit(request, 'precio_editado', product.pk, before, product_values(product))
            messages.success(request, 'Precio actualizado correctamente.')
            return redirect('inventario:product_list')
    return form_page(request, form, f'Cambiar precio de {product.codigo}',
                     'Ingresa un precio igual o mayor que 0. Esta operación solo modifica el precio.')


@inventory_permission_required('view_products')
@require_GET
def warehouse_list(request):
    access = get_user_access(request.user)
    warehouses = Warehouse.objects.order_by('codigo')
    if not access['manage_warehouses']:
        warehouses = warehouses.filter(activa=True)
    return render(request, 'inventario/warehouse_list.html', {'warehouses': warehouses, 'access': access})


@inventory_permission_required('manage_warehouses')
@require_http_methods(['GET', 'POST'])
def warehouse_create(request):
    form = WarehouseForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                warehouse = form.save()
                record_audit(request, 'bodega_creada', f'bodega:{warehouse.pk}', nuevo=warehouse_values(warehouse))
        except IntegrityError:
            form.add_error('codigo', 'Ya existe una bodega con este código.')
        else:
            messages.success(request, 'Bodega creada correctamente.')
            return redirect('inventario:warehouse_list')
    return form_page(request, form, 'Crear bodega', cancel_url='inventario:warehouse_list')


@inventory_permission_required('manage_warehouses')
@require_http_methods(['GET', 'POST'])
def warehouse_edit(request, pk):
    try:
        with transaction.atomic():
            warehouse = get_object_or_404(Warehouse.objects.select_for_update(), pk=pk)
            before = warehouse_values(warehouse)
            form = WarehouseForm(request.POST if request.method == 'POST' else None, instance=warehouse)
            if request.method == 'POST' and form.is_valid():
                warehouse = form.save()
                action = 'bodega_desactivada' if before['activa'] and not warehouse.activa else 'bodega_editada'
                record_audit(request, action, f'bodega:{warehouse.pk}', before, warehouse_values(warehouse))
                messages.success(request, 'Bodega actualizada. Se conserva su historial.')
                return redirect('inventario:warehouse_list')
    except IntegrityError:
        form.add_error('codigo', 'Ya existe una bodega con este código.')
    return form_page(request, form, f'Editar bodega {warehouse.codigo}',
                     'Desmarca Activa para impedir nuevos movimientos sin borrar el historial.',
                     'inventario:warehouse_list')


@inventory_permission_required('view_products')
@require_GET
def movement_list(request):
    return render(request, 'inventario/movement_list.html', {
        'movements': Movement.objects.select_related('producto', 'bodega', 'usuario'),
        'balances': WarehouseStock.objects.select_related('producto', 'bodega').order_by('bodega__codigo', 'producto_id'),
        'access': get_user_access(request.user),
    })


@inventory_permission_required('register_movements')
@require_http_methods(['GET', 'POST'])
def movement_create(request):
    form = MovementForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            movement = register_movement(request, **form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc)
        except OperationalError:
            # SQLite puede rechazar un segundo escritor mientras el primero termina; nunca confirmar un movimiento fallido.
            form.add_error(None, 'La base de datos está ocupada. Recarga el historial y vuelve a intentar.')
        else:
            messages.success(request, 'Movimiento registrado y stock actualizado.')
            return redirect('inventario:movement_detail', pk=movement.pk)
    return form_page(request, form, 'Registrar movimiento',
                     'La cantidad debe ser mayor que 0. Las salidas no pueden superar el stock de la bodega.',
                     'inventario:movement_list')


@inventory_permission_required('view_products')
@require_GET
def movement_detail(request, pk):
    movement = get_object_or_404(Movement.objects.select_related('producto', 'bodega', 'usuario'), pk=pk)
    return render(request, 'inventario/movement_detail.html', {'movement': movement})


@inventory_permission_required('manage_warehouses')
@require_GET
def audit_list(request):
    return render(request, 'inventario/audit_list.html', {
        'entries': AuditEntry.objects.select_related('usuario')[:200],
    })
