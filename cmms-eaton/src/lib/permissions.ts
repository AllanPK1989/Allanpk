import type { Role, User, WorkOrder } from "../types";

export type Permission =
  | "wo.request" // raise a breakdown or work request
  | "wo.create" // create any work order type with full fields
  | "wo.assign" // assign, prioritise, reschedule
  | "wo.execute" // start, hold, log labour/parts, complete (own or unassigned work)
  | "wo.close" // close or cancel
  | "wo.handback" // confirm machine back to production
  | "wo.comment"
  | "pm.view"
  | "pm.manage"
  | "asset.view"
  | "asset.manage"
  | "asset.meter" // update meter readings
  | "part.view"
  | "part.issue" // issue / return parts against a work order
  | "part.manage" // stock, min/max, receive, costs
  | "dashboard.full"
  | "reports.view"
  | "user.manage_technicians"
  | "user.manage_all"
  | "settings.manage"
  | "audit.view"
  | "data.export"
  | "data.import"
  | "storage.manage";

const TECHNICIAN: Permission[] = [
  "wo.request",
  "wo.execute",
  "wo.comment",
  "pm.view",
  "asset.view",
  "asset.meter",
  "part.view",
  "part.issue",
];

const PRODUCTION_SUPERVISOR: Permission[] = [
  "wo.request",
  "wo.handback",
  "wo.comment",
  "pm.view",
  "asset.view",
  "part.view",
  "reports.view",
];

const MAINTENANCE_SUPERVISOR: Permission[] = [
  ...TECHNICIAN,
  "wo.create",
  "wo.assign",
  "wo.close",
  "wo.handback",
  "pm.manage",
  "asset.manage",
  "part.manage",
  "dashboard.full",
  "reports.view",
  "user.manage_technicians",
  "data.export",
  "data.import",
];

const OWNER: Permission[] = [
  ...MAINTENANCE_SUPERVISOR,
  "user.manage_all",
  "settings.manage",
  "audit.view",
  "storage.manage",
];

export const MATRIX: Record<Role, ReadonlySet<Permission>> = {
  technician: new Set(TECHNICIAN),
  production_supervisor: new Set(PRODUCTION_SUPERVISOR),
  maintenance_supervisor: new Set(MAINTENANCE_SUPERVISOR),
  owner: new Set(OWNER),
};

export function can(user: User | null | undefined, permission: Permission): boolean {
  if (!user || !user.active) return false;
  return MATRIX[user.role]?.has(permission) ?? false;
}

export function canAny(user: User | null | undefined, ...permissions: Permission[]): boolean {
  return permissions.some((p) => can(user, p));
}

/** Work orders a user may see at all. Production supervisors with lines see only their lines. */
export function canSeeWorkOrder(user: User | null | undefined, wo: WorkOrder): boolean {
  if (!user) return false;
  if (user.role === "production_supervisor" && user.lineIds.length > 0) {
    return wo.lineId !== null && user.lineIds.includes(wo.lineId);
  }
  return true;
}

/** Who may execute (start, log, complete) a work order. */
export function canExecuteWorkOrder(user: User | null | undefined, wo: WorkOrder): boolean {
  if (!user || !can(user, "wo.execute")) return false;
  if (user.role === "maintenance_supervisor" || user.role === "owner") return true;
  if (wo.assignedToUserIds.includes(user.id)) return true;
  // A technician may pick up unassigned open work.
  return wo.assignedToUserIds.length === 0 && (wo.status === "open" || wo.status === "assigned");
}

export function canManageUserRole(actor: User | null | undefined, targetRole: Role): boolean {
  if (can(actor, "user.manage_all")) return true;
  if (can(actor, "user.manage_technicians")) return targetRole === "technician";
  return false;
}

export function homeRouteFor(role: Role): string {
  return role === "technician" ? "/work-orders?tab=mine" : "/";
}
