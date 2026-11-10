"""Top-view floor plan with layout options, drawn to scale, plus clearance checks.

Usage: floorplan.py OUT_DIR
Coordinates in cm: origin = top-left corner, x to the right, y down. The window wall
is the top wall; the door wall is the bottom wall. Edit ROOM / OPTIONS for a new room.
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")

ROOM = dict(w=310, h=280, window=(90, 230), door=(25, 105), door_hinge="left",
            outlets=[(270, 280)], outlet_note="שקעים: מיקום לא ודאי, צריך לאשר מול הלקוחה")
DIM = re.compile(r"(\d+×\d+)")


def iso(t):
    """Keep WxH runs left-to-right inside Hebrew text."""
    return DIM.sub("\u2066\\1\u2069", t)


CLEAR = 60  # minimum free depth in front of furniture that is used/opened

# name, x, y, w, h, colour, front side ('t','b','l','r' or None), label
OPTIONS = {
    "א · עריסה מול הכניסה": [
        ("crib", 244, 90, 66, 124, "#E9D3CB", "l", "עריסה 66×124"),
        ("wardrobe", 0, 100, 58, 100, "#D7DFCC", "r", "ארון 100×58"),
        ("dresser", 120, 230, 108, 50, "#EFE6DA", "t", "שידה 108×50"),
        ("chair", 235, 0, 75, 80, "#D9C9BA", None, "כורסת הנקה"),
        ("books", 0, 0, 80, 70, "#F3E3B8", None, "פינת ספרים"),
    ],
    "ב · פינת הנקה וספרים ליד החלון": [
        ("crib", 0, 70, 66, 124, "#E9D3CB", "r", "עריסה 66×124"),
        ("wardrobe", 115, 222, 90, 58, "#D7DFCC", "t", "ארון 90×58"),
        ("dresser", 260, 110, 50, 108, "#EFE6DA", "l", "שידה 108×50"),
        ("chair", 235, 0, 75, 80, "#D9C9BA", None, "כורסת הנקה"),
        ("books", 0, 0, 80, 62, "#F3E3B8", None, "פינת ספרים"),
    ],
    "ג · כורסה ליד השקע, עריסה לידה": [
        ("crib", 244, 30, 66, 124, "#E9D3CB", "l", "עריסה 66×124"),
        ("wardrobe", 0, 0, 58, 100, "#D7DFCC", "r", "ארון 100×58"),
        ("dresser", 115, 230, 108, 50, "#EFE6DA", "t", "שידה 108×50"),
        ("chair", 230, 200, 75, 80, "#D9C9BA", "t", "כורסת הנקה"),
        ("books", 125, 0, 90, 30, "#F3E3B8", None, "פינת ספרים"),
    ],
    "ד · לפי ההדמיה הסופית": [
        ("crib", 244, 25, 66, 124, "#E9D3CB", "l", "עריסה 66×124"),
        ("chair", 230, 160, 80, 75, "#D9C9BA", "l", "כורסת הנקה"),
        ("dresser", 112, 230, 108, 50, "#EFE6DA", "t", "שידה 108×50"),
        ("wardrobe", 0, 8, 58, 100, "#D7DFCC", "r", "ארון 100×58"),
        ("shelves", 0, 112, 22, 86, "#F3E3B8", None, "מדפים"),
    ],
}


# Another client room: select with ROOM_PROFILE=michal (simulation client, shared boys' room, rental)
PROFILES = {
    "michal": dict(
        ROOM=dict(w=330, h=300, window=(110, 270), door=(30, 110), door_hinge="left",
                  outlets=[(80, 0), (300, 0), (130, 300)], outlet_note="שקעים: לפי מה שהלקוחה סימנה",
                  ac=(316, 20, 14, 80), ac_label="מזגן, גובה 220", ac_zone=(130, 10, 200, 110),
                  sleep="bunk", label="חדר הבנים", ceiling=260,
                  project="חדר הבנים · משפחת אהרוני", dxf_title="KIDS ROOM - AHARONI",
                  rugs={1: ("circle", 212, 172, 58)}, shutter_note=(215, 103), outlet_label="שקע",
                  notes=["כל המידות בס״מ, נטו מקיר לקיר", "דירה בשכירות: בלי צבע, מינימום קדיחות",
                         "קומותיים: מעקה מלא למעלה, וסולם בצד הפנוי",
                         "את כנפי המזגן לכוון כלפי מעלה, לא לכיוון המיטה",
                         "כוורת האחסון: לעגן לקיר (קדיחה אחת)"]),
        OPTIONS={
            "א · קומותיים לאורך הקיר השמאלי": [
                ("bunk", 0, 12, 97, 206, "#D7DFCC", "r", "קומותיים 97×206"),
                ("desk", 160, 0, 80, 50, "#EFE6DA", "b", "שולחן 80×50"),
                ("storage", 291, 100, 39, 77, "#F3E3B8", "l", "כוורת 77×39"),
                ("closet", 180, 240, 150, 60, "#E9E4DA", "t", "ארון קיר 150×60"),
            ],
        }),
}
if os.environ.get("ROOM_PROFILE") in PROFILES:
    ROOM, OPTIONS = PROFILES[os.environ["ROOM_PROFILE"]]["ROOM"], PROFILES[os.environ["ROOM_PROFILE"]]["OPTIONS"]


def overlap(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def front_zone(it):
    kind, x, y, w, h, _, f, _ = it
    if kind == "chair":          # 'front' only orients the chair drawing; legroom is checked by eye
        return None
    return {"t": (x, y - CLEAR, w, CLEAR), "b": (x, y + h, w, CLEAR),
            "l": (x - CLEAR, y, CLEAR, h), "r": (x + w, y, CLEAR, h)}.get(f)


def check(items):
    notes = []
    door_zone = (ROOM["door"][0], ROOM["h"] - 80, 80, 80)
    rects = {i[0]: i[1:5] for i in items}
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if overlap(a[1:5], b[1:5]):
                notes.append(f"✗ {a[7]} חופף ל{b[7]}")
        if overlap(a[1:5], door_zone):
            notes.append(f"✗ {a[7]} בתוך תנועת הדלת")
        x, y, w, h = a[1:5]
        if x < 0 or y < 0 or x + w > ROOM["w"] or y + h > ROOM["h"]:
            notes.append(f"✗ {a[7]} יוצא מהחדר")
        fz = front_zone(a)
        if fz:
            blocked = [b[7] for b in items if b is not a and overlap(fz, b[1:5])]
            notes.append(f"{'✗' if blocked else '✓'} מול {a[7]}: {CLEAR} ס״מ פנויים" + (f" (חסום ע״י {', '.join(blocked)})" if blocked else ""))
    key = ROOM.get("sleep", "crib")
    word = {"crib": "העריסה", "bunk": "מיטת הקומותיים"}[key]
    c = rects[key]
    under_window = c[1] < 20 and c[0] < ROOM["window"][1] and c[0] + c[2] > ROOM["window"][0]
    notes.append(f"✗ {word} מתחת לחלון" if under_window else f"✓ {word} לא מתחת לחלון")
    acz = ROOM.get("ac_zone", (ROOM["door"][0] - 30, ROOM["h"] - 140, 140, 140))
    near_ac = overlap(acz, c)
    notes.append(f"⚠ {word} קרובה לזרם של המזגן" if near_ac else f"✓ {word} רחוקה מהמזגן")
    return notes


def svg(name, items, scale=2):
    W, H = ROOM["w"], ROOM["h"]
    pad = 70
    s = scale
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{(W + 2 * pad) * s}" height="{(H + 2 * pad) * s}" '
           f'viewBox="{-pad} {-pad} {W + 2 * pad} {H + 2 * pad}" style="direction:rtl;font-family:Heebo">']
    out.append(f'<rect x="{-pad}" y="{-pad}" width="{W + 2 * pad}" height="{H + 2 * pad}" fill="#FBF7F1"/>')
    # 60 cm clear zones
    for it in items:
        fz = front_zone(it)
        if fz:
            out.append(f'<rect x="{fz[0]}" y="{fz[1]}" width="{fz[2]}" height="{fz[3]}" fill="#5F7356" opacity=".08"/>')
    # door swing
    dx0, dx1 = ROOM["door"]
    out.append(f'<path d="M{dx0},{H} L{dx0},{H - 80} A80,80 0 0,1 {dx1},{H}" fill="#8C7466" opacity=".08" stroke="#8C7466" stroke-dasharray="3 3" stroke-width=".8"/>')
    out.append(f'<line x1="{dx0}" y1="{H}" x2="{dx0}" y2="{H - 80}" stroke="#8C7466" stroke-width="2"/>')
    # furniture
    for _, x, y, w, h, col, f, lab in items:
        out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="2" fill="{col}" stroke="#4A3226" stroke-width=".8"/>')
        fs = 7 if min(w, h) < 60 else 8
        rot = f' transform="rotate(-90 {x + w / 2} {y + h / 2})"' if h > w * 1.4 else ""
        out.append(f'<text x="{x + w / 2}" y="{y + h / 2 + 2.5}" font-size="{fs}" text-anchor="middle" fill="#4A3226"{rot}>{iso(lab)}</text>')
    # walls
    out.append(f'<path d="M0,0 H{ROOM["window"][0]} M{ROOM["window"][1]},0 H{W} V{H} H{dx1} M{dx0},{H} H0 V0" fill="none" stroke="#4A3226" stroke-width="5" stroke-linecap="square"/>')
    wx0, wx1 = ROOM["window"]
    out.append(f'<rect x="{wx0}" y="-3" width="{wx1 - wx0}" height="6" fill="#D7DFCC" stroke="#5F7356"/>')
    out.append(f'<text x="{(wx0 + wx1) / 2}" y="-8" font-size="8" text-anchor="middle" fill="#5F7356">חלון {ROOM["window"][1] - ROOM["window"][0]} · ארגז תריס 25 ס״מ מהתקרה</text>')
    if "ac" not in ROOM:
        out.append(f'<rect x="{dx0}" y="{H + 4}" width="{dx1 - dx0}" height="5" fill="#E9D3CB" stroke="#A0665F" stroke-width=".6"/>')
    if "ac" not in ROOM:
        out.append(f'<text x="{(dx0 + dx1) / 2}" y="{H + 18}" font-size="7.5" text-anchor="middle" fill="#A0665F">מזגן מעל הדלת</text>')
    else:
        ax, ay, aw, ah = ROOM["ac"]
        out.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="#E9D3CB" stroke="#A0665F" stroke-width=".6"/>')
        out.append(f'<text x="{ax - 4}" y="{ay + ah / 2}" font-size="7" text-anchor="end" fill="#A0665F">{ROOM["ac_label"]}</text>')
    out.append(f'<text x="{(dx0 + dx1) / 2}" y="{H - 30}" font-size="8" text-anchor="middle" fill="#8C7466">דלת 80</text>')
    for ox, oy in ROOM["outlets"]:
        out.append(f'<circle cx="{ox}" cy="{oy}" r="4" fill="#fff" stroke="#A0665F" stroke-width="1.2"/>')
        out.append(f'<text x="{ox}" y="{oy + 16}" font-size="8" text-anchor="middle" fill="#A0665F">שקעים ?</text>')
    # dimensions
    out.append(f'<text x="{W / 2}" y="{-24}" font-size="9" text-anchor="middle" fill="#4A3226">{W} ס״מ</text>')
    out.append(f'<text x="{-14}" y="{H / 2}" font-size="9" text-anchor="middle" fill="#4A3226" transform="rotate(-90 {-14} {H / 2})">{H} ס״מ</text>')
    # scale bar
    out.append(f'<line x1="{W - 100}" y1="{H + 40}" x2="{W}" y2="{H + 40}" stroke="#4A3226" stroke-width="1.2"/>')
    out.append(f'<text x="{W - 50}" y="{H + 52}" font-size="7.5" text-anchor="middle" fill="#4A3226">1 מטר</text>')
    out.append('</svg>')
    return "".join(out)


def page(name, items):
    notes = check(items)
    li = "".join(f"<li>{iso(n)}</li>" for n in notes)
    return f"""<section class="p"><div class="h">אפשרות {name}</div>{svg(name, items)}
    <ul>{li}</ul><div class="legend"><span class="g"></span>60 ס״מ פנויים מול רהיט · <span class="d"></span>תנועת הדלת</div></section>"""


def main(out):
    os.makedirs(out, exist_ok=True)
    css = """@font-face{font-family:Heebo;src:url(file:///root/.fonts/Heebo.ttf);}
    body{margin:0;background:#FBF7F1;font-family:Heebo;color:#4A3226;direction:rtl}
    .p{width:900px;padding:28px 30px 24px;box-sizing:border-box}.h{font-size:26px;font-weight:500;margin-bottom:6px}
    svg{display:block;margin:0 auto}ul{columns:2;font-size:15px;line-height:1.7;padding:0 18px;margin:10px 0}
    .legend{font-size:13px;color:#8C7466}.legend span{display:inline-block;width:14px;height:14px;vertical-align:-2px;margin:0 6px}
    .g{background:#5F735622;border:1px solid #5F735655}.d{background:#8C746622;border:1px dashed #8C7466}"""
    paths = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--allow-file-access-from-files"])
        pg = b.new_page(viewport={"width": 900, "height": 900})
        for i, (name, items) in enumerate(OPTIONS.items(), 1):
            html = f"<!doctype html><meta charset=utf-8><style>{css}</style>{page(name, items)}"
            tmp = os.path.join(out, f"_plan{i}.html")
            open(tmp, "w", encoding="utf-8").write(html)
            pg.goto("file://" + tmp)
            pg.wait_for_timeout(300)
            path = os.path.join(out, f"plan_option_{i}.png")
            pg.query_selector(".p").screenshot(path=path)
            paths.append(path)
            print(path)
            for n in check(items):
                print("   ", n)
        b.close()


if __name__ == "__main__":
    main(sys.argv[1])
