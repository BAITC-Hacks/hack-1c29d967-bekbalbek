import { applyEvents, failedEvents, happyEvents } from "../../test/fixtures";
import { initialTimeline, reduceTimeline } from "./timeline";

const run = (events: typeof happyEvents) => events.reduce(reduceTimeline, initialTimeline);

describe("timeline reducer", () => {
  it("should open a running step on tool_started and close it on tool_finished", () => {
    const state = run(happyEvents.slice(0, 3));
    const step = state.steps.find((s) => s.id === "c1");
    expect(step?.state).toBe("done");
    expect(step?.label).toBe("Чтение совещания");
    expect(step?.detail).toContain("12 ms");
    expect(step?.result).toEqual({ segments: [] });
  });

  it("should keep a retried tool running with the retry reason and finish on the second attempt", () => {
    const afterFailure = run(happyEvents.slice(0, 5));
    expect(afterFailure.steps.find((s) => s.id === "c2")?.state).toBe("running");
    expect(afterFailure.steps.find((s) => s.id === "c2")?.detail).toMatch(/повтор/i);
    const afterRetry = run(happyEvents.slice(0, 6));
    const step = afterRetry.steps.find((s) => s.id === "c2");
    expect(step?.state).toBe("done");
    expect(step?.attempt).toBe(2);
    expect(step?.truncated).toBe(true);
  });

  it("should mark a tool failed when no retry follows", () => {
    const state = run(failedEvents);
    expect(state.steps.find((s) => s.id === "c1")?.state).toBe("failed");
    expect(state.steps.find((s) => s.id === "c1")?.error?.code).toBe("not_found");
    expect(state.steps.at(-1)?.tone).toBe("bad");
    expect(state.status).toBe("failed");
  });

  it("should add milestones for agent output, proposal, apply and verification", () => {
    const state = run([...happyEvents, ...applyEvents]);
    const labels = state.steps.filter((s) => s.kind === "milestone").map((s) => s.label);
    expect(labels).toEqual(expect.arrayContaining([expect.stringMatching(/Протокол готов/), expect.stringMatching(/Сохраняем/), expect.stringMatching(/Подтверждено/)]));
    expect(state.status).toBe("verified");
    expect(state.stats?.tool_calls).toBe(2);
  });

  it("should ignore duplicate or out-of-order events by id", () => {
    const once = run(happyEvents);
    const twice = happyEvents.concat(happyEvents).reduce(reduceTimeline, initialTimeline);
    expect(twice.steps).toEqual(once.steps);
    expect(twice.lastEventId).toBe(9);
  });

  it("should track the latest run status from any event and ignore unknown types", () => {
    const state = reduceTimeline(initialTimeline, { id: 1, run_id: "r", type: "something_new", ts: "t", run_status: "analyzing", payload: {} });
    expect(state.status).toBe("analyzing");
    expect(state.steps).toEqual([]);
    expect(state.lastEventId).toBe(1);
  });

  it("should record validation failures and revisions as milestones", () => {
    const events = [
      { id: 1, run_id: "r", type: "validation_failed", ts: "t", run_status: "analyzing" as const, payload: { proposal_id: "p", version: 1, errors: [{ rule_id: "skill_match", message: "Boris lacks electrical" }], will_revise: true } },
      { id: 2, run_id: "r", type: "revision_started", ts: "t", run_status: "analyzing" as const, payload: { attempt: 2, reason: "1 failing check(s)" } },
    ];
    const state = events.reduce(reduceTimeline, initialTimeline);
    expect(state.steps[0].tone).toBe("bad");
    expect(state.steps[0].detail).toContain("skill_match");
    expect(state.steps[1].label).toMatch(/Исправление/);
  });
});
