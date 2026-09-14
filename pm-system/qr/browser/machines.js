// ---------------------------------------------------------------------------
// The machines the stickers are printed for.
//
// Generated from sharepoint/data/Machine_Master.csv - active machines only, in
// the order they are printed. If you add or retire a machine, edit this list
// AND Machine_Master, or the sticker sheet and the system disagree about what
// is on the shop floor.
// ---------------------------------------------------------------------------

const MACHINES = [
  {"id": "MC-01-001", "name": "Power Press 25T", "cell": "CELL-01", "loc": "Bay-6"},
  {"id": "MC-01-002", "name": "Strip Feeder", "cell": "CELL-01", "loc": "Bay-1"},
  {"id": "MC-01-003", "name": "Deburring Unit", "cell": "CELL-01", "loc": "Bay-5"},
  {"id": "MC-01-004", "name": "Coil Decoiler", "cell": "CELL-01", "loc": "Bay-1"},
  {"id": "MC-02-005", "name": "Spot Welding Machine", "cell": "CELL-02", "loc": "Bay-1"},
  {"id": "MC-02-006", "name": "Element Bending Unit", "cell": "CELL-02", "loc": "Bay-1"},
  {"id": "MC-02-007", "name": "Silver Plating Line", "cell": "CELL-02", "loc": "Bay-6"},
  {"id": "MC-02-008", "name": "Vision Inspection", "cell": "CELL-02", "loc": "Bay-6"},
  {"id": "MC-03-009", "name": "Cap Fitting Press", "cell": "CELL-03", "loc": "Bay-2"},
  {"id": "MC-03-010", "name": "Bowl Feeder Unit", "cell": "CELL-03", "loc": "Bay-6"},
  {"id": "MC-03-011", "name": "Riveting Station", "cell": "CELL-03", "loc": "Bay-4"},
  {"id": "MC-03-012", "name": "Contact Resistance Tester", "cell": "CELL-03", "loc": "Bay-6"},
  {"id": "MC-04-013", "name": "Sand Filling Machine - CAV", "cell": "CELL-04", "loc": "Bay-2"},
  {"id": "MC-04-014", "name": "Rotary Vibrator Table", "cell": "CELL-04", "loc": "Bay-6"},
  {"id": "MC-04-015", "name": "Sand Dryer Oven", "cell": "CELL-04", "loc": "Bay-6"},
  {"id": "MC-04-016", "name": "Dust Extraction Unit", "cell": "CELL-04", "loc": "Bay-2"},
  {"id": "MC-05-017", "name": "Curing Autoclave A", "cell": "CELL-05", "loc": "Bay-6"},
  {"id": "MC-05-018", "name": "Curing Autoclave B", "cell": "CELL-05", "loc": "Bay-4"},
  {"id": "MC-05-019", "name": "Induction Steam Generator", "cell": "CELL-05", "loc": "Bay-6"},
  {"id": "MC-05-020", "name": "Condensate Recovery Pump", "cell": "CELL-05", "loc": "Bay-2"},
  {"id": "MC-06-021", "name": "Body Assembly Station", "cell": "CELL-06", "loc": "Bay-6"},
  {"id": "MC-06-022", "name": "Hydro-Pneumatic Press", "cell": "CELL-06", "loc": "Bay-5"},
  {"id": "MC-06-023", "name": "Torque Tightening Station", "cell": "CELL-06", "loc": "Bay-3"},
  {"id": "MC-06-024", "name": "Leak Test Rig", "cell": "CELL-06", "loc": "Bay-1"},
  {"id": "MC-07-025", "name": "HIOKI Resistance Tester", "cell": "CELL-07", "loc": "Bay-5"},
  {"id": "MC-07-026", "name": "Hi-Pot Test Bench", "cell": "CELL-07", "loc": "Bay-4"},
  {"id": "MC-07-027", "name": "Calibration Chamber", "cell": "CELL-07", "loc": "Bay-2"},
  {"id": "MC-08-028", "name": "Fiber Laser Marker", "cell": "CELL-08", "loc": "Bay-1"},
  {"id": "MC-08-029", "name": "SATO Label Printer", "cell": "CELL-08", "loc": "Bay-1"},
  {"id": "MC-08-030", "name": "Carton Sealing Machine", "cell": "CELL-08", "loc": "Bay-5"}
];

// The number of active machines this sheet was generated for. If you add or
// retire a machine, change BOTH the list above and this number - the page
// compares them and refuses to print if they disagree, which is what turns a
// line accidentally deleted from the list into a message instead of a missing
// sticker nobody notices.
const MACHINE_COUNT_EXPECTED = 30;
