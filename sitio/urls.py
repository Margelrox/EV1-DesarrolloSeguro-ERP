from django.contrib import admin
from django.urls import include, path
from inicio.views import inicio

urlpatterns = [
    path('', inicio, name='home'),
    path('admin/', admin.site.urls),
    path('inicio/', include('inicio.urls')),
    path('inventario/', include('inventario.urls')),
]
