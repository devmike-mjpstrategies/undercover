import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Step } from "./api";
import { CLAIM_REFRESH_MS, ClaimPage } from "./ClaimPage";
import { claim, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const policy = {
  policy_id: "POL-2001",
  plan: { plan: "premium", name: "UnderCover Premium", deductible: 50 },
  add_ons: [],
  purchased_on: "2026-04-22",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

const history = [
  {
    claim_id: "CLM-0412",
    filed_on: "2024-08-19",
    claim_type: "baggage_delay",
    summary: "Checked bag arrived late",
    outcome: "approved",
    amount_paid: 140,
  },
];

const steps: Step[] = [
  {
    id: 1,
    kind: "tool_call",
    text: 'get_claim {"claim_id": "CLM-1001"}',
    created_at: "2026-10-19T13:00:00+00:00",
  },
  {
    id: 2,
    kind: "tool_result",
    text: 'get_claim: {"story": "My flight"}',
    created_at: "2026-10-19T13:00:01+00:00",
  },
  {
    id: 3,
    kind: "message",
    text: "Approved and paid $420.00.",
    created_at: "2026-10-19T13:00:02+00:00",
  },
];

const decided = claim({
  status: "decided",
  decision: {
    decision: "approve",
    payout: 420,
    reason: "The flight was canceled for a crew problem.",
    policy_section: "3. Trip Delay",
    decided_at: "2026-10-19T13:00:02+00:00",
  },
  payment: {
    amount: 420,
    released_by: "UnderCover Agent",
    paid_at: "2026-10-19T13:00:03+00:00",
  },
});

const waitingForSignOff = claim({
  status: "awaiting_sign_off",
  decision: {
    decision: "approve",
    payout: 1250,
    reason: "Covered.",
    policy_section: "5. Baggage",
    decided_at: "2026-10-19T13:00:02+00:00",
  },
});

const handlers = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
    can_approve_over_limit: true,
  },
  {
    handler_id: "HND-09",
    name: "Sam Trainee",
    role: "Trainee",
    can_approve_over_limit: false,
  },
];

function routes(current: unknown, currentSteps: Step[]) {
  return {
    "GET /api/claims/CLM-1001": current,
    "GET /api/claims/CLM-1001/steps": currentSteps,
    "GET /api/policies/POL-2001": policy,
    "GET /api/customers/CUS-3001/claims": history,
    "GET /api/handlers": handlers,
  };
}

it("shows the claim in full with its decision", async () => {
  stubApi(routes(decided, steps));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("Flight home canceled")).toBeDefined();
  expect(
    screen.getByText("My flight home from Rome was canceled."),
  ).toBeDefined();
  expect(screen.getByText("Airport hotel")).toBeDefined();
  expect(screen.getByText("Cancellation notice")).toBeDefined();
  const decision = within(screen.getByRole("region", { name: "Decision" }));
  expect(decision.getByText("Approved")).toBeDefined();
  expect(decision.getByText("$420.00")).toBeDefined();
  expect(
    decision.getByText("The flight was canceled for a crew problem."),
  ).toBeDefined();
  expect(decision.getByText("Policy wording: 3. Trip Delay")).toBeDefined();
  expect(
    decision.getByText(/^Paid \$420.00 by UnderCover Agent/),
  ).toBeDefined();
  expect(await screen.findByText("UnderCover Premium")).toBeDefined();
  expect(
    screen.getByText(/Checked bag arrived late, approved, \$140.00/),
  ).toBeDefined();
});

it("shows the agent's steps", async () => {
  stubApi(routes(decided, steps));
  render(<ClaimPage claimId="CLM-1001" />);
  const list = within(
    await screen.findByRole("region", { name: "What the agent did" }),
  );
  expect(list.getByText("Read the claim")).toBeDefined();
  expect(list.getByText('{"claim_id": "CLM-1001"}')).toBeDefined();
  expect(list.getByText("Result of get_claim")).toBeDefined();
  expect(list.getByText('{"story": "My flight"}')).toBeDefined();
  expect(list.getByText("Approved and paid $420.00.")).toBeDefined();
});

it("says when nothing has happened yet", async () => {
  stubApi(routes(claim({}), []));
  render(<ClaimPage claimId="CLM-1001" />);
  expect(await screen.findByText("No decision yet.")).toBeDefined();
  expect(
    screen.getByText("The agent has not worked on this claim yet."),
  ).toBeDefined();
});

it("follows the agent as it works", async () => {
  vi.useFakeTimers();
  const fetchMock = stubApi(
    routes(claim({ status: "in_progress" }), steps.slice(0, 1)),
  );
  render(<ClaimPage claimId="CLM-1001" />);
  await act(() => vi.advanceTimersByTimeAsync(0));
  expect(screen.getByText("Read the claim")).toBeDefined();
  stubApi(routes(decided, steps));
  await act(() => vi.advanceTimersByTimeAsync(CLAIM_REFRESH_MS));
  expect(screen.getByText("Approved and paid $420.00.")).toBeDefined();
  expect(screen.getByText("Decided")).toBeDefined();
  expect(fetchMock).toHaveBeenCalled();
});

it("says when the claim cannot be loaded", async () => {
  stubApi({});
  render(<ClaimPage claimId="CLM-9999" />);
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Could not load CLM-9999. GET /api/claims/CLM-9999 was not found.",
  );
});

it("signs off a payout over the limit", async () => {
  const fetchMock = stubApi({
    ...routes(waitingForSignOff, []),
    "POST /api/claims/CLM-1001/sign-off": decided,
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const panel = within(await screen.findByRole("region", { name: "Sign-off" }));
  expect(
    panel.getByText(/\$1,250.00 needs a handler's sign-off/),
  ).toBeDefined();
  const button = panel.getByRole<HTMLButtonElement>("button", {
    name: "Sign off and pay",
  });
  expect(button.disabled).toBe(true);
  await panel.findByRole("option", { name: "Dana Whitfield" });
  expect(panel.queryByRole("option", { name: "Sam Trainee" })).toBeNull();
  fireEvent.change(panel.getByRole("combobox"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(button);
  await vi.waitFor(() => {
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/claims/CLM-1001/sign-off",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ handler_id: "HND-01" }),
      }),
    );
  });
});

it("shows why a sign-off was refused", async () => {
  stubApi({
    ...routes(waitingForSignOff, []),
    "POST /api/claims/CLM-1001/sign-off": Response.json(
      { detail: "CLM-1001 is not waiting for sign-off." },
      { status: 409 },
    ),
  });
  render(<ClaimPage claimId="CLM-1001" />);
  const panel = within(await screen.findByRole("region", { name: "Sign-off" }));
  await panel.findByRole("option", { name: "Dana Whitfield" });
  fireEvent.change(panel.getByRole("combobox"), {
    target: { value: "HND-01" },
  });
  fireEvent.click(panel.getByRole("button", { name: "Sign off and pay" }));
  expect((await panel.findByRole("alert")).textContent).toBe(
    "CLM-1001 is not waiting for sign-off.",
  );
});
