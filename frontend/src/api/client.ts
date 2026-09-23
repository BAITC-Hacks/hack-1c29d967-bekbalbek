import type {
  Application, ApiErrorBody, CaseView, CreateRunRequest, ExampleCase, Health, Run, RunDetail, RunEvent,
} from "./types";

export class ApiError extends Error {
  constructor(public readonly code: string, message: string, public readonly status: number, public readonly details: unknown = null) {
    super(message);
    this.name = "ApiError";
  }
}

interface FastApiValidationItem { loc: (string | number)[]; msg: string }

async function toApiError(response: Response): Promise<ApiError> {
  const body = (await response.json().catch(() => null)) as (ApiErrorBody & { detail?: unknown }) | null;
  if (body && "error" in body && body.error?.code) {
    return new ApiError(body.error.code, body.error.message, response.status, body.error.details ?? null);
  }
  if (body && Array.isArray(body.detail)) {
    const items = body.detail as FastApiValidationItem[];
    const message = items.map((d) => `${d.loc.filter((part) => part !== "body").join(".")}: ${d.msg}`).join("; ");
    return new ApiError("validation_error", message, response.status, items);
  }
  return new ApiError("http_error", `Ошибка запроса к серверу (HTTP ${response.status}).`, response.status, body);
}

export function createApi(fetchImpl: typeof fetch = (input, init) => fetch(input, init), base = "/api") {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetchImpl(`${base}${path}`, { ...init, headers: { "content-type": "application/json", ...(init?.headers ?? {}) } });
    } catch (cause) {
      throw new ApiError("network_error", "Не удалось связаться с сервером. Проверьте подключение и запуск сервера.", 0, cause);
    }
    if (!response.ok) throw await toApiError(response);
    try {
      return (await response.json()) as T;
    } catch (cause) {
      throw new ApiError("bad_response", "Не удалось прочитать ответ сервера. Повторите попытку.", response.status, cause);
    }
  }
  const post = <T>(path: string, body: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(body) });

  return {
    request,
    health: () => request<Health>("/health"),
    examples: async () => (await request<{ examples: ExampleCase[] }>("/domain/examples")).examples,
    caseView: (caseRef: string) => request<CaseView>(`/domain/cases/${encodeURIComponent(caseRef)}`),
    resetSampleData: () => post<{ status: string; seeded: Record<string, number> }>("/domain/reset", {}),
    listRuns: async (limit = 50) => (await request<{ runs: Run[] }>(`/runs?limit=${limit}`)).runs,
    createRun: async (body: CreateRunRequest) => (await post<{ run: Run }>("/runs", body)).run,
    getRun: (runId: string) => request<RunDetail>(`/runs/${runId}`),
    listEvents: async (runId: string, after?: number) =>
      (await request<{ events: RunEvent[] }>(`/runs/${runId}/events/list${after ? `?after=${after}` : ""}`)).events,
    apply: (runId: string, proposalId: string, version: number) =>
      post<{ run: Run; application: Application }>(`/runs/${runId}/apply`, { proposal_id: proposalId, version }),
  };
}

export type Api = ReturnType<typeof createApi>;
export const api: Api = createApi();
