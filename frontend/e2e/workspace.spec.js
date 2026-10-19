import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// Deterministic publisher fixtures are used only in tests; production always calls Crossref.
const publication = (i = 1) => ({
  DOI: `10.1000/test${i}`,
  title: [`Evidence-based retrieval study ${i}`],
  author: [{ given: "Ada", family: "Researcher" }],
  published: { "date-parts": [[2025]] },
  "container-title": ["Research Journal"],
  abstract:
    "<jats:p>We evaluate retrieval against a baseline and report its limitations.</jats:p>",
  "is-referenced-by-count": 42,
});
async function search(page) {
  await page.route("https://api.crossref.org/works?**", (route) =>
    route.fulfill({
      json: {
        message: {
          items: [publication(1), publication(2)],
          "total-results": 28,
        },
      },
    }),
  );
  await page.getByRole("textbox", { name: "Research query" }).fill("retrieval");
  await page.getByRole("button", { name: "Search academic papers" }).click();
  await expect(
    page.getByRole("heading", { name: "Evidence-based retrieval study 1" }),
  ).toBeVisible();
}
test("search, filtering, bookmarking, notes, comparison and export survive navigation", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("./");
  await search(page);
  await page.getByLabel("Published", { exact: true }).selectOption("2024");
  await expect(
    page.getByRole("heading", { name: "Evidence-based retrieval study 1" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Bookmark paper", exact: true })
    .first()
    .click();
  await page
    .getByRole("button", { name: "Bookmark paper", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "My library" }).click();
  await page
    .getByRole("textbox", {
      name: "Notes for Evidence-based retrieval study 1",
    })
    .fill("Check evaluation reproducibility.");
  await page.getByRole("checkbox").first().check();
  await page.getByRole("checkbox").nth(1).check();
  await page.getByRole("button", { name: "Review 2 papers" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export report" }).click();
  expect((await downloaded).suggestedFilename()).toBe(
    "scientia-literature-review.md",
  );
  await page.getByRole("button", { name: "My library" }).click();
  await page.reload();
  await expect(
    page.getByRole("textbox", {
      name: "Notes for Evidence-based retrieval study 1",
    }),
  ).toHaveValue("Check evaluation reproducibility.");
  expect(errors).toEqual([]);
});
test("publication API errors and empty states stay actionable", async ({
  page,
}) => {
  await page.route("https://api.crossref.org/works?**", (route) =>
    route.fulfill({ status: 500, body: "{}" }),
  );
  await page.goto("./");
  await page
    .getByRole("textbox", { name: "Research query" })
    .fill("unknown topic");
  await page.getByRole("button", { name: "Search academic papers" }).click();
  await expect(page.getByRole("alert")).toContainText("500");
  await page.unroute("https://api.crossref.org/works?**");
  await page.route("https://api.crossref.org/works?**", (route) =>
    route.fulfill({ json: { message: { items: [], "total-results": 0 } } }),
  );
  await page.getByRole("button", { name: "Search academic papers" }).click();
  await expect(
    page.getByRole("heading", { name: "No papers found" }),
  ).toBeVisible();
});
test("hash navigation, browser back, theme and keyboard access work", async ({
  page,
}) => {
  await page.goto("./#library");
  await expect(page.getByRole("heading", { name: "My library" })).toBeVisible();
  await page
    .getByRole("button", { name: "Research history", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Research history" }),
  ).toBeVisible();
  await page.goBack();
  await expect(page.getByRole("heading", { name: "My library" })).toBeVisible();
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
});
test("static deployment does not request nonexistent API or claim AI availability", async ({
  page,
}) => {
  const apiRequests = [];
  page.on("request", (r) => {
    if (new URL(r.url()).pathname.startsWith("/api/"))
      apiRequests.push(r.url());
  });
  await page.goto("./#chat");
  await expect(
    page.getByRole("button", { name: "Send research question" }),
  ).toBeDisabled();
  await expect(page.getByText("Discovery mode", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Paper workspace", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Upload PDF", exact: true }),
  ).toBeDisabled();
  expect(apiRequests).toEqual([]);
});
test("desktop and mobile landing layouts have no overflow and pass accessibility checks", async ({
  page,
}) => {
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: width === 1440 ? 1000 : 844 });
    await page.goto("./");
    await page.evaluate(() => document.fonts.ready);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
      .analyze();
    expect(audit.violations).toEqual([]);
    if (width === 1440)
      await page.screenshot({
        path: "../docs/screenshots/desktop.png",
        fullPage: true,
      });
    if (width === 390) {
      await page.screenshot({
        path: "../docs/screenshots/mobile.png",
        fullPage: true,
      });
      await page.getByRole("button", { name: "Open navigation" }).click();
      await page
        .getByRole("button", { name: "My library", exact: true })
        .click();
      await expect(
        page.getByRole("heading", { name: "My library" }),
      ).toBeVisible();
    }
  }
});
test("dark mode and search result cards pass accessibility checks", async ({
  page,
}) => {
  await page.goto("./");
  await search(page);
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  const audit = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(audit.violations).toEqual([]);
});
