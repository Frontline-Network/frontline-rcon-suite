import assert from "node:assert/strict";
import test from "node:test";
import { zoomCamera, wheelZoomFactor } from "./interaction.mjs";

test("zoom keeps the pointed-to world position fixed, including at limits", () => {
  const camera = { x: -0.3, y: 0.2, scale: 2 };
  const anchor = { x: 0.7, y: 0.35 };
  for (const factor of [0.001, 0.5, 1.3, 100]) {
    const next = zoomCamera(camera, factor, anchor);
    assert.ok(next.scale >= 1 && next.scale <= 8);
    for (const axis of ["x", "y"]) {
      const before = (anchor[axis] - camera[axis]) / camera.scale;
      const after = (anchor[axis] - next[axis]) / next.scale;
      assert.ok(Math.abs(before - after) < 1e-12);
    }
  }
});

test("zoom buttons stay centered and wheel modes are normalized and bounded", () => {
  assert.deepEqual(zoomCamera({ x: 0, y: 0, scale: 1 }, 2), {
    x: -0.5,
    y: -0.5,
    scale: 2,
  });
  assert.equal(wheelZoomFactor(0), 1);
  assert.ok(wheelZoomFactor(-120) > 1);
  assert.ok(wheelZoomFactor(120) < 1);
  assert.equal(wheelZoomFactor(3, 1), wheelZoomFactor(48));
  assert.equal(wheelZoomFactor(0.5, 2, 800), wheelZoomFactor(400));
  assert.equal(wheelZoomFactor(-10000), wheelZoomFactor(-600));
});
