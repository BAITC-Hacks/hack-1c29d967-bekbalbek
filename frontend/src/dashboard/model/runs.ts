import type { ExampleCase, Run } from "../../api/types";

const byNewest = (a: Run, b: Run) => b.created_at.localeCompare(a.created_at);

// Meeting identity stays the same when the analysis goal, date or other inputs change.
export function exampleForRun(run: Run, examples: ExampleCase[]): ExampleCase | null {
  return examples.find((example) => example.request.case_ref === run.case_ref) ?? null;
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
