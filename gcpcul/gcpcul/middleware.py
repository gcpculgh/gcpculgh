class VercelSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Inject the missing headers directly into the Python response
        response['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
        response['Permissions-Policy'] = "camera=(), microphone=(), geolocation=()"
        return response