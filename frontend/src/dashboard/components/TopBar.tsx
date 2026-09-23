import { brand } from "../../config";
import type { Health } from "../../api/types";

interface Props {
  health: Health | null;
  dark: boolean;
  onToggleTheme: () => void;
  onReset: () => void;
  resetting: boolean;
  toast: string | null;
}

export function TopBar({ health, dark, onToggleTheme, onReset, resetting, toast }: Props) {
  const ok = health?.status === "ok";
  return (
    <header className="top">
      <a href="#/" className="logo"><span className="logo-mark" />{brand.name}</a>
      <span className="top-sep" />
      <span className="top-ws">Workspace</span>
      <div className="top-health" title={health ? `db ${health.database} · model ${health.model} · key ${health.api_key_configured ? "set" : "missing"}` : "Backend unreachable"}>
        <span className={`dot ${ok ? "dot-verified" : "dot-failed"}`} />
        {health ? `${health.model} · db ${health.database}${health.api_key_configured ? "" : " · no API key"}` : "Backend unreachable"}
      </div>
      {toast && <span className="toast" role="status">{toast}</span>}
      <div className="top-actions">
        <button className="btn btn-ghost" onClick={onToggleTheme} aria-label="Toggle theme">{dark ? "Light" : "Dark"}</button>
        <button className="btn" onClick={onReset} disabled={resetting}>{resetting ? "Resetting…" : "Reset sample data"}</button>
      </div>
    </header>
  );
}
