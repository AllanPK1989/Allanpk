import type { Asset, Line, Part, PMPlan, Settings, StockTransaction, User, WOType, WorkOrder } from "../types";
import { addDays, addInterval, daysBetween, formatMonth, isoToDateKey, monthStart, shiftHours, todayKey, weekStart } from "./dates";
import { planState } from "./pm";
import { isDoneStatus, isOpenStatus, isOtherType } from "./workorders";

export interface Period {
  from: string; // inclusive date key
  to: string; // inclusive date key
}

export function lastNDays(n: number, today: string = todayKey()): Period {
  return { from: addDays(today, -(n - 1)), to: today };
}

export function periodDays(p: Period): number {
  return daysBetween(p.from, p.to) + 1;
}

function inPeriod(key: string | null, p: Period): boolean {
  return key !== null && key >= p.from && key <= p.to;
}

export function createdKey(wo: WorkOrder): string | null {
  return isoToDateKey(wo.createdAt);
}

export function completedKey(wo: WorkOrder): string | null {
  return isoToDateKey(wo.completedAt);
}

/** Breakdowns that started (machine stopped) in the period. */
export function breakdownsIn(wos: WorkOrder[], p: Period): WorkOrder[] {
  return wos.filter((w) => w.type === "breakdown" && w.status !== "cancelled" && inPeriod(isoToDateKey(w.downtimeStart ?? w.createdAt), p));
}

export function totalDowntimeMinutes(wos: WorkOrder[]): number {
  return wos.reduce((s, w) => s + (w.downtimeMinutes ?? 0), 0);
}

/** Mean time to repair, in hours, over breakdowns completed in the period. */
export function mttrHours(wos: WorkOrder[], p: Period): number | null {
  const done = wos.filter((w) => w.type === "breakdown" && isDoneStatus(w.status) && w.downtimeMinutes !== null && inPeriod(completedKey(w), p));
  if (done.length === 0) return null;
  return totalDowntimeMinutes(done) / 60 / done.length;
}

/** Mean time between failures, in operating hours. */
export function mtbfHours(wos: WorkOrder[], p: Period, plannedHoursPerDay: number): number | null {
  const failures = breakdownsIn(wos, p);
  if (failures.length === 0) return null;
  const planned = periodDays(p) * plannedHoursPerDay;
  const downtime = totalDowntimeMinutes(failures) / 60;
  return Math.max(0, planned - downtime) / failures.length;
}

export function availabilityPct(wos: WorkOrder[], p: Period, plannedHoursPerDay: number): number | null {
  const planned = periodDays(p) * plannedHoursPerDay;
  if (planned <= 0) return null;
  const downtime = totalDowntimeMinutes(breakdownsIn(wos, p)) / 60;
  return Math.max(0, Math.min(100, ((planned - downtime) / planned) * 100));
}

export interface AssetDowntime {
  assetId: string;
  label: string;
  minutes: number;
  count: number;
}

export function downtimeByAsset(wos: WorkOrder[], p: Period, assets: Asset[]): AssetDowntime[] {
  const byId = new Map<string, AssetDowntime>();
  for (const w of breakdownsIn(wos, p)) {
    if (!w.assetId) continue;
    const asset = assets.find((a) => a.id === w.assetId);
    const row = byId.get(w.assetId) ?? { assetId: w.assetId, label: asset ? `${asset.assetNo} ${asset.name}` : "Unknown asset", minutes: 0, count: 0 };
    row.minutes += w.downtimeMinutes ?? 0;
    row.count += 1;
    byId.set(w.assetId, row);
  }
  return [...byId.values()].sort((a, b) => b.minutes - a.minutes);
}

export interface WeekPoint {
  weekKey: string;
  label: string;
  created: number;
  completed: number;
}

export function weeklySeries(wos: WorkOrder[], weeks: number, today: string = todayKey()): WeekPoint[] {
  const start = weekStart(addDays(today, -(weeks - 1) * 7));
  const points: WeekPoint[] = [];
  for (let i = 0; i < weeks; i++) {
    const key = addDays(start, i * 7);
    const d = new Date(key);
    points.push({ weekKey: key, label: `${d.getDate()}/${d.getMonth() + 1}`, created: 0, completed: 0 });
  }
  const index = (key: string | null): WeekPoint | undefined => (key ? points.find((pt) => pt.weekKey === weekStart(key)) : undefined);
  for (const w of wos) {
    if (w.status === "cancelled") continue;
    const c = index(createdKey(w));
    if (c) c.created += 1;
    const done = index(completedKey(w));
    if (done && isDoneStatus(w.status)) done.completed += 1;
  }
  return points;
}

export interface PmCompliance {
  due: number;
  onTime: number;
  late: number;
  open: number;
  pct: number | null;
}

/** PM work orders due in the period: completed on or before the due date count as compliant. */
export function pmCompliance(wos: WorkOrder[], p: Period): PmCompliance {
  const due = wos.filter((w) => w.type === "pm" && w.status !== "cancelled" && inPeriod(w.dueDate, p));
  let onTime = 0;
  let late = 0;
  let open = 0;
  for (const w of due) {
    if (isDoneStatus(w.status)) {
      const done = completedKey(w);
      if (done && w.dueDate && done <= w.dueDate) onTime += 1;
      else late += 1;
    } else open += 1;
  }
  return { due: due.length, onTime, late, open, pct: due.length ? (onTime / due.length) * 100 : null };
}

export interface MonthPoint {
  monthKey: string;
  label: string;
  compliance: PmCompliance;
}

export function monthlyPmCompliance(wos: WorkOrder[], months: number, today: string = todayKey()): MonthPoint[] {
  const out: MonthPoint[] = [];
  const first = addInterval(monthStart(today), -(months - 1), "month");
  for (let i = 0; i < months; i++) {
    const from = addInterval(first, i, "month");
    const to = addDays(addInterval(from, 1, "month"), -1);
    out.push({ monthKey: from, label: formatMonth(from), compliance: pmCompliance(wos, { from, to }) });
  }
  return out;
}

export function lowStockParts(parts: Part[]): Part[] {
  return parts
    .filter((p) => p.active && p.minStock > 0 && p.stock <= p.minStock)
    .sort((a, b) => a.stock / Math.max(1, a.minStock) - b.stock / Math.max(1, b.minStock));
}

export function duePlans(plans: PMPlan[], assets: Asset[], today: string = todayKey()): PMPlan[] {
  return plans
    .filter((p) => {
      const s = planState(p, assets.find((a) => a.id === p.assetId), today);
      return s === "overdue" || s === "due";
    })
    .sort((a, b) => a.nextDueAt.localeCompare(b.nextDueAt));
}

export function openByType(wos: WorkOrder[]): { breakdown: number; pm: number; other: number } {
  const out = { breakdown: 0, pm: 0, other: 0 };
  for (const w of wos) {
    if (!isOpenStatus(w.status)) continue;
    if (w.type === "breakdown") out.breakdown += 1;
    else if (w.type === "pm") out.pm += 1;
    else out.other += 1;
  }
  return out;
}

export function hoursPerDayForLine(line: Line | undefined, settings: Settings): number {
  if (!line) return settings.plannedHoursPerDay;
  const total = line.shifts.reduce((s, sh) => s + shiftHours(settings.shifts[sh]), 0);
  return total > 0 ? total : settings.plannedHoursPerDay;
}

export interface AssetMetrics {
  breakdowns: number;
  downtimeMinutes: number;
  mttrHours: number | null;
  mtbfHours: number | null;
}

export function assetMetrics(wos: WorkOrder[], assetId: string, p: Period, hoursPerDay: number): AssetMetrics {
  const own = wos.filter((w) => w.assetId === assetId);
  const failures = breakdownsIn(own, p);
  const downtime = totalDowntimeMinutes(failures);
  return {
    breakdowns: failures.length,
    downtimeMinutes: downtime,
    mttrHours: mttrHours(own, p),
    mtbfHours: failures.length ? Math.max(0, periodDays(p) * hoursPerDay - downtime / 60) / failures.length : null,
  };
}

export interface TechnicianHours {
  userId: string;
  name: string;
  hours: number;
  workOrders: number;
}

export function technicianHours(wos: WorkOrder[], p: Period, users: User[]): TechnicianHours[] {
  const byUser = new Map<string, TechnicianHours>();
  for (const w of wos) {
    const touched = new Set<string>();
    for (const l of w.labor) {
      if (!inPeriod(l.date, p)) continue;
      const u = users.find((x) => x.id === l.userId);
      const row = byUser.get(l.userId) ?? { userId: l.userId, name: u?.name ?? "Unknown", hours: 0, workOrders: 0 };
      row.hours += l.hours;
      if (!touched.has(l.userId)) {
        row.workOrders += 1;
        touched.add(l.userId);
      }
      byUser.set(l.userId, row);
    }
  }
  return [...byUser.values()].sort((a, b) => b.hours - a.hours);
}

export interface PartConsumption {
  partId: string;
  label: string;
  qty: number;
  cost: number;
}

export function partsConsumption(txs: StockTransaction[], p: Period, parts: Part[]): PartConsumption[] {
  const byPart = new Map<string, PartConsumption>();
  for (const t of txs) {
    if (t.type !== "issue" && t.type !== "return") continue;
    if (!inPeriod(isoToDateKey(t.at), p)) continue;
    const part = parts.find((x) => x.id === t.partId);
    const row = byPart.get(t.partId) ?? { partId: t.partId, label: part ? `${part.partNo} ${part.name}` : "Unknown part", qty: 0, cost: 0 };
    row.qty += -t.qty; // issues are negative stock changes
    row.cost += -t.qty * t.unitCost;
    byPart.set(t.partId, row);
  }
  return [...byPart.values()].filter((r) => r.qty !== 0).sort((a, b) => b.cost - a.cost);
}

export interface TypeSummary {
  type: WOType | "other";
  created: number;
  completed: number;
  open: number;
}

export function summaryByType(wos: WorkOrder[], p: Period): TypeSummary[] {
  const rows = new Map<string, TypeSummary>();
  const get = (t: WOType): TypeSummary => {
    const key = isOtherType(t) ? t : t;
    const row = rows.get(key) ?? { type: t, created: 0, completed: 0, open: 0 };
    rows.set(key, row);
    return row;
  };
  for (const w of wos) {
    if (w.status === "cancelled") continue;
    if (inPeriod(createdKey(w), p)) get(w.type).created += 1;
    if (isDoneStatus(w.status) && inPeriod(completedKey(w), p)) get(w.type).completed += 1;
    if (isOpenStatus(w.status)) get(w.type).open += 1;
  }
  return [...rows.values()];
}
