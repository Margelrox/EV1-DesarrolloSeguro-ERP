from django.shortcuts import render

FUNCIONES = [
    'Ficha completa de productos (código, grupos, código de barras, ficha técnica, impuestos)',
    'Emisión de etiquetas de productos',
    'Múltiples bodegas',
    'Control de reservas, consignaciones y consumos',
    'Toma de inventario',
    'Optimización de los niveles de stock',
    'Listas de precios',
    'Ficha del cliente',
    'Consultas e informes',
]


def inicio(request):
    """Página de inicio: presentación del Módulo de Inventario."""
    return render(
        request,
        'inicio/index.html',
        {
            'titulo': 'Módulo de Inventario — ERP Seguridad LTDA',
            'descripcion': 'Proyecto EV1 de Desarrollo Seguro (DevSecOps) — Caso "Seguridad LTDA", Equipo 3.',
            'funciones': FUNCIONES,
            'equipo': 'Luis · Juan · Esteban',
        },
    )
