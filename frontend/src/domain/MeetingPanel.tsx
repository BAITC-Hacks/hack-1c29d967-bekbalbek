import type { DemoPanelProps } from "../dashboard/model/adapter";
export function MeetingPanel({ caseView }: DemoPanelProps) {
  return <section className="card"><h2>Запись совещания</h2><p>{caseView?.title ?? "Выберите запись совещания"}</p></section>;
}
