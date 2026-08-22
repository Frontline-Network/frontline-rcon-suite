"""Safe recovery helpers for browser CSRF failures."""

from django.middleware.csrf import get_token
from django.views.csrf import csrf_failure as django_csrf_failure


def csrf_failure(request, reason=""):
    """Reject the request while issuing a token for the next safe retry.

    No protected action is performed for the rejected request.  Marking the
    response for a fresh CSRF cookie lets an already authenticated browser
    recover after a deployment or a stale client-side cookie.
    """

    # Return the token derived from the CSRF cookie Django actually accepted
    # for this request. Browsers can retain duplicate cookies with different
    # paths after upgrades. Reading ``document.cookie`` may then select a stale
    # value even though the browser sends a different cookie to ``/api``.
    # Supplying the server-derived token in the recovery response makes the
    # single retry deterministic without weakening CSRF validation.
    token = get_token(request)
    response = django_csrf_failure(request, reason=reason)
    response["X-CRCON-CSRF-Recovery"] = "1"
    response["X-CRCON-CSRF-Token"] = token
    return response
