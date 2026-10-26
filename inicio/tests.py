from django.test import TestCase
from django.urls import reverse


class PaginaInicioTests(TestCase):
    """Verificaciones básicas de la página de inicio."""

    def test_responde_200_y_usa_la_plantilla(self):
        respuesta = self.client.get('/')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, 'inicio/index.html')

    def test_muestra_el_titulo_del_modulo(self):
        contenido = self.client.get('/').content.decode('utf-8')
        self.assertIn('Módulo de Inventario — ERP Seguridad LTDA', contenido)
        self.assertIn('DevSecOps', contenido)

    def test_lista_las_funcionalidades(self):
        contenido = self.client.get('/').content.decode('utf-8')
        for funcion in ('Ficha completa de productos', 'Múltiples bodegas', 'Toma de inventario', 'Listas de precios'):
            self.assertIn(funcion, contenido)

    def test_muestra_el_equipo(self):
        contenido = self.client.get('/').content.decode('utf-8')
        for integrante in ('Luis', 'Juan', 'Esteban'):
            self.assertIn(integrante, contenido)

    def test_url_inicio_se_invierte_a_la_raiz(self):
        self.assertEqual(reverse('inicio:inicio'), '/')

    def test_ruta_inexistente_da_404(self):
        self.assertEqual(self.client.get('/no-existe/').status_code, 404)
