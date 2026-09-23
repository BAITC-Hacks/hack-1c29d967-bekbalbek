import type { ExampleCase, Run } from "../../api/types";

const byNewest = (a: Run, b: Run) => b.created_at.localeCompare(a.created_at);

function extendsInput(actual: Record<string, unknown>, base: Record<string, unknown>): boolean {
  return Object.entries(base).every(([key, value]) => JSON.stringify(actual[key]) === JSON.stringify(value));
}

// A run belongs to the most specific example whose request it extends (same case, same goal, input superset).
export function exampleForRun(run: Run, examples: ExampleCase[]): ExampleCase | null {
  return examples
    .filter((e) => e.request.case_ref === run.case_ref && e.request.goal === run.goal && extendsInput(run.input, e.request.input))
    .sort((a, b) => Object.keys(b.request.input).length - Object.keys(a.request.input).length)[0] ?? null;
}

export function runsForExample(runs: Run[], example: ExampleCase, examples: ExampleCase[]): Run[] {
  return runs.filter((r) => exampleForRun(r, examples)?.id === example.id).sort(byNewest);
}

export function latestRunForExample(runs: Run[], example: ExampleCase, examples: ExampleCase[]): Run | null {
  return runsForExample(runs, example, examples)[0] ?? null;
}

export function orphanRuns(runs: Run[], examples: ExampleCase[]): Run[] {
  return runs.filter((r) => exampleForRun(r, examples) === null).sort(byNewest);
}

export function relativeTime(iso: string, now: number = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - new Date(iso).getTime()) / 1000));
  if (seconds < 60) return `${seconds} с назад`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} мин назад`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} ч назад`;
  return `${Math.round(seconds / 86400)} д назад`;
}
