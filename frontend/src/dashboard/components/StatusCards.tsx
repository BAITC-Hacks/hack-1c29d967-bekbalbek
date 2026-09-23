import type { ApiError } from "../../api/client";
import type { BlockingConstraint, RunError, VerificationReport } from "../../api/types";
import type { BeforeAfterRow } from "../model/changes";

export function VerifiedBanner({ count, summary, collapsed }: { count: number; summary: string; collapsed: boolean }) {
  return collapsed
    ? <div className="banner-chip"><span className="chip chip-verified">✓ Verified</span><span className="muted">{summary}</span></div>
    : <div className="banner banner-ok" role="status">✓ Applied and verified. {count} change{count === 1 ? "" : "s"} confirmed by the database. <span className="banner-sub">{summary}</span></div>;
}

export function InfeasibleCard({ message, constraints }: { message: string; constraints: BlockingConstraint[] }) {
  return (
    <div className="card card-bad" role="region" aria-label="Infeasible">
      <div className="card-h"><span className="chip chip-failed">⊘ Infeasible</span><strong>The constraints cannot be satisfied</strong></div>
      <p className="card-p">{message}</p>
      <ul className="constraints">
        {constraints.map((c, i) => (
          <li key={`${c.rule_id}-${i}`}>
            <span className="chip chip-failed mono">{c.rule_id}</span>
            <span>{c.detail}</span>
            {c.refs.length > 0 && <span className="mono muted">{c.refs.join(", ")}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function FailedCard({ error, label, onRetry, details }: { error: RunError | { code: string; message: string; stage?: string }; label: string; onRetry?: () => void; details?: string }) {
  return (
    <div className="card card-bad" role="alert">
      <div className="card-h"><span className="chip chip-failed">✕ {label}</span><strong>{error.message}</strong></div>
      <p className="card-p mono">{error.code}{"stage" in error && error.stage ? ` · stage ${error.stage}` : ""}</p>
      <div className="card-actions">
        {onRetry && <button className="btn btn-primary" onClick={onRetry}>Retry</button>}
        {details && <details className="details"><summary className="btn btn-ghost">Show details</summary><pre className="act-pre mono">{details}</pre></details>}
      </div>
    </div>
  );
}

export function RejectionCard({ error, onRerun }: { error: ApiError; onRerun: () => void }) {
  const details = (error.details ?? {}) as { fingerprint_changed?: boolean; validation?: { errors?: { rule_id: string; message: string }[] } };
  const titles: Record<string, string> = {
    stale_proposal: "This proposal is out of date",
    duplicate_apply: "This proposal was already applied",
    invalid_state: "This run can no longer be applied",
    execution_failed: "The database rejected the change",
  };
  return (
    <div className="card card-attention" role="alert">
      <div className="card-h"><span className="chip chip-attention">! {error.code}</span><strong>{titles[error.code] ?? "Apply was rejected"}</strong></div>
      <p className="card-p">{error.message}</p>
      {details.fingerprint_changed && <p className="card-p muted">The fingerprint of the records this plan depends on no longer matches. Nothing was written.</p>}
      {details.validation?.errors && details.validation.errors.length > 0 && (
        <ul className="constraints">{details.validation.errors.map((e, i) => <li key={i}><span className="chip chip-failed mono">{e.rule_id}</span><span>{e.message}</span></li>)}</ul>
      )}
      <div className="card-actions"><button className="btn btn-primary" onClick={onRerun}>Re-run analysis</button></div>
    </div>
  );
}

export function ValidationFailedCard({ errors, onRerun }: { errors: { rule_id: string; message: string; action_id: string | null }[]; onRerun: () => void }) {
  return (
    <div className="card card-bad" role="region" aria-label="Validation failed">
      <div className="card-h"><span className="chip chip-failed">✕ Validation failed</span><strong>The proposal broke {errors.length} rule{errors.length === 1 ? "" : "s"} and the revision budget is used up</strong></div>
      <ul className="constraints">{errors.map((e, i) => <li key={i}><span className="chip chip-failed mono">{e.rule_id}</span><span>{e.message}{e.action_id ? ` (action ${e.action_id})` : ""}</span></li>)}</ul>
      <div className="card-actions"><button className="btn btn-primary" onClick={onRerun}>Re-run analysis</button></div>
    </div>
  );
}

export function BeforeAfter({ rows, verification, label }: { rows: BeforeAfterRow[]; verification: VerificationReport | null; label: string }) {
  return (
    <section className="ba" aria-label="Before and after">
      <h3>Before → after</h3>
      {rows.length === 0 ? <p className="muted">No load changes recorded.</p> : (
        <table className="tbl tbl-compact">
          <thead><tr><th>{label}</th><th>Before</th><th>After</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.label}><td>{r.label}</td><td><s className="ba-before">{r.before}</s></td><td><b className="ba-after">{r.after}</b></td></tr>)}</tbody>
        </table>
      )}
      {verification && (
        <ul className="checks">
          {verification.checks.map((c) => <li key={c.id} className={c.ok ? "ok" : "bad"}><span>{c.ok ? "✓" : "✕"}</span><span>{c.label}</span><span className="muted">{c.detail}</span></li>)}
        </ul>
      )}
    </section>
  );
}
