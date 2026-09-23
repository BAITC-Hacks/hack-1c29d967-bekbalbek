import type { ChangeRow } from "../model/changes";

const checkChip = (status: "pass" | "warn" | "fail") => (status === "pass" ? "chip-verified" : status === "warn" ? "chip-attention" : "chip-failed");

export function ChangeList({ changes, selected, onSelect }: { changes: ChangeRow[]; selected: string | null; onSelect: (id: string | null) => void }) {
  if (changes.length === 0) return null;
  return (
    <section aria-label="Предложенные поручения">
      <h4>Предложенные поручения <span className="cnt">{changes.length}</span></h4>
      <ul className="changes">
        {changes.map((change) => (
          <li key={change.id} className={change.id === selected ? "on" : ""}>
            <button onClick={() => onSelect(change.id === selected ? null : change.id)} aria-pressed={change.id === selected}>
              <span className="ch-t">{change.label}</span>
              <span className="ch-d">{change.field}: <s>{change.from}</s> → <b>{change.to}</b></span>
              <span className="ch-k">
                {change.checks.map((check) => (
                  <span key={`${check.name}-${check.message}`} className={`chip mini ${checkChip(check.status)}`} title={check.message}>
                    {check.status === "pass" ? "✓" : check.status === "warn" ? "!" : "✕"} {check.name}
                  </span>
                ))}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
