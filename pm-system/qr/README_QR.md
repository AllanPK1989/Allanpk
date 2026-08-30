# QR machine labels

One sticker per machine. Scanning it opens that machine's hub in SharePoint,
which shows last PM date, current cell hours, the open work order and five large
action buttons.

## Quick start

```bash
pip install -r qr/requirements.txt

# ALWAYS test before printing
python qr/generate_qr_labels.py --test

# point the payloads at your real site, then test again
python qr/generate_qr_labels.py --base-url https://contoso.sharepoint.com/sites/Maintenance --test

# one cell at a time (a machine was replaced, reprint just that cell)
python qr/generate_qr_labels.py --cell CELL-03 --test
```

Output lands in `qr/labels/`:
- `MC-01-001.png` … one 600 dpi PNG per machine
- `PM_QR_Labels.pdf` … A4 sheets, 3 across × 8 down, for pre-cut sticker paper

## What is on the label

```
┌──────────────────────────────────────────┐
│  ███ ▄▄ ███      MC-01-001               │   50 × 30 mm
│  █ ▄ █ ▀ █       Power Press 25T         │
│  ███ ▀▀ ███      CELL-01  Bay-6          │
│  ▀▄▀ █▄█ ▀       தொடங்கும் முன் ஸ்கேன்…    │
│  ███ ▄▄ ███      Scan before starting PM │
└──────────────────────────────────────────┘
   ≥ 25 mm QR
```

Machine_ID is printed large on purpose. A technician standing at the machine
should be able to confirm he is at the right one **without** taking his phone out.

## Decisions worth knowing about

**Error correction level H (30% recovery).** Shop-floor stickers get oil on them,
get scratched by a spanner and end up half covered by a cable tie. Level L would
fit the same URL into a smaller code, but a code that stops scanning after four
months is worse than no code at all — it teaches people the system is broken.

**Minimum 25 mm square.** Below that, a mid-range Android camera struggles at the
arm's length a technician actually holds a phone at, in the light a shop floor
actually has.

**Quiet zone of 2 modules.** The white border is part of the code. Do not crop it,
and do not let the sticker cutter eat into it.

**Tamil first, then English.** Tamil is the language most of this shop floor reads
first. If no Tamil font is installed the line is **omitted**, not printed as empty
boxes — a row of boxes on a sticker looks broken and undermines confidence in every
other sticker on the floor. Install one and re-run:

```bash
sudo apt-get install fonts-lohit-taml       # Linux
# Windows: Nirmala UI ships with the OS and is found automatically
```

**Text is auto-fitted, never clipped.** Each line is measured against the space
actually available beside the QR and the font shrinks until it fits. Machine_ID is
the one thing on the sticker that must never be unreadable.

## The `--test` flag — do not skip it

A wrong sticker on a machine is a field problem that takes about a month to
surface, and by then it has been scanned two hundred times against the wrong
machine. Every one of those scans is a corrupt row you cannot easily unpick.

`--test` runs three checks on all 30 labels:

| Check | Catches |
|---|---|
| Structural round-trip | The encoder altered the payload |
| Payload contains its own `Machine_ID` | A copy-paste error in the master data — a perfectly valid QR pointing at the wrong machine |
| Optical decode of the rendered PNG (`pyzbar`) | The label geometry shrank the code below what a scanner can read |
| Duplicate payload detection | Two machines that would scan as the same one |

The optical check needs `pyzbar` plus the `libzbar0` system library:

```bash
pip install pyzbar
sudo apt-get install libzbar0      # Linux
# Windows: the wheel bundles the DLL, nothing extra needed
```

Without it the test still runs the structural checks and says so plainly rather
than reporting a pass it did not perform.

## Printing

1. **A4 white polyester or vinyl sticker sheets**, 3 × 8 pre-cut at 50 × 30 mm.
   Paper labels do not survive a fuse plant — oil wicks in and the code is gone in
   weeks.
2. Print at **actual size / 100% scale**. "Fit to page" shrinks the QR below the
   25 mm minimum and the codes stop scanning reliably.
3. Laser, not inkjet. Inkjet runs when a machine is wiped down with solvent.
4. **Over-laminate** if you can, or use a clear protective patch. Doubles the life.
5. Fix at chest height, on a flat surface, away from the coolant spray line.

## When a payload changes

The QR encodes `Machine_Master.QR_Payload_URL`. Changing that column means
reprinting stickers, so it is not edited casually. It changes when:

- the SharePoint **site URL** changes (a tenant migration or a site rename)
- the **Machine Hub view** is renamed or recreated

The payload pattern is:

```
{SiteUrl}/Lists/Machine_Master/Machine%20Hub.aspx?FilterField1=Machine_ID&FilterValue1={Machine_ID}&FilterType1=Text
```

`apply_views.ps1` prints this pattern with your site substituted at the end of its
run. Use `--base-url` to rebuild every payload against the real site rather than
trusting a URL that was typed into a spreadsheet months ago:

```bash
python qr/generate_qr_labels.py --base-url https://contoso.sharepoint.com/sites/Maintenance --test
```

Then update `QR_Payload_URL` in `Machine_Master` to match, so the model, the app
and the stickers all agree.

## Adding a machine later

1. Add the row to `Machine_Master` with `Active = Yes`.
2. Increment `Machine_Count` on its cell in `Cell_Master` — the provisioning
   validator checks these agree, and Flow 2 raises an alert if a work order ends up
   with the wrong number of machine tasks.
3. Reprint just that cell: `python qr/generate_qr_labels.py --cell CELL-03 --test`
