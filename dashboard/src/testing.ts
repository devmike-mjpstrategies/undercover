import { vi } from "vitest";
import type { Claim, ClaimSummary } from "./api";

export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : input.toString();
    const key = `${init?.method ?? "GET"} ${url}`;
    const body = routes[key];
    if (body instanceof Response) return Promise.resolve(body);
    if (body === undefined) {
      return Promise.resolve(
        Response.json({ detail: `${key} was not found.` }, { status: 404 }),
      );
    }
    return Promise.resolve(Response.json(body));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function summary(overrides: Partial<ClaimSummary>): ClaimSummary {
  return {
    claim_id: "CLM-1001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    submitted_on: "2026-06-24",
    summary: "Flight home canceled",
    amount_claimed: 420,
    status: "waiting",
    decision: null,
    payout: null,
    ...overrides,
  };
}

export function claim(overrides: Partial<Claim>): Claim {
  return {
    claim_id: "CLM-1001",
    policy_id: "POL-2001",
    customer_id: "CUS-3001",
    claim_type: "trip_delay",
    submitted_on: "2026-06-24",
    incident_date: "2026-06-18",
    incident_location: "Rome, Italy",
    summary: "Flight home canceled",
    story: "My flight home from Rome was canceled.",
    items: [
      { description: "Airport hotel", category: "accommodation", amount: 245 },
    ],
    amount_claimed: 245,
    documents: [
      {
        name: "Cancellation notice",
        type: "carrier_report",
        content: "Flight MA 611 was canceled.",
      },
    ],
    status: "waiting",
    decision: null,
    payment: null,
    sign_off: null,
    ...overrides,
  };
}
