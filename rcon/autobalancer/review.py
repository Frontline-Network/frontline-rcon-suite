from __future__ import annotations

from typing import Any

SHADOW_REJECTION_CATEGORIES = {
    "squad_should_stay",
    "critical_role",
    "recent_join_or_move",
    "better_candidate",
    "skill_balance",
    "wrong_team_counts",
    "other",
}
SHADOW_STRATEGIES = {"squad-first", "balanced-v2", "skill-first"}


def validate_shadow_review(data: dict[str, Any]) -> tuple[
    str,
    str,
    str | None,
    str | None,
    str | None,
    str | None,
]:
    """Validate the admin calibration label without requiring Django state."""
    decision_id = str(data.get("decision_id") or "").strip()
    verdict = str(data.get("verdict") or "").strip().lower()
    category = str(data.get("category") or "").strip() or None
    comment = str(data.get("comment") or "").strip() or None
    preferred_strategy = str(data.get("preferred_strategy") or "").strip() or None
    preferred_player_id = str(data.get("preferred_player_id") or "").strip() or None
    if not decision_id:
        raise ValueError("decision_id fehlt")
    if verdict not in {"accepted", "rejected"}:
        raise ValueError("verdict muss accepted oder rejected sein")
    if verdict == "accepted":
        category = None
    elif category not in SHADOW_REJECTION_CATEGORIES:
        raise ValueError("Für eine Ablehnung ist ein gültiger Grund erforderlich")
    if comment and len(comment) > 1000:
        raise ValueError("Der Kommentar darf höchstens 1000 Zeichen lang sein")
    if preferred_strategy not in SHADOW_STRATEGIES | {None}:
        raise ValueError("preferred_strategy ist ungültig")
    if preferred_player_id and len(preferred_player_id) > 128:
        raise ValueError("preferred_player_id ist zu lang")
    return (
        decision_id,
        verdict,
        category,
        comment,
        preferred_strategy,
        preferred_player_id,
    )
