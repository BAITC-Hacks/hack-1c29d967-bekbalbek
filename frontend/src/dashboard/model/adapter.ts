import type { ComponentType } from "react";
import type { Api } from "../../api/client";
import type { CaseView, EvidenceRef, Proposal, ValidationReport } from "../../api/types";
import type { BeforeAfterRow, ChangeRow, EvidenceDescription, Table } from "./changes";

export type JsonInput = Record<string, unknown>;

export interface DemoPanelProps { api: Pick<Api, "request">; caseView: CaseView | null; onChanged: () => void }

// Connects the meeting dashboard to protocol tables, action items and transcript evidence.
export interface DomainAdapter {
  key: string;
  /** Header of the protocol's before/after comparison column. */
  beforeAfterLabel: string;
  /** Meeting upload, transcription and speaker review panel. */
  DemoPanel?: ComponentType<DemoPanelProps>;
  tableFor(view: CaseView): Table;
  changesFor(proposal: Proposal, validation: ValidationReport, view: CaseView): ChangeRow[];
  beforeAfter(beforeRaw: unknown, afterRaw: unknown): BeforeAfterRow[];
  describeEvidence(ref: EvidenceRef, view: CaseView): EvidenceDescription;
  applyMissingField(input: JsonInput, field: string, value: string): JsonInput;
}
