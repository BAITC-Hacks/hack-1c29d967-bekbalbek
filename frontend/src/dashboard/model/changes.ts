import type { CheckStatus, EvidenceRef } from "../../api/types";

export interface TableRow { id: string; cells: string[] }
export interface Table { columns: string[]; rows: TableRow[] }

export interface ChangeCheck { name: string; status: CheckStatus; message: string; source: string | null }

export interface ChangeRow {
  id: string;
  rowId: string;
  label: string;
  field: string;
  from: string;
  to: string;
  checks: ChangeCheck[];
  why: string;
  evidence: EvidenceRef[];
}

export interface BeforeAfterRow { label: string; before: string; after: string }
export interface EvidenceDescription { title: string; source?: string; snippet?: string }
