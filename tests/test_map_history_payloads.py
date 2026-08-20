import pytest

from rcon.map_history_payloads import build_map_history_summary


class FakeHistory:
    def __init__(self, records):
        self.records = records
        self.slices = []

    def __len__(self):
        return len(self.records)

    def __getitem__(self, index):
        self.slices.append(index)
        return self.records[index]


def map_record(name, *, start, end, guessed=False, match_time=0):
    return {
        "name": name,
        "start": start,
        "end": end,
        "guessed": guessed,
        "match_time": match_time,
        "player_stats": {"player": {"kills": 99}},
        "game_layout": {"requested": ["one"], "set": ["two"]},
        "cap_flips": [{"team": "allies"}],
    }


def test_summary_is_bounded_and_omits_nested_match_payloads():
    history = FakeHistory(
        [
            map_record("hue_warfare", start=100, end=None, match_time=1800),
            map_record("carentan_warfare", start=50, end=99, guessed=True),
            map_record("stalingrad_warfare", start=1, end=49),
        ]
    )

    result = build_map_history_summary(history, page=2, limit=2)

    assert result == {
        "page": 2,
        "page_size": 2,
        "total": 3,
        "has_more": False,
        "maps": [
            {
                "index": 2,
                "name": "stalingrad_warfare",
                "start": 1,
                "end": 49,
                "guessed": False,
                "match_time": 0,
            }
        ],
    }
    assert history.slices == [slice(2, 4)]
    assert "player_stats" not in result["maps"][0]
    assert "game_layout" not in result["maps"][0]
    assert "cap_flips" not in result["maps"][0]


def test_summary_preserves_hll_and_hllv_identifiers():
    history = FakeHistory(
        [
            map_record("carentan_warfare", start=1, end=2),
            map_record("hue_warfare", start=3, end=4),
        ]
    )

    result = build_map_history_summary(history, limit=2)

    assert [item["name"] for item in result["maps"]] == [
        "carentan_warfare",
        "hue_warfare",
    ]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("invalid", "limit must be a positive integer"),
        ("0", "limit must be a positive integer"),
        ("101", "limit must not exceed 100"),
    ],
)
def test_summary_rejects_invalid_or_unbounded_limits(value, message):
    history = FakeHistory([])

    with pytest.raises(ValueError, match=f"^{message}$"):
        build_map_history_summary(history, limit=value)

    assert history.slices == []


def test_summary_defaults_to_first_fifty_records():
    history = FakeHistory(
        [map_record(f"map_{index}", start=index, end=index + 1) for index in range(120)]
    )

    result = build_map_history_summary(history)

    assert result["page"] == 1
    assert result["page_size"] == 50
    assert result["total"] == 120
    assert result["has_more"] is True
    assert len(result["maps"]) == 50
    assert history.slices == [slice(0, 50)]
