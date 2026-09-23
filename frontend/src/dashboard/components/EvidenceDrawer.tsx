import { useState } from "react";
import type { CaseView } from "../../api/types";
import type { DomainAdapter } from "../model/adapter";
import type { ChangeRow } from "../model/changes";

type CopyState = { ref: string; ok: boolean } | null;

async function writeClipboard(text: string): Promise<boolean> {
  try {
    if (!navigator.clipboard) return false;
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export function EvidenceDrawer({ change, caseView, domain, onClose }: { change: ChangeRow; caseView: CaseView | null; domain: DomainAdapter; onClose: () => void }) {
  const [copied, setСкопировано] = useState<CopyState>(null);
  const copy = async (ref: string) => setСкопировано({ ref, ok: await writeClipboard(ref) });
  return (
    <section className="evidence" aria-label="Цитаты">
      <h4>Основание поручения <button className="act-d" onClick={onClose} aria-label="Закрыть цитаты">Закрыть</button></h4>
      <p>{change.why || "Проверки пройдены."}</p>
      <div className="ev-list">
        {change.evidence.map((ref, i) => {
          const described = caseView ? domain.describeEvidence(ref, caseView) : { title: ref.ref, snippet: ref.note ?? undefined };
          const feedback = copied?.ref === ref.ref ? (copied.ok ? "Скопировано" : "Не удалось скопировать — выделите ссылку и скопируйте вручную") : null;
          return (
            <div key={`${ref.ref}-${i}`} className="ev-box">
              <div className="ev-head"><span className="chip mini">{{ record: "Реплика", rule: "Правило", tool_result: "Результат проверки" }[ref.kind]}</span><span className="ev-title">{described.title}</span></div>
              {described.source && <div className="ev-src mono">{described.source}</div>}
              {described.snippet && <div className="ev-snip">{described.snippet}</div>}
              <div className="ev-actions">
                <button className="btn btn-ghost" onClick={() => { void copy(ref.ref); }}>Скопировать ссылку</button>
                <span className="mono muted">{ref.ref}</span>
                {feedback && <span className={`small ${copied?.ok ? "muted" : "err"}`} role="status">{feedback}</span>}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
