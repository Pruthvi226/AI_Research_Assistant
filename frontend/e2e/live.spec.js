import { test, expect } from '@playwright/test';
test.skip(!process.env.E2E_LIVE, 'Opt-in check against the real external publication API.');
test('live Crossref discovery returns actual publication cards in the production browser', async ({ page }) => {
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.goto('./');
  await page.getByRole('textbox', { name: 'Research query' }).fill('retrieval augmented generation');
  const response = page.waitForResponse(r => r.url().startsWith('https://api.crossref.org/works?'));
  await page.getByRole('button', { name: 'Search academic papers' }).click();
  expect((await response).status()).toBe(200);
  await expect(page.locator('.paper-card h3').first()).toBeVisible({ timeout: 30000 });
  expect(await page.locator('.paper-card').count()).toBeGreaterThan(0);
  expect(await page.locator('.paper-card h3 a').first().getAttribute('href')).toMatch(/^https:\/\/doi.org\//);
  await page.screenshot({ path: '../docs/screenshots/search-results.png', fullPage: true });
  expect(errors).toEqual([]);
});
