import assert from "node:assert/strict";
import {
  inspectConfigCompatibility,
  mergeConfigWithSchema,
} from "../src/pages/settings/config-form/configCompatibility.mjs";

const schema = {
  type: "object",
  $defs: {
    delivery: {
      type: "object",
      properties: {
        url: { type: "string" },
      },
    },
  },
  properties: {
    enabled: { type: "boolean" },
    delivery: {
      anyOf: [{ type: "null" }, { $ref: "#/$defs/delivery" }],
    },
    hooks: {
      type: "array",
      items: { type: "object" },
    },
    commands: {
      type: "object",
      additionalProperties: true,
    },
  },
};

const existing = {
  enabled: true,
  legacy_threshold: 42,
  delivery: {
    url: "https://discord.example/old",
    retry_policy: "exponential",
  },
  hooks: [{ url: "https://discord.example/one" }],
  commands: { old: { command: "punish" } },
};

const merged = mergeConfigWithSchema(
  existing,
  {
    enabled: false,
    delivery: { url: "https://discord.example/new" },
    hooks: [{ url: "https://discord.example/two" }],
    commands: { new: { command: "kick" } },
  },
  schema
);

assert.equal(merged.enabled, false);
assert.equal(merged.legacy_threshold, 42);
assert.equal(merged.delivery.url, "https://discord.example/new");
assert.equal(merged.delivery.retry_policy, "exponential");
assert.deepEqual(merged.hooks, [{ url: "https://discord.example/two" }]);
assert.deepEqual(merged.commands, { new: { command: "kick" } });
assert.deepEqual(JSON.parse(JSON.stringify(merged)), merged);
assert.deepEqual(inspectConfigCompatibility(existing, schema), []);
assert.deepEqual(
  inspectConfigCompatibility(
    { ...existing, hooks: "https://discord.example/not-a-list" },
    schema
  ),
  [
    {
      path: "hooks",
      expectedType: "array",
      actualType: "string",
    },
  ]
);

console.log(
  "Config compatibility contract passed: unknown values survive guided edits."
);
