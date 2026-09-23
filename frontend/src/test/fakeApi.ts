import { ApiError, type Api } from "../api/client";
import type { CaseView, CreateRunRequest, ExampleCase, Run, RunDetail, RunEvent } from "../api/types";
import { caseView, confirmedCaseView, examples, makeRun, proposedDetail, snapshotAfter } from "./fixtures";

export interface FakeApiOptions {
  details?: Record<string, RunDetail>; events?: Record<string, RunEvent[]>;
  createRun?: (body: CreateRunRequest) => Run; apply?: Api["apply"]; runs?: Run[];
  caseView?: CaseView; examples?: ExampleCase[];
}
export function createFakeApi(options: FakeApiOptions = {}) {
  const details: Record<string, RunDetail> = structuredClone({ "run-1": proposedDetail, ...(options.details ?? {}) });
  let view = structuredClone(options.caseView ?? caseView);
  const calls = { createRun: [] as CreateRunRequest[], apply: [] as unknown[], getRun: [] as string[], listEvents: [] as string[], request: [] as { path: string; init?: RequestInit }[], reset: 0 };
  const api: Api = {
    request: async <T,>(path: string, init?: RequestInit): Promise<T> => {
      calls.request.push({ path, init });
      if (path.endsWith("/transcribe") && init?.method === "POST") {
        view = { ...view, status: "transcribing", meeting: { ...view.meeting, status: "transcribing" } };
        return { meeting_id: view.case_ref, status: "transcribing" } as T;
      }
      if (path.includes("/speakers/") && init?.method === "PATCH") {
        const id = decodeURIComponent(path.split("/").at(-1)!);
        const { display_name } = JSON.parse(String(init.body)) as { display_name: string };
        view = { ...view, speakers: view.speakers.map((speaker) => speaker.speaker_id === id ? { ...speaker, display_name } : speaker) };
        return { speaker: view.speakers.find((speaker) => speaker.speaker_id === id) } as T;
      }
      if (/^\/domain\/meetings\/[^/]+$/.test(path)) return structuredClone(view) as T;
      throw new ApiError("not_found", `No fake route for ${path}`, 404);
    },
    health: async () => ({ status: "ok", database: "ok", model: "scripted:auto", api_key_configured: false, domain: { key: "protokol", title: "Протокол совещания" }, active_runs: 0, version: "0.1.0", provenance: { enabled: true, blocked_external_connections: 0 }, llm_endpoint: "http://localhost:11434/v1", stt_device: "cuda", models_present: true }),
    examples: async () => structuredClone(options.examples ?? examples),
    caseView: async (ref) => ({ ...view, case_ref: ref, meeting: { ...view.meeting, id: ref } }),
    resetSampleData: async () => { calls.reset += 1; return { status: "ok", seeded: { meetings: 2 } }; },
    listRuns: async () => options.runs ?? Object.values(details).map((d) => d.run),
    createRun: async (body) => {
      calls.createRun.push(body);
      return options.createRun ? options.createRun(body) : makeRun({ status: "queued", outcome: null, stats: { duration_ms: null, tool_calls: 0, usage: null } });
    },
    getRun: async (runId) => {
      calls.getRun.push(runId);
      const detail = details[runId];
      if (!detail) throw new ApiError("run_not_found", `Unknown run ${runId}`, 404);
      return detail;
    },
    listEvents: async (runId) => { calls.listEvents.push(runId); return options.events?.[runId] ?? []; },
    apply: async (runId, proposalId, version) => {
      calls.apply.push({ runId, proposalId, version });
      if (options.apply) return options.apply(runId, proposalId, version);
      const application = { id: "app-1", proposal_id: proposalId, version, status: "verified" as const, actions: [], verification: { ok: true, summary: "3 поручения сохранены", checks: [] }, error: null, started_at: "t", finished_at: "t" };
      const current = details[runId];
      if (current) details[runId] = { ...current, run: { ...current.run, status: "verified" }, application, snapshot_after: snapshotAfter };
      view = structuredClone(confirmedCaseView);
      return { run: makeRun({ status: "verified" }), application };
    },
  };
  return { api, calls, details };
}
