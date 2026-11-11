import type { Criticality, Priority, Snapshot, WOStatus, WOType, WorkOrder } from "../types";

export const WO_TYPES: { value: WOType; label: string }[] = [
  { value: "breakdown", label: "Breakdown" },
  { value: "pm", label: "Preventive maintenance" },
  { value: "corrective", label: "Corrective" },
  { value: "improvement", label: "Improvement" },
  { value: "safety", label: "Safety" },
  { value: "inspection", label: "Inspection" },
  { value: "project", label: "Project" },
  { value: "other", label: "Other" },
];

export const WO_TYPE_LABEL = Object.fromEntries(WO_TYPES.map((t) => [t.value, t.label])) as Record<WOType, string>;

export const WO_STATUSES: WOStatus[] = ["open", "assigned", "in_progress", "on_hold", "completed", "closed", "cancelled"];
export const WO_STATUS_LABEL: Record<WOStatus, string> = {
  open: "Open",
  assigned: "Assigned",
  in_progress: "In progress",
  on_hold: "On hold",
  completed: "Completed",
  closed: "Closed",
  cancelled: "Cancelled",
};

export const PRIORITIES: Priority[] = ["critical", "high", "medium", "low"];
export const PRIORITY_LABEL: Record<Priority, string> = { critical: "Critical", high: "High", medium: "Medium", low: "Low" };
export const PRIORITY_RANK: Record<Priority, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function isOpenStatus(status: WOStatus): boolean {
  return status !== "completed" && status !== "closed" && status !== "cancelled";
}

export function isDoneStatus(status: WOStatus): boolean {
  return status === "completed" || status === "closed";
}

export function isOtherType(type: WOType): boolean {
  return type !== "breakdown" && type !== "pm";
}

export function allocateWoNo(draft: Snapshot, year: number = new Date().getFullYear()): string {
  draft.sequences.wo += 1;
  return `${draft.settings.woPrefix}-${year}-${String(draft.sequences.wo).padStart(5, "0")}`;
}

export function priorityForBreakdown(criticality: Criticality): Priority {
  return criticality === "A" ? "critical" : criticality === "B" ? "high" : "medium";
}

export function priorityForCriticality(criticality: Criticality): Priority {
  return criticality === "A" ? "high" : criticality === "B" ? "medium" : "low";
}

/** Status changes a work order may take next. */
export function allowedTransitions(status: WOStatus): WOStatus[] {
  switch (status) {
    case "open":
      return ["assigned", "in_progress", "cancelled"];
    case "assigned":
      return ["in_progress", "open", "cancelled"];
    case "in_progress":
      return ["on_hold", "completed", "cancelled"];
    case "on_hold":
      return ["in_progress", "cancelled"];
    case "completed":
      return ["closed", "in_progress"];
    case "closed":
      return [];
    case "cancelled":
      return ["open"];
  }
}

export function partsCost(wo: WorkOrder): number {
  return wo.partsUsed.reduce((sum, p) => sum + p.qty * p.unitCost, 0);
}

export function laborHours(wo: WorkOrder): number {
  return wo.labor.reduce((sum, l) => sum + l.hours, 0);
}

export function isOverdue(wo: WorkOrder, today: string): boolean {
  return isOpenStatus(wo.status) && wo.dueDate !== null && wo.dueDate < today;
}

export interface NewWorkOrderInput {
  woNo: string;
  type: WOType;
  title: string;
  requestedByUserId: string;
  assetId?: string | null;
  lineId?: string | null;
  priority?: Priority;
  status?: WOStatus;
  description?: string;
  assignedToUserIds?: string[];
  dueDate?: string | null;
  scheduledDate?: string | null;
  estimatedHours?: number;
  downtimeStart?: string | null;
  shift?: WorkOrder["shift"];
  checklist?: WorkOrder["checklist"];
  pmPlanId?: string | null;
  history?: WorkOrder["history"];
  failureCode?: string;
}

export function newWorkOrder(input: NewWorkOrderInput, now: string): WorkOrder {
  const status = input.status ?? (input.assignedToUserIds && input.assignedToUserIds.length > 0 ? "assigned" : "open");
  return {
    id: "",
    woNo: input.woNo,
    type: input.type,
    title: input.title,
    description: input.description ?? "",
    assetId: input.assetId ?? null,
    lineId: input.lineId ?? null,
    priority: input.priority ?? "medium",
    status,
    requestedByUserId: input.requestedByUserId,
    assignedToUserIds: input.assignedToUserIds ?? [],
    dueDate: input.dueDate ?? null,
    scheduledDate: input.scheduledDate ?? null,
    estimatedHours: input.estimatedHours ?? 0,
    startedAt: null,
    completedAt: null,
    closedAt: null,
    closedByUserId: null,
    failureCode: input.failureCode ?? "",
    rootCause: "",
    actionTaken: "",
    downtimeStart: input.downtimeStart ?? null,
    downtimeEnd: null,
    downtimeMinutes: null,
    shift: input.shift ?? null,
    labor: [],
    partsUsed: [],
    checklist: input.checklist ?? [],
    comments: [],
    history: input.history ?? [{ at: now, userId: input.requestedByUserId, from: null, to: status, note: "Created" }],
    pmPlanId: input.pmPlanId ?? null,
    meterAtCompletion: null,
    handbackByUserId: null,
    handbackAt: null,
    createdAt: now,
    updatedAt: now,
  };
}
