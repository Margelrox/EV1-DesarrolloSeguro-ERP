from django import forms
from django.contrib.auth.forms import AuthenticationForm
from users.models import User

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label = 'Username',
        widget= forms.TextInput(attrs=
                                {
                                    'class': 'form-control',
                                    'placeholder' : 'Ingrese su usuario',
                                })
    )

    password = forms.CharField(
        label = 'Password',
        widget= forms.PasswordInput(attrs=
                                {
                                    'class': 'form-control',
                                    'placeholder' : 'Ingrese su contraseña',
                                })
    )

    class meta :
        model = User
        fields = ['username', 'password']