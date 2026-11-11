import { describe, expect, it } from "vitest";
import { can, canExecuteWorkOrder, canManageUserRole, canSeeWorkOrder } from "../src/lib/permissions";
import { newWorkOrder } from "../src/lib/workorders";
import type { Role, User } from "../src/types";

function user(role: Role, extra: Partial<User> = {}): User {
  return {
    id: `u-${role}`,
    employeeId: role,
    name: role,
    role,
    lineIds: [],
    phone: "",
    email: "",
    skills: "",
    active: true,
    passwordHash: "",
    passwordSalt: "",
    mustChangePassword: false,
    failedAttempts: 0,
    lockedUntil: null,
    lastLoginAt: null,
    createdAt: "",
    updatedAt: "",
    ...extra,
  };
}

describe("role matrix", () => {
  const tech = user("technician");
  const prod = user("production_supervisor");
  const msup = user("maintenance_supervisor");
  const owner = user("owner");

  it("lets everyone raise a request and only maintenance roles execute", () => {
    for (const u of [tech, prod, msup, owner]) expect(can(u, "wo.request")).toBe(true);
    expect(can(tech, "wo.execute")).toBe(true);
    expect(can(prod, "wo.execute")).toBe(false);
  });
  it("keeps assignment, closing and PM management with supervisors", () => {
    expect(can(tech, "wo.assign")).toBe(false);
    expect(can(prod, "wo.close")).toBe(false);
    expect(can(msup, "wo.assign")).toBe(true);
    expect(can(msup, "pm.manage")).toBe(true);
    expect(can(prod, "pm.manage")).toBe(false);
  });
  it("gives production the handback and the owner the settings", () => {
    expect(can(prod, "wo.handback")).toBe(true);
    expect(can(tech, "wo.handback")).toBe(false);
    expect(can(msup, "settings.manage")).toBe(false);
    expect(can(owner, "settings.manage")).toBe(true);
    expect(can(owner, "audit.view")).toBe(true);
    expect(can(msup, "audit.view")).toBe(false);
  });
  it("denies everything to inactive accounts", () => {
    expect(can(user("owner", { active: false }), "wo.request")).toBe(false);
  });
  it("scopes user management", () => {
    expect(canManageUserRole(msup, "technician")).toBe(true);
    expect(canManageUserRole(msup, "owner")).toBe(false);
    expect(canManageUserRole(owner, "maintenance_supervisor")).toBe(true);
    expect(canManageUserRole(tech, "technician")).toBe(false);
  });
});

describe("work order scoping", () => {
  const base = newWorkOrder({ woNo: "WO-1", type: "breakdown", title: "t", requestedByUserId: "x", lineId: "L1" }, "2026-11-11T00:00:00Z");
  it("limits production supervisors to their lines", () => {
    const prodL1 = user("production_supervisor", { lineIds: ["L1"] });
    const prodL2 = user("production_supervisor", { lineIds: ["L2"] });
    const prodAll = user("production_supervisor");
    expect(canSeeWorkOrder(prodL1, base)).toBe(true);
    expect(canSeeWorkOrder(prodL2, base)).toBe(false);
    expect(canSeeWorkOrder(prodAll, base)).toBe(true);
  });
  it("lets a technician pick up unassigned work but not someone else's", () => {
    const tech = user("technician", { id: "t1" });
    expect(canExecuteWorkOrder(tech, base)).toBe(true);
    const assignedToOther = { ...base, assignedToUserIds: ["t2"], status: "assigned" as const };
    expect(canExecuteWorkOrder(tech, assignedToOther)).toBe(false);
    const assignedToMe = { ...base, assignedToUserIds: ["t1"], status: "in_progress" as const };
    expect(canExecuteWorkOrder(tech, assignedToMe)).toBe(true);
    expect(canExecuteWorkOrder(user("maintenance_supervisor"), assignedToOther)).toBe(true);
    expect(canExecuteWorkOrder(user("production_supervisor"), base)).toBe(false);
  });
});
