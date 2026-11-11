import type { IntervalUnit, Shift, ShiftDef } from "../types";

export const DAY_MS = 86_400_000;

export function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/** Local calendar date as YYYY-MM-DD. */
export function toDateKey(d: Date = new Date()): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

export function todayKey(): string {
  return toDateKey(new Date());
}

export function parseDateKey(key: string): Date {
  const [y, m, d] = key.slice(0, 10).split("-").map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

export function isoToDateKey(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? null : toDateKey(d);
}

export function addDays(key: string, days: number): string {
  const d = parseDateKey(key);
  d.setDate(d.getDate() + days);
  return toDateKey(d);
}

function clampDay(d: Date, day: number): void {
  const last = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
  d.setDate(Math.min(day, last));
}

export function addInterval(key: string, value: number, unit: IntervalUnit): string {
  const d = parseDateKey(key);
  const day = d.getDate();
  switch (unit) {
    case "day":
      d.setDate(d.getDate() + value);
      break;
    case "week":
      d.setDate(d.getDate() + value * 7);
      break;
    case "month":
      d.setDate(1);
      d.setMonth(d.getMonth() + value);
      clampDay(d, day);
      break;
    case "year":
      d.setDate(1);
      d.setFullYear(d.getFullYear() + value);
      clampDay(d, day);
      break;
  }
  return toDateKey(d);
}

/** Whole days from a to b (positive when b is later). */
export function daysBetween(a: string, b: string): number {
  return Math.round((parseDateKey(b).getTime() - parseDateKey(a).getTime()) / DAY_MS);
}

export function minutesBetween(startIso: string, endIso: string): number {
  return Math.max(0, Math.round((new Date(endIso).getTime() - new Date(startIso).getTime()) / 60_000));
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function formatDate(key: string | null | undefined): string {
  if (!key) return "—";
  const d = key.length > 10 ? new Date(key) : parseDateKey(key);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}, ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function formatMonth(key: string): string {
  const d = parseDateKey(key);
  return `${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function formatMinutes(min: number | null | undefined): string {
  if (min === null || min === undefined) return "—";
  const h = Math.floor(min / 60);
  const m = Math.round(min % 60);
  if (h === 0) return `${m}m`;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}

export function formatHours(hours: number | null | undefined, digits = 1): string {
  if (hours === null || hours === undefined || !Number.isFinite(hours)) return "—";
  return `${hours.toFixed(digits)} h`;
}

/** Value for an <input type="datetime-local"> from an ISO timestamp. */
export function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return `${toDateKey(d)}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function fromLocalInput(value: string): string | null {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function nowLocalInput(): string {
  return toLocalInput(new Date().toISOString());
}

/** Monday of the week containing the given date. */
export function weekStart(key: string): string {
  const d = parseDateKey(key);
  const day = (d.getDay() + 6) % 7; // Monday = 0
  d.setDate(d.getDate() - day);
  return toDateKey(d);
}

export function monthStart(key: string): string {
  return `${key.slice(0, 7)}-01`;
}

function minutesOfDay(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}

export function shiftHours(def: ShiftDef): number {
  const s = minutesOfDay(def.start);
  const e = minutesOfDay(def.end);
  const span = e > s ? e - s : 24 * 60 - s + e;
  return span / 60;
}

/** Which shift a moment falls in. Shifts may wrap past midnight (22:00 to 06:00). */
export function shiftForDate(d: Date, shifts: Record<Shift, ShiftDef>): Shift {
  const t = d.getHours() * 60 + d.getMinutes();
  for (const shift of ["A", "B", "C"] as Shift[]) {
    const def = shifts[shift];
    if (!def) continue;
    const s = minutesOfDay(def.start);
    const e = minutesOfDay(def.end);
    const inside = s < e ? t >= s && t < e : t >= s || t < e;
    if (inside) return shift;
  }
  return "A";
}

export function shiftForIso(iso: string, shifts: Record<Shift, ShiftDef>): Shift {
  return shiftForDate(new Date(iso), shifts);
}
