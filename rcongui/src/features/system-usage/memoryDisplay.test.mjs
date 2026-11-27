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
  reclaimable_bytes: 512 * MiB,
  working_set_bytes: GiB,
  components: [
    { service: "backend", scope: "dedicated", used_bytes: 256 * MiB },
  ],
};

test("RCON total uses absolute charge without inventing a percentage or stack limit", () => {
  const display = rconMemoryDisplay(aggregate, t, "en");
  assert.equal(display.available, true);
  assert.equal(display.value, "1.5 GiB");
  assert.equal(display.dedicated, "640 MiB");
  assert.equal(display.shared, "896 MiB");
  assert.equal(display.reclaimable, "512 MiB");
  assert.equal(display.workingSet, "1 GiB");
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
    assert.equal(display.reclaimable, null);
    assert.deepEqual(display.components, []);
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

test("unknown optional cache fields are absent; known zero cache remains visible", () => {
  const missing = rconMemoryDisplay(
    { ...aggregate, reclaimable_bytes: undefined, working_set_bytes: null },
    t,
    "en"
  );
  assert.equal(missing.reclaimable, null);
  assert.equal(missing.workingSet, null);
  assert.equal(
    rconMemoryDisplay({ ...aggregate, reclaimable_bytes: 0 }, t, "en")
      .reclaimable,
    "0 MiB"
  );
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
      { ram_percent: 90 },
      { rcon_ram_used_bytes: 512 * MiB },
      { rcon_ram_used_bytes: null },
      { rcon_ram_used_bytes: 1.5 * GiB },
      { rcon_ram_used_bytes: -1 },
      { rcon_ram_used_bytes: Infinity },
    ],
    "en"
  );
  assert.equal(history.unit, "GiB");
  assert.deepEqual(history.data, [null, 0.5, null, 1.5, null, null]);
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
    memoryHistoryDisplay([{ rcon_ram_used_bytes: 512 * MiB }], "en").unit,
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
