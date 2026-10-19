export type Status =
  "waiting" | "in_progress" | "awaiting_sign_off" | "decided";
export type DecisionKind = "approve" | "decline" | "refer";

export interface ClaimSummary {
  claim_id: string;
  claim_type: string;
  summary: string;
  amount_claimed: number;
  status: Status;
  decision: DecisionKind | null;
  payout: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface ClaimDocument {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  decision: DecisionKind;
  payout: number;
  reason: string;
  policy_section: string;
  decided_at: string;
}

export interface Payment {
  amount: number;
  released_by: string;
  paid_at: string;
}

export interface SignOff {
  handler_id: string;
  signed_at: string;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  amount_claimed: number;
  documents: ClaimDocument[];
  status: Status;
  decision: Decision | null;
  payment: Payment | null;
  sign_off: SignOff | null;
}

export interface Plan {
  plan: string;
  name: string;
  deductible: number;
}

export interface AddOn {
  add_on: string;
  name: string;
}

export interface Policy {
  policy_id: string;
  plan: Plan;
  add_ons: AddOn[];
  purchased_on: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface EarlierClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface Step {
  id: number;
  kind: "tool_call" | "tool_result" | "message";
  text: string;
  created_at: string;
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
  can_approve_over_limit: boolean;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const body = (await response.json()) as { detail?: unknown };
    throw new Error(
      typeof body.detail === "string" ? body.detail : response.statusText,
    );
  }
  return (await response.json()) as T;
}

export const api = {
  claims: () => request<ClaimSummary[]>("/api/claims"),
  claim: (claimId: string) => request<Claim>(`/api/claims/${claimId}`),
  steps: (claimId: string) => request<Step[]>(`/api/claims/${claimId}/steps`),
  policy: (policyId: string) => request<Policy>(`/api/policies/${policyId}`),
  history: (customerId: string) =>
    request<EarlierClaim[]>(`/api/customers/${customerId}/claims`),
  instructions: () => request<{ text: string }>("/api/instructions"),
  handlers: () => request<Handler[]>("/api/handlers"),
  signOff: (claimId: string, handlerId: string) =>
    request<Claim>(`/api/claims/${claimId}/sign-off`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ handler_id: handlerId }),
    }),
};
