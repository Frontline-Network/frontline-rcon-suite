"""Provisional language defaults from an account's cached public Steam country."""
import re
from datetime import timezone
from sqlalchemy import select, or_
from rcon.models import PlayerID, SteamInfo

# Defaults, not evidence of a person's spoken language. Deliberately omit
# multilingual countries such as CH, BE, CA, LU, IN, SG and ZA.
COUNTRY_LANGUAGES = {
    "DE": "de", "AT": "de", "LI": "de",
    "GB": "en", "US": "en", "AU": "en", "NZ": "en", "IE": "en",
    "FR": "fr", "MC": "fr",
    "PL": "pl", "NL": "nl", "IT": "it", "ES": "es", "PT": "pt", "BR": "pt",
    "CZ": "cs", "SK": "sk", "HU": "hu", "RO": "ro", "BG": "bg",
    "DK": "da", "SE": "sv", "NO": "nb", "FI": "fi", "IS": "is",
    "EE": "et", "LV": "lv", "LT": "lt", "GR": "el",
    "TR": "tr", "UA": "uk", "RU": "ru", "HR": "hr", "SI": "sl",
    "JP": "ja", "KR": "ko", "TH": "th", "VN": "vi", "ID": "id",
    "AR": "es", "CL": "es", "CO": "es", "MX": "es", "PE": "es",
}


def steam_account_id(value):
    value = str(value or "")
    return value if re.fullmatch(r"7656119[0-9]{10}", value) else None


def country_hint(sess, player_id):
    if not player_id:
        return None
    spellings = [player_id]
    if re.fullmatch(r"[0-9a-f]{32}", player_id):
        spellings.append(player_id.upper())
    records = sess.execute(select(PlayerID.id, PlayerID.player_id, PlayerID.steam_id)
                           .where(PlayerID.player_id.in_(spellings))).all()
    identities = {steam_account_id(row.player_id) or steam_account_id(row.steam_id)
                  for row in records}
    identities.discard(None)
    if len(identities) != 1:
        return None
    steam_id = identities.pop()
    account_ids = select(PlayerID.id).where(or_(
        PlayerID.id.in_([row.id for row in records]), PlayerID.player_id == steam_id))
    profiles = sess.execute(select(SteamInfo.profile, SteamInfo.updated)
                            .where(SteamInfo.player_id_id.in_(account_ids))
                            .order_by(SteamInfo.updated.desc().nullslast(), SteamInfo.id.desc())
                            .limit(4)).all()
    for profile, updated in profiles:
        if not isinstance(profile, dict) or profile.get("steamid") != steam_id:
            continue
        # Missing/private country in the newest matching response must not
        # resurrect an older country, including the denormalized country field.
        country = str(profile.get("loccountrycode") or "").upper()
        language = COUNTRY_LANGUAGES.get(country)
        if not language:
            return None
        updated = updated.replace(tzinfo=timezone.utc) if updated and updated.tzinfo is None else updated
        return {"language": language, "country": country, "explicit": False,
                "source": "steam_country", "updated": updated.timestamp() if updated else None}
    return None
