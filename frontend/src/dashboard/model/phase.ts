import type { RunStatus } from "../../api/types";

export type Phase =
  | "idle" | "analyzing" | "needs_input" | "infeasible" | "proposed" | "validation_failed"
  | "applying" | "applied" | "verified" | "failed" | "interrupted";

export const JOURNEY = ["Запись", "Анализ", "Проект", "Сохранён", "Подтверждён"] as const;

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
  idle: { cls: "", text: "Новый", icon: "○" },
  analyzing: { cls: "chip-applying", text: "Анализ", icon: "", busy: true },
  needs_input: { cls: "chip-attention", text: "Нужны уточнения", icon: "?" },
  infeasible: { cls: "chip-failed", text: "Нет результата", icon: "⊘" },
  proposed: { cls: "chip-proposed", text: "Проект", icon: "◇" },
  validation_failed: { cls: "chip-failed", text: "Ошибка проверки", icon: "✕" },
  applying: { cls: "chip-applying", text: "Сохраняем", icon: "", busy: true },
  applied: { cls: "chip-applied", text: "Сохранён", icon: "●" },
  verified: { cls: "chip-verified", text: "Подтверждён", icon: "✓" },
  failed: { cls: "chip-failed", text: "Ошибка", icon: "✕" },
  interrupted: { cls: "chip-attention", text: "Прервано", icon: "!" },
};

export interface ApplyGateInput { phase: Phase; validationOk: boolean; warnings: number; acknowledged: boolean }

export function applyGate({ phase, validationOk, warnings, acknowledged }: ApplyGateInput): { enabled: boolean; reason: string | null } {
  if (phase !== "proposed") return { enabled: false, reason: "Пока нечего подтверждать" };
  if (!validationOk) return { enabled: false, reason: "Проверка протокола обнаружила ошибки" };
  if (warnings > 0 && !acknowledged) return { enabled: false, reason: "Сначала проверьте предупреждения" };
  return { enabled: true, reason: null };
}
