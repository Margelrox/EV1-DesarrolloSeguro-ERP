from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('productos/', views.product_list, name='product_list'),
    path('productos/crear/', views.product_create, name='product_create'),
    path('productos/<str:pk>/editar/', views.product_edit, name='product_edit'),
    path('productos/<str:pk>/precio/', views.product_price, name='product_price'),
]
