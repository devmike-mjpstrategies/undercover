import { expect, test } from "@playwright/test";

test("the queue lists every claim", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Claims queue" }),
  ).toBeVisible();
  await expect(page.locator("tbody tr")).toHaveCount(25);
  await page.getByRole("link", { name: "CLM-1004" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Checked bag arrived 31 hours late",
  );
});

test("the instructions are read only", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Instructions" }).click();
  await expect(page.getByText("You are the UnderCover Agent.")).toBeVisible();
  await expect(page.getByRole("button")).toHaveCount(0);
  await expect(page.getByRole("textbox")).toHaveCount(0);
});
