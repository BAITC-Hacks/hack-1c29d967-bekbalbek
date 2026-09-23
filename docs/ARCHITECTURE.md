# Architecture

One repository, one FastAPI process, one PostgreSQL database, one Vite/React frontend that talks only to the API.

```
frontend (React)    ──HTTP/SSE──▶  backend (FastAPI)  ──asyncpg──▶  PostgreSQL
                                                 │
                                                 ├─ app/core      domain-independent runtime
                                                 ├─ app/domain    REPLACEABLE business module
                                                 └─ OpenAI Agents SDK (model calls; key stays on the server)
```

## Backend layout

```
backend/
├── app/
│   ├── main.py            FastAPI app factory, lifespan (mark interrupted runs), routers
│   ├── config.py          Settings from environment (pydantic-settings)
│   ├── db/
│   │   ├── engine.py      async engine + session factory (one session per request / task)
│   │   ├── base.py        DeclarativeBase
│   │   └── models.py      core tables: runs, run_events, run_messages, proposals, applications, actions
│   ├── core/
│   │   ├── contracts.py   DomainModule interface + shared Pydantic types (AgentOutput, ValidationReport, ...)
│   │   ├── events.py      event types, persistence, in-process broadcast for SSE
│   │   ├── tooling.py     wraps domain tools: timeout, retries, bounded output, structured errors, events
│   │   ├── agent_runtime.py  builds the Agent and runs it with limits (SDK Runner owns the loop)
│   │   ├── run_service.py analysis pipeline: agent → parse → validate → bounded revision → persist
│   │   ├── apply_service.py apply pipeline: stale check → transactional execution → verification
│   │   ├── run_registry.py in-process background task registry
│   │   └── errors.py      typed application errors mapped to HTTP
│   ├── api/               routers + request/response schemas + SSE endpoint
│   └── domain/            the replaceable module (see docs/SWAPPING_THE_DOMAIN.md)
├── alembic/               migrations (async env)
├── evals/                 scenario runner (scripted model by default, live model optional)
├── scripts/               seed
└── tests/
```

## Execution flow

1. `POST /api/runs` validates the body against the domain `CaseInput` model, stores the run (`queued`), and starts a background task in the same process.
2. The task marks the run `analyzing`, emits `run_started`, and calls `Runner.run` with the domain agent. Every tool call is wrapped by `core/tooling.py`, which emits `tool_started` / `tool_finished` / `tool_failed`, enforces per-tool timeouts, retries transient read failures, bounds result size, and returns structured errors to the model instead of raising.
3. The agent returns `AgentOutput` (`proposal_ready` | `needs_input` | `infeasible`). The backend never trusts model claims about success; it only stores what the model said.
4. For `proposal_ready` the backend runs `domain.validate_proposal` (deterministic rules + referenced-record existence). Failing validation stores the proposal as `rejected`, emits `validation_failed`, and allows **one** bounded revision: the same conversation continues with the concrete validation errors. The revised proposal is validated again.
5. A validated proposal is stored immutably as `proposals(run_id, version)` with a `basis_fingerprint` (hash of the records it depends on) and a `snapshot_before`. The run becomes `proposed` and the agent invocation ends. Nothing waits for the user.
6. `POST /api/runs/{id}/apply` binds approval to `(proposal_id, version)`. It inserts an `applications` row (unique per proposal → duplicate requests get `409 duplicate_apply`), recomputes the fingerprint and re-validates (`409 stale_proposal` on mismatch), then executes every action inside **one transaction** with a unique `actions.action_key`. Afterwards it reads the committed state back through `domain.verify_outcome` and records `verified` or `failed`.
7. Events are persisted to `run_events` (per-run sequence) and broadcast in-process; the SSE endpoint replays from the persisted log and then tails live events, so reconnects with `Last-Event-ID` never lose anything.

## Reliability

- `AGENT_MAX_TURNS`, `AGENT_RUN_TIMEOUT_SECONDS`, `TOOL_TIMEOUT_SECONDS`, `TOOL_MAX_RETRIES`, `TOOL_RESULT_MAX_CHARS`, `AGENT_MAX_REVISIONS` are environment variables.
- Every tool call and every phase transition is an event with a timestamp and payload, so failures can be inspected after the fact.
- On startup the app marks runs still in `queued`, `analyzing` or `applying` as `interrupted`. In-memory tasks do not resume.
- Sessions: each request and each background task opens its own session. Transactions are short; no transaction is open while awaiting the model.

## Frontend (`frontend/`)

React 19 + TypeScript + Vite, no router or state library. Hash routes: `#/` landing, `#/app` dashboard,
`#/app/example/<id>` a case, `#/app/run/<id>` a specific run.

- `src/api/` — `types.ts` mirrors docs/API.md; `client.ts` is a fetch wrapper that turns every error into `ApiError(code, message, status, details)`.
- `src/dashboard/useRun.ts` — the run controller: creates a run, opens the SSE stream, reduces events into a timeline, refreshes the run detail on milestones, applies. Terminal runs are replayed from `GET /events/list` instead of a stream.
- `src/dashboard/model/` — pure functions and the domain contract: `adapter.ts` (`DomainAdapter` — `key`, `beforeAfterLabel`, the optional `DemoPanel`, `tableFor`, `changesFor`, `beforeAfter`, `describeEvidence`, `applyMissingField`), `phase.ts` (status → phase, journey progress, apply gate), `timeline.ts` (event reducer), `runs.ts` (which example a run belongs to), `changes.ts` (generic table/change types).
- `src/dashboard/components/` — top bar, case list, case header + stepper, request card, generic changes table, status cards, agent panel (activity, proposed changes, evidence drawer, apply panel).
- `src/domain/` — the only folder that knows the sample domain's field names: `dispatch.ts` implements `DomainAdapter` (table columns, change rows, before/after, evidence lookup, how a missing field maps into the input, plus `beforeAfterLabel` and `DemoPanel`), `DemoControls.tsx` (the sample `DemoPanel` — the "change the data before applying" demo button) and `api.ts` (domain-only endpoints, e.g. `patchWorker`, calling `api.request`).
- `src/landing/` + `src/config.ts` — marketing page; all copy lives in `config.ts`.

Tests: vitest + Testing Library for the pure models, the controller (fake API + fake EventSource) and the dashboard
flows; Playwright (`frontend/e2e/`) drives the real stack end to end in scripted model mode.
