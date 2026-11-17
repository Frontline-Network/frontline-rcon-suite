"""Explicit peer namespace for experimental durable Barricade scans.

Not connected to authentication or the websocket. A namespace must not be
inferred from a username, address or a shared bearer token alone.
"""
from urllib.parse import parse_qs
from uuid import UUID


def parse_integration_id(query_string: bytes) -> str | None:
    """Parse one explicitly supplied canonical integration UUID.

    None means the peer is not identified; it is not an anonymous namespace.
    API keys and bearer tokens are never included in the returned value.
    """
    if not isinstance(query_string, bytes):
        return None
    if len(query_string) > 2048:
        return None
    try:
        values = parse_qs(query_string.decode('utf-8'), keep_blank_values=True,
                          strict_parsing=True, max_num_fields=16).get('frontline_integration', [])
        if len(values) != 1:
            return None
        value = values[0]
        ident = UUID(value)
        if str(ident) != value:
            return None
    except (ValueError, UnicodeError):
        return None
    return str(ident)


def integration_namespace(query_string: bytes, *, server_number: int, credential_id: int | None) -> str | None:
    """Resolve only an administrator-registered key/peer binding.

    The caller must supply the ID of the already-authenticated key, not a value
    from the request. Registration and credential rotation require separate
    authorized management; peers cannot create their own bindings.
    """
    from sqlalchemy import select
    from rcon import barricade_scan_journal as journal

    ident = parse_integration_id(query_string)
    if ident is None or type(server_number) is not int or not 1 <= server_number <= 32:
        return None
    if type(credential_id) is not int or credential_id <= 0:
        return None
    with journal.get_session_maker()() as session:
        binding = session.scalar(select(journal.BarricadeScanIntegration).where(
            journal.BarricadeScanIntegration.server_number == server_number,
            journal.BarricadeScanIntegration.integration_id == ident,
            journal.BarricadeScanIntegration.credential_id == credential_id))
        return f'integration:{ident}' if binding is not None else None
