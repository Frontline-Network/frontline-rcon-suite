import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

async function openLogDemo(page, size = 5) {
  await openDemoPage(page, "/views/live", {
    query: { demo_log_stacks: "1", demo_log_stack_size: String(size) },
  });
  const mobileTab = page.getByRole("tab", { name: "Protokoll", exact: true });
  if (await mobileTab.isVisible()) {
    await mobileTab.click();
  } else {
    await page
      .getByRole("button", { name: "Live-Protokoll", exact: true })
      .click();
  }
  await expect(page.getByTestId("live-log-stack")).toHaveCount(1);
}

for (const viewport of ["desktop", "mobile"]) {
  test(`100-message stacks stay compact and all details are reachable (${viewport})`, async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS[viewport]);
    await openLogDemo(page, 100);
    const stack = page.getByTestId("live-log-stack");
    const toggle = stack.getByRole("button", { name: /100 gleiche Meldungen/ });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await toggle.click();
    const scroller = page.getByTestId("live-log-stack-scroll");
    const details = page.getByTestId("live-log-stack-details");
    await expect(details.locator("li")).toHaveCount(100);
    const dimensions = await scroller.evaluate((el) => ({
      height: el.clientHeight,
      scrollHeight: el.scrollHeight,
      width: el.clientWidth,
      scrollWidth: el.scrollWidth,
    }));
    expect(dimensions.height).toBeLessThanOrEqual(360);
    expect(dimensions.scrollHeight).toBeGreaterThan(dimensions.height);
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.width + 1);
    // The scroll area is keyboard reachable; End reaches the last recipient.
    await scroller.focus();
    await scroller.press("End");
    const lastRecipient = details.getByRole("button", {
      name: "Demo-Spieler 100",
      exact: true,
    });
    await expect(lastRecipient).toBeInViewport();
    await expect(toggle).toBeVisible();
    await expectNoHorizontalPageOverflow(page);
    await toggle.click();
    await expect(details).toHaveCount(0);
  });

  test(`repeated messages expand with every recipient and time (${viewport})`, async ({
    page,
  }) => {
    await page.setViewportSize(VIEWPORTS[viewport]);
    const errors = collectRuntimeErrors(page);
    await openLogDemo(page);
    const stack = page.getByTestId("live-log-stack");
    const toggle = stack.getByRole("button", { name: /5 gleiche Meldungen/ });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(page.getByTestId("live-log-stack-details")).toHaveCount(0);
    await toggle.press("Enter");
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    const details = page.getByTestId("live-log-stack-details");
    await expect(details.locator("li")).toHaveCount(5);
    await expect(
      details.getByRole("button", { name: "Originalmeldung kopieren" })
    ).toHaveCount(5);
    for (let index = 1; index <= 5; index += 1) {
      const recipient = details.getByRole("button", {
        name: new RegExp(`^Demo-Spieler ${index}( · .+)?$`),
      });
      await recipient.scrollIntoViewIfNeeded();
      await expect(recipient).toBeVisible();
      await expect(details.locator("time").nth(index - 1)).toHaveText(
        `21:23:${46 - index}`
      );
    }
    await expectNoHorizontalPageOverflow(page);
    await toggle.press("Space");
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await expect(details).toHaveCount(0);
    expect(errors).toEqual([]);
  });
}

test("live log filtering and pagination still operate on individual events", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.desktop);
  await openLogDemo(page);
  const stream = page.getByTestId("live-event-stream");
  const search = page.getByRole("textbox", { name: "protokoll durchsuchen …" });
  await expect(page.getByText("110 Ereignisse", { exact: true })).toBeVisible();
  await expect(stream.locator(":scope > ol > li")).toHaveCount(96);
  await page
    .getByRole("button", { name: "Nächste Seite", exact: true })
    .click();
  await expect(page.getByText("Seite 2 von 2", { exact: true })).toBeVisible();
  await expect(stream.locator(":scope > ol > li")).toHaveCount(10);
  await expect(page.getByTestId("live-log-stack")).toHaveCount(0);

  // Search resets pagination and matches the original recipient-bearing text.
  await search.fill("Demo-Spieler 3(");
  await expect(page.getByText("1 Ereignisse", { exact: true })).toBeVisible();
  await expect(stream.locator(":scope > ol > li")).toHaveCount(1);
  await expect(page.getByTestId("live-log-stack")).toHaveCount(0);
  await search.fill("no-such-message-983472");
  await expect(stream.locator("li")).toHaveCount(0);
  await search.fill("");
  await expect(page.getByTestId("live-log-stack")).toHaveCount(1);
  await page
    .getByRole("group", { name: "Ereignisse filtern" })
    .getByRole("button", { name: "Chat", exact: true })
    .click();
  await expect(stream.locator("li")).toHaveCount(1);
  await expect(stream.getByText("Hallo Squad!", { exact: true })).toBeVisible();
});
