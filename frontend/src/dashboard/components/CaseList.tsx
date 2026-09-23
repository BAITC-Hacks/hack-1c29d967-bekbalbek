import { useMemo, useState } from "react";
import type { ExampleCase, Run } from "../../api/types";
import { phaseChip, phaseFromStatus } from "../model/phase";
import { latestRunForExample, orphanRuns, relativeTime } from "../model/runs";

interface Props {
  examples: ExampleCase[];
  runs: Run[];
  activeExampleId: string | null;
  activeRunId: string | null;
  onPickExample: (example: ExampleCase) => void;
  onPickRun: (runId: string) => void;
}

function statusLine(run: Run | null): { cls: string; text: string } {
  if (!run) return { cls: "", text: "Not run yet" };
  const phase = phaseFromStatus(run.status);
  return { cls: `dot-${phase}`, text: `${phaseChip[phase].text} · ${relativeTime(run.created_at)}` };
}

export function CaseList({ examples, runs, activeExampleId, activeRunId, onPickExample, onPickRun }: Props) {
  const [query, setQuery] = useState("");
  const q = query.trim().toLowerCase();

  const cases = useMemo(
    () => examples
      .filter((e) => `${e.title} ${e.request.goal} ${e.request.case_ref}`.toLowerCase().includes(q))
      .map((example) => ({ example, latest: latestRunForExample(runs, example, examples) })),
    [examples, runs, q],
  );
  const others = useMemo(() => orphanRuns(runs, examples).filter((r) => `${r.goal} ${r.case_ref}`.toLowerCase().includes(q)), [examples, runs, q]);

  return (
    <aside className="left" aria-label="Cases">
      <input className="search" placeholder="Search cases" value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Search cases" />
      <div className="group">
        <div className="group-h">Cases <span>{cases.length}</span></div>
        {cases.map(({ example, latest }) => {
          const status = statusLine(latest);
          return (
            <button key={example.id} className={`row ${example.id === activeExampleId ? "on" : ""}`} onClick={() => onPickExample(example)} title={example.request.case_ref}>
              <span className={`dot ${status.cls}`} />
              <span className="row-t">{example.title}</span>
              <span className="row-m row-goal">{example.request.goal}</span>
              <span className="row-m">{status.text}</span>
            </button>
          );
        })}
        {examples.length === 0 && <p className="muted small">No examples published by the backend.</p>}
      </div>
      {others.length > 0 && (
        <div className="group">
          <div className="group-h">Other runs <span>{others.length}</span></div>
          {others.map((run) => {
            const status = statusLine(run);
            return (
              <button key={run.id} className={`row ${run.id === activeRunId && !activeExampleId ? "on" : ""}`} onClick={() => onPickRun(run.id)}>
                <span className={`dot ${status.cls}`} />
                <span className="row-t">{run.goal}</span>
                <span className="row-m">{run.case_ref} · {status.text}</span>
              </button>
            );
          })}
        </div>
      )}
    </aside>
  );
}
