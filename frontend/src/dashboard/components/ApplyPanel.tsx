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
      {phase === "idle" && <p className="muted small">Выберите совещание и сформируйте проект протокола.</p>}
      {phase === "analyzing" && <button className="btn wide" disabled><span className="spinner" /> Анализируем…</button>}
      {phase === "proposed" && !validation && <button className="btn wide" disabled><span className="spinner" /> Загружаем проект…</button>}
      {phase === "proposed" && validation && proposalStatus && proposalStatus !== "validated" && (
        <button className="btn wide" disabled>Проект недоступен для подтверждения — повторите анализ</button>
      )}
      {phase === "proposed" && validation && (!proposalStatus || proposalStatus === "validated") && (
        <>
          <div className="apply-sum">Поручений: {changeCount} · проверок пройдено: {passes}{warnings > 0 && ` · предупреждений: ${warnings}`}{failures > 0 && ` · ошибок: ${failures}`}</div>
          {warnings > 0 && failures === 0 && (
            <label className="ack"><input type="checkbox" checked={acknowledged} onChange={(e) => setAcknowledged(e.target.checked)} /> Я проверил предупреждения</label>
          )}
          {gate.reason && !gate.enabled && warnings === 0 && <p className="muted small">{gate.reason}</p>}
          <div className="apply-row">
            <button className="btn btn-primary wide" disabled={!gate.enabled || busy} onClick={onApply}>{busy ? <><span className="spinner" /> Сохраняем…</> : "Подтвердить протокол"}</button>
          </div>
          {extra}
        </>
      )}
      {phase === "applying" && <button className="btn wide" disabled><span className="spinner" /> Сохраняем…</button>}
      {phase === "applied" && <button className="btn wide" disabled><span className="spinner" /> Сохранено — проверяем</button>}
      {phase === "verified" && <button className="btn wide chip-verified" disabled>✓ Подтверждён</button>}
      {["needs_input", "infeasible", "validation_failed", "failed", "interrupted"].includes(phase) && (
        <p className="muted small">Подтверждение недоступно. Проверьте данные и повторите анализ.</p>
      )}
    </div>
  );
}
