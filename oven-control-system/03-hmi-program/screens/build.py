import os, csv, cairosvg
from pypdf import PdfWriter
import screens

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
DOCS = os.path.abspath(os.path.join(HERE, "..", "docs"))

sched, pdfs = [], []
w = PdfWriter()
for fn in screens.ALL:
    s = fn()
    base = os.path.join(OUT, s.sid)
    s.save(base + ".svg")
    cairosvg.svg2png(url=base + ".svg", write_to=base + ".png", scale=2)
    cairosvg.svg2pdf(url=base + ".svg", write_to=base + ".pdf")
    w.append(base + ".pdf"); pdfs.append(base + ".pdf")
    sched += s.objects
    print(f"  {s.sid}  {s.title:34s} {len(s.objects):3d} objects")

out_pdf = os.path.abspath(os.path.join(HERE, "..",
          "OVN-2026-01_HMI-Screen-Design.pdf"))
with open(out_pdf, "wb") as f:
    w.write(f)
for p in pdfs:
    os.remove(p)

os.makedirs(DOCS, exist_ok=True)
with open(os.path.join(DOCS, "object-schedule.csv"), "w", newline="") as f:
    c = csv.writer(f)
    c.writerow(["Screen", "Object type", "Name", "Device", "Action",
                "Role required", "Notes"])
    c.writerows(sched)
print(f"\n{len(screens.ALL)} screens, {len(sched)} objects -> "
      f"{os.path.basename(out_pdf)} + docs/object-schedule.csv")
