import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_WARDOGS_SHORTCUTS,
  normalizeWardogsShortcuts,
  resolveWardogsShortcuts,
  moveWardogsShortcut,
} from "./wardogs-shortcuts.mjs";

test("existing accounts get defaults but an intentionally empty rail stays empty", () => {
  assert.deepEqual(
    normalizeWardogsShortcuts(undefined),
    DEFAULT_WARDOGS_SHORTCUTS
  );
  assert.deepEqual(normalizeWardogsShortcuts([]), []);
});

test("preferences reject external or malformed routes and preserve unique order", () => {
  assert.deepEqual(
    normalizeWardogsShortcuts([
      "/views/live-map",
      "https://example.org",
      "//example.org",
      "/../login",
      "/views/live?token=x",
      false,
      "/records/players",
      "/views/live-map",
    ]),
    ["/views/live-map", "/records/players"]
  );
});

test("saved links never bypass current permissions and return when access is restored", () => {
  const saved = [
    "/views/live-map",
    "/records/players",
    "/retired",
    "/settings/game",
  ];
  const links = [
    { to: "/views/live-map", locked: true },
    { to: "/records/players", isAccessible: true },
    { to: "/settings/game", isAccessible: false },
  ];
  assert.deepEqual(
    resolveWardogsShortcuts(saved, links).map((link) => link.to),
    ["/records/players"]
  );
  links[0].locked = false;
  assert.deepEqual(
    resolveWardogsShortcuts(saved, links).map((link) => link.to),
    ["/views/live-map", "/records/players"]
  );
  assert.equal(saved.length, 4);
});

test("reordering keeps other positions and does not mutate saved preferences", () => {
  const saved = ["/views/live", "/views/live-map", "/records/players"];
  assert.deepEqual(moveWardogsShortcut(saved, "/views/live-map", -1), [
    "/views/live-map",
    "/views/live",
    "/records/players",
  ]);
  assert.deepEqual(moveWardogsShortcut(saved, "/views/live-map", 1), [
    "/views/live",
    "/records/players",
    "/views/live-map",
  ]);
  assert.deepEqual(moveWardogsShortcut(saved, "/views/live", -1), saved);
  assert.deepEqual(moveWardogsShortcut(saved, "/missing", 1), saved);
  assert.equal(saved[0], "/views/live");
});
