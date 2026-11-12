from secrets import token_urlsafe

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from users.models import Role, UserRole


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

    def test_login_ofrece_alternar_visibilidad_de_la_contrasena(self):
        response = self.client.get(reverse('inicio:login'))
        html = response.content.decode()
        campo = response.context['form']['password']
        self.assertEqual(campo.field.widget.input_type, 'password')
        self.assertIn(f'id="{campo.id_for_label}"', html)
        self.assertContains(response, 'class="toggle-password"')
        self.assertContains(response, f'data-target="{campo.id_for_label}"')
        self.assertContains(response, f'aria-controls="{campo.id_for_label}"')
        self.assertContains(response, 'aria-pressed="false"')
        self.assertContains(response, 'inicio/login.js')
        # El campo se envía como contraseña; el botón no altera el POST.
        self.assertEqual(response.context['form']['password'].value(), None)

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


class RolesEnLoginTests(TestCase):
    """El mini prompt del login lista roles y cuentas demo, sin exponer otras cuentas."""

    @classmethod
    def setUpTestData(cls):
        cls.password = token_urlsafe(24)
        admin_user = get_user_model().objects.create_user(username='demo_admin', password=cls.password)
        seller_user = get_user_model().objects.create_user(username='demo_vendedor', password=cls.password)
        get_user_model().objects.create_user(username='demo_sin_rol', password=cls.password)
        real_user = get_user_model().objects.create_user(username='cuenta_real_ltda', password=cls.password)
        admin_role = Role.objects.create(
            role_name='Administrador', inventory=2, can_change_prices=True, can_manage_roles=True,
        )
        seller_role = Role.objects.create(role_name='Vendedor', inventory=1)
        for user, role in ((admin_user, admin_role), (seller_user, seller_role), (real_user, admin_role)):
            UserRole.objects.create(user_id=user, role=role)

    def test_prompt_lista_roles_con_su_cuenta_demo_y_nivel_de_acceso(self):
        response = self.client.get(reverse('inicio:login'))
        self.assertEqual(response.status_code, 200)
        hints = {hint['role']: hint for hint in response.context['role_hints']}
        self.assertEqual(set(hints), {'Administrador', 'Vendedor', 'Sin rol'})
        self.assertEqual(hints['Administrador']['users'], ['demo_admin'])
        self.assertEqual(hints['Vendedor']['users'], ['demo_vendedor'])
        self.assertEqual(hints['Sin rol']['users'], ['demo_sin_rol'])
        self.assertIn('cambiar precios', hints['Administrador']['access'])
        self.assertEqual(hints['Vendedor']['access'], 'Solo consultar')
        for texto in ('Roles disponibles', 'demo_admin', 'demo_vendedor', 'demo_sin_rol'):
            self.assertContains(response, texto)

    def test_cada_fila_con_cuenta_demo_tiene_boton_de_copiar(self):
        response = self.client.get(reverse('inicio:login'))
        html = response.content.decode()
        self.assertEqual(html.count('class="copy-user"'), 3)
        for username in ('demo_admin', 'demo_vendedor', 'demo_sin_rol'):
            self.assertContains(response, f'data-copy="{username}"')
            self.assertContains(response, f'aria-label="Copiar el usuario {username}"')
        # Sin rol no tiene cuenta asociada real, así que no debe copiar la cuenta real.
        self.assertNotIn('data-copy="cuenta_real_ltda"', html)
        self.assertContains(response, 'inicio/login.js')

    def test_prompt_no_publica_cuentas_que_no_son_demo_ni_claves(self):
        response = self.client.get(reverse('inicio:login'))
        self.assertNotContains(response, 'cuenta_real_ltda')
        self.assertNotContains(response, self.password)
        # La cuenta real existe y tiene rol, pero queda fuera del listado público.
        self.assertTrue(UserRole.objects.filter(user_id__username='cuenta_real_ltda').exists())
