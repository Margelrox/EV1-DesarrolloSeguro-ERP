from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class PaginaInicioTests(TestCase):
    """Verificaciones de inicio adaptadas al flujo actual con autenticación."""

    @classmethod
    def setUpTestData(cls):
        cls.password = token_urlsafe(24)
        cls.user = get_user_model().objects.create_user(username='usuario_inicio', password=cls.password)

    def test_entrada_sin_sesion_lleva_al_login(self):
        for url in ('/', reverse('inicio:inicio')):
            self.assertRedirects(self.client.get(url), reverse('inicio:login'))

    def test_entrada_con_sesion_lleva_al_panel(self):
        self.client.force_login(self.user)
        for url in ('/', reverse('inicio:inicio'), reverse('inicio:login')):
            self.assertRedirects(self.client.get(url), reverse('inicio:dashboard'))

    def test_login_muestra_formulario(self):
        response = self.client.get(reverse('inicio:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'inicio/index.html')
        self.assertContains(response, 'Iniciar sesión')

    def test_login_incorrecto_no_abre_sesion(self):
        response = self.client.post(reverse('inicio:login'), {
            'username': self.user.username, 'password': 'credencial_incorrecta',
        })
        self.assertContains(response, 'Usuario o contraseña incorrectos.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_correcto_y_opcion_de_mantener_sesion(self):
        for remember, expires_on_close in (('', True), ('on', False)):
            with self.subTest(remember=remember):
                self.client.logout()
                response = self.client.post(reverse('inicio:login'), {
                    'username': self.user.username, 'password': self.password, 'remember_me': remember,
                })
                self.assertRedirects(response, reverse('inicio:dashboard'))
                self.assertEqual(self.client.session.get_expire_at_browser_close(), expires_on_close)

    def test_cerrar_sesion_muestra_confirmacion(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('inicio:logout'), follow=True)
        self.assertContains(response, 'Se ha cerrado sesión satisfactoriamente')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_panel_sin_rol_orienta_al_usuario(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('inicio:dashboard')), 'Tu cuenta no tiene acceso a Inventario.')

    def test_ruta_inexistente_da_404(self):
        self.assertEqual(self.client.get('/no-existe/').status_code, 404)
