from urllib.parse import urlsplit

from django import forms
from django.core.validators import RegexValidator

from .models import Product, Warehouse, Movement


PRODUCT_FIELDS = ('nombre', 'descripcion', 'grupo', 'subgrupo', 'codigo_barras',
                  'fotografia', 'ficha_tecnica', 'impuesto', 'nivel_optimo')
PRODUCT_LABELS = {
    'nombre': 'Nombre', 'descripcion': 'Descripción (opcional)', 'grupo': 'Grupo',
    'subgrupo': 'Subgrupo', 'codigo_barras': 'Código de barras',
    'fotografia': 'Fotografía (URL http/https, opcional)', 'ficha_tecnica': 'Ficha técnica',
    'impuesto': 'Impuesto (%)', 'nivel_optimo': 'Nivel óptimo de stock',
}


class ProductForm(forms.ModelForm):
    impuesto = forms.DecimalField(label='Impuesto (%)', max_digits=5, decimal_places=2,
                                  min_value=0, max_value=100, required=False)
    nivel_optimo = forms.IntegerField(label='Nivel óptimo de stock', min_value=0,
                                     max_value=2147483647, required=False)

    def clean_fotografia(self):
        value = self.cleaned_data.get('fotografia', '')
        if value and urlsplit(value).scheme not in ('http', 'https'):
            raise forms.ValidationError('La fotografía debe usar una URL http o https.')
        return value

    def clean_impuesto(self):
        return self.cleaned_data['impuesto'] or 0

    def clean_nivel_optimo(self):
        return self.cleaned_data['nivel_optimo'] or 0

    def clean(self):
        data = super().clean()
        if data.get('subgrupo') and not data.get('grupo'):
            self.add_error('grupo', 'Indica el grupo al que pertenece el subgrupo.')
        return data


class ProductCreateForm(ProductForm):
    codigo = forms.CharField(label='Código', max_length=20, validators=[
        RegexValidator(r'\A[A-Za-z0-9]+\Z', 'Usa solo letras y números (máximo 20 caracteres).')
    ])

    class Meta:
        model = Product
        # Precio y stock no se modifican mediante la ficha general.
        fields = ('codigo',) + PRODUCT_FIELDS
        labels = PRODUCT_LABELS
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3}),
                   'ficha_tecnica': forms.Textarea(attrs={'rows': 3})}

    def clean_codigo(self):
        value = self.cleaned_data['codigo']
        if Product.objects.filter(codigo=value).exists():
            raise forms.ValidationError('Ya existe un producto con este código.')
        return value


class ProductEditForm(ProductForm):
    class Meta:
        model = Product
        fields = PRODUCT_FIELDS
        labels = PRODUCT_LABELS
        widgets = {'descripcion': forms.Textarea(attrs={'rows': 3}),
                   'ficha_tecnica': forms.Textarea(attrs={'rows': 3})}


class ProductPriceForm(forms.ModelForm):
    precio = forms.DecimalField(label='Precio', max_digits=10, decimal_places=2, min_value=0)

    class Meta:
        model = Product
        fields = ('precio',)


class WarehouseForm(forms.ModelForm):
    codigo = forms.CharField(label='Código', max_length=20, validators=[
        RegexValidator(r'\A[A-Za-z0-9]+\Z', 'Usa solo letras y números.')
    ])

    class Meta:
        model = Warehouse
        fields = ('codigo', 'nombre', 'activa')
        labels = {'nombre': 'Nombre', 'activa': 'Activa (permite nuevos movimientos)'}


class MovementForm(forms.ModelForm):
    cantidad = forms.IntegerField(min_value=1, max_value=2147483647, label='Cantidad')

    class Meta:
        model = Movement
        fields = ('producto', 'bodega', 'tipo', 'cantidad', 'concepto')
        labels = {'producto': 'Producto', 'bodega': 'Bodega', 'tipo': 'Tipo', 'concepto': 'Concepto'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Product.objects.order_by('codigo')
        self.fields['bodega'].queryset = Warehouse.objects.filter(activa=True).order_by('codigo')
