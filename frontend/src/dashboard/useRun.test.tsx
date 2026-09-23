import { act, renderHook, waitFor } from "@testing-library/react";
import { ApiError } from "../api/client";
import { createFakeApi } from "../test/fakeApi";
import { FakeEventSource, fakeEventSourceFactory } from "../test/fakeEventSource";
import { applyEvents, happyEvents, makeRun, proposedDetail } from "../test/fixtures";
import { useRun } from "./useRun";

beforeEach(() => FakeEventSource.reset());

describe("useRun", () => {
  it("should start a run, stream its events into the timeline and refetch the detail when the proposal is ready", async () => {
    const { api, calls } = createFakeApi();
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));

    await act(() => result.current.start({ case_ref: "m-sample-1", goal: "g", input: { planning_start: "2026-09-24" } }));
    expect(calls.createRun).toHaveLength(1);
    expect(FakeEventSource.last().url).toBe("/api/runs/run-1/events");
    expect(result.current.phase).toBe("analyzing");

    act(() => FakeEventSource.last().emitAll(happyEvents));
    await waitFor(() => expect(result.current.phase).toBe("proposed"));
    expect(result.current.timeline.steps.filter((s) => s.kind === "tool")).toHaveLength(2);
    await waitFor(() => expect(result.current.detail?.proposal?.id).toBe("p-1"));
    expect(FakeEventSource.last().closed).toBe(false);
  });

  it("should load persisted events without a stream for a terminal run", async () => {
    const verified = { ...proposedDetail, run: makeRun({ status: "verified" }) };
    const { api, calls } = createFakeApi({ details: { "run-1": verified }, events: { "run-1": [...happyEvents, ...applyEvents] } });
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));

    await act(() => result.current.select("run-1"));
    await waitFor(() => expect(result.current.timeline.lastEventId).toBe(14));
    expect(calls.listEvents).toEqual(["run-1"]);
    expect(FakeEventSource.instances).toHaveLength(0);
    expect(result.current.phase).toBe("verified");
  });

  it("should close the stream when a terminal event arrives", async () => {
    const { api } = createFakeApi();
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));
    await act(() => result.current.select("run-1"));
    act(() => FakeEventSource.last().emitAll([...happyEvents, ...applyEvents]));
    await waitFor(() => expect(result.current.phase).toBe("verified"));
    expect(FakeEventSource.last().closed).toBe(true);
  });

  it("should apply the current proposal version and surface a 409 as an error without losing the run", async () => {
    const apply = vi.fn(async () => { throw new ApiError("stale_proposal", "The data changed", 409, { fingerprint_changed: true }); });
    const { api, calls } = createFakeApi({ apply });
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));
    await act(() => result.current.select("run-1"));
    await waitFor(() => expect(result.current.detail?.proposal?.id).toBe("p-1"));

    await act(() => result.current.apply());
    expect(calls.apply).toEqual([{ runId: "run-1", proposalId: "p-1", version: 1 }]);
    expect(result.current.error?.code).toBe("stale_proposal");
    expect(result.current.phase).toBe("proposed");
    act(() => result.current.clearError());
    expect(result.current.error).toBeNull();
  });

  it("should replace the stream when another run is selected", async () => {
    const { api } = createFakeApi({ details: { "run-9": { ...proposedDetail, run: makeRun({ id: "run-9", status: "analyzing" }) } } });
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));
    await act(() => result.current.select("run-1"));
    const first = FakeEventSource.last();
    await act(() => result.current.select("run-9"));
    expect(first.closed).toBe(true);
    expect(FakeEventSource.last().url).toBe("/api/runs/run-9/events");
    expect(result.current.timeline.steps).toEqual([]);
  });

  it("should mark the connection as reconnecting on a stream error and live again on the next event", async () => {
    const { api } = createFakeApi();
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));
    await act(() => result.current.select("run-1"));
    expect(result.current.connection).toBe("live");
    act(() => FakeEventSource.last().emitError());
    expect(result.current.connection).toBe("reconnecting");
    act(() => FakeEventSource.last().emit(happyEvents[0]));
    expect(result.current.connection).toBe("live");
  });

  it("should skip a malformed stream message, report it, and keep processing later events", async () => {
    const { api } = createFakeApi();
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));
    await act(() => result.current.select("run-1"));
    act(() => FakeEventSource.last().emitRaw("tool_started", "not json"));
    expect(result.current.error?.code).toBe("bad_event");
    act(() => FakeEventSource.last().emitAll(happyEvents.slice(0, 3)));
    expect(result.current.timeline.lastEventId).toBe(3);
  });

  it("should ignore a refresh response that is older than one that already landed", async () => {
    const { api } = createFakeApi();
    const resolvers: ((detail: typeof proposedDetail) => void)[] = [];
    const getRun = vi.fn(() => new Promise<typeof proposedDetail>((resolve) => { resolvers.push(resolve); }));
    const { result } = renderHook(() => useRun({ ...api, getRun }, fakeEventSourceFactory));
    const selecting = act(() => result.current.select("run-1"));
    await waitFor(() => expect(resolvers).toHaveLength(1));
    resolvers[0](proposedDetail);
    await selecting;
    act(() => FakeEventSource.last().emitAll(happyEvents.slice(6, 8)));
    await waitFor(() => expect(resolvers).toHaveLength(3));
    await act(async () => { resolvers[2]({ ...proposedDetail, run: makeRun({ status: "verified" }) }); });
    await act(async () => { resolvers[1](proposedDetail); });
    expect(result.current.detail?.run.status).toBe("verified");
  });

  it("should not clear a newer start when an older apply settles", async () => {
    let finishApply: () => void = () => undefined;
    let finishCreate: () => void = () => undefined;
    const apply = vi.fn(() => new Promise<never>((_, reject) => { finishApply = () => reject(new ApiError("stale_proposal", "stale", 409)); }));
    const { api } = createFakeApi({ apply });
    const createRun = vi.fn(() => new Promise<ReturnType<typeof makeRun>>((resolve) => { finishCreate = () => resolve(makeRun({ id: "run-2", status: "queued" })); }));
    const { result } = renderHook(() => useRun({ ...api, createRun }, fakeEventSourceFactory));
    await act(() => result.current.select("run-1"));
    await waitFor(() => expect(result.current.detail?.proposal?.id).toBe("p-1"));

    let applying: Promise<void> = Promise.resolve();
    act(() => { applying = result.current.apply(); });
    expect(result.current.busy).toBe("applying");
    let starting: Promise<unknown> = Promise.resolve();
    act(() => { starting = result.current.start({ case_ref: "m-sample-1", goal: "g", input: {} }); });
    expect(result.current.busy).toBe("starting");
    await act(async () => { finishApply(); await applying; });
    expect(result.current.busy).toBe("starting");
    await act(async () => { finishCreate(); await starting; });
    expect(result.current.busy).toBeNull();
    expect(result.current.detail?.run.id).toBe("run-2");
  });

  it("should expose a start error and stay idle when the backend rejects the request", async () => {
    const { api } = createFakeApi({ createRun: () => { throw new ApiError("case_not_found", "Unknown case", 404); } });
    const { result } = renderHook(() => useRun(api, fakeEventSourceFactory));
    await act(() => result.current.start({ case_ref: "nope", goal: "g", input: {} }));
    expect(result.current.error?.code).toBe("case_not_found");
    expect(result.current.phase).toBe("idle");
  });
});
