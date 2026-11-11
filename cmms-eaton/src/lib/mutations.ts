/** State changes applied to a Snapshot draft. Pure functions so they can be unit tested. */
import type { LaborEntry, Snapshot, StockTxType, WOStatus, WorkOrder } from "../types";
import { isoToDateKey, minutesBetween, shiftForIso, todayKey } from "./dates";
import { newId, nowIso } from "./ids";
import { completePlanCycle, usesMeter } from "./pm";
import { allocateWoNo, isOpenStatus, newWorkOrder, priorityForBreakdown, type NewWorkOrderInput } from "./workorders";

export function findWo(draft: Snapshot, id: string): WorkOrder {
  const wo = draft.workOrders.find((w) => w.id === id);
  if (!wo) throw new Error("Work order not found");
  return wo;
}

export function refreshAssetStatus(draft: Snapshot, assetId: string | null): void {
  if (!assetId) return;
  const asset = draft.assets.find((a) => a.id === assetId);
  if (!asset || asset.status === "retired") return;
  const openBreakdown = draft.workOrders.some((w) => w.assetId === assetId && w.type === "breakdown" && isOpenStatus(w.status));
  const underMaintenance = draft.workOrders.some((w) => w.assetId === assetId && w.type !== "breakdown" && w.status === "in_progress");
  asset.status = openBreakdown ? "down" : underMaintenance ? "maintenance" : "running";
}

export function createWorkOrder(draft: Snapshot, input: Omit<NewWorkOrderInput, "woNo" | "requestedByUserId">, userId: string): WorkOrder {
  const now = nowIso();
  const asset = input.assetId ? draft.assets.find((a) => a.id === input.assetId) : undefined;
  const lineId = input.lineId ?? asset?.lineId ?? null;
  let priority = input.priority;
  if (!priority) priority = input.type === "breakdown" && asset ? priorityForBreakdown(asset.criticality) : "medium";
  const downtimeStart = input.type === "breakdown" ? (input.downtimeStart ?? now) : null;
  const wo = newWorkOrder(
    {
      ...input,
      woNo: allocateWoNo(draft),
      requestedByUserId: userId,
      lineId,
      priority,
      downtimeStart,
      shift: downtimeStart ? shiftForIso(downtimeStart, draft.settings.shifts) : null,
    },
    now,
  );
  wo.id = newId();
  draft.workOrders.push(wo);
  if (wo.type === "breakdown") refreshAssetStatus(draft, wo.assetId);
  return wo;
}

export function changeStatus(draft: Snapshot, woId: string, to: WOStatus, userId: string, note = ""): void {
  const wo = findWo(draft, woId);
  const now = nowIso();
  const from = wo.status;
  wo.status = to;
  wo.history.push({ at: now, userId, from, to, note });
  wo.updatedAt = now;
  if (to === "in_progress") {
    if (!wo.startedAt) wo.startedAt = now;
    if (wo.assignedToUserIds.length === 0) wo.assignedToUserIds = [userId];
    if (from === "completed") {
      wo.completedAt = null;
      wo.closedAt = null;
      wo.closedByUserId = null;
    }
  }
  if (to === "open") wo.assignedToUserIds = [];
  if (to === "closed") {
    wo.closedAt = now;
    wo.closedByUserId = userId;
  }
  refreshAssetStatus(draft, wo.assetId);
}

export interface CompletionInput {
  rootCause: string;
  actionTaken: string;
  failureCode: string;
  downtimeEnd: string | null;
  meterReading: number | null;
  laborHours: number;
}

export function completeWorkOrder(draft: Snapshot, woId: string, input: CompletionInput, userId: string): void {
  const wo = findWo(draft, woId);
  const now = nowIso();
  wo.rootCause = input.rootCause;
  wo.actionTaken = input.actionTaken;
  wo.failureCode = input.failureCode;
  if (wo.type === "breakdown") {
    wo.downtimeEnd = input.downtimeEnd ?? now;
    if (wo.downtimeStart) wo.downtimeMinutes = minutesBetween(wo.downtimeStart, wo.downtimeEnd);
  }
  const asset = wo.assetId ? draft.assets.find((a) => a.id === wo.assetId) : undefined;
  if (input.meterReading !== null && asset) {
    asset.meterReading = input.meterReading;
    asset.meterUpdatedAt = now;
    wo.meterAtCompletion = input.meterReading;
  }
  if (input.laborHours > 0) {
    wo.labor.push({ id: newId(), userId, date: todayKey(), hours: input.laborHours, note: "" });
  }
  wo.completedAt = now;
  changeStatus(draft, woId, "completed", userId);
  if (wo.pmPlanId) {
    const plan = draft.pmPlans.find((p) => p.id === wo.pmPlanId);
    if (plan) {
      const meter = usesMeter(plan) ? (wo.meterAtCompletion ?? asset?.meterReading ?? null) : null;
      completePlanCycle(plan, isoToDateKey(now) ?? todayKey(), meter);
      plan.updatedAt = now;
    }
  }
}

export function assignWorkOrder(draft: Snapshot, woId: string, userIds: string[], userId: string): void {
  const wo = findWo(draft, woId);
  wo.assignedToUserIds = userIds;
  wo.updatedAt = nowIso();
  if (wo.status === "open" && userIds.length > 0) changeStatus(draft, woId, "assigned", userId, "Assigned");
  else if (wo.status === "assigned" && userIds.length === 0) changeStatus(draft, woId, "open", userId, "Unassigned");
}

export function addComment(draft: Snapshot, woId: string, userId: string, text: string): void {
  const wo = findWo(draft, woId);
  wo.comments.push({ id: newId(), userId, text, at: nowIso() });
  wo.updatedAt = nowIso();
}

export function addLabor(draft: Snapshot, woId: string, entry: Omit<LaborEntry, "id">): void {
  const wo = findWo(draft, woId);
  wo.labor.push({ id: newId(), ...entry });
  wo.updatedAt = nowIso();
}

export function removeLabor(draft: Snapshot, woId: string, laborId: string): void {
  const wo = findWo(draft, woId);
  wo.labor = wo.labor.filter((l) => l.id !== laborId);
  wo.updatedAt = nowIso();
}

export function toggleChecklist(draft: Snapshot, woId: string, itemId: string, userId: string): void {
  const wo = findWo(draft, woId);
  const item = wo.checklist.find((c) => c.id === itemId);
  if (!item) return;
  item.done = !item.done;
  item.doneByUserId = item.done ? userId : null;
  item.doneAt = item.done ? nowIso() : null;
  wo.updatedAt = nowIso();
}

export function setHandback(draft: Snapshot, woId: string, userId: string): void {
  const wo = findWo(draft, woId);
  wo.handbackByUserId = userId;
  wo.handbackAt = nowIso();
  wo.updatedAt = wo.handbackAt;
}

/** Issue a part from stock to a work order, or return it. Returns an error message or null. */
export function movePart(draft: Snapshot, woId: string, partId: string, qty: number, userId: string, direction: "issue" | "return"): string | null {
  if (!(qty > 0)) return "Quantity must be more than zero";
  const wo = findWo(draft, woId);
  const part = draft.parts.find((p) => p.id === partId);
  if (!part) return "Part not found";
  const now = nowIso();
  const used = wo.partsUsed.find((p) => p.partId === partId);
  if (direction === "issue") {
    if (part.stock < qty) return `Only ${part.stock} ${part.unit} in stock`;
    part.stock -= qty;
    if (used) used.qty += qty;
    else wo.partsUsed.push({ id: newId(), partId, qty, unitCost: part.unitCost });
    draft.stockTransactions.push({ id: newId(), partId, type: "issue", qty: -qty, unitCost: part.unitCost, workOrderId: woId, userId, at: now, note: `Issued to ${wo.woNo}` });
  } else {
    if (!used || used.qty < qty) return "Cannot return more than was issued";
    part.stock += qty;
    used.qty -= qty;
    if (used.qty === 0) wo.partsUsed = wo.partsUsed.filter((p) => p.id !== used.id);
    draft.stockTransactions.push({ id: newId(), partId, type: "return", qty, unitCost: used.unitCost, workOrderId: woId, userId, at: now, note: `Returned from ${wo.woNo}` });
  }
  part.updatedAt = now;
  wo.updatedAt = now;
  return null;
}

/** Receive or adjust stock outside a work order. Returns an error message or null. */
export function adjustStock(draft: Snapshot, partId: string, type: Exclude<StockTxType, "issue" | "return">, qty: number, unitCost: number | null, userId: string, note: string): string | null {
  const part = draft.parts.find((p) => p.id === partId);
  if (!part) return "Part not found";
  if (type === "receive" && !(qty > 0)) return "Quantity must be more than zero";
  if (part.stock + qty < 0) return "Stock cannot go below zero";
  const now = nowIso();
  part.stock += qty;
  if (type === "receive" && unitCost !== null && unitCost >= 0) part.unitCost = unitCost;
  part.updatedAt = now;
  draft.stockTransactions.push({ id: newId(), partId, type, qty, unitCost: unitCost ?? part.unitCost, workOrderId: null, userId, at: now, note });
  return null;
}
