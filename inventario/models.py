from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class Product(models.Model):
    codigo = models.CharField(max_length=50, unique=True, primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    stock = models.IntegerField(default=0)
    grupo = models.CharField(max_length=80, blank=True)
    subgrupo = models.CharField(max_length=80, blank=True)
    codigo_barras = models.CharField(max_length=50, blank=True)
    fotografia = models.URLField(blank=True, verbose_name='URL de fotografía')
    ficha_tecnica = models.TextField(blank=True)
    impuesto = models.DecimalField(max_digits=5, decimal_places=2, default=0,
                                  validators=[MinValueValidator(0), MaxValueValidator(100)])
    nivel_optimo = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'products'
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Warehouse(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.codigo} - {self.nombre}'


class WarehouseStock(models.Model):
    producto = models.ForeignKey(Product, on_delete=models.PROTECT)
    bodega = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['producto', 'bodega'], name='stock_producto_bodega_unico'),
            models.CheckConstraint(condition=models.Q(cantidad__gte=0), name='stock_bodega_no_negativo'),
        ]


class Movement(models.Model):
    ENTRADA = 'entrada'
    SALIDA = 'salida'
    TIPOS = [(ENTRADA, 'Entrada'), (SALIDA, 'Salida')]
    producto = models.ForeignKey(Product, on_delete=models.PROTECT)
    bodega = models.ForeignKey(Warehouse, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=7, choices=TIPOS)
    cantidad = models.PositiveIntegerField()
    concepto = models.CharField(max_length=200)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    stock_anterior = models.PositiveIntegerField()
    stock_nuevo = models.PositiveIntegerField()

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(cantidad__gt=0),
                                               name='movimiento_cantidad_positiva')]


class AuditEntry(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(null=True)
    accion = models.CharField(max_length=80)
    objeto = models.CharField(max_length=250)
    anterior = models.JSONField(default=dict)
    nuevo = models.JSONField(default=dict)

    class Meta:
        ordering = ['-fecha', '-pk']
