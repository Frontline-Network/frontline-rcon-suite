"""Browser account forms presented by the CRCON frontend."""

import logging
from math import ceil

from django.conf import settings
from django.contrib.auth import password_validation
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordChangeView, PasswordResetView, PasswordResetConfirmView
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.template import loader
from django.utils import translation
from django.utils.crypto import salted_hmac
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters

from .ratelimits import _proxy_client_ip

logger = logging.getLogger(__name__)


def limited(scope, identity, maximum, seconds):
    """Use the existing shared cache; store no plaintext addresses or tokens."""
    key = "password-reset:" + salted_hmac(scope, identity).hexdigest()
    if cache.add(key, 1, timeout=seconds):
        return False
    try:
        return cache.incr(key) > maximum
    except ValueError:  # Expired between add and incr.
        return not cache.add(key, 1, timeout=seconds)


def password_settings(request):
    return {
        "can_change_password": True,
        "requirements": password_validation.password_validators_help_texts(),
        "csrf_token": get_token(request),
    }


class AccountJsonMixin:
    def dispatch(self, request, *args, **kwargs):
        self.json_response = "application/json" in request.headers.get("Accept", "")
        language = request.GET.get("ui_language")
        self.language = language if language in {"de", "en", "fr"} else translation.get_language()
        with translation.override(self.language):
            response = super().dispatch(request, *args, **kwargs)
        response["Referrer-Policy"] = "no-referrer"
        return response

    def form_invalid(self, form):
        return JsonResponse({"errors": dict(form.errors)}, status=400)


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters(), name="dispatch")
class AccountPasswordChangeView(PasswordChangeView):
    success_url = "/account/password?changed=1"

    def dispatch(self, request, *args, **kwargs):
        self.json_response = "application/json" in request.headers.get("Accept", "")
        if not request.user.is_authenticated:
            if self.json_response:
                return JsonResponse({"error": "authentication_required"}, status=401)
            return HttpResponseRedirect("/login?from=%2Faccount%2Fpassword")
        language = request.GET.get("ui_language")
        if language not in {"de", "en", "fr"}:
            language = translation.get_language()
        with translation.override(language):
            # Keep Django's login, CSRF, old-password and validator checks.
            return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not self.json_response:
            return HttpResponseRedirect("/account/password")
        return JsonResponse({
            "username": request.user.get_username(),
            "can_change_password": request.user.has_usable_password(),
            "requirements": password_validation.password_validators_help_texts(),
            "csrf_token": get_token(request),
        })

    def form_valid(self, form):
        # Django saves only request.user and preserves the current session.
        response = super().form_valid(form)
        if self.json_response:
            return JsonResponse({"changed": True})
        return response

    def form_invalid(self, form):
        # Return messages, never bound input values or rendered password fields.
        return JsonResponse({"errors": dict(form.errors)}, status=400)


class PrivatePasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name, context,
                  from_email, to_email, html_email_template_name=None):
        # Django's default exception logger includes the recipient. Keep failures
        # private and let the view return the same result for every address.
        subject = "".join(loader.render_to_string(subject_template_name, context).splitlines())
        body = loader.render_to_string(email_template_name, context)
        EmailMultiAlternatives(subject, body, from_email, [to_email]).send()


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("email"), name="dispatch")
class AccountPasswordResetView(AccountJsonMixin, PasswordResetView):
    form_class = PrivatePasswordResetForm
    email_template_name = "registration/crcon_password_reset_email.txt"
    subject_template_name = "registration/crcon_password_reset_subject.txt"
    success_url = "/forgot-password?sent=1"

    def get(self, request, *args, **kwargs):
        if not self.json_response:
            return HttpResponseRedirect("/forgot-password")
        return JsonResponse({
            "available": bool(getattr(settings, "CRCON_PASSWORD_RESET_ENABLED", False)),
            "csrf_token": get_token(request),
        })

    def post(self, request, *args, **kwargs):
        if not getattr(settings, "CRCON_PASSWORD_RESET_ENABLED", False):
            return JsonResponse({"error": "unavailable"}, status=503)
        try:
            if limited("reset-ip", _proxy_client_ip(request), 10, 900):
                response = JsonResponse({"error": "rate_limited"}, status=429)
                response["Retry-After"] = "900"
                return response
        except Exception:
            logger.error("Password reset rate limiter unavailable.")
            return JsonResponse({"error": "temporarily_unavailable"}, status=503)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        response = JsonResponse({"sent": True}) if self.json_response else HttpResponseRedirect(self.success_url)
        try:
            # Apply the same recipient limit whether or not that account exists.
            if limited("reset-email", form.cleaned_data["email"].strip().casefold(), 3, 3600):
                return response
            self.extra_email_context = {
                "base_url": settings.CRCON_PUBLIC_URL.rstrip("/"),
                "language": self.language,
                "timeout_minutes": ceil(settings.PASSWORD_RESET_TIMEOUT / 60),
            }
            # Force a configured origin; never derive recovery links from Host.
            form.save(
                domain_override=settings.CRCON_PUBLIC_URL.split("://", 1)[1].rstrip("/"),
                use_https=True,
                token_generator=self.token_generator,
                from_email=settings.DEFAULT_FROM_EMAIL,
                email_template_name=self.email_template_name,
                subject_template_name=self.subject_template_name,
                request=self.request,
                extra_email_context=self.extra_email_context,
            )
        except Exception:
            # No recipient, token, request body, or SMTP credentials in logs.
            logger.error("Password reset email delivery failed.")
        return response


@method_decorator(never_cache, name="dispatch")
@method_decorator(csrf_protect, name="dispatch")
@method_decorator(sensitive_post_parameters(), name="dispatch")
class AccountPasswordResetConfirmView(AccountJsonMixin, PasswordResetConfirmView):
    success_url = "/login?password_reset=1"

    def get_user(self, uidb64):
        user = super().get_user(uidb64)
        return user if user and user.is_active and user.has_usable_password() else None

    def get(self, request, *args, **kwargs):
        if not self.json_response:
            return HttpResponseRedirect("/reset-password/" + kwargs["uidb64"])
        return JsonResponse(password_settings(request))

    def render_to_response(self, context, **response_kwargs):
        # Django reaches this method for expired, reused or malformed tokens.
        if not self.json_response:
            return HttpResponseRedirect("/reset-password/" + self.kwargs["uidb64"])
        return JsonResponse({"error": "invalid_link"}, status=400)

    def form_valid(self, form):
        response = super().form_valid(form)
        return JsonResponse({"changed": True}) if self.json_response else response
