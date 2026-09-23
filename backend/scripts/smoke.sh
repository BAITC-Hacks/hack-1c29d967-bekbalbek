#!/usr/bin/env bash
# Upload a new meeting, transcribe, review its generated protocol, confirm and export.
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
BACKEND_DIR=$(cd -- "$SCRIPT_DIR/.." && pwd)
API=${API:-http://localhost:8080}
API=${API%/}
FILE=${FILE:-"$BACKEND_DIR/samples/sovechanie_2.mp3"}
MEETING_DATE=${MEETING_DATE:-2026-09-23}
TITLE=${TITLE:-"Проверка протокола совещания"}
OUTPUT_DIR=${OUTPUT_DIR:-"$BACKEND_DIR/media/verification/smoke-$(date +%Y%m%d-%H%M%S)-$$"}
TRANSCRIBE_TIMEOUT=${TRANSCRIBE_TIMEOUT:-1200}
RUN_TIMEOUT=${RUN_TIMEOUT:-1200}

for dependency in curl jq od; do
  command -v "$dependency" >/dev/null || { echo "Missing command: $dependency" >&2; exit 1; }
done
[[ -s "$FILE" ]] || { echo "Audio file missing or empty: $FILE" >&2; exit 1; }
[[ "$TRANSCRIBE_TIMEOUT" =~ ^[1-9][0-9]*$ && "$RUN_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
  echo 'Timeouts must be positive integer seconds.' >&2
  exit 1
}
mkdir -p -- "$OUTPUT_DIR"

fail() {
  echo "ERROR: $*" >&2
  echo "Proof files: $OUTPUT_DIR" >&2
  exit 1
}

request() {
  local expected=$1 output=$2 path=$3 code
  shift 3
  code=$(curl --silent --show-error --connect-timeout 10 --max-time 60 \
    --output "$OUTPUT_DIR/$output" --write-out '%{http_code}' "$@" "$API$path") || fail "Request failed: $path"
  [[ "$code" == "$expected" ]] || fail "$path returned HTTP $code (expected $expected); see $output"
}

request 200 health-before.json /api/health
jq -e '.status == "ok" and .database == "ok" and .models_present == true and
  .provenance.enabled == true and .provenance.blocked_external_connections == 0 and
  (.model | type == "string" and length > 0)' "$OUTPUT_DIR/health-before.json" >/dev/null || fail 'Health, local models or provenance checks failed.'
MODEL=$(jq -r .model "$OUTPUT_DIR/health-before.json")
echo "API: $API; model: $MODEL"
if [[ "$MODEL" == scripted:* ]]; then
  echo 'Scripted demo mode: this checks the workflow, not language-model extraction quality.'
fi

request 202 upload.json /api/domain/meetings -X POST \
  --form "file=@$FILE" --form-string "title=$TITLE" --form-string "meeting_date=$MEETING_DATE"
MEETING_ID=$(jq -er '.meeting.id | select(type == "string" and startswith("m-"))' "$OUTPUT_DIR/upload.json") || fail 'Upload response has no meeting id.'
jq -e '.meeting.status == "uploaded"' "$OUTPUT_DIR/upload.json" >/dev/null || fail 'Meeting was not uploaded.'
echo "Uploaded new meeting: $MEETING_ID"

TRANSCRIBE_STARTED=$SECONDS
request 202 transcribe.json "/api/domain/meetings/$MEETING_ID/transcribe" -X POST
while :; do
  request 200 meeting.json "/api/domain/meetings/$MEETING_ID"
  STATUS=$(jq -er .meeting.status "$OUTPUT_DIR/meeting.json") || fail 'Meeting status missing.'
  case "$STATUS" in
    ready) break ;;
    failed) jq -r '.meeting.error // "Transcription failed"' "$OUTPUT_DIR/meeting.json" >&2; fail 'Transcription failed.' ;;
    uploaded|transcribing) ;;
    *) fail "Unexpected meeting status: $STATUS" ;;
  esac
  (( SECONDS - TRANSCRIBE_STARTED < TRANSCRIBE_TIMEOUT )) || fail 'Transcription timed out.'
  sleep 2
done
TRANSCRIPTION_SECONDS=$((SECONDS - TRANSCRIBE_STARTED))
jq -e '(.segments | length) > 0 and all(.segments[]; (.speaker_id | startswith("S")))' \
  "$OUTPUT_DIR/meeting.json" >/dev/null || fail 'Transcript is empty or speaker labels are missing.'
echo "Transcription ready in ${TRANSCRIPTION_SECONDS}s."

request 200 examples.json /api/domain/examples
jq -e --arg id "$MEETING_ID" --arg day "$MEETING_DATE" '
  [.examples[] | select(.request.case_ref == $id)][0].request
  | select(type == "object") | .case_ref = $id | .input.meeting_date = $day
' "$OUTPUT_DIR/examples.json" > "$OUTPUT_DIR/run-request.json" || fail 'Uploaded meeting is not selectable in examples.'
request 202 run-created.json /api/runs -X POST -H 'content-type: application/json' \
  --data-binary "@$OUTPUT_DIR/run-request.json"
RUN_ID=$(jq -er '.run.id | select(type == "string" and length > 0)' "$OUTPUT_DIR/run-created.json") || fail 'Run id missing.'
RUN_STARTED=$SECONDS
while :; do
  request 200 run.json "/api/runs/$RUN_ID"
  STATUS=$(jq -er .run.status "$OUTPUT_DIR/run.json") || fail 'Run status missing.'
  case "$STATUS" in
    proposed) break ;;
    queued|analyzing) ;;
    *) jq -c '{status:.run.status,error:.run.error,outcome:.run.outcome}' "$OUTPUT_DIR/run.json" >&2; fail 'Run did not produce a proposal.' ;;
  esac
  (( SECONDS - RUN_STARTED < RUN_TIMEOUT )) || fail 'Protocol extraction timed out.'
  sleep 2
done
jq -e '.proposal.status == "validated" and .proposal.validation.ok == true' "$OUTPUT_DIR/run.json" >/dev/null || fail 'Proposal is not validated.'
request 200 events.json "/api/runs/$RUN_ID/events/list"
jq -e '{proposal_id:.proposal.id,version:.proposal.version}' "$OUTPUT_DIR/run.json" > "$OUTPUT_DIR/apply-request.json"
request 200 applied.json "/api/runs/$RUN_ID/apply" -X POST -H 'content-type: application/json' \
  --data-binary "@$OUTPUT_DIR/apply-request.json"
jq -e '.run.status == "verified" and .application.status == "verified" and .application.verification.ok == true' \
  "$OUTPUT_DIR/applied.json" >/dev/null || fail 'Protocol confirmation was not verified.'
request 200 meeting-confirmed.json "/api/domain/meetings/$MEETING_ID"
jq -e '.protocol != null' "$OUTPUT_DIR/meeting-confirmed.json" >/dev/null || fail 'Confirmed protocol missing.'

request 200 protocol.pdf "/api/domain/meetings/$MEETING_ID/protocol.pdf"
request 200 protocol.docx "/api/domain/meetings/$MEETING_ID/protocol.docx"
PDF_MAGIC=$(od -An -tx1 -N4 "$OUTPUT_DIR/protocol.pdf" | tr -d ' \n')
DOCX_MAGIC=$(od -An -tx1 -N4 "$OUTPUT_DIR/protocol.docx" | tr -d ' \n')
[[ "$PDF_MAGIC" == 25504446 ]] || fail 'Export does not have PDF magic.'
[[ "$DOCX_MAGIC" == 504b0304 ]] || fail 'Export does not have DOCX/ZIP magic.'
request 200 health-after.json /api/health
jq -e '.status == "ok" and .provenance.enabled == true and .provenance.blocked_external_connections == 0' \
  "$OUTPUT_DIR/health-after.json" >/dev/null || fail 'Final health/provenance check failed.'
ACTIONS=$(jq '.action_items | length' "$OUTPUT_DIR/meeting-confirmed.json")
jq -n --arg api "$API" --arg model "$MODEL" --arg meeting "$MEETING_ID" --arg run "$RUN_ID" \
  --argjson transcription_seconds "$TRANSCRIPTION_SECONDS" --argjson actions "$ACTIONS" \
  '{status:"verified",api:$api,model:$model,meeting_id:$meeting,run_id:$run,transcription_seconds:$transcription_seconds,action_items:$actions,pdf_magic_valid:true,docx_magic_valid:true}' \
  > "$OUTPUT_DIR/result.json"
echo "Verified $ACTIONS action items; PDF and DOCX magic valid; external attempts: 0."
echo "Transcription: ${TRANSCRIPTION_SECONDS}s. Proof files: $OUTPUT_DIR"
