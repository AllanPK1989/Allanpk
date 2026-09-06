"""Render IMPLEMENTATION-GUIDE.md to a printable A4 PDF."""
import re, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, KeepTogether,
                                PageBreak, HRFlowable)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "IMPLEMENTATION-GUIDE.md")
OUT = os.path.join(HERE, "OVN-2026-01_Implementation-Guide.pdf")

INK, DIM, RULE = colors.HexColor("#14181D"), colors.HexColor("#5B636E"), colors.HexColor("#C2C8CF")
ACCENT, CRIT = colors.HexColor("#1D5C86"), colors.HexColor("#B5342A")
CODEBG, HEADBG = colors.HexColor("#F1F3F5"), colors.HexColor("#E7EAEE")

S = {
 "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=19, leading=23,
                      textColor=INK, spaceBefore=2, spaceAfter=8),
 "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13.5, leading=17,
                      textColor=ACCENT, spaceBefore=15, spaceAfter=5),
 "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=11, leading=14,
                      textColor=INK, spaceBefore=11, spaceAfter=3),
 "p":  ParagraphStyle("p", fontName="Helvetica", fontSize=9.3, leading=13.4,
                      textColor=INK, spaceAfter=5, alignment=TA_LEFT),
 "li": ParagraphStyle("li", fontName="Helvetica", fontSize=9.3, leading=13.2,
                      textColor=INK, leftIndent=13, bulletIndent=3, spaceAfter=2.5),
 "quote": ParagraphStyle("quote", fontName="Helvetica-Oblique", fontSize=9.2,
                         leading=13, textColor=DIM, leftIndent=10, spaceAfter=6),
 "code": ParagraphStyle("code", fontName="Courier", fontSize=8.2, leading=11,
                        textColor=INK, leftIndent=7, spaceAfter=2),
 "th": ParagraphStyle("th", fontName="Helvetica-Bold", fontSize=8.4, leading=11,
                      textColor=INK),
 "td": ParagraphStyle("td", fontName="Helvetica", fontSize=8.4, leading=11,
                      textColor=INK),
}


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.4">\1</font>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", t)
    t = t.replace("—", "&#8212;").replace("–", "&#8211;").replace("→", "&#8594;")
    t = t.replace("×", "&#215;").replace("’", "&#8217;").replace("“", '"').replace("”", '"')
    t = t.replace("≥", "&#8805;")
    for a, b in (("├──", "+--"), ("└──", "\\--"), ("│", "|"), ("─", "-")):
        t = t.replace(a, b)
    for tick in ("[ ]",):
        t = t.replace(tick, "&#9744;")
    return t


def reflow(raw):
    """Join soft-wrapped continuation lines into their list item or paragraph,
    leaving fenced code and tables verbatim."""
    out, buf, fence = [], None, False
    def flush():
        nonlocal buf
        if buf is not None:
            out.append(buf); buf = None
    for ln in raw:
        if ln.strip().startswith("```"):
            flush(); fence = not fence; out.append("```"); continue
        if fence:
            out.append(ln[3:] if ln.startswith("   ") else ln); continue
        st = ln.strip()
        if ln.startswith("> "):
            if out and out[-1].startswith("> "):
                flush(); out[-1] = out[-1].rstrip() + " " + st[2:]
            else:
                flush(); out.append(ln)
            continue
        if not st or st == "---" or ln.startswith("#") or ln.startswith("|"):
            flush(); out.append(ln); continue
        if re.match(r"^\s*([-*]|\d+\.) ", ln):
            flush(); buf = ln; continue
        if buf is not None:
            buf = buf.rstrip() + " " + st          # continuation of a list item
        else:
            buf = st                               # start of a paragraph
    flush()
    return out


def build():
    lines = reflow(open(SRC).read().split("\n"))
    flow, i = [], 0
    while i < len(lines):
        ln = lines[i]

        if ln.strip().startswith("```"):
            block, i = [], i + 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i]); i += 1
            i += 1
            tbl = Table([[Paragraph(inline(b) or "&nbsp;", S["code"])] for b in block],
                        colWidths=[168 * mm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), CODEBG),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("LINEBEFORE", (0, 0), (0, -1), 2, ACCENT)]))
            flow += [Spacer(1, 4), tbl, Spacer(1, 7)]
            continue

        if ln.startswith("| ") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            rows, i = [], i
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            hdr, body = rows[0], rows[2:]
            n = len(hdr)
            avail = 168 * mm
            wmax = [max(len(r[c]) if c < len(r) else 0 for r in [hdr] + body) for c in range(n)]
            tot = sum(wmax) or 1
            widths = [max(16 * mm, avail * w / tot) for w in wmax]
            k = avail / sum(widths)
            widths = [w * k for w in widths]
            data = [[Paragraph(inline(h), S["th"]) for h in hdr]]
            for r in body:
                data.append([Paragraph(inline(r[c]) if c < len(r) else "", S["td"])
                             for c in range(n)])
            t = Table(data, colWidths=widths, repeatRows=1)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HEADBG),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#F7F8F9")])]))
            flow += [Spacer(1, 4), t, Spacer(1, 9)]
            continue

        if ln.startswith("# "):
            if flow:
                flow.append(PageBreak())
            flow.append(Paragraph(inline(ln[2:]), S["h1"]))
            flow.append(HRFlowable(width="100%", thickness=1.4, color=ACCENT,
                                   spaceAfter=9))
        elif ln.startswith("## "):
            flow.append(Paragraph(inline(ln[3:]), S["h2"]))
        elif ln.startswith("### "):
            flow.append(Paragraph(inline(ln[4:]), S["h3"]))
        elif ln.startswith("> "):
            flow.append(Paragraph(inline(ln[2:]), S["quote"]))
        elif ln.strip() == "---":
            pass
        elif re.match(r"^\s*[-*] ", ln):
            ind = (len(ln) - len(ln.lstrip())) // 2
            st = ParagraphStyle("x", parent=S["li"], leftIndent=13 + ind * 12,
                                bulletIndent=3 + ind * 12)
            flow.append(Paragraph(inline(re.sub(r"^\s*[-*] ", "", ln)), st,
                                  bulletText="•"))
        elif re.match(r"^\s*\d+\. ", ln):
            ind = (len(ln) - len(ln.lstrip())) // 3
            num = re.match(r"^\s*(\d+)\. ", ln).group(1)
            st = ParagraphStyle("x", parent=S["li"], leftIndent=17 + ind * 12,
                                bulletIndent=3 + ind * 12)
            flow.append(Paragraph(inline(re.sub(r"^\s*\d+\. ", "", ln)), st,
                                  bulletText=f"{num}."))
        elif ln.strip():
            flow.append(Paragraph(inline(ln.strip()), S["p"]))
        else:
            flow.append(Spacer(1, 2.5))
        i += 1
    return flow


def deco(canv, doc):
    canv.saveState()
    canv.setStrokeColor(RULE); canv.setLineWidth(0.5)
    canv.line(21 * mm, 283 * mm, 189 * mm, 283 * mm)
    canv.setFont("Helvetica-Bold", 7.5); canv.setFillColor(DIM)
    canv.drawString(21 * mm, 286 * mm, "OVN-2026-01   OVEN CONTROL PANEL")
    canv.setFont("Helvetica", 7.5)
    canv.drawRightString(189 * mm, 286 * mm, "IMPLEMENTATION GUIDE   Rev 3   06-09-2026")
    canv.line(21 * mm, 17 * mm, 189 * mm, 17 * mm)
    canv.drawString(21 * mm, 12.5 * mm,
                    "GX Works3  +  GT Designer3   |   FX5U-32MT/ES  +  GT2107-WTBD")
    canv.drawRightString(189 * mm, 12.5 * mm, f"Page {doc.page}")
    canv.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=21 * mm, rightMargin=21 * mm,
                      topMargin=24 * mm, bottomMargin=22 * mm,
                      title="OVN-2026-01 Implementation Guide",
                      author="Oven control panel project")
doc.addPageTemplates([PageTemplate(id="n", frames=[Frame(
    21 * mm, 22 * mm, 168 * mm, 253 * mm, id="f",
    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=deco)])
doc.build(build())
print("wrote", os.path.basename(OUT))
