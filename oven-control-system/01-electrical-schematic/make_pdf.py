import glob, os, cairosvg
from pypdf import PdfWriter
HERE = os.path.dirname(os.path.abspath(__file__))
svgs = sorted(glob.glob(os.path.join(HERE, "svg", "sheet-*.svg")))
tmp = os.path.join(HERE, ".pdftmp"); os.makedirs(tmp, exist_ok=True)
w = PdfWriter()
for f in svgs:
    p = os.path.join(tmp, os.path.basename(f).replace(".svg", ".pdf"))
    cairosvg.svg2pdf(url=f, write_to=p)
    w.append(p)
out = os.path.join(HERE, "OVN-2026-01_Oven-Control-Panel_Electrical-Schematic.pdf")
with open(out, "wb") as fh:
    w.write(fh)
for f in glob.glob(os.path.join(tmp, "*.pdf")): os.remove(f)
os.rmdir(tmp)
print("pages:", len(svgs), "->", os.path.basename(out))
