class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # DSE-75 (ZAP-01): Política de Seguridad de Contenidos (CSP)
        # Ajusta los dominios si utilizas CDNs externos como jsdelivr o Google Fonts
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self';"
        )
        response['Content-Security-Policy'] = csp_policy

        # DSE-79 (ZAP-04): Ocultar o sobrescribir la cabecera Server
        response['Server'] = 'WebServer'
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        return response