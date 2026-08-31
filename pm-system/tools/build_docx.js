/**
 * build_docx.js
 * -------------
 * Converts one of the project's markdown documents into a styled Word file.
 *
 *     node tools/build_docx.js docs/STEP_BY_STEP_GUIDE.md
 *     node tools/build_docx.js docs/HANDOVER.md
 *     node tools/build_docx.js docs/UAT_TEST_CASES.md docs/UAT.docx
 *
 * Written as a converter rather than a one-off transcription so the Word copy can
 * be regenerated whenever the markdown changes. A Word file that has drifted from
 * the source it was copied from is worse than no Word file.
 *
 * Handles the constructs these documents actually use: headings, tables, fenced
 * code, blockquote callouts, bullet and numbered lists, horizontal rules, and
 * inline bold / inline code.
 */

const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  HeadingLevel, AlignmentType, WidthType, BorderStyle, ShadingType,
  PageBreak, Header, Footer, PageNumber, LevelFormat, convertInchesToTwip,
} = require("docx");

// Same palette as the dashboard, the SharePoint lists and the slide deck.
const NAVY = "0C3549";
const BLUE = "2E86AB";
const AMBER = "8A5A00";
const TEXT = "1F2933";
const MUTED = "6B7680";
const RULE = "D9E2E6";
const CODE_BG = "F4F6F7";
const CALL_BG = "FDF6E3";
const HEAD_BG = "0C3549";
const BAND_BG = "F7F9FA";

const BODY_FONT = "Calibri";
const HEAD_FONT = "Calibri";
const MONO_FONT = "Consolas";

// A4 portrait, 1" margins -> usable width in DXA (1440 = 1 inch)
const PAGE_W = 11906;
const MARGIN = 1080;                     // 0.75"
const CONTENT_W = PAGE_W - 2 * MARGIN;   // 9746

// ---------------------------------------------------------------- inline runs
/**
 * Splits a line into runs, honouring **bold** and `code`.
 * Code is matched first so a ** inside backticks is not treated as emphasis.
 */
function runs(text, base = {}) {
  const out = [];
  const re = /(`[^`]+`)|(\*\*[^*]+\*\*)/g;
  let last = 0, m;
  const push = (t, opts) => { if (t) out.push(new TextRun({ text: t, ...base, ...opts })); };

  while ((m = re.exec(text)) !== null) {
    push(text.slice(last, m.index));
    if (m[1]) {
      push(m[1].slice(1, -1), { font: MONO_FONT, size: (base.size || 21) - 2, color: NAVY, shading: { type: ShadingType.CLEAR, fill: CODE_BG } });
    } else {
      push(m[2].slice(2, -2), { bold: true });
    }
    last = re.lastIndex;
  }
  push(text.slice(last));
  return out.length ? out : [new TextRun({ text: "", ...base })];
}

// ---------------------------------------------------------------- table widths
/**
 * Column widths proportional to content, with a floor so a narrow column stays
 * readable. Widths must sum to the table width or Word renders it ragged.
 */
function columnWidths(rows) {
  const n = rows[0].length;
  const weight = new Array(n).fill(1);
  rows.forEach(r => r.forEach((c, i) => {
    const len = c.replace(/[*`]/g, "").length;
    weight[i] = Math.max(weight[i], Math.min(len, 60));
  }));
  const total = weight.reduce((a, b) => a + b, 0);
  const min = Math.floor(CONTENT_W * 0.08);
  let w = weight.map(x => Math.max(min, Math.round((x / total) * CONTENT_W)));
  const diff = CONTENT_W - w.reduce((a, b) => a + b, 0);
  w[w.length - 1] += diff;             // absorb rounding into the last column
  return w;
}

function buildTable(rows) {
  const widths = columnWidths(rows);
  const cell = (txt, i, isHeader) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: isHeader ? HEAD_BG : "FFFFFF" },
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: [new Paragraph({
      spacing: { before: 0, after: 0 },
      children: runs(txt, {
        size: 19, font: BODY_FONT,
        color: isHeader ? "FFFFFF" : TEXT,
        bold: isHeader || undefined,
      }),
    })],
  });

  return new Table({
    columnWidths: widths,
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      left: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      right: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 2, color: RULE },
      insideVertical: { style: BorderStyle.SINGLE, size: 2, color: RULE },
    },
    rows: rows.map((r, ri) => new TableRow({
      tableHeader: ri === 0,
      children: r.map((c, ci) => cell(c, ci, ri === 0)),
    })),
  });
}

// ---------------------------------------------------------------- block parser
/**
 * True when a line continues the paragraph above rather than starting a new
 * block. Markdown wraps prose freely, so a paragraph is a run of consecutive
 * non-blank lines - and inline formatting can straddle the wrap.
 */
function isContinuation(l) {
  if (l === undefined) return false;
  const t = l.trim();
  if (t === "") return false;
  return !(
    /^#{1,6}\s/.test(t) ||          // heading
    /^```/.test(t) ||               // code fence
    /^\|/.test(t) ||                // table row
    /^>/.test(t) ||                 // blockquote
    /^---+$/.test(t) ||             // horizontal rule
    /^[-*]\s/.test(t) ||            // new bullet
    /^\d+\.\s/.test(t)              // new numbered item
  );
}

function convert(md) {
  const lines = md.split("\n");
  const out = [];
  let i = 0;
  let firstH1 = true;

  const para = (opts) => out.push(new Paragraph(opts));

  while (i < lines.length) {
    const line = lines[i];

    // ---- fenced code -----------------------------------------------------
    if (/^```/.test(line)) {
      const body = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) body.push(lines[i++]);
      i++;
      body.forEach((l, n) => para({
        spacing: { before: n === 0 ? 100 : 0, after: n === body.length - 1 ? 140 : 0 },
        shading: { type: ShadingType.CLEAR, fill: CODE_BG },
        indent: { left: 170, right: 170 },
        children: [new TextRun({ text: l || " ", font: MONO_FONT, size: 17, color: NAVY })],
      }));
      continue;
    }

    // ---- table -----------------------------------------------------------
    if (/^\|/.test(line) && i + 1 < lines.length && /^\|[\s:|-]+\|/.test(lines[i + 1])) {
      const rows = [];
      const cells = l => l.trim().replace(/^\||\|$/g, "").split("|").map(c => c.trim());
      rows.push(cells(line));
      i += 2;                                   // skip the --- separator row
      while (i < lines.length && /^\|/.test(lines[i])) rows.push(cells(lines[i++]));
      out.push(buildTable(rows));
      para({ spacing: { after: 180 }, children: [new TextRun("")] });
      continue;
    }

    // ---- blockquote callout ---------------------------------------------
    if (/^>/.test(line)) {
      const body = [];
      while (i < lines.length && /^>/.test(lines[i])) {
        body.push(lines[i].replace(/^>\s?/, ""));
        i++;
      }
      const kept = body.filter(l => l.trim() !== "");
      kept.forEach((raw, n) => {
        const heading = /^#{1,6}\s/.test(raw);
        const txt = raw.replace(/^#{1,6}\s/, "");
        para({
          spacing: { before: n === 0 ? 140 : 0, after: n === kept.length - 1 ? 180 : 60 },
          shading: { type: ShadingType.CLEAR, fill: CALL_BG },
          indent: { left: 280, right: 280 },
          border: {
            top: n === 0 ? { style: BorderStyle.SINGLE, size: 6, color: CALL_BG } : undefined,
            bottom: n === kept.length - 1 ? { style: BorderStyle.SINGLE, size: 6, color: CALL_BG } : undefined,
          },
          children: runs(txt, {
            size: heading ? 24 : 20,
            bold: heading || undefined,
            font: BODY_FONT,
            color: heading ? NAVY : AMBER,
          }),
        });
      });
      continue;
    }

    // ---- horizontal rule -------------------------------------------------
    if (/^---+\s*$/.test(line)) {
      para({
        spacing: { before: 120, after: 200 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE } },
        children: [new TextRun("")],
      });
      i++;
      continue;
    }

    // ---- headings --------------------------------------------------------
    let m;
    if ((m = /^(#{1,4})\s+(.*)$/.exec(line))) {
      const level = m[1].length;
      const text = m[2];
      if (level === 1) {
        // Each major section starts a new page - these are read one at a time.
        if (!firstH1) para({ children: [new PageBreak()] });
        firstH1 = false;
        para({
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 0, after: 200 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: NAVY } },
          children: runs(text, { size: 34, bold: true, color: NAVY, font: HEAD_FONT }),
        });
      } else if (level === 2) {
        para({
          heading: HeadingLevel.HEADING_2,
          spacing: { before: 320, after: 140 },
          children: runs(text, { size: 26, bold: true, color: NAVY, font: HEAD_FONT }),
        });
      } else {
        para({
          heading: level === 3 ? HeadingLevel.HEADING_3 : HeadingLevel.HEADING_4,
          spacing: { before: 240, after: 100 },
          children: runs(text, { size: 22, bold: true, color: BLUE, font: HEAD_FONT }),
        });
      }
      i++;
      continue;
    }

    // ---- bullet ----------------------------------------------------------
    if ((m = /^(\s*)[-*]\s+(.*)$/.exec(line))) {
      const indent = m[1].length;
      let text = m[2];
      i++;
      // Absorb wrapped continuation lines so inline formatting spanning a line
      // break still parses. Markdown wraps freely; a run of **bold** split
      // across two source lines is one phrase, not two paragraphs.
      while (i < lines.length && isContinuation(lines[i])) text += " " + lines[i++].trim();
      para({
        numbering: { reference: "bullets", level: Math.min(Math.floor(indent / 2), 2) },
        spacing: { before: 40, after: 40 },
        children: runs(text, { size: 21, font: BODY_FONT, color: TEXT }),
      });
      continue;
    }

    // ---- numbered --------------------------------------------------------
    if ((m = /^(\s*)\d+\.\s+(.*)$/.exec(line))) {
      const indent = m[1].length;
      let text = m[2];
      i++;
      while (i < lines.length && isContinuation(lines[i])) text += " " + lines[i++].trim();
      para({
        numbering: { reference: "steps", level: Math.min(Math.floor(indent / 3), 2) },
        spacing: { before: 60, after: 60 },
        children: runs(text, { size: 21, font: BODY_FONT, color: TEXT }),
      });
      continue;
    }

    // ---- blank -----------------------------------------------------------
    if (line.trim() === "") {
      i++;
      continue;
    }

    // ---- ordinary paragraph ---------------------------------------------
    // Join the whole wrapped paragraph before parsing inline formatting.
    let text = line;
    i++;
    while (i < lines.length && isContinuation(lines[i])) text += " " + lines[i++].trim();
    para({
      spacing: { before: 60, after: 120 },
      children: runs(text, { size: 21, font: BODY_FONT, color: TEXT }),
    });
  }

  return out;
}

// ---------------------------------------------------------------- main
const src = process.argv[2];
if (!src) {
  console.error("usage: node tools/build_docx.js <markdown file> [output.docx]");
  process.exit(1);
}
const out = process.argv[3] || src.replace(/\.md$/i, ".docx");
const md = fs.readFileSync(src, "utf8");

// Title comes from the first H1; it is then removed so it is not repeated.
const titleMatch = /^#\s+(.*)$/m.exec(md);
const title = titleMatch ? titleMatch[1] : path.basename(src, ".md");
const body = titleMatch ? md.replace(titleMatch[0], "").replace(/^\s*\n/, "") : md;

const doc = new Document({
  creator: "Maintenance Engineering",
  title,
  description: "EPQPL Pondicherry - cell-based preventive maintenance system",
  numbering: {
    config: [
      {
        reference: "bullets",
        levels: [0, 1, 2].map(l => ({
          level: l, format: LevelFormat.BULLET, text: ["•", "–", "·"][l],
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 380 + l * 300, hanging: 220 } } },
        })),
      },
      {
        reference: "steps",
        levels: [0, 1, 2].map(l => ({
          level: l,
          format: [LevelFormat.DECIMAL, LevelFormat.LOWER_LETTER, LevelFormat.LOWER_ROMAN][l],
          text: [`%1.`, `%2.`, `%3.`][l],
          alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 420 + l * 300, hanging: 260 } } },
        })),
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: BODY_FONT, size: 21, color: TEXT } },
    },
  },
  sections: [{
    properties: {
      page: {
        size: { width: PAGE_W, height: 16838 },          // A4 portrait
        margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          spacing: { after: 100 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: RULE } },
          children: [new TextRun({
            text: "EPQPL Pondicherry  ·  Preventive Maintenance System",
            size: 16, color: MUTED, font: BODY_FONT,
          })],
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ children: ["Page ", PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: 16, color: MUTED, font: BODY_FONT })],
        })],
      }),
    },
    children: [
      // --- cover block ---
      new Paragraph({ spacing: { before: 1400, after: 0 }, children: [
        new TextRun({ text: title, size: 48, bold: true, color: NAVY, font: HEAD_FONT }),
      ]}),
      new Paragraph({
        spacing: { before: 160, after: 0 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: BLUE } },
        children: [new TextRun({ text: "" })],
      }),
      new Paragraph({ spacing: { before: 240, after: 0 }, children: [
        new TextRun({ text: "Cell-Based PM Planning, Scheduling & Tracking System", size: 26, color: BLUE, font: HEAD_FONT }),
      ]}),
      new Paragraph({ spacing: { before: 100, after: 0 }, children: [
        new TextRun({ text: "Eaton Power Quality Pvt Ltd  ·  Pondicherry  ·  Maintenance Engineering", size: 20, color: MUTED, font: BODY_FONT }),
      ]}),
      new Paragraph({ spacing: { before: 900, after: 0 }, children: [
        new TextRun({ text: "SharePoint Online  ·  Microsoft Forms  ·  Power Automate  ·  Power BI", size: 19, color: TEXT, font: BODY_FONT }),
      ]}),
      new Paragraph({ spacing: { before: 60, after: 0 }, children: [
        new TextRun({ text: "No additional licence required", size: 19, italics: true, color: MUTED, font: BODY_FONT }),
      ]}),
      new Paragraph({ children: [new PageBreak()] }),
      ...convert(body),
    ],
  }],
});

Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(out, buf);
  console.log(`wrote ${out}  (${(buf.length / 1024).toFixed(0)} KB)`);
});
