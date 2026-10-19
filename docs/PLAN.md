# Plan: the claims pilot

This plan builds the pilot in `docs/SPEC.md`: a backend that holds the claims queue, the UnderCover Agent that decides claims through the backend's API, and a dashboard where handlers follow the queue, each claim, the agent's steps and its instructions.

## How it fits together

```
dashboard (React)  ──HTTP──▶  backend (FastAPI + SQLite)  ◀──HTTP──  agent (create_agent)
                                     ▲
                              seeded from data/
                     (never data/evals/ or data/security/)
```

- **The backend is the single source of truth.** It loads `data/` into SQLite, holds each claim's status, decision, steps and payment, and enforces the rules. The agent and the dashboard only talk to it over HTTP.
- **The rules live in the backend, not in the prompt.** The $1,000 sign-off limit is checked by the pay operation, so the payment is blocked even if the agent tries to pay. The prompt tells the agent the rule too, but the backend doesn't rely on the agent following it.
- **The agent's instructions live in the backend.** The agent fetches them through the API at the start of each run, and the dashboard shows the same text read only. One copy, so what handlers see is what the agent got.
- **The agent never sees the answer key.** The seed reads only the named files in `data/`. Nothing in `backend/` or `agent/` refers to `data/evals/`, and a test checks that.

### Claim statuses

| Status | Label | Set when | Color |
|---|---|---|---|
| `waiting` | Waiting | seeded | Marigold |
| `in_progress` | In progress | the agent starts the claim | Cerulean |
| `awaiting_sign_off` | Waiting for sign-off | the agent approves a payout over $1,000 | Coral |
| `decided` | Decided | the agent declines, refers or approves $1,000 or less, or a handler signs off | Sea Green |

A referred claim is `decided` from the agent's point of view: the decision is "refer", and it's now with a handler.

### The API

Every operation has an `operation_id`, a one-line docstring and no optional inputs. Request and response bodies are Pydantic models.

| Method and path | `operation_id` | What it does |
|---|---|---|
| `GET /api/health` | `health` | Already built |
| `GET /api/claims` | `list_claims` | The queue: id, type, summary, amount claimed, status, decision, payout |
| `GET /api/claims/{claim_id}` | `get_claim` | One claim in full: story, items, documents, status, decision, payment, sign-off |
| `GET /api/policies/{policy_id}` | `get_policy` | The policy with its plan's limits and the add-ons it has |
| `GET /api/customers/{customer_id}/claims` | `get_claim_history` | The customer's earlier claims only, no contact details |
| `GET /api/policy-wording` | `get_policy_wording` | `data/policy_wording.md` as text |
| `GET /api/instructions` | `get_instructions` | The agent's instructions as text |
| `POST /api/claims/{claim_id}/start` | `start_claim` | Moves a claim to `in_progress` and clears earlier steps |
| `GET /api/claims/{claim_id}/steps` | `list_steps` | The agent's steps on the claim, oldest first |
| `POST /api/claims/{claim_id}/steps` | `add_step` | Records one step: a kind (`tool_call`, `tool_result`, `message`) and text |
| `POST /api/claims/{claim_id}/decision` | `record_decision` | Records approve, decline or refer, the payout, the reason and the policy section |
| `POST /api/claims/{claim_id}/payment` | `pay_claim` | Pays the amount. Refused unless the claim is approved, the amount equals the approved payout, it isn't already paid, and a payout over $1,000 has a handler's sign-off |
| `POST /api/claims/{claim_id}/sign-off` | `sign_off_claim` | A handler who can approve over the limit signs off, the payment is released and the claim is `decided` |
| `GET /api/handlers` | `list_handlers` | The handlers, for the sign-off control |

Refusals use `409 Conflict` with a plain-English `detail`, such as "A payout over $1,000.00 needs a handler's sign-off." Unknown ids return `404`. The payout is always given: `0` for a decline or a referral.

"No real payments": a payment is a row in the `payments` table with the amount, the date and who released it (the agent or a handler).

### Running the agent

`uv run -m agent CLM-1001` works one claim, and `uv run -m agent` works every claim that's waiting, one after the other. The entry point stays `run(claim_id, thread_id)`. The run:

1. calls `start_claim` and `get_instructions`
2. runs `create_agent` with the tools below, streaming its updates
3. posts each tool call, tool result and message to `add_step` as it happens, so the dashboard can show it live

The tools are thin wrappers on the API: `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `record_decision` and `pay_claim`. The agent works out the payout itself from the policy wording and the plan's limits. The instructions tell it to read everything, decide, record the decision with a two or three sentence reason and the section of the wording it relied on, and pay an approval only when it's $1,000 or less.

Why a command and not a button in the dashboard: it keeps the backend from depending on the agent, and the spec asks the dashboard to show the agent's work, not to drive it. A "Run" button is easy to add later if the team wants one.

### Choices to review

- **SQLite file:** `undercover.db` at the repo root, gitignored, path overridable with the `UNDERCOVER_DB` environment variable so tests and the e2e run use their own. The backend seeds it on startup when it's empty. `uv run -m backend.seed` rebuilds it from `data/`, which resets the queue.
- **No ORM:** the standard library's `sqlite3` with a handful of tables. It's the simplest thing that works for 25 claims.
- **Dashboard routing:** three views (Queue, Claim, Instructions) switched by the URL hash, so no router library.
- **Live steps:** the claim page polls `list_steps` and `get_claim` every two seconds while the claim is in progress. Simpler than websockets and enough for one agent at a time.
- **The pilot doesn't score the agent against `data/evals/`.** The spec keeps that for checking later, and `docs/PROCESS.md` says not to open it unless asked.

## Phase 1: Data and the read API

Builds the database, the seed and the read operations, so everything after has real claims to work with.

- `backend/db.py`: the schema (claims, claim items, documents, policies, plans, add-ons, customers, earlier claims, handlers, steps, decisions, payments, sign-offs) and a connection helper that reads `UNDERCOVER_DB`.
- `backend/seed.py`: loads `claims.json`, `policies.json`, `customers.json`, `plans.json`, `handlers.json` and `company.json`. Runnable as `uv run -m backend.seed`.
- `backend/main.py`: seeds on startup when empty, and the read operations: `list_claims`, `get_claim`, `get_policy`, `get_claim_history`, `get_policy_wording`, `get_instructions`, `list_handlers`.
- `backend/instructions.md`: a first version of the agent's instructions.
- `.gitignore`: `*.db`.

Success criteria:

- [x] `uv run -m backend.seed` creates `undercover.db` and prints that it loaded 25 claims, 50 policies, 49 customers and 3 handlers
- [x] `GET /api/claims` returns 25 claims, all `waiting`, CLM-1001 first
- [x] `GET /api/claims/CLM-1001` returns the story, 3 items totaling $420.00 and the Meridian Air cancellation notice
- [x] `GET /api/policies/POL-2001` returns the Premium plan with a $50 deductible and an $800 trip delay maximum
- [x] `GET /api/customers/CUS-3001/claims` returns CLM-0412 and no email, phone, address or date of birth
- [x] `GET /api/policy-wording` returns text starting "# UnderCover Travel Insurance: Policy Wording"
- [x] `GET /api/claims/CLM-9999` returns 404
- [x] Every route in `/openapi.json` has an `operation_id` and a summary, checked by a test
- [x] A test checks that no file in `backend/` or `agent/` mentions `evals`, and that CLM-1901 from `data/security/` is not in the queue
- [x] Pytest passes with coverage of 80% or more; ruff and pyright are clean

## Phase 2: Decisions, steps, payments and sign-off

Builds the write operations and the sign-off rule, so the system enforces the rules before an agent ever touches it.

- `start_claim`, `list_steps`, `add_step`, `record_decision`, `pay_claim`, `sign_off_claim`.
- The status changes in the table above, and the payment checks in the backend.

Success criteria:

- [x] `start_claim` on CLM-1001 sets it to `in_progress`; `add_step` then `list_steps` returns the step
- [x] Recording a decline sets the claim to `decided` with payout $0.00; paying it returns 409
- [x] Approving $420.00 then paying $420.00 records the payment and sets `decided`; paying again returns 409; paying a different amount returns 409
- [x] Approving $1,250.00 sets `awaiting_sign_off`; paying $1,250.00 returns 409 "A payout over $1,000.00 needs a handler's sign-off." and no payment is recorded
- [x] `sign_off_claim` by HND-01 records the sign-off, releases the $1,250.00 payment and sets `decided`
- [x] `sign_off_claim` by a handler who can't approve over the limit returns 409; sign-off on a claim not waiting for sign-off returns 409
- [x] Recording a decision with a decision other than approve, decline or refer returns 422
- [x] Pytest passes with coverage of 80% or more; ruff and pyright are clean

## Phase 3: The UnderCover Agent

Replaces the hello-world agent with one that works a claim through the API.

- `agent/main.py`: the tools, `run(claim_id, thread_id)` fetching its instructions from the backend and posting each step, and the model from `MODEL_NAME` or `openai/gpt-6-luna` at low reasoning effort.
- `agent/__main__.py`: `uv run -m agent [CLAIM_ID]`.
- `backend/instructions.md`: the full instructions: the order of work, how to choose approve, decline or refer from the wording, how to work out the payout (plan maximums, per-item limits, deductibles, refunds taken off), the $1,000 rule, and the shape of the reason.

Success criteria:

- [x] A stub-model test runs CLM-1001 through `get_claim`, `get_policy`, `get_policy_wording`, `record_decision` (approve $420.00) and `pay_claim`; the claim ends `decided` with a payment, and `list_steps` shows each tool call and result in order
- [x] A stub-model test where the agent approves $1,250.00 and then calls `pay_claim` gets the 409 back as a tool result, no payment is recorded, and the claim stays `awaiting_sign_off`
- [x] A test checks that `run` uses the instructions served by `get_instructions`
- [x] `MODEL_NAME` test still passes (default `openai/gpt-6-luna`, override honored)
- [x] With the backend running, `uv run -m agent CLM-1001` with the real model records a decision with a payout, a two or three sentence reason and a policy section, and prints them
- [x] Pytest passes with coverage of 80% or more; ruff and pyright are clean

## Phase 4: The dashboard queue and the brand

Builds the dashboard's frame and the queue.

- `dashboard/index.html`: Instrument Sans, Instrument Serif and JetBrains Mono from Google Fonts.
- `dashboard/src/styles.css`: the brand colors and surfaces as CSS variables, light and dark mode from `prefers-color-scheme`, rounded panels with no outlines.
- `dashboard/src/api.ts`: typed fetch functions and types for the API.
- `dashboard/src/Queue.tsx`: the queue as a table: claim id (mono), type, summary, amount claimed, status chip, decision and payout. A count of claims in each status above it. Rows link to the claim.
- `dashboard/src/App.tsx`: a header with the name and the three views, switched by the URL hash.
- `dashboard/src/format.ts`: money as `$1,250.00` and plain labels for statuses and claim types.

Success criteria:

- [ ] Vitest tests cover the queue table, the status counts, money formatting and the hash routing, with a stubbed `fetch`; coverage 80% or more
- [ ] ESLint, Prettier and `tsc` are clean, with no `any`
- [ ] With `npm run dev`, the Playwright MCP server shows the queue at `http://localhost:5173` with 25 claims and status chips in the brand colors, in light and dark mode, with no console errors
- [ ] At a phone width of 390px the queue has no horizontal page scroll

## Phase 5: The claim page and the instructions

Builds the rest of what the team needs to see.

- `dashboard/src/Claim.tsx`: the claim in full: summary, story, items, documents, the policy (plan, trip, add-ons) and earlier claims; the agent's decision, payout, reason and policy section; the payment; and the steps.
- `dashboard/src/Steps.tsx`: the agent's steps in order, tool calls and results shown compactly, updated every two seconds while the claim is in progress.
- A sign-off panel on a claim waiting for sign-off: choose a handler who can approve over the limit, then "Sign off and pay".
- `dashboard/src/Instructions.tsx`: the agent's instructions, read only.

Success criteria:

- [ ] Vitest tests cover the claim page, the steps list, polling while in progress, the sign-off panel and the instructions page; coverage 80% or more
- [ ] ESLint, Prettier and `tsc` are clean
- [ ] With the Playwright MCP server: running `uv run -m agent CLM-1001` while the claim page is open shows the steps appearing, then the decision, reason and payment, with no reload
- [ ] With the Playwright MCP server: a claim set up through the API with a $1,250.00 approval shows "Waiting for sign-off" and no payment; signing off as Dana Whitfield shows the payment and "Decided"
- [ ] The Instructions view shows the same text as `GET /api/instructions` with no way to edit it

## Phase 6: End to end, a live run and handover

Proves the whole thing works together and leaves it ready for the next build.

- `e2e/`: Playwright tests against their own backend on port 8001 and database (`UNDERCOVER_DB`), reseeded at start, with the Vite proxy target read from an environment variable so the dev server isn't touched. Tests: the queue loads with 25 claims; a decision recorded through the API shows on the claim page; the sign-off flow; the instructions page.
- `README.md` section for the product, kept short: install, `npm run dev`, `uv run -m agent`, reset.
- `docs/STATUS.md`: what's built, how to run it and what's left.

Success criteria:

- [ ] `npm run e2e` passes
- [ ] With the real model, `uv run -m agent CLM-1001`, then two more claims of different types, each record a decision and show it on the dashboard; I report the decisions for you to review
- [ ] `npm run check` passes in full
- [ ] `docs/STATUS.md` describes the pilot and how to run it
- [ ] Each phase is committed, with the pre-commit hook passing
