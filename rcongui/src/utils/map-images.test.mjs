import assert from "node:assert/strict";
import { readdirSync } from "node:fs";
import test from "node:test";

import {
  getLiveMapArtwork,
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

test("each shipped map resolves to the matching live-map artwork", () => {
  const names = readdirSync(new URL("../../../assets/images/tac-maps/", import.meta.url));
  const files = new Set(readdirSync(new URL("../../../assets/rcongui/live-maps/", import.meta.url)));
  for (const name of names.filter((file) => file.endsWith(".webp"))) {
    const id = name.slice(0, -5);
    const { image, headquarters, grid } = getLiveMapArtwork({ map: { id } });
    if (id.startsWith("wdev_")) {
      assert.equal(image, `/tac-maps/${name}`);
      assert.equal(headquarters, `/live-maps/${id}-hq.svg`);
      assert.ok(files.has(`${id}-hq.svg`));
      assert.equal(grid, false);
    } else {
      assert.equal(image, `/live-maps/${name}`);
      assert.ok(files.has(name));
      assert.equal(headquarters, null);
      assert.equal(grid, true);
    }
  }
  assert.deepEqual(getLiveMapArtwork({ map: { id: "future" } }),
    { image: "/tac-maps/future.webp", headquarters: null, grid: false });
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
