import { ApiError, type Api } from "../api/client";
import type { ApiErrorBody, Meeting, MeetingDetail, MeetingSpeaker } from "../api/types";

type RequestApi = Pick<Api, "request">;
const meetingPath = (id: string) => `/domain/meetings/${encodeURIComponent(id)}`;

export async function uploadMeeting(file: File, title: string, meetingDate: string, base = "/api"): Promise<Meeting> {
  const body = new FormData();
  body.append("file", file);
  body.append("title", title);
  body.append("meeting_date", meetingDate);
  let response: Response;
  try { response = await fetch(`${base}/domain/meetings`, { method: "POST", body }); }
  catch (cause) { throw new ApiError("network_error", "Не удалось связаться с сервером. Проверьте подключение.", 0, cause); }
  const data = await response.json().catch(() => null) as
    (Partial<ApiErrorBody> & { meeting?: Meeting; detail?: unknown }) | null;
  if (!response.ok) {
    if (data?.error?.code) throw new ApiError(data.error.code, data.error.message, response.status, data.error.details);
    if (Array.isArray(data?.detail)) {
      const details = data.detail as { loc: (string | number)[]; msg: string }[];
      throw new ApiError("validation_error", details.map((item) => `${item.loc.filter((part) => part !== "body").join(".")}: ${item.msg}`).join("; "), response.status, details);
    }
    throw new ApiError("http_error", typeof data?.detail === "string" ? data.detail : `Ошибка загрузки (HTTP ${response.status})`, response.status, data);
  }
  if (!data?.meeting?.id) throw new ApiError("bad_response", "Сервер не вернул загруженную запись", response.status);
  return data.meeting;
}
export const startTranscription = (api: RequestApi, id: string) =>
  api.request<{ meeting_id: string; status: "transcribing" }>(`${meetingPath(id)}/transcribe`, { method: "POST" });
export const getMeeting = (api: RequestApi, id: string, signal?: AbortSignal) =>
  api.request<MeetingDetail>(meetingPath(id), { signal });
export const renameSpeaker = (api: RequestApi, id: string, speakerId: string, displayName: string) =>
  api.request<{ speaker: MeetingSpeaker }>(`${meetingPath(id)}/speakers/${encodeURIComponent(speakerId)}`, {
    method: "PATCH", body: JSON.stringify({ display_name: displayName }),
  });
export const protocolPdfUrl = (id: string) => `/api${meetingPath(id)}/protocol.pdf`;
export const protocolDocxUrl = (id: string) => `/api${meetingPath(id)}/protocol.docx`;
