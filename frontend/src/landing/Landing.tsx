import { useEffect, useRef, useState } from "react";
import { brand, heroScenes, tourTabs, howItWorks, sampleCases, landingCopy } from "../config";
import "./landing.css";

/* ---------------- tiny hooks ---------------- */
function useInView<T extends HTMLElement>(threshold = 0.4) {
  const ref = useRef<T>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => e.isIntersecting && setInView(true), { threshold });
    io.observe(el);
    return () => io.disconnect();
  }, [threshold]);
  return { ref, inView };
}

/* ---------------- hero scenes ---------------- */
function SceneActivity({ scene, active }: { scene: (typeof heroScenes)[0]; active: boolean }) {
  const [step, setStep] = useState(0);
  useEffect(() => {
    if (!active) return;
    const lines = scene.kind === "activity" ? scene.lines : [];
    const timers = [setTimeout(() => setStep(0), 0), ...lines.map((_, i) => setTimeout(() => setStep(i + 1), 500 + i * 1100))];
    return () => timers.forEach(clearTimeout);
  }, [active, scene]);
  if (scene.kind !== "activity") return null;
  return (
    <div className="mock">
      <div className="mock-head"><span className="chip chip-attention">Анализ</span><span className="mock-title">{scene.title}</span></div>
      <ul className="mock-activity">
        {scene.lines.map((l, i) => {
          const shown = active ? step : 0;
          const state = i < shown - 1 ? "done" : i === shown - 1 ? "running" : "pending";
          return (
            <li key={l.label} className={`act ${state}`}>
              <span className="act-icon">{state === "done" ? "✓" : state === "running" ? <span className="spinner" /> : "○"}</span>
              <span className="act-label">{l.label}</span>
              {l.detail && state !== "pending" && <span className="act-detail mono">{l.detail}</span>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function SceneProposal({ scene }: { scene: (typeof heroScenes)[1] }) {
  if (scene.kind !== "proposal") return null;
  return (
    <div className="mock">
      <div className="mock-head"><span className="chip chip-proposed">◇ Проект</span><span className="mock-title">{scene.title}</span></div>
      <div className="mock-rows">
        {scene.rows.map((r, i) => (
          <div key={r.label} className="diff-row" style={{ animationDelay: `${i * 80}ms` }}>
            <span className="diff-label">{r.label}</span>
            <span className="diff-field">{r.field}</span>
            <span className="diff-from">{r.from}</span>
            <span className="diff-arrow">→</span>
            <span className="diff-to">{r.to}</span>
          </div>
        ))}
      </div>
      <div className="mock-foot"><button className="btn btn-primary" tabIndex={-1}>{landingCopy.mockApply}</button><button className="btn btn-ghost" tabIndex={-1}>{landingCopy.mockWhy}</button></div>
    </div>
  );
}

function SceneVerified({ scene }: { scene: (typeof heroScenes)[2] }) {
  if (scene.kind !== "verified") return null;
  return (
    <div className="mock">
      <div className="mock-head"><span className="chip chip-verified">✓ Подтверждён</span><span className="mock-title">{scene.title}</span></div>
      <ul className="mock-verified">
        {scene.lines.map((l, i) => <li key={l} style={{ animationDelay: `${i * 120}ms` }}>✓ {l}</li>)}
      </ul>
    </div>
  );
}

function HeroDemo() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % heroScenes.length), 6500);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="hero-demo" aria-label="Иллюстрация работы интерфейса">
      <div className="hero-demo-tabs">
        {heroScenes.map((s, k) => (
          <button key={s.title} className={k === i ? "on" : ""} onClick={() => setI(k)}>{["Анализ", "Поручения", "Подтверждение"][k]}</button>
        ))}
      </div>
      <div className="hero-demo-stage">
        {heroScenes.map((s, k) => (
          <div key={s.title} className={`scene ${k === i ? "scene-on" : ""}`} aria-hidden={k !== i}>
            {s.kind === "activity" && <SceneActivity scene={s} active={k === i} />}
            {s.kind === "proposal" && <SceneProposal scene={s} />}
            {s.kind === "verified" && <SceneVerified scene={s} />}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------------- tour mocks ---------------- */
function MockTable({ highlight }: { highlight: boolean }) {
  const c = sampleCases[0];
  const changed = new Set(c.changes.map((ch) => ch.label.replace("#", "")));
  return (
    <div className="tour-mock">
      <div className="tm-toolbar"><span className="tm-search">Поиск совещаний</span><span className="chip">Пример поручений</span></div>
      <table className="tm-table">
        <thead><tr>{c.columns.map((h) => <th key={h}>{h}</th>)}</tr></thead>
        <tbody>
          {c.rows.map((r) => (
            <tr key={r.id} className={highlight && changed.has(r.id) ? "tm-changed" : ""}>
              {r.cells.map((cell, j) => <td key={j}>{cell}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function MockTimeline() {
  const c = sampleCases[0];
  return (
    <div className="tour-mock">
      <ul className="mock-activity">
        {c.events.map((e, i) => (
          <li key={e.key} className={`act ${i < 2 ? "done" : "running"}`}>
            <span className="act-icon">{i < 2 ? "✓" : <span className="spinner" />}</span>
            <span className="act-label">{e.label}</span>
            <span className="act-detail mono">{e.key} · {e.detail}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
function MockDocument() {
  return (
    <div className="tour-mock tm-doc">
      <div className="chip chip-verified">✓ Подтверждён</div>
      <h4>{landingCopy.tourResult.title}</h4>
      <p>{landingCopy.tourResult.body}</p>
      <div className="tm-evidence">{landingCopy.tourResult.evidenceLabel} <span className="ev">{landingCopy.tourResult.evidence}</span></div>
    </div>
  );
}

function Tour() {
  const [tab, setTab] = useState(0);
  const t = tourTabs[tab];
  return (
    <section id="tour" className="section">
      <div className="wrap">
        <h2 className="h2">{landingCopy.tourHeading}</h2>
        <div className="tour">
          <div className="tour-tabs" role="tablist">
            {tourTabs.map((x, i) => (
              <button key={x.id} role="tab" aria-selected={i === tab} className={i === tab ? "on" : ""} onClick={() => setTab(i)}>
                <span className="tour-n">{i + 1}</span>{x.label}
              </button>
            ))}
          </div>
          <div className="tour-body" key={t.id}>
            <div className="tour-text">
              <h3>{t.heading}</h3>
              <p>{t.body}</p>
            </div>
            <div className="tour-stage">
              {t.mock === "table" && <MockTable highlight={t.id === "propose"} />}
              {t.mock === "timeline" && <MockTimeline />}
              {t.mock === "document" && <MockDocument />}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ---------------- signature interaction ---------------- */
type Phase = keyof typeof landingCopy.signature.phases;
function Signature() {
  const { ref, inView } = useInView<HTMLDivElement>(0.5);
  const [phase, setPhase] = useState<Phase>("proposed");
  useEffect(() => {
    if (!inView) return;
    const t1 = setTimeout(() => setPhase("applying"), 1400);
    const t2 = setTimeout(() => setPhase("applied"), 2600);
    const t3 = setTimeout(() => setPhase("verified"), 3600);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [inView]);
  const ch = sampleCases[0].changes[0];
  const label = landingCopy.signature.phases[phase];
  return (
    <section id="signature" className="section section-alt">
      <div className="wrap wrap-2">
        <div>
          <h2 className="h2">{landingCopy.signature.heading}</h2>
          <p className="lead">{landingCopy.signature.lead}</p>
          <ol className="steps">{landingCopy.signature.steps.map((s) => <li key={s}>{s}</li>)}</ol>
        </div>
        <div ref={ref} className={`sig sig-${phase}`}>
          <div className="sig-head">
            <span className="sig-title">{ch.label} · {ch.field}</span>
            <span className={`chip chip-${phase}`}>{phase === "applying" ? <span className="spinner" /> : phase === "verified" ? "✓" : phase === "applied" ? "●" : "◇"} {label}</span>
          </div>
          <div className="sig-diff">
            <span className="diff-from">{ch.from}</span><span className="diff-arrow">→</span><span className="diff-to">{ch.to}</span>
          </div>
          <div className="sig-checks">
            {ch.checks.map((c) => <span key={c.name} className={`chip chip-${c.status === "pass" ? "verified" : c.status === "warn" ? "attention" : "failed"}`}>{c.status === "pass" ? "✓" : "!"} {c.name}</span>)}
          </div>
          <div className="sig-evidence">
            <span className="ev-src">{ch.evidence.source} · {ch.evidence.ref}</span>
            <span className="ev-snip">{ch.evidence.snippet}</span>
          </div>
          <button className={`btn btn-lg ${phase === "verified" ? "" : "btn-primary"}`} disabled={phase !== "proposed"}>{label}</button>
        </div>
      </div>
    </section>
  );
}

/* ---------------- page ---------------- */
export default function Landing() {
  return (
    <div className="landing">
      {brand.announcement && <div className="announce">{brand.announcement}</div>}
      <header className="nav">
        <div className="wrap nav-in">
          <a href="#/" className="logo"><span className="logo-mark" />{brand.name}</a>
          <nav>{brand.nav.map((n) => <a key={n.label} href={n.href}>{n.label}</a>)}</nav>
          <div className="nav-cta"><a className="btn btn-ghost" href="#how">{brand.ctaSecondary}</a><a className="btn btn-primary" href="#/app">{brand.ctaPrimary}</a></div>
        </div>
      </header>

      <section className="hero">
        <div className="wrap hero-in">
          <h1>{brand.tagline}</h1>
          <p className="lead">{brand.sub}</p>
          <div className="hero-cta"><a className="btn btn-primary btn-lg" href="#/app">{brand.ctaPrimary}</a><a className="btn btn-lg" href="#tour">{brand.ctaSecondary}</a></div>
          <p className="small muted">Ниже — иллюстрация интерфейса. Обработка вашей записи запускается в рабочем пространстве.</p>
          <HeroDemo />
        </div>
      </section>

      {brand.logos.length > 0 && (
        <div className="logos" aria-label="Partners">
          <div className="logos-track">{[...brand.logos, ...brand.logos].map((l, i) => <span key={i}>{l}</span>)}</div>
        </div>
      )}

      <Tour />
      <Signature />

      <section id="how" className="section">
        <div className="wrap">
          <h2 className="h2">{landingCopy.howHeading}</h2>
          <div className="how">
            {howItWorks.map((s, i) => (
              <div key={s.title} className="how-step">
                <span className="how-n">{i + 1}</span>
                <h3>{s.title}</h3>
                <p>{s.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section section-alt">
        <div className="wrap stats">
          {brand.stats.map((s) => <div key={s.label} className="stat"><strong>{s.value}</strong><span>{s.label}</span></div>)}
        </div>
      </section>

      <section className="section cta">
        <div className="wrap">
          <h2 className="h2">{landingCopy.ctaHeading}</h2>
          <a className="btn btn-primary btn-lg" href="#/app">{brand.ctaPrimary}</a>
        </div>
      </section>

      <footer className="foot"><div className="wrap">{brand.name} · {landingCopy.footer} · <a href="#/app">Совещания</a></div></footer>
    </div>
  );
}
