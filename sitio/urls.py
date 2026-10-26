from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('inicio/', include('inicio.urls')),
    path('inventario/', include('inventario.urls')),
]
