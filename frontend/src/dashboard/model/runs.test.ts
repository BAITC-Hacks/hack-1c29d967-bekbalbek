import type { ExampleCase } from "../../api/types";
import { makeRun } from "../../test/fixtures";
import { exampleForRun, latestRunForExample, orphanRuns, relativeTime, runsForExample } from "./runs";

const example = (id: string, case_ref: string, goal: string, input: Record<string, unknown>): ExampleCase =>
  ({ id, title: id, description: "", expected_outcome: "proposal_ready", request: { case_ref, goal, input } });

describe("runs model", () => {
  const plain = example("plain", "c1", "go", { planning_start: "2026-09-24" });
  const reduced = example("reduced", "c1", "go", { planning_start: "2026-09-24", capacity_overrides: { w: 4 } });
  const examples = [plain, reduced];
  const runs = [
    makeRun({ id: "a", case_ref: "c1", goal: "go", input: { planning_start: "2026-09-24" }, created_at: "2026-09-24T10:00:00Z" }),
    makeRun({ id: "b", case_ref: "c1", goal: "go", input: { planning_start: "2026-09-24", job_overrides: { j: { required_skill: "x" } } }, created_at: "2026-09-24T11:00:00Z" }),
    makeRun({ id: "c", case_ref: "c1", goal: "go", input: { planning_start: "2026-09-24", capacity_overrides: { w: 4 } }, created_at: "2026-09-24T12:00:00Z" }),
    makeRun({ id: "d", case_ref: "c1", goal: "edited goal", input: { planning_start: "2026-09-24" }, created_at: "2026-09-24T13:00:00Z" }),
    makeRun({ id: "e", case_ref: "c9", goal: "go", input: {}, created_at: "2026-09-24T14:00:00Z" }),
  ];

  it("should attach a run to the most specific example whose request it extends", () => {
    expect(exampleForRun(runs[0], examples)?.id).toBe("plain");
    expect(exampleForRun(runs[1], examples)?.id).toBe("plain");
    expect(exampleForRun(runs[2], examples)?.id).toBe("reduced");
    expect(exampleForRun(runs[3], examples)).toBeNull();
  });

  it("should list an example's runs newest first and pick the latest", () => {
    expect(runsForExample(runs, plain, examples).map((r) => r.id)).toEqual(["b", "a"]);
    expect(latestRunForExample(runs, reduced, examples)?.id).toBe("c");
    expect(latestRunForExample(runs, example("none", "c2", "go", {}), examples)).toBeNull();
  });

  it("should list runs that belong to no example as orphans", () => {
    expect(orphanRuns(runs, examples).map((r) => r.id)).toEqual(["e", "d"]);
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
