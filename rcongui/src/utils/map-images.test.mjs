import assert from "node:assert/strict";
import test from "node:test";

import {
  getMapIconSrc,
  getMapImageSrc,
  getTacticalMapImageSrc,
  resolveMapImageName,
  resolveTacticalMapImageName,
} from "./map-images.mjs";

test("resolves every HLLV map from current and legacy map identifiers", () => {
  for (const [suffix, mapId] of [
    ["a", "WDEV_A"],
    ["b", "WDEV_B"],
    ["c", "WDEV_C"],
    ["d", "WDEV_D"],
    ["e", "WDEV_E"],
    ["f", "WDEV_F"],
  ]) {
    assert.equal(
      resolveMapImageName({ id: `wdev${suffix}_warfare_day` }),
      `wdev_${suffix}-day.webp`
    );
    assert.equal(
      resolveMapImageName({ map: { id: mapId } }),
      `wdev_${suffix}-day.webp`
    );
  }
});

test("replaces an unknown API image with the matching HLLV artwork", () => {
  const layer = {
    image_name: "unknown-day.webp",
    pretty_name: "Cam Ranh Port Warfare",
  };

  assert.equal(resolveMapImageName(layer), "wdev_e-day.webp");
  assert.equal(getMapImageSrc(layer), "/maps/wdev_e-day.webp");
  assert.equal(getMapIconSrc(layer), "/maps/icons/wdev_e-day.webp");
});

test("matches localized HLLV names and preserves non-HLLV images", () => {
  assert.equal(
    resolveMapImageName({ map: { pretty_name: "Quảng Ngãi" } }),
    "wdev_b-day.webp"
  );
  assert.equal(
    resolveMapImageName({ map: { pretty_name: "Đăk Tô Airfield" } }),
    "wdev_d-day.webp"
  );
  assert.equal(
    resolveMapImageName({ image_name: "foy-night.webp" }),
    "foy-night.webp"
  );
});

test("resolves dedicated tactical artwork for every HLLV map", () => {
  for (const [suffix, mapName] of [
    ["a", "Vạn Tường"],
    ["b", "Quảng Ngãi"],
    ["c", "Huế Outskirts"],
    ["d", "Đăk Tô Airfield"],
    ["e", "Cam Ranh Port"],
    ["f", "Thanh Hòa Bridge"],
  ]) {
    assert.equal(
      resolveTacticalMapImageName({
        map: { id: `WDEV_${suffix.toUpperCase()}` },
      }),
      `wdev_${suffix}.webp`
    );
    assert.equal(
      getTacticalMapImageSrc({ map: { pretty_name: mapName } }),
      `/tac-maps/wdev_${suffix}.webp`
    );
  }
});

test("preserves the existing tactical-map naming for non-HLLV maps", () => {
  const layer = { map: { id: "carentan" } };

  assert.equal(resolveTacticalMapImageName(layer), "carentan.webp");
  assert.equal(getTacticalMapImageSrc(layer), "/tac-maps/carentan.webp");
});
