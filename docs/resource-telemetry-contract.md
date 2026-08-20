# Resource telemetry contract

The authenticated `get_system_usage` endpoint exposes a bounded operational
snapshot for administrators without multiplying host inspection work by the
number of open browser sessions.

## Truthful values

- `sampled_at`, `generated_at`, and `data_age_seconds` distinguish measurement
  time from response time.
- CPU and RAM prefer Linux cgroup v2 or v1 limits. Host values are used only
  when the installation has no finite container limit.
- The first container CPU sample is explicitly unavailable until a real usage
  delta exists. Missing metrics use `available: false` and `null`, never `0`.
- Every metric names its source and reports used, total, unit, percent, and an
  explainable severity.
- Warnings contain the metric, severity, stable code, and applied threshold.

## Sampling and polling budget

- Expensive inspection is sampled at most once every 15 seconds per web
  worker, independent of the number of connected administrators.
- Responses tell clients when to poll through `poll_after_seconds`.
- The admin client does not poll in a background tab and respects the endpoint
  cadence, with a ten-second lower safety bound.
- The sampler keeps at most 61 compact points, covering approximately 15
  minutes at the default cadence. It does not create a database write stream.
- Process enumeration uses the bounded PID list once per sample instead of
  materializing every process object for every browser request.

## Compatibility

Legacy `cpu_usage`, `ram_usage`, and `disk_usage` objects and their `percent`,
`used`, `total`, and CPU `cores` fields remain available. Schema version 2 adds
availability, source, unit, severity, timestamps, history, range, warning, and
polling metadata. The contract is game-independent and therefore identical for
HLL, HLL Vietnam, and multi-server installations.

The history is intentionally process-local. It is operational context, not an
accounting or billing record, and resets safely when a web worker restarts.
