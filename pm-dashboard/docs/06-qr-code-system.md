# 06 · The QR Code System

Two kinds of code, one app behind both.

## What is actually in the code

A URL. Nothing clever — the phone camera opens it, the Power App reads the query
string, and jumps to the right screen.

```
Machine     https://apps.powerapps.com/play/e/<ENV>/a/<APP>?tenantId=<TENANT>
                &source=qr&type=machine&id=MC-001

Technician  https://apps.powerapps.com/play/e/<ENV>/a/<APP>?tenantId=<TENANT>
                &source=qr&type=tech&id=TECH-01
```

Generated at error-correction level **H** (30% recoverable), which is what lets a
label survive coolant, swarf and a scratch or two. Quiet zone of 2 modules on all
four sides — printing right up to the edge of the label is the most common reason
a code will not scan.

## Generating them

```bash
python3 scripts/generate_qr_codes.py <ENV_ID> <APP_ID> <TENANT_ID>
```

Produces:

```
qr/machines/MC-001.png … MC-033.png     one per machine
qr/technicians/TECH-01.png … TECH-10.png
qr/print/machine-labels.html            4 labels per A4 page, print to PDF
qr/print/technician-badges.html         8 badges per A4 page
qr/qr_payload_index.csv                 ID → exact URL, for the audit trail
```

Run it with no arguments and you get placeholder IDs — fine for reviewing the
layout, useless on the shop floor.

## Machine labels — physical spec

| | |
|---|---|
| Size | 90 × 60 mm; QR itself 34 × 34 mm |
| Material | Polyester or laminated vinyl. Paper in a lamination pouch works for a pilot and fails within a quarter in a machine shop |
| Placement | Eye height, next to the operator panel, out of the coolant spray line, not on a door that swings open |
| Print | 600 dpi minimum, pure black on white — no grey, no tint, no background image behind the code |
| Content beyond the QR | Machine name, machine ID, cell, criticality, the six actions, make/model/serial, checklist ID, PM standard minutes |

Print two per machine: one at the panel, one inside the electrical cabinet door as
a spare. Replacing a damaged label is a five-minute job only if you have one to hand.

## Technician badges

Credit-card size, into the existing ID holder, QR facing out. 42 × 42 mm code —
larger than the machine label because it gets scanned by a supervisor's phone at
arm's length rather than held up close.

## What each scan does

### Machine QR

Opens `scrMachineHub`. Top of the screen, before any button, answers the question
people actually scan to ask: **when was the last PM, and when is the next one**.

Then six actions:

1. **Start PM checklist** — only shown when this machine has an open work order
   assigned to the person scanning. Flips the work order to In Progress and stamps
   `MachineQRScanned = Yes`.
2. **Report breakdown**
3. **Request spare part**
4. **Record spare replaced**
5. **Log abnormality**
6. **View full history**

### Technician QR

Opens `scrMyPMList` — the person's open work orders, oldest due date first.

**This list maintains itself.** An item disappears from it when the machine QR is
scanned and the checklist submitted. There is no "mark as done" control, anywhere.
That single design choice is what makes `QR Verification %` a real measure rather
than a formality: to close a job you have to be standing at the machine.

## The security question, answered honestly

**A QR code is not authentication.** Anyone who photographs a label can open that
URL. What stops abuse is what sits behind it:

| Layer | What it does |
|-------|--------------|
| Power Apps requires a Microsoft 365 sign-in | An outsider with the URL gets a login prompt, not your data |
| The app resolves the technician from `User().Email`, not from the QR | A borrowed badge shows *your* list, not the badge owner's |
| SharePoint item-level permissions on `PM_WorkOrders` | Read all, edit only your own |
| Every scan lands in `QR_Scan_Log` with the signed-in identity | Any dispute is settled by looking |
| Technicians are site **Visitors**, not Members | They cannot edit the lists directly, only through the app |

So: the QR code is a convenient pointer, and identity comes from the sign-in. Treat
the codes as public information, because on a shop floor wall that is exactly what
they are.

## Operating the code set

**When the app is republished to the same environment** — nothing to do, the IDs
are unchanged.

**When the app moves environment** (dev → test → production) — the environment ID
changes, every code changes, every label is reprinted. Do the environment move
*before* you print for the floor, not after.

**When a machine is added** — add the row to `Machine_Master`, re-run the
generator, print the one new label. The script is idempotent; existing codes come
out byte-identical.

**When a machine is decommissioned** — set `Active = No` in `Machine_Master` and
physically remove the label. Leaving a live QR on a scrapped machine generates work
orders for equipment that no longer exists.

**When a technician leaves** — set `Active = No` and collect the badge. Their
historical work orders keep the TechID; that is why the master says never delete.

## Testing before you print 33 labels

1. Print **one** label on plain paper, tape it to the machine in its intended spot.
2. Scan it with three different phones — one iPhone, one Android, one older device.
3. Scan it in the actual light at that spot, not in the office.
4. Scan it with wet hands and with a glove on, because that is the real use case.
5. Only then send the batch to print.
