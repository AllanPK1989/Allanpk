#!/usr/bin/env python3
"""
Generate the GA drawings and the process flow diagram from layout.json.

Everything is driven off the single dimension table in ../layout.json, which was
itself read out of animation/lib/plant.js. Change a dimension there and every
drawing follows -- there are no dimensions hard-coded in this file.

    python3 process/scripts/drawings.py

Outputs into process/drawings/:
    ga-plan.svg        general arrangement, plan view
    ga-elevation.svg   general arrangement, front elevation
    pfd.svg            process flow diagram with tags and interlocks
    ga-plan.dxf        plan view as R12 DXF, for a drafter to take into CAD
"""

import json
import math
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAYOUT = ROOT / "layout.json"
OUT = ROOT / "drawings"

PX_PER_M = 44.0
MARGIN = 90

# Muted, print-safe palette. Line weights follow drawing convention: heavy for
# equipment outline, light for dimensions and hidden detail.
INK = "#1a1a1a"
STEEL = "#5b6672"
SAND = "#c8a96a"
DIM = "#8a8a8a"
ACCENT = "#a8442a"
GRID = "#e2e2e2"


# ---------------------------------------------------------------- SVG helpers

class Svg:
    """Minimal SVG writer working in model coordinates (metres)."""

    def __init__(self, xr, yr, flip_y=True, title=""):
        self.x0, self.x1 = xr
        self.y0, self.y1 = yr
        self.flip = flip_y
        self.w = (self.x1 - self.x0) * PX_PER_M + 2 * MARGIN
        self.h = (self.y1 - self.y0) * PX_PER_M + 2 * MARGIN
        self.parts = []
        self.title = title

    def px(self, x):
        return MARGIN + (x - self.x0) * PX_PER_M

    def py(self, y):
        if self.flip:
            return MARGIN + (self.y1 - y) * PX_PER_M
        return MARGIN + (y - self.y0) * PX_PER_M

    def line(self, x1, y1, x2, y2, stroke=INK, w=1.4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<line x1="{self.px(x1):.1f}" y1="{self.py(y1):.1f}" '
            f'x2="{self.px(x2):.1f}" y2="{self.py(y2):.1f}" '
            f'stroke="{stroke}" stroke-width="{w}"{d}/>'
        )

    def rect(self, x, y, w, h, stroke=INK, fill="none", sw=1.6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        px, py = self.px(x), self.py(y + h) if self.flip else self.py(y)
        self.parts.append(
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{w * PX_PER_M:.1f}" '
            f'height="{h * PX_PER_M:.1f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d}/>'
        )

    def circle(self, x, y, r, stroke=INK, fill="none", sw=1.6, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<circle cx="{self.px(x):.1f}" cy="{self.py(y):.1f}" '
            f'r="{r * PX_PER_M:.1f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}"{d}/>'
        )

    def poly(self, pts, stroke=INK, fill="none", sw=1.6):
        s = " ".join(f"{self.px(x):.1f},{self.py(y):.1f}" for x, y in pts)
        self.parts.append(
            f'<polygon points="{s}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
        )

    def text(self, x, y, s, size=11, anchor="middle", fill=INK, weight="normal",
             dy=0, italic=False):
        st = ' font-style="italic"' if italic else ""
        self.parts.append(
            f'<text x="{self.px(x):.1f}" y="{self.py(y) + dy:.1f}" '
            f'font-family="Inter, Helvetica, Arial, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}"{st}>'
            f'{esc(s)}</text>'
        )

    def dim_h(self, x1, x2, y, label, off=0.0):
        """Horizontal dimension line with ticks and a centred label."""
        yy = y + off
        self.line(x1, yy, x2, yy, DIM, 0.8)
        for x in (x1, x2):
            self.line(x, yy - 0.09, x, yy + 0.09, DIM, 0.8)
        self.text((x1 + x2) / 2, yy, label, 10, fill=DIM, dy=-4)

    def dim_v(self, y1, y2, x, label, off=0.0):
        """Vertical dimension line with ticks and a rotated-free label."""
        xx = x + off
        self.line(xx, y1, xx, y2, DIM, 0.8)
        for y in (y1, y2):
            self.line(xx - 0.09, y, xx + 0.09, y, DIM, 0.8)
        self.text(xx, (y1 + y2) / 2, label, 10, anchor="start", fill=DIM, dy=3)
        # nudge the label clear of the line
        self.parts[-1] = self.parts[-1].replace(
            f'x="{self.px(xx):.1f}"', f'x="{self.px(xx) + 5:.1f}"'
        )

    def tag(self, x, y, code, dy=0):
        """Equipment tag bubble."""
        self.parts.append(
            f'<circle cx="{self.px(x):.1f}" cy="{self.py(y) + dy:.1f}" r="15" '
            f'fill="#ffffff" stroke="{ACCENT}" stroke-width="1.3"/>'
        )
        self.parts.append(
            f'<text x="{self.px(x):.1f}" y="{self.py(y) + dy + 4:.1f}" '
            f'font-family="Inter, Helvetica, Arial, sans-serif" font-size="9.5" '
            f'font-weight="600" text-anchor="middle" fill="{ACCENT}">{esc(code)}</text>'
        )

    def render(self, subtitle=""):
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w:.0f}" '
            f'height="{self.h:.0f}" viewBox="0 0 {self.w:.0f} {self.h:.0f}">'
            f'<rect width="100%" height="100%" fill="#ffffff"/>'
        )
        title = (
            f'<text x="{MARGIN}" y="34" font-family="Inter, Helvetica, Arial, sans-serif" '
            f'font-size="16" font-weight="700" fill="{INK}">{esc(self.title)}</text>'
            f'<text x="{MARGIN}" y="54" font-family="Inter, Helvetica, Arial, sans-serif" '
            f'font-size="11" fill="{DIM}">{esc(subtitle)}</text>'
        )
        foot = (
            f'<text x="{MARGIN}" y="{self.h - 26:.0f}" '
            f'font-family="Inter, Helvetica, Arial, sans-serif" font-size="9.5" fill="{DIM}">'
            f'Dimensions in metres, generated from layout.json. '
            f'Representative geometry from the 3D model - NOT a surveyed plant drawing. '
            f'Verify on site before procurement.</text>'
        )
        return head + title + "".join(self.parts) + foot + "</svg>"


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ---------------------------------------------------------------- derivations

def derive(L):
    m, cv, hp, br = L["material"], L["stations"]["conveyor"], L["stations"]["hopper"], L["mobile"]["barrel"]
    mx = L["stations"]["mixer"]
    rho = m["bulk_density_kg_m3"]["value"]

    fx, fy, _ = cv["from"]
    tx, ty, _ = cv["to"]
    d = dict()
    d["conveyor_length_m"] = round(math.hypot(tx - fx, ty - fy), 3)
    d["conveyor_incline_deg"] = round(math.degrees(math.atan2(ty - fy, tx - fx)), 2)

    # mixer pan: straight cylinder between pan floor and pan top
    d["mixer_geometric_volume_m3"] = round(
        math.pi * mx["pan_radius"] ** 2 * (mx["pan_top_y"] - mx["pan_floor_y"]), 3)

    # hopper: cylinder body + frustum cone
    rb = hp["body_dia"] / 2
    vb = math.pi * rb ** 2 * (hp["body_y"][1] - hp["body_y"][0])
    r1, r2 = hp["cone_dia"][0] / 2, hp["cone_dia"][1] / 2
    hc = hp["cone_y"][1] - hp["cone_y"][0]
    vc = math.pi * hc / 3 * (r1 * r1 + r1 * r2 + r2 * r2)
    d["hopper_geometric_volume_m3"] = round(vb + vc, 3)
    d["hopper_body_volume_m3"] = round(vb, 3)
    d["hopper_cone_volume_m3"] = round(vc, 3)

    d["barrel_full_mass_kg"] = round(br["geometric_volume_m3"] * rho)
    d["mixer_batch_mass_kg_at_60pct"] = round(d["mixer_geometric_volume_m3"] * 0.60 * rho)
    d["hopper_working_mass_kg_at_85pct"] = round(d["hopper_geometric_volume_m3"] * 0.85 * rho)
    d["hopper_batches_held"] = round(
        d["hopper_working_mass_kg_at_85pct"] / max(d["mixer_batch_mass_kg_at_60pct"], 1), 1)
    return d


# ------------------------------------------------------------------- GA plan

def ga_plan(L, d):
    s = Svg((-16, 16), (-11, 11), flip_y=True, title="Sand mixing line - General Arrangement, plan")
    B, S = L["building"], L["stations"]

    # building envelope
    s.rect(-15, -10, 30, 20, INK, "none", 2.2)
    # mezzanine over
    mz = B["mezzanine_extent_x"]
    s.rect(mz[0], -10, mz[1] - mz[0], 20, STEEL, "#f4f6f8", 1.2, dash="7 4")
    s.text((mz[0] + mz[1]) / 2, 8.6, "MEZZANINE OVER  (floor +4.20)", 11, fill=STEEL, weight="600")

    # lift
    li = S["lift"]
    lx, _, lz = li["pos"]
    cw = li["car_internal"][0]
    s.rect(lx - cw / 2, lz - cw / 2, cw, cw, INK, "#eef1f4", 1.8)
    s.line(lx - cw / 2, lz - cw / 2, lx + cw / 2, lz + cw / 2, STEEL, 0.9)
    s.line(lx - cw / 2, lz + cw / 2, lx + cw / 2, lz - cw / 2, STEEL, 0.9)
    s.tag(lx - 1.85, lz, li["tag"])

    # mixer
    mx = S["mixer"]
    px, _, pz = mx["pos"]
    s.rect(px - mx["base_plate"][0] / 2, pz - mx["base_plate"][1] / 2,
           *mx["base_plate"], STEEL, "none", 1.0, dash="4 3")
    s.circle(px, pz, mx["pan_radius"], INK, "#f7f2e6", 2.0)
    s.tag(px, pz + 1.3, mx["tag"])

    # conveyor in plan (runs along -z line)
    cv = S["conveyor"]
    fx, _, fz = cv["from"]
    tx, _, tz = cv["to"]
    hw = cv["trough_width"] / 2
    s.rect(fx, fz - hw, tx - fx, cv["trough_width"], STEEL, "#eef1f4", 1.4)
    s.text((fx + tx) / 2, fz - 1.15, f'{cv["tag"]}  L={d["conveyor_length_m"]} m  @{d["conveyor_incline_deg"]}deg',
           10, fill=ACCENT, weight="600")

    # hopper
    hp = S["hopper"]
    hx, _, hz = hp["pos"]
    s.circle(hx, hz, hp["body_dia"] / 2, INK, "#f7f2e6", 2.0)
    s.circle(hx, hz, hp["cone_dia"][1] / 2, STEEL, "none", 1.0, dash="4 3")
    for sx in (-0.75, 0.75):
        for sz in (-0.75, 0.75):
            s.rect(hx + sx - 0.06, hz + sz - 0.06, 0.12, 0.12, STEEL, STEEL, 0.8)
    s.tag(hx, hz + 1.45, hp["tag"])

    # filler
    fl = S["filler"]
    flx, _, flz = fl["pos"]
    fw, fd = fl["footprint"]
    s.rect(flx - fw / 2, flz - fd / 2, fw, fd, INK, "#eef1f4", 2.0)
    s.tag(flx + 1.5, flz, fl["tag"])

    # AMR route
    route = [(-6, -5.4), (-6, 2.6), (-1.0, 2.6), (3.5, 2.6), (8.5, 2.6), (8.5, 1.0)]
    for i in range(len(route) - 1):
        s.line(route[i][0], route[i][1], route[i + 1][0], route[i + 1][1], ACCENT, 1.6, dash="9 5")
    for x, z in [(-1.0, 2.6), (3.5, 2.6), (8.5, 2.6)]:
        s.circle(x, z, 0.16, ACCENT, ACCENT, 1.0)
    s.text(1.2, 3.3, "AMR ROUTE  (2.60 m clear aisle)", 10, fill=ACCENT, weight="600")

    # dimensions
    s.dim_h(px, hx, -3.6, f"{hx - px:.2f}")
    s.dim_h(hx, flx, -3.6, f"{flx - hx:.2f}")
    s.dim_h(lx, px, -8.8, f"{px - lx:.2f}")
    s.dim_h(-15, 15, -9.999, "30.00", off=-0.6)

    s.text(-12.0, -8.6, "+z toward aisle / building front", 10, anchor="start",
           fill=DIM, italic=True)

    return s.render("Ground floor. Mezzanine shown dashed. Aisle width governs AMR selection.")


# -------------------------------------------------------------- GA elevation

def ga_elev(L, d):
    s = Svg((-16, 16), (-1.6, 9.6), flip_y=True,
            title="Sand mixing line - General Arrangement, front elevation")
    B, S = L["building"], L["stations"]

    # floor + ceiling
    s.line(-15, 0, 15, 0, INK, 2.4)
    s.line(-15, B["ceiling_y"], 15, B["ceiling_y"], STEEL, 1.2, dash="9 5")
    s.text(13.6, B["ceiling_y"] + 0.22, "u/s ceiling +8.70", 10, anchor="end", fill=STEEL)

    # mezzanine
    mz = B["mezzanine_extent_x"]
    s.rect(mz[0], B["mezzanine_floor_y"] - 0.14, mz[1] - mz[0], 0.14, INK, "#e8ebee", 1.6)
    s.text((mz[0] + mz[1]) / 2, B["mezzanine_floor_y"] + 0.55, "MEZZANINE  +4.20", 11,
           fill=STEEL, weight="600")
    for x in (mz[0] + 0.6, -8.0, mz[1] - 0.4):
        s.line(x, 0, x, B["mezzanine_floor_y"] - 0.14, STEEL, 1.2)

    # lift shaft
    li = S["lift"]
    lx = li["pos"][0]
    cw = li["car_internal"][0]
    s.rect(lx - cw / 2 - 0.12, 0, cw + 0.24, 5.3, STEEL, "none", 1.2, dash="6 4")
    s.rect(lx - cw / 2, 0.05, cw, li["car_internal"][1], INK, "#eef1f4", 1.6)
    s.tag(lx, 6.1, li["tag"])
    s.dim_v(0, B["mezzanine_floor_y"], lx + cw / 2 + 0.5, "4.20 travel")

    # mixer
    mx = S["mixer"]
    px = mx["pos"][0]
    R = mx["pan_radius"]
    s.rect(px - 0.575, 0, 1.15, 0.06, STEEL, STEEL, 1.0)
    for lx2 in (px - 0.42, px + 0.42):
        s.line(lx2, 0.06, lx2, 0.52, STEEL, 1.6)
    s.poly([(px - 0.34, 0.52), (px + 0.34, 0.52), (px + R, 0.88), (px - R, 0.88)],
           INK, "#e6ece4", 1.8)
    s.rect(px - R, 0.88, 2 * R, mx["pan_top_y"] - 0.88, INK, "#e6ece4", 1.8)
    s.rect(px - R - 0.03, mx["pan_top_y"], 2 * R + 0.06,
           mx["charge_rim_y"] - mx["pan_top_y"], INK, "#3a4048", 1.4)
    s.rect(px - R + 0.06, mx["pan_floor_y"], 2 * R - 0.12, 0.30, "none", SAND, 0)
    s.tag(px, 2.5, mx["tag"])
    s.dim_v(0, mx["charge_rim_y"], px - R - 1.35, "1.52 charge rim")

    # conveyor
    cv = S["conveyor"]
    fx, fy, _ = cv["from"]
    tx, ty, _ = cv["to"]
    ang = math.radians(d["conveyor_incline_deg"])
    dx, dy = -0.12 * math.sin(ang), 0.12 * math.cos(ang)
    s.poly([(fx, fy), (tx, ty), (tx - dx, ty - dy), (fx - dx, fy - dy)], INK, "#dfe4e9", 1.6)
    for t in (0.3, 0.62, 0.9):
        lxp = fx + (tx - fx) * t
        lyp = fy + (ty - fy) * t
        s.line(lxp, 0, lxp, lyp, STEEL, 1.2)
    s.text((fx + tx) / 2 - 0.3, (fy + ty) / 2 + 0.55,
           f'{cv["tag"]}  {d["conveyor_incline_deg"]}deg', 10, fill=ACCENT, weight="700")

    # hopper
    hp = S["hopper"]
    hx = hp["pos"][0]
    rb = hp["body_dia"] / 2
    for lx2 in (hx - 0.75, hx + 0.75):
        s.line(lx2, 0, lx2, hp["leg_top_y"], STEEL, 1.8)
    s.line(hx - 0.8, 1.0, hx + 0.8, 1.0, STEEL, 1.2)
    s.poly([(hx - hp["cone_dia"][0] / 2, hp["cone_y"][1]),
            (hx + hp["cone_dia"][0] / 2, hp["cone_y"][1]),
            (hx + hp["cone_dia"][1] / 2, hp["cone_y"][0]),
            (hx - hp["cone_dia"][1] / 2, hp["cone_y"][0])], INK, "#eef1f4", 1.8)
    s.rect(hx - rb, hp["body_y"][0], 2 * rb, hp["body_y"][1] - hp["body_y"][0],
           INK, "#eef1f4", 1.8)
    s.rect(hx - rb + 0.05, hp["body_y"][0], 2 * rb - 0.1, 0.72, "none", SAND, 0)
    s.rect(hx - rb - 0.04, hp["body_y"][1], 2 * rb + 0.08, 0.06, INK, "#c9d0d7", 1.2)
    # level probes
    for y, nm in ((hp["level_probe_hi_y"], "LSH"), (hp["level_probe_lo_y"], "LSL")):
        s.rect(hx + rb, y - 0.07, 0.16, 0.14, ACCENT, "#fff", 1.2)
        s.text(hx + rb + 0.32, y, nm, 9.5, anchor="start", fill=ACCENT, weight="600", dy=3)
    # spout + valve
    s.rect(hx - 0.17, hp["spout_y"], 0.34, hp["cone_y"][0] - hp["spout_y"], INK, "#c9d0d7", 1.4)
    s.tag(hx, 4.55, hp["tag"])
    s.dim_v(0, hp["overall_height"], hx + rb + 1.55, "3.90 overall")
    s.dim_v(0, hp["spout_y"], hx - rb - 0.65, "1.83 spout")

    # filler
    fl = S["filler"]
    flx = fl["pos"][0]
    fw = fl["footprint"][0]
    s.rect(flx - fw / 2, 0.10, fw, fl["cabinet_top_y"] - 0.10, INK, "#eef1f4", 1.8)
    s.rect(flx - fw / 2 + 0.1, fl["cabinet_top_y"], fw - 0.2,
           fl["deck_y"] - fl["cabinet_top_y"], STEEL, "#dfe4e9", 1.2)
    s.poly([(flx - 0.42, fl["infeed_rim_y"]), (flx + 0.42, fl["infeed_rim_y"]),
            (flx + 0.16, fl["infeed_hopper_y"][0]), (flx - 0.16, fl["infeed_hopper_y"][0])],
           INK, "#f7f2e6", 1.8)
    for lx2 in (flx - 0.38, flx + 0.38):
        s.line(lx2, fl["deck_y"], lx2, fl["infeed_hopper_y"][0], STEEL, 1.2)
    s.tag(flx, 3.55, fl["tag"])
    s.dim_v(0, fl["infeed_rim_y"], flx + fw / 2 + 0.45, "1.95 infeed rim")

    # AMR + barrel, drawn at the filler to show the lift the cobot must make
    amr = L["mobile"]["amr"]
    br = L["mobile"]["barrel"]
    ax = flx - 2.3
    s.rect(ax - 0.6, 0.06, 1.2, amr["deck_y"] - 0.06, INK, "#e9e2f0", 1.6)
    s.rect(ax - br["outer_dia"] / 2, amr["deck_y"], br["outer_dia"], br["height"],
           INK, "#f2e2d2", 1.6)
    s.line(ax, amr["deck_y"] + br["height"], ax, amr["deck_y"] + br["height"] + 1.28,
           ACCENT, 0.8)
    s.text(ax, amr["deck_y"] + br["height"] + 1.38,
           f'{d["barrel_full_mass_kg"]} kg full', 10, fill=ACCENT, weight="700")
    s.line(ax + 0.5, amr["deck_y"] + br["height"] + 0.42, flx - 0.55,
           fl["infeed_rim_y"] + 0.32, ACCENT, 1.5, dash="7 4")
    s.text((ax + flx) / 2 + 0.1, fl["infeed_rim_y"] + 0.62,
           "lift beyond any cobot payload", 10, fill=ACCENT, weight="600", italic=True)

    return s.render(
        "Heights above finished floor level. Level switches LSH/LSL interlock CV-01.")


# --------------------------------------------------------------------- PFD

def pfd(L, d):
    s = Svg((0, 26), (0, 13), flip_y=True, title="Sand mixing line - Process Flow Diagram")

    def blk(x, y, w, h, tag, name, sub=""):
        s.rect(x, y, w, h, INK, "#ffffff", 1.8)
        s.text(x + w / 2, y + h - 0.42, tag, 12, weight="700", dy=4)
        s.text(x + w / 2, y + h - 0.95, name, 10, dy=4)
        if sub:
            s.text(x + w / 2, y + h - 1.42, sub, 9, fill=DIM, dy=4)

    def arrow(x1, y1, x2, y2, label="", dash=None):
        s.line(x1, y1, x2, y2, INK, 1.5, dash=dash)
        ang = math.atan2(y2 - y1, x2 - x1)
        for a in (ang + 2.6, ang - 2.6):
            s.line(x2, y2, x2 + 0.32 * math.cos(a), y2 + 0.32 * math.sin(a), INK, 1.5)
        if label:
            s.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.28, label, 9.5, fill=ACCENT, weight="600")

    S = L["stations"]
    blk(0.6, 9.4, 4.0, 2.2, S["rack"]["tag"], "Bag racking", "mezzanine +4.20")
    blk(6.0, 9.4, 4.0, 2.2, S["lift"]["tag"], "Goods lift", "4.20 m travel")
    blk(11.4, 9.4, 4.4, 2.2, "MT-01", "Bag opening", "manual - only touch")
    blk(17.2, 9.4, 4.4, 2.2, "VT-01", "Vacuum transfer", "to mixer")

    blk(11.4, 5.6, 4.4, 2.2, S["mixer"]["tag"], "Pan mixer",
        f'batch ~{d["mixer_batch_mass_kg_at_60pct"]} kg')
    blk(17.2, 5.6, 4.4, 2.2, S["conveyor"]["tag"], "Incline conveyor",
        f'{d["conveyor_incline_deg"]}deg  L={d["conveyor_length_m"]} m')

    blk(17.2, 1.8, 4.4, 2.2, S["hopper"]["tag"], "Storage hopper",
        f'{d["hopper_geometric_volume_m3"]} m3 geom.')
    blk(11.4, 1.8, 4.4, 2.2, "BR-01", "Barrel fill",
        f'{d["barrel_full_mass_kg"]} kg full')
    blk(5.6, 1.8, 4.4, 2.2, "RB-01", "Cobot discharge", "1.70 m reach")
    blk(0.4, 1.8, 4.4, 2.2, S["filler"]["tag"], "Filling machine", "infeed +1.95")

    arrow(4.6, 10.5, 6.0, 10.5)
    arrow(10.0, 10.5, 11.4, 10.5)
    arrow(15.8, 10.5, 17.2, 10.5)
    arrow(19.4, 9.4, 15.8, 7.8, "sand")
    arrow(15.8, 6.7, 17.2, 6.7, "disch")
    arrow(19.4, 5.6, 19.4, 4.0, "lift 3.35 m")
    arrow(17.2, 2.9, 15.8, 2.9, "gravity")
    arrow(11.4, 2.9, 10.0, 2.9, "AMR")
    arrow(5.6, 2.9, 4.8, 2.9, "tip")

    # interlocks
    s.line(21.6, 2.9, 23.2, 2.9, ACCENT, 1.3, dash="6 3")
    s.line(23.2, 2.9, 23.2, 6.7, ACCENT, 1.3, dash="6 3")
    s.line(23.2, 6.7, 21.6, 6.7, ACCENT, 1.3, dash="6 3")
    s.text(23.9, 4.8, "LSH stops CV-01", 9.5, anchor="middle", fill=ACCENT, weight="600")
    s.text(23.9, 4.35, "LSL starts CV-01", 9.5, anchor="middle", fill=ACCENT, weight="600")

    s.text(13.0, 0.5, "Solid line = material flow.  Dashed = control interlock.",
           10, fill=DIM)
    return s.render("AFTER state. Tags carry through to the equipment spec, BOM and I/O list.")


# --------------------------------------------------------------------- DXF

def dxf_plan(L):
    """Minimal R12 ASCII DXF of the plan view -- opens in AutoCAD/LibreCAD/QCAD."""
    e = []

    def ln(x1, y1, x2, y2, layer="EQUIPMENT"):
        e.extend(["0", "LINE", "8", layer,
                  "10", f"{x1:.4f}", "20", f"{y1:.4f}", "30", "0.0",
                  "11", f"{x2:.4f}", "21", f"{y2:.4f}", "31", "0.0"])

    def rect(x, y, w, h, layer="EQUIPMENT"):
        ln(x, y, x + w, y, layer); ln(x + w, y, x + w, y + h, layer)
        ln(x + w, y + h, x, y + h, layer); ln(x, y + h, x, y, layer)

    def circ(x, y, r, layer="EQUIPMENT"):
        e.extend(["0", "CIRCLE", "8", layer,
                  "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0", "40", f"{r:.4f}"])

    def txt(x, y, s, h=0.3, layer="TEXT"):
        e.extend(["0", "TEXT", "8", layer,
                  "10", f"{x:.4f}", "20", f"{y:.4f}", "30", "0.0",
                  "40", f"{h:.3f}", "1", str(s)])

    B, S = L["building"], L["stations"]
    rect(-15, -10, 30, 20, "BUILDING")
    mz = B["mezzanine_extent_x"]
    rect(mz[0], -10, mz[1] - mz[0], 20, "MEZZANINE")
    txt(mz[0] + 0.4, 8.4, "MEZZANINE OVER +4.20", 0.42)

    li = S["lift"]; cw = li["car_internal"][0]
    rect(li["pos"][0] - cw / 2, li["pos"][2] - cw / 2, cw, cw)
    txt(li["pos"][0] - cw / 2, li["pos"][2] + cw / 2 + 0.3, li["tag"], 0.42)

    mx = S["mixer"]
    circ(mx["pos"][0], mx["pos"][2], mx["pan_radius"])
    txt(mx["pos"][0] - 0.5, mx["pos"][2] + 1.0, mx["tag"], 0.42)

    cv = S["conveyor"]; hw = cv["trough_width"] / 2
    rect(cv["from"][0], cv["from"][2] - hw, cv["to"][0] - cv["from"][0], cv["trough_width"])
    txt(cv["from"][0], cv["from"][2] - 1.1, cv["tag"], 0.42)

    hp = S["hopper"]
    circ(hp["pos"][0], hp["pos"][2], hp["body_dia"] / 2)
    circ(hp["pos"][0], hp["pos"][2], hp["cone_dia"][1] / 2)
    txt(hp["pos"][0] - 0.5, hp["pos"][2] + 1.3, hp["tag"], 0.42)

    fl = S["filler"]; fw, fd = fl["footprint"]
    rect(fl["pos"][0] - fw / 2, fl["pos"][2] - fd / 2, fw, fd)
    txt(fl["pos"][0] - 0.5, fl["pos"][2] + 0.9, fl["tag"], 0.42)

    route = [(-6, -5.4), (-6, 2.6), (8.5, 2.6), (8.5, 1.0)]
    for i in range(len(route) - 1):
        ln(*route[i], *route[i + 1], "AMR_ROUTE")
    txt(0.0, 3.0, "AMR ROUTE", 0.42)

    body = "\n".join(e)
    return f"0\nSECTION\n2\nENTITIES\n{body}\n0\nENDSEC\n0\nEOF\n"


# -------------------------------------------------------------------- main

def main():
    L = json.loads(LAYOUT.read_text())
    d = derive(L)

    # write derived values back so layout.json never carries a stale number
    L["derived"] = {"_comment": L["derived"]["_comment"], **d}
    LAYOUT.write_text(json.dumps(L, indent=2) + "\n")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "ga-plan.svg").write_text(ga_plan(L, d))
    (OUT / "ga-elevation.svg").write_text(ga_elev(L, d))
    (OUT / "pfd.svg").write_text(pfd(L, d))
    (OUT / "ga-plan.dxf").write_text(dxf_plan(L))

    print("Derived quantities")
    print("-" * 52)
    for k, v in d.items():
        print(f"  {k:<38} {v}")
    print()
    for f in sorted(OUT.iterdir()):
        print(f"  wrote {f.relative_to(ROOT.parent)}  ({f.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
