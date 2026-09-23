# Protokol frontend integration

The backend meeting workflow is available now. Frontend work belongs to the frontend teammate. API paths below include `/api`; `api.request()` already adds that prefix.

## Required flow and two UI blockers

1. Upload a recording or select an existing meeting.
2. Start transcription; poll the meeting every 2 seconds until `ready` or `failed`.
3. Show speaker-attributed transcript; allow speaker renaming.
4. Start the protocol run only when transcription is `ready`.
5. Review its proposal and evidence, confirm it, then show PDF/DOCX downloads.

`Dashboard.tsx` currently passes `DemoPanel` only when `detail && phase === "proposed"`. `ApplyPanel.tsx` also renders its `extra` only inside the proposed-state branch. Place `MeetingPanel` somewhere accessible **before a run exists**, including the empty dashboard, and keep downloads accessible after confirmation. Changing only one of these conditions does not fix the full flow.

Upload navigation needs a list refresh: `GET /api/domain/examples` dynamically includes every stored meeting, but Dashboard fetches examples only at mount. Its current `onChanged` reloads only the selected case. Refresh examples after upload before navigating to `#/app/example/<meeting.id>`; otherwise `routeExample` and `caseRef` remain null for the new id. Expose a refresh callback or another explicit refresh mechanism. After transcription, rename and apply, refresh the selected case as well.

## Meeting endpoints

| Request | Body | Success response |
|---|---|---|
| `POST /api/domain/meetings` | Multipart: `file`, `title`, `meeting_date` (`YYYY-MM-DD`) | 202 `{ "meeting": Meeting }` |
| `GET /api/domain/examples` | — | `{ "examples": Example[] }` |
| `GET /api/domain/meetings/{id}` | — | `{ meeting, speakers, segments, protocol, action_items }` |
| `GET /api/domain/cases/{id}` | — | The same data plus `case_ref`, `title`, `description`, `status`, `meeting_date`, `duration_s`, `error` at the top level |
| `POST /api/domain/meetings/{id}/transcribe` | None | 202 `{ "meeting_id": "m-…", "status": "transcribing" }` |
| `PATCH /api/domain/meetings/{id}/speakers/{speaker_id}` | JSON `{ "display_name": "Асхат" }` | `{ "speaker": Speaker }` |
| `GET /api/domain/meetings/{id}/protocol.pdf` | — | PDF attachment |
| `GET /api/domain/meetings/{id}/protocol.docx` | — | DOCX attachment |

Uploads accept `.mp3`, `.wav`, `.m4a`, `.mp4`, `.ogg`, `.webm`, `.flac`, up to 300 MiB. Titles are 1–200 characters; empty files fail. Use `FormData` and let the browser set the multipart boundary. The current generic `api.request()` always sets JSON content-type, so use an upload-aware fetch path with the same API base or update the client to support FormData. `Api` currently exposes no `base` property.

Transcription returns 409 if already in progress or if a confirmed protocol exists. On `failed`, display `meeting.error`. Renames accept 1–200 characters and reject whitespace-only names. Renaming after a proposal changes its evidence fingerprint: start a new run before confirming.

```ts
type Meeting = {
  id: string; title: string; meeting_date: string;
  status: "uploaded" | "transcribing" | "ready" | "failed";
  error: string | null; duration_s: number | null;
  language_hint: string; created_at: string; audio_path: string;
};
type Speaker = { meeting_id: string; speaker_id: string; display_name: string };
type Segment = {
  id: number; meeting_id: string; idx: number;
  start_s: number; end_s: number; speaker_id: string;
  language: string; text: string;
  words: { start: number; end: number; text: string; prob: number }[];
};
```

Render timecodes from `start_s`; REST segments have no `t` field. Language badges come from `segment.language` (RU/KK/EN). REST does not expose language-window probabilities. Do not render the server's `audio_path` as a playable URL: there is no audio-serving endpoint.

Each example has `{ id, title, description, expected_outcome: "proposal_ready", request: { case_ref, goal, input: { meeting_date } } }`. The two seeded ids are `m-sample-1` and `m-sample-2`. `POST /api/domain/reset` resets those samples and their runs to uploaded state, preserving other uploads; response is `{ status: "ok", seeded: { meetings: 2 } }`.

## Protocol runs and confirmation

The existing generic run client and event stream remain usable:

```json
POST /api/runs
{
  "case_ref": "m-sample-1",
  "goal": "Составь протокол совещания",
  "input": { "meeting_date": "2026-09-23", "language": "auto", "notes": null }
}
```

Response: 202 `{ run }`. Poll `GET /api/runs/{run.id}` or keep the current SSE integration at `/api/runs/{run.id}/events`. A successful analysis reaches `run.status = "proposed"`; the proposal is under `detail.proposal.content`, with checks under `detail.proposal.validation`.

Proposal content contains `summary`, `decisions: string[]`, `actions`, `evidence`, `assumptions`, and `expected_effects`. Each action has:

```ts
type ProtocolAction = {
  action_id: string; type: "action_item"; text: string;
  owner_name: string; owner_speaker_id: string | null;
  deadline_text: string; deadline_date: string | null;
  urgency: "высокий" | "средний" | "низкий";
  source_segment_ids: number[];
};
```

**`owner_name` is the assignee. `owner_speaker_id` identifies the person who gave the instruction.** Never replace the assignee with the display name resolved from `owner_speaker_id`. Show a separate “Поручил” label if useful. Unknown assignee is `не назначен`; null deadline displays `срок не указан`, retaining the original `deadline_text` when present.

For each action, use `source_segment_ids` to link transcript rows. Evidence references have `{ kind: "record", ref: "segment:12", note }`; find segment id 12 and show its time, speaker name and text. Use `String(segment.id)` consistently for table row ids/highlighting. Required-tool and evidence-read failures must remain visible; the backend rejects proposals whose citations were not read by that run.

Confirm with `POST /api/runs/{run.id}/apply`, JSON `{ "proposal_id": detail.proposal.id, "version": detail.proposal.version }`. Success returns `{ run, application }` with verified status. Then refresh the meeting. A protocol with zero actions is valid: it still has a summary/decisions and can be confirmed/exported.

The confirmed `protocol` has `id`, `meeting_id`, nullable `run_id`, `summary`, `decisions`, `confirmed_at`. Persisted `action_items` retain action content, but use `id`, `action_key`, `protocol_id`, `meeting_id`, `status` instead of proposal `action_id`/`type`. Show export links when `protocol !== null`; before confirmation they return 404. Snapshots are `{ action_items: number, protocol_exists: boolean }`.

There are currently **no endpoints to edit action items, proposal deadlines, or action statuses**. Do not present editable controls that imply persistence. A read-only board can display current `status` and derive overdue when `deadline_date` precedes today's local date and `status !== "done"`.

## Local processing and finish checks

`GET /api/health` includes `provenance: { enabled: boolean, blocked_external_connections: number }`, `models_present`, `stt_device`, `model`, `llm_endpoint`, and `domain: { key: "protokol", title }`. Display the actual guard state and blocked-attempt count; the counter is not a count of permitted network connections. Avoid claiming protection is enabled when `enabled` is false. Hide the API-key badge. A `scripted:auto` model is demo mode and should be identified as such.

Replace the domain adapter/imports, meeting types, Russian product copy and fixtures. Preserve generic lifecycle/error/SSE coverage. Run `pnpm test && pnpm lint && pnpm build`, then verify upload → transcription → proposal → confirmation → PDF/DOCX in the UI. Critical regressions: panel accessible before any run; upload becomes selectable without page reload; assignee differs from giver; downloads remain visible after verification.
