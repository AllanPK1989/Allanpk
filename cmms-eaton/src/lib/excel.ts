import type { Snapshot } from "../types";
import { formatDateTime, isoToDateKey } from "./dates";
import { laborHours, partsCost, PRIORITY_LABEL, WO_STATUS_LABEL, WO_TYPE_LABEL } from "./workorders";
import { ROLE_LABELS } from "../types";
import { intervalLabel } from "./pm";

export type Row = Record<string, string | number | boolean | null>;

export interface Sheet {
  name: string;
  rows: Row[];
}

function sanitizeCell(v: Row[string]): Row[string] {
  // Prevent formula injection when the file is opened in Excel.
  if (typeof v === "string" && /^[=+\-@\t\r]/.test(v)) return `'${v}`;
  return v;
}

/** Builds an .xlsx in the browser. The spreadsheet library loads on first use so the app shell stays small. */
export async function downloadWorkbook(filename: string, sheets: Sheet[]): Promise<void> {
  const XLSX = await import("xlsx");
  const wb = XLSX.utils.book_new();
  for (const s of sheets) {
    const rows = s.rows.map((r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, sanitizeCell(v)])));
    const ws = XLSX.utils.json_to_sheet(rows.length ? rows : [{ note: "No rows" }]);
    XLSX.utils.book_append_sheet(wb, ws, s.name.slice(0, 31));
  }
  XLSX.writeFile(wb, filename);
}

export function downloadText(filename: string, text: string, mime = "text/plain"): void {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function snapshotSheets(s: Snapshot): Sheet[] {
  const userName = (id: string | null): string => (id ? (s.users.find((u) => u.id === id)?.name ?? id) : "");
  const assetLabel = (id: string | null): string => {
    const a = id ? s.assets.find((x) => x.id === id) : undefined;
    return a ? `${a.assetNo} ${a.name}` : "";
  };
  const lineLabel = (id: string | null): string => (id ? (s.lines.find((l) => l.id === id)?.code ?? "") : "");
  const partLabel = (id: string): string => {
    const p = s.parts.find((x) => x.id === id);
    return p ? `${p.partNo} ${p.name}` : id;
  };
  return [
    {
      name: "Work orders",
      rows: s.workOrders.map((w) => ({
        "WO no": w.woNo,
        Type: WO_TYPE_LABEL[w.type],
        Title: w.title,
        Status: WO_STATUS_LABEL[w.status],
        Priority: PRIORITY_LABEL[w.priority],
        Asset: assetLabel(w.assetId),
        Line: lineLabel(w.lineId),
        "Requested by": userName(w.requestedByUserId),
        "Assigned to": w.assignedToUserIds.map(userName).join("; "),
        Created: formatDateTime(w.createdAt),
        Due: w.dueDate ?? "",
        Started: formatDateTime(w.startedAt),
        Completed: formatDateTime(w.completedAt),
        Closed: formatDateTime(w.closedAt),
        Shift: w.shift ?? "",
        "Downtime start": formatDateTime(w.downtimeStart),
        "Downtime end": formatDateTime(w.downtimeEnd),
        "Downtime (min)": w.downtimeMinutes,
        "Failure code": w.failureCode,
        "Root cause": w.rootCause,
        "Action taken": w.actionTaken,
        "Labour (h)": laborHours(w),
        "Parts cost": partsCost(w),
        "Parts used": w.partsUsed.map((p) => `${partLabel(p.partId)} x${p.qty}`).join("; "),
        "Handback by": userName(w.handbackByUserId),
        Description: w.description,
      })),
    },
    {
      name: "Assets",
      rows: s.assets.map((a) => ({
        "Asset no": a.assetNo,
        Name: a.name,
        Line: lineLabel(a.lineId),
        Parent: assetLabel(a.parentId),
        Category: a.category,
        Make: a.make,
        Model: a.model,
        "Serial no": a.serialNo,
        Criticality: a.criticality,
        Status: a.status,
        Location: a.location,
        "Install date": a.installDate ?? "",
        "Meter unit": a.meterUnit,
        "Meter reading": a.meterReading,
        Active: a.active,
        Notes: a.notes,
      })),
    },
    {
      name: "Spare parts",
      rows: s.parts.map((p) => ({
        "Part no": p.partNo,
        Name: p.name,
        Description: p.description,
        Category: p.category,
        Unit: p.unit,
        Stock: p.stock,
        "Min stock": p.minStock,
        "Max stock": p.maxStock,
        Location: p.location,
        "Unit cost": p.unitCost,
        Supplier: p.supplier,
        "Lead time (days)": p.leadTimeDays,
        Assets: p.assetIds.map(assetLabel).join("; "),
        Active: p.active,
      })),
    },
    {
      name: "PM plans",
      rows: s.pmPlans.map((p) => ({
        Code: p.code,
        Name: p.name,
        Asset: assetLabel(p.assetId),
        Interval: intervalLabel(p),
        "Schedule mode": p.scheduleMode,
        "Lead days": p.leadDays,
        "Last done": p.lastDoneAt ?? "",
        "Next due": p.nextDueAt,
        "Next due meter": p.nextDueMeter,
        "Estimated hours": p.estimatedHours,
        Priority: PRIORITY_LABEL[p.priority],
        "Assigned to": userName(p.assignedToUserId),
        Checklist: p.checklist.join(" | "),
        Active: p.active,
      })),
    },
    {
      name: "Stock transactions",
      rows: s.stockTransactions.map((t) => ({
        Date: formatDateTime(t.at),
        Part: partLabel(t.partId),
        Type: t.type,
        Qty: t.qty,
        "Unit cost": t.unitCost,
        "Work order": t.workOrderId ? (s.workOrders.find((w) => w.id === t.workOrderId)?.woNo ?? "") : "",
        By: userName(t.userId),
        Note: t.note,
      })),
    },
    {
      name: "Users",
      rows: s.users.map((u) => ({
        "Employee ID": u.employeeId,
        Name: u.name,
        Role: ROLE_LABELS[u.role],
        Lines: u.lineIds.map(lineLabel).join("; "),
        Phone: u.phone,
        Email: u.email,
        Active: u.active,
        "Last login": formatDateTime(u.lastLoginAt),
      })),
    },
    {
      name: "Audit log",
      rows: s.audit.map((a) => ({
        At: formatDateTime(a.at),
        User: userName(a.userId),
        Entity: a.entity,
        Action: a.action,
        Summary: a.summary,
        Date: isoToDateKey(a.at) ?? "",
      })),
    },
  ];
}
