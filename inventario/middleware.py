class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # DSE-75 (ZAP-01): Política de Seguridad de Contenidos (CSP)
        # Se remueven comodines (https:) y 'unsafe-inline' para mitigar alertas de ZAP
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net; "
            "img-src 'self' data:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "object-src 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )
        response['Content-Security-Policy'] = csp_policy

        # DSE-79 (ZAP-04): Ocultar o sobrescribir la cabecera Server y tecnologías
        response['Server'] = 'WebServer'
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        # Cabeceras complementarias de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'

        return response