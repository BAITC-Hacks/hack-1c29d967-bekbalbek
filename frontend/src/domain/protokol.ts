import type { ActionItemAction, CaseView, ProposedAction, Snapshot } from "../api/types";
import type { DomainAdapter } from "../dashboard/model/adapter";
import { MeetingPanel } from "./MeetingPanel";

export const isActionItem = (action: ProposedAction): action is ActionItemAction => action.type === "action_item";
export const fmt = (seconds: number): string => {
  const value = Math.max(0, Math.floor(seconds));
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(value % 60).padStart(2, "0")}`;
};
export const speakerName = (view: Pick<CaseView, "speakers">, id: string): string =>
  view.speakers.find((speaker) => speaker.speaker_id === id)?.display_name ?? id;
const snapshot = (raw: unknown): Snapshot | null => {
  if (!raw || typeof raw !== "object") return null;
  const value = raw as Partial<Snapshot>;
  return typeof value.action_items === "number" && typeof value.protocol_exists === "boolean" ? value as Snapshot : null;
};

export const protokolDomain: DomainAdapter = {
  key: "protokol",
  beforeAfterLabel: "Протокол",
  DemoPanel: MeetingPanel,
  tableFor: (view) => ({
    columns: ["Время", "Говорящий", "Язык", "Реплика"],
    rows: [
      ...view.segments.slice(0, 300).map((segment) => ({
        id: String(segment.id),
        cells: [fmt(segment.start_s), speakerName(view, segment.speaker_id), segment.language.toUpperCase(), segment.text],
      })),
      ...(view.segments.length > 300 ? [{ id: "remaining-segments", cells: ["…", "", "", `ещё ${view.segments.length - 300} реплик`] }] : []),
    ],
  }),
  changesFor: (proposal, validation, view) => proposal.actions.filter(isActionItem).map((action) => ({
    id: action.action_id,
    rowId: String(action.source_segment_ids[0] ?? ""),
    label: `${action.owner_speaker_id ? speakerName(view, action.owner_speaker_id) : action.owner_name} · ${action.deadline_date ?? (action.deadline_text || "срок не указан")}`,
    field: action.urgency,
    from: "—", to: action.text,
    checks: validation.checks.filter((check) => check.action_id === action.action_id)
      .map((check) => ({ name: check.label, status: check.status, message: check.message, source: check.source })),
    why: action.deadline_text ? `Срок из речи: «${action.deadline_text}»` : "Срок в речи не назван",
    evidence: action.source_segment_ids.map((id) => ({ kind: "record" as const, ref: `segment:${id}`, note: null })),
  })),
  beforeAfter: (beforeRaw, afterRaw) => {
    const before = snapshot(beforeRaw), after = snapshot(afterRaw);
    if (!before || !after) return [];
    return [
      { label: "Поручений в протоколе", before: String(before.action_items), after: String(after.action_items) },
      { label: "Протокол подтверждён", before: before.protocol_exists ? "да" : "нет", after: after.protocol_exists ? "да" : "нет" },
    ];
  },
  describeEvidence: (ref, view) => {
    const match = /^segment:(\d+)$/.exec(ref.ref);
    const segment = match ? view.segments.find((item) => item.id === Number(match[1])) : undefined;
    return segment ? {
      title: `${speakerName(view, segment.speaker_id)} · ${fmt(segment.start_s)}`,
      source: `реплика №${segment.idx + 1}`, snippet: segment.text,
    } : { title: ref.ref, snippet: ref.note ?? undefined };
  },
  applyMissingField: (input, field, value) => ({ ...input, [field]: value }),
};
