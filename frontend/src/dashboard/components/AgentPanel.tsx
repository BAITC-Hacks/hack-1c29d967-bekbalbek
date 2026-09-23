import type { ReactNode } from "react";
import type { CaseView, ProposalStatus, ValidationReport } from "../../api/types";
import type { DomainAdapter } from "../model/adapter";
import type { ChangeRow } from "../model/changes";
import type { Phase } from "../model/phase";
import type { Step } from "../model/timeline";
import type { Connection } from "../useRun";
import { ApplyPanel } from "./ApplyPanel";
import { ChangeList } from "./ChangeList";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { Timeline } from "./Timeline";

interface Props {
  phase: Phase;
  steps: Step[];
  connection: Connection;
  changes: ChangeRow[];
  validation: ValidationReport | null;
  proposalStatus: ProposalStatus | null;
  proposalKey: string;
  selected: string | null;
  onSelect: (id: string | null) => void;
  caseView: CaseView | null;
  domain: DomainAdapter;
  applying: boolean;
  onApply: () => void;
  open: boolean;
  onToggle: () => void;
  demoControls?: ReactNode;
}

export function AgentPanel({ phase, steps, connection, changes, validation, proposalStatus, proposalKey, selected, onSelect, caseView, domain, applying, onApply, open, onToggle, demoControls }: Props) {
  if (!open) {
    return <aside className="right rail"><button className="btn btn-ghost" onClick={onToggle} aria-label="Открыть панель агента">‹</button></aside>;
  }
  const selectedChange = changes.find((c) => c.id === selected) ?? null;
  return (
    <aside className="right" aria-label="Агент">
      <div className="right-h"><strong>Агент</strong><button className="btn btn-ghost" onClick={onToggle} aria-label="Свернуть панель агента">›</button></div>
      <div className="right-body">
        <Timeline steps={steps} connection={connection} />
        <ChangeList changes={changes} selected={selected} onSelect={onSelect} />
        {selectedChange && <EvidenceDrawer change={selectedChange} caseView={caseView} domain={domain} onClose={() => onSelect(null)} />}
      </div>
      <ApplyPanel key={proposalKey} phase={phase} validation={validation} proposalStatus={proposalStatus} changeCount={changes.length} busy={applying} onApply={onApply} extra={demoControls} />
    </aside>
  );
}
