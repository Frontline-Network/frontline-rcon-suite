"""Bounded, passive operational telemetry for the administrator health view."""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone


class RconLatencyTracker:
    """Record timings from existing RCON requests without issuing probes."""

    def __init__(self, max_samples: int = 241):
        self._samples: deque[dict] = deque(maxlen=max_samples)
        self._lock = threading.Lock()

    def record(self, duration_seconds: float, *, failed: bool) -> None:
        with self._lock:
            self._samples.append(
                {
                    "sampled_at": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": max(0, round(duration_seconds * 1000)),
                    "failed": bool(failed),
                }
            )

    def snapshot(self, *, window_seconds: int) -> dict:
        cutoff = time.time() - window_seconds
        with self._lock:
            samples = [
                sample
                for sample in self._samples
                if datetime.fromisoformat(sample["sampled_at"]).timestamp() >= cutoff
            ]
        latencies = [sample["latency_ms"] for sample in samples]
        return {
            "state": "unknown" if not samples else "degraded" if any(sample["failed"] for sample in samples) else "healthy",
            "last_checked_at": samples[-1]["sampled_at"] if samples else None,
            "latency_ms": round(sum(latencies) / len(latencies)) if latencies else None,
            "failure_count": sum(sample["failed"] for sample in samples),
            "history": samples,
        }


rcon_latency_tracker = RconLatencyTracker()
