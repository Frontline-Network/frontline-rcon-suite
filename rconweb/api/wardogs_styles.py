"""Wardogs accents shared by saved preferences and the standalone admin.

Pairs match the frontend colorStyles.js; covered by the color contract check.
"""

DEFAULT_WARDOGS_STYLE = "rose"
WARDOGS_STYLES = {
    "rose": {"accent": "#e45b80", "lightAccent": "#b72d58"},
    "blue": {"accent": "#61a9ee", "lightAccent": "#2368a6"},
    "emerald": {"accent": "#51bb99", "lightAccent": "#187553"},
    "amber": {"accent": "#dda44e", "lightAccent": "#875d12"},
    "violet": {"accent": "#b393f1", "lightAccent": "#7045b4"},
    "slate": {"accent": "#adb9cc", "lightAccent": "#56667d"},
}


def normalize_wardogs_style(value):
    if not isinstance(value, str) or value not in WARDOGS_STYLES:
        raise ValueError("Unsupported Wardogs color style.")
    return value
