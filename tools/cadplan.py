"""CAD-style furniture plan (PDF/PNG at 1:20 on A4 landscape + DXF for AutoCAD/SketchUp).

Usage: cadplan.py OUT_DIR
Room geometry and layout options come from floorplan.py (cm, origin = inner top-left
corner, x right, y down). Walls are drawn outside the inner outline.
"""
import math
import os
import sys

import ezdxf
from ezdxf.enums import TextEntityAlignment
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from floorplan import CHROME, OPTIONS, ROOM, check, iso  # noqa: E402

T = 12            # wall thickness, cm
SCALE = 20        # 1:20 -> 1 cm real = 0.5 mm on paper
MM = 10 / SCALE   # paper mm per real cm
PROJECT = "חדר תינוקת · משפחת לוי"
DATE = "02.11.2026"
DRAWN = "Room Story Tell · תמר"
NOTES = ["כל המידות בס״מ, נטו מקיר לקיר", "יש לאמת מידות באתר לפני הזמנה",
         "מיקום השקעים לבירור מול הלקוחה", "מידות הארון: לפי הדגם שייבחר"]

# lineweights in real-cm units (paper mm / MM)
LW_WALL, LW_MED, LW_THIN, LW_HAIR = 0.5 / MM, 0.3 / MM, 0.18 / MM, 0.12 / MM


# ---------------------------------------------------------------- shared geometry
def furniture_shapes(item):
    """Return primitives for one furniture item: ('rect'|'line'|'circle'|'arc', ...)."""
    kind, x, y, w, h = item[0], *item[1:5]
    s = [("rect", x, y, w, h, LW_MED)]
    if kind == "crib":
        s.append(("rect", x + 3, y + 3, w - 6, h - 6, LW_THIN))          # mattress 60x120
        long_vertical = h > w
        n = 14
        for i in range(1, n):
            if long_vertical:
                yy = y + h * i / n
                s += [("line", x, yy, x + 3, yy, LW_HAIR), ("line", x + w - 3, yy, x + w, yy, LW_HAIR)]
            else:
                xx = x + w * i / n
                s += [("line", xx, y, xx, y + 3, LW_HAIR), ("line", xx, y + h - 3, xx, y + h, LW_HAIR)]
    elif kind == "wardrobe":
        if h > w:   # depth along x
            cx = x + w / 2
            s.append(("line", cx, y + 4, cx, y + h - 4, LW_THIN))
            for i in range(1, 7):
                yy = y + h * i / 7
                s.append(("line", cx - 18, yy - 4, cx + 18, yy + 4, LW_HAIR))
        else:
            cy = y + h / 2
            s.append(("line", x + 4, cy, x + w - 4, cy, LW_THIN))
            for i in range(1, 7):
                xx = x + w * i / 7
                s.append(("line", xx - 4, cy - 18, xx + 4, cy + 18, LW_HAIR))
        s.append(("line", x, y, x + w, y + h, LW_HAIR))  # full-height unit marker
    elif kind == "dresser":
        f = item[6]
        if f == "t":
            s.append(("line", x, y + 4, x + w, y + 4, LW_THIN))
        elif f == "l":
            s.append(("line", x + 4, y, x + 4, y + h, LW_THIN))
        s.append(("rect", x + w / 2 - 22, y + h / 2 - 15, 44, 30, LW_HAIR))  # changing pad
    elif kind == "chair":
        s = [("rect", x + 4, y + 2, w - 8, 16, LW_MED),                   # back (window side)
             ("rect", x + 2, y + 2, 12, h - 6, LW_MED), ("rect", x + w - 14, y + 2, 12, h - 6, LW_MED),  # arms
             ("rect", x + 14, y + 18, w - 28, h - 26, LW_THIN)]           # seat
        s.append(("circle", x - 22, y + h - 10, 18, LW_THIN))             # side table
    elif kind == "books":
        s = [("rect", x + 4, y, 6, h - 6, LW_MED),                        # wall ledges (left wall)
             ("rect", x + 4, y + 6, w - 10, 6, LW_MED) if False else ("line", x, y, x, y, 0),
             ("circle", x + 42, y + 36, 24, LW_THIN),                     # floor cushion
             ("rect", x + 52, y + 4, 26, 22, LW_THIN)]                    # basket
    return s


def rug(option_idx):
    return ("circle", 160, 150, 70, LW_HAIR) if option_idx == 1 else ("circle", 150, 140, 55, LW_HAIR)


# ---------------------------------------------------------------- SVG / PDF
def svg_sheet(idx, name, items):
    W, H = ROOM["w"], ROOM["h"]
    wx0, wx1 = ROOM["window"]
    dx0, dx1 = ROOM["door"]
    sw = lambda v: f'stroke-width="{v:.3f}"'
    el = []

    # wall poché: outer rect minus inner rect and openings, hatched
    el.append('<defs><pattern id="h" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
              f'<line x1="0" y1="0" x2="0" y2="6" stroke="#000" {sw(LW_HAIR)}/></pattern></defs>')
    outer = f"M{-T},{-T} H{W + T} V{H + T} H{-T} Z"
    inner = f"M0,0 V{H} H{W} V0 Z"
    el.append(f'<path d="{outer} {inner}" fill="url(#h)" fill-rule="evenodd" stroke="none"/>')
    # wall outlines with openings cut
    el.append(f'<rect x="{wx0}" y="{-T - 1}" width="{wx1 - wx0}" height="{T + 2}" fill="#fff"/>')
    el.append(f'<rect x="{dx0}" y="{H - 1}" width="{dx1 - dx0}" height="{T + 2}" fill="#fff"/>')
    wall_lines = [
        (-T, -T, wx0, -T), (wx1, -T, W + T, -T), (0, 0, wx0, 0), (wx1, 0, W, 0),           # top
        (W + T, -T, W + T, H + T), (W, 0, W, H),                                            # right
        (-T, H + T, dx0, H + T), (dx1, H + T, W + T, H + T), (0, H, dx0, H), (dx1, H, W, H),  # bottom
        (-T, -T, -T, H + T), (0, 0, 0, H),                                                  # left
        (wx0, -T, wx0, 0), (wx1, -T, wx1, 0), (dx0, H, dx0, H + T), (dx1, H, dx1, H + T),   # jambs
    ]
    for a, b, c, d in wall_lines:
        el.append(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}" stroke="#000" {sw(LW_WALL)} stroke-linecap="square"/>')
    # window: frame + glass
    for yy in (-T, -T * 0.55, -T * 0.45, 0):
        el.append(f'<line x1="{wx0}" y1="{yy}" x2="{wx1}" y2="{yy}" stroke="#000" {sw(LW_THIN)}/>')
    el.append(f'<line x1="{wx0}" y1="{T * 0.6}" x2="{wx1}" y2="{T * 0.6}" stroke="#000" {sw(LW_HAIR)} stroke-dasharray="6 3"/>')
    # door leaf + swing
    el.append(f'<line x1="{dx0}" y1="{H}" x2="{dx0}" y2="{H - (dx1 - dx0)}" stroke="#000" {sw(LW_MED)}/>')
    r = dx1 - dx0
    el.append(f'<path d="M{dx0},{H - r} A{r},{r} 0 0,1 {dx1},{H}" fill="none" stroke="#000" {sw(LW_HAIR)} stroke-dasharray="4 3"/>')
    # AC above door (hidden line)
    el.append(f'<rect x="{dx0 - 5}" y="{H - 22}" width="{r + 10}" height="18" fill="none" stroke="#000" {sw(LW_HAIR)} stroke-dasharray="6 3"/>')
    # sockets
    for ox, oy in ROOM["outlets"]:
        el.append(f'<circle cx="{ox}" cy="{oy - 5}" r="4" fill="#fff" stroke="#000" {sw(LW_THIN)}/>'
                  f'<line x1="{ox - 4}" y1="{oy - 5}" x2="{ox + 4}" y2="{oy - 5}" stroke="#000" {sw(LW_THIN)}/>')
    # rug + furniture
    for kind, *g in [rug(idx)] + [p for it in items for p in furniture_shapes(it)]:
        if kind == "rect":
            x, y, w, h, lw = g
            el.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#fff" stroke="#000" {sw(lw)}/>')
        elif kind == "line" and g[4]:
            el.append(f'<line x1="{g[0]}" y1="{g[1]}" x2="{g[2]}" y2="{g[3]}" stroke="#000" {sw(g[4])}/>')
        elif kind == "circle":
            dash = ' stroke-dasharray="8 4"' if g[3] == LW_HAIR else ""
            el.append(f'<circle cx="{g[0]}" cy="{g[1]}" r="{g[2]}" fill="{"none" if dash else "#fff"}" stroke="#000" {sw(g[3])}{dash}/>')
    # labels (tags in circles + text)
    tags = {"crib": "1", "wardrobe": "2", "dresser": "3", "chair": "4", "books": "5"}
    for it in items:
        x, y, w, h = it[1:5]
        cx, cy = x + w / 2, y + h / 2
        el.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="#fff" stroke="#000" {sw(LW_THIN)}/>'
                  f'<text x="{cx}" y="{cy + 3.2}" class="tag">{tags[it[0]]}</text>')

    # dimensions
    def dim(x1, y1, x2, y2, off, text=None, vertical=False):
        t = text or f"{round(abs((y2 - y1) if vertical else (x2 - x1)))}"
        out = []
        if vertical:
            xd = x1 + off
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{xd + (4 if off > 0 else -4)}" y2="{y1}" class="ext"/>')
            out.append(f'<line x1="{x2}" y1="{y2}" x2="{xd + (4 if off > 0 else -4)}" y2="{y2}" class="ext"/>')
            out.append(f'<line x1="{xd}" y1="{y1}" x2="{xd}" y2="{y2}" class="dim"/>')
            for yy in (y1, y2):
                out.append(f'<line x1="{xd - 3}" y1="{yy + 3}" x2="{xd + 3}" y2="{yy - 3}" class="tick"/>')
            out.append(f'<text x="{xd - 3}" y="{(y1 + y2) / 2}" class="dt" transform="rotate(-90 {xd - 3} {(y1 + y2) / 2})">{t}</text>')
        else:
            yd = y1 + off
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{yd + (4 if off > 0 else -4)}" class="ext"/>')
            out.append(f'<line x1="{x2}" y1="{y2}" x2="{x2}" y2="{yd + (4 if off > 0 else -4)}" class="ext"/>')
            out.append(f'<line x1="{x1}" y1="{yd}" x2="{x2}" y2="{yd}" class="dim"/>')
            for xx in (x1, x2):
                out.append(f'<line x1="{xx - 3}" y1="{yd + 3}" x2="{xx + 3}" y2="{yd - 3}" class="tick"/>')
            out.append(f'<text x="{(x1 + x2) / 2}" y="{yd - 3}" class="dt">{t}</text>')
        return out

    el += dim(0, -T, wx0, -T, -22) + dim(wx0, -T, wx1, -T, -22) + dim(wx1, -T, W, -T, -22)
    el += dim(-T, -T, W + T, -T, -42, f"{W + 2 * T}") + dim(0, -T, W, -T, -32 + 0) if False else []
    el += dim(0, -T, wx0, -T, -22)[:0]
    el += dim(-T, 0, -T, H, -24, vertical=True)
    el += dim(0, H + T, dx0, H + T, 22) + dim(dx0, H + T, dx1, H + T, 22) + dim(dx1, H + T, W, H + T, 22)
    el += dim(0, H + T, W, H + T, 42)
    rects = {i[0]: i[1:5] for i in items}
    c = rects["crib"]
    if c[0] > W / 2:   # crib on right wall: distance from window wall
        el += dim(W + T, 0, W + T, c[1], 24, vertical=True) + dim(W + T, c[1], W + T, c[1] + c[3], 24, vertical=True)
    else:
        el += dim(-T, 0, -T, c[1], -38, vertical=True) + dim(-T, c[1], -T, c[1] + c[3], -38, vertical=True)

    # room label
    area = W * H / 10000
    el.append(f'<text x="{W / 2 + 10}" y="{H / 2 - 30}" class="room">חדר תינוקת</text>'
              f'<text x="{W / 2 + 10}" y="{H / 2 - 18}" class="area">שטח: {area:.2f} מ״ר · גובה תקרה: 260</text>')
    el.append(f'<text x="{(wx0 + wx1) / 2}" y="{T * 0.6 + 9}" class="note">ארגז תריס, 25 ס״מ מהתקרה</text>')
    el.append(f'<text x="{dx0 + r / 2}" y="{H - 26}" class="note">מזגן (עילי)</text>')
    for ox, oy in ROOM["outlets"]:
        el.append(f'<text x="{ox}" y="{oy - 14}" class="note">שקעים ?</text>')

    drawing = "".join(el)
    legend = "".join(f"<tr><td class='n'>{n}</td><td>{t}</td></tr>" for n, t in [
        ("1", "עריסה קיימת · 66×124 (מזרן 60×120)"), ("2", f"ארון · {next(i[3] if i[4] > i[3] else i[3] for i in items if i[0]=='wardrobe') if False else ''}"),
    ][:0])
    items_rows = []
    names = {"crib": "עריסה קיימת, מזרן 60×120", "wardrobe": "ארון בגדים (חדש)", "dresser": "שידה קיימת HEMNES",
             "chair": "כורסת הנקה קיימת + שולחן צד", "books": "פינת ספרים: מדפי תמונות, כרית, סלסלה"}
    for it in items:
        w, h = it[3], it[4]
        a, b = (max(w, h), min(w, h))
        items_rows.append(f"<tr><td class='n'>{tags[it[0]]}</td><td>{names[it[0]]}</td><td class='m'>⁦{a}×{b}⁩</td></tr>")
    checks = "".join(f"<li>{iso(n)}</li>" for n in check(items))
    notes = "".join(f"<li>{n}</li>" for n in NOTES)

    # sheet: A4 landscape 297x210 mm; drawing group scaled to 1:20
    crib_left = {i[0]: i for i in items}["crib"][1] < ROOM["w"] / 2
    gx, gy = (122 if crib_left else 112), 31   # inner top-left corner on paper (mm), right of the title block
    return f"""
<div class="sheet">
 <svg class="dwg" viewBox="0 0 297 210" width="297mm" height="210mm" xmlns="http://www.w3.org/2000/svg">
  <rect x="6" y="6" width="285" height="198" fill="none" stroke="#000" stroke-width=".5"/>
  <g transform="translate({gx} {gy}) scale({MM})">{drawing}</g>
 </svg>
 <div class="block">
  <div class="bh">{PROJECT}</div>
  <div class="bt">תוכנית העמדה · אפשרות {name}</div>
  <table class="items">{"".join(items_rows)}</table>
  <div class="sub">בדיקות</div><ul class="chk">{checks}</ul>
  <div class="sub">הערות</div><ul class="chk">{notes}</ul>
  <table class="meta"><tr><td>קנ״מ</td><td>1:{SCALE} (A4)</td></tr><tr><td>תאריך</td><td>{DATE}</td></tr>
   <tr><td>שרטוט</td><td>{DRAWN}</td></tr><tr><td>גיליון</td><td>{idx} מתוך {len(OPTIONS)}</td></tr></table>
 </div>
</div>"""


CSS = """
@font-face{font-family:Heebo;src:url(file:///root/.fonts/Heebo.ttf);font-weight:100 900}
@page{size:A4 landscape;margin:0}
*{box-sizing:border-box}body{margin:0;font-family:Heebo;color:#000}
.sheet{width:297mm;height:210mm;position:relative;page-break-after:always;background:#fff}
.dwg{position:absolute;inset:0}
.dwg text{font-family:Heebo;fill:#000}
.ext{stroke:#000;stroke-width:%(hair)s}.dim{stroke:#000;stroke-width:%(hair)s}.tick{stroke:#000;stroke-width:%(thin)s}
.dt{font-size:9px;text-anchor:middle}.tag{font-size:8.5px;text-anchor:middle;font-weight:500}
.room{font-size:12px;text-anchor:middle;font-weight:500;direction:rtl}.area{font-size:7.5px;text-anchor:middle;direction:rtl}
.note{font-size:6.5px;text-anchor:middle;direction:rtl;fill:#333}.s{font-size:2.4px;text-anchor:middle;direction:rtl}
.block{position:absolute;top:6mm;bottom:6mm;left:6mm;width:78mm;border-right:.5mm solid #000;padding:5mm 5mm 4mm;
 direction:rtl;font-size:7.5pt;display:flex;flex-direction:column;gap:2mm;background:#fff}
.bh{font-size:12pt;font-weight:600}.bt{font-size:9.5pt;border-bottom:.3mm solid #000;padding-bottom:2mm}
.sub{font-weight:600;margin-top:1mm}
table{border-collapse:collapse;width:100%%}td{border-bottom:.15mm solid #999;padding:.8mm 0;vertical-align:top}
td.n{width:6mm;font-weight:600}td.m{text-align:left;white-space:nowrap}
ul.chk{margin:0;padding-inline-start:4mm;line-height:1.45}
.meta{margin-top:auto;border-top:.3mm solid #000}.meta td:first-child{width:16mm;font-weight:600}
""" % {"hair": LW_HAIR, "thin": LW_THIN}


# ---------------------------------------------------------------- DXF
def write_dxf(path, idx, name, items):
    doc = ezdxf.new("R2018", setup=True)
    doc.header["$INSUNITS"] = 5  # cm
    doc.styles.add("HEB", font="arial.ttf")
    for n, col, lw in [("WALLS", 7, 50), ("OPENINGS", 4, 25), ("FURNITURE", 3, 30), ("DIMS", 1, 13),
                       ("TEXT", 7, 18), ("HATCH", 8, 9), ("HIDDEN", 6, 13)]:
        doc.layers.add(n, color=col, lineweight=lw)
    msp = doc.modelspace()
    W, H = ROOM["w"], ROOM["h"]
    f = lambda x, y: (x, H - y)   # DXF y is up
    wx0, wx1 = ROOM["window"]
    dx0, dx1 = ROOM["door"]
    # walls as closed polylines per segment (with openings)
    segs = [[(-T, -T), (wx0, -T), (wx0, 0), (0, 0), (0, H), (dx0, H), (dx0, H + T), (-T, H + T)],
            [(wx1, -T), (W + T, -T), (W + T, H + T), (dx1, H + T), (dx1, H), (W, H), (W, 0), (wx1, 0)]]
    for s in segs:
        pts = [f(*p) for p in s]
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": "WALLS"})
        hatch = msp.add_hatch(dxfattribs={"layer": "HATCH"})
        hatch.set_pattern_fill("ANSI31", scale=0.6)
        hatch.paths.add_polyline_path(pts, is_closed=True)
    for yy in (-T * 0.55, -T * 0.45):
        msp.add_line(f(wx0, yy), f(wx1, yy), dxfattribs={"layer": "OPENINGS"})
    msp.add_line(f(wx0, -T), f(wx1, -T), dxfattribs={"layer": "OPENINGS"})
    msp.add_line(f(wx0, 0), f(wx1, 0), dxfattribs={"layer": "OPENINGS"})
    r = dx1 - dx0
    msp.add_line(f(dx0, H), f(dx0, H - r), dxfattribs={"layer": "OPENINGS"})
    msp.add_arc(f(dx0, H), r, 0, 90, dxfattribs={"layer": "OPENINGS"})
    msp.add_lwpolyline([f(dx0 - 5, H - 22), f(dx1 + 5, H - 22), f(dx1 + 5, H - 4), f(dx0 - 5, H - 4)], close=True,
                       dxfattribs={"layer": "HIDDEN", "linetype": "DASHED"})
    for kind, *g in [rug(idx)] + [p for it in items for p in furniture_shapes(it)]:
        if kind == "rect":
            x, y, w, h, _ = g
            msp.add_lwpolyline([f(x, y), f(x + w, y), f(x + w, y + h), f(x, y + h)], close=True, dxfattribs={"layer": "FURNITURE"})
        elif kind == "line" and g[4]:
            msp.add_line(f(g[0], g[1]), f(g[2], g[3]), dxfattribs={"layer": "FURNITURE"})
        elif kind == "circle":
            msp.add_circle(f(g[0], g[1]), g[2], dxfattribs={"layer": "FURNITURE"})
    names = {"crib": "CRIB 66x124", "wardrobe": "WARDROBE", "dresser": "DRESSER 108x50",
             "chair": "NURSING CHAIR", "books": "READING NOOK"}
    for it in items:
        x, y, w, h = it[1:5]
        msp.add_text(names[it[0]], height=5, dxfattribs={"layer": "TEXT"}).set_placement(
            f(x + w / 2, y + h / 2), align=TextEntityAlignment.MIDDLE_CENTER)
    msp.add_text(f"NURSERY - LEVI - OPTION {idx}", height=8, dxfattribs={"layer": "TEXT"}).set_placement(
        f(W / 2, H + 75), align=TextEntityAlignment.MIDDLE_CENTER)
    ds = dict(dimstyle="EZ_CM_100_H25_CM", dxfattribs={"layer": "DIMS"},
              override={"dimtxt": 6, "dimasz": 4, "dimblk": "ARCHTICK", "dimexo": 2, "dimexe": 3, "dimdec": 0})
    for a, b, base in [((0, -T), (wx0, -T), -32), ((wx0, -T), (wx1, -T), -32), ((wx1, -T), (W, -T), -32),
                       ((0, H + T), (dx0, H + T), 30), ((dx0, H + T), (dx1, H + T), 30), ((dx1, H + T), (W, H + T), 30),
                       ((0, H + T), (W, H + T), 50)]:
        try:
            msp.add_linear_dim(base=f(0, a[1] + base), p1=f(*a), p2=f(*b), angle=0, **ds).render()
        except Exception:
            msp.add_linear_dim(base=f(0, a[1] + base), p1=f(*a), p2=f(*b), angle=0,
                               dxfattribs={"layer": "DIMS"}).render()
    msp.add_linear_dim(base=f(-T - 30, 0), p1=f(-T, 0), p2=f(-T, H), angle=90, dxfattribs={"layer": "DIMS"}).render()
    doc.saveas(path)


def main(out):
    os.makedirs(out, exist_ok=True)
    sheets = "".join(svg_sheet(i, n, it) for i, (n, it) in enumerate(OPTIONS.items(), 1))
    html = f"<!doctype html><html lang=he><meta charset=utf-8><style>{CSS}</style><body>{sheets}</body></html>"
    hp = os.path.join(out, "_cad.html")
    open(hp, "w", encoding="utf-8").write(html)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": 1123, "height": 794}, device_scale_factor=2)
        pg.goto("file://" + hp)
        pg.wait_for_timeout(500)
        pg.pdf(path=os.path.join(out, "plan_cad.pdf"), prefer_css_page_size=True, print_background=True)
        for i, el in enumerate(pg.query_selector_all(".sheet"), 1):
            el.screenshot(path=os.path.join(out, f"plan_cad_{i}.png"))
        b.close()
    for i, (n, it) in enumerate(OPTIONS.items(), 1):
        write_dxf(os.path.join(out, f"plan_option_{i}.dxf"), i, n, it)
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
