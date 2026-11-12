from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm
from users.permissions import get_login_role_hints, get_user_access

FUNCIONES = [
    'Ficha completa de productos (código, grupos, código de barras, ficha técnica, impuestos)',
    'Emisión de etiquetas de productos',
    'Múltiples bodegas',
    'Control de reservas, consignaciones y consumos',
    'Toma de inventario',
    'Optimización de los niveles de stock',
    'Listas de precios',
    'Ficha del cliente',
    'Consultas e informes',
]
def inicio(request):
    return redirect('inicio:dashboard' if request.user.is_authenticated else 'inicio:login')


#Se añade login view para seguir protocolos de desarrollo de django - Juan
def login_view(request):
    if request.user.is_authenticated:
        return redirect('inicio:dashboard')
        
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None: 
                login(request, user)
                request.session.set_expiry(None if request.POST.get('remember_me') == 'on' else 0)
                return redirect('inicio:dashboard')
            else: 
                messages.error(request, 'Usuario o contraseña inválido')
    else:
        
        form = LoginForm()
        
   
    return render(request, 'inicio/index.html', {
        'form': form,
        'role_hints': get_login_role_hints(),
    })
        
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, 'Se ha cerrado sesión satisfactoriamente')
    return redirect('inicio:login')

''' def inicio(request):
    """Página de inicio: presentación del Módulo de Inventario."""
    return render(
        request,
        'inicio/index.html',
        {
            'titulo': 'Módulo de Inventario — ERP Seguridad LTDA',
            'descripcion': 'Proyecto EV1 de Desarrollo Seguro (DevSecOps) — Caso "Seguridad LTDA", Equipo 3.',
            'funciones': FUNCIONES,
            'equipo': 'Luis · Juan · Esteban',
        },
    )
    #Deprecated 
'''
#Se requiere login para entrar a dashboard
@login_required
def dashboard(request):
    from django.shortcuts import render
    from users.permissions import get_user_access
    from django.db.models import F, Sum
    from inventario.models import Product, Warehouse, Movement

    access = get_user_access(request.user)
    context = {
        'user': request.user,
        'permissions': access['modules'],
        'roles': access['roles'],
        'access': access,
    } 
    if access['view_products']:
        context['summary'] = {
            'products': Product.objects.count(),
            'warehouses': Warehouse.objects.filter(activa=True).count(),
            'units': Product.objects.aggregate(total=Sum('stock'))['total'] or 0,
            'low_stock': Product.objects.filter(nivel_optimo__gt=0, stock__lt=F('nivel_optimo')).count(),
        }
        context['recent_movements'] = Movement.objects.select_related('producto', 'bodega', 'usuario')[:5]
    return render(request, 'inicio/dashboard.html', context)

