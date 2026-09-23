import type { Run } from "../../api/types";
import { JOURNEY, journeyProgress, phaseChip, phaseFromStatus, type Phase } from "../model/phase";
import { relativeTime } from "../model/runs";

const MAX_HISTORY = 6;

interface Props {
  title: string;
  summary: string;
  caseRef: string;
  phase: Phase;
  outcome: string | null;
  model: string | null;
  history: Run[];
  activeRunId: string | null;
  onPickRun: (runId: string) => void;
}

export function Stepper({ phase }: { phase: Phase }) {
  const { done, current } = journeyProgress(phase);
  const complete = phase === "verified";
  return (
    <ol className="stepper" aria-label="Case progress">
      {JOURNEY.map((label, i) => (
        <li key={label} className={i < done ? "done" : i === current && !complete ? "current" : ""}>
          <span className="st-dot" /><span className="st-l">{label}</span>
        </li>
      ))}
    </ol>
  );
}

export function CaseHeader({ title, summary, caseRef, phase, outcome, model, history, activeRunId, onPickRun }: Props) {
  const chip = phaseChip[phase];
  return (
    <div className="case-h">
      <h1>{title}</h1>
      <div className="case-meta">
        <span className="chip mono">{caseRef}</span>
        {outcome && <span className="chip">{outcome.replace("_", " ")}</span>}
        {model && <span className="chip">{model}</span>}
        <span className={`chip ${chip.cls}`} aria-live="polite">{chip.busy ? <span className="spinner" /> : chip.icon} {chip.text}</span>
        <Stepper phase={phase} />
      </div>
      {summary && <p className="case-sum">{summary}</p>}
      {history.length > 0 && (
        <div className="history" aria-label="Runs of this case">
          <span className="muted small">Runs</span>
          {history.slice(0, MAX_HISTORY).map((run) => {
            const p = phaseFromStatus(run.status);
            return (
              <button key={run.id} className={`chip ${phaseChip[p].cls} ${run.id === activeRunId ? "on" : ""}`} onClick={() => onPickRun(run.id)} aria-pressed={run.id === activeRunId}>
                {phaseChip[p].icon} {phaseChip[p].text} · {relativeTime(run.created_at)}
              </button>
            );
          })}
          {history.length > MAX_HISTORY && <span className="muted small">+{history.length - MAX_HISTORY} older</span>}
        </div>
      )}
    </div>
  );
}
