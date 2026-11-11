import { describe, expect, it } from "vitest";
import { changeStatus, completeWorkOrder, createWorkOrder, movePart } from "../src/lib/mutations";
import { buildDemoSnapshot } from "../src/store/seed";
import { migrate } from "../src/store/snapshot";
import { parseCsv, toCsv } from "../src/lib/csv";

describe("sample data", () => {
  it("builds a consistent snapshot that survives a save/load round trip", async () => {
    const s = await buildDemoSnapshot("2026-11-11");
    expect(s.users).toHaveLength(6);
    expect(s.assets.length).toBeGreaterThan(10);
    expect(s.workOrders.length).toBeGreaterThan(20);
    expect(new Set(s.workOrders.map((w) => w.woNo)).size).toBe(s.workOrders.length);
    for (const w of s.workOrders) {
      if (w.assetId) expect(s.assets.some((a) => a.id === w.assetId)).toBe(true);
      for (const p of w.partsUsed) expect(s.parts.some((x) => x.id === p.partId)).toBe(true);
    }
    const again = migrate(JSON.parse(JSON.stringify(s)));
    expect(again?.workOrders.length).toBe(s.workOrders.length);
    expect(migrate({ foo: 1 })).toBeNull();
    expect(migrate({ app: "CMMS_Eaton", schemaVersion: 1 })?.settings.shifts.C.start).toBe("22:00");
  }, 30_000);
});

describe("work order flow", () => {
  it("breakdown creation stamps shift, priority and marks the machine down", async () => {
    const s = await buildDemoSnapshot("2026-11-11");
    const asset = s.assets.find((a) => a.assetNo === "FA-01")!;
    const tech = s.users.find((u) => u.employeeId === "D-TECH1")!;
    const wo = createWorkOrder(s, { type: "breakdown", title: "Jam", assetId: asset.id, downtimeStart: "2026-11-11T23:30:00" }, tech.id);
    expect(wo.priority).toBe("critical"); // criticality A
    expect(wo.shift).toBe("C");
    expect(wo.lineId).toBe(asset.lineId);
    expect(s.assets.find((a) => a.id === asset.id)!.status).toBe("down");

    changeStatus(s, wo.id, "in_progress", tech.id);
    expect(wo.assignedToUserIds).toEqual([tech.id]);
    expect(wo.startedAt).not.toBeNull();

    const part = s.parts.find((p) => p.partNo === "SP-1003")!;
    const before = part.stock;
    expect(movePart(s, wo.id, part.id, 2, tech.id, "issue")).toBeNull();
    expect(part.stock).toBe(before - 2);
    expect(movePart(s, wo.id, part.id, 999, tech.id, "issue")).toMatch(/in stock/);
    expect(movePart(s, wo.id, part.id, 1, tech.id, "return")).toBeNull();
    expect(part.stock).toBe(before - 1);
    expect(wo.partsUsed[0].qty).toBe(1);

    completeWorkOrder(s, wo.id, { rootCause: "Sensor", actionTaken: "Replaced", failureCode: "Sensor", downtimeEnd: "2026-11-12T01:00:00", meterReading: 12500, laborHours: 1.5 }, tech.id);
    expect(wo.status).toBe("completed");
    expect(wo.downtimeMinutes).toBe(90);
    expect(wo.labor.some((l) => l.hours === 1.5)).toBe(true);
    expect(s.assets.find((a) => a.id === asset.id)!.meterReading).toBe(12500);
  }, 30_000);

  it("completing a PM work order rolls the plan forward", async () => {
    const s = await buildDemoSnapshot("2026-11-11");
    const wo = s.workOrders.find((w) => w.type === "pm" && (w.status === "open" || w.status === "assigned"))!;
    const plan = s.pmPlans.find((p) => p.id === wo.pmPlanId)!;
    const dueBefore = plan.nextDueAt;
    changeStatus(s, wo.id, "in_progress", "u");
    completeWorkOrder(s, wo.id, { rootCause: "", actionTaken: "Done", failureCode: "", downtimeEnd: null, meterReading: null, laborHours: 1 }, "u");
    expect(plan.nextDueAt > dueBefore).toBe(true);
    expect(plan.lastDoneAt).toBe(new Date().toISOString().slice(0, 10));
  }, 30_000);
});

describe("csv", () => {
  it("parses quoted fields and normalises headers", () => {
    const rows = parseCsv('Asset No,Name,Notes\r\nEQ-1,"Press, big","Line ""A"""\nEQ-2,Pump,\n');
    expect(rows).toEqual([
      { asset_no: "EQ-1", name: "Press, big", notes: 'Line "A"' },
      { asset_no: "EQ-2", name: "Pump", notes: "" },
    ]);
  });
  it("neutralises formula injection on export", () => {
    expect(toCsv([{ a: "=SUM(1)", b: "x,y" }])).toBe('a,b\r\n\'=SUM(1),"x,y"');
  });
});
