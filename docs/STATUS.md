# Status

The claims pilot, in progress. See `docs/PLAN.md` for the phases.

## Built

- `backend/`: FastAPI on SQLite. The database (`undercover.db`, or the file in `UNDERCOVER_DB`) is loaded from `data/` on startup when it doesn't exist. Read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`. The agent's instructions are in `backend/instructions.md`.
- `agent/`: still the hello-world agent.
- `dashboard/`: still the page that shows whether the backend is up.
- `e2e/`: one test of that page.

## Run it

- `npm run dev` starts the backend and the dashboard.
- `uv run -m backend.seed` rebuilds the database from `data/`, which resets the queue.
