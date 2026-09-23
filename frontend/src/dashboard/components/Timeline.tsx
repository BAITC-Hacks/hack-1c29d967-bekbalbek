import { useState } from "react";
import type { Step } from "../model/timeline";
import type { Connection } from "../useRun";

const icon = (step: Step) => {
  if (step.state === "running") return <span className="spinner" />;
  if (step.state === "failed") return "✕";
  if (step.kind === "milestone") return step.tone === "bad" ? "✕" : step.tone === "warn" ? "!" : step.tone === "ok" ? "✓" : "●";
  return step.state === "done" ? "✓" : "○";
};

const pretty = (value: unknown) => (value === undefined ? "" : JSON.stringify(value, null, 2));

function Details({ step }: { step: Step }) {
  return (
    <pre className="act-pre mono">
      {step.kind === "tool" ? `${step.key}${step.attempt ? ` · attempt ${step.attempt}` : ""}${step.durationMs !== undefined ? ` · ${step.durationMs} ms` : ""}\n` : `${step.key}\n`}
      {step.args !== undefined && `arguments: ${pretty(step.args)}\n`}
      {step.result !== undefined && `result${step.truncated ? " (truncated)" : ""}: ${pretty(step.result)}\n`}
      {step.error && `error: ${step.error.code} — ${step.error.message}\n`}
      {step.kind === "milestone" && step.detail}
    </pre>
  );
}

export function Timeline({ steps, connection }: { steps: Step[]; connection: Connection }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const done = steps.filter((s) => s.kind === "tool" && s.state === "done").length;
  const tools = steps.filter((s) => s.kind === "tool").length;
  return (
    <section aria-label="Activity">
      <h4>
        Activity {tools > 0 && <span className="cnt">{done} of {tools} tool calls</span>}
        {connection === "live" && <span className="live-dot" title="Live" />}
        {connection === "reconnecting" && <span className="chip chip-attention mini" role="status">Reconnecting…</span>}
      </h4>
      {steps.length === 0 && <p className="muted">No run yet. Start the analysis to see each step here.</p>}
      <ul className="acts" aria-live="polite">
        {steps.map((step) => (
          <li key={step.id} className={`act ${step.state} tone-${step.tone}`}>
            <span className="act-i">{icon(step)}</span>
            <span className="act-l">{step.label}</span>
            <button className="act-d" onClick={() => setOpen((o) => ({ ...o, [step.id]: !o[step.id] }))} aria-expanded={Boolean(open[step.id])}>
              {open[step.id] ? "Hide" : "Details"}
            </button>
            {step.detail && !open[step.id] && <span className="act-sub">{step.detail.split("\n")[0]}</span>}
            {open[step.id] && <Details step={step} />}
          </li>
        ))}
      </ul>
    </section>
  );
}
