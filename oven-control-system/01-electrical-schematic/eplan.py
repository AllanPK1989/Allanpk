"""
eplan.py - minimal IEC 60617 schematic drawing library, SVG output.
Units are millimetres. Sheet size A3 landscape (420 x 297 mm).
"""

SHEET_W = 420.0
SHEET_H = 297.0

# line weights (mm)
LW_THIN = 0.18
LW_MED = 0.30
LW_THICK = 0.50
LW_POWER = 0.60

FONT = "DejaVu Sans, Helvetica, Arial, sans-serif"


class Sheet:
    def __init__(self, number, title, dwg_no, rev="0", date="2026-09-06",
                 project="OVEN CONTROL PANEL - HEATER + 2 BLOWER",
                 client="", scale="NTS", drawn="CLAUDE", checked=""):
        self.number = number
        self.title = title
        self.dwg_no = dwg_no
        self.rev = rev
        self.date = date
        self.project = project
        self.client = client
        self.scale = scale
        self.drawn = drawn
        self.checked = checked
        self.body = []

    # ---------- raw ----------
    def add(self, s):
        self.body.append(s)

    # ---------- primitives ----------
    def line(self, x1, y1, x2, y2, w=LW_MED, dash=None, color="#000"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                 f'stroke="{color}" stroke-width="{w}" stroke-linecap="round"{d}/>')

    def poly(self, pts, w=LW_MED, dash=None, color="#000", fill="none", close=False):
        p = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        d = f' stroke-dasharray="{dash}"' if dash else ""
        tag = "polygon" if close else "polyline"
        self.add(f'<{tag} points="{p}" fill="{fill}" stroke="{color}" '
                 f'stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{d}/>')

    def rect(self, x, y, w, h, lw=LW_MED, fill="none", dash=None, color="#000", rx=0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" rx="{rx}" '
                 f'fill="{fill}" stroke="{color}" stroke-width="{lw}"{d}/>')

    def circle(self, cx, cy, r, lw=LW_MED, fill="none", color="#000", dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}" '
                 f'stroke="{color}" stroke-width="{lw}"{d}/>')

    def arc(self, x1, y1, x2, y2, r, sweep=1, w=LW_MED, color="#000"):
        self.add(f'<path d="M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 0 {sweep} {x2:.2f} {y2:.2f}" '
                 f'fill="none" stroke="{color}" stroke-width="{w}"/>')

    def text(self, x, y, s, size=2.5, anchor="start", color="#000", weight="normal",
             style="normal", rotate=None, family=None):
        tr = f' transform="rotate({rotate} {x:.2f} {y:.2f})"' if rotate else ""
        fam = family or FONT
        s = (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        self.add(f'<text x="{x:.2f}" y="{y:.2f}" font-family="{fam}" font-size="{size}" '
                 f'fill="{color}" text-anchor="{anchor}" font-weight="{weight}" '
                 f'font-style="{style}"{tr}>{s}</text>')

    def mono(self, x, y, s, size=2.5, anchor="start", color="#000", weight="normal"):
        self.text(x, y, s, size, anchor, color, weight,
                  family="DejaVu Sans Mono, Consolas, monospace")

    # ---------- connection dot ----------
    def dot(self, x, y, r=0.7):
        self.circle(x, y, r, lw=0, fill="#000")


    def _sub(self, x, y, sub, size=1.9, lh=3.0, anchor="start"):
        if not sub:
            return
        for i, s in enumerate(sub if isinstance(sub, (list, tuple)) else [sub]):
            self.text(x, y + i * lh, s, size, anchor)

    # ---------- terminal ----------
    def terminal(self, x, y, label=None, size=1.3, lp="above", tsize=2.0):
        self.circle(x, y, size, lw=LW_MED, fill="#fff")
        if label:
            if lp == "above":
                self.text(x, y - size - 1.0, label, tsize, "middle")
            elif lp == "below":
                self.text(x, y + size + 2.2, label, tsize, "middle")
            elif lp == "left":
                self.text(x - size - 1.0, y + 0.7, label, tsize, "end")
            else:
                self.text(x + size + 1.0, y + 0.7, label, tsize, "start")

    # ================= IEC SYMBOLS (vertical orientation) =================
    # All contact symbols occupy 8 mm vertically from (x,y) to (x,y+8)

    def _contact_body(self, x, y, blade_to_right=True):
        s = 1 if blade_to_right else -1
        self.line(x, y, x, y + 1.6)          # upper fixed lead
        self.line(x, y + 6.4, x, y + 8)      # lower fixed lead
        self.line(x, y + 6.4, x + 3.4 * s, y + 1.4)   # moving blade
        return s

    def c_no(self, x, y, tag=None, tsize=2.2, right=True, tag_dx=None):
        """Normally-open contact, vertical, 8 mm."""
        s = self._contact_body(x, y, right)
        if tag:
            dx = tag_dx if tag_dx is not None else (5.0 * s)
            self.text(x + dx, y + 4.6, tag, tsize,
                      "start" if s > 0 else "end")

    def c_nc(self, x, y, tag=None, tsize=2.2, right=True, tag_dx=None):
        """Normally-closed contact, vertical, 8 mm."""
        s = self._contact_body(x, y, right)
        # bar across the tip of the blade = contact is made
        self.line(x + 2.2 * s, y + 0.2, x + 4.6 * s, y + 2.6)
        if tag:
            dx = tag_dx if tag_dx is not None else (5.6 * s)
            self.text(x + dx, y + 4.6, tag, tsize,
                      "start" if s > 0 else "end")

    def c_no_h(self, x, y, tag=None, tsize=2.2):
        """Normally-open contact, HORIZONTAL, 8 mm, left->right."""
        self.line(x, y, x + 1.6, y)
        self.line(x + 6.4, y, x + 8, y)
        self.line(x + 6.4, y, x + 1.4, y - 3.4)
        if tag:
            self.text(x + 4, y - 5.4, tag, tsize, "middle")

    def pb_no(self, x, y, tag=None, tsize=2.2, label=None):
        """Push-button, NO, spring return."""
        self.c_no(x, y, tag, tsize)
        px = x + 1.7
        self.line(px, y + 3.9, px + 3.6, y + 3.9, w=LW_THIN, dash="0.8,0.8")
        self.line(px + 3.6, y + 3.9, px + 3.6, y + 1.4)
        self.line(px + 2.2, y + 1.4, px + 5.0, y + 1.4)   # button bar
        if label:
            self.text(x + 8.2, y + 4.6, label, tsize, "start")

    def pb_nc(self, x, y, tag=None, tsize=2.2, label=None):
        """Push-button, NC, spring return."""
        self.c_nc(x, y, tag, tsize)
        px = x + 1.7
        self.line(px, y + 3.9, px + 4.4, y + 3.9, w=LW_THIN, dash="0.8,0.8")
        self.line(px + 4.4, y + 3.9, px + 4.4, y + 1.4)
        self.line(px + 3.0, y + 1.4, px + 5.8, y + 1.4)
        if label:
            self.text(x + 9.0, y + 4.6, label, tsize, "start")

    def estop(self, x, y, tag=None, label=None, tsize=2.2):
        """Emergency stop, NC, mushroom head, latching."""
        self.c_nc(x, y, tag, tsize, tag_dx=-2.0)
        px = x + 1.7
        self.line(px, y + 3.9, px + 4.4, y + 3.9, w=LW_THIN, dash="0.8,0.8")
        self.line(px + 4.4, y + 3.9, px + 4.4, y + 1.8)
        self.arc(px + 2.4, y + 1.8, px + 6.4, y + 1.8, 2.2, sweep=1, w=LW_MED)
        if label:
            self.text(x + 9.6, y + 4.6, label, tsize, "start")

    def limit_switch(self, x, y, tag=None, label=None, tsize=2.2, nc=False):
        """Position (limit) switch with roller actuator."""
        (self.c_nc if nc else self.c_no)(x, y, tag, tsize)
        px = x + 1.7
        self.line(px, y + 3.9, px + 4.2, y + 3.9, w=LW_THIN, dash="0.8,0.8")
        self.line(px + 4.2, y + 3.9, px + 4.2, y + 2.2)
        self.circle(px + 4.2, y + 1.3, 0.9, lw=LW_MED)
        if label:
            self.text(x + 9.0, y + 4.6, label, tsize, "start")

    def coil(self, x, y, tag=None, sub=None, tsize=2.4, w=9.0, h=6.0, dash=None):
        """Relay / contactor coil. Leads at (x,y) and (x,y+12)."""
        top = y + 3.0
        self.line(x, y, x, top)
        self.line(x, top + h, x, y + 12)
        self.rect(x - w / 2, top, w, h, lw=LW_MED, dash=dash)
        self.text(x - w / 2 - 1.2, top + 2.6, "A1", 1.9, "end")
        self.text(x - w / 2 - 1.2, top + h - 0.4, "A2", 1.9, "end")
        if tag:
            self.text(x + w / 2 + 1.6, top + 2.8, tag, tsize, "start", weight="bold")
        self._sub(x + w / 2 + 1.6, top + 6.0, sub)

    def coil_slow(self, x, y, tag=None, sub=None):
        """Coil with on-delay marking (timer relay)."""
        self.coil(x, y, tag, sub)
        top = y + 3.0
        self.line(x - 4.5, top, x - 4.5 + 2.2, top + 6.0, w=LW_THIN)

    def lamp(self, x, y, tag=None, colr="#000", label=None, tsize=2.2, r=3.0):
        """Indicator lamp. Leads at (x,y) and (x,y+12)."""
        cy = y + 6.0
        self.line(x, y, x, cy - r)
        self.line(x, cy + r, x, y + 12)
        self.circle(x, cy, r, lw=LW_MED, color=colr)
        k = r * 0.707
        self.line(x - k, cy - k, x + k, cy + k, w=LW_MED, color=colr)
        self.line(x - k, cy + k, x + k, cy - k, w=LW_MED, color=colr)
        if tag:
            self.text(x + r + 1.6, cy - 0.6, tag, tsize, "start", weight="bold")
        if label:
            self.text(x + r + 1.6, cy + 2.8, label, 1.9, "start")

    def buzzer(self, x, y, tag=None, label=None):
        cy = y + 6.0
        self.line(x, y, x, cy - 3.0)
        self.line(x, cy + 3.0, x, y + 12)
        self.add(f'<path d="M {x-3.4:.2f} {cy+3.0:.2f} A 3.4 3.4 0 0 1 {x+3.4:.2f} {cy+3.0:.2f} Z" '
                 f'fill="none" stroke="#000" stroke-width="{LW_MED}"/>')
        if tag:
            self.text(x + 5.0, cy, tag, 2.2, "start", weight="bold")
        if label:
            self.text(x + 5.0, cy + 3.2, label, 1.9, "start")

    def motor(self, x, y, tag=None, sub=None, r=6.0):
        """3-phase motor. Terminal at top (x, y)."""
        cy = y + r
        self.line(x, y - 3, x, y)
        self.circle(x, cy, r, lw=LW_MED)
        self.text(x, cy - 0.2, "M", 4.5, "middle", weight="bold")
        self.text(x, cy + 3.8, "3~", 2.6, "middle")
        if tag:
            self.text(x + r + 2.0, cy - 1.0, tag, 2.6, "start", weight="bold")
        self._sub(x + r + 2.0, cy + 2.4, sub, size=2.0)

    def heater(self, x, y, tag=None, sub=None, w=7.0, h=14.0):
        """Heating element (resistor with hatch). Lead at top (x,y)."""
        self.line(x, y, x, y + 2)
        self.rect(x - w / 2, y + 2, w, h, lw=LW_MED)
        for i in range(3):
            yy = y + 4.5 + i * 3.4
            self.line(x - w / 2 + 1.0, yy + 1.6, x + w / 2 - 1.0, yy - 1.0, w=LW_THIN)
        self.line(x, y + 2 + h, x, y + 4 + h)
        if tag:
            self.text(x + w / 2 + 1.6, y + 6.0, tag, 2.3, "start", weight="bold")
        self._sub(x + w / 2 + 1.6, y + 9.4, sub)

    def fuse(self, x, y, tag=None, sub=None, h=8.0, w=3.2):
        self.line(x, y, x, y + (h * 0.0))
        self.rect(x - w / 2, y, w, h, lw=LW_MED)
        self.line(x, y, x, y + h, w=LW_MED)
        if tag:
            self.text(x + w / 2 + 1.4, y + 3.2, tag, 2.2, "start", weight="bold")
        self._sub(x + w / 2 + 1.4, y + 6.4, sub)

    def breaker_pole(self, x, y, h=12.0, thermal=True, magnetic=True):
        """Single pole of a thermal-magnetic circuit breaker, vertical."""
        self.line(x, y, x, y + 2.0)
        self.line(x, y + h - 2.0, x, y + h)
        self.line(x, y + h - 2.0, x + 3.2, y + 2.6)          # blade
        # cross bar (isolating function)
        self.line(x - 1.6, y + 3.6, x + 1.2, y + 1.0, w=LW_MED)
        if thermal:  # thermal element hook
            self.add(f'<path d="M {x+3.6:.2f} {y+3.2:.2f} l 2.2 0 l 0 3.2 l -2.2 0" '
                     f'fill="none" stroke="#000" stroke-width="{LW_THIN}"/>')
        if magnetic:  # magnetic element
            self.add(f'<path d="M {x+3.6:.2f} {y+7.2:.2f} q 1.1 -1.6 2.2 0" '
                     f'fill="none" stroke="#000" stroke-width="{LW_THIN}"/>')
            self.line(x + 3.6, y + 8.2, x + 5.8, y + 8.2, w=LW_THIN)

    def breaker(self, xs, y, tag=None, sub=None, h=12.0, thermal=True, magnetic=True,
                box=True, boxpad=4.0):
        """Multi-pole breaker: xs = list of pole x positions."""
        for x in xs:
            self.breaker_pole(x, y, h, thermal, magnetic)
        if box and len(xs) > 1:
            self.line(xs[0] - 1.0, y + h * 0.52, xs[-1] + 1.0, y + h * 0.52,
                      w=LW_THIN, dash="1.2,1.2")
        if tag:
            self.text(xs[-1] + 8.0, y + 4.0, tag, 2.4, "start", weight="bold")
        self._sub(xs[-1] + 8.0, y + 7.4, sub)

    def isolator(self, xs, y, tag=None, sub=None, h=12.0):
        """Load-break switch / isolator poles."""
        for x in xs:
            self.line(x, y, x, y + 2.0)
            self.line(x, y + h - 2.0, x, y + h)
            self.line(x, y + h - 2.0, x + 3.2, y + 2.6)
            self.line(x - 1.6, y + 3.6, x + 1.2, y + 1.0)
        if len(xs) > 1:
            self.line(xs[0] - 1.0, y + h * 0.52, xs[-1] + 1.0, y + h * 0.52,
                      w=LW_THIN, dash="1.2,1.2")
        if tag:
            self.text(xs[-1] + 8.0, y + 4.0, tag, 2.4, "start", weight="bold")
        self._sub(xs[-1] + 8.0, y + 7.4, sub)

    def contactor_poles(self, xs, y, tag=None, sub=None, h=10.0, xref=None):
        """Main (power) contacts of a contactor."""
        for x in xs:
            self.line(x, y, x, y + 1.8)
            self.line(x, y + h - 1.8, x, y + h)
            self.line(x, y + h - 1.8, x + 3.4, y + 1.6)
        if len(xs) > 1:
            self.line(xs[0] + 1.7, y + h * 0.5, xs[-1] + 1.7, y + h * 0.5,
                      w=LW_THIN, dash="1.2,1.2")
        if tag:
            self.text(xs[-1] + 8.0, y + 3.6, tag, 2.4, "start", weight="bold")
        self._sub(xs[-1] + 8.0, y + 7.0, sub)
        if xref:
            self.text(xs[-1] + 8.0, y + 10.2, xref, 1.8, "start", style="italic")

    def overload(self, xs, y, tag=None, sub=None, h=10.0):
        """Thermal overload relay, main path."""
        x0, x1 = xs[0] - 2.6, xs[-1] + 2.6
        self.rect(x0, y + 1.5, x1 - x0, h - 3.0, lw=LW_MED)
        for x in xs:
            self.line(x, y, x, y + h)
        # thermal hooks
        for x in xs:
            self.add(f'<path d="M {x-1.4:.2f} {y+3.4:.2f} l 2.8 0 l 0 3.2 l -2.8 0" '
                     f'fill="none" stroke="#000" stroke-width="{LW_THIN}"/>')
        if tag:
            self.text(x1 + 2.0, y + 3.8, tag, 2.4, "start", weight="bold")
        self._sub(x1 + 2.0, y + 7.2, sub)

    def transformer(self, x, y, tag=None, sub=None, h=20.0):
        """Two-winding transformer, vertical, primary left / secondary right."""
        self.circle(x - 2.6, y + h / 2, 5.2, lw=LW_MED)
        self.circle(x + 2.6, y + h / 2, 5.2, lw=LW_MED)
        if tag:
            self.text(x + 9.0, y + h / 2 - 1.0, tag, 2.4, "start", weight="bold")
        self._sub(x + 9.0, y + h / 2 + 2.4, sub)

    def psu(self, x, y, w=26.0, h=18.0, tag=None, sub=None):
        self.rect(x, y, w, h, lw=LW_MED)
        self.text(x + w / 2, y + h / 2 - 1.0, "AC", 2.4, "middle")
        self.line(x + w / 2 - 5, y + h / 2 + 0.6, x + w / 2 + 5, y + h / 2 + 0.6, w=LW_MED)
        self.text(x + w / 2, y + h / 2 + 4.6, "DC", 2.4, "middle")
        if tag:
            self.text(x + w + 2.0, y + 4.0, tag, 2.4, "start", weight="bold")
        self._sub(x + w + 2.0, y + 7.6, sub)

    def earth(self, x, y, size=4.0, label=None):
        self.line(x, y, x, y + 2.5)
        for i, f in enumerate([1.0, 0.62, 0.28]):
            self.line(x - size * f / 2, y + 2.5 + i * 1.4, x + size * f / 2, y + 2.5 + i * 1.4)
        if label:
            self.text(x + size / 2 + 1.5, y + 4.6, label, 1.9, "start")

    def thermocouple(self, x, y, tag=None, sub=None):
        """Thermocouple sensor symbol."""
        self.line(x - 3, y, x, y + 5)
        self.line(x + 3, y, x, y + 5)
        self.line(x, y + 5, x, y + 9)
        self.circle(x, y + 11.5, 2.5, lw=LW_MED)
        if tag:
            self.text(x + 4.5, y + 10.0, tag, 2.2, "start", weight="bold")
        self._sub(x + 4.5, y + 13.2, sub)

    def instrument(self, x, y, r=8.0, top="", bot="", sq=False):
        """ISA instrument bubble."""
        if sq:
            self.rect(x - r, y - r, 2 * r, 2 * r, lw=LW_MED)
        self.circle(x, y, r, lw=LW_MED)
        self.text(x, y - 0.6, top, 2.8, "middle", weight="bold")
        self.text(x, y + 3.4, bot, 2.4, "middle")



    # ---------- native horizontal loads ----------
    def coil_h(self, x, y, w=12.0, hh=7.0, tag=None, dash=None):
        """Coil drawn horizontally. Leads at (x,y) and (x+w,y)."""
        bx = x + (w - 9.0) / 2
        self.line(x, y, bx, y)
        self.line(bx + 9.0, y, x + w, y)
        self.rect(bx, y - hh / 2, 9.0, hh, lw=LW_MED, dash=dash)
        self.text(bx - 0.4, y - hh / 2 - 0.8, "A1", 1.8, "end")
        self.text(bx + 9.4, y - hh / 2 - 0.8, "A2", 1.8, "start")
        if tag:
            self.text(x + w / 2, y - hh / 2 - 1.2, tag, 2.2, "middle", weight="bold")

    def lamp_h(self, x, y, w=12.0, r=3.4, colr="#000"):
        cx = x + w / 2
        self.line(x, y, cx - r, y)
        self.line(cx + r, y, x + w, y)
        self.circle(cx, y, r, lw=LW_MED, color=colr)
        k = r * 0.707
        self.line(cx - k, y - k, cx + k, y + k, w=LW_MED, color=colr)
        self.line(cx - k, y + k, cx + k, y - k, w=LW_MED, color=colr)

    def buzzer_h(self, x, y, w=12.0, r=3.6):
        cx = x + w / 2
        self.line(x, y, cx - r, y)
        self.line(cx + r, y, x + w, y)
        self.add(f'<path d="M {cx-r:.2f} {y:.2f} A {r:.2f} {r:.2f} 0 0 0 {cx+r:.2f} {y:.2f} Z" '
                 f'fill="none" stroke="#000" stroke-width="{LW_MED}"/>')

    def hop(self, x, y, r=1.6, vertical=False):
        """Wire crossing without connection - semicircular hop."""
        if vertical:
            self.add(f'<path d="M {x:.2f} {y-r:.2f} A {r:.2f} {r:.2f} 0 0 1 {x:.2f} {y+r:.2f}" '
                     f'fill="none" stroke="#000" stroke-width="{LW_MED}"/>')
        else:
            self.add(f'<path d="M {x-r:.2f} {y:.2f} A {r:.2f} {r:.2f} 0 0 1 {x+r:.2f} {y:.2f}" '
                     f'fill="none" stroke="#000" stroke-width="{LW_MED}"/>')

    def hline_hops(self, y, x0, x1, hops=(), w=LW_MED, r=1.6):
        """Horizontal line broken by hops at the given x positions."""
        cur = x0
        for hx in sorted(hops):
            self.line(cur, y, hx - r, y, w=w)
            self.hop(hx, y, r)
            cur = hx + r
        self.line(cur, y, x1, y, w=w)

    # ---------- transform wrapper ----------
    def _wrap(self, transform, fn):
        i = len(self.body)
        fn()
        seg = self.body[i:]
        del self.body[i:]
        self.add(f'<g transform="{transform}">' + "".join(seg) + '</g>')

    def h(self, x, y, fn):
        """Draw a vertical 8 mm symbol rotated so it runs left->right from (x,y)."""
        self._wrap(f"rotate(-90 {x:.2f} {y:.2f})", lambda: fn(x, y))

    def hsym(self, kind, x, y):
        """Horizontal contact/device by name. Left lead (x,y), right lead (x+8,y)."""
        m = {
            "no": lambda a, b: self.c_no(a, b),
            "nc": lambda a, b: self.c_nc(a, b),
            "pb_no": lambda a, b: self.pb_no(a, b),
            "pb_nc": lambda a, b: self.pb_nc(a, b),
            "estop": lambda a, b: self.estop(a, b),
            "ls_no": lambda a, b: self.limit_switch(a, b),
            "ls_nc": lambda a, b: self.limit_switch(a, b, nc=True),
        }
        self.h(x, y, m[kind])

    def hload(self, kind, x, y):
        """Horizontal 12 mm load (coil / lamp / buzzer). Leads (x,y) and (x+12,y)."""
        {"coil": self.coil_h, "lamp": self.lamp_h, "buzzer": self.buzzer_h}[kind](x, y)

    # ---------- PLC / device block with terminal stubs ----------
    def plcblock(self, x, y, w, h, title, sub=None, lw=LW_MED):
        self.rect(x, y, w, h, lw=LW_THICK)
        self.text(x + w / 2, y + 6.5, title, 3.4, "middle", weight="bold")
        if sub:
            for i, t in enumerate(sub if isinstance(sub, (list, tuple)) else [sub]):
                self.text(x + w / 2, y + 10.8 + i * 3.4, t, 2.1, "middle")

    def stub(self, x, y, label, side="right", length=4.0, tsize=2.0, box=True):
        """Terminal stub on a device block edge."""
        if side == "right":
            self.line(x, y, x + length, y, w=LW_MED)
            if box:
                self.rect(x - 7.5, y - 2.0, 7.5, 4.0, lw=LW_THIN)
                self.text(x - 3.75, y + 1.4, label, tsize, "middle")
            return x + length, y
        if side == "left":
            self.line(x - length, y, x, y, w=LW_MED)
            if box:
                self.rect(x, y - 2.0, 7.5, 4.0, lw=LW_THIN)
                self.text(x + 3.75, y + 1.4, label, tsize, "middle")
            return x - length, y
        if side == "bottom":
            self.line(x, y, x, y + length, w=LW_MED)
            if box:
                self.rect(x - 4.0, y - 7.5, 8.0, 7.5, lw=LW_THIN)
                self.text(x, y - 2.6, label, tsize, "middle")
            return x, y + length
        # top
        self.line(x, y - length, x, y, w=LW_MED)
        if box:
            self.rect(x - 4.0, y, 8.0, 7.5, lw=LW_THIN)
            self.text(x, y + 5.0, label, tsize, "middle")
        return x, y - length

    # ---------- boxes / blocks ----------
    def block(self, x, y, w, h, title=None, sub=None, lw=LW_MED, dash=None, fill="none",
              tsize=3.0):
        self.rect(x, y, w, h, lw=lw, dash=dash, fill=fill)
        if title:
            self.text(x + w / 2, y + 5.4, title, tsize, "middle", weight="bold")
        self._sub(x + w / 2, y + 9.6, sub, size=2.2, lh=3.4, anchor="middle")

    def dashbox(self, x, y, w, h, label=None, lp="tl", size=2.2):
        self.rect(x, y, w, h, lw=LW_THIN, dash="2,1.6")
        if label:
            if lp == "tl":
                self.text(x + 1.5, y - 1.2, label, size, "start", style="italic")
            else:
                self.text(x + w - 1.5, y - 1.2, label, size, "end", style="italic")

    # ---------- tables ----------
    def table(self, x, y, cols, rows, rh=5.0, hdr_size=2.1, cell_size=2.0,
              hdr_fill="#e8e8e8", zebra=None, align=None, bold_col=None):
        """cols = [(width, header), ...]; rows = list of list of str."""
        widths = [c[0] for c in cols]
        total = sum(widths)
        align = align or ["start"] * len(cols)
        # header
        self.rect(x, y, total, rh, lw=LW_MED, fill=hdr_fill)
        cx = x
        for i, (w, h) in enumerate(cols):
            self.text(cx + 1.4, y + rh - 1.6, h, hdr_size, "start", weight="bold")
            if i:
                self.line(cx, y, cx, y + rh + rh * 0 + len(rows) * rh, w=LW_THIN)
            cx += w
        # rows
        for r, row in enumerate(rows):
            ry = y + rh + r * rh
            if zebra and r % 2 == 1:
                self.rect(x, ry, total, rh, lw=0, fill=zebra)
            cx = x
            for i, w in enumerate(widths):
                if i < len(row):
                    val = str(row[i])
                    a = align[i]
                    tx = cx + 1.4 if a == "start" else (cx + w / 2 if a == "middle" else cx + w - 1.4)
                    bold = "bold" if (bold_col is not None and i == bold_col) else "normal"
                    self.text(tx, ry + rh - 1.6, val, cell_size, a, weight=bold)
                cx += w
            self.line(x, ry, x + total, ry, w=LW_THIN)
        # outer + verticals over full height
        h_all = rh + len(rows) * rh
        self.rect(x, y, total, h_all, lw=LW_MED)
        cx = x
        for i, w in enumerate(widths[:-1]):
            cx += w
            self.line(cx, y, cx, y + h_all, w=LW_THIN)
        return h_all

    # ---------- frame + title block ----------
    def frame(self):
        ml, mr, mt, mb = 12.0, 6.0, 6.0, 6.0
        x0, y0 = ml, mt
        x1, y1 = SHEET_W - mr, SHEET_H - mb
        self.add(f'<rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="#fff"/>')
        self.rect(x0, y0, x1 - x0, y1 - y0, lw=LW_THICK)
        self.rect(x0 + 2, y0 + 2, x1 - x0 - 4, y1 - y0 - 4, lw=LW_THIN)
        # column refs 1..8 ; row refs A..D
        ncol, nrow = 8, 4
        cw = (x1 - x0) / ncol
        rh = (y1 - y0) / nrow
        for i in range(ncol):
            cx = x0 + cw * (i + 0.5)
            self.text(cx, y0 + 1.6, str(i + 1), 2.4, "middle")
            self.text(cx, y1 - 0.6, str(i + 1), 2.4, "middle")
            if i:
                self.line(x0 + cw * i, y0, x0 + cw * i, y0 + 2, w=LW_THIN)
                self.line(x0 + cw * i, y1 - 2, x0 + cw * i, y1, w=LW_THIN)
        for j in range(nrow):
            cy = y0 + rh * (j + 0.5)
            self.text(x0 + 1.0, cy, chr(65 + j), 2.4, "middle")
            self.text(x1 - 1.0, cy, chr(65 + j), 2.4, "middle")
            if j:
                self.line(x0, y0 + rh * j, x0 + 2, y0 + rh * j, w=LW_THIN)
                self.line(x1 - 2, y0 + rh * j, x1, y0 + rh * j, w=LW_THIN)
        self.title_block(x1, y1)

    def title_block(self, x1, y1):
        w, h = 156.0, 30.0
        x, y = x1 - 2 - w, y1 - 2 - h
        self.rect(x, y, w, h, lw=LW_MED, fill="#fff")
        # rows
        self.line(x, y + 8, x + w, y + 8, w=LW_THIN)
        self.line(x, y + 18, x + w, y + 18, w=LW_THIN)
        self.line(x, y + 24, x + w, y + 24, w=LW_THIN)
        self.line(x + 104, y + 18, x + 104, y + h, w=LW_THIN)
        self.line(x + 130, y + 18, x + 130, y + h, w=LW_THIN)
        self.line(x + 104, y, x + 104, y + 8, w=LW_THIN)

        self.text(x + 2, y + 3.2, "PROJECT", 1.7, "start")
        self.text(x + 2, y + 6.8, self.project, 2.7, "start", weight="bold")
        self.text(x + 106, y + 3.2, "CLIENT / LOCATION", 1.7, "start")
        self.text(x + 106, y + 6.8, self.client or "-", 2.2, "start")

        self.text(x + 2, y + 11.2, "SHEET TITLE", 1.7, "start")
        ts = 3.4 if len(self.title) <= 46 else max(2.2, 3.4 * 46.0 / len(self.title))
        self.text(x + 2, y + 16.2, self.title, ts, "start", weight="bold")

        self.text(x + 2, y + 21.4, "DRAWN", 1.7, "start")
        self.text(x + 22, y + 21.4, self.drawn, 2.0, "start")
        self.text(x + 2, y + 27.6, "CHECKED", 1.7, "start")
        self.text(x + 22, y + 27.6, self.checked or "-", 2.0, "start")
        self.text(x + 52, y + 21.4, "DATE", 1.7, "start")
        self.text(x + 66, y + 21.4, self.date, 2.0, "start")
        self.text(x + 52, y + 27.6, "SCALE", 1.7, "start")
        self.text(x + 66, y + 27.6, self.scale, 2.0, "start")

        self.text(x + 106, y + 21.4, "DRAWING No.", 1.7, "start")
        self.text(x + 106, y + 27.6, self.dwg_no, 2.6, "start", weight="bold")
        self.text(x + 132, y + 21.4, "SHEET", 1.7, "start")
        self.text(x + 132, y + 27.6, self.number, 2.6, "start", weight="bold")
        self.text(x + 146, y + 21.4, "REV", 1.7, "start")
        self.text(x + 146, y + 27.6, self.rev, 2.6, "start", weight="bold")

    # ---------- sheet header strip ----------
    def header(self, subtitle=None):
        self.text(16, 12.5, self.title, 4.6, "start", weight="bold")
        if subtitle:
            self.text(16, 17.4, subtitle, 2.6, "start")
        self.line(16, 19.6, 408, 19.6, w=LW_MED)

    # ---------- notes ----------
    def notes(self, x, y, lines, w=None, title="NOTES:", size=2.1, lh=3.4):
        self.text(x, y, title, size + 0.2, "start", weight="bold")
        for i, ln in enumerate(lines):
            self.text(x, y + 4.2 + i * lh, ln, size, "start")
        return y + 4.2 + len(lines) * lh

    # ---------- render ----------
    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'width="{SHEET_W}mm" height="{SHEET_H}mm" '
                f'viewBox="0 0 {SHEET_W} {SHEET_H}">\n'
                f'<rect x="0" y="0" width="{SHEET_W}" height="{SHEET_H}" fill="#ffffff"/>\n'
                + "\n".join(self.body) + "\n</svg>\n")

    def save(self, path):
        with open(path, "w") as f:
            f.write(self.svg())
