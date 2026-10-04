"""Safe recovery helpers for browser CSRF failures."""

from django.http import JsonResponse
from django.middleware.csrf import (
    REASON_CSRF_TOKEN_MISSING,
    REASON_NO_CSRF_COOKIE,
    get_token,
)
from django.utils.cache import add_never_cache_headers, patch_vary_headers
from django.views.csrf import csrf_failure as django_csrf_failure


def _is_token_failure(reason):
    # Fail closed for unknown reasons. Origin/Referer checks are security
    # denials, not stale-token failures, and must never advertise a retry.
    return reason in {REASON_CSRF_TOKEN_MISSING, REASON_NO_CSRF_COOKIE} or (
        reason.startswith(("CSRF cookie ", "CSRF token from "))
        and reason.endswith(
            (" incorrect.", " has incorrect length.", " has invalid characters.")
        )
    )


def csrf_failure(request, reason=""):
    """Reject before executing any action, with an explicit API error contract."""
    recoverable = _is_token_failure(reason)
    if request.path.startswith("/api/"):
        response = JsonResponse(
            {
                "failed": True,
                "result": None,
                "error": "CSRF verification failed.",
                "error_code": "csrf_failed",
            },
            status=403,
        )
    else:
        # Preserve Django's normal HTML error page for admin/form submissions.
        response = django_csrf_failure(request, reason=reason)
    response["X-CRCON-CSRF-Error"] = "token" if recoverable else "request"
    if recoverable:
        # Keep the existing recovery contract for older deployed frontends.
        response["X-CRCON-CSRF-Recovery"] = "1"
        response["X-CRCON-CSRF-Token"] = get_token(request)
    add_never_cache_headers(response)
    patch_vary_headers(response, ("Cookie",))
    return response
