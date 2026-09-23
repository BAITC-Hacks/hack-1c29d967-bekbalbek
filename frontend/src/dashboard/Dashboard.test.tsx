import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError } from "../api/client";
import { protokolDomain } from "../domain/protokol";
import { createFakeApi } from "../test/fakeApi";
import { FakeEventSource, fakeEventSourceFactory } from "../test/fakeEventSource";
import { caseView, examples, applyEvents, happyEvents, infeasibleDetail, makeRun, needsInputDetail } from "../test/fixtures";
import Dashboard from "./Dashboard";

afterEach(() => vi.unstubAllGlobals());

beforeEach(() => { FakeEventSource.reset(); window.location.hash = "#/app"; });

function renderDashboard(options: Parameters<typeof createFakeApi>[0] = {}) {
  const fake = createFakeApi(options);
  render(<Dashboard api={fake.api} eventSourceFactory={fakeEventSourceFactory} domain={protokolDomain} />);
  return fake;
}

describe("Dashboard", () => {
  it("should expose upload on the empty dashboard and refresh the new meeting without reloading", async () => {
    const user = userEvent.setup();
    const meetings = [] as typeof examples;
    const uploaded = { ...caseView, status: "uploaded" as const, meeting: { ...caseView.meeting, status: "uploaded" as const } };
    const fake = renderDashboard({ examples: meetings, runs: [], caseView: uploaded });
    vi.stubGlobal("fetch", vi.fn(async () => {
      meetings.push({ ...examples[0], id: "m-new", title: "Новая встреча", request: { ...examples[0].request, case_ref: "m-new" } });
      return new Response(JSON.stringify({ meeting: { ...uploaded.meeting, id: "m-new" } }), { status: 202 });
    }));
    await user.upload(screen.getByLabelText("Аудио или видео"), new File(["audio"], "new.mp3", { type: "audio/mpeg" }));
    // jsdom keeps the native file-input validity empty after userEvent.upload.
    fireEvent.submit(screen.getByRole("button", { name: "Загрузить" }).closest("form")!);
    expect(await screen.findByRole("button", { name: /Новая встреча/ })).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: "Транскрибировать" }));
    expect(fake.calls.request[0].path).toBe("/domain/meetings/m-new/transcribe");
  });
  it("should prevent protocol generation until the transcript is ready", async () => {
    const user = userEvent.setup();
    renderDashboard({ runs: [], caseView: { ...caseView, status: "uploaded", meeting: { ...caseView.meeting, status: "uploaded" } } });
    await user.click(await screen.findByText("Развитие химической промышленности и ТБ"));
    expect(await screen.findByRole("button", { name: /run analysis/i })).toBeDisabled();
  });
  it("should list examples and previous runs in the left panel", async () => {
    renderDashboard();
    expect(await screen.findByText("Развитие химической промышленности и ТБ")).toBeInTheDocument();
    expect(await screen.findByText(/Составь протокол совещания\./)).toBeInTheDocument();
  });

  it("should walk the happy path: start, watch tool calls, review the proposal on the table, apply, verify", async () => {
    const user = userEvent.setup();
    const fake = renderDashboard();
    await user.click(await screen.findByText("Развитие химической промышленности и ТБ"));
    await user.click(await screen.findByRole("button", { name: /run analysis/i }));
    expect(fake.calls.createRun[0].case_ref).toBe("m-sample-1");

    act(() => FakeEventSource.last().emitAll(happyEvents));
    expect(await screen.findByText("Чтение совещания")).toBeInTheDocument();
    expect(await screen.findByText(/Proposal ready · 3 action/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /apply proposal/i })).toBeDisabled());

    const table = await screen.findByRole("table");
    expect(within(table).getAllByText(/Айдос Б\./).length).toBeGreaterThan(0);
    await user.click(screen.getByLabelText(/reviewed the warning/i));
    await user.click(screen.getByRole("button", { name: /apply proposal/i }));
    expect(fake.calls.apply).toHaveLength(1);

    act(() => FakeEventSource.last().emitAll(applyEvents));
    expect(await screen.findByText(/applied and verified/i)).toBeInTheDocument();
    expect(await screen.findByText(/Before → after/i)).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "Скачать PDF" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Скачать DOCX" })).toBeInTheDocument();
  });

  it("should show the missing fields as a form and continue with the supplied values", async () => {
    const user = userEvent.setup();
    const fake = renderDashboard({ details: { "run-2": needsInputDetail }, events: { "run-2": [] } });
    await user.click(await screen.findByRole("button", { name: /Подготовь протокол оперативного совещания.*m-sample-2/ }));
    const input = await screen.findByLabelText("meeting_date");
    await user.type(input, "2026-09-23");
    await user.click(screen.getByRole("button", { name: /continue/i }));
    expect(fake.calls.createRun[0].input).toEqual({ meeting_date: "2026-09-23" });
  });

  it("should show blocking constraints for an infeasible run", async () => {
    const user = userEvent.setup();
    renderDashboard({ details: { "run-3": infeasibleDetail } });
    await user.click(await screen.findByText(/m-sample-3/));
    expect(await screen.findByText(/Сначала распознайте запись/)).toBeInTheDocument();
    expect(screen.getByText("transcript_ready")).toBeInTheDocument();
  });

  it("should explain a stale proposal rejection and offer to re-run", async () => {
    const user = userEvent.setup();
    const apply = vi.fn(async () => { throw new ApiError("stale_proposal", "The data changed", 409, { fingerprint_changed: true, validation: { errors: [] } }); });
    renderDashboard({ apply });
    await user.click(await screen.findByText(/Составь протокол совещания\./));
    await user.click(await screen.findByLabelText(/reviewed the warning/i));
    await user.click(screen.getByRole("button", { name: /apply proposal/i }));
    expect(await screen.findByText(/data changed/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /re-run analysis/i })).toBeInTheDocument();
  });

  it("should open an evidence drawer for a selected change", async () => {
    const user = userEvent.setup();
    renderDashboard();
    await user.click(await screen.findByText(/Составь протокол совещания\./));
    await user.click(await screen.findByText(/Гульнара С\. · 2026-09-30/));
    expect(await screen.findByText(/реплика №4/)).toBeInTheDocument();
  });

  it("should reset sample data from the top bar", async () => {
    const user = userEvent.setup();
    const fake = renderDashboard();
    await user.click(await screen.findByRole("button", { name: /reset sample data/i }));
    await waitFor(() => expect(fake.calls.reset).toBe(1));
  });

  it("should select the run from the url hash", async () => {
    window.location.hash = "#/app/run/run-3";
    renderDashboard({ details: { "run-3": { ...infeasibleDetail, run: makeRun({ id: "run-3", status: "infeasible", outcome: "infeasible" }) } } });
    expect(await screen.findByText(/Сначала распознайте запись/)).toBeInTheDocument();
  });
});
