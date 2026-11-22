"""Parse explicitly supplied VIP deadlines without filling in today's date."""
from datetime import datetime, timezone

from dateutil import parser


class InvalidVipExpiration(ValueError):
    """The supplied VIP deadline cannot be used for a grant."""


def parse_vip_expiration(value: str) -> datetime:
    if not isinstance(value, str):
        raise InvalidVipExpiration("Invalid VIP expiration date")
    try:
        # Keep legacy dateutil formats, but require an explicit year, month and day.
        # An incomplete date depends on the default used to fill its missing fields.
        first = parser.parse(value, default=datetime(2000, 1, 1))
        second = parser.parse(value, default=datetime(2004, 7, 15))
        if first.date() != second.date():
            raise ValueError("Incomplete date")
        if first.tzinfo is None:
            return first.replace(tzinfo=timezone.utc)
        return first.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise InvalidVipExpiration("Invalid VIP expiration date") from exc
