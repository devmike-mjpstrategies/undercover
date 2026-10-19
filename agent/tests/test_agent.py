import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from agent import __main__ as cli
from agent import main
from backend.main import app
from backend.seed import seed


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies in place of a real model."""

    def bind_tools(self, tools, **kwargs):
        return self


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    seed()
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))
    monkeypatch.setattr(cli, "backend", lambda: TestClient(app))
    return TestClient(app)


def tool_call(name, args, id_):
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": id_}])


def stub(*replies):
    return StubModel(messages=iter(replies))


def decision(payout):
    return {
        "claim_id": "CLM-1001",
        "decision": "approve",
        "payout": payout,
        "reason": "The flight was canceled for a crew problem. The costs are covered.",
        "policy_section": "3. Trip Delay",
    }


def test_run_decides_and_pays(client):
    replies = [
        tool_call("get_claim", {"claim_id": "CLM-1001"}, "1"),
        tool_call("get_policy", {"policy_id": "POL-2001"}, "2"),
        tool_call("get_claim_history", {"customer_id": "CUS-3001"}, "3"),
        tool_call("get_policy_wording", {}, "4"),
        tool_call("record_decision", decision(420), "5"),
        tool_call("pay_claim", {"claim_id": "CLM-1001", "amount": 420}, "6"),
        AIMessage(content="Approved $420.00 and paid."),
    ]
    assert main.run("CLM-1001", "thread-1", stub(*replies)) == (
        "Approved $420.00 and paid."
    )
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 420
    steps = client.get("/api/claims/CLM-1001/steps").json()
    names = [s["text"].split()[0] for s in steps if s["kind"] == "tool_call"]
    assert names == [
        "get_claim",
        "get_policy",
        "get_claim_history",
        "get_policy_wording",
        "record_decision",
        "pay_claim",
    ]
    kinds = [s["kind"] for s in steps]
    assert kinds[:2] == ["tool_call", "tool_result"]
    assert kinds[-1] == "message"
    assert "Meridian Air" in steps[1]["text"]


def test_payment_over_the_limit_is_refused(client):
    replies = [
        tool_call("record_decision", decision(1250), "1"),
        tool_call("pay_claim", {"claim_id": "CLM-1001", "amount": 1250}, "2"),
        AIMessage(content="Approved $1,250.00."),
    ]
    main.run("CLM-1001", "thread-1", stub(*replies))
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["status"] == "awaiting_sign_off"
    assert claim["payment"] is None
    results = [
        s["text"]
        for s in client.get("/api/claims/CLM-1001/steps").json()
        if s["kind"] == "tool_result"
    ]
    assert "needs a handler's sign-off" in results[-1]


def test_run_uses_the_served_instructions(client, monkeypatch):
    seen = {}
    real = main.create_agent

    def spy(llm, tools, system_prompt):
        seen["prompt"] = system_prompt
        return real(llm, tools=tools, system_prompt=system_prompt)

    monkeypatch.setattr(main, "create_agent", spy)
    main.run("CLM-1001", "thread-1", stub(AIMessage(content="Done.")))
    assert seen["prompt"] == client.get("/api/instructions").json()["text"]


def test_cli_works_the_waiting_claims(client, monkeypatch, capsys):
    ran = []

    def fake_run(claim_id, thread_id):
        ran.append(claim_id)
        if claim_id == "CLM-1001":
            client.post("/api/claims/CLM-1001/start")
            client.post(
                "/api/claims/CLM-1001/decision",
                json={k: v for k, v in decision(420).items() if k != "claim_id"},
            )
        return ""

    monkeypatch.setattr(cli, "run", fake_run)
    cli.main([])
    assert len(ran) == 25
    output = capsys.readouterr().out
    assert "CLM-1001: approve $420.00 (decided)" in output
    assert "CLM-1002: no decision recorded" in output
    ran.clear()
    cli.main(["CLM-1002"])
    assert ran == ["CLM-1002"]


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
