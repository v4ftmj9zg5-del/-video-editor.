"""Build a SketchUp model of a room + layout options from one geometry description.

Outputs, from the same parts list (cm; X = plan x, Y = north i.e. away from the door wall, Z up):
  <name>.rb     Ruby script for SketchUp (Window > Ruby Console, or Extensions load):
                builds named groups with materials; each layout option on its own tag.
  <name>_A.dae / <name>_B.dae   COLLADA in metres (File > Import) as a fallback.
  <name>_preview.png            quick isometric check render.

Usage: sketchup_room.py OUT_DIR
"""
import os
import sys

import numpy as np
import trimesh

W, D, H = 310, 280, 260        # inner width (x), depth (y), height
T = 12                          # wall thickness
WIN = (90, 230, 95, 210)        # window x0, x1, sill z, head z (head height assumed)
DOOR = (25, 105, 210)           # door x0, x1, head z
NAME = "noa_levi_nursery"
TITLE = "חדר תינוקת - משפחת לוי"

MATS = {
    "קיר": (242, 239, 233), "רצפה": (205, 205, 200), "זכוכית": (190, 214, 222), "דלת": (250, 250, 248),
    "מזגן": (245, 245, 245), "לבן": (248, 247, 243), "מזרן": (236, 228, 220), "עץ": (201, 169, 139),
    "כורסה": (160, 160, 158), "מרווה": (110, 127, 94), "ורוד": (217, 184, 174), "קש": (196, 164, 116),
    "שטיח": (226, 214, 196), "ידית": (180, 150, 115),
}


def box(name, mat, x0, y0, z0, x1, y1, z1, group=None):
    return dict(kind="box", name=name, mat=mat, a=(x0, y0, z0), b=(x1, y1, z1), group=group)


def cyl(name, mat, cx, cy, z0, r, h, group=None):
    return dict(kind="cyl", name=name, mat=mat, c=(cx, cy, z0), r=r, h=h, group=group)


def room():
    wx0, wx1, sill, whead = WIN
    dx0, dx1, dhead = DOOR
    g = "קירות"
    p = [
        box("רצפה", "רצפה", 0, 0, -1, W, D, 0, "רצפה"),
        # north (window) wall
        box("קיר חלון שמאל", "קיר", -T, D, 0, wx0, D + T, H, g),
        box("קיר חלון ימין", "קיר", wx1, D, 0, W + T, D + T, H, g),
        box("אדן חלון", "קיר", wx0, D, 0, wx1, D + T, sill, g),
        box("משקוף חלון", "קיר", wx0, D, whead, wx1, D + T, H, g),
        # south (door) wall
        box("קיר דלת שמאל", "קיר", -T, -T, 0, dx0, 0, H, g),
        box("קיר דלת ימין", "קיר", dx1, -T, 0, W + T, 0, H, g),
        box("משקוף דלת", "קיר", dx0, -T, dhead, dx1, 0, H, g),
        # side walls
        box("קיר מערבי", "קיר", -T, 0, 0, 0, D, H, g),
        box("קיר מזרחי", "קיר", W, 0, 0, W + T, D, H, g),
        # openings & fixtures
        box("זכוכית חלון", "זכוכית", wx0, D + 5, sill, wx1, D + 6, whead, "חלון"),
        box("ארגז תריס (לאמת עומק)", "קיר", wx0 - 5, D - 18, H - 25, wx1 + 5, D, H, "חלון"),
        box("כנף דלת (פתוחה)", "דלת", dx0, 0, 0, dx0 + 4, dx1 - dx0, 205, "דלת"),
        box("מזגן", "מזגן", dx0, 0, 222, dx1, 20, 250, "מזגן"),
        box("שקע (לאמת מיקום)", "לבן", 266, 0, 30, 274, 1, 38, "שקעים"),
    ]
    return p


def crib(x0, y0, grp):
    x1, y1 = x0 + 66, y0 + 124
    p = [box("ראש עריסה", "לבן", x0, y0, 0, x1, y0 + 3, 86, grp),
         box("רגלי עריסה", "לבן", x0, y1 - 3, 0, x1, y1, 86, grp),
         box("מזרן 60×120", "מזרן", x0 + 3, y0 + 3, 27, x1 - 3, y1 - 3, 39, grp)]
    for xa in (x0, x1 - 3):
        p += [box("מעקה עליון", "לבן", xa, y0 + 3, 81, xa + 3, y1 - 3, 86, grp),
              box("מעקה תחתון", "לבן", xa, y0 + 3, 22, xa + 3, y1 - 3, 27, grp)]
        for i in range(1, 13):
            y = y0 + 3 + i * (118 / 13) - 1.25
            p.append(box("שלב", "לבן", xa + .25, y, 27, xa + 2.75, y + 2.5, 81, grp))
    return p


def chair_corner(grp):
    return [box("משענת כורסה", "כורסה", 235, 265, 0, 310, 280, 90, grp),
            box("ידית שמאל", "כורסה", 235, 200, 0, 247, 265, 60, grp),
            box("ידית ימין", "כורסה", 298, 200, 0, 310, 265, 60, grp),
            box("מושב", "כורסה", 247, 200, 0, 298, 265, 42, grp),
            cyl("שולחן צד", "עץ", 213, 210, 0, 18, 50, grp)]


def books_corner(grp):
    return [box("מדף תמונות תחתון", "מרווה", 0, 220, 55, 10, 275, 62, grp),
            box("מדף תמונות עליון", "מרווה", 0, 220, 95, 10, 275, 102, grp),
            cyl("כרית רצפה", "ורוד", 42, 244, 0, 24, 12, grp),
            box("סלסלה", "קש", 52, 254, 0, 78, 276, 25, grp)]


def option_a():
    return (crib(244, 66, "עריסה") +
            [box("ארון 100×58", "לבן", 0, 80, 0, 58, 180, 200, "ארון"),
             box("ידית", "ידית", 58, 126, 100, 60, 128, 115, "ארון"),
             box("ידית", "ידית", 58, 132, 100, 60, 134, 115, "ארון"),
             box("שידה HEMNES", "לבן", 120, 0, 0, 228, 50, 96, "שידה"),
             box("משטח החתלה", "מזרן", 139, 0, 96, 209, 50, 106, "שידה")] +
            chair_corner("פינת הנקה") + books_corner("פינת ספרים") +
            [cyl("שטיח", "שטיח", 160, 130, 0, 70, 1, "שטיח")])


def option_b():
    return (crib(0, 86, "עריסה") +
            [box("ארון 90×58", "לבן", 115, 0, 0, 205, 58, 200, "ארון"),
             box("ידית", "ידית", 156, 58, 100, 158, 60, 115, "ארון"),
             box("ידית", "ידית", 162, 58, 100, 164, 60, 115, "ארון"),
             box("שידה HEMNES", "לבן", 260, 62, 0, 310, 170, 96, "שידה"),
             box("משטח החתלה", "מזרן", 260, 81, 96, 310, 151, 106, "שידה")] +
            chair_corner("פינת הנקה") + books_corner("פינת ספרים") +
            [cyl("שטיח", "שטיח", 150, 140, 0, 55, 1, "שטיח")])


# ------------------------------------------------------------------ Ruby for SketchUp
def ruby(parts_room, options):
    L = ["# encoding: utf-8",
         f"# {TITLE} — נבנה אוטומטית. הדביקי ב-Window > Ruby Console, או: load 'C:/path/{NAME}.rb'",
         "model = Sketchup.active_model",
         f"model.start_operation('{TITLE}', true)",
         "ents = model.active_entities",
         "MATS = {}",
         "def mat(model, name, rgb)",
         "  MATS[name] ||= (model.materials[name] || model.materials.add(name)).tap { |m| m.color = Sketchup::Color.new(*rgb) }",
         "end",
         "def tag(model, name)",
         "  model.layers[name] || model.layers.add(name)",
         "end",
         "def mkbox(ents, name, a, b, material)",
         "  g = ents.add_group",
         "  g.name = name",
         "  pts = [[a[0].cm, a[1].cm, a[2].cm], [b[0].cm, a[1].cm, a[2].cm], [b[0].cm, b[1].cm, a[2].cm], [a[0].cm, b[1].cm, a[2].cm]]",
         "  f = g.entities.add_face(pts)",
         "  f.reverse! if f.normal.z < 0",
         "  f.pushpull((b[2] - a[2]).cm)",
         "  g.material = material",
         "  g",
         "end",
         "def mkcyl(ents, name, c, r, h, material)",
         "  g = ents.add_group",
         "  g.name = name",
         "  edges = g.entities.add_circle(Geom::Point3d.new(c[0].cm, c[1].cm, c[2].cm), Z_AXIS, r.cm, 32)",
         "  f = g.entities.add_face(edges)",
         "  f.reverse! if f.normal.z < 0",
         "  f.pushpull(h.cm)",
         "  g.material = material",
         "  g",
         "end"]
    for k, rgb in MATS.items():
        L.append(f"mat(model, '{k}', {list(rgb)})")
    MATS_GLASS = "MATS['זכוכית'].alpha = 0.35"
    L.append(MATS_GLASS)

    def emit(parts, tagname, top_name):
        L.append(f"top = ents.add_group; top.name = '{top_name}'; top.layer = tag(model, '{tagname}')")
        groups = {}
        for p in parts:
            gname = p["group"] or "שונות"
            if gname not in groups:
                var = f"g{len(groups)}"
                groups[gname] = var
                L.append(f"{var} = top.entities.add_group; {var}.name = '{gname}'")
            var = groups[gname]
            if p["kind"] == "box":
                L.append(f"mkbox({var}.entities, '{p['name']}', {list(p['a'])}, {list(p['b'])}, MATS['{p['mat']}'])")
            else:
                L.append(f"mkcyl({var}.entities, '{p['name']}', {list(p['c'])}, {p['r']}, {p['h']}, MATS['{p['mat']}'])")

    emit(parts_room, "חדר", "חדר · קירות ופתחים")
    for i, (label, parts) in enumerate(options):
        emit(parts, label, f"העמדה · {label}")
        if i > 0:
            L.append(f"tag(model, '{label}').visible = false")
    L += ["model.commit_operation",
          "cam = Sketchup::Camera.new([20.cm, -10.cm, 210.cm], [200.cm, 200.cm, 60.cm], Z_AXIS)",
          "cam.fov = 70 if cam.respond_to?(:fov=)",
          "model.active_view.camera = cam",
          "puts 'נבנה: " + TITLE + ". החלפה בין האפשרויות: חלון Tags.'"]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ COLLADA (metres)
def meshes(parts):
    out = []
    for p in parts:
        if p["kind"] == "box":
            a, b = np.array(p["a"], float), np.array(p["b"], float)
            m = trimesh.creation.box(extents=(b - a) / 100, transform=trimesh.transformations.translation_matrix((a + b) / 200))
        else:
            cx, cy, z0 = p["c"]
            m = trimesh.creation.cylinder(radius=p["r"] / 100, height=p["h"] / 100, sections=32,
                                          transform=trimesh.transformations.translation_matrix((cx / 100, cy / 100, (z0 + p["h"] / 2) / 100)))
        m.visual.face_colors = (*MATS[p["mat"]], 90 if p["mat"] == "זכוכית" else 255)
        out.append((p["name"], m))
    return out


def write_dae(path, parts):
    scene = trimesh.Scene()
    for i, (n, m) in enumerate(meshes(parts)):
        scene.add_geometry(m, node_name=f"part_{i}", geom_name=f"part_{i}")
    xml = trimesh.exchange.dae.export_collada([g for g in scene.dump()]).decode("utf-8")
    # model is Z-up in metres (SketchUp's convention); trimesh writes Y_UP with no unit
    xml = xml.replace("<up_axis>Y_UP</up_axis>", '<unit name="meter" meter="1"/>\n    <up_axis>Z_UP</up_axis>', 1)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(xml)


def preview(path, parts, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(8, 7), dpi=110)
    ax = fig.add_subplot(111, projection="3d")
    polys, cols = [], []
    for p in parts:
        if p["name"].startswith(("קיר מזרחי", "קיר דלת", "משקוף דלת")):   # cut-away so we can see in
            continue
        (n, m), = meshes([p])
        rgba = (*(np.array(MATS[p["mat"]]) / 255), .35 if p["mat"] == "זכוכית" else 1)
        for f in m.faces:
            polys.append(m.vertices[f] * 100)
            cols.append(rgba)
    # one collection so faces are depth-sorted individually (per-object sorting hides parts)
    ax.add_collection3d(Poly3DCollection(polys, facecolors=cols, edgecolor=(0, 0, 0, .12), linewidths=.2))
    ax.set_xlim(-20, 330); ax.set_ylim(-20, 300); ax.set_zlim(0, 270)
    ax.set_box_aspect((350, 320, 270))
    ax.view_init(elev=32, azim=-62)
    ax.set_axis_off()
    ax.set_title(title[::-1] if False else title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def main(out):
    os.makedirs(out, exist_ok=True)
    r = room()
    opts = [("אפשרות א", option_a()), ("אפשרות ב", option_b())]
    open(os.path.join(out, f"{NAME}.rb"), "w", encoding="utf-8").write(ruby(r, opts))
    for key, (_, parts) in zip("AB", opts):
        write_dae(os.path.join(out, f"{NAME}_{key}.dae"), r + parts)
        preview(os.path.join(out, f"{NAME}_preview_{key}.png"), r + parts, f"option {key}")
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
