"""Experimental, explicitly bound CRCON protocol-version negotiation."""
import os

from django.contrib.auth.hashers import make_password

from rcon.barricade_scan_identity import integration_namespace, parse_integration_id
from rcon.utils import get_server_number
from rconweb.settings import SECRET_KEY

from .barricade_scan_auth import BARRICADE_PERMISSIONS
from .models import DjangoAPIKey

COMPATIBILITY_VERSION = 'v12.3.0'
REQUIRED_PERMISSIONS = BARRICADE_PERMISSIONS + ('api.can_view_player_profile',)


def authorized_peer(request) -> bool:
    """Fail closed unless the live API key is explicitly bound to this peer.

    This version identifies a narrow compatibility profile, not the installed
    Frontline release or a claim that all upstream CRCON behavior is present.
    """
    if any(os.getenv(flag) != '1' for flag in (
        'HLL_BARRICADE_DURABLE_SCANS', 'HLL_BARRICADE_JOURNAL_OBSERVATIONS',
        'HLL_BARRICADE_CRCON_COMPAT')):
        return False
    try:
        query = request.META.get('QUERY_STRING', '').encode('utf-8')
        ident = parse_integration_id(query)
        parts = request.META.get('HTTP_AUTHORIZATION', '').split()
        if ident is None or len(parts) != 2 or parts[0].upper() not in ('BEARER', 'BEARER:'):
            return False
        hashed = make_password(parts[1], salt=SECRET_KEY.replace('$', ''))
        key = DjangoAPIKey.objects.select_related('user').filter(api_key=hashed).first()
        user = key.user if key else None
        if not user or not user.is_active or not user.has_perms(REQUIRED_PERMISSIONS):
            return False
        namespace = integration_namespace(query, server_number=int(get_server_number()), credential_id=key.pk)
        return namespace == f'integration:{ident}'
    except Exception:
        # A missing binding, malformed input or database failure is not proof
        # of compatibility. Never log keys or database connection details.
        return False
