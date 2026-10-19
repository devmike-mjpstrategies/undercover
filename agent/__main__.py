"""Run the UnderCover Agent on one claim, or on every waiting claim in the queue."""

import sys
import uuid

from agent.main import backend, run


def waiting_claims() -> list[str]:
    """Return the ids of the claims still waiting in the queue."""
    with backend() as client:
        claims = client.get("/api/claims").json()
    return [claim["claim_id"] for claim in claims if claim["status"] == "waiting"]


def describe(claim_id: str) -> str:
    """Describe the decision recorded on a claim."""
    with backend() as client:
        claim = client.get(f"/api/claims/{claim_id}").json()
    decision = claim["decision"]
    if decision is None:
        return f"{claim_id}: no decision recorded"
    return (
        f"{claim_id}: {decision['decision']} ${decision['payout']:,.2f}"
        f" ({claim['status']})\n{decision['reason']}\n{decision['policy_section']}"
    )


def main(claim_ids: list[str]) -> None:
    for claim_id in claim_ids or waiting_claims():
        run(claim_id, str(uuid.uuid4()))
        print(describe(claim_id), end="\n\n")


if __name__ == "__main__":
    main(sys.argv[1:])
