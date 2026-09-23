import type { RunEvent, RunStatus, Usage, ValidationCheck, ValidationReport, VerificationReport } from "../../api/types";

export type StepState = "pending" | "running" | "done" | "failed";
export type Tone = "neutral" | "ok" | "warn" | "bad";

export interface Step {
  id: string;
  kind: "tool" | "milestone";
  key: string;
  label: string;
  detail: string;
  state: StepState;
  tone: Tone;
  ts: string;
  durationMs?: number;
  attempt?: number;
  args?: unknown;
  result?: unknown;
  truncated?: boolean;
  error?: { code: string; message: string };
}

export interface RunStats { duration_ms: number; tool_calls: number; usage: Usage | null }

export interface TimelineState {
  steps: Step[];
  lastEventId: number;
  status: RunStatus | null;
  stats: RunStats | null;
  lastError: { code: string; message: string; stage: string } | null;
  rejection: { code: string; message: string; details: unknown } | null;
}

export const initialTimeline: TimelineState = { steps: [], lastEventId: 0, status: null, stats: null, lastError: null, rejection: null };

type P = Record<string, unknown>;
const str = (v: unknown, fallback = "") => (typeof v === "string" ? v : fallback);
const num = (v: unknown, fallback = 0) => (typeof v === "number" ? v : fallback);

function milestone(event: RunEvent, label: string, detail: string, tone: Tone, state: StepState = "done", id?: string): Step {
  return { id: id ?? `m-${event.id}`, kind: "milestone", key: String(event.type), label, detail, state, tone, ts: event.ts };
}

function updateStep(steps: Step[], id: string, patch: Partial<Step>): Step[] {
  return steps.map((step) => (step.id === id ? { ...step, ...patch } : step));
}

function validationSummary(report: ValidationReport | undefined): string {
  if (!report) return "";
  const warnings = report.checks.filter((c) => c.status === "warn").length;
  const passes = report.checks.filter((c) => c.status === "pass").length;
  return `${passes} checks passed · ${warnings} warning${warnings === 1 ? "" : "s"} · ${report.errors.length} failing`;
}

function describeErrors(errors: Pick<ValidationCheck, "rule_id" | "message">[]): string {
  return errors.map((e) => `[${e.rule_id}] ${e.message}`).join("\n");
}

function stepFor(event: RunEvent): Step | null {
  const p = event.payload as P;
  switch (event.type) {
    case "run_started":
      return milestone(event, "Run started", `${str(p.model)} · up to ${num(p.max_turns)} turns`, "neutral");
    case "agent_output": {
      const outcome = str(p.outcome);
      const tone: Tone = outcome === "proposal_ready" ? "ok" : outcome === "needs_input" ? "warn" : "bad";
      return milestone(event, `Agent answered: ${outcome.replace("_", " ")}`, str(p.message), tone);
    }
    case "proposal_ready":
      return milestone(event, `Proposal ready · ${num(p.action_count)} action(s)`,
        [str(p.summary), validationSummary(p.validation as ValidationReport | undefined)].filter(Boolean).join("\n"), "ok");
    case "validation_failed": {
      const errors = (p.errors as ValidationCheck[] | undefined) ?? [];
      const suffix = p.will_revise ? "\nOne revision allowed." : "\nNo revisions left.";
      return milestone(event, `Validation failed · ${errors.length} check(s)`, describeErrors(errors) + suffix, "bad");
    }
    case "revision_started":
      return milestone(event, `Revising the proposal (attempt ${num(p.attempt)})`, str(p.reason), "warn");
    case "apply_started":
      return milestone(event, `Applying proposal v${num(p.version)}`, "Writing the changes to the database", "neutral", "running", "apply");
    case "apply_rejected":
      return milestone(event, `Apply rejected: ${str(p.code)}`, str(p.message), "bad");
    case "action_applied":
      return milestone(event, `Applied: ${str(p.summary)}`, "", "ok");
    case "verification_finished": {
      const report = p as unknown as VerificationReport;
      const checks = report.checks?.map((c) => `${c.ok ? "✓" : "✕"} ${c.label}: ${c.detail}`).join("\n") ?? "";
      return milestone(event, report.ok ? "Verified: the committed state matches the proposal" : "Verification failed",
        [report.summary, checks].filter(Boolean).join("\n"), report.ok ? "ok" : "bad");
    }
    case "run_finished": {
      const usage = p.usage as Usage | null | undefined;
      const tokens = usage ? ` · ${usage.total_tokens} tokens` : "";
      return milestone(event, `Finished: ${str(p.status).replace("_", " ")}`, `${num(p.tool_calls)} tool calls · ${num(p.duration_ms)} ms${tokens}`,
        str(p.status) === "verified" ? "ok" : "neutral");
    }
    case "run_failed":
      return milestone(event, `Run failed: ${str(p.code)}`, str(p.message), "bad");
    default:
      return null;
  }
}

function reduceTool(state: TimelineState, event: RunEvent): Step[] {
  const p = event.payload as P;
  const id = str(p.call_id, `call-${event.id}`);
  switch (event.type) {
    case "tool_started":
      return [...state.steps, { id, kind: "tool", key: str(p.tool), label: str(p.label, str(p.tool)), detail: "", state: "running", tone: "neutral", ts: event.ts, args: p.arguments }];
    case "tool_finished":
      return updateStep(state.steps, id, {
        state: "done", tone: "ok", detail: `${str(p.summary)} · ${num(p.duration_ms)} ms`, durationMs: num(p.duration_ms),
        attempt: num(p.attempt, 1), result: p.result, truncated: Boolean(p.truncated),
      });
    case "tool_failed": {
      const error = (p.error as { code: string; message: string } | undefined) ?? { code: "error", message: "" };
      if (p.will_retry) {
        return updateStep(state.steps, id, { state: "running", tone: "warn", detail: `Retrying after ${error.code}: ${error.message} (attempt ${num(p.attempt, 1)})`, error });
      }
      return updateStep(state.steps, id, { state: "failed", tone: "bad", detail: `${error.code}: ${error.message}`, error, durationMs: num(p.duration_ms), attempt: num(p.attempt, 1) });
    }
    default:
      return state.steps;
  }
}

function closeApply(steps: Step[], failed: boolean): Step[] {
  return steps.some((s) => s.id === "apply" && s.state === "running") ? updateStep(steps, "apply", { state: failed ? "failed" : "done", tone: failed ? "bad" : "ok" }) : steps;
}

export function reduceTimeline(state: TimelineState, event: RunEvent): TimelineState {
  if (event.id <= state.lastEventId) return state;
  const base: TimelineState = { ...state, lastEventId: event.id, status: event.run_status };
  const p = event.payload as P;
  if (event.type === "tool_started" || event.type === "tool_finished" || event.type === "tool_failed") {
    return { ...base, steps: reduceTool(state, event) };
  }
  const step = stepFor(event);
  let steps = step ? [...state.steps, step] : state.steps;
  let extra: Partial<TimelineState> = {};
  if (event.type === "run_finished") {
    extra = { stats: { duration_ms: num(p.duration_ms), tool_calls: num(p.tool_calls), usage: (p.usage as Usage | null) ?? null } };
    steps = closeApply(steps.filter((s) => s !== step), false).concat(step ? [step] : []);
  }
  if (event.type === "verification_finished") steps = closeApply(steps.filter((s) => s !== step), !p.ok).concat(step ? [step] : []);
  if (event.type === "run_failed") {
    extra = { lastError: { code: str(p.code), message: str(p.message), stage: str(p.stage) } };
    steps = closeApply(steps.filter((s) => s !== step), true).concat(step ? [step] : []);
  }
  if (event.type === "apply_rejected") {
    extra = { rejection: { code: str(p.code), message: str(p.message), details: p.details ?? null } };
    steps = closeApply(steps.filter((s) => s !== step), true).concat(step ? [step] : []);
  }
  return { ...base, ...extra, steps };
}
