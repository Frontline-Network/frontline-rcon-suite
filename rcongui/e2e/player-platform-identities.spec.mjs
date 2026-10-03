import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

const query = { demo_platform_identities: 1 };
const cases = [
  {
    name: "FLN_Raven",
    platform: "Steam",
    kind: "steamId",
    id: "76561198000000001",
    eos: "00000000000000000000000000000001",
    url: "https://steamcommunity.com/profiles/76561198000000001",
  },
  {
    name: "FLN_Wolf",
    platform: "PlayStation 5",
    kind: "psnId",
    id: "1234567890123456789",
    eos: "00000000000000000000000000000002",
    url: "https://profile.playstation.com/FLN_Wolf",
  },
  {
    name: "FLN_Valkyrie",
    platform: "Xbox Series X|S",
    kind: "xboxId",
    id: "2533274800000001",
    eos: "00000000000000000000000000000003",
    url: "https://www.xbox.com/en-US/play/user/FLN_Valkyrie",
  },
  {
    name: "FLN_Hawkeye",
    platform: "Epic Games",
    kind: "platformId",
    id: `${"a".repeat(32)}|${"b".repeat(32)}`,
    eos: "00000000000000000000000000000004",
    url: null,
  },
];

for (const language of ["de", "en"]) {
  test(`shows readable platforms and separate IDs in live details (${language})`, async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS.desktop);
    await openDemoPage(page, "/views/live", { query, language });
    for (const account of cases) {
      const row = page
        .locator('tr[data-player-row="true"]')
        .filter({ hasText: account.name });
      await row
        .getByRole("button", {
          name: new RegExp(`(Details zu|Show details for) ${account.name}`),
        })
        .click();
      const detail = page.getByTestId("live-player-detail-panel");
      await expect(
        detail.getByText(account.platform, { exact: true })
      ).toBeVisible();
      const identities = detail.getByTestId("player-identifiers");
      await expect(
        identities.getByText(account.id, { exact: true })
      ).toBeVisible();
      const eos = identities.locator('[data-identity-kind="eosId"]');
      await expect(eos).toContainText(account.eos);
      await expect(eos.locator("a")).toHaveCount(0);
      const platformId = identities.locator(
        `[data-identity-kind="${account.kind}"]`
      );
      if (account.url) {
        await expect(platformId.locator("a")).toHaveAttribute(
          "href",
          account.url
        );
        await expect(platformId.locator("a")).toHaveAttribute(
          "rel",
          "noopener noreferrer"
        );
      } else {
        await expect(platformId.locator("a")).toHaveCount(0);
      }
      await expect(detail).not.toContainText("EPlatformFamily::");
    }
  });
}

test("copies the full PSN account ID while the internal profile still uses EOS", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await openDemoPage(page, "/views/live", { query, language: "en" });
  const row = page
    .locator('tr[data-player-row="true"]')
    .filter({ hasText: "FLN_Wolf" });
  await row.getByRole("button", { name: /Show details for FLN_Wolf/ }).click();
  const detail = page.getByTestId("live-player-detail-panel");
  await detail
    .getByRole("button", { name: "Copy PSN account ID", exact: true })
    .click();
  await expect
    .poll(() => page.evaluate(() => navigator.clipboard.readText()))
    .toBe(cases[1].id);
  await detail.getByRole("button", { name: "Profile", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "FLN_Wolf", exact: true })
  ).toHaveAttribute("href", `/records/players/${cases[1].eos}`);
});

for (const viewport of [VIEWPORTS.mobile, VIEWPORTS.desktop]) {
  test(`profile keeps EOS unlinked and platform ID linked at ${viewport.width}px`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    await openDemoPage(page, `/records/players/${cases[1].eos}`, {
      query,
      language: "en",
    });
    const identities = page.getByTestId("player-identifiers").first();
    await expect(
      identities.getByText(cases[1].id, { exact: true })
    ).toBeVisible();
    await expect(
      identities.locator('[data-identity-kind="psnId"] a')
    ).toHaveAttribute("href", cases[1].url);
    await expect(
      identities.locator('[data-identity-kind="eosId"] a')
    ).toHaveCount(0);
    await expect(identities).toContainText(
      "Profile link uses the in-game name"
    );
    const overflow = await identities.evaluate(
      (element) => element.scrollWidth - element.clientWidth
    );
    expect(overflow).toBeLessThanOrEqual(1);
    await expectNoHorizontalPageOverflow(page);
  });
}

test("long Epic IDs fit the mobile inspector without invented links", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live", { query, language: "en" });
  await page
    .getByRole("button", { name: /Open details for FLN_Hawkeye/ })
    .click();
  const detail = page.getByTestId("live-player-detail-panel");
  await expect(detail.getByText(cases[3].id, { exact: true })).toBeVisible();
  await expect(
    detail.getByTestId("player-identifiers").locator("a")
  ).toHaveCount(0);
  const overflow = await detail.evaluate(
    (element) => element.scrollWidth - element.clientWidth
  );
  expect(overflow).toBeLessThanOrEqual(1);
});

test("soldier editor displays the friendly platform without replacing the raw API value", async ({
  page,
}) => {
  await openDemoPage(page, `/records/players/${cases[1].eos}`, {
    query,
    language: "en",
  });
  await page
    .getByRole("button", { name: "Add soldier information", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("combobox")).toContainText("PlayStation 5");
  await expect(dialog.locator(".MuiSelect-nativeInput")).toHaveValue(
    "EPlatformFamily::PS5"
  );
});
