"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException

from backend import db
from backend.models import (
    AddOn,
    Claim,
    ClaimSummary,
    EarlierClaim,
    Handler,
    Payment,
    Plan,
    Policy,
    RecordedDecision,
    SignOff,
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
    rows = connection.execute("SELECT * FROM claims ORDER BY position").fetchall()
    return [
        ClaimSummary(
            **json.loads(row["data"])
            | {
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
