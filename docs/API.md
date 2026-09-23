# API and event contract

All endpoints are served by the single FastAPI process under `/api`. The frontend talks only to this API. Errors use one envelope:

```json
{ "error": { "code": "stale_proposal", "message": "Human readable", "details": {} } }
```

## Health

`GET /api/health` → `200`

```json
{ "status": "ok" | "degraded", "database": "ok" | "error", "model": "gpt-5.4-mini",
  "api_key_configured": true, "domain": { "key": "dispatch", "title": "Field-service dispatch" },
  "active_runs": 0, "version": "0.1.0" }
```

## Domain data (replaceable module; shapes below are for the sample dispatch domain)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/domain/examples` | Example cases the UI can start from |
| `GET` | `/api/domain/cases/{case_ref}` | Records for the workspace (workers, jobs, assignments, rules) |
| `POST` | `/api/domain/reset` | Reset sample data (repeatable demo) |
| `PATCH` | `/api/domain/workers/{worker_id}` | Demo control: change capacity / availability to show stale-proposal rejection |

`GET /api/domain/examples` → `{ "examples": ExampleCase[] }`

```ts
type ExampleCase = { id: string; title: string; description: string; expected_outcome: "proposal_ready"|"needs_input"|"infeasible";
                     request: { case_ref: string; goal: string; input: CaseInput } }
```

`GET /api/domain/cases/{case_ref}` → `CaseView`

```ts
type CaseView = {
  case_ref: string; title: string; description: string; planning_start: string; dates: string[];           // dates shown in the board
  workers: { id: string; name: string; skills: string[]; zone: string; capacity_hours: number; unavailable_dates: string[] }[];
  jobs:    { id: string; title: string; required_skill: string|null; duration_hours: number|null; deadline: string; priority: "low"|"normal"|"high";
             zone: string; status: "unassigned"|"assigned"|"done" }[];
  assignments: { id: string; job_id: string; worker_id: string; scheduled_date: string; hours: number; source_action_key: string|null }[];
  rules: { id: string; label: string; severity: "fail"|"warn"; source: string; description: string }[];
}
```

## Runs

### `POST /api/runs` → `202 { run: Run }`

```ts
type CreateRunRequest = { case_ref: string; goal: string; input: CaseInput; options?: { max_turns?: number } }
// sample domain CaseInput:
type CaseInput = { planning_start: string; job_ids?: string[]; job_overrides?: Record<string, { required_skill?: string; duration_hours?: number }>;
                   capacity_overrides?: Record<string, number>; notes?: string }
```

`422` on validation errors (FastAPI/Pydantic format).

### `GET /api/runs?limit=50` → `{ runs: Run[] }` (newest first)

### `GET /api/runs/{id}` → `RunDetail`

```ts
type RunStatus = "queued"|"analyzing"|"needs_input"|"infeasible"|"proposed"|"validation_failed"|"applying"|"applied"|"verified"|"failed"|"interrupted"
type Run = { id: string; case_ref: string; goal: string; input: CaseInput; status: RunStatus; outcome: "proposal_ready"|"needs_input"|"infeasible"|null;
             model: string; max_turns: number; error: { code: string; message: string; stage: string }|null;
             stats: { duration_ms: number|null; tool_calls: number; usage: { requests: number; input_tokens: number; output_tokens: number; total_tokens: number }|null };
             created_at: string; started_at: string|null; finished_at: string|null; updated_at: string }
type RunDetail = {
  run: Run;
  proposals: ProposalRecord[];                 // every version, oldest first (v1 rejected, v2 validated, ...)
  proposal: ProposalRecord | null;             // the latest one
  needs_input: { message: string; missing_fields: { field: string; reason: string }[] } | null;
  infeasible:  { message: string; blocking_constraints: { rule_id: string; detail: string; refs: string[] }[] } | null;
  application: Application | null;
  snapshot_before: unknown | null;             // domain snapshot at proposal time
  snapshot_after: unknown | null;              // domain snapshot after verification
  messages: RunMessage[];                      // conversation history (expandable, for debugging)
}
type ProposalRecord = { id: string; run_id: string; version: number; status: "validated"|"rejected"|"superseded"|"applied"|"stale";
                        content: Proposal; validation: ValidationReport; basis_fingerprint: string; created_at: string }
type Proposal = { summary: string; actions: ProposedAction[]; evidence: EvidenceRef[]; assumptions: string[]; expected_effects: string[] }
type ProposedAction = { action_id: string; type: string; [k: string]: unknown }      // sample: type "assign_job" { job_id, worker_id, scheduled_date }
type EvidenceRef = { kind: "record"|"rule"|"tool_result"; ref: string; note: string|null }
type ValidationReport = { ok: boolean; checks: ValidationCheck[]; errors: ValidationCheck[] }
type ValidationCheck = { rule_id: string; label: string; status: "pass"|"warn"|"fail"; message: string; action_id: string|null; refs: string[]; source: string|null }
type Application = { id: string; proposal_id: string; version: number; status: "applying"|"applied"|"verified"|"failed"|"rejected";
                     actions: { id: string; action_id: string; type: string; status: "applied"|"failed"; result: unknown; summary: string }[];
                     verification: VerificationReport | null; error: { code: string; message: string } | null; started_at: string; finished_at: string|null }
type VerificationReport = { ok: boolean; summary: string; checks: { id: string; label: string; ok: boolean; detail: string }[] }
type RunMessage = { seq: number; role: "system"|"user"|"assistant"|"tool"; kind: "message"|"tool_call"|"tool_output"|"final_output"; content: unknown; created_at: string }
```

### `POST /api/runs/{id}/apply` body `{ proposal_id: string; version: number }`

- `200 { run: Run; application: Application }` after execution **and** verification finished.
- `409` with `error.code` one of `stale_proposal` (data changed since the proposal was made, or re-validation failed), `duplicate_apply` (already applying/applied), `invalid_state` (run not in `proposed`, or proposal id/version mismatch).
- `404` unknown run/proposal.

### `GET /api/runs/{id}/events` — Server-Sent Events

- Replays persisted events, then streams live ones. Reconnect with the `Last-Event-ID` header (browsers do this automatically) or `?after=<seq>`.
- `id` = per-run sequence number, `event` = event type, `data` = JSON `RunEvent`.
- The stream closes when the run reaches a terminal status (`verified`, `failed`, `interrupted`, `infeasible`, `needs_input`, `validation_failed`). It stays open while `proposed` so the apply phase streams into the same timeline.
- `GET /api/runs/{id}/events/list` returns the same events as JSON for non-streaming reads.

```ts
type RunEvent = { id: number; run_id: string; type: EventType; ts: string; run_status: RunStatus; payload: EventPayload }
type EventType = "run_started"|"tool_started"|"tool_finished"|"tool_failed"|"agent_output"|"proposal_ready"|"validation_failed"|"revision_started"
               | "apply_started"|"apply_rejected"|"action_applied"|"verification_finished"|"run_finished"|"run_failed"
```

Payloads:

| type | payload |
|---|---|
| `run_started` | `{ goal, case_ref, model, max_turns }` |
| `tool_started` | `{ call_id, tool, label, arguments }` |
| `tool_finished` | `{ call_id, tool, label, duration_ms, attempt, summary, result, truncated }` |
| `tool_failed` | `{ call_id, tool, label, duration_ms, attempt, will_retry, error: { code, message } }` |
| `agent_output` | `{ outcome, message, missing_fields, blocking_constraints, action_count }` |
| `proposal_ready` | `{ proposal_id, version, summary, action_count, validation: ValidationReport }` |
| `validation_failed` | `{ proposal_id, version, errors: ValidationCheck[], will_revise }` |
| `revision_started` | `{ attempt, reason }` |
| `apply_started` | `{ application_id, proposal_id, version }` |
| `apply_rejected` | `{ code, message, details }` |
| `action_applied` | `{ action_id, type, summary, result }` |
| `verification_finished` | `{ ok, summary, checks }` |
| `run_finished` | `{ outcome, status, duration_ms, tool_calls, usage }` |
| `run_failed` | `{ code, message, stage, details }` |

`label` is the plain-language label from the domain tool registry (e.g. `get_case` → "Reading the case"). `arguments`/`result` are bounded (truncated with `truncated: true`).
