"""Safe recovery helpers for browser CSRF failures."""

from django.middleware.csrf import get_token
from django.views.csrf import csrf_failure as django_csrf_failure


def csrf_failure(request, reason=""):
    """Reject the request while issuing a token for the next safe retry.

    No protected action is performed for the rejected request.  Marking the
    response for a fresh CSRF cookie lets an already authenticated browser
    recover after a deployment or a stale client-side cookie.
    """

    get_token(request)
    response = django_csrf_failure(request, reason=reason)
    response["X-CRCON-CSRF-Recovery"] = "1"
    return response
