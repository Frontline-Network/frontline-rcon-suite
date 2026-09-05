import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

const mapCanvas = (page) =>
  page.getByRole("group", {
    name: "Taktische Karte mit auswählbaren Spielern",
  });
const cameraMatrix = (page) =>
  page.getByTestId("map-camera").evaluate((node) => {
    const m = node.transform.baseVal.consolidate().matrix;
    return { x: m.e, y: m.f, scale: m.a };
  });
const dragFrom = async (page, point, dx = 60, dy = 30) => {
  await page.mouse.move(point.x, point.y);
  await page.mouse.down();
  await page.mouse.move(point.x + dx, point.y + dy, { steps: 8 });
  await page.mouse.up();
};

test("zoom never reveals unselected names, pointer and keyboard selection still work", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live-map");
  const marker = page.locator('[data-player-id="demo-55"]');
  await expect(page.getByTestId("player-map-marker")).toHaveCount(100);
  await expect(page.getByLabel("Namen bei Zoom")).toHaveCount(0);
  await expect(page.getByTestId("player-map-name")).toHaveCount(0);
  await marker.click();
  await expect(marker).toHaveCSS("outline-style", "none");
  await expect(page.getByTestId("player-map-nameplate")).toHaveAttribute(
    "stroke-width",
    "1"
  );
  await expect(page.getByTestId("player-map-name")).not.toHaveAttribute(
    "stroke"
  );
  await expect(page.getByTestId("player-map-nameplate")).not.toHaveAttribute(
    "rx"
  );
  await expect(marker.locator("[data-marker-focus-ring]")).toHaveCSS(
    "opacity",
    "0"
  );
  await expect(page.getByTestId("player-map-name")).toHaveText(
    "Demo Spieler 56"
  );
  for (let i = 0; i < 3; i++)
    await page.getByRole("button", { name: "Vergrößern", exact: true }).click();
  await expect(page.getByTestId("player-map-name")).toHaveCount(1);
  const other = page.locator('[data-player-id="demo-56"]');
  await other.focus();
  await other.press("Enter");
  await expect(other.locator("[data-marker-focus-ring]")).toHaveCSS(
    "opacity",
    "1"
  );
  await expect(page.getByTestId("player-map-name")).toHaveText(
    "Demo Spieler 57"
  );
  await expect(marker).toHaveAttribute("aria-pressed", "false");
  await mapCanvas(page).screenshot({
    path: "test-results/live-map-compact-selection.png",
  });
});

test("wheel zoom is pointer anchored and never scrolls the page", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live-map");
  const canvas = mapCanvas(page);
  await expect(page.getByTestId("player-map-marker")).toHaveCount(100);
  await canvas.scrollIntoViewIfNeeded();
  const point = await canvas.evaluate((node) => {
    const p = node.createSVGPoint();
    p.x = 620;
    p.y = 420;
    const s = p.matrixTransform(node.getScreenCTM());
    // Native wheel coordinates use CSS-pixel integers; compare that exact anchor.
    return { x: Math.round(s.x), y: Math.round(s.y) };
  });
  const worldUnderPointer = () =>
    canvas.evaluate((node, coords) => {
      const p = node.createSVGPoint();
      p.x = coords.x;
      p.y = coords.y;
      const world = p.matrixTransform(
        node
          .querySelector('[data-testid="map-camera"]')
          .getScreenCTM()
          .inverse()
      );
      return { x: world.x, y: world.y, scrollY: window.scrollY };
    }, point);
  const before = await worldUnderPointer();
  await page.mouse.move(point.x, point.y);
  await page.mouse.wheel(0, -240);
  await expect
    .poll(async () => (await cameraMatrix(page)).scale)
    .toBeGreaterThan(1);
  const zoomed = await worldUnderPointer();
  expect(zoomed.x).toBeCloseTo(before.x, 2);
  expect(zoomed.y).toBeCloseTo(before.y, 2);
  expect(zoomed.scrollY).toBe(before.scrollY);
  const high = (await cameraMatrix(page)).scale;
  await page.mouse.wheel(0, 120);
  await expect
    .poll(async () => (await cameraMatrix(page)).scale)
    .toBeLessThan(high);
  expect((await worldUnderPointer()).scrollY).toBe(before.scrollY);
  await expect(page.getByTestId("player-map-name")).toHaveCount(0);
});

test("dragging players and labels pans without accidental selection or follow snapback", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live-map");
  const canvas = mapCanvas(page);
  const marker = page.locator('[data-player-id="demo-55"]');
  await expect(page.getByTestId("player-map-marker")).toHaveCount(100);
  await canvas.scrollIntoViewIfNeeded();
  let box = await marker.boundingBox();
  const before = await cameraMatrix(page);
  await dragFrom(page, { x: box.x + box.width / 2, y: box.y + box.height / 2 });
  await expect
    .poll(async () => (await cameraMatrix(page)).x)
    .toBeGreaterThan(before.x);
  await expect(marker).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByTestId("player-map-name")).toHaveCount(0);
  // Assistive technologies may activate a marker without pointer events.
  await marker.dispatchEvent("click", { detail: 0 });
  await expect(marker).toHaveAttribute("aria-pressed", "true");
  await marker.click();
  const follow = page.getByRole("button", { name: "Verfolgen", exact: true });
  await follow.click();
  await expect(follow).toHaveAttribute("aria-pressed", "true");
  box = await page.getByTestId("player-map-name").boundingBox();
  await dragFrom(page, { x: box.x + 8, y: box.y + box.height / 2 });
  await expect(follow).toHaveAttribute("aria-pressed", "false");
  await expect(page.getByTestId("player-map-name")).toHaveText(
    "Demo Spieler 56"
  );
  const after = await cameraMatrix(page);
  const sampleText = page.getByTestId("live-map-status");
  await expect(sampleText).toContainText("Live-Daten");
  // Let real polling update the moving fixture; the user-controlled camera stays put.
  await expect
    .poll(async () => {
      const count = await canvas.locator("polyline").count();
      return count
        ? await canvas.locator("polyline").first().getAttribute("points")
        : "";
    })
    .not.toBe("");
  const trail = canvas.locator("polyline").first();
  const oldPoints = await trail.getAttribute("points");
  await expect(trail).not.toHaveAttribute("points", oldPoints);
  expect(await cameraMatrix(page)).toEqual(after);
  // A drag starting on a painted trail is just as valid as the image background.
  const trailPoint = await trail.evaluate((node) => {
    const p = node
      .getPointAtLength(node.getTotalLength() / 2)
      .matrixTransform(node.getScreenCTM());
    return { x: p.x, y: p.y };
  });
  await dragFrom(page, trailPoint, -45, 20);
  expect((await cameraMatrix(page)).x).toBeLessThan(after.x);
});

test("pointer capture keeps dragging outside the map and releases cleanly", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live-map");
  const canvas = mapCanvas(page);
  await expect(page.getByTestId("player-map-marker")).toHaveCount(100);
  await canvas.scrollIntoViewIfNeeded();
  const box = await canvas.boundingBox();
  const point = { x: box.x + box.width - 15, y: box.y + box.height / 2 };
  const before = await cameraMatrix(page);
  await dragFrom(page, point, 65, 0);
  expect((await cameraMatrix(page)).x).toBeGreaterThan(before.x);
  const after = await cameraMatrix(page);
  await page.mouse.move(point.x - 50, point.y + 20);
  expect(await cameraMatrix(page)).toEqual(after);
  await expect(canvas).toHaveCSS("cursor", "grab");
});

test("100 synthetic players, search, replay and protected evidence", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await openDemoPage(page, "/views/live-map");
  const view = page.getByTestId("live-map-page");
  await expect(view.locator('svg g[role="button"]')).toHaveCount(100);
  await expect(view.getByText("DEMO · Synthetische Testdaten")).toBeVisible();
  await view
    .getByLabel("Spieler suchen", { exact: true })
    .fill("Demo Spieler 01");
  await expect(view.locator('svg g[role="button"]')).toHaveCount(1);
  await view.locator('svg g[role="button"]').click();
  await expect(
    view.getByRole("button", { name: "Verfolgen", exact: true })
  ).toBeEnabled();
  await view.getByRole("button", { name: "Vergrößern", exact: true }).click();
  await expect(view.getByText("150 %")).toBeVisible();
  await view.locator("summary").filter({ hasText: "Begegnungen" }).click();
  await view
    .getByRole("button", { name: "Ort im Rückblick ansehen" })
    .first()
    .click();
  await expect(view.getByTestId("encounter-marker")).toBeVisible();
  await view.getByRole("button", { name: "Zurück zu Live" }).click();
  await view
    .getByRole("button", { name: "Als Fall sichern", exact: true })
    .click();
  await expect(
    view.getByRole("button", { name: "Ausschnitt ansehen" })
  ).toBeVisible();
  await view.getByRole("button", { name: "Ausschnitt ansehen" }).click();
  await expect(
    view.getByRole("button", { name: "Zurück zu Live" })
  ).toBeVisible();
  await expect(
    view.getByRole("button", { name: "Übernehmen", exact: true })
  ).toHaveCount(0);
  await view.getByRole("button", { name: "Zurück zu Live" }).click();
  await view.getByRole("button", { name: "Verlauf laden" }).click();
  await expect(
    view.getByText(/Im Rückblick werden keine aktuellen Live-Hinweise/)
  ).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
  await page.screenshot({
    path: "test-results/live-map-desktop.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("unverified maps never display precise markers", async ({ page }) => {
  await openDemoPage(page, "/views/live-map", {
    query: { tacticalScenario: "uncalibrated" },
  });
  await expect(
    page.getByText("Kartenabbildung noch nicht geprüft")
  ).toBeVisible();
  await expect(page.locator('svg g[role="button"]')).toHaveCount(0);
});

test("ordinary viewer gets no tactical page", async ({ page }) => {
  await openDemoPage(page, "/views/live-map", {
    query: { demo_role: "viewer" },
  });
  await expect(
    page.getByText(/ausdrückliche Freigabe für taktische Daten/)
  ).toBeVisible();
  await expect(page.locator('svg g[role="button"]')).toHaveCount(0);
});

test("enabled display renders players without warning banners or unavailable objects", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live-map", {
    query: { tacticalScenario: "estimated" },
  });
  await expect(page.getByTestId("player-map-marker")).toHaveCount(100);
  await expect(
    page.getByText("Vorläufige Kartenabbildung", { exact: true })
  ).toHaveCount(0);
  const quality = page.getByTestId("map-projection-details");
  await expect(quality).not.toHaveAttribute("open", "");
  await quality.locator("summary").click();
  await expect(quality).toHaveAttribute("open", "");
  await expect(quality).toContainText("Gegenprüfung");
  await expect(
    page.getByText("Garnisonen / Outposts", { exact: true })
  ).toHaveCount(0);
});

test("stale and recovered samples do not move the map or reset its zoom", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live-map", {
    query: { tacticalScenario: "stale-recovery" },
  });
  const canvas = page.getByRole("group", {
    name: "Taktische Karte mit auswählbaren Spielern",
  });
  await expect(page.getByTestId("player-map-marker")).toHaveCount(100);
  await page.getByRole("button", { name: "Vergrößern", exact: true }).click();
  const before = await canvas.evaluate((node) => ({
    top: node.getBoundingClientRect().top + window.scrollY,
    transform: node.querySelector("g").getAttribute("transform"),
  }));
  const status = page.getByTestId("live-map-status");
  await expect(status).toContainText("Messung verzögert", { timeout: 20000 });
  const stale = await canvas.evaluate((node) => ({
    top: node.getBoundingClientRect().top + window.scrollY,
    transform: node.querySelector("g").getAttribute("transform"),
  }));
  expect(stale).toEqual(before);
  await expect(status).toContainText("Live-Daten werden aktualisiert", {
    timeout: 15000,
  });
  const recovered = await canvas.evaluate((node) => ({
    top: node.getBoundingClientRect().top + window.scrollY,
    transform: node.querySelector("g").getAttribute("transform"),
  }));
  expect(recovered).toEqual(before);
});

test("mobile switches between map and inspector without overflow", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live-map");
  await page.getByRole("tab", { name: "Details & Monitor" }).click();
  await expect(
    page.getByText("Ausgewählter Spieler", { exact: true })
  ).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
  await page.screenshot({
    path: "test-results/live-map-mobile.png",
    fullPage: true,
  });
});

test.describe("touch map input", () => {
  test.use({ viewport: VIEWPORTS.mobile, hasTouch: true, isMobile: true });
  test("touch tap selects and touch drag pans without selecting", async ({
    page,
  }) => {
    await openDemoPage(page, "/views/live-map");
    const marker = page.locator('[data-player-id="demo-55"]');
    await expect(page.getByTestId("player-map-marker")).toHaveCount(100);
    await marker.tap();
    await expect(page.getByTestId("player-map-name")).toHaveText(
      "Demo Spieler 56"
    );
    const before = await cameraMatrix(page);
    const other = page.locator('[data-player-id="demo-56"]');
    const box = await other.boundingBox();
    const point = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
    const input = await page.context().newCDPSession(page);
    await input.send("Input.dispatchTouchEvent", {
      type: "touchStart",
      touchPoints: [point],
    });
    await input.send("Input.dispatchTouchEvent", {
      type: "touchMove",
      touchPoints: [{ x: point.x + 45, y: point.y + 25 }],
    });
    await input.send("Input.dispatchTouchEvent", {
      type: "touchEnd",
      touchPoints: [],
    });
    await expect
      .poll(async () => (await cameraMatrix(page)).x)
      .toBeGreaterThan(before.x);
    await expect(other).toHaveAttribute("aria-pressed", "false");
    await expect(page.getByTestId("player-map-name")).toHaveText(
      "Demo Spieler 56"
    );
    await input.detach();
  });
});
