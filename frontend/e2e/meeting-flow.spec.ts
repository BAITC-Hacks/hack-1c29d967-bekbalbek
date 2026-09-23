import { expect, test, type Page } from "@playwright/test";
import { caseView, confirmedCaseView, examples, happyEvents, makeRun, proposedDetail } from "../src/test/fixtures";

// Browser contract tests use simulated HTTP responses. They do not run speech models.
async function installMeetingApi(page: Page) {
  const view = structuredClone(caseView);
  view.meeting.status = "uploaded"; view.status = "uploaded";
  view.speakers = []; view.segments = [];
  const meetings: typeof examples = [];
  let detail = structuredClone(proposedDetail);
  let runs: ReturnType<typeof makeRun>[] = [];
  let transcribing = false;
  let uploadedMultipart = false;
  const externalRequests: string[] = [];
  page.on("request", (request) => { if (!/^https?:\/\/(localhost|127\.0\.0\.1)(:|\/)/.test(request.url())) externalRequests.push(request.url()); });
  await page.context().route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (!path.startsWith("/api/")) return route.continue();
    const send = (data: unknown, status = 200) => route.fulfill({ status, json: data });
    if (path === "/api/health") return send({ status: "ok", database: "ok", model: "scripted:auto", api_key_configured: false, domain: { key: "protokol", title: "Протокол" }, active_runs: 0, version: "test", provenance: { enabled: true, blocked_external_connections: 0 }, models_present: true, stt_device: "cuda", llm_endpoint: "http://localhost:11434/v1" });
    if (path === "/api/domain/examples") return send({ examples: meetings });
    if (path === "/api/domain/meetings" && request.method() === "POST") {
      uploadedMultipart = request.headers()["content-type"].startsWith("multipart/form-data; boundary=") && (request.postDataBuffer()?.includes(Buffer.from("meeting.mp3")) ?? false);
      meetings.push(examples[0]);
      return send({ meeting: view.meeting }, 202);
    }
    if (path.endsWith("/transcribe")) { transcribing = true; view.meeting.status = "transcribing"; view.status = "transcribing"; return send({ meeting_id: view.case_ref, status: "transcribing" }, 202); }
    if (path.includes("/speakers/")) {
      const speakerId = path.split("/").at(-1);
      const speaker = view.speakers.find((item) => item.speaker_id === speakerId)!;
      speaker.display_name = request.postDataJSON().display_name;
      return send({ speaker });
    }
    if (path.startsWith("/api/domain/cases/")) return send(view);
    if (/\/domain\/meetings\/[^/]+$/.test(path)) {
      if (transcribing) { Object.assign(view, structuredClone(caseView)); transcribing = false; }
      return send(view);
    }
    if (/\/protocol\.(pdf|docx)$/.test(path)) return route.fulfill({ body: "contract test export", headers: { "content-disposition": "attachment; filename=protocol-test.pdf", "content-type": "application/octet-stream" } });
    if (path.endsWith("/apply")) {
      Object.assign(view, structuredClone(confirmedCaseView));
      const run = { ...detail.run, status: "verified" as const };
      const application = { id: "app-1", proposal_id: "p-1", version: 1, status: "verified" as const, actions: [], verification: { ok: true, summary: "Поручения сохранены", checks: [] }, error: null, started_at: "t", finished_at: "t" };
      detail = { ...detail, run, application, snapshot_after: { action_items: 3, protocol_exists: true } };
      runs = [run];
      return send({ run, application });
    }
    if (path === "/api/runs") {
      if (request.method() === "POST") {
        detail = { ...detail, run: makeRun({ ...request.postDataJSON(), status: "proposed" }) };
        runs = [detail.run];
        return send({ run: { ...detail.run, status: "queued" } }, 202);
      }
      return send({ runs });
    }
    if (path.endsWith("/events/list")) return send({ events: happyEvents });
    if (path.endsWith("/events")) return route.fulfill({ headers: { "content-type": "text/event-stream" }, body: happyEvents.map((event) => `id: ${event.id}\nevent: ${event.type}\ndata: ${JSON.stringify(event)}\n\n`).join("") });
    if (path === "/api/runs/run-1") return send(detail);
    return send({ error: { code: "unhandled_test_route", message: path } }, 404);
  });
  return { externalRequests, multipartReceived: () => uploadedMultipart };
}

test("should complete upload, transcription, review, confirmation and export links against the HTTP contract", async ({ page }) => {
  const api = await installMeetingApi(page);
  const errors: string[] = []; page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/#/app");
  await page.getByLabel("Аудио или видео").setInputFiles({ name: "meeting.mp3", mimeType: "audio/mpeg", buffer: Buffer.from("test recording bytes") });
  await page.getByRole("button", { name: "Загрузить", exact: true }).click();
  await expect(page.getByRole("button", { name: "Транскрибировать", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Сформировать протокол", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Транскрибировать", exact: true }).click();
  await expect(page.getByText("стенограмма готова", { exact: true })).toBeVisible();
  await page.getByText("Говорящие · 3").click();
  await page.getByLabel("Имя S1", { exact: true }).fill("Асхат Ерланович");
  await page.getByLabel("Имя S1", { exact: true }).press("Enter");
  await expect(page.getByLabel("Имя S1", { exact: true })).toHaveValue("Асхат Ерланович");
  await page.getByLabel("Дата для расчёта сроков", { exact: true }).fill("2026-09-25");
  await page.getByRole("textbox", { name: "Задача для анализа", exact: true }).fill("Проверь сроки и решения");
  await page.getByRole("button", { name: "Сформировать протокол", exact: true }).click();
  await expect(page.getByRole("button", { name: "Подтвердить протокол", exact: true })).toBeDisabled();
  await expect(page.getByRole("heading", { level: 1, name: examples[0].title })).toBeVisible();
  await expect(page.getByText("Другие запуски", { exact: true })).toHaveCount(0);
  const decisions = page.getByRole("region", { name: "Решения совещания" });
  await expect(decisions.getByRole("listitem")).toHaveCount(proposedDetail.proposal!.content.decisions.length);
  for (const decision of proposedDetail.proposal!.content.decisions) await expect(decisions.getByText(decision, { exact: true })).toBeVisible();
  await page.screenshot({ path: "test-results/meeting-proposed.png", fullPage: true });
  await page.getByRole("button", { name: /Гульнара С\. · 2026-09-30/ }).click();
  await expect(page.getByRole("region", { name: "Цитаты" }).getByText(caseView.segments[3].text)).toBeVisible();
  await expect(page.getByTestId("row-104")).toHaveClass(/sel/);
  await page.getByLabel("Я проверил предупреждения").check();
  await page.getByRole("button", { name: "Подтвердить протокол", exact: true }).click();
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Скачать DOCX" })).toBeVisible();
  await page.getByLabel("Статус поручения 1", { exact: true }).selectOption("done");
  await expect(page.getByLabel("Статус поручения 1", { exact: true })).toHaveValue("done");
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute("href", "/api/domain/meetings/m-sample-1/protocol.pdf");
  await expect(page.getByRole("link", { name: "Скачать DOCX" })).toHaveAttribute("href", "/api/domain/meetings/m-sample-1/protocol.docx");
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute("download", "");
  await page.screenshot({ path: "test-results/meeting-confirmed.png", fullPage: true });
  expect(api.multipartReceived()).toBe(true);
  expect(api.externalRequests).toEqual([]);
  expect(errors).toEqual([]);
});

test("should keep upload and agent controls accessible on a narrow screen without external requests", async ({ page }) => {
  const api = await installMeetingApi(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/#/app");
  await expect(page.getByRole("button", { name: "Загрузить", exact: true })).toBeVisible();
  await expect(page.getByRole("complementary", { name: "Агент", exact: true })).toBeVisible();
  const width = await page.evaluate(() => ({ content: document.documentElement.scrollWidth, viewport: innerWidth }));
  expect(width.content).toBeLessThanOrEqual(width.viewport);
  await page.screenshot({ path: "test-results/meeting-mobile.png", fullPage: true });
  expect(api.externalRequests).toEqual([]);
});
