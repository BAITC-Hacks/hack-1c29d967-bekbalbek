import type { ExampleCase } from "../../api/types";
import { makeRun } from "../../test/fixtures";
import { exampleForRun, latestRunForExample, orphanRuns, relativeTime, runsForExample } from "./runs";

const example = (id: string, case_ref: string): ExampleCase =>
  ({ id, title: id, description: "", expected_outcome: "proposal_ready", request: { case_ref, goal: "Составь протокол", input: { meeting_date: "2026-09-23" } } });

describe("runs model", () => {
  const first = example("meeting-1", "m1");
  const second = example("meeting-2", "m2");
  const examples = [first, second];
  const runs = [
    makeRun({ id: "a", ...first.request, created_at: "2026-09-24T10:00:00Z" }),
    makeRun({ id: "b", ...first.request, input: { meeting_date: "2026-09-25" }, created_at: "2026-09-24T11:00:00Z" }),
    makeRun({ id: "c", ...second.request, created_at: "2026-09-24T12:00:00Z" }),
    makeRun({ id: "d", ...first.request, goal: "Выдели решения", input: { meeting_date: "2026-09-26", language: "kk", notes: "Проверь сроки" }, created_at: "2026-09-24T13:00:00Z" }),
    makeRun({ id: "e", ...first.request, case_ref: "m9", created_at: "2026-09-24T14:00:00Z" }),
  ];

  it("should keep runs attached to their meeting after the date, goal or other inputs change", () => {
    for (const run of [runs[0], runs[1], runs[3]]) expect(exampleForRun(run, examples)?.id).toBe(first.id);
  });

  it("should distinguish meetings even when they have identical goals and inputs", () => {
    expect(exampleForRun(runs[2], examples)?.id).toBe(second.id);
    expect(exampleForRun(runs[4], examples)).toBeNull();
  });

  it("should list a meeting's runs newest first and pick the latest", () => {
    expect(runsForExample(runs, first, examples).map((r) => r.id)).toEqual(["d", "b", "a"]);
    expect(latestRunForExample(runs, first, examples)?.id).toBe("d");
    expect(latestRunForExample(runs, second, examples)?.id).toBe("c");
    expect(latestRunForExample(runs, example("missing", "m3"), examples)).toBeNull();
  });

  it("should list only runs whose meeting is absent as orphans", () => {
    expect(orphanRuns(runs, examples).map((r) => r.id)).toEqual(["e"]);
    expect(orphanRuns(runs, []).map((r) => r.id)).toEqual(["e", "d", "c", "b", "a"]);
  });

  it("should format relative times and clamp the future to now", () => {
    const now = Date.parse("2026-09-24T12:00:00Z");
    expect(relativeTime("2026-09-24T11:59:30Z", now)).toBe("30 с назад");
    expect(relativeTime("2026-09-24T11:30:00Z", now)).toBe("30 мин назад");
    expect(relativeTime("2026-09-24T06:00:00Z", now)).toBe("6 ч назад");
    expect(relativeTime("2026-09-20T12:00:00Z", now)).toBe("4 д назад");
    expect(relativeTime("2026-09-25T12:00:00Z", now)).toBe("0 с назад");
  });
});
