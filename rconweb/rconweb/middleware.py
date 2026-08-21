"""Security middleware used by the browser-facing Django application."""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware


class SessionCsrfProtectionMiddleware(CsrfViewMiddleware):
    """Enforce CSRF for every unsafe request authenticated by a browser session.

    CRCON historically annotated many API views with ``csrf_exempt`` so that
    token-authenticated integrations could call them.  A browser request with
    a Django session cookie must never inherit that exemption: it can otherwise
    execute administrative actions from a hostile origin.  Service requests
    without a session cookie retain their explicit authentication contract.
    """

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            return None
        if not request.COOKIES.get(settings.SESSION_COOKIE_NAME):
            return None

        if getattr(callback, "csrf_exempt", False):
            # Do not use functools.wraps here: it would copy csrf_exempt to the
            # wrapper and reintroduce the bypass in CsrfViewMiddleware.
            original_callback = callback

            def protected_callback(*args, **kwargs):
                return original_callback(*args, **kwargs)

            callback = protected_callback

        return super().process_view(request, callback, callback_args, callback_kwargs)
