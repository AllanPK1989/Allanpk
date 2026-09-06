"""hmilib.py - 800 x 480 screen renderer for the GOT2000 GT2107-WTBD.

Draws each screen at the panel's true pixel resolution so the layout can be
approved, and so every object's position is unambiguous when it is built in
GT Designer3.

Palette follows ISA-101: a neutral grey field for normal operation, with
saturated colour reserved for abnormal conditions. Green does not mean "good",
it means "this motor is turning"; red is only ever an alarm.
"""

W, H = 800, 480
HEAD_H, FOOT_H = 56, 56
BODY_Y, BODY_H = HEAD_H, H - HEAD_H - FOOT_H

BG       = "#D3D7DC"
PANEL    = "#EFF1F3"
PANEL_2  = "#E2E5E9"
LINE     = "#9AA2AC"
LINE_2   = "#C2C8CF"
TXT      = "#1A1F26"
TXT_DIM  = "#5B636E"
HEAD_BG  = "#2B323B"
HEAD_TXT = "#F3F5F7"
RUN      = "#1B7A4B"
HEAT     = "#B25A16"
ALARM    = "#B5342A"
WARN     = "#9C6B12"
INFO     = "#1D5C86"
OFF      = "#AEB5BD"
FONT     = "DejaVu Sans, Arial, Helvetica, sans-serif"
MONO     = "DejaVu Sans Mono, Consolas, monospace"


class Screen:
    def __init__(self, sid, title, role="-", clock="14:32", alarm=None):
        self.sid, self.title, self.role, self.clock, self.alarm = sid, title, role, clock, alarm
        self.b = []
        self.objects = []          # object schedule rows

    # ------------------------------------------------------------ primitives
    def add(self, s):
        self.b.append(s)

    def rect(self, x, y, w, h, fill=PANEL, stroke=LINE, sw=1, r=4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" '
                 f'fill="{fill}"{st}{d}/>')

    def line(self, x1, y1, x2, y2, c=LINE, sw=1, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{c}" '
                 f'stroke-width="{sw}"{d}/>')

    def txt(self, x, y, s, size=14, fill=TXT, anchor="start", weight="normal",
            mono=False, style="normal"):
        s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.add(f'<text x="{x}" y="{y}" font-family="{MONO if mono else FONT}" '
                 f'font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" font-style="{style}">{s}</text>')

    def circle(self, cx, cy, r, fill, stroke=None, sw=1):
        st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"{st}/>')

    # -------------------------------------------------------------- schedule
    def obj(self, kind, name, device, action="", sec="-", note=""):
        self.objects.append([self.sid, kind, name, device, action, sec, note])

    # ---------------------------------------------------------- chrome
    def header(self):
        self.rect(0, 0, W, HEAD_H, HEAD_BG, None, r=0)
        self.txt(14, 24, "OVN-2026-01  OVEN CONTROL", 13, "#9FB0C0", weight="bold")
        self.txt(14, 44, self.title, 19, HEAD_TXT, weight="bold")
        # role chip
        rc = {"MAINT": WARN, "QUALITY": INFO}.get(self.role, "#4A525C")
        rl = {"MAINT": "MAINTENANCE", "QUALITY": "QUALITY"}.get(self.role, "OPERATOR")
        self.rect(560, 12, 128, 22, rc, None, r=11)
        self.txt(624, 27, rl, 11, "#FFFFFF", "middle", weight="bold")
        self.txt(624, 47, "logged in" if self.role != "-" else "no login",
                 10, "#9FB0C0", "middle")
        self.txt(786, 27, self.clock, 17, HEAD_TXT, "end", mono=True)
        self.txt(786, 45, "06-09-2026", 10, "#9FB0C0", "end")
        self.obj("Header", "Role indicator", "D28", "word lamp 0/1/2", "-",
                 "0 none, 1 maintenance, 2 quality")
        self.obj("Header", "Clock", "GOT RTC", "date+time display", "-", "")

    def banner(self, text, colour=ALARM, y=None, sub=None):
        y = BODY_Y + 6 if y is None else y
        self.rect(8, y, W - 16, 34 if not sub else 44, colour, None, r=5)
        self.txt(20, y + 23, text, 15, "#FFFFFF", weight="bold")
        if sub:
            self.txt(20, y + 38, sub, 11, "#FFE9E6")
        return y + (34 if not sub else 44) + 8

    def footer(self, active="HOME"):
        self.rect(0, H - FOOT_H, W, FOOT_H, HEAD_BG, None, r=0)
        tabs = [("HOME", "B-1000"), ("SLOTS", "B-1100"), ("COUNTERS", "B-1200"),
                ("ALARMS", "B-1300"), ("HISTORY", "B-1900"), ("LOGIN", "B-1600")]
        bw = (W - 12) / 6
        for i, (name, scr) in enumerate(tabs):
            x = 6 + i * bw
            on = name == active
            self.rect(x + 2, H - FOOT_H + 6, bw - 4, FOOT_H - 12,
                      "#48525E" if on else "#39424C", "#5C6773", r=4)
            self.txt(x + bw / 2, H - FOOT_H + 34, name, 13,
                     "#FFFFFF" if on else "#C7CED6", "middle",
                     weight="bold" if on else "normal")
            self.obj("Switch", f"Nav {name}", "-", f"screen -> {scr}", "-", "")

    # ---------------------------------------------------------- widgets
    def panel(self, x, y, w, h, title=None, fill=PANEL):
        self.rect(x, y, w, h, fill, LINE_2)
        if title:
            self.txt(x + 12, y + 20, title, 12, TXT_DIM, weight="bold")
        return y + (30 if title else 8)

    def button(self, x, y, w, h, label, kind="neutral", sub=None, size=15,
               enabled=True):
        face = {"neutral": "#E6E9ED", "go": "#DCEBE2", "stop": "#F1DEDC",
                "warn": "#F4E9D4", "info": "#DEE9F1", "dark": "#48525E"}[kind]
        edge = {"neutral": LINE, "go": RUN, "stop": ALARM, "warn": WARN,
                "info": INFO, "dark": "#39424C"}[kind]
        col = {"neutral": TXT, "go": RUN, "stop": ALARM, "warn": WARN,
               "info": INFO, "dark": "#FFFFFF"}[kind]
        if not enabled:
            face, edge, col = "#DDE0E4", "#BFC5CC", "#9AA2AC"
        self.rect(x, y, w, h, face, edge, sw=2)
        self.txt(x + w / 2, y + h / 2 + (0 if not sub else -4) + 5, label, size,
                 col, "middle", weight="bold")
        if sub:
            self.txt(x + w / 2, y + h / 2 + 16, sub, 10, TXT_DIM, "middle")

    def lamp(self, x, y, label, state, on_col=RUN, on_txt="RUNNING",
             off_txt="STOPPED", w=170, h=52):
        self.rect(x, y, w, h, PANEL_2, LINE_2)
        self.circle(x + 22, y + h / 2, 11, on_col if state else OFF,
                    "#FFFFFF" if state else "#9AA2AC", 2)
        self.txt(x + 42, y + 22, label, 12, TXT_DIM, weight="bold")
        self.txt(x + 42, y + 40, on_txt if state else off_txt, 15,
                 on_col if state else TXT_DIM, weight="bold")

    def value(self, x, y, w, label, val, unit="", size=30, col=TXT, h=64):
        self.rect(x, y, w, h, PANEL_2, LINE_2)
        self.txt(x + 10, y + 18, label, 11, TXT_DIM, weight="bold")
        self.txt(x + 10, y + 50, val, size, col, weight="bold", mono=True)
        if unit:
            self.txt(x + w - 10, y + 50, unit, 12, TXT_DIM, "end")

    def bar(self, x, y, w, h, pct, col=RUN):
        self.rect(x, y, w, h, "#CFD4DA", LINE_2, r=3)
        if pct > 0:
            self.rect(x, y, max(4, w * pct / 100), h, col, None, r=3)

    def svg(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
                f'viewBox="0 0 {W} {H}">\n<rect width="{W}" height="{H}" fill="{BG}"/>\n'
                + "\n".join(self.b) + "\n</svg>\n")

    def save(self, path):
        open(path, "w").write(self.svg())
