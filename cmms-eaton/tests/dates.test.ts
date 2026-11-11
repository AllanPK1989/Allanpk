import { describe, expect, it } from "vitest";
import { addInterval, daysBetween, minutesBetween, shiftForDate, shiftHours, weekStart } from "../src/lib/dates";
import { defaultSettings } from "../src/store/snapshot";

const shifts = defaultSettings().shifts;

describe("shifts", () => {
  it("maps plant times to A, B and C", () => {
    expect(shiftForDate(new Date(2026, 10, 11, 6, 0), shifts)).toBe("A");
    expect(shiftForDate(new Date(2026, 10, 11, 13, 59), shifts)).toBe("A");
    expect(shiftForDate(new Date(2026, 10, 11, 14, 0), shifts)).toBe("B");
    expect(shiftForDate(new Date(2026, 10, 11, 21, 30), shifts)).toBe("B");
  });
  it("handles shift C wrapping past midnight", () => {
    expect(shiftForDate(new Date(2026, 10, 11, 22, 0), shifts)).toBe("C");
    expect(shiftForDate(new Date(2026, 10, 11, 23, 59), shifts)).toBe("C");
    expect(shiftForDate(new Date(2026, 10, 12, 2, 15), shifts)).toBe("C");
    expect(shiftForDate(new Date(2026, 10, 12, 5, 59), shifts)).toBe("C");
  });
  it("knows how long each shift is", () => {
    expect(shiftHours(shifts.A)).toBe(8);
    expect(shiftHours(shifts.C)).toBe(8);
    expect(shiftHours({ start: "06:00", end: "18:00" })).toBe(12);
  });
});

describe("intervals", () => {
  it("adds calendar intervals and clamps month ends", () => {
    expect(addInterval("2026-01-31", 1, "month")).toBe("2026-02-28");
    expect(addInterval("2026-01-15", 2, "week")).toBe("2026-01-29");
    expect(addInterval("2026-11-11", 1, "year")).toBe("2027-11-11");
    expect(addInterval("2026-12-30", 3, "day")).toBe("2027-01-02");
  });
  it("counts days and minutes", () => {
    expect(daysBetween("2026-11-01", "2026-11-11")).toBe(10);
    expect(daysBetween("2026-11-11", "2026-11-01")).toBe(-10);
    expect(minutesBetween("2026-11-11T06:00:00Z", "2026-11-11T08:30:00Z")).toBe(150);
    expect(minutesBetween("2026-11-11T08:00:00Z", "2026-11-11T07:00:00Z")).toBe(0);
  });
  it("finds the Monday of a week", () => {
    expect(weekStart("2026-11-11")).toBe("2026-11-09"); // Wednesday -> Monday
    expect(weekStart("2026-11-09")).toBe("2026-11-09");
    expect(weekStart("2026-11-15")).toBe("2026-11-09"); // Sunday
  });
});
