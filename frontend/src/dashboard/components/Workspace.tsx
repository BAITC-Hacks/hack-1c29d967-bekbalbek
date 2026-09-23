import type { ApiError } from "../../api/client";
import type { CreateRunRequest, RunDetail, RunError } from "../../api/types";
import type { DomainAdapter } from "../model/adapter";
import type { BeforeAfterRow, ChangeRow, Table } from "../model/changes";
import type { Phase } from "../model/phase";
import type { Busy } from "../useRun";
import { ChangesTable } from "./ChangesTable";
import { NeedsInputForm } from "./NeedsInputForm";
import { StartCard, type RunSeed } from "./StartCard";
import { BeforeAfter, FailedCard, InfeasibleCard, RejectionCard, ValidationFailedCard, VerifiedBanner } from "./StatusCards";

export const REJECTION_CODES = new Set(["stale_proposal", "duplicate_apply", "invalid_state", "execution_failed"]);

interface Props {
  seed: RunSeed | null;
  startBlockedReason?: string | null;
  description: string;
  detail: RunDetail | null;
  phase: Phase;
  runError: RunError | null;
  table: Table | null;
  changes: ChangeRow[];
  beforeAfterRows: BeforeAfterRow[];
  selectedChange: string | null;
  onSelectChange: (id: string | null) => void;
  busy: Busy;
  error: ApiError | null;
  onClearError: () => void;
  onStart: (request: CreateRunRequest) => void;
  onContinue: (input: Record<string, unknown>) => void;
  onRerun: () => void;
  domain: DomainAdapter;
}

function TableSkeleton() {
  return (
    <div className="tbl-skeleton" aria-hidden data-testid="table-skeleton">
      {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ animationDelay: `${i * 80}ms` }} />)}
    </div>
  );
}

export function Workspace(p: Props) {
  const { detail, phase, seed } = p;
  const rejection = p.error && REJECTION_CODES.has(p.error.code) ? p.error : null;
  const otherError = p.error && !rejection ? p.error : null;
  const lastProposal = detail?.proposals[detail.proposals.length - 1] ?? null;
  const busyPhase = phase === "analyzing" || phase === "applying" || phase === "applied";

  return (
    <main className="center">
      {otherError && (
        <div className="banner banner-bad" role="alert">
          <span>{otherError.code}: {otherError.message}</span>
          <button className="btn btn-ghost" onClick={p.onClearError}>Закрыть</button>
        </div>
      )}
      {rejection && <RejectionCard error={rejection} onRerun={p.onRerun} />}
      {seed && <StartCard key={`${seed.case_ref}|${seed.goal}|${JSON.stringify(seed.input)}`} seed={seed} blockedReason={p.startBlockedReason} description={p.description} hasRun={Boolean(detail)} busy={p.busy !== null} onStart={p.onStart} />}
      {detail && phase === "needs_input" && detail.needs_input && (
        <NeedsInputForm message={detail.needs_input.message} fields={detail.needs_input.missing_fields} input={detail.run.input} domain={p.domain} onContinue={p.onContinue} busy={p.busy !== null} />
      )}
      {detail && phase === "infeasible" && detail.infeasible && <InfeasibleCard message={detail.infeasible.message} constraints={detail.infeasible.blocking_constraints} />}
      {detail && phase === "validation_failed" && <ValidationFailedCard errors={lastProposal?.validation.errors ?? []} onRerun={p.onRerun} />}
      {detail && (phase === "failed" || phase === "interrupted") && (
        <FailedCard
          error={p.runError ?? { code: phase, message: phase === "interrupted" ? "Сервер перезапустился во время анализа." : "Анализ завершился ошибкой." }}
          label={phase === "interrupted" ? "Прервано" : "Ошибка анализа"}
          onRetry={p.onRerun}
          details={p.runError ? JSON.stringify(p.runError, null, 2) : undefined}
        />
      )}
      {detail && phase === "verified" && <VerifiedBanner count={detail.application?.actions.length || p.changes.length} summary={detail.application?.verification?.summary ?? ""} collapsed={false} />}
      <div className={`ws ${busyPhase ? "ws-analyzing" : ""}`} aria-busy={busyPhase}>
        {p.table ? <ChangesTable table={p.table} changes={p.changes} phase={phase} selected={p.selectedChange} onSelect={p.onSelectChange} /> : <TableSkeleton />}
      </div>
      {detail && phase === "verified" && <BeforeAfter rows={p.beforeAfterRows} verification={detail.application?.verification ?? null} label={p.domain.beforeAfterLabel} />}
    </main>
  );
}
