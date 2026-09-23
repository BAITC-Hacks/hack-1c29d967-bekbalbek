import type { RunStatus } from "../../api/types";

export type Phase =
  | "idle" | "analyzing" | "needs_input" | "infeasible" | "proposed" | "validation_failed"
  | "applying" | "applied" | "verified" | "failed" | "interrupted";

export const JOURNEY = ["Detected", "Analyzed", "Proposed", "Applied", "Verified"] as const;

const TERMINAL: ReadonlySet<Phase> = new Set(["verified", "failed", "interrupted", "infeasible", "needs_input", "validation_failed"]);

export function phaseFromStatus(status: RunStatus | null | undefined): Phase {
  if (!status) return "idle";
  return status === "queued" ? "analyzing" : status;
}

export function isTerminalPhase(phase: Phase): boolean {
  return TERMINAL.has(phase);
}

const PROGRESS: Record<Phase, number> = {
  idle: 0, analyzing: 1, needs_input: 1, infeasible: 1, validation_failed: 1, failed: 1, interrupted: 1,
  proposed: 3, applying: 3, applied: 4, verified: 5,
};

export function journeyProgress(phase: Phase): { done: number; current: number } {
  const done = PROGRESS[phase];
  return { done, current: done };
}

export const phaseChip: Record<Phase, { cls: string; text: string; icon: string; busy?: boolean }> = {
  idle: { cls: "", text: "New", icon: "○" },
  analyzing: { cls: "chip-applying", text: "Analyzing", icon: "", busy: true },
  needs_input: { cls: "chip-attention", text: "Needs information", icon: "?" },
  infeasible: { cls: "chip-failed", text: "Infeasible", icon: "⊘" },
  proposed: { cls: "chip-proposed", text: "Proposed", icon: "◇" },
  validation_failed: { cls: "chip-failed", text: "Validation failed", icon: "✕" },
  applying: { cls: "chip-applying", text: "Applying", icon: "", busy: true },
  applied: { cls: "chip-applied", text: "Applied", icon: "●" },
  verified: { cls: "chip-verified", text: "Verified", icon: "✓" },
  failed: { cls: "chip-failed", text: "Failed", icon: "✕" },
  interrupted: { cls: "chip-attention", text: "Interrupted", icon: "!" },
};

export interface ApplyGateInput { phase: Phase; validationOk: boolean; warnings: number; acknowledged: boolean }

export function applyGate({ phase, validationOk, warnings, acknowledged }: ApplyGateInput): { enabled: boolean; reason: string | null } {
  if (phase !== "proposed") return { enabled: false, reason: "Nothing to apply yet" };
  if (!validationOk) return { enabled: false, reason: "The proposal has failing checks" };
  if (warnings > 0 && !acknowledged) return { enabled: false, reason: "Review the warnings first" };
  return { enabled: true, reason: null };
}
