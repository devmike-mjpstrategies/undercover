# Status

The claims pilot, in progress. See `docs/PLAN.md` for the phases.

## Built

- `backend/`: FastAPI on SQLite. The database (`undercover.db`, or the file in `UNDERCOVER_DB`) is loaded from `data/` on startup when it doesn't exist. Read operations for claims, policies, claim history, the policy wording, the instructions and handlers; write operations to start a claim, record steps and decisions, pay a claim and sign off. Payouts over $1,000 are paid only after a handler's sign-off. The agent's instructions are in `backend/instructions.md`.
- `agent/`: the UnderCover Agent, `create_agent` with tools for the claim, the policy, the claim history, the policy wording, recording the decision and paying. It fetches its instructions from the backend and records each step there as it works.
- `dashboard/`: still the page that shows whether the backend is up.
- `e2e/`: one test of that page.

## Run it

- `npm run dev` starts the backend and the dashboard.
- `uv run -m agent CLM-1001` works one claim; `uv run -m agent` works every waiting claim. The backend must be running.
- `uv run -m backend.seed` rebuilds the database from `data/`, which resets the queue.
