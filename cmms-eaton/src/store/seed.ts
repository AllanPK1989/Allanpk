/**
 * SAMPLE data for demos and first runs. Nothing here is real plant data:
 * employee IDs start with "D-" and the plant is named "(sample plant)".
 */
import type { Asset, Criticality, Line, Part, PMPlan, Priority, Role, Shift, Snapshot, StockTransaction, User, WorkOrder } from "../types";
import { hashPassword } from "../lib/auth";
import { addDays, addInterval, minutesBetween, shiftForIso, todayKey } from "../lib/dates";
import { newId, nowIso } from "../lib/ids";
import { completePlanCycle } from "../lib/pm";
import { allocateWoNo, newWorkOrder, priorityForBreakdown } from "../lib/workorders";
import { emptySnapshot } from "./snapshot";

export const DEMO_PASSWORD = "demo1234";

export const DEMO_ACCOUNTS: { employeeId: string; name: string; role: Role; lines: string[] }[] = [
  { employeeId: "D-OWNER", name: "Anand R", role: "owner", lines: [] },
  { employeeId: "D-MSUP", name: "Meena S", role: "maintenance_supervisor", lines: [] },
  { employeeId: "D-PSUP", name: "Karthik V", role: "production_supervisor", lines: ["L1", "L2"] },
  { employeeId: "D-TECH1", name: "Senthil M", role: "technician", lines: [] },
  { employeeId: "D-TECH2", name: "Ravi K", role: "technician", lines: [] },
  { employeeId: "D-TECH3", name: "Divya P", role: "technician", lines: [] },
];

function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a += 0x6d2b79f5;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(rand: () => number, items: T[]): T {
  return items[Math.floor(rand() * items.length)];
}

function atTime(dateKey: string, hour: number, minute = 0): string {
  const [y, m, d] = dateKey.split("-").map(Number);
  return new Date(y, m - 1, d, hour, minute).toISOString();
}

interface AssetSeed {
  no: string;
  name: string;
  line: string;
  category: string;
  make: string;
  model: string;
  crit: Criticality;
  meterUnit: string;
  meter: number;
  location: string;
}

const ASSET_SEEDS: AssetSeed[] = [
  { no: "FA-01", name: "Fuse assembly machine 1", line: "L1", category: "Assembly", make: "Bosch Rexroth", model: "FA-2200", crit: "A", meterUnit: "hours", meter: 12480, location: "Bay 1" },
  { no: "CP-01", name: "Crimping press 1", line: "L1", category: "Press", make: "Schmidt", model: "PressControl 300", crit: "B", meterUnit: "cycles", meter: 842000, location: "Bay 1" },
  { no: "LM-01", name: "Laser marker 1", line: "L1", category: "Testing", make: "Keyence", model: "MD-X1000", crit: "B", meterUnit: "", meter: 0, location: "Bay 1" },
  { no: "PK-01", name: "Packing machine 1", line: "L1", category: "Packing", make: "Ishida", model: "DACS-W", crit: "C", meterUnit: "", meter: 0, location: "Bay 1 end" },
  { no: "FA-02", name: "Fuse assembly machine 2", line: "L2", category: "Assembly", make: "Bosch Rexroth", model: "FA-2200", crit: "A", meterUnit: "hours", meter: 9310, location: "Bay 2" },
  { no: "CP-02", name: "Crimping press 2", line: "L2", category: "Press", make: "Schmidt", model: "PressControl 300", crit: "B", meterUnit: "cycles", meter: 611500, location: "Bay 2" },
  { no: "CV-02", name: "Conveyor line 2", line: "L2", category: "Conveyor", make: "Interroll", model: "RM 8731", crit: "C", meterUnit: "", meter: 0, location: "Bay 2" },
  { no: "IM-01", name: "Injection moulding machine 1", line: "L3", category: "Moulding", make: "Engel", model: "Victory 120", crit: "A", meterUnit: "cycles", meter: 1248000, location: "Moulding hall" },
  { no: "IM-02", name: "Injection moulding machine 2", line: "L3", category: "Moulding", make: "Engel", model: "Victory 120", crit: "A", meterUnit: "cycles", meter: 998400, location: "Moulding hall" },
  { no: "CH-01", name: "Chiller 1", line: "L3", category: "Utility", make: "Blue Star", model: "CHW-30", crit: "B", meterUnit: "hours", meter: 18700, location: "Moulding hall" },
  { no: "AC-01", name: "Air compressor 1", line: "UT", category: "Utility", make: "Atlas Copco", model: "GA 37", crit: "A", meterUnit: "hours", meter: 21590, location: "Compressor room" },
  { no: "AU-01", name: "Autoclave 1", line: "UT", category: "Utility", make: "Equitron", model: "7407ST", crit: "B", meterUnit: "", meter: 0, location: "Utility block" },
  { no: "DG-01", name: "DG set 1", line: "UT", category: "Utility", make: "Cummins", model: "C250 D5", crit: "B", meterUnit: "hours", meter: 1320, location: "DG yard" },
];

interface ComponentSeed {
  parent: string;
  no: string;
  name: string;
  category: string;
}

const COMPONENT_SEEDS: ComponentSeed[] = [
  { parent: "FA-01", no: "FA-01-SRV", name: "Indexing table servo", category: "Component" },
  { parent: "FA-01", no: "FA-01-GRP", name: "Pneumatic gripper station", category: "Component" },
  { parent: "FA-02", no: "FA-02-SRV", name: "Indexing table servo", category: "Component" },
  { parent: "AC-01", no: "AC-01-DRY", name: "Refrigerant air dryer", category: "Component" },
  { parent: "IM-01", no: "IM-01-HYD", name: "Hydraulic power pack", category: "Component" },
];

interface PartSeed {
  no: string;
  name: string;
  category: string;
  unit: string;
  stock: number;
  min: number;
  max: number;
  cost: number;
  location: string;
  supplier: string;
  lead: number;
  assets: string[];
}

const PART_SEEDS: PartSeed[] = [
  { no: "SP-1001", name: "Solenoid valve 5/2 24 V DC", category: "Pneumatic", unit: "pc", stock: 4, min: 4, max: 12, cost: 2850, location: "Rack A1", supplier: "Festo India", lead: 7, assets: ["FA-01", "FA-02", "CP-01", "CP-02"] },
  { no: "SP-1002", name: "Pneumatic cylinder 32 x 50", category: "Pneumatic", unit: "pc", stock: 2, min: 3, max: 8, cost: 3200, location: "Rack A1", supplier: "Festo India", lead: 10, assets: ["FA-01", "FA-02"] },
  { no: "SP-1003", name: "Proximity sensor M12 PNP NO", category: "Sensor", unit: "pc", stock: 9, min: 6, max: 20, cost: 1450, location: "Rack A2", supplier: "ifm", lead: 5, assets: ["FA-01", "FA-02", "CV-02"] },
  { no: "SP-1004", name: "Servo motor 400 W", category: "Electrical", unit: "pc", stock: 1, min: 1, max: 2, cost: 48500, location: "Cage C1", supplier: "Bosch Rexroth", lead: 30, assets: ["FA-01", "FA-02"] },
  { no: "SP-1005", name: "Timing belt 5M-600-15", category: "Mechanical", unit: "pc", stock: 3, min: 2, max: 6, cost: 980, location: "Rack B1", supplier: "Gates", lead: 7, assets: ["FA-01", "FA-02"] },
  { no: "SP-1006", name: "V-belt B-52", category: "Mechanical", unit: "pc", stock: 0, min: 2, max: 6, cost: 420, location: "Rack B1", supplier: "Fenner", lead: 3, assets: ["AC-01", "CH-01"] },
  { no: "SP-1007", name: "Bearing 6205-2RS", category: "Mechanical", unit: "pc", stock: 14, min: 6, max: 24, cost: 310, location: "Rack B2", supplier: "SKF", lead: 3, assets: ["CV-02", "CP-01", "CP-02"] },
  { no: "SP-1008", name: "Contactor 25 A 3P 230 V coil", category: "Electrical", unit: "pc", stock: 5, min: 3, max: 10, cost: 1650, location: "Rack A3", supplier: "Schneider", lead: 5, assets: ["AC-01", "CH-01", "IM-01", "IM-02"] },
  { no: "SP-1009", name: "Air filter element GA37", category: "Filter", unit: "pc", stock: 1, min: 2, max: 4, cost: 5400, location: "Rack D1", supplier: "Atlas Copco", lead: 14, assets: ["AC-01"] },
  { no: "SP-1010", name: "Oil filter element GA37", category: "Filter", unit: "pc", stock: 2, min: 2, max: 4, cost: 4100, location: "Rack D1", supplier: "Atlas Copco", lead: 14, assets: ["AC-01"] },
  { no: "SP-1011", name: "Thermocouple K-type 6 mm", category: "Sensor", unit: "pc", stock: 6, min: 4, max: 12, cost: 850, location: "Rack A2", supplier: "Tempsens", lead: 7, assets: ["IM-01", "IM-02", "AU-01"] },
  { no: "SP-1012", name: "Heater band 200 W 60 mm", category: "Electrical", unit: "pc", stock: 8, min: 4, max: 16, cost: 1200, location: "Rack A3", supplier: "Tempsens", lead: 7, assets: ["IM-01", "IM-02"] },
  { no: "SP-1013", name: "Fuse 10 A gG 10x38", category: "Electrical", unit: "pc", stock: 40, min: 20, max: 100, cost: 45, location: "Drawer E1", supplier: "Eaton Bussmann", lead: 2, assets: [] },
  { no: "SP-1014", name: "Hydraulic oil ISO VG 68", category: "Lubricant", unit: "litre", stock: 120, min: 60, max: 210, cost: 210, location: "Oil store", supplier: "Shell", lead: 5, assets: ["IM-01", "IM-02"] },
  { no: "SP-1015", name: "Grease EP2", category: "Lubricant", unit: "kg", stock: 6, min: 4, max: 15, cost: 380, location: "Oil store", supplier: "Shell", lead: 5, assets: [] },
];

interface PlanSeed {
  code: string;
  name: string;
  asset: string;
  trigger: PMPlan["trigger"];
  value: number;
  unit: PMPlan["intervalUnit"];
  meter: number | null;
  dueOffsetDays: number; // relative to today
  hours: number;
  priority: Priority;
  tech: string | null;
  checklist: string[];
  parts: { no: string; qty: number }[];
}

const PLAN_SEEDS: PlanSeed[] = [
  { code: "PM-001", name: "Weekly lubrication and air check", asset: "FA-01", trigger: "time", value: 1, unit: "week", meter: null, dueOffsetDays: -2, hours: 1, priority: "medium", tech: "D-TECH1", checklist: ["LOTO applied", "Grease indexing table bearings", "Check air pressure 6 bar", "Check gripper wear", "Clean sensors"], parts: [{ no: "SP-1015", qty: 0.2 }] },
  { code: "PM-002", name: "Servo and drive inspection", asset: "FA-01", trigger: "meter", value: 1, unit: "month", meter: 500, dueOffsetDays: 30, hours: 2, priority: "high", tech: "D-TECH2", checklist: ["LOTO applied", "Check servo temperature log", "Inspect encoder cable", "Check drive fault history", "Verify homing"], parts: [] },
  { code: "PM-003", name: "Monthly press inspection", asset: "CP-01", trigger: "time", value: 1, unit: "month", meter: null, dueOffsetDays: 3, hours: 1.5, priority: "medium", tech: "D-TECH2", checklist: ["LOTO applied", "Check ram alignment", "Inspect tooling", "Lubricate guides", "Test light curtain"], parts: [] },
  { code: "PM-004", name: "Quarterly hydraulic service", asset: "IM-01", trigger: "both", value: 3, unit: "month", meter: 300000, dueOffsetDays: 12, hours: 4, priority: "high", tech: "D-TECH3", checklist: ["LOTO applied", "Oil sample and top-up", "Replace return filter", "Check hose condition", "Check accumulator pre-charge"], parts: [{ no: "SP-1014", qty: 20 }] },
  { code: "PM-005", name: "Compressor filter change", asset: "AC-01", trigger: "time", value: 1, unit: "month", meter: null, dueOffsetDays: -5, hours: 1, priority: "high", tech: "D-TECH1", checklist: ["Isolate and depressurise", "Replace air filter", "Check oil level", "Drain condensate", "Check belt tension"], parts: [{ no: "SP-1009", qty: 1 }] },
  { code: "PM-006", name: "Compressor 1000 h service", asset: "AC-01", trigger: "meter", value: 1, unit: "month", meter: 1000, dueOffsetDays: 60, hours: 3, priority: "high", tech: "D-TECH1", checklist: ["Isolate and depressurise", "Replace oil filter", "Change oil", "Check cooler", "Check safety valve"], parts: [{ no: "SP-1010", qty: 1 }] },
  { code: "PM-007", name: "Annual pressure vessel test", asset: "AU-01", trigger: "time", value: 1, unit: "year", meter: null, dueOffsetDays: 45, hours: 6, priority: "critical", tech: null, checklist: ["Hydro test with external agency", "Check safety valve certificate", "Inspect door gasket", "Calibrate pressure gauge"], parts: [] },
  { code: "PM-008", name: "Monthly condenser cleaning", asset: "CH-01", trigger: "time", value: 1, unit: "month", meter: null, dueOffsetDays: 9, hours: 2, priority: "medium", tech: "D-TECH3", checklist: ["Isolate power", "Clean condenser fins", "Check refrigerant pressure", "Check water flow", "Check fan bearings"], parts: [] },
  { code: "PM-009", name: "Weekly DG test run", asset: "DG-01", trigger: "time", value: 1, unit: "week", meter: null, dueOffsetDays: 1, hours: 0.5, priority: "medium", tech: "D-TECH2", checklist: ["Check fuel and coolant", "Run 15 minutes on load", "Record voltage and frequency", "Check battery"], parts: [] },
  { code: "PM-010", name: "Conveyor monthly check", asset: "CV-02", trigger: "time", value: 1, unit: "month", meter: null, dueOffsetDays: 20, hours: 1, priority: "low", tech: "D-TECH3", checklist: ["LOTO applied", "Check belt tracking", "Lubricate rollers", "Check emergency stops"], parts: [{ no: "SP-1007", qty: 0 }] },
  { code: "PM-011", name: "Weekly lubrication and air check", asset: "FA-02", trigger: "time", value: 1, unit: "week", meter: null, dueOffsetDays: 4, hours: 1, priority: "medium", tech: "D-TECH2", checklist: ["LOTO applied", "Grease indexing table bearings", "Check air pressure 6 bar", "Check gripper wear", "Clean sensors"], parts: [{ no: "SP-1015", qty: 0.2 }] },
  { code: "PM-012", name: "Barrel heater and thermocouple check", asset: "IM-02", trigger: "time", value: 2, unit: "month", meter: null, dueOffsetDays: 25, hours: 2, priority: "medium", tech: "D-TECH3", checklist: ["LOTO applied", "Check heater band resistance", "Check thermocouple readings", "Inspect wiring"], parts: [] },
];

const ROOT_CAUSES = [
  ["Solenoid valve coil burnt", "Replaced 5/2 solenoid valve, checked supply voltage", "Pneumatic"],
  ["Proximity sensor loose, intermittent signal", "Re-fixed and realigned sensor, tightened bracket", "Sensor"],
  ["Timing belt worn and slipping", "Replaced timing belt, set tension", "Mechanical"],
  ["Contactor contacts pitted", "Replaced contactor, checked load current", "Electrical"],
  ["Air pressure dropped below 5 bar", "Drained condensate, cleaned filter, reset pressure switch", "Pneumatic"],
  ["Servo drive over-temperature alarm", "Cleaned cabinet filter, checked fan, reset drive", "Electrical"],
  ["Heater band open circuit", "Replaced heater band, checked thermocouple", "Electrical"],
  ["Operator loaded wrong fixture", "Corrected setup, briefed operator", "Operator error"],
  ["Bearing seized on roller", "Replaced bearing 6205, lubricated shaft", "Mechanical"],
  ["PLC input card fault", "Swapped input card from spares, restored program", "PLC / Controls"],
];

export async function buildDemoSnapshot(today: string = todayKey()): Promise<Snapshot> {
  const s = emptySnapshot();
  const now = nowIso();
  s.demo = true;
  s.settings.plantName = "Eaton (sample plant)";
  s.settings.siteCode = "DEMO";
  const stamp = { createdAt: now, updatedAt: now };
  const rand = rng(20261111);

  const lineSeeds: { code: string; name: string; area: string; shifts: Shift[] }[] = [
    { code: "L1", name: "Fuse assembly line 1", area: "Bussmann", shifts: ["A", "B"] },
    { code: "L2", name: "Fuse assembly line 2", area: "Bussmann", shifts: ["A", "B", "C"] },
    { code: "L3", name: "Moulding", area: "Bussmann", shifts: ["A", "B", "C"] },
    { code: "UT", name: "Utilities", area: "Plant", shifts: ["A", "B"] },
  ];
  const lines: Line[] = lineSeeds.map((l) => ({ id: newId(), ...l, active: true, ...stamp }));
  const lineId = (code: string): string => lines.find((l) => l.code === code)!.id;
  s.lines = lines;

  const users: User[] = [];
  for (const acc of DEMO_ACCOUNTS) {
    const { hash, salt } = await hashPassword(DEMO_PASSWORD);
    users.push({
      id: newId(),
      employeeId: acc.employeeId,
      name: acc.name,
      role: acc.role,
      lineIds: acc.lines.map(lineId),
      phone: "",
      email: "",
      skills: acc.role === "technician" ? pick(rand, ["Electrical, PLC", "Mechanical, pneumatics", "Hydraulics, moulding"]) : "",
      active: true,
      passwordHash: hash,
      passwordSalt: salt,
      mustChangePassword: false,
      failedAttempts: 0,
      lockedUntil: null,
      lastLoginAt: null,
      ...stamp,
    });
  }
  s.users = users;
  const userId = (emp: string): string => users.find((u) => u.employeeId === emp)!.id;
  const techs = users.filter((u) => u.role === "technician");
  const owner = userId("D-OWNER");
  const msup = userId("D-MSUP");
  const psup = userId("D-PSUP");

  const assets: Asset[] = ASSET_SEEDS.map((a) => ({
    id: newId(),
    assetNo: a.no,
    name: a.name,
    lineId: lineId(a.line),
    parentId: null,
    category: a.category,
    make: a.make,
    model: a.model,
    serialNo: `SN-${Math.floor(rand() * 900000 + 100000)}`,
    criticality: a.crit,
    status: "running",
    location: a.location,
    installDate: addDays(today, -Math.floor(rand() * 2500 + 365)),
    meterUnit: a.meterUnit,
    meterReading: a.meter,
    meterUpdatedAt: a.meterUnit ? now : null,
    specs: a.category === "Utility" ? [{ key: "Rated power", value: "37 kW" }] : [{ key: "Supply", value: "415 V 3 ph" }],
    notes: "",
    active: true,
    ...stamp,
  }));
  const assetId = (no: string): string => assets.find((a) => a.assetNo === no)!.id;
  for (const c of COMPONENT_SEEDS) {
    const parent = assets.find((a) => a.assetNo === c.parent)!;
    assets.push({
      id: newId(),
      assetNo: c.no,
      name: c.name,
      lineId: parent.lineId,
      parentId: parent.id,
      category: c.category,
      make: "",
      model: "",
      serialNo: "",
      criticality: parent.criticality,
      status: "running",
      location: parent.location,
      installDate: parent.installDate,
      meterUnit: "",
      meterReading: 0,
      meterUpdatedAt: null,
      specs: [],
      notes: "",
      active: true,
      ...stamp,
    });
  }
  s.assets = assets;
  s.sequences.asset = assets.length;

  const parts: Part[] = PART_SEEDS.map((p) => ({
    id: newId(),
    partNo: p.no,
    name: p.name,
    description: "",
    category: p.category,
    unit: p.unit,
    stock: p.stock,
    minStock: p.min,
    maxStock: p.max,
    location: p.location,
    unitCost: p.cost,
    supplier: p.supplier,
    leadTimeDays: p.lead,
    assetIds: p.assets.map(assetId),
    active: true,
    ...stamp,
  }));
  s.parts = parts;
  s.sequences.part = parts.length;
  const partId = (no: string): string => parts.find((p) => p.partNo === no)!.id;

  const txs: StockTransaction[] = parts.map((p) => ({
    id: newId(),
    partId: p.id,
    type: "receive",
    qty: p.stock + 2,
    unitCost: p.unitCost,
    workOrderId: null,
    userId: msup,
    at: atTime(addDays(today, -45), 10),
    note: "Opening stock",
  }));

  const plans: PMPlan[] = PLAN_SEEDS.map((p, idx) => {
    const asset = assets.find((a) => a.assetNo === p.asset)!;
    const nextDue = addDays(today, p.dueOffsetDays);
    const lastDone = p.trigger === "meter" ? null : addInterval(nextDue, -p.value, p.unit);
    const lastMeter = p.meter ? Math.max(0, asset.meterReading - Math.floor(p.meter * (p.trigger === "both" ? 0.6 : 0.85))) : null;
    return {
      id: newId(),
      code: p.code,
      name: p.name,
      description: `${p.name} for ${asset.assetNo} ${asset.name}.`,
      assetId: asset.id,
      trigger: p.trigger,
      intervalValue: p.value,
      intervalUnit: p.unit,
      meterInterval: p.meter,
      scheduleMode: idx % 3 === 0 ? "floating" : "fixed",
      leadDays: 7,
      lastDoneAt: lastDone,
      lastDoneMeter: lastMeter,
      nextDueAt: nextDue,
      nextDueMeter: lastMeter !== null && p.meter ? lastMeter + p.meter : null,
      estimatedHours: p.hours,
      priority: p.priority,
      assignedToUserId: p.tech ? userId(p.tech) : null,
      checklist: p.checklist,
      parts: p.parts.filter((x) => x.qty > 0).map((x) => ({ partId: partId(x.no), qty: x.qty })),
      active: true,
      ...stamp,
    };
  });
  s.pmPlans = plans;
  s.sequences.pm = plans.length;

  const workOrders: WorkOrder[] = [];
  const mainAssets = assets.filter((a) => a.parentId === null);
  // Weighted so two machines show up as bad actors on the dashboard.
  const weighted = [...mainAssets, assetId("FA-01"), assetId("FA-01"), assetId("AC-01"), assetId("IM-01")].map((x) => (typeof x === "string" ? assets.find((a) => a.id === x)! : x));

  // Historic breakdowns over the last ten weeks.
  for (let i = 0; i < 26; i++) {
    const asset = pick(rand, weighted);
    const dayKey = addDays(today, -Math.floor(2 + i * 2.6 + rand() * 2));
    const line = lines.find((l) => l.id === asset.lineId)!;
    const hour = line.shifts.includes("C") ? Math.floor(rand() * 24) : 6 + Math.floor(rand() * 16);
    const start = atTime(dayKey, hour, Math.floor(rand() * 60));
    const downtime = 25 + Math.floor(rand() * 220);
    const end = new Date(new Date(start).getTime() + downtime * 60_000).toISOString();
    const tech = pick(rand, techs);
    const [cause, action, code] = pick(rand, ROOT_CAUSES);
    const createdAt = new Date(new Date(start).getTime() + 5 * 60_000).toISOString();
    const wo = newWorkOrder(
      {
        woNo: allocateWoNo(s, new Date(start).getFullYear()),
        type: "breakdown",
        title: `${asset.name}: ${cause.split(",")[0].toLowerCase()}`,
        description: `Machine stopped. Operator reported: ${cause.toLowerCase()}.`,
        assetId: asset.id,
        lineId: asset.lineId,
        priority: priorityForBreakdown(asset.criticality),
        requestedByUserId: rand() < 0.6 ? psup : tech.id,
        assignedToUserIds: [tech.id],
        downtimeStart: start,
        shift: shiftForIso(start, s.settings.shifts),
        failureCode: code,
      },
      createdAt,
    );
    wo.id = newId();
    wo.startedAt = new Date(new Date(start).getTime() + 15 * 60_000).toISOString();
    wo.completedAt = end;
    wo.downtimeEnd = end;
    wo.downtimeMinutes = minutesBetween(start, end);
    wo.rootCause = cause;
    wo.actionTaken = action;
    wo.labor = [{ id: newId(), userId: tech.id, date: dayKey, hours: Math.round((downtime / 60) * 4) / 4 || 0.25, note: "" }];
    const closed = i > 1 && rand() < 0.8;
    wo.status = closed ? "closed" : "completed";
    if (closed) {
      wo.closedAt = new Date(new Date(end).getTime() + 3 * 3600_000).toISOString();
      wo.closedByUserId = msup;
      wo.handbackByUserId = psup;
      wo.handbackAt = new Date(new Date(end).getTime() + 20 * 60_000).toISOString();
    }
    wo.history.push(
      { at: wo.startedAt, userId: tech.id, from: "assigned", to: "in_progress", note: "" },
      { at: end, userId: tech.id, from: "in_progress", to: "completed", note: "" },
    );
    if (closed) wo.history.push({ at: wo.closedAt!, userId: msup, from: "completed", to: "closed", note: "" });
    // Parts used on about half of the breakdowns.
    if (rand() < 0.5) {
      const candidates = parts.filter((p) => p.assetIds.includes(asset.id) || p.partNo === "SP-1013");
      const part = pick(rand, candidates.length ? candidates : parts);
      const qty = 1;
      wo.partsUsed.push({ id: newId(), partId: part.id, qty, unitCost: part.unitCost });
      txs.push({ id: newId(), partId: part.id, type: "issue", qty: -qty, unitCost: part.unitCost, workOrderId: wo.id, userId: tech.id, at: end, note: `Issued to ${wo.woNo}` });
    }
    wo.updatedAt = wo.closedAt ?? end;
    workOrders.push(wo);
  }

  // Open breakdowns right now.
  const openSpecs: { asset: string; status: WorkOrder["status"]; minutesAgo: number; tech: string | null; title: string }[] = [
    { asset: "FA-02", status: "in_progress", minutesAgo: 95, tech: "D-TECH2", title: "Fuse assembly machine 2: indexing table not homing" },
    { asset: "CP-01", status: "open", minutesAgo: 25, tech: null, title: "Crimping press 1: light curtain fault, press will not cycle" },
    { asset: "CH-01", status: "on_hold", minutesAgo: 60 * 26, tech: "D-TECH3", title: "Chiller 1: low refrigerant pressure alarm, waiting for gas" },
  ];
  for (const spec of openSpecs) {
    const asset = assets.find((a) => a.assetNo === spec.asset)!;
    const start = new Date(Date.now() - spec.minutesAgo * 60_000).toISOString();
    const wo = newWorkOrder(
      {
        woNo: allocateWoNo(s),
        type: "breakdown",
        title: spec.title,
        description: "Reported by production. Machine stopped.",
        assetId: asset.id,
        lineId: asset.lineId,
        priority: priorityForBreakdown(asset.criticality),
        requestedByUserId: psup,
        assignedToUserIds: spec.tech ? [userId(spec.tech)] : [],
        downtimeStart: start,
        shift: shiftForIso(start, s.settings.shifts),
        status: spec.status,
      },
      start,
    );
    wo.id = newId();
    if (spec.status !== "open") {
      wo.startedAt = new Date(new Date(start).getTime() + 10 * 60_000).toISOString();
      wo.history.push({ at: wo.startedAt, userId: wo.assignedToUserIds[0], from: "assigned", to: "in_progress", note: "" });
      if (spec.status === "on_hold") {
        wo.history.push({ at: new Date(new Date(start).getTime() + 90 * 60_000).toISOString(), userId: wo.assignedToUserIds[0], from: "in_progress", to: "on_hold", note: "Refrigerant gas on order" });
        wo.comments.push({ id: newId(), userId: msup, text: "Gas cylinder expected tomorrow morning. Keep moulding on IM-02 only.", at: new Date(new Date(start).getTime() + 95 * 60_000).toISOString() });
      }
    }
    asset.status = "down";
    workOrders.push(wo);
  }

  // PM history: weekly and monthly plans completed over the past weeks, mostly on time.
  for (const plan of plans) {
    if (plan.trigger === "meter") continue;
    const asset = assets.find((a) => a.id === plan.assetId)!;
    const cycles = plan.intervalUnit === "week" ? 8 : plan.intervalUnit === "month" ? 2 : 0;
    for (let c = cycles; c >= 1; c--) {
      const due = addInterval(plan.nextDueAt, -c * plan.intervalValue, plan.intervalUnit);
      if (due > today) continue;
      const late = rand() < 0.18;
      const doneKey = addDays(due, late ? 1 + Math.floor(rand() * 4) : -Math.floor(rand() * 2));
      if (doneKey > today) continue;
      const doneAt = atTime(doneKey, 9 + Math.floor(rand() * 6));
      const tech = plan.assignedToUserId ?? pick(rand, techs).id;
      const wo = newWorkOrder(
        {
          woNo: allocateWoNo(s, new Date(doneAt).getFullYear()),
          type: "pm",
          title: `${plan.code} · ${plan.name}`,
          description: plan.description,
          assetId: asset.id,
          lineId: asset.lineId,
          priority: plan.priority,
          requestedByUserId: msup,
          assignedToUserIds: [tech],
          dueDate: due,
          scheduledDate: due,
          estimatedHours: plan.estimatedHours,
          checklist: plan.checklist.map((text) => ({ id: newId(), text, done: true, doneByUserId: tech, doneAt })),
          pmPlanId: plan.id,
        },
        atTime(addDays(due, -plan.leadDays), 8),
      );
      wo.id = newId();
      wo.status = "closed";
      wo.startedAt = atTime(doneKey, 8);
      wo.completedAt = doneAt;
      wo.closedAt = doneAt;
      wo.closedByUserId = msup;
      wo.actionTaken = "Checklist completed, no abnormality.";
      wo.labor = [{ id: newId(), userId: tech, date: doneKey, hours: plan.estimatedHours, note: "" }];
      wo.history.push({ at: doneAt, userId: tech, from: "in_progress", to: "completed", note: "" }, { at: doneAt, userId: msup, from: "completed", to: "closed", note: "" });
      wo.updatedAt = doneAt;
      workOrders.push(wo);
    }
  }

  // One PM work order that was generated and is now overdue, one due this week.
  const pm5 = plans.find((p) => p.code === "PM-005")!;
  {
    const asset = assets.find((a) => a.id === pm5.assetId)!;
    const wo = newWorkOrder(
      {
        woNo: allocateWoNo(s),
        type: "pm",
        title: `${pm5.code} · ${pm5.name}`,
        description: pm5.description,
        assetId: asset.id,
        lineId: asset.lineId,
        priority: pm5.priority,
        requestedByUserId: msup,
        assignedToUserIds: pm5.assignedToUserId ? [pm5.assignedToUserId] : [],
        dueDate: pm5.nextDueAt,
        scheduledDate: pm5.nextDueAt,
        estimatedHours: pm5.estimatedHours,
        checklist: pm5.checklist.map((text) => ({ id: newId(), text, done: false, doneByUserId: null, doneAt: null })),
        pmPlanId: pm5.id,
      },
      atTime(addDays(pm5.nextDueAt, -pm5.leadDays), 8),
    );
    wo.id = newId();
    workOrders.push(wo);
  }

  // Other work order types.
  const others: { type: WorkOrder["type"]; title: string; asset: string; status: WorkOrder["status"]; daysAgo: number; due: number; tech: string | null; priority: Priority }[] = [
    { type: "improvement", title: "Add poka-yoke sensor on fixture loading", asset: "FA-01", status: "assigned", daysAgo: 6, due: 10, tech: "D-TECH1", priority: "low" },
    { type: "safety", title: "Replace damaged E-stop guard on press", asset: "CP-02", status: "in_progress", daysAgo: 3, due: 1, tech: "D-TECH2", priority: "high" },
    { type: "inspection", title: "Thermography of main LT panel", asset: "DG-01", status: "open", daysAgo: 1, due: 14, tech: null, priority: "medium" },
    { type: "corrective", title: "Repair leaking air dryer drain", asset: "AC-01-DRY", status: "closed", daysAgo: 12, due: -8, tech: "D-TECH1", priority: "medium" },
    { type: "project", title: "Install energy meter on moulding hall feeder", asset: "IM-01", status: "on_hold", daysAgo: 20, due: 30, tech: "D-TECH3", priority: "low" },
  ];
  for (const o of others) {
    const asset = assets.find((a) => a.assetNo === o.asset)!;
    const createdAt = atTime(addDays(today, -o.daysAgo), 10);
    const wo = newWorkOrder(
      {
        woNo: allocateWoNo(s),
        type: o.type,
        title: o.title,
        description: "",
        assetId: asset.id,
        lineId: asset.lineId,
        priority: o.priority,
        requestedByUserId: o.type === "safety" ? psup : msup,
        assignedToUserIds: o.tech ? [userId(o.tech)] : [],
        dueDate: addDays(today, o.due),
        status: o.status,
        estimatedHours: 2,
      },
      createdAt,
    );
    wo.id = newId();
    if (o.status === "closed") {
      wo.startedAt = atTime(addDays(today, -o.daysAgo + 1), 9);
      wo.completedAt = atTime(addDays(today, -o.daysAgo + 2), 15);
      wo.closedAt = wo.completedAt;
      wo.closedByUserId = msup;
      wo.actionTaken = "Drain valve replaced and tested.";
      wo.labor = [{ id: newId(), userId: wo.assignedToUserIds[0], date: addDays(today, -o.daysAgo + 2), hours: 1.5, note: "" }];
    }
    workOrders.push(wo);
  }

  workOrders.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  s.workOrders = workOrders;
  s.stockTransactions = txs.sort((a, b) => a.at.localeCompare(b.at));

  // Keep plan cycles consistent with the generated history for the floating plans.
  for (const plan of plans) {
    if (plan.scheduleMode === "floating" && plan.lastDoneAt) {
      const copy = { ...plan, scheduleMode: "fixed" as const };
      completePlanCycle(copy, plan.lastDoneAt, null);
    }
  }

  s.audit.push({ id: newId(), at: now, userId: owner, entity: "system", entityId: "seed", action: "seed", summary: "Sample data created" });
  s.updatedAt = now;
  return s;
}
