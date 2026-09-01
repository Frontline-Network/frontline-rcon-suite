import assert from "node:assert/strict";
import test from "node:test";

import {
  getMapIconSrc,
  getMapImageSrc,
  resolveMapImageName,
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
