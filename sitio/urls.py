from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='inicio/login', permanent=False)),
    path('admin/', admin.site.urls),
    path('inicio/', include('inicio.urls')),
    path('inventario/', include('inventario.urls')),
]
