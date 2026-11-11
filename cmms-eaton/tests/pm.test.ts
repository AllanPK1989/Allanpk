import { describe, expect, it } from "vitest";
import { completePlanCycle, generateDuePMs, planState } from "../src/lib/pm";
import { emptySnapshot } from "../src/store/snapshot";
import type { Asset, PMPlan } from "../src/types";

function asset(extra: Partial<Asset> = {}): Asset {
  return {
    id: "a1",
    assetNo: "EQ-001",
    name: "Press",
    lineId: null,
    parentId: null,
    category: "",
    make: "",
    model: "",
    serialNo: "",
    criticality: "A",
    status: "running",
    location: "",
    installDate: null,
    meterUnit: "hours",
    meterReading: 1000,
    meterUpdatedAt: null,
    specs: [],
    notes: "",
    active: true,
    createdAt: "",
    updatedAt: "",
    ...extra,
  };
}

function plan(extra: Partial<PMPlan> = {}): PMPlan {
  return {
    id: "p1",
    code: "PM-001",
    name: "Monthly check",
    description: "",
    assetId: "a1",
    trigger: "time",
    intervalValue: 1,
    intervalUnit: "month",
    meterInterval: null,
    scheduleMode: "fixed",
    leadDays: 7,
    lastDoneAt: null,
    lastDoneMeter: null,
    nextDueAt: "2026-11-20",
    nextDueMeter: null,
    estimatedHours: 1,
    priority: "medium",
    assignedToUserId: null,
    checklist: ["Step 1", "Step 2"],
    parts: [],
    active: true,
    createdAt: "",
    updatedAt: "",
    ...extra,
  };
}

describe("plan state", () => {
  it("classifies time-based plans by lead days", () => {
    const a = asset();
    expect(planState(plan({ nextDueAt: "2026-11-10" }), a, "2026-11-11")).toBe("overdue");
    expect(planState(plan({ nextDueAt: "2026-11-15" }), a, "2026-11-11")).toBe("due");
    expect(planState(plan({ nextDueAt: "2026-11-25" }), a, "2026-11-11")).toBe("upcoming");
    expect(planState(plan({ nextDueAt: "2027-01-15" }), a, "2026-11-11")).toBe("ok");
    expect(planState(plan({ active: false }), a, "2026-11-11")).toBe("inactive");
  });
  it("classifies meter-based plans by remaining units", () => {
    const p = plan({ trigger: "meter", meterInterval: 500, nextDueMeter: 1040, nextDueAt: "2027-01-01" });
    expect(planState(p, asset({ meterReading: 1000 }), "2026-11-11")).toBe("due"); // within 10% lead
    expect(planState(p, asset({ meterReading: 1100 }), "2026-11-11")).toBe("overdue");
    expect(planState(p, asset({ meterReading: 500 }), "2026-11-11")).toBe("ok");
  });
});

describe("generation", () => {
  it("creates one work order per due plan and never duplicates", () => {
    const s = emptySnapshot();
    s.assets.push(asset());
    s.pmPlans.push(plan({ id: "due", nextDueAt: "2026-11-12", assignedToUserId: "tech" }), plan({ id: "later", code: "PM-002", nextDueAt: "2027-03-01" }));
    const first = generateDuePMs(s, "owner", "2026-11-11");
    expect(first).toHaveLength(1);
    expect(first[0].pmPlanId).toBe("due");
    expect(first[0].status).toBe("assigned");
    expect(first[0].checklist.map((c) => c.text)).toEqual(["Step 1", "Step 2"]);
    expect(first[0].woNo).toBe("WO-" + new Date().getFullYear() + "-00001");
    expect(generateDuePMs(s, "owner", "2026-11-11")).toHaveLength(0);
  });
  it("skips retired assets", () => {
    const s = emptySnapshot();
    s.assets.push(asset({ status: "retired" }));
    s.pmPlans.push(plan({ nextDueAt: "2026-11-01" }));
    expect(generateDuePMs(s, "owner", "2026-11-11")).toHaveLength(0);
  });
});

describe("cycle roll-forward", () => {
  it("fixed schedules keep their rhythm and catch up when behind", () => {
    const p = plan({ nextDueAt: "2026-11-01", scheduleMode: "fixed" });
    completePlanCycle(p, "2026-11-11", null);
    expect(p.lastDoneAt).toBe("2026-11-11");
    expect(p.nextDueAt).toBe("2026-12-01");
    const late = plan({ nextDueAt: "2026-06-01", scheduleMode: "fixed" });
    completePlanCycle(late, "2026-11-11", null);
    expect(late.nextDueAt).toBe("2026-12-01");
  });
  it("floating schedules count from the completion date", () => {
    const p = plan({ nextDueAt: "2026-11-01", scheduleMode: "floating", intervalValue: 2, intervalUnit: "week" });
    completePlanCycle(p, "2026-11-11", null);
    expect(p.nextDueAt).toBe("2026-11-25");
  });
  it("meter plans advance by the meter interval", () => {
    const p = plan({ trigger: "both", meterInterval: 500, nextDueMeter: 1000 });
    completePlanCycle(p, "2026-11-11", 1012);
    expect(p.lastDoneMeter).toBe(1012);
    expect(p.nextDueMeter).toBe(1512);
    expect(p.nextDueAt).toBe("2026-12-20");
  });
});
