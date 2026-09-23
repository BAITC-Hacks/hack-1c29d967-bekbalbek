import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ActionItem, CaseView, MeetingDetail, MeetingSpeaker } from "../api/types";
import type { DemoPanelProps } from "../dashboard/model/adapter";
import { getMeeting, protocolDocxUrl, protocolPdfUrl, renameSpeaker, startTranscription, uploadMeeting } from "./api";
import { fmt } from "./protokol";
import { localDate, readItemStatus, statusFor, type ItemStatus } from "./status";
import "./meeting-panel.css";

const describe = (error: unknown) => error instanceof Error ? error.message : String(error);
const statusLabels = { uploaded: "загружена", transcribing: "распознаётся", ready: "стенограмма готова", failed: "ошибка" };

function UploadForm({ onChanged, hasMeeting }: Pick<DemoPanelProps, "onChanged"> & { hasMeeting: boolean }) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(localDate);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || busy || !title.trim() || !date) return;
    if (!file.size || file.size > 300 * 1024 * 1024) { setError("Выберите непустую запись размером до 300 MiB."); return; }
    setBusy(true); setError(null);
    try {
      const meeting = await uploadMeeting(file, title.trim(), date);
      window.location.hash = `#/app/example/${encodeURIComponent(meeting.id)}`;
      onChanged();
      setFile(null); setTitle("");
      if (fileInput.current) fileInput.current.value = "";
    } catch (cause) { setError(describe(cause)); }
    finally { setBusy(false); }
  };
  return <details className="meeting-upload" open={!hasMeeting}>
    <summary>Новая запись</summary>
    <form onSubmit={(event) => { void submit(event); }} className="upload-form">
      <label className="field"><span>Аудио или видео</span>
        <input ref={fileInput} aria-label="Аудио или видео" type="file" accept="audio/*,.mp3,.wav,.m4a,.mp4,.ogg,.webm,.flac" disabled={busy} required
          onChange={(event) => { const next = event.target.files?.[0] ?? null; setFile(next); if (next && !title) setTitle(next.name.replace(/\.[^.]+$/, "").slice(0, 200)); }} />
        <span className="muted small">MP3, WAV, M4A, MP4, OGG, WEBM, FLAC · до 300 MiB</span>
      </label>
      <div className="meeting-fields">
        <label className="field"><span>Название совещания</span><input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} required disabled={busy} /></label>
        <label className="field"><span>Дата совещания</span><input type="date" value={date} onChange={(event) => setDate(event.target.value)} required disabled={busy} /></label>
      </div>
      <span className="muted small">Укажите фактическую дату: от неё считаются сроки «до пятницы» и «через неделю».</span>
      {error && <p className="err" role="alert">{error}</p>}
      <button className="btn btn-primary" type="submit" disabled={busy || !file || !title.trim() || !date}>{busy ? <><span className="spinner" /> Загружаем…</> : "Загрузить"}</button>
    </form>
  </details>;
}

function SpeakerEditor({ api, meetingId, speaker, onChanged }: { api: DemoPanelProps["api"]; meetingId: string; speaker: MeetingSpeaker; onChanged: () => void }) {
  const [name, setName] = useState(speaker.display_name);
  const [saved, setSaved] = useState(speaker.display_name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const saving = useRef(false);
  const save = async () => {
    const value = name.trim();
    if (saving.current || value === saved) return;
    if (!value) { setError("Имя не может быть пустым"); return; }
    saving.current = true; setBusy(true); setError(null);
    try { const result = await renameSpeaker(api, meetingId, speaker.speaker_id, value); setSaved(result.speaker.display_name); setName(result.speaker.display_name); onChanged(); }
    catch (cause) { setError(describe(cause)); }
    finally { saving.current = false; setBusy(false); }
  };
  return <div className="speaker-editor">
    <label><span className="chip">{speaker.speaker_id}</span>
      <input aria-label={`Имя ${speaker.speaker_id}`} value={name} maxLength={200} disabled={busy}
        onChange={(event) => setName(event.target.value)} onBlur={() => { void save(); }}
        onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); void save(); } }} />
    </label>
    <button type="button" className="btn btn-ghost" disabled={busy || name.trim() === saved} onClick={() => { void save(); }} aria-label={`Сохранить имя ${speaker.speaker_id}`}>{busy ? "Сохраняем…" : "Сохранить"}</button>
    {error && <span className="err" role="alert">{error}</span>}
  </div>;
}

function StatusBoard({ items }: { items: ActionItem[] }) {
  const [statuses, setStatuses] = useState<Record<string, ItemStatus>>(() => Object.fromEntries(items.map((item) => [item.id, readItemStatus(item)])));
  const [storageError, setStorageError] = useState(false);
  const today = localDate();
  const ordered = [...items].sort((a, b) => (a.deadline_date ?? "9999").localeCompare(b.deadline_date ?? "9999") || a.id.localeCompare(b.id));
  const state = (item: ActionItem) => statusFor(item, statuses[item.id] ?? readItemStatus(item), today);
  const counts = { new: 0, in_progress: 0, done: 0, overdue: 0 };
  for (const item of items) counts[state(item)]++;
  const labels = { new: "новое", in_progress: "в работе", done: "выполнено", overdue: "просрочено" };
  const change = (id: string, value: ItemStatus) => {
    setStatuses((current) => ({ ...current, [id]: value }));
    try { localStorage.setItem(`protokol.status.${id}`, value); }
    catch { setStorageError(true); }
  };
  return <section className="status-board" aria-label="Поручения">
    <h3>Поручения</h3>
    <p aria-live="polite" className="muted">новых {counts.new} · в работе {counts.in_progress} · выполнено {counts.done} · просрочено {counts.overdue}</p>
    <p className="small muted">Статусы хранятся локально в этом браузере; в PDF/DOCX они не передаются.</p>
    {storageError && <p role="alert" className="err">Браузер запретил сохранение. Статусы сохранятся только до закрытия страницы.</p>}
    {items.length === 0 ? <p>В этом совещании поручения не зафиксированы.</p> : <div className="meeting-table-scroll"><table className="tbl">
      <thead><tr>{["№", "Поручение", "Ответственный", "Срок", "Срочность", "Статус"].map((label) => <th key={label}>{label}</th>)}</tr></thead>
      <tbody>{ordered.map((item, index) => <tr key={item.id}>
        <td>{index + 1}</td><td>{item.text}</td><td>{item.owner_name || "не назначен"}</td>
        <td>{item.deadline_date ?? (item.deadline_text || "срок не указан")}{item.deadline_date && item.deadline_text && <small className="deadline-source">{item.deadline_text}</small>}</td>
        <td>{item.urgency}</td><td><span className={`chip ${state(item) === "overdue" ? "chip-failed" : state(item) === "done" ? "chip-verified" : ""}`}>{labels[state(item)]}</span>
          <select aria-label={`Статус поручения ${index + 1}`} value={statuses[item.id] ?? readItemStatus(item)} onChange={(event) => change(item.id, event.target.value as ItemStatus)}>
            <option value="new">Новое</option><option value="in_progress">В работе</option><option value="done">Выполнено</option>
          </select>
        </td>
      </tr>)}</tbody>
    </table></div>}
  </section>;
}

function MeetingSession({ api, caseView, onChanged }: DemoPanelProps & { caseView: CaseView }) {
  const [update, setUpdate] = useState<{ basis: CaseView; detail: MeetingDetail } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);
  const changed = useRef(onChanged);
  useEffect(() => { changed.current = onChanged; }, [onChanged]);
  const current = update?.basis === caseView ? update.detail : caseView;
  const { meeting, speakers, segments, protocol, action_items } = current;
  const status = meeting.status;
  useEffect(() => {
    if (status !== "transcribing") return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    const poll = async () => {
      try {
        const detail = await getMeeting(api, meeting.id, controller.signal);
        if (stopped) return;
        setPollError(null);
        if (detail.meeting.status !== "transcribing") {
          setUpdate({ basis: caseView, detail }); changed.current(); return;
        }
      } catch (cause) {
        if (stopped) return;
        setPollError(`Не удалось обновить состояние: ${describe(cause)}. Повторяем запрос…`);
      }
      if (!stopped) timer = setTimeout(() => { void poll(); }, 2000);
    };
    timer = setTimeout(() => { void poll(); }, 2000);
    return () => { stopped = true; clearTimeout(timer); controller.abort(); };
  }, [api, meeting.id, status, caseView]);
  const transcribe = async () => {
    setBusy(true); setError(null);
    try {
      await startTranscription(api, meeting.id);
      setUpdate({ basis: caseView, detail: { ...current, meeting: { ...meeting, status: "transcribing", error: null } } });
      onChanged();
    } catch (cause) { setError(describe(cause)); }
    finally { setBusy(false); }
  };
  const languages = segments.reduce<Record<string, number>>((result, segment) => { result[segment.language.toUpperCase()] = (result[segment.language.toUpperCase()] ?? 0) + 1; return result; }, {});
  return <div className="meeting-session">
    <div className="meeting-meta" aria-live="polite">
      <h3>Состояние записи</h3>
      <span className={`chip ${status === "failed" ? "chip-failed" : status === "ready" ? "chip-verified" : "chip-applying"}`}>{status === "transcribing" && <span className="spinner" />}{statusLabels[status]}</span>
      {meeting.duration_s !== null && <span className="mono">{fmt(meeting.duration_s)}</span>}
      {Object.entries(languages).map(([language, count]) => <span className={`chip ${language === "KK" ? "chip-proposed" : ""}`} key={language}>{language} {count}</span>)}
    </div>
    {meeting.error && <p className="err" role="alert">{meeting.error}</p>}
    {pollError && <p className="err" role="alert">{pollError}</p>}
    {error && <p className="err" role="alert">{error}</p>}
    {!protocol && <button className="btn" disabled={busy || status === "transcribing"} onClick={() => { void transcribe(); }}>{busy ? "Запускаем…" : status === "transcribing" ? "Распознаётся…" : "Транскрибировать"}</button>}
    {status === "ready" && <details className="meeting-speakers">
      <summary>Говорящие · {speakers.length}</summary>
      <p className="muted small">Уточните имена до формирования протокола. После переименования запустите анализ заново.</p>
      {speakers.map((speaker) => <SpeakerEditor key={`${speaker.speaker_id}:${speaker.display_name}`} api={api} meetingId={meeting.id} speaker={speaker} onChanged={onChanged} />)}
    </details>}
    {protocol && <section className="confirmed-protocol" aria-label="Подтверждённый протокол">
      <div className="meeting-meta"><h3>Протокол подтверждён</h3><a className="btn" href={protocolPdfUrl(meeting.id)} download>Скачать PDF</a><a className="btn" href={protocolDocxUrl(meeting.id)} download>Скачать DOCX</a></div>
      <p>{protocol.summary}</p>
      {protocol.decisions.length > 0 && <><h4>Решения</h4><ul>{protocol.decisions.map((decision, index) => <li key={index}>{decision}</li>)}</ul></>}
      <StatusBoard key={protocol.id} items={action_items} />
    </section>}
  </div>;
}

export function MeetingPanel(props: DemoPanelProps) {
  return <section className="meeting-panel card" aria-label="Запись совещания">
    <UploadForm onChanged={props.onChanged} hasMeeting={Boolean(props.caseView)} />
    {props.caseView && <MeetingSession key={props.caseView.case_ref} {...props} caseView={props.caseView} />}
  </section>;
}
