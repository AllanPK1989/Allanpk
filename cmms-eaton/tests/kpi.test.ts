import { describe, expect, it } from "vitest";
import { availabilityPct, lowStockParts, mtbfHours, mttrHours, pmCompliance, weeklySeries } from "../src/lib/kpi";
import { newWorkOrder } from "../src/lib/workorders";
import type { Part, WorkOrder } from "../src/types";

function breakdown(start: string, minutes: number, status: WorkOrder["status"] = "closed"): WorkOrder {
  const wo = newWorkOrder({ woNo: "x", type: "breakdown", title: "t", requestedByUserId: "u", downtimeStart: start }, start);
  const end = new Date(new Date(start).getTime() + minutes * 60_000).toISOString();
  return { ...wo, status, downtimeEnd: end, downtimeMinutes: minutes, completedAt: end };
}

const period = { from: "2026-11-01", to: "2026-11-10" }; // 10 days

describe("reliability KPIs", () => {
  const wos = [breakdown("2026-11-02T08:00:00", 60), breakdown("2026-11-05T08:00:00", 120), breakdown("2026-10-20T08:00:00", 600)];
  it("MTTR averages downtime of breakdowns completed in the period", () => {
    expect(mttrHours(wos, period)).toBeCloseTo(1.5);
    expect(mttrHours([], period)).toBeNull();
  });
  it("MTBF divides planned hours minus downtime by failures", () => {
    // 10 days x 16 h = 160 h, minus 3 h downtime, over 2 failures
    expect(mtbfHours(wos, period, 16)).toBeCloseTo(78.5);
    expect(mtbfHours([], period, 16)).toBeNull();
  });
  it("availability is planned minus downtime", () => {
    expect(availabilityPct(wos, period, 16)).toBeCloseTo((157 / 160) * 100);
  });
});

describe("PM compliance", () => {
  const pm = (due: string, completed: string | null, status: WorkOrder["status"]): WorkOrder => ({
    ...newWorkOrder({ woNo: "p", type: "pm", title: "t", requestedByUserId: "u", dueDate: due }, "2026-10-01T00:00:00"),
    status,
    completedAt: completed,
  });
  it("counts on time, late and open", () => {
    const c = pmCompliance([pm("2026-11-03", "2026-11-02T10:00:00", "closed"), pm("2026-11-04", "2026-11-06T10:00:00", "completed"), pm("2026-11-05", null, "open"), pm("2026-12-01", null, "open")], period);
    expect(c.due).toBe(3);
    expect(c.onTime).toBe(1);
    expect(c.late).toBe(1);
    expect(c.open).toBe(1);
    expect(c.pct).toBeCloseTo(33.33, 1);
  });
});

describe("series and stock", () => {
  it("buckets work orders by week", () => {
    const wos = [breakdown("2026-11-03T08:00:00", 30), breakdown("2026-11-10T08:00:00", 30, "in_progress")];
    const pts = weeklySeries(wos, 2, "2026-11-11");
    expect(pts.map((p) => p.weekKey)).toEqual(["2026-11-02", "2026-11-09"]);
    expect(pts.map((p) => p.created)).toEqual([1, 1]);
    expect(pts.map((p) => p.completed)).toEqual([1, 0]);
  });
  it("flags parts at or below minimum, most urgent first", () => {
    const part = (partNo: string, stock: number, min: number): Part => ({ id: partNo, partNo, name: "", description: "", category: "", unit: "pc", stock, minStock: min, maxStock: 10, location: "", unitCost: 1, supplier: "", leadTimeDays: 0, assetIds: [], active: true, createdAt: "", updatedAt: "" });
    const low = lowStockParts([part("a", 5, 4), part("b", 0, 2), part("c", 2, 2), part("d", 3, 0)]);
    expect(low.map((p) => p.partNo)).toEqual(["b", "c"]);
  });
});
