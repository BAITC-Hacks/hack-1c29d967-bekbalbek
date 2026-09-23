import { useState } from "react";
import type { CreateRunRequest } from "../../api/types";
export interface RunSeed { case_ref: string; goal: string; input: Record<string, unknown> }
interface Props {
  seed: RunSeed; description: string; hasRun: boolean; busy: boolean;
  blockedReason?: string | null; onStart: (request: CreateRunRequest) => void;
}
export function StartCard({ seed, description, hasRun, busy, blockedReason, onStart }: Props) {
  const [openOverride, setOpenOverride] = useState<boolean | null>(null);
  const [goal, setGoal] = useState(seed.goal);
  const [date, setDate] = useState(String(seed.input.meeting_date ?? ""));
  const [language, setLanguage] = useState(String(seed.input.language ?? "auto"));
  const [notes, setNotes] = useState(String(seed.input.notes ?? ""));
  const open = openOverride ?? !hasRun;
  const disabled = busy || Boolean(blockedReason) || !goal.trim() || !date;
  const submit = () => {
    if (disabled) return;
    setOpenOverride(null);
    onStart({ case_ref: seed.case_ref, goal: goal.trim(), input: { ...seed.input, meeting_date: date, language, notes: notes.trim() || null } });
  };
  const label = busy ? <><span className="spinner" /> Запускаем…</> : hasRun ? "Сформировать заново" : "Сформировать протокол";
  return <div className={`card request ${open ? "" : "compact"}`} role="region" aria-label="Формирование протокола">
    {open ? <>
      <div className="card-h"><span className="chip">○ {hasRun ? "Повторный анализ" : "Новый протокол"}</span>{description && <strong>{description}</strong>}</div>
      <label className="field"><span className="field-l">Задача для анализа</span><textarea value={goal} onChange={(event) => setGoal(event.target.value)} rows={2} /></label>
      <div className="meeting-fields">
        <label className="field"><span className="field-l">Дата для расчёта сроков</span><input type="date" required value={date} onChange={(event) => setDate(event.target.value)} /></label>
        <label className="field"><span className="field-l">Язык анализа</span><select value={language} onChange={(event) => setLanguage(event.target.value)}><option value="auto">Автоматически</option><option value="ru">Русский</option><option value="kk">Қазақша</option></select></label>
      </div>
      <label className="field"><span className="field-l">Уточнения для анализа (необязательно)</span><textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={2000} rows={2} placeholder="Контекст, имена участников или важные ограничения" /></label>
    </> : <><span className="chip">○ Анализ</span><span className="request-goal">{goal}</span></>}
    {blockedReason && <p className="muted">{blockedReason}</p>}
    <div className="card-actions">
      {!open && <button className="btn btn-ghost" onClick={() => setOpenOverride(true)}>Параметры анализа</button>}
      {open && hasRun && <button className="btn btn-ghost" onClick={() => setOpenOverride(false)}>Свернуть</button>}
      <button className="btn btn-primary" onClick={submit} disabled={Boolean(disabled)}>{label}</button>
    </div>
  </div>;
}
