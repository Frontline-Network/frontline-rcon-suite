import { expect } from "@playwright/test";

export const VIEWPORTS = {
  mobile: { width: 390, height: 844 },
  tablet: { width: 768, height: 1024 },
  desktop: { width: 1440, height: 1000 },
};

export async function openDemoPage(
  page,
  path,
  { query = {}, language = "de" } = {},
) {
  await page.addInitScript((selectedLanguage) => {
    window.localStorage.setItem("crcon.language", selectedLanguage);
  }, language);

  const url = new URL(path, "http://127.0.0.1:3000");
  Object.entries(query).forEach(([key, value]) => {
    url.searchParams.set(key, String(value));
  });

  await page.goto(`${url.pathname}${url.search}`, { waitUntil: "domcontentloaded" });

  const main = page.locator("#main-content");
  await expect(main).toBeVisible();
  // The server selector intentionally exposes CPU, RAM, and disk meters as
  // progressbars. Only wait for transient loading spinners, otherwise every
  // loaded page is mistaken for an unfinished page.
  await expect(
    page.locator('.MuiCircularProgress-root[role="progressbar"]'),
  ).toHaveCount(0);
  await expect(page.getByText("Das hat nicht funktioniert", { exact: true })).toHaveCount(0);
  await expect(page.getByText("That did not work", { exact: true })).toHaveCount(0);
  await expect(page.getByText("Une erreur s’est produite", { exact: true })).toHaveCount(0);
  await expect.poll(async () => (await main.innerText()).trim().length).toBeGreaterThan(20);

  return main;
}

export async function expectNoHorizontalPageOverflow(page) {
  const overflow = await page.evaluate(() => ({
    documentWidth: document.documentElement.scrollWidth,
    viewportWidth: document.documentElement.clientWidth,
  }));

  expect(
    overflow.documentWidth,
    `document is ${overflow.documentWidth - overflow.viewportWidth}px wider than the viewport`,
  ).toBeLessThanOrEqual(overflow.viewportWidth + 1);
}

export function collectRuntimeErrors(page) {
  const errors = [];

  page.on("pageerror", (error) => errors.push(`pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(`console: ${message.text()}`);
  });

  return errors;
}
