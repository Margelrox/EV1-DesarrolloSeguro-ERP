from django import forms

from .models import Product


class ProductCreateForm(forms.ModelForm):
    class Meta:
        model = Product
        # Precio y stock no se modifican mediante la ficha general.
        fields = ('codigo', 'nombre', 'descripcion')


class ProductEditForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('nombre', 'descripcion')


class ProductPriceForm(forms.ModelForm):
    precio = forms.DecimalField(max_digits=10, decimal_places=2, min_value=0)

    class Meta:
        model = Product
        fields = ('precio',)
