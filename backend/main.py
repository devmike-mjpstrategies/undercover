"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException

from backend import db
from backend.models import (
    AddOn,
    Claim,
    ClaimSummary,
    Decision,
    EarlierClaim,
    Handler,
    NewStep,
    Payment,
    PaymentRequest,
    Plan,
    Policy,
    RecordedDecision,
    SignOff,
    SignOffRequest,
    Step,
    Text,
)
from backend.seed import DATA, seed

INSTRUCTIONS = Path(__file__).parent / "instructions.md"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not db.path().exists():
        seed()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def database() -> Iterator[sqlite3.Connection]:
    connection = db.connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


Database = Annotated[sqlite3.Connection, Depends(database)]


def fetch(connection: sqlite3.Connection, sql: str, key: str) -> sqlite3.Row:
    row = connection.execute(sql, (key,)).fetchone()
    if row is None:
        raise HTTPException(404, f"{key} was not found.")
    return row


def claim_row(connection: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
    return fetch(connection, "SELECT * FROM claims WHERE claim_id = ?", claim_id)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def money(amount: float) -> str:
    return f"${amount:,.2f}"


def payout_limit(connection: sqlite3.Connection) -> float:
    row = fetch(
        connection,
        "SELECT value FROM settings WHERE key = ?",
        "payout_approval_limit",
    )
    return json.loads(row["value"])


def pay(
    connection: sqlite3.Connection, claim_id: str, amount: float, paid_by: str
) -> None:
    connection.execute(
        "UPDATE claims SET paid_amount = ?, paid_by = ?, paid_at = ?"
        " WHERE claim_id = ?",
        (amount, paid_by, now(), claim_id),
    )


def to_claim(row: sqlite3.Row) -> Claim:
    data: dict[str, Any] = json.loads(row["data"])
    decision = payment = sign_off = None
    if row["decision"]:
        decision = RecordedDecision(
            decision=row["decision"],
            payout=row["payout"],
            reason=row["reason"],
            policy_section=row["policy_section"],
            decided_at=row["decided_at"],
        )
    if row["paid_at"]:
        payment = Payment(
            amount=row["paid_amount"],
            released_by=row["paid_by"],
            paid_at=row["paid_at"],
        )
    if row["signed_off_at"]:
        sign_off = SignOff(
            handler_id=row["signed_off_by"], signed_at=row["signed_off_at"]
        )
    return Claim(
        **(data | {"status": row["status"]}),
        decision=decision,
        payment=payment,
        sign_off=sign_off,
    )


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims(connection: Database) -> list[ClaimSummary]:
    """List the claims queue in order, with where each claim stands."""
    rows = connection.execute(
        "SELECT claims.*, json_extract(customers.data, '$.name') AS customer_name"
        " FROM claims JOIN customers"
        " ON customers.customer_id = json_extract(claims.data, '$.customer_id')"
        " ORDER BY position"
    ).fetchall()
    return [
        ClaimSummary(
            **json.loads(row["data"])
            | {
                "customer_name": row["customer_name"],
                "status": row["status"],
                "decision": row["decision"],
                "payout": row["payout"],
            }
        )
        for row in rows
    ]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str, connection: Database) -> Claim:
    """Get one claim in full, with its decision, payment and sign-off."""
    return to_claim(claim_row(connection, claim_id))


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str, connection: Database) -> Policy:
    """Get a policy with its plan's limits and its add-ons."""
    policy = json.loads(
        fetch(connection, "SELECT data FROM policies WHERE policy_id = ?", policy_id)[
            "data"
        ]
    )
    plan = fetch(connection, "SELECT data FROM plans WHERE plan = ?", policy["plan"])
    add_ons = [
        AddOn(**json.loads(row["data"]))
        for row in connection.execute(
            "SELECT data FROM add_ons WHERE add_on IN (SELECT value FROM json_each(?))",
            (json.dumps(policy["add_ons"]),),
        )
    ]
    return Policy(
        **policy | {"plan": Plan(**json.loads(plan["data"])), "add_ons": add_ons}
    )


@app.get("/api/customers/{customer_id}/claims", operation_id="get_claim_history")
def get_claim_history(customer_id: str, connection: Database) -> list[EarlierClaim]:
    """Get a customer's earlier claims, without their contact details."""
    customer = json.loads(
        fetch(
            connection,
            "SELECT data FROM customers WHERE customer_id = ?",
            customer_id,
        )["data"]
    )
    return [EarlierClaim(**claim) for claim in customer["previous_claims"]]


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> Text:
    """Get the policy wording, the contract with the customer."""
    return Text(text=(DATA / "policy_wording.md").read_text(encoding="utf-8"))


@app.get("/api/instructions", operation_id="get_instructions")
def get_instructions() -> Text:
    """Get the UnderCover Agent's instructions."""
    return Text(text=INSTRUCTIONS.read_text(encoding="utf-8"))


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers(connection: Database) -> list[Handler]:
    """List the claims handlers."""
    rows = connection.execute("SELECT data FROM handlers ORDER BY handler_id")
    return [Handler(**json.loads(row["data"])) for row in rows]


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str, connection: Database) -> Claim:
    """Start work on a claim and clear any earlier steps."""
    if claim_row(connection, claim_id)["status"] not in ("waiting", "in_progress"):
        raise HTTPException(409, f"{claim_id} already has a decision.")
    connection.execute(
        "UPDATE claims SET status = 'in_progress' WHERE claim_id = ?", (claim_id,)
    )
    connection.execute("DELETE FROM steps WHERE claim_id = ?", (claim_id,))
    return to_claim(claim_row(connection, claim_id))


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str, connection: Database) -> list[Step]:
    """List the agent's steps on a claim, oldest first."""
    claim_row(connection, claim_id)
    rows = connection.execute(
        "SELECT id, kind, text, created_at FROM steps WHERE claim_id = ? ORDER BY id",
        (claim_id,),
    )
    return [Step(**dict(row)) for row in rows]


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, step: NewStep, connection: Database) -> Step:
    """Record one step the agent took on a claim."""
    claim_row(connection, claim_id)
    created_at = now()
    cursor = connection.execute(
        "INSERT INTO steps (claim_id, kind, text, created_at) VALUES (?, ?, ?, ?)",
        (claim_id, step.kind, step.text, created_at),
    )
    return Step(id=cursor.lastrowid or 0, created_at=created_at, **step.model_dump())


@app.post("/api/claims/{claim_id}/decision", operation_id="record_decision")
def record_decision(claim_id: str, decision: Decision, connection: Database) -> Claim:
    """Approve, decline or refer a claim, with the payout and the reason."""
    if claim_row(connection, claim_id)["status"] != "in_progress":
        raise HTTPException(409, f"{claim_id} is not in progress.")
    over_limit = decision.payout > payout_limit(connection)
    status = "awaiting_sign_off" if over_limit else "decided"
    connection.execute(
        "UPDATE claims SET status = ?, decision = ?, payout = ?, reason = ?,"
        " policy_section = ?, decided_at = ? WHERE claim_id = ?",
        (
            status,
            decision.decision,
            decision.payout,
            decision.reason,
            decision.policy_section,
            now(),
            claim_id,
        ),
    )
    return to_claim(claim_row(connection, claim_id))


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: PaymentRequest, connection: Database) -> Claim:
    """Pay the approved payout on a claim."""
    row = claim_row(connection, claim_id)
    limit = payout_limit(connection)
    if row["decision"] != "approve":
        raise HTTPException(409, f"{claim_id} has no approved payout to pay.")
    if row["paid_at"]:
        raise HTTPException(409, f"{claim_id} has already been paid.")
    if payment.amount != row["payout"]:
        raise HTTPException(
            409,
            f"The approved payout is {money(row['payout'])},"
            f" not {money(payment.amount)}.",
        )
    if row["payout"] > limit:
        raise HTTPException(
            409, f"A payout over {money(limit)} needs a handler's sign-off."
        )
    pay(connection, claim_id, row["payout"], "UnderCover Agent")
    return to_claim(claim_row(connection, claim_id))


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(
    claim_id: str, sign_off: SignOffRequest, connection: Database
) -> Claim:
    """Sign off a payout over the limit as a handler, which releases the payment."""
    row = claim_row(connection, claim_id)
    if row["status"] != "awaiting_sign_off":
        raise HTTPException(409, f"{claim_id} is not waiting for sign-off.")
    handler = Handler(
        **json.loads(
            fetch(
                connection,
                "SELECT data FROM handlers WHERE handler_id = ?",
                sign_off.handler_id,
            )["data"]
        )
    )
    if not handler.can_approve_over_limit:
        raise HTTPException(
            409,
            f"{handler.name} cannot sign off payouts over"
            f" {money(payout_limit(connection))}.",
        )
    connection.execute(
        "UPDATE claims SET status = 'decided', signed_off_by = ?, signed_off_at = ?"
        " WHERE claim_id = ?",
        (handler.handler_id, now(), claim_id),
    )
    pay(connection, claim_id, row["payout"], handler.name)
    return to_claim(claim_row(connection, claim_id))
