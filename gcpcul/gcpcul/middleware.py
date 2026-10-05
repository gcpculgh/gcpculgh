import re

class VercelSecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Inject the missing headers directly into the Python response
        response['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:;"
        response['Permissions-Policy'] = "camera=(), microphone=(), geolocation=()"
        return response


class StripHtmlCommentsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.has_header('Content-Type') and 'text/html' in response['Content-Type']:
            content = b''.join(response.streaming_content) if response.streaming else response.content
            content = re.sub(rb'<!--.*?-->', b'', content, flags=re.DOTALL)
            if response.streaming:
                response.streaming_content = [content]
            else:
                response.content = content
            del response['Content-Length']
            response['Content-Length'] = len(content)
        return response   