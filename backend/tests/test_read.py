from pathlib import Path

from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from backend.seed import load as seed_data
from backend.seed import seed

ROOT = Path(__file__).parent.parent.parent


def test_seed_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    assert seed() == {"claims": 25, "policies": 50, "customers": 49, "handlers": 3}


def test_startup_seeds_an_empty_database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "fresh.db"))
    with TestClient(app) as client:
        assert len(client.get("/api/claims").json()) == 25
    assert db.path().exists()


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert claims[0]["claim_id"] == "CLM-1001"
    assert {claim["status"] for claim in claims} == {"waiting"}
    assert claims[0]["decision"] is None
    assert claims[0]["customer_name"] == "Maya Patel"
    assert claims[0]["submitted_on"] == "2026-06-24"


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert "Rome" in claim["story"]
    assert len(claim["items"]) == 3
    assert sum(item["amount"] for item in claim["items"]) == 420.0
    assert claim["documents"][0]["name"] == "Meridian Air cancellation notice"
    assert claim["decision"] is None
    assert claim["payment"] is None


def test_unknown_claim(client):
    response = client.get("/api/claims/CLM-9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "CLM-9999 was not found."


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"]["plan"] == "premium"
    assert policy["plan"]["deductible"] == 50.0
    assert policy["plan"]["trip_delay_max"] == 800.0
    assert policy["add_ons"] == []


def test_policy_with_add_ons(client):
    for policy in seed_data("policies.json"):
        served = client.get(f"/api/policies/{policy['policy_id']}").json()
        assert sorted(a["add_on"] for a in served["add_ons"]) == sorted(
            policy["add_ons"]
        )


def test_claim_history_has_no_contact_details(client):
    response = client.get("/api/customers/CUS-3001/claims")
    history = response.json()
    assert [claim["claim_id"] for claim in history] == ["CLM-0412"]
    for field in ["email", "phone", "address", "date_of_birth", "@"]:
        assert field not in response.text


def test_policy_wording(client):
    text = client.get("/api/policy-wording").json()["text"]
    assert text.startswith("# UnderCover Travel Insurance: Policy Wording")


def test_instructions(client):
    assert "UnderCover Agent" in client.get("/api/instructions").json()["text"]


def test_handlers(client):
    handlers = client.get("/api/handlers").json()
    assert len(handlers) == 3
    assert handlers[0]["handler_id"] == "HND-01"


def test_every_operation_is_described(client):
    for path in client.get("/openapi.json").json()["paths"].values():
        for operation in path.values():
            assert operation["operationId"]
            assert operation["description"]
            assert all(p["required"] for p in operation.get("parameters", []))


def test_answer_key_stays_out(client):
    for folder in ["backend", "agent"]:
        for file in (ROOT / folder).rglob("*.py"):
            if "tests" not in file.parts:
                assert "evals" not in file.read_text(encoding="utf-8"), file
    ids = {claim["claim_id"] for claim in client.get("/api/claims").json()}
    assert "CLM-1901" not in ids
