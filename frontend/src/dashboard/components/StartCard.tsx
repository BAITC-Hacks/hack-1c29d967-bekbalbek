import { useState } from "react";
import type { CreateRunRequest } from "../../api/types";

export interface RunSeed { case_ref: string; goal: string; input: Record<string, unknown> }

interface Props {
  seed: RunSeed;
  description: string;
  hasRun: boolean;
  busy: boolean;
  blockedReason?: string | null;
  onStart: (request: CreateRunRequest) => void;
}

const INPUT_HINT = "Edit any condition here (dates, ids, overrides) to get a different plan.";

export function StartCard({ seed, description, hasRun, busy, blockedReason, onStart }: Props) {
  const [openOverride, setOpenOverride] = useState<boolean | null>(null);
  const [goal, setGoal] = useState(seed.goal);
  const [inputText, setInputText] = useState(JSON.stringify(seed.input, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);
  const open = openOverride ?? !hasRun;
  const setOpen = (value: boolean) => setOpenOverride(value);

  const submit = () => {
    if (blockedReason) return;
    try {
      const input = JSON.parse(inputText) as Record<string, unknown>;
      if (typeof input !== "object" || input === null || Array.isArray(input)) throw new Error("not an object");
      setParseError(null);
      setOpenOverride(null);
      onStart({ case_ref: seed.case_ref, goal: goal.trim(), input });
    } catch {
      setParseError("Input must be a JSON object");
      setOpen(true);
    }
  };
  const label = busy ? <><span className="spinner" /> Starting…</> : hasRun ? "Run analysis again" : "Run analysis";

  if (!open) {
    return (
      <div className="card request compact" role="region" aria-label="Request">
        <span className="chip">○ Request</span>
        <span className="request-goal">{goal}</span>
        <div className="card-actions">
          <button className="btn btn-ghost" onClick={() => setOpen(true)}>Edit input</button>
          <button className="btn btn-primary" onClick={submit} disabled={busy || Boolean(blockedReason) || goal.trim().length === 0}>{label}</button>
        </div>
      </div>
    );
  }

  return (
    <div className="card request" role="region" aria-label="Request">
      <div className="card-h"><span className="chip">○ {hasRun ? "Run again" : "New run"}</span>{description && <strong>{description}</strong>}</div>
      <label className="field">
        <span className="field-l">Goal</span>
        <textarea value={goal} onChange={(e) => setGoal(e.target.value)} rows={2} />
      </label>
      <label className="field">
        <span className="field-l">Input <span className="mono muted">{seed.case_ref}</span></span>
        <textarea className="mono" value={inputText} onChange={(e) => setInputText(e.target.value)} rows={Math.min(12, inputText.split("\n").length + 1)} spellCheck={false} />
        <span className="field-h">{INPUT_HINT}</span>
      </label>
      {blockedReason && <p className="muted">{blockedReason}</p>}
      {parseError && <p className="err">{parseError}</p>}
      <div className="card-actions">
        {hasRun && <button className="btn btn-ghost" onClick={() => setOpen(false)}>Cancel</button>}
        <button className="btn btn-primary btn-lg" onClick={submit} disabled={busy || Boolean(blockedReason) || goal.trim().length === 0}>{label}</button>
      </div>
    </div>
  );
}
