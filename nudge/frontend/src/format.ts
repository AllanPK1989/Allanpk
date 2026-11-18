// Friendly dates: "Today 11:00", "Tomorrow", "Mon 23 Nov", "2 days overdue".
import type { ShortTask } from "./api";

export function todayISO(): string {
  const d = new Date();
  return toISO(d);
}

export function toISO(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function addDays(iso: string, n: number): string {
  const [y, m, d] = iso.split("-").map(Number);
  return toISO(new Date(y, m - 1, d + n));
}

export function daysBetween(fromISO: string, toISOStr: string): number {
  const [y1, m1, d1] = fromISO.split("-").map(Number);
  const [y2, m2, d2] = toISOStr.split("-").map(Number);
  return Math.round((Date.UTC(y2, m2 - 1, d2) - Date.UTC(y1, m1 - 1, d1)) / 86400000);
}

export function dayLabel(iso: string, today = todayISO()): string {
  const diff = daysBetween(today, iso);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff === -1) return "Yesterday";
  const [y, m, d] = iso.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  const opts: Intl.DateTimeFormatOptions = diff > 1 && diff < 7
    ? { weekday: "long" }
    : { weekday: "short", day: "numeric", month: "short", ...(y !== new Date().getFullYear() ? { year: "numeric" } : {}) };
  return date.toLocaleDateString("en-IN", opts);
}

export function longDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });
}

export function shortDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function dueText(t: Pick<ShortTask, "due_date" | "due_time" | "overdue">, today = todayISO()): { text: string; tone: "over" | "today" | "" } {
  if (!t.due_date) return { text: "", tone: "" };
  const diff = daysBetween(today, t.due_date);
  if (t.overdue) {
    if (diff < 0) return { text: diff === -1 ? "Overdue since yesterday" : `${-diff} days overdue`, tone: "over" };
    return { text: `Overdue · was ${t.due_time}`, tone: "over" };
  }
  const label = dayLabel(t.due_date, today);
  const text = t.due_time ? `${label} ${t.due_time}` : label;
  return { text, tone: diff === 0 ? "today" : "" };
}

export function timeAgo(isoUtc: string): string {
  const s = (Date.now() - new Date(isoUtc).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  const d = Math.floor(s / 86400);
  return d === 1 ? "yesterday" : `${d} days ago`;
}

export function localDateTime(isoUtc: string): string {
  return new Date(isoUtc).toLocaleString("en-IN", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export function plural(n: number, word: string, many?: string): string {
  return `${n} ${n === 1 ? word : many ?? `${word}s`}`;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1][0] : "")).toUpperCase();
}
