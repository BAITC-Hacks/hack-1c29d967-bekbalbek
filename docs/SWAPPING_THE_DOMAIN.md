# Swapping the business case

Everything specific to the sample "field-service dispatch" case lives in `backend/app/domain/`, the Python module
exporting `DOMAIN: DomainModule`. The rest of the backend only knows the `DomainModule` interface in
`backend/app/core/contracts.py`. Keep the same split in the frontend: one folder that renders the case view, the
proposed actions and the before/after state.

## Backend checklist

| File | Replace with |
|---|---|
| `domain/models.py` | Your SQLAlchemy tables (add an Alembic migration) |
| `domain/schemas.py` | `CaseInput` (validated request body), `ProposedAction` types, `Proposal` (extends `ProposalBase`) |
| `domain/instructions.py` | Agent task, scope, when to return `needs_input` / `infeasible` |
| `domain/tools.py` | Read-only / simulation tools (`get_case`, `find_resources`, `lookup_rules`, `simulate_plan` are examples). Each has typed args, a label, bounded output |
| `domain/records.py` | Plain in-memory records + `build_plan_context` (applies user overrides) so rules stay DB-free and unit-testable |
| `domain/rules.py` | Rule table with source ids, `evaluate_plan` (deterministic validator) and `simulate` — reused by tools and by the apply path |
| `domain/repo.py` | Loads DB rows into records |
| `domain/service.py` | `load_case_view`, `validate_proposal`, `fingerprint` (staleness), `snapshot` (before/after), `execute_actions` (the only business writes), `verify_outcome` (reads committed state) |
| `domain/seed.py` | Sample data + reset |
| `domain/examples.py` | Example cases shown in the UI and used by evals |
| `domain/scripts.py` | Canned agent conversations for tests, evals and the `OPENAI_MODEL=scripted:<name>` fallback |
| `domain/api.py` | Domain read endpoints (case view, demo controls) |

Then re-run `alembic revision --autogenerate` for your tables and update `evals/scenarios.py`.

## Frontend checklist

- `frontend/src/api/types.ts`, bottom section: replace `Worker`, `Job`, `Assignment`, `Rule`, `CaseView`, `Snapshot` with the shapes your `GET /api/domain/cases/{ref}` and snapshots return.
- `frontend/src/domain/dispatch.ts`: implements the `DomainAdapter` interface (`frontend/src/dashboard/model/adapter.ts`) — `key`, `beforeAfterLabel` (the before/after table's row-label header), the optional `DemoPanel`, `tableFor`, `changesFor`, `beforeAfter`, `describeEvidence`, `applyMissingField`. Keep the same exported shape and rewrite the bodies for your records. `frontend/src/domain/dispatch.test.ts` shows what each one must produce.
- `frontend/src/domain/DemoControls.tsx`: the sample `DemoPanel` — the "change the data before applying" demo button. It calls `patchWorker` in `frontend/src/domain/api.ts` (domain-only endpoints live there and call `api.request`); point it at your own mutation endpoint or delete it (and drop `DemoPanel` from your adapter).
- `frontend/src/config.ts`: brand, hero scenes, landing copy.
- `frontend/src/test/fixtures.ts`: update the fixtures so the dashboard tests exercise your fields.
- Nothing else in the frontend references domain field names; `App.tsx` passes the domain adapter into the dashboard.
