import type { Asset, PMPlan, Snapshot, WorkOrder } from "../types";
import { addInterval, daysBetween, todayKey } from "./dates";
import { newId, nowIso } from "./ids";
import { allocateWoNo, isOpenStatus, newWorkOrder } from "./workorders";

export type PlanState = "inactive" | "overdue" | "due" | "upcoming" | "ok";
export const PLAN_STATE_LABEL: Record<PlanState, string> = {
  inactive: "Inactive",
  overdue: "Overdue",
  due: "Due",
  upcoming: "Upcoming",
  ok: "Scheduled",
};

export function usesTime(plan: PMPlan): boolean {
  return plan.trigger === "time" || plan.trigger === "both";
}

export function usesMeter(plan: PMPlan): boolean {
  return plan.trigger !== "time" && plan.meterInterval !== null && plan.meterInterval > 0;
}

/** Meter lead: the plan becomes due within the last 10% of its meter interval. */
export function meterLead(plan: PMPlan): number {
  return Math.max(1, Math.round((plan.meterInterval ?? 0) * 0.1));
}

export function planState(plan: PMPlan, asset: Asset | undefined, today: string = todayKey()): PlanState {
  if (!plan.active) return "inactive";
  let overdue = false;
  let due = false;
  let upcoming = false;
  if (usesTime(plan)) {
    const d = daysBetween(today, plan.nextDueAt); // > 0 means in the future
    if (d < 0) overdue = true;
    else if (d <= plan.leadDays) due = true;
    else if (d <= plan.leadDays + 14) upcoming = true;
  }
  if (usesMeter(plan) && asset && plan.nextDueMeter !== null) {
    const remaining = plan.nextDueMeter - asset.meterReading;
    if (remaining < 0) overdue = true;
    else if (remaining <= meterLead(plan)) due = true;
  }
  if (overdue) return "overdue";
  if (due) return "due";
  if (upcoming) return "upcoming";
  return "ok";
}

export function intervalLabel(plan: PMPlan): string {
  const parts: string[] = [];
  if (usesTime(plan)) {
    const unit = plan.intervalValue === 1 ? plan.intervalUnit : `${plan.intervalUnit}s`;
    parts.push(`every ${plan.intervalValue} ${unit}`);
  }
  if (usesMeter(plan)) parts.push(`every ${plan.meterInterval} meter units`);
  return parts.join(" / ") || "—";
}

export function hasOpenWorkOrder(workOrders: WorkOrder[], planId: string): WorkOrder | undefined {
  return workOrders.find((w) => w.pmPlanId === planId && isOpenStatus(w.status));
}

export function buildPmWorkOrder(draft: Snapshot, plan: PMPlan, asset: Asset, userId: string, today: string): WorkOrder {
  const now = nowIso();
  const woNo = allocateWoNo(draft, new Date().getFullYear());
  const due = usesTime(plan) ? plan.nextDueAt : today;
  const assigned = plan.assignedToUserId ? [plan.assignedToUserId] : [];
  const status = assigned.length > 0 ? "assigned" : "open";
  const wo = newWorkOrder(
    {
      woNo,
      type: "pm",
      title: `${plan.code} · ${plan.name}`,
      description: plan.description,
      assetId: asset.id,
      lineId: asset.lineId,
      priority: plan.priority,
      status,
      requestedByUserId: userId,
      assignedToUserIds: assigned,
      dueDate: due,
      scheduledDate: due,
      estimatedHours: plan.estimatedHours,
      checklist: plan.checklist.map((text) => ({ id: newId(), text, done: false, doneByUserId: null, doneAt: null })),
      pmPlanId: plan.id,
      history: [{ at: now, userId, from: null, to: status, note: `Generated from PM plan ${plan.code}` }],
    },
    now,
  );
  wo.id = newId();
  return wo;
}

/** Create work orders for every active plan that is due or overdue and has no open work order yet. */
export function generateDuePMs(draft: Snapshot, userId: string, today: string = todayKey()): WorkOrder[] {
  const created: WorkOrder[] = [];
  for (const plan of draft.pmPlans) {
    if (!plan.active) continue;
    const asset = draft.assets.find((a) => a.id === plan.assetId);
    if (!asset || !asset.active || asset.status === "retired") continue;
    const state = planState(plan, asset, today);
    if (state !== "due" && state !== "overdue") continue;
    if (hasOpenWorkOrder(draft.workOrders, plan.id)) continue;
    const wo = buildPmWorkOrder(draft, plan, asset, userId, today);
    draft.workOrders.push(wo);
    created.push(wo);
  }
  return created;
}

/** Roll a plan forward once its work order is completed. Mutates the plan. */
export function completePlanCycle(plan: PMPlan, completedKey: string, meterAtCompletion: number | null): void {
  plan.lastDoneAt = completedKey;
  if (usesTime(plan)) {
    let next =
      plan.scheduleMode === "fixed"
        ? addInterval(plan.nextDueAt, plan.intervalValue, plan.intervalUnit)
        : addInterval(completedKey, plan.intervalValue, plan.intervalUnit);
    // A fixed schedule that fell behind catches up to the first slot after the completion date.
    let guard = 0;
    while (plan.scheduleMode === "fixed" && daysBetween(completedKey, next) <= 0 && guard < 1000) {
      next = addInterval(next, plan.intervalValue, plan.intervalUnit);
      guard += 1;
    }
    plan.nextDueAt = next;
  }
  if (usesMeter(plan) && meterAtCompletion !== null) {
    plan.lastDoneMeter = meterAtCompletion;
    plan.nextDueMeter = meterAtCompletion + (plan.meterInterval ?? 0);
  }
}

export function plansDueBetween(plans: PMPlan[], from: string, to: string): PMPlan[] {
  return plans.filter((p) => p.active && usesTime(p) && p.nextDueAt >= from && p.nextDueAt <= to);
}
