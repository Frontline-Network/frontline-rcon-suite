import { test } from "node:test";
import assert from "node:assert/strict";
import { highlightReleaseForChannel } from "./highlight-release.mjs";

const hotfix = { tag_name: "v0.9.1", current: true, highlights: null };
const feature = {
  tag_name: "v0.9.0",
  current: false,
  highlights: { schema_version: 1 },
};
const channel = {
  status: "ready",
  releases: [hotfix, feature],
  highlight_state: { release_version: "v0.9.0", seen: false },
};

test("hotfix selects original spotlight without relabelling the installed release", () => {
  assert.equal(highlightReleaseForChannel(channel), feature);
  assert.equal(
    channel.releases.find((release) => release.current),
    hotfix
  );
});
test("seen and snoozed spotlights remain available for manual reopening", () => {
  for (const state of [
    { seen: true },
    { seen: false, auto_show: false, snoozed_until: "2030-01-01" },
  ]) {
    assert.equal(
      highlightReleaseForChannel({
        ...channel,
        highlight_state: { ...channel.highlight_state, ...state },
      }),
      feature
    );
  }
});
test("equivalent version tags share the backend's canonical identity", () => {
  const equivalent = { ...feature, tag_name: "0.9.0" };
  assert.equal(
    highlightReleaseForChannel({ ...channel, releases: [hotfix, equivalent] }),
    equivalent
  );
});
test("unverified channel, absent state and unavailable metadata fail closed", () => {
  for (const value of [
    null,
    { ...channel, status: "version_mismatch" },
    { ...channel, highlight_state: null },
    { ...channel, releases: [hotfix] },
    { ...channel, releases: null },
    { ...channel, highlight_state: { release_version: "v0.8.8" } },
  ]) {
    assert.equal(highlightReleaseForChannel(value), null);
  }
});
