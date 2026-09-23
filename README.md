# Agent Workspace — reusable AI-agent application foundation

![ci](https://github.com/BAITC-Hacks/hack-1c29d967-bekbalbek/actions/workflows/ci.yml/badge.svg)

A complete, working foundation for a business-case agent app that you adapt in one replaceable module:
the user submits a goal, an agent investigates with typed tools, returns a structured proposal (or asks for
missing input, or explains why the task is infeasible), the backend validates the proposal against deterministic
business rules, the user applies it with one click, and the backend verifies the resulting database state.
Every tool call and state change streams to the UI as a persisted event.

Sample domain (clearly marked as sample data): **field-service dispatch** — assign open jobs to technicians under
skill, capacity, deadline, availability and zone rules.

| Layer | Stack |
|---|---|
| Frontend | React 19, TypeScript, Vite, plain CSS design tokens ([docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md)), vitest + Testing Library, Playwright |
| Backend | FastAPI, OpenAI Agents SDK 0.22, Pydantic 2, SQLAlchemy 2 async + asyncpg, Alembic, sse-starlette, pytest |
| Database | PostgreSQL 16 (Docker Compose, health check, persistent volume) |

## Quick start

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), Node 22 + [pnpm](https://pnpm.io), `curl` (used by `make stack`
and the smoke script), `jq` for the smoke script. Python 3.12 is installed by uv automatically. The Docker-only path
(`make stack`) needs only Docker and curl.

```bash
cp .env.example .env              # scripted demo out of the box; add OPENAI_API_KEY + a real OPENAI_MODEL for the live model
make install web-install           # backend (uv sync) + frontend (pnpm install)
make demo                          # docker compose up db → alembic upgrade head → seed sample data
make api                           # terminal 1: FastAPI on http://localhost:8000 (OpenAPI UI at /docs, also on :8080 via the stack)
make web                           # terminal 2: Vite on http://localhost:5173 (proxies /api to :8000)
```

Open http://localhost:5173 — the landing page; "Open the demo" leads to the workspace at `#/app`. Pick a case on the
left, press **Run analysis**, watch the tool calls stream in, review the proposed changes overlaid on the table,
acknowledge any warning, press **Apply proposal**, and read the verification with the before → after load table.
`make smoke` does the same flow with curl.

`make smoke` starts example 1, prints every persisted event (real tool calls with their labels), applies the proposal,
shows the verification summary, tries a duplicate apply, and reads the resulting database state. `POST /api/domain/reset`
makes it repeatable.

### No API key? Deterministic scripted mode

```bash
OPENAI_MODEL=scripted:auto make api
```

The model is replaced by canned conversations (`backend/app/domain/scripts.py`); tools, validation, execution and
verification are the real thing. `scripted:auto` picks the right script per case (`happy`, `needs_input`,
`infeasible`, `reduced_capacity`). Other keys: `revision`, `tool_failure`, `model_error`. This is also the on-stage
fallback if the model provider is down.

### Everything in Docker (no local Python or Node)

```bash
make stack        # builds api + web images, starts db + api + web, waits for health
# then open http://localhost:8080 in a browser
make stack-down   # stop everything (the database volume is kept)
```

The containers use the `OPENAI_API_KEY` and `OPENAI_MODEL` values from `.env` (compose substitutes them) — `.env.example`
ships in scripted mode, so `cp .env.example .env && make stack` demos without a key; to run without a key set
`OPENAI_MODEL=scripted:auto` in `.env` (or leave both unset, in which case compose defaults the model to
`scripted:auto`). Every `make stack` applies migrations and reloads the sample data, so a second `make stack` resets
what the first session produced; `SEED_ON_START=0 make stack` keeps existing data (seeding runs only when
`SEED_ON_START` is `1`, the default).

## Demo script (what the API can show)

1. **Normal path** — example 1 (`GET /api/domain/examples`) → `POST /api/runs` → 4 real tool calls (`get_case`,
   `lookup_rules`, `find_resources`, `simulate_plan`) → proposal with 6 assignments, 1 zone warning → `POST .../apply` → verified.
2. **Changed condition** — example 4 ("Chen at half capacity") → a different plan (j-104 moves to Ana on 26 Sep).
3. **Missing information** — example 2 → `needs_input` names `jobs.j-107.required_skill`; re-post with `input.job_overrides`.
4. **Infeasible** — example 3 → blocking constraints with rule ids and record refs.
5. **Safety** — example 1 → before applying, `PATCH /api/domain/workers/w-chen {"unavailable_dates": ["2026-09-24"]}`
   → apply → `409 stale_proposal`. Apply twice → `409 duplicate_apply`. Restart the API mid-run → run marked `interrupted`.

## Commands

| Command | What it does |
|---|---|
| `make up` / `make down` | Start / stop PostgreSQL (data volume kept) |
| `make stack` / `make stack-down` | Whole stack in Docker on http://localhost:8080 |
| `make migrate` | `alembic upgrade head` |
| `make seed` | Reset the sample dataset |
| `make api` | Run the backend |
| `make api-demo` | Backend without auto-reload, for live demos (a file save cannot interrupt a run) |
| `make demo-offline` | Backend in scripted mode, no API key needed |
| `make smoke` | curl walkthrough of the whole flow |
| `make test` | Backend tests (pytest, needs the DB) |
| `make eval` | Evaluation suite, scripted model (`EVAL_MODEL=live make eval` for the real model) |
| `make web` / `make web-build` | Frontend dev server / production build into `frontend/dist` |
| `make test-web` | Frontend unit tests (vitest, no backend needed) |
| `make e2e` | Playwright flow against the running stack (landing, happy path, needs input, infeasible, stale proposal) |
| `make lint` | ruff + eslint |

Backend tests use a separate `agent_workspace_test` database and evals use `agent_workspace_eval`; both are created
automatically on the same server.

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://agent:agent@localhost:5433/agent_workspace` | asyncpg URL (host port 5433) |
| `OPENAI_API_KEY` | — | Backend only, never sent to the browser |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Model name, or `scripted:<name>` (`.env.example` ships `scripted:auto`) |
| `AGENT_MAX_TURNS` | `12` | Max model turns per invocation |
| `AGENT_RUN_TIMEOUT_SECONDS` | `120` | Whole-run timeout |
| `TOOL_TIMEOUT_SECONDS` / `TOOL_MAX_RETRIES` | `15` / `2` | Per-tool timeout and retries for transient failures |
| `TOOL_RESULT_MAX_CHARS` | `6000` | Tool results are truncated beyond this |
| `AGENT_MAX_REVISIONS` | `1` | Bounded revisions after a validation failure |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma separated |

## How it works

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) (flow, reliability, layout), [docs/API.md](docs/API.md)
(endpoints + event contract), [docs/DESIGN_SYSTEM.md](docs/DESIGN_SYSTEM.md) (UI system) and
[docs/SWAPPING_THE_DOMAIN.md](docs/SWAPPING_THE_DOMAIN.md) (what to replace for the real case).

Key guarantees:

- The agent only reads and simulates. Writes happen in `domain/service.py::execute_actions`, inside one transaction,
  keyed by unique action ids. Approval is bound to an immutable `(proposal_id, version)`.
- Before executing, the backend recomputes a fingerprint of the records the proposal depends on and re-validates;
  changed data → `409 stale_proposal`. A partial unique index allows one live application per proposal →
  `409 duplicate_apply`, also under concurrency.
- After executing, `verify_outcome` reads the committed state back; the run is `verified` only if that check passes.
- Model claims are never trusted: validation results, execution status and verification come from application code.
- Every event is persisted with a per-run sequence; SSE reconnects with `Last-Event-ID` lose nothing.
- On restart, in-flight runs are marked `interrupted` (nothing resumes silently).

## Evaluation results

`make eval` (scripted model, n = 9 scenarios, one run each, measured on this machine):

```
scenario                       ok   status             outcome         violations   state       ms tools
normal_success                 PASS verified           proposal_ready  -            ok         727     4
missing_information            PASS needs_input        needs_input     -            ok         192     1
impossible_constraints         PASS infeasible         infeasible      -            ok         238     2
tool_failure                   PASS proposed           proposal_ready  -            ok         313     2
changed_resource_availability  PASS verified           proposal_ready  -            ok         600     4
duplicate_apply                PASS verified           proposal_ready  -            ok         863     4
stale_proposal                 PASS proposed           proposal_ready  -            ok         559     4
bounded_revision               PASS proposed           proposal_ready  -            ok         404     2
model_failure                  PASS failed             None            -            ok         169     1
9/9 scenarios passed
```

Token usage is 0 in scripted mode; live mode records real usage per run. Live results depend on the model and are
not reproducible run-to-run — report the actual table from your machine.

## What to replace for the real business case

Everything domain-specific is in `backend/app/domain/` (data models, `CaseInput`, proposal/action schemas, agent
instructions, tools, rules, executor, verifier, seed, examples, scripts). The contract between it and the rest of the
app is `DomainModule` in `backend/app/core/contracts.py`. On the frontend the same split is `frontend/src/domain/`
(`dispatch.ts`: table columns, change rows, before/after, evidence lookup, missing-field mapping) plus the domain types at
the bottom of `frontend/src/api/types.ts`; the contract is the `DomainAdapter` interface in
`frontend/src/dashboard/model/adapter.ts` (`beforeAfterLabel` for the before/after table's header, and an optional
`DemoPanel` component for demo-only controls) — everything else only knows the run/event contract. Domain-only
endpoints, such as the worker patch the demo panel uses, live in `frontend/src/domain/api.ts` and call `api.request`.
Landing copy and brand live in `frontend/src/config.ts`. Step-by-step checklist:
[docs/SWAPPING_THE_DOMAIN.md](docs/SWAPPING_THE_DOMAIN.md).

Adding capabilities (transcription, image understanding, document retrieval, image generation): add them as separate
tools in the domain module with explicit typed inputs/outputs; the runtime wraps them with the same timeouts,
retries, bounded output and events.

## Repository layout

```
backend/   FastAPI app (app/core = runtime, app/domain = replaceable), alembic/, evals/, tests/, scripts/, Dockerfile
frontend/  Vite app (src/api = contract, src/dashboard = generic UI, src/domain = replaceable, src/landing), e2e/, Dockerfile
docs/      architecture, API + event contract, design system, domain-swap guide
docker-compose.yml, Makefile, .env.example
.github/workflows/ci.yml  lint + tests for both halves on every push
```
