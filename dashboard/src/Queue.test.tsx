import { act, cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Queue, QUEUE_REFRESH_MS } from "./Queue";
import { stubApi, summary } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const claims = [
  summary({}),
  summary({
    claim_id: "CLM-1002",
    claim_type: "baggage",
    amount_claimed: 1150,
    status: "decided",
    decision: "approve",
    payout: 1100,
  }),
  summary({
    claim_id: "CLM-1003",
    status: "awaiting_sign_off",
    decision: "approve",
    payout: 3800,
  }),
];

it("lists the claims with where each stands", async () => {
  stubApi({ "GET /api/claims": claims });
  render(<Queue />);
  const row = (await screen.findByText("CLM-1002")).closest("tr");
  if (!row) throw new Error("no row");
  const cells = within(row);
  expect(cells.getByText("Baggage")).toBeDefined();
  expect(cells.getByText("$1,150.00")).toBeDefined();
  expect(cells.getByText("Approved")).toBeDefined();
  expect(cells.getByText("$1,100.00")).toBeDefined();
  expect(cells.getByText("Decided").className).toBe("chip chip-decided");
  expect(
    screen.getByRole("link", { name: "CLM-1001" }).getAttribute("href"),
  ).toBe("#/claims/CLM-1001");
});

it("counts the claims in each status", async () => {
  stubApi({ "GET /api/claims": claims });
  render(<Queue />);
  await screen.findByText("CLM-1001");
  expect(screen.getByTestId("count-waiting").textContent).toBe("1");
  expect(screen.getByTestId("count-in_progress").textContent).toBe("0");
  expect(screen.getByTestId("count-awaiting_sign_off").textContent).toBe("1");
  expect(screen.getByTestId("count-decided").textContent).toBe("1");
});

it("says when the queue cannot be loaded", async () => {
  stubApi({
    "GET /api/claims": Response.json({ detail: "Down" }, { status: 500 }),
  });
  render(<Queue />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Could not load the queue. Down",
  );
});

it("refreshes the queue", async () => {
  vi.useFakeTimers();
  const fetchMock = stubApi({ "GET /api/claims": claims });
  render(<Queue />);
  expect(screen.getByText("Loading the queue")).toBeDefined();
  await act(() => vi.advanceTimersByTimeAsync(QUEUE_REFRESH_MS));
  expect(fetchMock).toHaveBeenCalledTimes(2);
});
