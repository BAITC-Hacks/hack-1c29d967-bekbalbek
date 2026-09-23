import { useState, type ReactNode } from "react";
import type { ProposalStatus, ValidationReport } from "../../api/types";
import { applyGate, type Phase } from "../model/phase";

interface Props {
  phase: Phase;
  validation: ValidationReport | null;
  proposalStatus: ProposalStatus | null;
  changeCount: number;
  busy: boolean;
  onApply: () => void;
  extra?: ReactNode;
}

export function ApplyPanel({ phase, validation, proposalStatus, changeCount, busy, onApply, extra }: Props) {
  const [acknowledged, setAcknowledged] = useState(false);
  const warnings = validation?.checks.filter((c) => c.status === "warn").length ?? 0;
  const passes = validation?.checks.filter((c) => c.status === "pass").length ?? 0;
  const failures = validation?.errors.length ?? 0;
  const gate = applyGate({ phase, validationOk: validation?.ok ?? false, warnings, acknowledged });

  return (
    <div className="apply">
      {phase === "idle" && <p className="muted small">Pick an example and run the analysis to get a proposal.</p>}
      {phase === "analyzing" && <button className="btn wide" disabled><span className="spinner" /> Analyzing…</button>}
      {phase === "proposed" && !validation && <button className="btn wide" disabled><span className="spinner" /> Loading proposal…</button>}
      {phase === "proposed" && validation && proposalStatus && proposalStatus !== "validated" && (
        <button className="btn wide" disabled>Proposal {proposalStatus} — run the analysis again</button>
      )}
      {phase === "proposed" && validation && (!proposalStatus || proposalStatus === "validated") && (
        <>
          <div className="apply-sum">{changeCount} change{changeCount === 1 ? "" : "s"} · {passes} checks passed{warnings > 0 && ` · ${warnings} warning${warnings === 1 ? "" : "s"}`}{failures > 0 && ` · ${failures} failing`}</div>
          {warnings > 0 && failures === 0 && (
            <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} /> I reviewed the warning{warnings === 1 ? "" : "s"}</label>
          )}
          {gate.reason && !gate.enabled && warnings === 0 && <p className="muted small">{gate.reason}</p>}
          <div className="apply-row">
            <button className="btn btn-primary wide" disabled={!gate.enabled || busy} onClick={onApply}>{busy ? <><span className="spinner" /> Applying…</> : "Apply proposal"}</button>
          </div>
          {extra}
        </>
      )}
      {phase === "applying" && <button className="btn wide" disabled><span className="spinner" /> Applying…</button>}
      {phase === "applied" && <button className="btn wide" disabled><span className="spinner" /> Applied — verifying</button>}
      {phase === "verified" && <button className="btn wide chip-verified" disabled>✓ Verified</button>}
      {["needs_input", "infeasible", "validation_failed", "failed", "interrupted"].includes(phase) && (
        <p className="muted small">Nothing to apply. Adjust the request above and run the analysis again.</p>
      )}
    </div>
  );
}
