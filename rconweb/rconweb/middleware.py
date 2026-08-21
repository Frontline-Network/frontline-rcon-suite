"""Security middleware used by the browser-facing Django application."""

from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware


# These historical API endpoints use POST for filter payloads, but only return
# data. They are explicitly kept outside session CSRF enforcement so an
# already-authenticated operator can open the live/log views without requiring
# a CSRF token for a non-mutating request. Server and moderation actions are
# deliberately not listed here.
READ_ONLY_POST_PATHS = frozenset(
    {
        "/api/get_historical_logs",
        "/api/get_players_history",
        "/api/get_recent_logs",
        "/api/get_recent_logs_summary",
    }
)


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
        if request.path.rstrip("/") in READ_ONLY_POST_PATHS:
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
