import { caseView } from "../test/fixtures";
import { protocolDocxUrl, protocolPdfUrl, uploadMeeting } from "./api";

afterEach(() => vi.unstubAllGlobals());
describe("meeting upload API", () => {
  it("should send the original file as multipart without a JSON content-type", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ meeting: caseView.meeting }), { status: 202 }));
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["audio"], "meeting.mp3", { type: "audio/mpeg" });
    expect(await uploadMeeting(file, "Совещание", "2026-09-23")).toEqual(caseView.meeting);
    const [url, options] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/domain/meetings");
    expect(options.headers).toBeUndefined();
    expect((options.body as FormData).get("file")).toBe(file);
    expect((options.body as FormData).get("meeting_date")).toBe("2026-09-23");
  });
  it("should surface the server error envelope", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ error: { code: "too_large", message: "Файл слишком большой" } }), { status: 413 })));
    await expect(uploadMeeting(new File(["a"], "a.mp3"), "a", "2026-09-23")).rejects.toMatchObject({ code: "too_large", message: "Файл слишком большой" });
  });
  it("should surface FastAPI field validation failures", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: [{ loc: ["body", "meeting_date"], msg: "Invalid date" }] }), { status: 422 })));
    await expect(uploadMeeting(new File(["a"], "a.mp3"), "a", "bad")).rejects.toMatchObject({ message: "meeting_date: Invalid date" });
  });
  it("should create encoded URLs for both export formats", () => {
    expect(protocolPdfUrl("m/1")).toBe("/api/domain/meetings/m%2F1/protocol.pdf");
    expect(protocolDocxUrl("m-1")).toBe("/api/domain/meetings/m-1/protocol.docx");
  });
});
