import test from "node:test";
import assert from "node:assert/strict";
import {
  formatMemorySize,
  memoryBytes,
  memoryDisplay,
  memoryHistoryDisplay,
  rconMemoryDisplay,
} from "./memoryDisplay.js";

const MiB = 1024 ** 2;
const GiB = 1024 ** 3;
const t = (key, options) =>
  options ? `${key}: ${options.used} / ${options.total}` : key;
const aggregate = {
  available: true,
  source: "rcon_services",
  used_bytes: 1.5 * GiB,
  total: null,
  percent: null,
  dedicated_used_bytes: 640 * MiB,
  shared_used_bytes: 896 * MiB,
  service_ram_available: true,
  service_used_bytes: GiB,
  dedicated_service_used_bytes: 384 * MiB,
  shared_service_used_bytes: 640 * MiB,
  file_cache_bytes: 512 * MiB,
  reclaimable_bytes: 512 * MiB,
  working_set_bytes: GiB,
  components: [
    { service: "backend", scope: "dedicated", used_bytes: 256 * MiB },
  ],
};

test("instance RAM uses only dedicated services; the full group stays separate", () => {
  const display = rconMemoryDisplay(aggregate, t, "en");
  assert.equal(display.available, true);
  assert.equal(display.label, "dashboard.resources.instanceRam");
  assert.equal(display.value, "384 MiB");
  assert.equal(display.totalValue, undefined);
  assert.equal(display.serviceValue, "1 GiB");
  assert.equal(display.dedicated, "384 MiB");
  assert.equal(display.shared, "640 MiB");
  assert.equal(display.fileCache, undefined);
  assert.equal(display.reclaimable, undefined);
  assert.equal(display.workingSet, undefined);
  assert.equal(display.components.length, 1);
  assert.equal(display.percent, undefined);
  assert.equal(display.capacity, undefined);
});

test("unavailable, missing, invalid and host metrics cannot masquerade as the RCON total", () => {
  for (const metric of [
    undefined,
    null,
    {},
    { ...aggregate, available: false },
    { ...aggregate, source: "host", used: 32, unit: "GiB" },
    { ...aggregate, source: "cgroup_v2" },
    { ...aggregate, used_bytes: -1 },
    { ...aggregate, used_bytes: NaN },
  ]) {
    const display = rconMemoryDisplay(metric, t, "en");
    assert.equal(display.available, false);
    assert.equal(display.value, null);
    assert.equal(display.totalValue, undefined);
    assert.equal(display.reclaimable, undefined);
    assert.deepEqual(display.components, []);
  }
});

test("665 MiB of dedicated services cannot be confused with a 10 GiB shared service group", () => {
  const display = rconMemoryDisplay(
    {
      ...aggregate,
      dedicated_used_bytes: 690 * MiB,
      shared_used_bytes: 9959 * MiB,
      used_bytes: 10649 * MiB,
      dedicated_service_used_bytes: 665 * MiB,
      shared_service_used_bytes: 1.35 * GiB,
      service_used_bytes: 665 * MiB + 1.35 * GiB,
      file_cache_bytes: 8.4 * GiB,
      reclaimable_bytes: 7 * GiB,
    },
    t,
    "de"
  );
  assert.equal(display.value, "665 MiB");
  assert.equal(display.shared, "1,35 GiB");
  assert.equal(display.serviceValue, "2 GiB");
  assert.equal(display.totalValue, undefined);
  assert.equal(display.fileCache, undefined);
  assert.equal(display.reclaimable, undefined);
});

test("missing cache measurements never fall back to raw charge or the inactive-file working set", () => {
  for (const extra of [
    { service_ram_available: false },
    { service_ram_available: undefined },
    { dedicated_service_used_bytes: null },
    { shared_service_used_bytes: -1 },
    { file_cache_bytes: null },
  ]) {
    const display = rconMemoryDisplay({ ...aggregate, ...extra }, t, "en");
    assert.equal(display.available, false);
    assert.equal(display.value, null);
    assert.equal(display.serviceValue, null);
    assert.equal(display.shared, null);
    assert.equal(display.totalValue, undefined);
    assert.equal(display.workingSet, undefined);
  }
});

test("stale samples hide current values while preserving an explicit stale explanation", () => {
  for (const [metric, options] of [
    [aggregate, { stale: true }],
    [{ ...aggregate, reason: "stale" }, {}],
  ]) {
    const display = rconMemoryDisplay(metric, t, "de", options);
    assert.equal(display.available, false);
    assert.equal(display.value, null);
    assert.equal(
      display.unavailableText,
      "dashboard.resources.rconMemoryStale"
    );
  }
});

test("display values never expose full charge, cache or inactive-file working-set numbers", () => {
  const missing = rconMemoryDisplay(
    { ...aggregate, reclaimable_bytes: undefined, working_set_bytes: null },
    t,
    "en"
  );
  assert.equal(missing.reclaimable, undefined);
  assert.equal(missing.workingSet, undefined);
  assert.equal(missing.totalValue, undefined);
  assert.equal(missing.fileCache, undefined);
  assert.equal(missing.value, "384 MiB");
});

test("size formatting uses locale and binary units without displaying invalid numbers", () => {
  assert.equal(formatMemorySize(1.5 * GiB, "de"), "1,5 GiB");
  assert.equal(formatMemorySize(1.5 * GiB, "en"), "1.5 GiB");
  assert.equal(formatMemorySize(1.5 * GiB, "fr"), "1,5 GiB");
  assert.equal(formatMemorySize(256.25 * MiB, "en"), "256.3 MiB");
  assert.equal(formatMemorySize(0, "en"), "0 MiB");
  for (const value of [undefined, null, -1, NaN, Infinity, "256"]) {
    assert.equal(formatMemorySize(value, "en"), null);
  }
  assert.equal(
    memoryBytes({ used_bytes: 256 * MiB, used: 100, unit: "GiB" }),
    256 * MiB
  );
});

test("RCON history only uses absolute byte samples and preserves missing gaps", () => {
  const history = memoryHistoryDisplay(
    [
      { ram_percent: 90, rcon_ram_used_bytes: 10 * GiB },
      {
        rcon_service_ram_used_bytes: 512 * MiB,
        rcon_dedicated_ram_used_bytes: 256 * MiB,
        rcon_shared_ram_used_bytes: 256 * MiB,
      },
      { rcon_service_ram_used_bytes: null, rcon_ram_used_bytes: 10 * GiB },
      {
        rcon_service_ram_used_bytes: 1.5 * GiB,
        rcon_dedicated_ram_used_bytes: 0.5 * GiB,
        rcon_shared_ram_used_bytes: GiB,
      },
      { rcon_service_ram_used_bytes: -1 },
      { rcon_service_ram_used_bytes: Infinity },
    ],
    "en"
  );
  assert.equal(history.unit, "GiB");
  assert.deepEqual(history.data, [null, 0.5, null, 1.5, null, null]);
  assert.deepEqual(history.dedicated, [null, 0.25, null, 0.5, null, null]);
  assert.deepEqual(history.shared, [null, 0.25, null, 1, null, null]);
  assert.equal(history.minimum, "512 MiB");
  assert.equal(history.maximum, "1.5 GiB");
  assert.equal(history.available, true);
  assert.deepEqual(memoryHistoryDisplay([{ ram_percent: 40 }], "en").data, [
    null,
  ]);
  assert.equal(
    memoryHistoryDisplay([{ ram_percent: 40 }], "en").available,
    false
  );
  assert.equal(
    memoryHistoryDisplay([{ rcon_service_ram_used_bytes: 512 * MiB }], "en")
      .unit,
    "MiB"
  );
});

test("backend capacity remains explicitly secondary and labeled as backend RAM", () => {
  const backend = memoryDisplay(
    {
      available: true,
      source: "cgroup_v2",
      percent: 25,
      used_bytes: 256 * MiB,
      total_bytes: GiB,
    },
    t,
    "en"
  );
  assert.equal(backend.label, "dashboard.resources.containerRam");
  assert.equal(
    backend.capacity,
    "dashboard.resources.memoryCapacity: 256 MiB / 1 GiB"
  );
});
