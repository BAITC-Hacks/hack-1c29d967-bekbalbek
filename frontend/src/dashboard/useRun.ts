import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, type Api } from "../api/client";
import type { CreateRunRequest, Run, RunDetail, RunEvent } from "../api/types";
import { initialTimeline, reduceTimeline, type TimelineState } from "./model/timeline";
import { isTerminalPhase, phaseFromStatus, type Phase } from "./model/phase";

export interface EventSourceLike {
  addEventListener(type: string, listener: (event: MessageEvent | Event) => void): void;
  close(): void;
}
export type EventSourceFactory = (url: string) => EventSourceLike;

export const EVENT_TYPES = [
  "run_started", "tool_started", "tool_finished", "tool_failed", "agent_output", "proposal_ready", "validation_failed",
  "revision_started", "apply_started", "apply_rejected", "action_applied", "verification_finished", "run_finished", "run_failed",
] as const;

const REFRESH_ON = new Set<string>(["agent_output", "proposal_ready", "validation_failed", "run_finished", "run_failed", "apply_rejected", "verification_finished"]);

export type Busy = "starting" | "applying" | null;
export type Connection = "idle" | "live" | "reconnecting" | "closed";

export interface RunController {
  detail: RunDetail | null;
  timeline: TimelineState;
  phase: Phase;
  busy: Busy;
  error: ApiError | null;
  connection: Connection;
  start: (request: CreateRunRequest) => Promise<Run | null>;
  select: (runId: string | null) => Promise<void>;
  apply: () => Promise<void>;
  clearError: () => void;
}

const asApiError = (error: unknown): ApiError =>
  error instanceof ApiError ? error : new ApiError("unexpected_error", "Произошла непредвиденная ошибка. Повторите попытку.", 0, error);

function emptyDetail(run: RunDetail["run"]): RunDetail {
  return { run, proposals: [], proposal: null, needs_input: null, infeasible: null, application: null, snapshot_before: null, snapshot_after: null, messages: [] };
}

export const defaultEventSourceFactory: EventSourceFactory = (url) => new EventSource(url);

export function useRun(api: Api, eventSourceFactory: EventSourceFactory = defaultEventSourceFactory): RunController {
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineState>(initialTimeline);
  const [busy, setBusy] = useState<Busy>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [connection, setConnection] = useState<Connection>("idle");
  const sourceRef = useRef<EventSourceLike | null>(null);
  const runIdRef = useRef<string | null>(null);
  const refreshSeq = useRef({ issued: 0, landed: 0 });

  const closeStream = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
      setConnection("closed");
    }
  }, []);

  const refresh = useCallback(async (runId: string): Promise<RunDetail | null> => {
    const seq = ++refreshSeq.current.issued;
    try {
      const next = await api.getRun(runId);
      if (runIdRef.current === runId && seq > refreshSeq.current.landed) {
        refreshSeq.current.landed = seq;
        setDetail(next);
      }
      return next;
    } catch (cause) {
      if (runIdRef.current === runId) setError(asApiError(cause));
      return null;
    }
  }, [api]);

  const openStream = useCallback((runId: string) => {
    const source = eventSourceFactory(`/api/runs/${runId}/events`);
    sourceRef.current = source;
    setConnection("live");
    const isCurrent = () => runIdRef.current === runId && sourceRef.current === source;
    source.addEventListener("error", () => { if (isCurrent()) setConnection("reconnecting"); });
    const onEvent = (message: MessageEvent | Event) => {
      if (!isCurrent()) return;
      setConnection("live");
      const raw = "data" in message ? String(message.data) : "";
      let event: RunEvent;
      try {
        event = JSON.parse(raw) as RunEvent;
      } catch {
        setError(new ApiError("bad_event", "Не удалось прочитать событие сервера. Журнал обработки может быть неполным.", 0, raw));
        return;
      }
      setTimeline((previous) => reduceTimeline(previous, event));
      if (REFRESH_ON.has(event.type)) void refresh(runId);
      if ((event.type === "run_finished" || event.type === "run_failed") && isTerminalPhase(phaseFromStatus(event.run_status))) {
        source.close();
        if (sourceRef.current === source) {
          sourceRef.current = null;
          setConnection("closed");
        }
      }
    };
    EVENT_TYPES.forEach((type) => source.addEventListener(type, onEvent));
  }, [eventSourceFactory, refresh]);

  const select = useCallback(async (runId: string | null) => {
    closeStream();
    runIdRef.current = runId;
    setTimeline(initialTimeline);
    setError(null);
    setDetail(null);
    if (!runId) return;
    const loaded = await refresh(runId);
    if (!loaded || runIdRef.current !== runId) return;
    if (isTerminalPhase(phaseFromStatus(loaded.run.status))) {
      try {
        const events = await api.listEvents(runId);
        if (runIdRef.current === runId) setTimeline(events.reduce(reduceTimeline, initialTimeline));
      } catch (cause) { if (runIdRef.current === runId) setError(asApiError(cause)); }
      return;
    }
    openStream(runId);
  }, [api, closeStream, openStream, refresh]);

  const start = useCallback(async (request: CreateRunRequest): Promise<Run | null> => {
    setBusy("starting");
    setError(null);
    try {
      const run = await api.createRun(request);
      closeStream();
      runIdRef.current = run.id;
      setTimeline(initialTimeline);
      setDetail(emptyDetail(run));
      openStream(run.id);
      return run;
    } catch (cause) {
      setError(asApiError(cause));
      return null;
    } finally {
      setBusy((current) => (current === "starting" ? null : current));
    }
  }, [api, closeStream, openStream]);

  const apply = useCallback(async () => {
    const current = detail;
    if (!current?.proposal) return;
    setBusy("applying");
    setError(null);
    try {
      const result = await api.apply(current.run.id, current.proposal.id, current.proposal.version);
      if (runIdRef.current === current.run.id) {
        setDetail((previous) => previous ? { ...previous, run: result.run, application: result.application } : previous);
        setTimeline((previous) => ({ ...previous, status: result.run.status }));
        if (isTerminalPhase(phaseFromStatus(result.run.status))) closeStream();
      }
    } catch (cause) {
      setError(asApiError(cause));
    } finally {
      setBusy((busyNow) => (busyNow === "applying" ? null : busyNow));
      await refresh(current.run.id);
    }
  }, [api, detail, refresh, closeStream]);

  useEffect(() => closeStream, [closeStream]);

  const phase = phaseFromStatus(timeline.status ?? detail?.run.status ?? null);
  return { detail, timeline, phase, busy, error, connection, start, select, apply, clearError: () => setError(null) };
}
