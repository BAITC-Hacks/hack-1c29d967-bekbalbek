import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { MeetingDetail } from "../api/types";
import { createFakeApi } from "../test/fakeApi";
import { caseView, confirmedCaseView } from "../test/fixtures";
import { MeetingPanel } from "./MeetingPanel";

beforeEach(() => { localStorage.clear(); window.location.hash = "#/app"; });
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); });
describe("MeetingPanel", () => {
  it("should offer upload with no selected meeting", () => {
    const { api } = createFakeApi();
    render(<MeetingPanel api={api} caseView={null} onChanged={vi.fn()} />);
    expect(screen.getByLabelText("Аудио или видео")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Загрузить" })).toBeDisabled();
  });
  it("should offer transcription for an uploaded meeting and stop polling after unmount", async () => {
    vi.useFakeTimers();
    const uploaded = { ...caseView, status: "uploaded" as const, meeting: { ...caseView.meeting, status: "uploaded" as const } };
    const { api, calls } = createFakeApi({ caseView: uploaded });
    const changed = vi.fn();
    const { unmount } = render(<MeetingPanel api={api} caseView={uploaded} onChanged={changed} />);
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Транскрибировать" })); });
    expect(screen.getByRole("button", { name: "Распознаётся…" })).toBeDisabled();
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(calls.request.map((call) => call.path)).toEqual(["/domain/meetings/m-sample-1/transcribe", "/domain/meetings/m-sample-1"]);
    unmount();
    await act(async () => { await vi.advanceTimersByTimeAsync(5000); });
    expect(calls.request).toHaveLength(2);
  });
  it("should finish polling and refresh when the transcript becomes ready", async () => {
    vi.useFakeTimers();
    const { api } = createFakeApi();
    const request = vi.fn(async () => caseView);
    const changed = vi.fn();
    const transcribing = { ...caseView, status: "transcribing" as const, meeting: { ...caseView.meeting, status: "transcribing" as const } };
    render(<MeetingPanel api={{ ...api, request: async <T,>() => await request() as T }} caseView={transcribing} onChanged={changed} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(screen.getByText("стенограмма готова")).toBeInTheDocument();
    expect(changed).toHaveBeenCalledTimes(1);
    await act(async () => { await vi.advanceTimersByTimeAsync(6000); });
    expect(request).toHaveBeenCalledTimes(1);
  });
  it("should display transcription failures returned by polling", async () => {
    vi.useFakeTimers();
    const failed: MeetingDetail = { ...caseView, meeting: { ...caseView.meeting, status: "failed", error: "Модель не установлена" } };
    const { api } = createFakeApi();
    const transcribing = { ...caseView, meeting: { ...caseView.meeting, status: "transcribing" as const } };
    render(<MeetingPanel api={{ ...api, request: async <T,>() => failed as T }} caseView={transcribing} onChanged={vi.fn()} />);
    await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
    expect(screen.getByRole("alert")).toHaveTextContent("Модель не установлена");
    expect(screen.getByRole("button", { name: "Транскрибировать" })).toBeEnabled();
  });
  it("should upload and navigate to the new meeting and refresh the list", async () => {
    const user = userEvent.setup();
    const { api } = createFakeApi();
    const changed = vi.fn();
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ meeting: { ...caseView.meeting, id: "m-new" } }), { status: 202 })));
    render(<MeetingPanel api={api} caseView={null} onChanged={changed} />);
    await user.upload(screen.getByLabelText("Аудио или видео"), new File(["audio"], "recording.mp3", { type: "audio/mpeg" }));
    // jsdom keeps the native file-input validity empty after userEvent.upload.
    fireEvent.submit(screen.getByRole("button", { name: "Загрузить" }).closest("form")!);
    await waitFor(() => expect(changed).toHaveBeenCalledTimes(1));
    expect(window.location.hash).toBe("#/app/example/m-new");
  });
  it("should save speaker names once when Enter is followed by blur", async () => {
    const user = userEvent.setup();
    const { api, calls } = createFakeApi();
    render(<MeetingPanel api={api} caseView={caseView} onChanged={vi.fn()} />);
    await user.click(screen.getByText("Говорящие · 3"));
    const input = screen.getByLabelText("Имя S1");
    await user.clear(input); await user.type(input, "Асхат{Enter}"); await user.tab();
    expect(calls.request.filter((call) => call.init?.method === "PATCH")).toHaveLength(1);
    expect(JSON.parse(String(calls.request[0].init?.body))).toEqual({ display_name: "Асхат" });
  });
  it("should show exports after confirmation and retain the named assignee instead of the giver", () => {
    const { api } = createFakeApi();
    render(<MeetingPanel api={api} caseView={{ ...confirmedCaseView, action_items: [{ ...confirmedCaseView.action_items[0], owner_name: "Ерлан", owner_speaker_id: "S1" }] }} onChanged={vi.fn()} />);
    expect(screen.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute("href", "/api/domain/meetings/m-sample-1/protocol.pdf");
    expect(screen.getByRole("link", { name: "Скачать DOCX" })).toHaveAttribute("href", "/api/domain/meetings/m-sample-1/protocol.docx");
    expect(within(screen.getByRole("table")).getByText("Ерлан")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Транскрибировать" })).not.toBeInTheDocument();
  });
  it("should mark past deadlines overdue and persist completion locally", async () => {
    const user = userEvent.setup();
    const { api } = createFakeApi();
    const view = { ...confirmedCaseView, action_items: [{ ...confirmedCaseView.action_items[0], deadline_date: "2000-01-01" }] };
    const { unmount } = render(<MeetingPanel api={api} caseView={view} onChanged={vi.fn()} />);
    expect(screen.getByText("просрочено")).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Статус поручения 1"), "done");
    expect(screen.queryByText("просрочено")).not.toBeInTheDocument();
    expect(localStorage.getItem("protokol.status.ai-1")).toBe("done");
    unmount(); render(<MeetingPanel api={api} caseView={view} onChanged={vi.fn()} />);
    expect(screen.getByLabelText("Статус поручения 1")).toHaveValue("done");
  });
});
