from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from users.permissions import get_user_access, inventory_permission_required
from .forms import ProductCreateForm, ProductEditForm, ProductPriceForm
from .models import Product


@inventory_permission_required('view_products')
@require_GET
def product_list(request):
    return render(request, 'inventario/product_list.html', {
        'products': Product.objects.order_by('codigo'),
        'access': get_user_access(request.user),
    })


@inventory_permission_required('edit_products')
@require_http_methods(['GET', 'POST'])
def product_create(request):
    if request.method == 'POST' and 'precio' in request.POST:
        raise PermissionDenied('El precio se cambia en la operación de precios.')
    form = ProductCreateForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Producto creado correctamente.')
        return redirect('inventario:product_list')
    return render(request, 'inventario/product_form.html', {
        'form': form, 'title': 'Crear producto',
        'help_text': 'El precio y el stock iniciales son 0. Un administrador puede configurar el precio por separado.',
    })


@inventory_permission_required('edit_products')
@require_http_methods(['GET', 'POST'])
def product_edit(request, pk):
    if request.method == 'POST' and 'precio' in request.POST:
        raise PermissionDenied('El precio se cambia en la operación de precios.')
    product = get_object_or_404(Product, pk=pk)
    form = ProductEditForm(request.POST if request.method == 'POST' else None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Ficha actualizada correctamente.')
        return redirect('inventario:product_list')
    return render(request, 'inventario/product_form.html', {
        'form': form, 'title': f'Editar producto {product.codigo}',
        'help_text': 'Aquí puedes editar el nombre y la descripción. El código, el precio y el stock se conservan.',
    })


@inventory_permission_required('change_prices')
@require_http_methods(['GET', 'POST'])
def product_price(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductPriceForm(request.POST if request.method == 'POST' else None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Precio actualizado correctamente.')
        return redirect('inventario:product_list')
    return render(request, 'inventario/product_form.html', {
        'form': form, 'title': f'Cambiar precio de {product.codigo}',
        'help_text': 'Ingresa un precio igual o mayor que 0. Esta operación solo modifica el precio.',
    })
