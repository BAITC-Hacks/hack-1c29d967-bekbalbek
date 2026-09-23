import type { ActionItem } from "../api/types";
export type ItemStatus = "new" | "in_progress" | "done";
export const localDate = (date = new Date()): string =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
export function readItemStatus(item: ActionItem): ItemStatus {
  try {
    const saved = localStorage.getItem(`protokol.status.${item.id}`);
    if (saved === "new" || saved === "in_progress" || saved === "done") return saved;
  } catch { /* Use the server status when browser storage is unavailable. */ }
  return item.status === "done" || item.status === "in_progress" ? item.status : "new";
}
export const statusFor = (item: Pick<ActionItem, "deadline_date">, status: ItemStatus, today: string): ItemStatus | "overdue" =>
  status !== "done" && item.deadline_date && item.deadline_date < today ? "overdue" : status;
