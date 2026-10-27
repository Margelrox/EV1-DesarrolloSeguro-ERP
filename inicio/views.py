from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm
from users.permissions import get_user_access

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
                return redirect('inicio:dashboard')
            else: 
                messages.error(request, 'Usuario o contraseña inválido')
    else:
        
        form = LoginForm()
        
   
    return render(request, 'inicio/index.html', {'form': form})
        
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
    access = get_user_access(request.user)
    context = {
        'user': request.user,
        'permissions': access['modules'],
        'roles': access['roles'],
        'access': access,
    } 
    return render (request, 'inicio/dashboard.html', context)

