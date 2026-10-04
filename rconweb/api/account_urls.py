from django.urls import re_path
from django.views.generic import RedirectView

from .account_views import AccountPasswordChangeView, AccountPasswordResetView, AccountPasswordResetConfirmView

urlpatterns = [
    # Accept both historic spellings without redirecting a POST body.
    re_path(r"^password_change/?$", AccountPasswordChangeView.as_view(), name="password_change"),
    re_path(
        r"^password_change/done/?$",
        RedirectView.as_view(url="/account/password?changed=1", permanent=False),
        name="password_change_done",
    ),
    re_path(r"^password_reset/?$", AccountPasswordResetView.as_view(), name="password_reset"),
    re_path(r"^password_reset/done/?$", RedirectView.as_view(url="/forgot-password?sent=1", permanent=False), name="password_reset_done"),
    re_path(r"^reset/(?P<uidb64>[0-9A-Za-z_-]+)/(?P<token>[0-9A-Za-z_-]+)/?$", AccountPasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    re_path(r"^reset/done/?$", RedirectView.as_view(url="/login?password_reset=1", permanent=False), name="password_reset_complete"),
]
