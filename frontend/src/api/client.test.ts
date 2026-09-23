import { ApiError, createApi } from "./client";
import { makeRun } from "../test/fixtures";

function fakeFetch(status: number, body: unknown, capture?: { calls: { url: string; init?: RequestInit }[] }) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    capture?.calls.push({ url, init });
    return new Response(body === undefined ? null : JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
  }) as unknown as typeof fetch;
}

describe("api client", () => {
  it("should post a run request and return the run", async () => {
    const capture = { calls: [] as { url: string; init?: RequestInit }[] };
    const api = createApi(fakeFetch(202, { run: makeRun() }, capture));
    const run = await api.createRun({ case_ref: "m-sample-1", goal: "g", input: { planning_start: "2026-09-24" } });
    expect(run.id).toBe("run-1");
    expect(capture.calls[0].url).toBe("/api/runs");
    expect(capture.calls[0].init?.method).toBe("POST");
    expect(JSON.parse(String(capture.calls[0].init?.body))).toEqual({ case_ref: "m-sample-1", goal: "g", input: { planning_start: "2026-09-24" } });
  });

  it("should turn the error envelope into an ApiError with code and details", async () => {
    const api = createApi(fakeFetch(409, { error: { code: "stale_proposal", message: "changed", details: { fingerprint_changed: true } } }));
    const error = await api.apply("run-1", "p-1", 1).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("stale_proposal");
    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).details).toEqual({ fingerprint_changed: true });
  });

  it("should turn FastAPI 422 details into a readable validation error", async () => {
    const api = createApi(fakeFetch(422, { detail: [{ loc: ["body", "input", "planning_start"], msg: "Input should be a valid date", type: "date" }] }));
    const error = (await api.createRun({ case_ref: "x", goal: "g", input: {} }).catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("validation_error");
    expect(error.message).toContain("input.planning_start");
    expect(error.message).toContain("valid date");
  });

  it("should report network failures as network_error", async () => {
    const failing = vi.fn(async () => { throw new TypeError("Failed to fetch"); }) as unknown as typeof fetch;
    const error = (await createApi(failing).health().catch((e: unknown) => e)) as ApiError;
    expect(error.code).toBe("network_error");
  });

  it("should pass the after parameter when listing events", async () => {
    const capture = { calls: [] as { url: string; init?: RequestInit }[] };
    const api = createApi(fakeFetch(200, { events: [] }, capture));
    await api.listEvents("run-1", 7);
    expect(capture.calls[0].url).toBe("/api/runs/run-1/events/list?after=7");
  });

  it("should unwrap list responses", async () => {
    const api = createApi(fakeFetch(200, { runs: [makeRun()] }));
    expect((await api.listRuns()).map((r) => r.id)).toEqual(["run-1"]);
  });

  it("should turn a malformed success body into a coded error", async () => {
    const api = createApi(async () => new Response("not json", { status: 200, headers: { "content-type": "application/json" } }));
    await expect(api.health()).rejects.toMatchObject({ code: "bad_response" });
  });
});
