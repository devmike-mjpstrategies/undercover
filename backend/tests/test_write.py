import json
from contextlib import closing

import pytest

from backend import db

CLAIM = "/api/claims/CLM-1001"


def decide(client, decision, payout):
    client.post(f"{CLAIM}/start")
    return client.post(
        f"{CLAIM}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reason": "The reason.",
            "policy_section": "Section 3, Trip Delay",
        },
    )


def test_start_and_steps(client):
    assert client.post(f"{CLAIM}/start").json()["status"] == "in_progress"
    step = client.post(f"{CLAIM}/steps", json={"kind": "message", "text": "Reading"})
    assert step.json()["id"] > 0
    steps = client.get(f"{CLAIM}/steps").json()
    assert [(s["kind"], s["text"]) for s in steps] == [("message", "Reading")]


def test_start_clears_earlier_steps(client):
    client.post(f"{CLAIM}/start")
    client.post(f"{CLAIM}/steps", json={"kind": "message", "text": "First run"})
    client.post(f"{CLAIM}/start")
    assert client.get(f"{CLAIM}/steps").json() == []


def test_steps_on_unknown_claim(client):
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


def test_decision_needs_a_started_claim(client):
    response = client.post(
        f"{CLAIM}/decision",
        json={
            "decision": "decline",
            "payout": 0,
            "reason": "r",
            "policy_section": "s",
        },
    )
    assert response.status_code == 409


def test_decline(client):
    claim = decide(client, "decline", 0).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["payout"] == 0
    response = client.post(f"{CLAIM}/payment", json={"amount": 1})
    assert response.status_code == 409
    assert response.json()["detail"] == "CLM-1001 has no approved payout to pay."


def test_start_after_a_decision(client):
    decide(client, "refer", 0)
    assert client.post(f"{CLAIM}/start").status_code == 409


def test_approve_and_pay(client):
    assert decide(client, "approve", 420).json()["status"] == "decided"
    wrong = client.post(f"{CLAIM}/payment", json={"amount": 400})
    assert wrong.status_code == 409
    assert wrong.json()["detail"] == "The approved payout is $420.00, not $400.00."
    claim = client.post(f"{CLAIM}/payment", json={"amount": 420}).json()
    assert claim["payment"]["amount"] == 420
    assert claim["payment"]["released_by"] == "UnderCover Agent"
    again = client.post(f"{CLAIM}/payment", json={"amount": 420})
    assert again.json()["detail"] == "CLM-1001 has already been paid."


def test_payment_over_the_limit_waits_for_sign_off(client):
    assert decide(client, "approve", 1250).json()["status"] == "awaiting_sign_off"
    response = client.post(f"{CLAIM}/payment", json={"amount": 1250})
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "A payout over $1,000.00 needs a handler's sign-off."
    )
    assert client.get(CLAIM).json()["payment"] is None
    claim = client.post(f"{CLAIM}/sign-off", json={"handler_id": "HND-01"}).json()
    assert claim["status"] == "decided"
    assert claim["sign_off"]["handler_id"] == "HND-01"
    assert claim["payment"] == {
        "amount": 1250,
        "released_by": "Dana Whitfield",
        "paid_at": claim["payment"]["paid_at"],
    }


def test_sign_off_needs_a_claim_waiting_for_it(client):
    decide(client, "approve", 420)
    response = client.post(f"{CLAIM}/sign-off", json={"handler_id": "HND-01"})
    assert response.status_code == 409


def test_sign_off_needs_a_handler_who_can(client):
    with closing(db.connect()) as connection, connection:
        handler = {
            "handler_id": "HND-09",
            "name": "Sam Trainee",
            "role": "Trainee",
            "can_approve_over_limit": False,
        }
        connection.execute(
            "INSERT INTO handlers VALUES (?, ?)", ("HND-09", json.dumps(handler))
        )
    decide(client, "approve", 1250)
    response = client.post(f"{CLAIM}/sign-off", json={"handler_id": "HND-09"})
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Sam Trainee cannot sign off payouts over $1,000.00."
    )
    unknown = client.post(f"{CLAIM}/sign-off", json={"handler_id": "HND-99"})
    assert unknown.status_code == 404


@pytest.mark.parametrize(
    ("decision", "payout"), [("pay", 10), ("approve", 0), ("decline", 50)]
)
def test_invalid_decisions(client, decision, payout):
    assert decide(client, decision, payout).status_code == 422
