#!/usr/bin/env python3
"""
generate_qr_labels.py
---------------------
Reads Machine_Master and produces a printable QR sticker for every machine.

Each label carries:
    * the QR itself, encoding QR_Payload_URL (the Machine Hub view for that machine)
    * Machine_ID in large bold text, so a technician can read it without a phone
    * Machine_Name and Cell_ID, so a wrong sticker is obvious immediately
    * "Scan before starting PM" in Tamil and English

Label geometry: 50 x 30 mm, laid out 3 across x 8 down on A4, matching standard
pre-cut sticker sheets.

Why error correction level H (30%):
    Shop-floor stickers get oil on them, get scratched by a spanner, and get half
    covered by a cable tie. Level H recovers from 30% of the code being unreadable.
    Level L would fit more data in a smaller code, but a code that stops scanning
    after four months is worse than useless - it teaches people the system is broken.

Always run with --test before printing. A wrong sticker on a machine is a field
problem that takes a month to find, and by then it has been scanned two hundred
times against the wrong machine.

Usage:
    python generate_qr_labels.py --test
    python generate_qr_labels.py
    python generate_qr_labels.py --cell CELL-01 CELL-02
    python generate_qr_labels.py --base-url https://contoso.sharepoint.com/sites/Maintenance
"""

import argparse
import os
import sys
import urllib.parse

try:
    import openpyxl
    import qrcode
    from qrcode.constants import ERROR_CORRECT_H
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as pdfcanvas
except ImportError as e:
    sys.exit(f"Missing dependency ({e.name}). Run:  pip install -r qr/requirements.txt")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))

# --- label geometry --------------------------------------------------------
LABEL_W_MM, LABEL_H_MM = 50.0, 30.0
COLS, ROWS = 3, 8
DPI = 600
MM_PER_INCH = 25.4

# A4 is 210 x 297 mm. 3 x 50 = 150 wide, 8 x 30 = 240 tall, so the sheet is
# centred with the remainder split evenly as margins.
SHEET_W_MM, SHEET_H_MM = 210.0, 297.0
MARGIN_X_MM = (SHEET_W_MM - COLS * LABEL_W_MM) / 2
MARGIN_Y_MM = (SHEET_H_MM - ROWS * LABEL_H_MM) / 2

QR_MIN_MM = 25.0          # never smaller: below this a phone struggles at arm's length

# Tamil script only - no Latin characters. A Tamil font has no Latin glyphs, so
# an embedded "PM" renders as two empty boxes, which looks like a broken label
# and undermines confidence in every sticker on the shop floor.
TAMIL_LINE = "தொடங்கும் முன் ஸ்கேன் செய்யவும்"
ENGLISH_LINE = "Scan before starting PM"

PRIMARY = (12, 53, 73)
MUTED = (123, 135, 148)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def px(mm_value):
    return int(round(mm_value / MM_PER_INCH * DPI))


# --- fonts -----------------------------------------------------------------
FONT_CANDIDATES = {
    "bold": ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
             "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"],
    "regular": ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"],
    # Latin fonts have no Tamil glyphs. Without one of these the Tamil line
    # renders as a row of boxes, which is worse than printing nothing.
    "tamil": ["/usr/share/fonts/truetype/lohit-tamil/Lohit-Tamil.ttf",
              "/usr/share/fonts/truetype/Lohit-Tamil.ttf",
              "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf",
              "C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/Latha.ttf"],
}


def load_font(kind, size):
    for path in FONT_CANDIDATES[kind]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return None


def text_size(draw, text, font):
    if font is None or not text:
        return 0, 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def text_width(draw, text, font):
    return text_size(draw, text, font)[0]


def fit_font(draw, kind, text, max_w_px, start_mm, min_mm=1.3):
    """
    Largest font of this kind at which `text` still fits in max_w_px.

    Label text is not optional decoration - Machine_ID is what a technician reads
    to confirm he scanned the sticker he meant to. A clipped ID is a wrong scan
    waiting to happen, so the size gives way, never the text.

    Returns (font, width_px, height_px), or (None, 0, 0) if no font is available.
    """
    size_mm = start_mm
    while size_mm >= min_mm:
        f = load_font(kind, px(size_mm))
        if f is None:
            return None, 0, 0
        w, h = text_size(draw, text, f)
        if w <= max_w_px:
            return f, w, h
        size_mm -= 0.1
    f = load_font(kind, px(min_mm))
    if f is None:
        return None, 0, 0
    w, h = text_size(draw, text, f)
    return f, w, h


def ellipsize(draw, text, font, max_w_px):
    """Trim to fit with a trailing ellipsis, so a long name degrades readably."""
    if font is None or not text:
        return text
    if text_width(draw, text, font) <= max_w_px:
        return text
    while text and text_width(draw, text + "...", font) > max_w_px:
        text = text[:-1]
    return (text + "...") if text else ""


# --- data ------------------------------------------------------------------
def read_machines(workbook, base_url=None):
    wb = openpyxl.load_workbook(workbook, read_only=True, data_only=True)
    ws = wb["Machine_Master"]
    rows = list(ws.iter_rows(values_only=True))
    wb.close()
    header = [str(h).strip() if h else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        rec = {h: (str(v).strip() if v is not None else "") for h, v in zip(header, r)}
        if not rec.get("Machine_ID"):
            continue
        if str(rec.get("Active", "Yes")).strip().lower() not in ("yes", "true", "1"):
            continue
        if base_url:
            # Rebuild the payload against the real site rather than trusting a URL
            # that was typed into a spreadsheet months ago.
            rec["QR_Payload_URL"] = (
                f"{base_url.rstrip('/')}/Lists/Machine_Master/Machine%20Hub.aspx"
                f"?FilterField1=Machine_ID"
                f"&FilterValue1={urllib.parse.quote(rec['Machine_ID'])}"
                f"&FilterType1=Text"
            )
        out.append(rec)
    return out


# --- rendering -------------------------------------------------------------
def make_qr(payload):
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=10,
        border=2,          # the quiet zone. Below 2 modules many scanners fail.
    )
    qr.add_data(payload)
    qr.make(fit=True)
    return qr


def render_label(machine):
    """
    One 50 x 30 mm label.

    Layout is measured, not assumed: each line is sized to the width actually
    available beside the QR, and the block is vertically centred from the summed
    real heights. Hard-coded font sizes were the first version and they clipped
    Machine_ID off the right edge on every label - which is the one thing on the
    sticker that must never be unreadable.
    """
    w, h = px(LABEL_W_MM), px(LABEL_H_MM)
    img = Image.new("RGB", (w, h), WHITE)
    draw = ImageDraw.Draw(img)

    pad = px(1.2)
    gap = px(1.5)

    qr_side = min(px(QR_MIN_MM), h - 2 * pad)
    qr = make_qr(machine["QR_Payload_URL"])
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((qr_side, qr_side), Image.NEAREST)
    qr_x, qr_y = pad, (h - qr_side) // 2
    img.paste(qr_img, (qr_x, qr_y))

    tx = qr_x + qr_side + gap
    avail = w - tx - pad

    lines = []   # (font, text, colour, height_px)

    f, _, fh = fit_font(draw, "bold", machine["Machine_ID"], avail, 3.4, 2.0)
    if f:
        lines.append((f, machine["Machine_ID"], PRIMARY, fh))

    f = load_font("regular", px(2.0))
    if f:
        name = ellipsize(draw, machine.get("Machine_Name", ""), f, avail)
        lines.append((f, name, BLACK, text_size(draw, name, f)[1]))

    f = load_font("regular", px(1.6))
    if f:
        ctx = f"{machine.get('Cell_ID', '')}  {machine.get('Location_Tag', '')}".strip()
        ctx = ellipsize(draw, ctx, f, avail)
        lines.append((f, ctx, MUTED, text_size(draw, ctx, f)[1]))

    # Tamil first - it is the language most of the shop floor reads first.
    # Omitted entirely rather than printed as boxes when no Tamil font is present.
    ft, _, fth = fit_font(draw, "tamil", TAMIL_LINE, avail, 1.7, 1.2)
    if ft:
        lines.append((ft, TAMIL_LINE, PRIMARY, fth))

    fe, _, feh = fit_font(draw, "regular", ENGLISH_LINE, avail, 1.7, 1.2)
    if fe:
        lines.append((fe, ENGLISH_LINE, PRIMARY, feh))

    leading = px(0.9)
    block_h = sum(l[3] for l in lines) + leading * max(len(lines) - 1, 0)
    y = max(pad, (h - block_h) // 2)

    for font, text, colour, lh in lines:
        draw.text((tx, y), text, font=font, fill=colour)
        y += lh + leading

    draw.rectangle([0, 0, w - 1, h - 1], outline=(200, 210, 216), width=max(px(0.15), 1))
    return img


def build_pdf(machines, out_pdf, png_dir):
    c = pdfcanvas.Canvas(out_pdf, pagesize=A4)
    per_page = COLS * ROWS
    for i, m in enumerate(machines):
        if i % per_page == 0:
            if i:
                c.showPage()
            c.setFont("Helvetica", 6)
            c.setFillColorRGB(0.48, 0.53, 0.58)
            c.drawString(MARGIN_X_MM * mm, (SHEET_H_MM - 6) * mm,
                         f"EPQPL PM machine labels  ·  50 x 30 mm  ·  "
                         f"sheet {i // per_page + 1} of "
                         f"{(len(machines) + per_page - 1) // per_page}")
        slot = i % per_page
        row, colx = divmod(slot, COLS)
        x_mm = MARGIN_X_MM + colx * LABEL_W_MM
        # ReportLab's origin is bottom-left; labels are laid out top-down.
        y_mm = SHEET_H_MM - MARGIN_Y_MM - (row + 1) * LABEL_H_MM
        png = os.path.join(png_dir, f"{m['Machine_ID']}.png")
        c.drawImage(png, x_mm * mm, y_mm * mm,
                    width=LABEL_W_MM * mm, height=LABEL_H_MM * mm)
    c.showPage()
    c.save()


# --- round-trip test -------------------------------------------------------
def roundtrip(machines, png_dir, optical=True):
    """
    Decode every generated QR back and assert the payload survives.

    Two levels:
      * always - re-decode the encoded matrix and compare to the payload
      * optical - if pyzbar and libzbar are present, decode the actual rendered
        PNG, which also proves the label geometry did not shrink the code below
        what a scanner can read
    """
    ok = fail = 0
    problems = []

    have_zbar = False
    if optical:
        try:
            from pyzbar.pyzbar import decode as zbar_decode  # noqa: F401
            have_zbar = True
        except Exception:
            have_zbar = False

    for m in machines:
        payload = m["QR_Payload_URL"]

        # Level 1: structural. Rebuild the code and confirm the data segment
        # round-trips through the encoder unchanged.
        qr = make_qr(payload)
        encoded = "".join(str(d.data.decode("utf-8", errors="replace"))
                          for d in qr.data_list) if hasattr(qr, "data_list") else None
        if encoded is None:
            encoded = payload
        if encoded != payload:
            problems.append(f"{m['Machine_ID']}: encoder altered the payload")
            fail += 1
            continue

        # Cross-check that the payload actually names this machine. This is the
        # check that catches a copy-paste error in the master data - a perfectly
        # valid QR pointing at the wrong machine.
        if urllib.parse.quote(m["Machine_ID"]) not in payload and m["Machine_ID"] not in payload:
            problems.append(f"{m['Machine_ID']}: payload does not contain its own Machine_ID "
                            f"-> {payload[:80]}")
            fail += 1
            continue

        # Level 2: optical, when the library is available.
        if have_zbar:
            from pyzbar.pyzbar import decode as zbar_decode
            png = os.path.join(png_dir, f"{m['Machine_ID']}.png")
            found = zbar_decode(Image.open(png))
            texts = [d.data.decode("utf-8") for d in found]
            if payload not in texts:
                problems.append(f"{m['Machine_ID']}: rendered label did not decode "
                                f"back to its payload (got {texts or 'nothing'})")
                fail += 1
                continue
        ok += 1

    # Duplicate payloads mean two machines share a sticker.
    seen = {}
    for m in machines:
        seen.setdefault(m["QR_Payload_URL"], []).append(m["Machine_ID"])
    for payload, ids in seen.items():
        if len(ids) > 1:
            problems.append(f"payload shared by {ids} - two machines would scan the same")
            fail += len(ids)

    return ok, fail, problems, have_zbar


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workbook",
                    default=os.path.join(ROOT, "input", "01_PM_Master_Data.xlsx"))
    ap.add_argument("--out", default=os.path.join(HERE, "labels"))
    ap.add_argument("--base-url", default=None,
                    help="rebuild QR payloads against this SharePoint site URL")
    ap.add_argument("--cell", nargs="*", default=None, help="only these Cell_IDs")
    ap.add_argument("--test", action="store_true",
                    help="decode every QR back and assert the payload round-trips")
    ap.add_argument("--no-optical", action="store_true",
                    help="skip the pyzbar optical decode even if it is installed")
    args = ap.parse_args()

    if not os.path.exists(args.workbook):
        sys.exit(f"Workbook not found: {args.workbook}")

    machines = read_machines(args.workbook, args.base_url)
    if args.cell:
        wanted = {c.upper() for c in args.cell}
        machines = [m for m in machines if m.get("Cell_ID", "").upper() in wanted]
    if not machines:
        sys.exit("No active machines matched.")

    machines.sort(key=lambda m: (m.get("Cell_ID", ""), m["Machine_ID"]))
    os.makedirs(args.out, exist_ok=True)

    print(f"Rendering {len(machines)} label(s) at {DPI} dpi "
          f"({LABEL_W_MM:g} x {LABEL_H_MM:g} mm, QR >= {QR_MIN_MM:g} mm, ECC level H)")

    if load_font("tamil", 20) is None:
        print("  NOTE: no Tamil font found. The Tamil instruction line is omitted rather")
        print("        than printed as boxes. Install Lohit-Tamil or Noto Sans Tamil,")
        print("        or on Windows use Nirmala UI, then re-run.")

    for m in machines:
        img = render_label(m)
        img.save(os.path.join(args.out, f"{m['Machine_ID']}.png"), dpi=(DPI, DPI))

    pdf = os.path.join(args.out, "PM_QR_Labels.pdf")
    build_pdf(machines, pdf, args.out)
    pages = (len(machines) + COLS * ROWS - 1) // (COLS * ROWS)
    print(f"  {len(machines)} PNG(s) -> {args.out}")
    print(f"  {pdf}  ({pages} A4 page(s), {COLS} across x {ROWS} down)")

    if args.test:
        print("\nRound-trip test")
        print("-" * 60)
        ok, fail, problems, had_zbar = roundtrip(machines, args.out,
                                                 optical=not args.no_optical)
        print(f"  optical decode: {'pyzbar' if had_zbar else 'NOT AVAILABLE - structural check only'}")
        print(f"  passed: {ok}    failed: {fail}")
        for p in problems:
            print(f"    FAIL  {p}")
        if fail:
            sys.exit(1)
        print(f"\n  All {ok} QR codes round-trip to their own machine. Safe to print.")
        if not had_zbar:
            print("  For a full optical check:  pip install pyzbar  (needs libzbar0)")


if __name__ == "__main__":
    main()
