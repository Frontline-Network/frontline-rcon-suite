import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "locales");
const flatten = (object, prefix = "") => Object.fromEntries(
  Object.entries(object).flatMap(([key, value]) =>
    value && typeof value === "object"
      ? Object.entries(flatten(value, `${prefix}${key}.`))
      : [[`${prefix}${key}`, value]],
  ),
);
const markers = (text) => [...text.matchAll(/\{\{\s*[^}]+\s*\}\}|\$t\([^)]+\)|<\/?[\w]+\s*\/?\s*>/g)]
  .map(([marker]) => marker.replace(/\s+/g, ""))
  .sort();

test("French public catalogs cover English keys and retain template markers", () => {
  const files = fs.readdirSync(path.join(root, "en")).filter((name) => name.endsWith(".json"));
  assert.ok(files.length > 0);
  for (const file of files) {
    const english = flatten(JSON.parse(fs.readFileSync(path.join(root, "en", file), "utf8")));
    const french = flatten(JSON.parse(fs.readFileSync(path.join(root, "fr", file), "utf8")));
    for (const [key, value] of Object.entries(english)) {
      assert.ok(Object.hasOwn(french, key), `${file}: missing French ${key}`);
      assert.equal(typeof french[key], typeof value, `${file}: type mismatch for ${key}`);
      if (typeof value === "string") {
        if (value.trim()) assert.ok(french[key].trim(), `${file}: empty French ${key}`);
        assert.deepEqual(markers(french[key]), markers(value), `${file}: markers differ for ${key}`);
      }
    }
  }
});
