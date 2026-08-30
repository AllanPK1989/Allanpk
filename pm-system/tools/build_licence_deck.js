/**
 * build_licence_deck.js
 * ---------------------
 * Generates docs/POWERAPPS_LICENCE_CASE.pptx - the business case for requesting a
 * Power Apps licence so the PM system can move to Phase 2.
 *
 * Every figure in the deck comes from the twelve months of plant data already in
 * the system. Nothing is estimated except the two numbers the plant owns: the cost
 * of an hour of downtime and the current licence rate. Both are presented as inputs
 * for the reader to fill, not as claims.
 *
 *     node tools/build_licence_deck.js
 */

const pptxgen = require("pptxgenjs");

// Palette - the same one the dashboard, the SharePoint lists and the app use, so
// the deck looks like part of the system rather than a document about it.
const NAVY = "0C3549";
const NAVY_2 = "16455C";
const AMBER = "F0A202";
const BLUE = "2E86AB";
const GREEN = "44C088";
const RED = "ED7373";
const LIGHT = "F5F7F8";
const WHITE = "FFFFFF";
const TEXT = "1F2933";
const MUTED = "7B8794";
const PALE = "B9CBD4";

const HEAD = "Cambria";
const BODY = "Calibri";

const W = 13.3, H = 7.5, M = 0.65;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Maintenance Engineering";
pres.company = "EPQPL Pondicherry";
pres.title = "Power Apps licence request - PM system Phase 2";

// ---------------------------------------------------------------- helpers
function darkSlide() {
  const s = pres.addSlide();
  s.background = { color: NAVY };
  return s;
}

function lightSlide(title, kicker) {
  const s = pres.addSlide();
  s.background = { color: WHITE };
  s.addText(title, {
    x: M, y: 0.45, w: W - 2 * M, h: 0.75,
    fontSize: 32, bold: true, color: NAVY, fontFace: HEAD,
    isTextBox: true, margin: 0,
  });
  if (kicker) {
    s.addText(kicker, {
      x: M, y: 1.18, w: W - 2 * M, h: 0.4,
      fontSize: 14, color: MUTED, fontFace: BODY, italic: true,
      isTextBox: true, margin: 0,
    });
  }
  return s;
}

/** A number in a filled circle - the deck's one repeated motif. */
function numberBadge(slide, n, x, y, d, fill, fg) {
  slide.addShape(pres.ShapeType.ellipse, {
    x, y, w: d, h: d, fill: { color: fill || NAVY },
    line: { type: "none" },
  });
  slide.addText(String(n), {
    x, y, w: d, h: d, align: "center", valign: "middle",
    fontSize: d * 26, bold: true, color: fg || WHITE, fontFace: HEAD,
    isTextBox: true, margin: 0,
  });
}

/** Big figure with a label under it. */
function statBlock(slide, x, y, w, value, label, sub, colour) {
  slide.addText(value, {
    x, y, w, h: 0.95, fontSize: 44, bold: true,
    color: colour || NAVY, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  slide.addText(label, {
    x, y: y + 0.92, w, h: 0.32, fontSize: 13, bold: true,
    color: TEXT, fontFace: BODY, isTextBox: true, margin: 0,
  });
  if (sub) {
    slide.addText(sub, {
      x, y: y + 1.22, w, h: 0.6, fontSize: 11, color: MUTED,
      fontFace: BODY, isTextBox: true, margin: 0,
    });
  }
}

/** Tinted card. No edge stripes - a background tint and a shadow instead. */
function card(slide, x, y, w, h, fill) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.06,
    fill: { color: fill || LIGHT }, line: { type: "none" },
    shadow: { type: "outer", angle: 90, blur: 8, offset: 1, color: NAVY, opacity: 0.07 },
  });
}

function footer(slide, text) {
  slide.addText(text, {
    x: M, y: H - 0.55, w: W - 2 * M, h: 0.3,
    fontSize: 9, color: MUTED, fontFace: BODY, isTextBox: true, margin: 0,
  });
}

// ================================================================ 1. Title
{
  const s = darkSlide();
  s.addText("Power Apps licence request", {
    x: M, y: 2.25, w: 10.5, h: 0.9,
    fontSize: 46, bold: true, color: WHITE, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText("Preventive maintenance system  ·  Phase 2", {
    x: M, y: 3.18, w: 10.5, h: 0.5,
    fontSize: 22, color: AMBER, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText(
    "The PM system is live and working without it. This asks for the licence that closes " +
    "the four gaps the current front end cannot, and shows what those gaps cost.",
    { x: M, y: 3.95, w: 8.6, h: 0.9, fontSize: 15, color: PALE, fontFace: BODY, isTextBox: true, margin: 0, lineSpacingMultiple: 1.25 }
  );
  s.addText("Eaton Power Quality Pvt Ltd  ·  Pondicherry  ·  Maintenance Engineering", {
    x: M, y: H - 0.95, w: 10, h: 0.35,
    fontSize: 11, color: MUTED, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addNotes(
    "Opening line: we are not asking for money to build the system. The system is built and it works. " +
    "We are asking for a licence that closes four specific gaps, and here is what those gaps cost us."
  );
}

// ================================================================ 2. Where we are
{
  const s = lightSlide("The system is already live", "Delivered on Microsoft 365 E3. No additional licence was purchased.");
  const cols = [
    ["16", "SharePoint lists", "Every PM record, indexed and versioned"],
    ["11", "Automated flows", "Trigger, reset, escalation, digest"],
    ["9", "Dashboard pages", "94 measures, refreshed twice daily"],
    ["30", "QR-tagged machines", "Scan opens that machine's hub"],
  ];
  const cw = (W - 2 * M - 3 * 0.3) / 4;
  cols.forEach((c, i) => {
    const x = M + i * (cw + 0.3);
    card(s, x, 1.85, cw, 2.05);
    statBlock(s, x + 0.28, 2.1, cw - 0.56, c[0], c[1], c[2]);
  });

  s.addText("What it does today, unattended", {
    x: M, y: 4.25, w: W - 2 * M, h: 0.4,
    fontSize: 17, bold: true, color: NAVY, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  const items = [
    "Adds each month's standard hours to every cell's running counter, prorated by working days when a PM reset falls mid-month",
    "Raises a work order the morning a cell reaches 4,000 hours, or six months, whichever comes first",
    "Resets the counter only when every machine in the cell is complete - never on a partial cell",
    "Escalates a safety-critical finding immediately and blocks the cell from closing behind it",
  ];
  s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })), {
    x: M + 0.05, y: 4.68, w: W - 2 * M - 0.1, h: 1.65,
    fontSize: 13, color: TEXT, fontFace: BODY, isTextBox: true, margin: 0, paraSpaceAfter: 6,
  });
  footer(s, "Figures from the system as built. Twelve months of plant data loaded and verified.");
  s.addNotes("Establish credibility before asking for anything. The system works, it cost no extra licence, and it runs unattended.");
}

// ================================================================ 3. The gap
{
  const s = lightSlide("Four things the current front end cannot do",
    "Microsoft Forms is a form. These are not form problems.");
  const gaps = [
    ["Work offline",
     "Where the floor has no reliable signal a technician either walks to the office to submit, or writes on paper and re-keys later. Re-keyed data arrives late, and some of it never arrives at all."],
    ["Enforce one check at a time",
     "Six checks on one screen can be tapped straight down the OK column. The acceptance standard - the actual limit - sits on a page the technician has to go and find."],
    ["Scan inside the workflow",
     "The camera app opens a browser, which opens a form. Three context switches per machine, and any one of them can drop the pre-filled machine ID."],
    ["Show the technician what he needs to know",
     "Current stock before he requests a part. Whether his machine is the last one in the cell. Forms shows a blank page and asks him to type."],
  ];
  const rowH = 1.06;
  gaps.forEach((g, i) => {
    const y = 1.78 + i * (rowH + 0.16);
    card(s, M, y, W - 2 * M, rowH);
    numberBadge(s, i + 1, M + 0.28, y + 0.24, 0.58, NAVY);
    s.addText(g[0], {
      x: M + 1.05, y: y + 0.16, w: 3.5, h: 0.35,
      fontSize: 15, bold: true, color: NAVY, fontFace: HEAD, isTextBox: true, margin: 0,
    });
    s.addText(g[1], {
      x: M + 4.7, y: y + 0.14, w: W - 2 * M - 5.0, h: 0.8,
      fontSize: 12, color: TEXT, fontFace: BODY, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
    });
  });
  footer(s, "None of these are fixed by writing a better form. They need an application.");
  s.addNotes("Be specific. A vague 'better user experience' request gets declined. Four named gaps, each with a consequence.");
}

// ================================================================ 4. What it costs
{
  const s = lightSlide("What the gap costs, measured",
    "Twelve months of this plant's own breakdown data - not an industry benchmark.");

  card(s, M, 1.8, 4.35, 3.5, NAVY);
  s.addText("34.4", {
    x: M + 0.35, y: 2.15, w: 3.7, h: 1.15,
    fontSize: 68, bold: true, color: AMBER, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText("hours of production lost", {
    x: M + 0.35, y: 3.28, w: 3.7, h: 0.35,
    fontSize: 16, bold: true, color: WHITE, fontFace: BODY, isTextBox: true, margin: 0,
  });
  s.addText(
    "to breakdowns that happened within seven days of a completed PM on that same cell.\n\n" +
    "9 of 88 breakdowns. 11.5% of all downtime, on machines we had just maintained.",
    { x: M + 0.35, y: 3.72, w: 3.7, h: 1.35, fontSize: 12.5, color: PALE, fontFace: BODY, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 }
  );

  s.addChart(pres.ChartType.doughnut, [{
    name: "Annual downtime",
    labels: ["Within 7 days of a PM", "All other causes"],
    values: [34.4, 265.1],
  }], {
    x: 5.35, y: 1.75, w: 3.7, h: 3.6,
    chartColors: [AMBER, "D9E2E6"],
    holeSize: 58,
    showLegend: true, legendPos: "b", legendFontSize: 11, legendColor: TEXT,
    showValue: true, dataLabelPosition: "bestFit", dataLabelFontSize: 12,
    dataLabelColor: NAVY, dataLabelFormatCode: '0.0"h"',
    showTitle: true, title: "Annual production loss, 299.5 h",
    titleFontSize: 13, titleColor: NAVY,
  });

  card(s, 9.35, 1.8, W - M - 9.35, 3.5);
  s.addText("Why this number is the right one", {
    x: 9.6, y: 2.0, w: 2.95, h: 0.35,
    fontSize: 14, bold: true, color: NAVY, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText(
    "A breakdown days after a PM means the PM did not find what was there.\n\n" +
    "That is either a check performed too fast to see anything, or a reading nobody wrote down.\n\n" +
    "Both are execution problems at the point of capture - exactly where the four gaps are.",
    { x: 9.6, y: 2.45, w: 2.95, h: 2.6, fontSize: 11.5, color: TEXT, fontFace: BODY, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 }
  );

  s.addText(
    "Compliance is 89.6% and on-time is 48.8%. Neither number would tell you any of this. " +
    "A PM programme can be fully compliant and still not be working.",
    { x: M, y: 5.55, w: W - 2 * M, h: 0.6, fontSize: 13.5, italic: true, color: NAVY, fontFace: BODY, isTextBox: true, margin: 0 }
  );
  footer(s, "Source: Breakdown_Log and PM_WorkOrder, 12 months. Measure definition and verification in docs/ASSUMPTIONS.md.");
  s.addNotes("This is the slide that carries the argument. 34.4 hours is measured from our own data, not estimated.");
}

// ================================================================ 5. Where it concentrates
{
  const s = lightSlide("It is concentrated, not spread",
    "Four of eight cells carry the whole of it. Those four are the pilot.");

  s.addChart(pres.ChartType.bar, [{
    name: "Hours lost within 7 days of a PM",
    labels: ["Curing / Autoclave", "Testing & Calibration", "Cap Fitting", "Assembly NH", "Element Welding", "Sand Filling", "Element Punching", "Marking & Packing"],
    values: [10.2, 9.0, 8.4, 3.0, 2.1, 1.6, 0, 0],
  }], {
    x: M, y: 1.85, w: 7.55, h: 4.0,
    barDir: "bar", chartColors: [AMBER],
    showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 11,
    dataLabelColor: NAVY, dataLabelFormatCode: '0.0"h"',
    showLegend: false,
    catAxisLabelColor: TEXT, catAxisLabelFontSize: 11,
    valAxisLabelColor: MUTED, valAxisLabelFontSize: 10,
    valGridLine: { color: "EDF1F3", size: 1 },
    catGridLine: { style: "none" },
    showTitle: true, title: "Production hours lost to post-PM breakdowns, by cell",
    titleFontSize: 13, titleColor: NAVY,
    barGapWidthPct: 45,
  });

  const notes = [
    ["4 cells", "carry 30.6 of the 34.4 hours", AMBER],
    ["15 machines", "in those four cells", NAVY],
    ["6 technicians", "would need a licence", NAVY],
  ];
  notes.forEach((n, i) => {
    const y = 2.0 + i * 1.28;
    statBlock(s, 8.5, y, 4.0, n[0], n[1], null, n[2]);
  });
  s.addText(
    "A pilot on those four cells tests the case before the plant commits to all eight.",
    { x: 8.5, y: 5.85, w: 4.0, h: 0.5, fontSize: 12, italic: true, color: NAVY, fontFace: BODY, isTextBox: true, margin: 0 }
  );
  footer(s, "Two cells lost nothing to post-PM breakdowns in twelve months. Whatever they do differently is worth copying either way.");
  s.addNotes("Pre-empt 'this is a big rollout'. It is four cells and six people. It can be piloted and reversed.");
}

// ================================================================ 6. Before / after
{
  const s = lightSlide("What changes at the machine", "Same data, same lists, same flows. Only the capture changes.");

  const colW = (W - 2 * M - 0.4) / 2;
  card(s, M, 1.8, colW, 4.0, LIGHT);
  card(s, M + colW + 0.4, 1.8, colW, 4.0, "EAF4F8");

  s.addText("Today  ·  Microsoft Forms", {
    x: M + 0.3, y: 2.0, w: colW - 0.6, h: 0.4,
    fontSize: 15, bold: true, color: MUTED, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText("Phase 2  ·  Canvas app", {
    x: M + colW + 0.7, y: 2.0, w: colW - 0.6, h: 0.4,
    fontSize: 15, bold: true, color: BLUE, fontFace: HEAD, isTextBox: true, margin: 0,
  });

  const before = [
    "Camera app opens a browser, which opens a form",
    "Six checks on one screen, tappable straight down the OK column",
    "Acceptance standard on a page nobody opens",
    "No signal means paper, then re-keying",
    "Requests a part without seeing the stock",
    "No idea his machine was the last in the cell",
  ];
  const after = [
    "Scanner inside the app, straight to the machine",
    "One check at a time, cannot skip an unanswered one",
    "Acceptance standard on screen with the check",
    "Captured offline, sent when back in range",
    "Current stock, minimum and lead time shown first",
    "Told when his machine closed the cell",
  ];
  s.addText(before.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < before.length - 1 } })), {
    x: M + 0.35, y: 2.5, w: colW - 0.7, h: 3.1,
    fontSize: 12.5, color: TEXT, fontFace: BODY, isTextBox: true, margin: 0, paraSpaceAfter: 8,
  });
  s.addText(after.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < after.length - 1 } })), {
    x: M + colW + 0.75, y: 2.5, w: colW - 0.7, h: 3.1,
    fontSize: 12.5, color: TEXT, fontFace: BODY, isTextBox: true, margin: 0, paraSpaceAfter: 8,
  });

  s.addText(
    "The lists, the eleven flows and the dashboard are unchanged. The app is an alternative " +
    "front end over the same data - which is why Forms stays available as the fallback.",
    { x: M, y: 6.0, w: W - 2 * M, h: 0.55, fontSize: 12.5, italic: true, color: NAVY, fontFace: BODY, isTextBox: true, margin: 0 }
  );
  footer(s, "Full screen-by-screen specification already written: powerapps/CANVAS_APP_BUILD.md");
  s.addNotes("The build is already specified. This is not a discovery project - the risk is low and the estimate is real.");
}

// ================================================================ 7. Cost and break-even
{
  const s = lightSlide("What it costs, and what it has to prevent",
    "Two numbers the plant owns. Fill them in and the decision makes itself.");

  s.addText("6 technicians + 2 supervisors  =  8 licences", {
    x: M, y: 1.75, w: 6.0, h: 0.4,
    fontSize: 15, bold: true, color: NAVY, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText(
    "Standard connectors only - SharePoint and Office 365 Users. No Dataverse, no premium " +
    "connector, no custom connector.",
    { x: M, y: 2.15, w: 6.0, h: 0.6, fontSize: 12, color: TEXT, fontFace: BODY, isTextBox: true, margin: 0 }
  );

  const rows = [
    [{ text: "Licence rate", options: { bold: true } },
     { text: "Annual, 8 users", options: { bold: true } },
     { text: "Break-even at\n₹5,000/h", options: { bold: true } },
     { text: "Break-even at\n₹10,000/h", options: { bold: true } },
     { text: "Break-even at\n₹20,000/h", options: { bold: true } }],
    ["₹500 / user / mo", "₹48,000", "9.6 h  (28%)", "4.8 h  (14%)", "2.4 h  (7%)"],
    ["₹1,000 / user / mo", "₹96,000", "19.2 h  (56%)", "9.6 h  (28%)", "4.8 h  (14%)"],
    ["₹1,500 / user / mo", "₹144,000", "28.8 h  (84%)", "14.4 h  (42%)", "7.2 h  (21%)"],
    ["₹2,000 / user / mo", "₹192,000", "38.4 h  (112%)", "19.2 h  (56%)", "9.6 h  (28%)"],
  ];
  s.addTable(rows, {
    x: M, y: 3.0, w: W - 2 * M, colW: [2.6, 2.2, 2.4, 2.4, 2.4],
    rowH: 0.42,
    fontSize: 12, fontFace: BODY, color: TEXT,
    border: { type: "solid", color: "E1E8EB", pt: 1 },
    fill: { color: WHITE },
    align: "left", valign: "middle",
    margin: 0.08,
  });

  s.addText(
    "Read a row: at ₹1,500 per user per month and ₹10,000 an hour of downtime, the licence " +
    "pays for itself if it prevents 14.4 hours a year — 42% of the 34.4 hours currently lost " +
    "to breakdowns that follow a PM.",
    { x: M, y: 5.55, w: W - 2 * M, h: 0.75, fontSize: 13, color: NAVY, fontFace: BODY, isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 }
  );
  footer(s, "Licence rates are illustrative — confirm current pricing with your Microsoft partner. Downtime cost per hour is the plant's own figure.");
  s.addNotes(
    "Do not assert a price. The grid lets them find their own row. The percentage column is the honest test: " +
    "is it plausible that better capture prevents that share of post-PM breakdowns?"
  );
}

// ================================================================ 8. The ask
{
  const s = darkSlide();
  s.addText("The ask", {
    x: M, y: 0.7, w: 8, h: 0.7,
    fontSize: 36, bold: true, color: WHITE, fontFace: HEAD, isTextBox: true, margin: 0,
  });
  s.addText("Eight Power Apps licences, and four cells to prove it on.", {
    x: M, y: 1.42, w: 9, h: 0.4,
    fontSize: 16, color: AMBER, fontFace: BODY, isTextBox: true, margin: 0,
  });

  const asks = [
    ["1", "Approve 8 licences", "6 technicians, 2 supervisors. Standard connectors only."],
    ["2", "Pilot on 4 cells", "Curing, Testing, Cap Fitting, Assembly - the four carrying 30.6 of the 34.4 hours (89%)."],
    ["3", "Review after 6 months", "Against post-PM breakdown hours on those four cells versus the other four."],
  ];
  asks.forEach((a, i) => {
    const y = 2.25 + i * 1.15;
    numberBadge(s, a[0], M, y, 0.62, AMBER, NAVY);
    s.addText(a[1], {
      x: M + 0.9, y: y + 0.02, w: 3.6, h: 0.4,
      fontSize: 17, bold: true, color: WHITE, fontFace: HEAD, isTextBox: true, margin: 0,
    });
    s.addText(a[2], {
      x: M + 4.6, y: y + 0.03, w: 7.4, h: 0.75,
      fontSize: 13, color: PALE, fontFace: BODY, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
    });
  });

  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: 5.85, w: W - 2 * M, h: 0.95, rectRadius: 0.06,
    fill: { color: NAVY_2 }, line: { type: "none" },
  });
  s.addText(
    "If the answer is no, nothing breaks. The system stays live on Forms, and this stays on the shelf " +
    "as a costed option with the evidence attached.",
    { x: M + 0.35, y: 6.05, w: W - 2 * M - 0.7, h: 0.6, fontSize: 13.5, color: PALE, fontFace: BODY, isTextBox: true, margin: 0, lineSpacingMultiple: 1.15 }
  );
  s.addNotes(
    "Close by removing the pressure. A request that survives a 'no' without drama is easier to say yes to. " +
    "Offer the 6-month review as the reversal point."
  );
}

// ================================================================ 9. Sources
{
  const s = lightSlide("Where every number came from",
    "So anyone can check them rather than take them on trust.");
  const rows = [
    [{ text: "Figure", options: { bold: true } },
     { text: "Value", options: { bold: true } },
     { text: "Source", options: { bold: true } }],
    ["Annual production loss", "299.5 h", "Breakdown_Log, sum of Production_Loss_Min, 12 months"],
    ["Breakdowns within 7 days of a PM", "9 of 88", "Breakdown_Log paired to completed PM_WorkOrder by cell and date"],
    ["Downtime from those breakdowns", "34.4 h  (11.5%)", "Same 9 rows, sum of Production_Loss_Min"],
    ["Concentration in four cells", "30.6 h  (89%)", "Curing 10.2, Testing 9.0, Cap Fitting 8.4, Assembly 3.0"],
    ["PM compliance / on-time", "89.6%  /  48.8%", "43 of 48 completed; 21 of 43 by the committed date"],
    ["Machines in the pilot cells", "15", "Machine_Master, Active = Yes, those four cells"],
    ["Technicians", "6", "Technician_Master, Active = Yes"],
  ];
  s.addTable(rows, {
    x: M, y: 1.85, w: W - 2 * M, colW: [3.5, 2.3, 6.2],
    rowH: 0.44, fontSize: 11.5, fontFace: BODY, color: TEXT,
    border: { type: "solid", color: "E1E8EB", pt: 1 },
    fill: { color: WHITE }, align: "left", valign: "middle", margin: 0.08,
  });
  s.addText(
    "Reproduce all of it:   python tools/verify_measures.py --asof 2026-08-30",
    { x: M, y: 5.4, w: W - 2 * M, h: 0.4, fontSize: 13, bold: true, color: NAVY,
      fontFace: "Courier New", isTextBox: true, margin: 0 }
  );
  s.addText(
    "Every measure is recomputed there in plain Python, independently of the dashboard, " +
    "so the two can be compared rather than one trusted. Licence rates on the previous " +
    "slide are the only illustrative figures in this deck - confirm those with your " +
    "Microsoft partner, and the downtime cost per hour with Finance.",
    { x: M, y: 5.85, w: W - 2 * M, h: 0.9, fontSize: 12, color: MUTED, fontFace: BODY,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.2 }
  );
  footer(s, "Twelve months of plant data. 0 integrity errors on load; every figure re-derived from the source lists.");
  s.addNotes("Offer the checkability up front. It is the difference between a number someone believes and a number someone can verify.");
}

pres.writeFile({ fileName: "docs/POWERAPPS_LICENCE_CASE.pptx" })
  .then(f => console.log("wrote " + f));
