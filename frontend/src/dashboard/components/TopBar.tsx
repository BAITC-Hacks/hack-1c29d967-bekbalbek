import { brand } from "../../config";
import type { Health } from "../../api/types";
interface Props {
  health: Health | null; dark: boolean; onToggleTheme: () => void;
  onReset: () => void; resetting: boolean; toast: string | null;
}
export function TopBar({ health, dark, onToggleTheme, onReset, resetting, toast }: Props) {
  const guarded = health?.provenance?.enabled === true;
  return <header className="top">
    <a href="#/" className="logo"><span className="logo-mark" />{brand.name}</a>
    <span className="top-sep" /><span className="top-ws">Совещания</span>
    <div className="top-health" aria-live="polite">
      {!health ? <span className="chip chip-failed">Сервер недоступен</span> : <>
        <span className={`chip ${guarded ? "chip-verified" : "chip-attention"}`}>{guarded ? "Защита сети включена" : "Защита сети выключена"}</span>
        <span title="Число внешних попыток, заблокированных backend. Это не счётчик разрешённых соединений.">Заблокировано: {health.provenance?.blocked_external_connections ?? "—"}</span>
        <span className="mono">{health.model}</span>
        {health.model.startsWith("scripted:") && <span className="chip chip-attention">Демонстрационный режим</span>}
        {health.models_present === false && <span className="chip chip-attention">Модели не установлены</span>}
        {health.database !== "ok" && <span className="chip chip-failed">База недоступна</span>}
      </>}
    </div>
    {toast && <span className="toast" role="status">{toast}</span>}
    <div className="top-actions">
      <button className="btn btn-ghost" onClick={onToggleTheme} aria-label="Сменить тему">{dark ? "Светлая" : "Тёмная"}</button>
      <button className="btn" onClick={onReset} disabled={resetting}>{resetting ? "Сбрасываем…" : "Сбросить примеры"}</button>
    </div>
  </header>;
}
