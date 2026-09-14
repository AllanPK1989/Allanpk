# QR stickers — the no-install way

**Open `qr_labels.html` in a browser.** That is the whole tool chain: no Python, no
Node.js, no install, no network. It works from a file on your desktop, and it works
on a locked-down machine.

## What to do

1. Copy this whole `browser` folder somewhere local (all three files together).
2. Double-click **`qr_labels.html`**.
3. Paste your SharePoint site address — the one you provisioned the lists on, ending
   at the site name with nothing after it.
4. **Generate**, then **scan the first label off your screen with a real phone.**
5. Print on polyester at 100% scale, laser printer, margins **None**, headers and
   footers **off**.
6. The last page is a fitting checklist. Take it to the floor.

## The three files

| File | What it is |
|---|---|
| `qr_labels.html` | The page. Layout, the label design, and the checks. |
| `machines.js` | The 30 active machines, generated from `Machine_Master.csv`. |
| `qrcode.js` | QR encoder — MIT licensed, © 2009 Kazuhiko Arase, unmodified. |

All three must sit in the same folder. Open the HTML file directly; do not rename it.

## What the page checks before it lets you print

A sticker that fails is obvious and harmless — somebody scans it and nothing happens.
**The one that costs you is a sticker that works perfectly and opens the wrong
machine**, because nobody questions it, and by the time anyone notices it has been
scanned a few hundred times against the wrong history.

So before showing you the sheets, the page verifies:

1. The text beside each code names the machine that code was built for
2. No machine appears twice — a duplicate means another machine has no sticker
3. **The rendered symbol really does encode that machine's link** — it re-encodes what
   the label *should* say and compares the two symbols module by module
4. Every machine in the list got a sticker
5. The list is still the length it is supposed to be, so a line accidentally deleted
   from `machines.js` becomes a message rather than a machine that silently never
   gets a sticker

If any of those fail it says **STOP** and names the machine.

**What it cannot check** is whether the encoder is wrong in the same way twice — it
would agree with itself. That is what step 4 above is for. **Scan one with a real
phone before you print thirty.** It takes ten seconds and it is the only check that
tests the whole chain, camera included.

## If you change the machine list

Edit `machines.js` — and change `MACHINE_COUNT_EXPECTED` at the bottom to match.
Keep it in step with `sharepoint/data/Machine_Master.csv`, or the sticker sheet and
the system disagree about what is on the shop floor.

## What the sticker points at

The Machine Hub **view**, filtered to that one machine:

```
https://<your site>/Lists/Machine_Master/Machine%20Hub.aspx
    ?FilterField1=Machine_ID&FilterValue1=MC-01-001&FilterType1=Text
```

Not a form. A scan lands on a page showing the machine, its cell, its counter and the
five action buttons — so the sticker is still useful on the day somebody needs to look
something up rather than submit something.

This means **`apply_views.ps1` must have run first**, because the Machine Hub view has
to exist before a sticker can point at it.

## Design constraints that are not negotiable

- **Error correction level H** — 30% of the symbol can be destroyed and it still
  reads. A label on a fuse machine gets oil, swarf and a wipe with solvent.
- **25 mm minimum** — below that a phone struggles at arm's length under bay lighting.
- **Machine ID printed large** — it is how a wrong sticker gets spotted by eye.
- **Tamil above English.** It is the language most of the shop floor reads first. The
  text auto-shrinks to fit rather than truncating: a half-printed instruction is worse
  than none.
