import type { Settings, Snapshot } from "../types";
import { nowIso } from "../lib/ids";

export const SNAPSHOT_FILE = "CMMS_Eaton-data.json";

export function defaultSettings(): Settings {
  return {
    plantName: "Eaton",
    siteCode: "PLANT",
    timezone: "Asia/Kolkata",
    currency: "INR",
    woPrefix: "WO",
    shifts: {
      A: { start: "06:00", end: "14:00" },
      B: { start: "14:00", end: "22:00" },
      C: { start: "22:00", end: "06:00" },
    },
    defaultLineShifts: ["A", "B"],
    pmLeadDays: 7,
    plannedHoursPerDay: 16,
    failureCodes: ["Electrical", "Mechanical", "Pneumatic", "Hydraulic", "Sensor", "PLC / Controls", "Operator error", "Material", "Utility", "Unknown"],
    assetCategories: ["Assembly", "Press", "Moulding", "Conveyor", "Utility", "Testing", "Packing", "Component", "Other"],
    partCategories: ["Electrical", "Mechanical", "Pneumatic", "Hydraulic", "Sensor", "Consumable", "Filter", "Lubricant", "Other"],
    sharepoint: { siteUrl: "", libraryPath: "", tenantId: "", clientId: "" },
  };
}

export function emptySnapshot(now: string = nowIso()): Snapshot {
  return {
    schemaVersion: 1,
    app: "CMMS_Eaton",
    createdAt: now,
    updatedAt: now,
    demo: false,
    settings: defaultSettings(),
    users: [],
    lines: [],
    assets: [],
    parts: [],
    stockTransactions: [],
    workOrders: [],
    pmPlans: [],
    audit: [],
    sequences: { wo: 0, pm: 0, asset: 0, part: 0 },
  };
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

/** Validate and upgrade a stored document. Returns null when it is not a CMMS_Eaton snapshot. */
export function migrate(raw: unknown): Snapshot | null {
  if (!isRecord(raw) || raw.app !== "CMMS_Eaton") return null;
  if (raw.schemaVersion !== 1) return null;
  const base = emptySnapshot();
  const arr = (key: keyof Snapshot): unknown[] => (Array.isArray(raw[key]) ? (raw[key] as unknown[]) : []);
  const settings = isRecord(raw.settings) ? raw.settings : {};
  const merged: Snapshot = {
    ...base,
    createdAt: typeof raw.createdAt === "string" ? raw.createdAt : base.createdAt,
    updatedAt: typeof raw.updatedAt === "string" ? raw.updatedAt : base.updatedAt,
    demo: raw.demo === true,
    settings: {
      ...base.settings,
      ...(settings as Partial<Settings>),
      shifts: { ...base.settings.shifts, ...(isRecord(settings.shifts) ? (settings.shifts as Settings["shifts"]) : {}) },
      sharepoint: { ...base.settings.sharepoint, ...(isRecord(settings.sharepoint) ? (settings.sharepoint as Partial<Settings["sharepoint"]>) : {}) },
    },
    users: arr("users") as Snapshot["users"],
    lines: arr("lines") as Snapshot["lines"],
    assets: arr("assets") as Snapshot["assets"],
    parts: arr("parts") as Snapshot["parts"],
    stockTransactions: arr("stockTransactions") as Snapshot["stockTransactions"],
    workOrders: arr("workOrders") as Snapshot["workOrders"],
    pmPlans: arr("pmPlans") as Snapshot["pmPlans"],
    audit: arr("audit") as Snapshot["audit"],
    sequences: { ...base.sequences, ...(isRecord(raw.sequences) ? (raw.sequences as Partial<Snapshot["sequences"]>) : {}) },
  };
  return merged;
}
