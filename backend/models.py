"""The shapes the UnderCover API takes and returns."""

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["waiting", "in_progress", "awaiting_sign_off", "decided"]
DecisionKind = Literal["approve", "decline", "refer"]


class Item(BaseModel):
    description: str
    category: str
    amount: float


class Document(BaseModel):
    name: str
    type: str
    content: str


class Decision(BaseModel):
    decision: DecisionKind
    payout: float = Field(ge=0)
    reason: str = Field(min_length=1)
    policy_section: str = Field(min_length=1)


class RecordedDecision(Decision):
    decided_at: str


class Payment(BaseModel):
    amount: float
    released_by: str
    paid_at: str


class SignOff(BaseModel):
    handler_id: str
    signed_at: str


class ClaimSummary(BaseModel):
    claim_id: str
    claim_type: str
    summary: str
    amount_claimed: float
    status: Status
    decision: DecisionKind | None
    payout: float | None


class Claim(BaseModel):
    claim_id: str
    policy_id: str
    customer_id: str
    claim_type: str
    submitted_on: str
    incident_date: str
    incident_location: str
    summary: str
    story: str
    items: list[Item]
    amount_claimed: float
    documents: list[Document]
    status: Status
    decision: RecordedDecision | None
    payment: Payment | None
    sign_off: SignOff | None


class Plan(BaseModel):
    plan: str
    name: str
    trip_cancellation_max: float
    trip_delay_waiting_hours: int
    trip_delay_max: float
    baggage_delay_waiting_hours: int
    baggage_delay_max: float
    baggage_max: float
    per_item_limit: float
    passport_max: float
    emergency_medical_max: float
    deductible: float


class AddOn(BaseModel):
    add_on: str
    name: str
    effect: str
    electronics_per_item_limit: float | None = None


class Trip(BaseModel):
    destination: str
    departs_on: str
    returns_on: str
    trip_cost: float


class Policy(BaseModel):
    policy_id: str
    customer_id: str
    plan: Plan
    add_ons: list[AddOn]
    purchased_on: str
    sold_through: str
    trip: Trip
    travelers: list[str]
    status: str


class EarlierClaim(BaseModel):
    claim_id: str
    filed_on: str
    incident_date: str
    claim_type: str
    summary: str
    outcome: str
    amount_paid: float


class Handler(BaseModel):
    handler_id: str
    name: str
    role: str
    can_approve_over_limit: bool


class Text(BaseModel):
    text: str
