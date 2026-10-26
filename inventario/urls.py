from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('productos/', views.product_list, name='product_list'),
]