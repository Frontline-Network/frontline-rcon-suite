"""HLL Vietnam roles, keyed by the values returned by RCON."""

import hllrcon


HLLV_ROLES: frozenset[str] = frozenset(
    role.name.lower() for role in hllrcon.HLLVRole.all()
)
HLLV_ROLE_LABELS: dict[str, str] = {
    role.name.lower(): role.pretty_name for role in hllrcon.HLLVRole.all()
}

__all__ = ["HLLV_ROLES", "HLLV_ROLE_LABELS"]
