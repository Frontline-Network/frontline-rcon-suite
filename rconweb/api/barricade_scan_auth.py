"""Revalidate a Barricade credential for each durable outbound scan."""
from .models import DjangoAPIKey

BARRICADE_PERMISSIONS = (
    'api.can_view_blacklists',
    'api.can_create_blacklists',
    'api.can_add_blacklist_records',
    'api.can_change_blacklist_records',
    'api.can_delete_blacklist_records',
)


def current_credential_is_authorized(credential_id: int) -> bool:
    if type(credential_id) is not int or credential_id <= 0:
        return False
    try:
        key = DjangoAPIKey.objects.select_related('user').get(pk=credential_id)
    except DjangoAPIKey.DoesNotExist:
        return False
    user = key.user
    return bool(user and user.is_active and user.has_perms(BARRICADE_PERMISSIONS))
