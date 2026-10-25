"""Synthetic boundary and missing-evidence checks for read-only assessment."""

from copy import deepcopy
import unittest

from rcon import playtime_followup_reconstruction as module


def stamp(seconds):
    from datetime import datetime, timedelta

    return (datetime(2026, 10, 20, 12) + timedelta(seconds=seconds)).isoformat()


def fixture(join=90, leave=150, actual_end=100, stored_end=120):
    candidate = {
        "before": {
            "id": 1,
            "playersteamid_id": 7,
            "time_seconds": -50,
            "kills": 0,
            "deaths": 0,
            "teamkills": 0,
            "deaths_by_tk": 0,
        },
        "round": {
            "id": 2,
            "server_number": 3,
            "start": stamp(0),
            "end": stamp(stored_end),
        },
    }
    player = {
        "transitions": [
            {"id": 10, "event_time": stamp(join), "type": "CONNECTED"},
            {"id": 11, "event_time": stamp(leave), "type": "DISCONNECTED"},
        ],
        "sessions": [{"id": 30, "start": stamp(join), "end": stamp(leave)}],
    }
    markers = [
        {"id": 40, "event_time": stamp(0), "type": "MATCH START"},
        {"id": 41, "event_time": stamp(actual_end), "type": "MATCH ENDED"},
    ]
    if stored_end != actual_end:
        markers.append(
            {"id": 42, "event_time": stamp(stored_end), "type": "MATCH START"}
        )
    return candidate, player, markers, {"activity": []}


class ReconstructionTests(unittest.TestCase):
    def test_positive_clipped_to_actual_round(self):
        r = module.assess(*fixture())
        self.assertEqual((r["reason"], r["seconds"]), ("exact_positive", 10))

    def test_intermission_join_is_actual_zero(self):
        r = module.assess(*fixture(join=110))
        self.assertEqual((r["reason"], r["seconds"]), ("proven_zero", 0))

    def test_join_at_end_is_zero(self):
        self.assertEqual(module.assess(*fixture(join=100))["reason"], "proven_zero")

    def test_absent_join_does_not_prove_zero(self):
        self.assertEqual(
            module.assess(*fixture(join=130))["reason"], "zero_without_join_evidence"
        )

    def test_missing_round_end_rejected(self):
        c, p, m, d = fixture()
        m = [x for x in m if x["type"] != "MATCH ENDED"]
        self.assertEqual(module.assess(c, p, m, d)["reason"], "missing_match_end")

    def test_unconfirmed_intermission_rejected(self):
        c, p, m, d = fixture()
        m = m[:2]
        self.assertEqual(
            module.assess(c, p, m, d)["reason"], "unconfirmed_intermission"
        )

    def test_missing_disconnect_rejected(self):
        c, p, m, d = fixture()
        p["transitions"] = p["transitions"][:1]
        p["sessions"][0]["end"] = None
        self.assertEqual(module.assess(c, p, m, d)["reason"], "missing_disconnect")

    def test_stale_open_requires_pre_round_disconnect(self):
        c, p, m, d = fixture()
        p["sessions"].insert(0, {"id": 29, "start": stamp(-1000), "end": None})
        self.assertEqual(module.assess(c, p, m, d)["reason"], "unresolved_open_session")
        p["transitions"].insert(
            0, {"id": 9, "event_time": stamp(-20), "type": "DISCONNECTED"}
        )
        r = module.assess(c, p, m, d)
        self.assertEqual(r["reason"], "exact_positive")
        self.assertEqual(r["stale_sessions_disproved"][0]["disconnected_log_id"], 9)

    def test_repeated_connect_inside_round_rejected(self):
        c, p, m, d = fixture()
        p["transitions"].insert(
            0, {"id": 9, "event_time": stamp(10), "type": "CONNECTED"}
        )
        self.assertEqual(
            module.assess(c, p, m, d)["reason"], "connect_without_disconnect"
        )

    def test_exact_duplicate_events_deduplicated(self):
        c, p, m, d = fixture()
        p["transitions"].insert(1, deepcopy(p["transitions"][0]))
        self.assertEqual(module.assess(c, p, m, d)["seconds"], 10)

    def test_activity_outside_session_rejected(self):
        c, p, m, d = fixture()
        d["activity"] = [
            {
                "event_time": stamp(50),
                "type": "CHAT",
                "player1_steamid": 7,
                "player2_steamid": None,
            }
        ]
        self.assertEqual(
            module.assess(c, p, m, d)["reason"], "activity_outside_proven_connection"
        )

    def test_counter_disagreement_rejected(self):
        c, p, m, d = fixture()
        c["before"]["kills"] = 1
        self.assertEqual(
            module.assess(c, p, m, d)["reason"], "combat_count_disagreement"
        )

    def test_closed_session_must_match_raw_events(self):
        c, p, m, d = fixture()
        p["sessions"][0]["end"] = stamp(149)
        self.assertEqual(
            module.assess(c, p, m, d)["reason"], "closed_session_log_conflict"
        )

    def test_damaged_long_round_rejected(self):
        c, p, m, d = fixture()
        c["round"]["end"] = stamp(15000)
        self.assertEqual(
            module.assess(c, p, m, d)["reason"], "damaged_or_unusually_long_round"
        )


def manifest():
    records = []
    approved = []
    baseline = []
    groups = (
        (3, 183, 90, True),
        (3, 292, 110, True),
        (4, 24, 90, True),
        (4, 144, 110, True),
        (3, 396, 90, False),
        (4, 102, 90, False),
    )
    row_id = 0
    for server, count, join, supported in groups:
        for _ in range(count):
            row_id += 1
            c, p, m, d = fixture(join=join)
            c["before"].update(id=row_id, map_id=row_id, playersteamid_id=row_id)
            c["round"].update(id=row_id, server_number=server)
            p.update(server_number=server, playersteamid_id=row_id)
            for session in p["sessions"]:
                session["server_number"] = server
            if not supported:
                m = [e for e in m if e["type"] != "MATCH ENDED"]
            approved.append(module.assess(c, p, m, d))
            baseline.append(deepcopy(c["before"]))
            records.extend(
                (
                    {"section": "candidate", **c},
                    {"section": "player", **p},
                    {"section": "map", "map_id": row_id, "markers": m},
                    {"section": "detail", "id": row_id, **d},
                )
            )
    baseline.extend({"id": i, "time_seconds": 123} for i in range(5000, 8590))
    return {
        "records": records,
        "assessment": {"rows": approved},
        "before_scope": baseline,
    }


class ManifestTests(unittest.TestCase):
    def test_exact_authorized_selection_and_no_input_mutation(self):
        from scripts.repair_followup_playtimes import validate_manifest

        bundle = manifest()
        original = deepcopy(bundle)
        selected, scope = validate_manifest(bundle)
        self.assertEqual(len(selected), 643)
        self.assertEqual(len(scope), 4731)
        self.assertEqual(sum(r["reason"] == "proven_zero" for _, r, _ in selected), 436)
        self.assertEqual(bundle, original)

    def test_modified_proposal_is_rejected(self):
        from scripts.repair_followup_playtimes import validate_manifest

        bundle = manifest()
        bundle["assessment"]["rows"][0]["seconds"] = 999
        with self.assertRaisesRegex(AssertionError, "recalculation"):
            validate_manifest(bundle)

    def test_other_server_is_rejected(self):
        from scripts.repair_followup_playtimes import validate_manifest

        bundle = manifest()
        bundle["records"][0]["round"]["server_number"] = 1
        with self.assertRaisesRegex(AssertionError, "Unauthorized server"):
            validate_manifest(bundle)

    def test_changed_baseline_is_rejected(self):
        from scripts.repair_followup_playtimes import validate_manifest

        bundle = manifest()
        bundle["before_scope"][0]["time_seconds"] = 42
        with self.assertRaisesRegex(AssertionError, "Baseline disagrees"):
            validate_manifest(bundle)

    def test_missing_or_duplicate_approval_is_rejected(self):
        from scripts.repair_followup_playtimes import validate_manifest

        bundle = manifest()
        bundle["assessment"]["rows"][0] = bundle["assessment"]["rows"][1]
        with self.assertRaises(AssertionError):
            validate_manifest(bundle)

    def test_cross_server_sessions_cannot_corroborate(self):
        from scripts.repair_followup_playtimes import validate_manifest

        bundle = manifest()
        bundle["records"][1]["sessions"][0]["server_number"] = 4
        with self.assertRaises(AssertionError):
            validate_manifest(bundle)

    def test_zero_requires_zero_combat_and_preserves_all_other_fields(self):
        from scripts.repair_followup_playtimes import replacement

        p = {"kills": 0, "deaths": 0, "teamkills": 0, "deaths_by_tk": 0, "score": 42}
        r = {"reason": "proven_zero", "seconds": 0}
        self.assertEqual(
            replacement(p, r),
            {"time_seconds": 0, "kills_per_minute": 0.0, "deaths_per_minute": 0.0},
        )
        self.assertEqual(p["score"], 42)
        p["kills"] = 1
        with self.assertRaises(AssertionError):
            replacement(p, r)


if __name__ == "__main__":
    unittest.main()
