import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Api } from "../api/client";
import type { CaseView, CreateRunRequest, ExampleCase, Health, Run } from "../api/types";
import type { DomainAdapter } from "./model/adapter";
import { AgentPanel } from "./components/AgentPanel";
import { CaseHeader } from "./components/CaseHeader";
import { CaseList } from "./components/CaseList";
import type { RunSeed } from "./components/StartCard";
import { TopBar } from "./components/TopBar";
import { Workspace } from "./components/Workspace";
import { isTerminalPhase } from "./model/phase";
import { exampleForRun, latestRunForExample, orphanRuns, runsForExample } from "./model/runs";
import { parseRoute, routeHash, type Route } from "./route";
import { useRun, type EventSourceFactory } from "./useRun";
import "./dashboard.css";

interface Props {
  api: Api;
  eventSourceFactory: EventSourceFactory;
  domain: DomainAdapter;
}

const TOAST_MS = 2500;
const THEME_KEY = "agent-workspace-theme";

const readTheme = (): boolean => { try { return localStorage.getItem(THEME_KEY) === "dark"; } catch { return false; } };
const writeTheme = (dark: boolean) => { try { localStorage.setItem(THEME_KEY, dark ? "dark" : "light"); } catch { /* storage unavailable */ } };
const describe = (error: unknown) => (error instanceof Error ? error.message : String(error));

export default function Dashboard({ api, eventSourceFactory, domain }: Props) {
  const controller = useRun(api, eventSourceFactory);
  const { detail, phase, select, start, timeline } = controller;
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.hash));
  const [health, setHealth] = useState<Health | null>(null);
  const [examples, setExamples] = useState<ExampleCase[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [caseView, setCaseView] = useState<CaseView | null>(null);
  const [dark, setDark] = useState(readTheme);
  const [toast, setToast] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);
  const [panelOpen, setPanelOpen] = useState(true);
  const [changeSelection, setChangeSelection] = useState<{ runId: string; changeId: string } | null>(null);
  const requestedRunId = useRef<string | null>(null);
  const caseRequest = useRef(0);

  const notify = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast((current) => (current === message ? null : current)), TOAST_MS);
  }, []);

  const loadRuns = useCallback(
    () => api.listRuns().then(setRuns).catch((error: unknown) => notify(`Не удалось загрузить историю: ${describe(error)}`)),
    [api, notify],
  );

  const loadCaseView = useCallback(
    (ref: string) => {
      const requestId = ++caseRequest.current;
      return api.caseView(ref).then((result) => { if (requestId === caseRequest.current) setCaseView(result); })
        .catch((error: unknown) => { if (requestId === caseRequest.current) notify(`Не удалось загрузить совещание: ${describe(error)}`); });
    },
    [api, notify],
  );

  const navigate = useCallback((next: Route) => {
    setRoute(next);
    const hash = routeHash(next);
    if (window.location.hash !== hash) window.location.hash = hash;
  }, []);

  useEffect(() => {
    const onHash = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    const refreshHealth = () => { void api.health().then(setHealth).catch(() => setHealth(null)); };
    refreshHealth();
    const healthTimer = window.setInterval(refreshHealth, 10000);
    api.examples().then(setExamples).catch((error) => notify(`Не удалось загрузить совещания: ${describe(error)}`));
    void loadRuns();
    return () => window.clearInterval(healthTimer);
  }, [api, loadRuns, notify]);

  const routeExample = route.kind === "example" ? examples.find((e) => e.id === route.id) ?? null : null;
  const routeRun = route.kind === "run" ? detail?.run ?? runs.find((r) => r.id === route.id) ?? null : null;
  const example = routeExample ?? (routeRun ? exampleForRun(routeRun, examples) : null);
  const caseRef = routeExample?.request.case_ref ?? routeRun?.case_ref ?? null;
  const targetRunId = route.kind === "run" ? route.id : routeExample ? latestRunForExample(runs, routeExample, examples)?.id ?? null : null;

  useEffect(() => {
    if (requestedRunId.current === targetRunId) return;
    requestedRunId.current = targetRunId;
    void select(targetRunId);
  }, [targetRunId, select]);
  useEffect(() => { document.documentElement.dataset.theme = dark ? "dark" : "light"; writeTheme(dark); }, [dark]);
  useEffect(() => { if (isTerminalPhase(phase) || phase === "proposed") void loadRuns(); }, [phase, loadRuns]);
  useEffect(() => { if (caseRef) void loadCaseView(caseRef); }, [caseRef, phase, loadCaseView]);

  const view = caseView && caseView.case_ref === caseRef ? caseView : null;
  const proposal = detail?.proposal ?? null;
  const selectedChange = changeSelection && changeSelection.runId === detail?.run.id ? changeSelection.changeId : null;
  const selectChange = (changeId: string | null) => setChangeSelection(changeId && detail ? { runId: detail.run.id, changeId } : null);

  const DemoPanel = domain.DemoPanel;
  const table = useMemo(() => (view ? domain.tableFor(view) : null), [view, domain]);
  const changes = useMemo(() => (proposal && view ? domain.changesFor(proposal.content, proposal.validation, view) : []), [proposal, view, domain]);
  const beforeAfterRows = useMemo(() => (detail ? domain.beforeAfter(detail.snapshot_before, detail.snapshot_after) : []), [detail, domain]);
  const history = useMemo(
    () => (example ? runsForExample(runs, example, examples) : caseRef ? orphanRuns(runs, examples).filter((r) => r.case_ref === caseRef) : []),
    [runs, example, examples, caseRef],
  );

  const refreshMeeting = useCallback(() => {
    void api.examples().then(setExamples).catch((error: unknown) => notify(`Не удалось обновить список: ${describe(error)}`));
    if (caseRef) void loadCaseView(caseRef);
  }, [api, caseRef, loadCaseView, notify]);

  const startRun = useCallback(async (request: CreateRunRequest) => {
    if (view?.meeting.status !== "ready") { notify("Сначала дождитесь готовности стенограммы"); return; }
    const run = await start(request);
    if (!run) return;
    requestedRunId.current = run.id;
    navigate({ kind: "run", id: run.id });
    void loadRuns();
  }, [start, navigate, loadRuns, view, notify]);

  const rerunSameRequest = useCallback(() => {
    if (detail) void startRun({ case_ref: detail.run.case_ref, goal: detail.run.goal, input: detail.run.input });
  }, [detail, startRun]);

  const reset = async () => {
    setResetting(true);
    try {
      await api.resetSampleData();
      notify("Примеры сброшены");
      navigate({ kind: "none" });
      await loadRuns();
      await api.examples().then(setExamples);
      setCaseView(null);
    } catch (error) {
      notify(`Не удалось сбросить примеры: ${describe(error)}`);
    } finally {
      setResetting(false);
    }
  };

  const seed: RunSeed | null = detail
    ? { case_ref: detail.run.case_ref, goal: detail.run.goal, input: detail.run.input }
    : example ? example.request : null;
  const title = example?.title ?? detail?.run.goal ?? "";
  const summary = detail
    ? detail.proposal?.content.summary ?? detail.needs_input?.message ?? detail.infeasible?.message ?? detail.application?.verification?.summary ?? detail.run.error?.message ?? ""
    : example?.description ?? "";

  return (
    <div className="dash">
      <TopBar health={health} dark={dark} onToggleTheme={() => setDark((d) => !d)} onReset={reset} resetting={resetting} toast={toast} />
      <div className="cols">
        <CaseList examples={examples} runs={runs} activeExampleId={example?.id ?? null} activeRunId={detail?.run.id ?? null}
          onPickExample={(picked) => navigate({ kind: "example", id: picked.id })} onPickRun={(id) => navigate({ kind: "run", id })} />
        <div className="center-col">
          {DemoPanel && <DemoPanel api={api} caseView={view} onChanged={refreshMeeting} />}
          {seed ? (
          <>
            <CaseHeader title={title} summary={summary} caseRef={caseRef ?? ""} phase={phase} outcome={detail?.run.outcome ?? null} model={detail?.run.model ?? null}
              history={history} activeRunId={detail?.run.id ?? null} onPickRun={(id) => navigate({ kind: "run", id })} />
            <Workspace
              seed={seed}
              startBlockedReason={view?.meeting.status === "ready" ? null : "Сначала транскрибируйте запись и дождитесь готовности стенограммы."}
              description={example?.description ?? ""}
              detail={detail}
              phase={phase}
              runError={detail?.run.error ?? timeline.lastError}
              table={table}
              changes={changes}
              beforeAfterRows={beforeAfterRows}
              selectedChange={selectedChange}
              onSelectChange={selectChange}
              busy={controller.busy}
              error={controller.error}
              onClearError={controller.clearError}
              onStart={startRun}
              onContinue={(input) => { if (detail) void startRun({ case_ref: detail.run.case_ref, goal: detail.run.goal, input }); }}
              onRerun={rerunSameRequest}
              domain={domain}
            />
          </>
        ) : (
          <main className="center"><div className="empty"><div><h2>Начните с записи совещания</h2><p>Загрузите файл выше или выберите совещание слева.</p></div></div></main>
        )}
        </div>
        <AgentPanel
          proposalKey={`${detail?.run.id ?? "none"}:${proposal?.id ?? "none"}:${proposal?.version ?? 0}`}
          phase={phase}
          steps={timeline.steps}
          connection={controller.connection}
          changes={changes}
          validation={proposal?.validation ?? null}
          proposalStatus={proposal?.status ?? null}
          selected={selectedChange}
          onSelect={selectChange}
          caseView={view}
          domain={domain}
          applying={controller.busy === "applying"}
          onApply={() => { void controller.apply().then(() => { void loadRuns(); refreshMeeting(); }); }}
          open={panelOpen}
          onToggle={() => setPanelOpen((o) => !o)}
        />
      </div>
    </div>
  );
}
