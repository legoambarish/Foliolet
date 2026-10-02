class PrivateResponseMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Remove pre-fix plaintext copies even when a user leaves/cancels the review flow.
        request.session.pop("claim_suggestions", None)
        response = self.get_response(request)
        response["Cache-Control"] = "no-store, private"
        # Origin-only referrers hide bearer paths and preserve browser POST Origin for CSRF.
        # no-referrer makes Chromium form POSTs use Origin: null, which Django correctly rejects.
        response["Referrer-Policy"] = "strict-origin"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self' http: https:; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
        return response
