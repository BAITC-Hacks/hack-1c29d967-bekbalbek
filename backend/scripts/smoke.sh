#!/usr/bin/env bash
# End-to-end API smoke test: reset → run → poll → events → apply → verify. Needs the API on $API (default :8000) and jq.
set -euo pipefail
API=${API:-http://localhost:8000}
say() { printf '\n\033[1m%s\033[0m\n' "$*"; }

say "1. health";        curl -sf "$API/api/health" | jq -c '{status,database,model,api_key_configured}'
say "2. reset sample";  curl -sf -X POST "$API/api/domain/reset" | jq -c .seeded
say "3. examples";      curl -sf "$API/api/domain/examples" | jq -r '.examples[] | "   \(.id): \(.expected_outcome)"'
REQ=$(curl -sf "$API/api/domain/examples" | jq -c '.examples[0].request')
say "4. start run";     RUN_ID=$(curl -sf -X POST "$API/api/runs" -H 'content-type: application/json' -d "$REQ" | jq -r .run.id); echo "   run_id=$RUN_ID"
for _ in $(seq 1 60); do
  STATUS=$(curl -sf "$API/api/runs/$RUN_ID" | jq -r .run.status)
  case "$STATUS" in proposed|needs_input|infeasible|validation_failed|failed|interrupted) break;; esac
  sleep 1
done
say "5. status=$STATUS"; curl -sf "$API/api/runs/$RUN_ID" | jq -c '{outcome: .run.outcome, tool_calls: .run.stats.tool_calls, actions: (.proposal.content.actions|length), validation_ok: .proposal.validation.ok}'
say "6. events";        curl -sf "$API/api/runs/$RUN_ID/events/list" | jq -r '.events[] | "   #\(.id) \(.type) \(.payload.label // .payload.outcome // .payload.status // "")"'
PROPOSAL=$(curl -sf "$API/api/runs/$RUN_ID" | jq -c '{proposal_id: .proposal.id, version: .proposal.version}')
say "7. apply";         curl -s -X POST "$API/api/runs/$RUN_ID/apply" -H 'content-type: application/json' -d "$PROPOSAL" | jq -c '{run: .run.status, application: .application.status, verification: .application.verification.summary, error: .error.code}'
say "8. apply again";   curl -s -X POST "$API/api/runs/$RUN_ID/apply" -H 'content-type: application/json' -d "$PROPOSAL" | jq -c '.error | {code, message}'
say "9. db state";      curl -sf "$API/api/domain/cases/case-dispatch-001" | jq -c '{assignments: (.assignments|length), unassigned: ([.jobs[] | select(.status=="unassigned")] | length)}'
say "10. sse replay (first 3 lines)"; curl -sN --max-time 3 "$API/api/runs/$RUN_ID/events" | head -3 || true
