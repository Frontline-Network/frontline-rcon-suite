from datetime import datetime, timezone

import pytest

from rcon.autobalancer import snapshot


@pytest.mark.parametrize(
    ("current", "recorded", "started", "expected"),
    [
        ("unknown", "foy", 1000, False),
        ("foy", None, 1000, False),
        ("foy", "omaha", 1000, False),
        ("foy", "foy", 3000, False),
        ("foy", "foy", float("nan"), False),
        ("foy", "foy", 1000, True),
    ],
)
def test_stable_map_requires_matching_known_map_and_valid_start(monkeypatch, current, recorded, started, expected):
    monkeypatch.setattr(snapshot, "MapsHistory", lambda **_: [{"name": recorded, "start": started}])
    _, _, stable = snapshot._current_round(current, datetime.fromtimestamp(2000, timezone.utc))
    assert stable is expected
