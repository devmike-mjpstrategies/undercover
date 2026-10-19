# Status

The claims pilot is built. See `docs/PLAN.md` for how it was planned.

## Built

- `backend/`: FastAPI on SQLite. The database (`undercover.db`, or the file in `UNDERCOVER_DB`) is loaded from `data/` on startup when it doesn't exist; `data/evals/` and `data/security/` are never read. It serves claims, policies with their plan's limits, claim history without contact details, the policy wording and the agent's instructions (`backend/instructions.md`), and records steps, decisions, payments and sign-offs. A payout over $1,000 is paid only after a handler's sign-off: the pay operation refuses it before then, whoever asks.
- `agent/`: the UnderCover Agent, `create_agent` on OpenRouter with tools for the claim, the policy, the claim history, the policy wording, recording the decision and paying. It fetches its instructions from the backend and records each step there as it works. It uses `MODEL_NAME` if set, or `openai/gpt-6-luna` at low reasoning effort.
- `dashboard/`: the UnderCover brand in light and dark mode. The queue shows claims by status and every claim with its status, decision and payout. Each claim's page shows the claim in full, the policy and earlier claims, the decision and payment, the agent's steps as they happen, and a sign-off panel for payouts over $1,000. The Instructions view shows the agent's instructions, read only.
- `e2e/`: Playwright tests of the queue, a decision on the claim page, the sign-off flow and the instructions. They run against their own backend (port 8001, `e2e/undercover-e2e.db`, reseeded each run) and a production build of the dashboard (port 5174), so they never touch the dev servers or data.

## Run it

- `npm run dev` starts the backend on port 8000 and the dashboard at http://localhost:5173.
- `uv run -m agent CLM-1001` works one claim; `uv run -m agent` works every waiting claim. The backend must be running.
- `uv run -m backend.seed` rebuilds the database from `data/`, which resets the queue. Stop the backend first.
- `npm run check` runs every check.

## Not yet

- The agent isn't scored against `data/evals/`.
- The claims manual isn't used; the agent works from the policy wording alone.
