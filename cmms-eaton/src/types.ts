/** Domain model for CMMS_Eaton. Everything lives in one Snapshot document (see store/snapshot.ts). */

export type Role = "technician" | "production_supervisor" | "maintenance_supervisor" | "owner";
export const ROLES: Role[] = ["technician", "production_supervisor", "maintenance_supervisor", "owner"];
export const ROLE_LABELS: Record<Role, string> = {
  technician: "Technician",
  production_supervisor: "Production supervisor",
  maintenance_supervisor: "Maintenance supervisor",
  owner: "Owner",
};

export type Shift = "A" | "B" | "C";
export const SHIFTS: Shift[] = ["A", "B", "C"];
export interface ShiftDef {
  start: string; // HH:MM, plant local time
  end: string; // HH:MM, may wrap past midnight (shift C)
}

export type Criticality = "A" | "B" | "C";
export type AssetStatus = "running" | "down" | "maintenance" | "retired";
export const ASSET_STATUS_LABELS: Record<AssetStatus, string> = {
  running: "Running",
  down: "Down",
  maintenance: "Under maintenance",
  retired: "Retired",
};

export type WOType = "breakdown" | "pm" | "corrective" | "improvement" | "safety" | "inspection" | "project" | "other";
export type WOStatus = "open" | "assigned" | "in_progress" | "on_hold" | "completed" | "closed" | "cancelled";
export type Priority = "low" | "medium" | "high" | "critical";

export interface Timestamps {
  createdAt: string;
  updatedAt: string;
}

export interface User extends Timestamps {
  id: string;
  employeeId: string;
  name: string;
  role: Role;
  /** Production supervisors: the lines they cover (empty = all lines). */
  lineIds: string[];
  phone: string;
  email: string;
  skills: string;
  active: boolean;
  passwordHash: string;
  passwordSalt: string;
  mustChangePassword: boolean;
  failedAttempts: number;
  lockedUntil: string | null;
  lastLoginAt: string | null;
}

export interface Line extends Timestamps {
  id: string;
  code: string;
  name: string;
  area: string;
  /** Shifts this line runs. Plant default is A and B; selected lines also run C. */
  shifts: Shift[];
  active: boolean;
}

export interface SpecItem {
  key: string;
  value: string;
}

export interface Asset extends Timestamps {
  id: string;
  assetNo: string;
  name: string;
  lineId: string | null;
  /** Sub-assets / components point at their parent machine. */
  parentId: string | null;
  category: string;
  make: string;
  model: string;
  serialNo: string;
  criticality: Criticality;
  status: AssetStatus;
  location: string;
  installDate: string | null;
  meterUnit: string; // "hours", "cycles", "" when no meter
  meterReading: number;
  meterUpdatedAt: string | null;
  specs: SpecItem[];
  notes: string;
  active: boolean;
}

export interface Part extends Timestamps {
  id: string;
  partNo: string;
  name: string;
  description: string;
  category: string;
  unit: string;
  stock: number;
  minStock: number;
  maxStock: number;
  location: string;
  unitCost: number;
  supplier: string;
  leadTimeDays: number;
  assetIds: string[];
  active: boolean;
}

export type StockTxType = "receive" | "issue" | "return" | "adjust";
export interface StockTransaction {
  id: string;
  partId: string;
  type: StockTxType;
  /** Signed quantity change applied to stock. */
  qty: number;
  unitCost: number;
  workOrderId: string | null;
  userId: string;
  at: string;
  note: string;
}

export interface LaborEntry {
  id: string;
  userId: string;
  date: string;
  hours: number;
  note: string;
}

export interface PartUsage {
  id: string;
  partId: string;
  qty: number;
  unitCost: number;
}

export interface ChecklistItem {
  id: string;
  text: string;
  done: boolean;
  doneByUserId: string | null;
  doneAt: string | null;
}

export interface Comment {
  id: string;
  userId: string;
  text: string;
  at: string;
}

export interface StatusChange {
  at: string;
  userId: string;
  from: WOStatus | null;
  to: WOStatus;
  note: string;
}

export interface WorkOrder extends Timestamps {
  id: string;
  woNo: string;
  type: WOType;
  title: string;
  description: string;
  assetId: string | null;
  lineId: string | null;
  priority: Priority;
  status: WOStatus;
  requestedByUserId: string;
  assignedToUserIds: string[];
  dueDate: string | null;
  scheduledDate: string | null;
  estimatedHours: number;
  startedAt: string | null;
  completedAt: string | null;
  closedAt: string | null;
  closedByUserId: string | null;
  failureCode: string;
  rootCause: string;
  actionTaken: string;
  /** Breakdowns: when the machine stopped / was handed back to production. */
  downtimeStart: string | null;
  downtimeEnd: string | null;
  downtimeMinutes: number | null;
  shift: Shift | null;
  labor: LaborEntry[];
  partsUsed: PartUsage[];
  checklist: ChecklistItem[];
  comments: Comment[];
  history: StatusChange[];
  pmPlanId: string | null;
  meterAtCompletion: number | null;
  /** Production supervisor confirmation that the machine is back in service. */
  handbackByUserId: string | null;
  handbackAt: string | null;
}

export type IntervalUnit = "day" | "week" | "month" | "year";
export type PMTrigger = "time" | "meter" | "both";

export interface PMPlanPart {
  partId: string;
  qty: number;
}

export interface PMPlan extends Timestamps {
  id: string;
  code: string;
  name: string;
  description: string;
  assetId: string;
  trigger: PMTrigger;
  intervalValue: number;
  intervalUnit: IntervalUnit;
  meterInterval: number | null;
  /** fixed: next due counts from the scheduled date; floating: from the completion date. */
  scheduleMode: "fixed" | "floating";
  leadDays: number;
  lastDoneAt: string | null;
  lastDoneMeter: number | null;
  nextDueAt: string;
  nextDueMeter: number | null;
  estimatedHours: number;
  priority: Priority;
  assignedToUserId: string | null;
  checklist: string[];
  parts: PMPlanPart[];
  active: boolean;
}

export interface AuditEntry {
  id: string;
  at: string;
  userId: string | null;
  entity: string;
  entityId: string;
  action: string;
  summary: string;
}

export interface SharePointConfig {
  siteUrl: string;
  libraryPath: string;
  tenantId: string;
  clientId: string;
}

export interface Settings {
  plantName: string;
  siteCode: string;
  timezone: string;
  currency: string;
  woPrefix: string;
  shifts: Record<Shift, ShiftDef>;
  defaultLineShifts: Shift[];
  pmLeadDays: number;
  /** Planned production hours per day for plant-wide MTBF (two shifts = 16). */
  plannedHoursPerDay: number;
  failureCodes: string[];
  assetCategories: string[];
  partCategories: string[];
  sharepoint: SharePointConfig;
}

export interface Sequences {
  wo: number;
  pm: number;
  asset: number;
  part: number;
}

export interface Snapshot {
  schemaVersion: 1;
  app: "CMMS_Eaton";
  createdAt: string;
  updatedAt: string;
  demo: boolean;
  settings: Settings;
  users: User[];
  lines: Line[];
  assets: Asset[];
  parts: Part[];
  stockTransactions: StockTransaction[];
  workOrders: WorkOrder[];
  pmPlans: PMPlan[];
  audit: AuditEntry[];
  sequences: Sequences;
}
