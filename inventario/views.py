from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from users.models import UserRole
from .models import Product

@login_required
def product_list(request):
    # Obtenemos los roles del usuario logueado
    user_roles = UserRole.objects.filter(user_id=request.user)
    
    # Determinamos el nivel máximo de permiso para 'inventory'
    max_permission = 0
    for ur in user_roles:
        perm = ur.role.inventory # Campo inventory de tu modelo Role
        if perm > max_permission:
            max_permission = perm

    # Si no tiene ningún acceso (0), lo devolvemos al dashboard
    if max_permission == 0:
        return redirect('inicio:dashboard')

    products = Product.objects.all()
    
    context = {
        'products': products,
        'permission_level': max_permission, # 1 = View only, 2 = Create/Modify
    }
    return render(request, 'inventario/product_list.html', context)