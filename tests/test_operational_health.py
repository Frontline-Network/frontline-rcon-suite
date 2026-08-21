from datetime import datetime, timedelta, timezone

from rcon.operational_health import RconLatencyTracker


def test_rcon_latency_tracker_keeps_only_recent_bounded_samples():
    tracker = RconLatencyTracker(max_samples=2)
    tracker.record(0.012, failed=False)
    tracker.record(0.034, failed=True)
    tracker.record(0.056, failed=False)

    snapshot = tracker.snapshot(window_seconds=60)

    assert len(snapshot["history"]) == 2
    assert snapshot["latency_ms"] == 45
    assert snapshot["failure_count"] == 1
    assert snapshot["state"] == "degraded"


def test_rcon_latency_tracker_ignores_expired_samples():
    tracker = RconLatencyTracker()
    tracker._samples.append(
        {
            "sampled_at": (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat(),
            "latency_ms": 99,
            "failed": False,
        }
    )

    snapshot = tracker.snapshot(window_seconds=60)

    assert snapshot["state"] == "unknown"
    assert snapshot["history"] == []
