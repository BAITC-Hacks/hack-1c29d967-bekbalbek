import type { ComponentType } from "react";
import type { Api } from "../../api/client";
import type { CaseView, EvidenceRef, Proposal, ValidationReport } from "../../api/types";
import type { BeforeAfterRow, ChangeRow, EvidenceDescription, Table } from "./changes";

export type JsonInput = Record<string, unknown>;

export interface DemoPanelProps { api: Pick<Api, "request">; caseView: CaseView | null; onChanged: () => void }

// The contract between the generic dashboard and a domain module. A new business case implements this
// once (see frontend/src/domain/protokol.ts for the sample) and nothing under src/dashboard changes.
export interface DomainAdapter {
  key: string;
  /** Header of the row-label column in the before/after load table, e.g. "Worker · date". */
  beforeAfterLabel: string;
  /** Optional demo-only panel rendered with the request card, e.g. to change data before applying. */
  DemoPanel?: ComponentType<DemoPanelProps>;
  tableFor(view: CaseView): Table;
  changesFor(proposal: Proposal, validation: ValidationReport, view: CaseView): ChangeRow[];
  beforeAfter(beforeRaw: unknown, afterRaw: unknown): BeforeAfterRow[];
  describeEvidence(ref: EvidenceRef, view: CaseView): EvidenceDescription;
  applyMissingField(input: JsonInput, field: string, value: string): JsonInput;
}
