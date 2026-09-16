import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

test("English player disclosure labels preserve the target identity", async ({ page }) => {
  await openDemoPage(page, "/views/live", { language: "en", query: { demo_warning_sources: 1 } });
  const panel = page.getByTestId("live-players-panel");
  await panel.getByRole("button", { name: "Show details for FLN_Raven", exact: true }).click();
  await expect(panel.getByRole("region", { name: "Details for FLN_Raven", exact: true })).toBeVisible();
  await panel.getByRole("button", { name: "Hide details for FLN_Raven", exact: true }).click();
  await expect(panel.getByRole("region", { name: "Details for FLN_Raven", exact: true })).toHaveCount(0);
});

test("English live balance includes the review, explanations, notices and actions", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", {
    language: "en",
    query: { demo_balance: "unbalanced" },
  });
  const card = page.getByRole("region", { name: "Live balance assistant" });
  await expect(
    card.getByRole("heading", { name: "Uneven player counts" })
  ).toBeVisible();
  await expect(
    card.getByText(/selection remains visible for up to 60 seconds/)
  ).toBeVisible();
  await expect(
    card.getByRole("img", { name: /^Live strength index: Allies/ })
  ).toBeVisible();
  await card.getByRole("button", { name: "Why?", exact: true }).click();
  await expect(
    card.getByText(/Previous rounds or a learning period are not required/)
  ).toBeVisible();
  await card
    .getByRole("button", { name: "Review squad switch", exact: true })
    .click();
  const dialog = page.getByRole("dialog", {
    name: "Review coordinated squad switch",
  });
  await expect(
    dialog.getByText("What does the strength index mean?", { exact: true })
  ).toBeVisible();
  await expect(dialog.getByText(/player level contributes 45%/)).toBeVisible();
  await expect(
    dialog.getByText(/does not switch players automatically/)
  ).toBeVisible();
  await expect(
    dialog.getByRole("button", {
      name: "Notify and switch squad(s)",
      exact: true,
    })
  ).toBeEnabled();
  await expect(dialog).not.toContainText(
    /Stärke-Index|Aussagekraft|Schließen|Vorschlag/
  );
  await dialog.getByRole("button", { name: "Close", exact: true }).click();
});

test("switching language without reload refreshes memoized balance labels", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", {
    query: { demo_balance: "unbalanced" },
  });
  await expect(
    page.getByRole("region", { name: "Live-Balance-Assistent" })
  ).toBeVisible();
  await page.getByRole("button", { name: "Sprache", exact: true }).click();
  await page.getByRole("menuitem", { name: /Englisch|English/ }).click();
  const card = page.getByRole("region", { name: "Live balance assistant" });
  await expect(
    card.getByRole("heading", { name: "Uneven player counts" })
  ).toBeVisible();
  await expect(
    card.getByText("Move squad together", { exact: true })
  ).toBeVisible();
  await expect(card).not.toContainText(
    /Achsenmächte|Spielerzahl|Wechsel nötig|Aussagekraft/
  );
});

test("English mobile compact balance retains indices and actions without overflow", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live", { language: "en" });
  const card = page.getByRole("region", { name: "Live balance assistant" });
  await card.getByRole("switch").click();
  await expect(card.getByRole("switch")).not.toBeChecked();
  await expect(card.getByText("Estimated team strength", { exact: true })).toHaveCount(0);
  await expect(
    card.getByRole("img", { name: /^Live strength index:/ })
  ).toBeVisible();
  await expect(
    card.getByRole("button", { name: "No intervention needed" })
  ).toBeVisible();
  await expect(
    card.getByText("No forecast available", { exact: true })
  ).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
});
