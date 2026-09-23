import { applyGate, journeyProgress, phaseChip, phaseFromStatus, isTerminalPhase } from "./phase";

describe("phase model", () => {
  it("should map a missing run to idle and statuses to phases", () => {
    expect(phaseFromStatus(null)).toBe("idle");
    expect(phaseFromStatus("queued")).toBe("analyzing");
    expect(phaseFromStatus("verified")).toBe("verified");
    expect(phaseFromStatus("validation_failed")).toBe("validation_failed");
  });

  it("should compute journey progress per phase", () => {
    expect(journeyProgress("idle")).toEqual({ done: 0, current: 0 });
    expect(journeyProgress("analyzing")).toEqual({ done: 1, current: 1 });
    expect(journeyProgress("proposed")).toEqual({ done: 3, current: 3 });
    expect(journeyProgress("applying")).toEqual({ done: 3, current: 3 });
    expect(journeyProgress("applied")).toEqual({ done: 4, current: 4 });
    expect(journeyProgress("verified")).toEqual({ done: 5, current: 5 });
    expect(journeyProgress("failed")).toEqual({ done: 1, current: 1 });
  });

  it("should give every phase a chip with icon and text", () => {
    for (const phase of ["idle", "analyzing", "needs_input", "infeasible", "proposed", "validation_failed", "applying", "applied", "verified", "failed", "interrupted"] as const) {
      expect(phaseChip[phase].text.length).toBeGreaterThan(0);
      expect(typeof phaseChip[phase].icon).toBe("string");
    }
  });

  it("should mark terminal phases", () => {
    expect(isTerminalPhase("verified")).toBe(true);
    expect(isTerminalPhase("needs_input")).toBe(true);
    expect(isTerminalPhase("proposed")).toBe(false);
    expect(isTerminalPhase("analyzing")).toBe(false);
  });

  it("should only allow apply on a validated proposal with warnings acknowledged", () => {
    expect(applyGate({ phase: "proposed", validationOk: true, warnings: 0, acknowledged: false })).toEqual({ enabled: true, reason: null });
    expect(applyGate({ phase: "proposed", validationOk: true, warnings: 1, acknowledged: false }).enabled).toBe(false);
    expect(applyGate({ phase: "proposed", validationOk: true, warnings: 1, acknowledged: true }).enabled).toBe(true);
    expect(applyGate({ phase: "proposed", validationOk: false, warnings: 0, acknowledged: true }).reason).toMatch(/ошибки/);
    expect(applyGate({ phase: "analyzing", validationOk: true, warnings: 0, acknowledged: true }).enabled).toBe(false);
  });
});
