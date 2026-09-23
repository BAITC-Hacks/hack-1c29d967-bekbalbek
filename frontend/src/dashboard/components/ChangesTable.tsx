import { useMemo } from "react";
import type { Phase } from "../model/phase";
import { phaseChip } from "../model/phase";
import type { ChangeRow, Table } from "../model/changes";

interface Props {
  table: Table;
  changes: ChangeRow[];
  phase: Phase;
  selected: string | null;
  onSelect: (changeId: string | null) => void;
}

const STAGGER_MS = 40;
const MAX_STAGGER_MS = 320;
const OVERLAY_PHASES: Phase[] = ["proposed", "applying", "applied", "verified", "validation_failed"];

export function ChangesTable({ table, changes, phase, selected, onSelect }: Props) {
  const byRow = useMemo(() => {
    const map = new Map<string, ChangeRow[]>();
    changes.forEach((change) => map.set(change.rowId, [...(map.get(change.rowId) ?? []), change]));
    return map;
  }, [changes]);
  const show = OVERLAY_PHASES.includes(phase);
  const rowPhase = phase === "validation_failed" ? "proposed" : phase;

  return (
    <table className="tbl">
      <thead><tr>{table.columns.map((column) => <th key={column}>{column}</th>)}</tr></thead>
      <tbody>
        {table.rows.map((row, index) => {
          const rowChanges = show ? byRow.get(row.id) : undefined;
          const isSelected = rowChanges?.some((c) => c.id === selected) ?? false;
          return (
            <tr
              key={row.id}
              className={`${rowChanges ? `changed ${rowPhase}` : ""} ${isSelected ? "sel" : ""}`}
              style={{ animationDelay: `${Math.min(index * STAGGER_MS, MAX_STAGGER_MS)}ms` }}
              onClick={() => rowChanges && onSelect(isSelected ? null : rowChanges[0].id)}
              data-testid={`row-${row.id}`}
            >
              {row.cells.map((cell, j) => {
                const change = rowChanges?.find((c) => c.field === table.columns[j]);
                return (
                  <td key={j}>
                    {change ? <span className="cell-diff"><s>{change.from}</s><b>{change.to}</b></span> : cell}
                    {j === 0 && rowChanges && <span className={`chip ${phaseChip[rowPhase].cls} mini`}>{phaseChip[rowPhase].text}</span>}
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
