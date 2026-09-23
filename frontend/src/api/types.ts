// Mirrors docs/API.md. Keep in sync with the backend contract.

export type Outcome = "proposal_ready" | "needs_input" | "infeasible";
export type RunStatus =
  | "queued" | "analyzing" | "needs_input" | "infeasible" | "proposed" | "validation_failed"
  | "applying" | "applied" | "verified" | "failed" | "interrupted";
export type CheckStatus = "pass" | "warn" | "fail";

export interface Usage { requests: number; input_tokens: number; output_tokens: number; total_tokens: number }
export interface RunError { code: string; message: string; stage: string }

export interface Run {
  id: string;
  case_ref: string;
  goal: string;
  input: Record<string, unknown>;
  status: RunStatus;
  outcome: Outcome | null;
  model: string;
  max_turns: number;
  error: RunError | null;
  stats: { duration_ms: number | null; tool_calls: number; usage: Usage | null };
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  updated_at: string;
}

export interface EvidenceRef { kind: "record" | "rule" | "tool_result"; ref: string; note: string | null }
export interface ProposedAction { action_id: string; type: string; [key: string]: unknown }
export interface Proposal {
  summary: string;
  actions: ProposedAction[];
  evidence: EvidenceRef[];
  assumptions: string[];
  expected_effects: string[];
}
export interface ValidationCheck {
  rule_id: string; label: string; status: CheckStatus; message: string; action_id: string | null; refs: string[]; source: string | null;
}
export interface ValidationReport { ok: boolean; checks: ValidationCheck[]; errors: ValidationCheck[] }
export type ProposalStatus = "validated" | "rejected" | "superseded" | "applied" | "stale";
export interface ProposalRecord {
  id: string; run_id: string; version: number; status: ProposalStatus; content: Proposal; validation: ValidationReport;
  basis_fingerprint: string; created_at: string;
}

export interface VerificationCheck { id: string; label: string; ok: boolean; detail: string }
export interface VerificationReport { ok: boolean; summary: string; checks: VerificationCheck[] }
export interface ApplicationAction { id: string; action_id: string; type: string; status: "applied" | "failed"; result: unknown; summary: string }
export interface Application {
  id: string; proposal_id: string; version: number; status: "applying" | "applied" | "verified" | "failed" | "rejected";
  actions: ApplicationAction[]; verification: VerificationReport | null; error: { code: string; message: string } | null;
  started_at: string; finished_at: string | null;
}

export interface MissingField { field: string; reason: string }
export interface BlockingConstraint { rule_id: string; detail: string; refs: string[] }
export interface RunMessage { seq: number; role: string; kind: string; content: unknown; created_at: string }

export interface RunDetail {
  run: Run;
  proposals: ProposalRecord[];
  proposal: ProposalRecord | null;
  needs_input: { message: string; missing_fields: MissingField[] } | null;
  infeasible: { message: string; blocking_constraints: BlockingConstraint[] } | null;
  application: Application | null;
  snapshot_before: unknown | null;
  snapshot_after: unknown | null;
  messages: RunMessage[];
}

export type EventType =
  | "run_started" | "tool_started" | "tool_finished" | "tool_failed" | "agent_output" | "proposal_ready" | "validation_failed"
  | "revision_started" | "apply_started" | "apply_rejected" | "action_applied" | "verification_finished" | "run_finished" | "run_failed";

export interface RunEvent<P = Record<string, unknown>> {
  id: number; run_id: string; type: EventType | string; ts: string; run_status: RunStatus; payload: P;
}

export interface ExampleCase {
  id: string; title: string; description: string; expected_outcome: Outcome;
  request: { case_ref: string; goal: string; input: Record<string, unknown> };
}
export interface CreateRunRequest { case_ref: string; goal: string; input: Record<string, unknown>; options?: { max_turns?: number } }

export interface Health {
  status: "ok" | "degraded"; database: "ok" | "error"; model: string; api_key_configured: boolean;
  domain: { key: string; title: string }; active_runs: number; version: string;
  provenance: { enabled: boolean; blocked_external_connections: number };
  llm_endpoint: string; stt_device: "auto" | "cuda" | "cpu"; models_present: boolean;
}

export interface ApiErrorBody { error: { code: string; message: string; details?: unknown } }

// Meeting domain: /api/domain/meetings and /api/domain/cases.
export type MeetingStatus = "uploaded" | "transcribing" | "ready" | "failed";
export interface Meeting {
  id: string; title: string; meeting_date: string; audio_path: string; status: MeetingStatus;
  error: string | null; duration_s: number | null; language_hint: string; created_at: string;
}
export interface MeetingSpeaker { meeting_id: string; speaker_id: string; display_name: string }
export interface Word { start: number; end: number; text: string; prob: number }
export interface MeetingSegment {
  id: number; meeting_id: string; idx: number; start_s: number; end_s: number;
  speaker_id: string; language: string; text: string; words: Word[];
}
export interface Protocol {
  id: string; meeting_id: string; run_id: string | null;
  summary: string; decisions: string[]; confirmed_at: string;
}
export interface ActionItem {
  id: string; protocol_id: string; meeting_id: string; action_key: string;
  text: string; owner_name: string; owner_speaker_id: string | null;
  deadline_text: string; deadline_date: string | null;
  urgency: "высокий" | "средний" | "низкий"; status: string; source_segment_ids: number[];
}
export interface MeetingDetail {
  meeting: Meeting; speakers: MeetingSpeaker[]; segments: MeetingSegment[];
  protocol: Protocol | null; action_items: ActionItem[];
}
export interface CaseView extends MeetingDetail {
  case_ref: string; title: string; description: string; status: MeetingStatus;
  meeting_date: string; duration_s: number | null; error: string | null;
}
export interface CaseInput { meeting_date: string; language?: "ru" | "kk" | "auto"; notes?: string | null }
export interface Snapshot { action_items: number; protocol_exists: boolean }
export interface ActionItemAction extends ProposedAction {
  type: "action_item"; text: string; owner_name: string; owner_speaker_id: string | null;
  deadline_text: string; deadline_date: string | null;
  urgency: "высокий" | "средний" | "низкий"; source_segment_ids: number[];
}
export interface ProtocolProposal extends Proposal { actions: ActionItemAction[]; decisions: string[] }
