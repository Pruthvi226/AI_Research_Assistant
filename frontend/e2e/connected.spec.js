import { test, expect } from "@playwright/test";
test.skip(
  !process.env.E2E_CONNECTED,
  "Requires the separately started local Flask API and a connected production build.",
);
test("real PDF upload, local retrieval chat, source links, code and missing-key errors", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("./#documents");
  await expect(
    page.getByRole("button", { name: "Upload PDF", exact: true }),
  ).toBeEnabled();
  await page
    .locator("input[type=file]")
    .setInputFiles("../.codex-test/workflow-fixture.pdf");
  await expect(
    page.getByRole("heading", { name: "workflow-fixture.pdf", exact: true }),
  ).toBeVisible({ timeout: 30000 });
  await expect(
    page.getByText("EXTRACTIVE ANALYSIS · SOURCE SENTENCES", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Ask this paper", exact: true })
    .click();
  await page
    .getByRole("textbox", { name: "Research question" })
    .fill("What dataset was evaluated?");
  await page.getByRole("button", { name: "Send research question" }).click();
  await expect(page.locator(".message.assistant")).toContainText("120");
  await page.reload({ waitUntil: "networkidle" });
  await page
    .getByRole("button", { name: "Paper workspace", exact: true })
    .click();
  await page
    .getByRole("button", { name: "workflow-fixture.pdf", exact: true })
    .first()
    .click();
  await page
    .getByRole("heading", { name: "workflow-fixture.pdf", exact: true })
    .waitFor();
  await page
    .getByRole("button", { name: "Ask this paper", exact: true })
    .click();
  await expect(page.locator(".message.assistant")).toContainText("120");
  await page.locator(".message.assistant summary").first().click();
  const source = page
    .getByRole("link", { name: /Open source.*page 1/ })
    .first();
  await expect(source).toHaveAttribute(
    "href",
    /\/api\/documents\/.+\/file#page=1/,
  );
  await page.getByRole("combobox").selectOption("code");
  await page
    .getByRole("textbox", { name: "Research question" })
    .fill("Generate a model scaffold");
  await page.getByRole("button", { name: "Send research question" }).click();
  await expect(page.getByText("Generated code", { exact: true })).toBeVisible();
  await page.getByText("Generated code", { exact: true }).click();
  await expect(page.locator(".message.assistant pre")).toContainText(
    "import torch",
  );
  await page.getByRole("button", { name: "Detach paper" }).click();
  await page
    .getByRole("textbox", { name: "Research question" })
    .fill("What is retrieval augmented generation?");
  await page.getByRole("button", { name: "Send research question" }).click();
  await expect(page.getByRole("alert")).toContainText("GEMINI_API_KEY");
  await expect(
    page.getByRole("textbox", { name: "Research question" }),
  ).toHaveValue("What is retrieval augmented generation?");
  expect(errors).toEqual([]);
});
