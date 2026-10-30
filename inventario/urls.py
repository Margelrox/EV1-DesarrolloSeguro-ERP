from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('productos/', views.product_list, name='product_list'),
    path('productos/crear/', views.product_create, name='product_create'),
    path('productos/<str:pk>/', views.product_detail, name='product_detail'),
    path('productos/<str:pk>/editar/', views.product_edit, name='product_edit'),
    path('productos/<str:pk>/precio/', views.product_price, name='product_price'),
    path('bodegas/', views.warehouse_list, name='warehouse_list'),
    path('bodegas/crear/', views.warehouse_create, name='warehouse_create'),
    path('bodegas/<int:pk>/editar/', views.warehouse_edit, name='warehouse_edit'),
    path('movimientos/', views.movement_list, name='movement_list'),
    path('movimientos/crear/', views.movement_create, name='movement_create'),
    path('movimientos/<int:pk>/', views.movement_detail, name='movement_detail'),
    path('auditoria/', views.audit_list, name='audit_list'),
]
