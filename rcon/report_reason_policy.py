"""Rejection guards for AI interpretations, never a keyword sanction fallback."""

import re

from rcon.admin_incidents import _normalize_message

# A model once misread reports of Nazi slogans in voice chat as voice silence.
# These terms can only STOP a communication kick. The model still reads the
# complete complaint; absence of a match does not authorize any action.
OTHER_COMMUNICATION_COMPLAINT = re.compile(
    r"\b(?:ns(?:dap)?|hh|nazi\w*|neo ?nazi\w*|heil hitler|sieg heil|"
    r"rassis\w*|racis\w*|antisemit\w*|anti semit\w*|hate speech|"
    r"hassrede\w*|volksverhetz\w*|beleidig\w*|insult\w*|slurs?|"
    r"droh\w*|bedroh\w*|threat\w*|death threats?)\b"
)


def interpretation_failure(incident, decision):
    """Return the actual routing failure before attempting identity resolution."""
    if decision.rule == "manual":
        return "manual_review_required"
    if not decision.unambiguous or decision.uncertainties:
        return "interpretation_uncertain"
    body = re.sub(
        r"^\s*!admin\b", "", str(incident.get("raw_message") or ""), count=1, flags=re.I
    )
    if (
        decision.target_kind == "none"
        or not decision.target_text.strip()
        or not decision.allegation_excerpt.strip()
        or decision.target_text not in body
        or decision.allegation_excerpt not in body
        or "!admin" in decision.target_text.casefold()
        or decision.allegation_excerpt.strip() == decision.target_text.strip()
        or (decision.rule != "communication" and decision.target_kind != "player")
    ):
        return "ungrounded_interpretation"
    if decision.rule == "communication":
        # A handle such as 'NaziHunter' is not itself an allegation. Remove only
        # the selected reference, once; retain the rest of the complete report.
        complaint = body.replace(decision.target_text, " ", 1)
        if OTHER_COMMUNICATION_COMPLAINT.search(_normalize_message(complaint)):
            return "communication_category_conflict"
    return None
