"""Allow the existing admin inside the same-origin CRCON workspace only."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from django.utils import translation


class AdminEmbeddingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_admin = request.path.startswith("/admin/")
        embedded = is_admin and request.GET.get("embedded") == "1"
        language = request.GET.get("ui_language") if is_admin else None
        if language not in {"de", "en", "fr"}:
            language = None
        if embedded or (is_admin and "ui_language" in request.GET):
            # Django changelists interpret every unknown query key as a model
            # filter. Keep the transport flag out of their filtering logic.
            query = request.GET.copy()
            query.pop("embedded", None)
            query.pop("ui_language", None)
            request.GET = query
        with translation.override(language or translation.get_language()):
            response = self.get_response(request)
        if embedded:
            response["X-Frame-Options"] = "SAMEORIGIN"
            if "Content-Security-Policy" not in response:
                response["Content-Security-Policy"] = "frame-ancestors 'self'"
            location = response.get("Location")
            if location:
                target = urlsplit(location)
                if not target.netloc and target.path.startswith("/admin/"):
                    query = [(key, value) for key, value in parse_qsl(target.query, keep_blank_values=True) if key != "embedded"]
                    query.append(("embedded", "1"))
                    if language:
                        query = [(key, value) for key, value in query if key != "ui_language"]
                        query.append(("ui_language", language))
                    response["Location"] = urlunsplit(target._replace(query=urlencode(query)))
        return response
