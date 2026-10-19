import { expect, test, type APIRequestContext } from "@playwright/test";

async function decide(
  request: APIRequestContext,
  claimId: string,
  decision: string,
  payout: number,
) {
  await request.post(`/api/claims/${claimId}/start`);
  const response = await request.post(`/api/claims/${claimId}/decision`, {
    data: {
      decision,
      payout,
      reason: "Recorded by the end-to-end test.",
      policy_section: "5. Baggage and Personal Effects",
    },
  });
  expect(response.ok()).toBe(true);
}

test("a decision shows on the claim page", async ({ page, request }) => {
  await decide(request, "CLM-1009", "decline", 0);
  await page.goto("/#/claims/CLM-1009");
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(decision.getByText("Declined")).toBeVisible();
  await expect(
    decision.getByText("Recorded by the end-to-end test."),
  ).toBeVisible();
  await expect(page.locator(".title-line")).toContainText("Decided");
});

test("a handler signs off a payout over the limit", async ({
  page,
  request,
}) => {
  await decide(request, "CLM-1012", "approve", 2500);
  const refused = await request.post("/api/claims/CLM-1012/payment", {
    data: { amount: 2500 },
  });
  expect(refused.status()).toBe(409);

  await page.goto("/#/claims/CLM-1012");
  await expect(page.locator(".title-line")).toContainText(
    "Waiting for sign-off",
  );
  const signOff = page.getByRole("region", { name: "Sign-off" });
  await signOff.getByRole("combobox").selectOption("HND-01");
  await signOff.getByRole("button", { name: "Sign off and pay" }).click();
  await expect(
    page.getByText(/^Paid \$2,500.00 by Dana Whitfield/),
  ).toBeVisible();
  await expect(page.locator(".title-line")).toContainText("Decided");
});
