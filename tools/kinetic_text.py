"""Kinetic Hebrew text layer for Reels: word-by-word rise-and-fade, rendered with PIL/raqm (correct RTL).

Writes raw RGBA frames (1080x1920) to stdout, to be piped into ffmpeg as an overlay:
  python3 kinetic_text.py PLAN.json | ffmpeg -f rawvideo -pix_fmt rgba -s 1080x1920 -r 30 -i - ...

PLAN = {
  "fonts_dir": "path/with/heebo-300.ttf, heebo-800.ttf ...",
  "duration": 15.36, "fps": 30,
  "color": [58, 38, 28], "glow": [250, 245, 238], "accent": [122, 138, 96],
  "cards": [
    {"start": 0.15, "end": 2.95, "y": 600, "accent": true,
     "lines": [ [["חדר", 800, 128], ["ילדים", 800, 128]],
                [["הוא", 300, 58], ["לא", 300, 58], ["רק", 300, 58], ["מקום", 300, 58], ["לישון", 300, 58]] ]}
  ]}
Each line is a list of [word, weight, size] in logical (reading) order.
"""
import json
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def main(plan_path):
    P = json.load(open(plan_path))
    fps = P.get("fps", 30)
    col = tuple(P.get("color", [58, 38, 28]))
    glow = tuple(P.get("glow", [250, 245, 238]))
    acc = tuple(P.get("accent", [122, 138, 96]))
    fonts = {}

    def font(w, s):
        k = (w, s)
        if k not in fonts:
            fonts[k] = ImageFont.truetype(f"{P['fonts_dir']}/heebo-{w}.ttf", s, layout_engine=ImageFont.Layout.RAQM)
        return fonts[k]

    # pre-render every word as a sprite (text + soft glow) and lay out lines right-to-left
    cards = []
    for c in P["cards"]:
        sprites, line_h, y = [], [], 0
        layout = []
        for line in c["lines"]:
            fs = [font(w, s) for _, w, s in line]
            asc = max(f.getmetrics()[0] for f in fs)
            desc = max(f.getmetrics()[1] for f in fs)
            gaps = [max(f.getlength(" ", direction="rtl"), s * .3) for f, (_, _, s) in zip(fs, line)]
            widths = [f.getlength(t, direction="rtl", language="he") for (t, _, _), f in zip(line, fs)]
            total = sum(widths) + sum(gaps[:-1])
            cx = c.get("x", W / 2)
            x_right = cx + total / 2
            row = []
            for (t, _, _), f, wd, g in zip(line, fs, widths, gaps):
                x = x_right - wd
                row.append((t, f, x, wd))
                x_right = x - g
            layout.append((row, asc, desc))
            line_h.append(asc + desc)
        block = sum(line_h) + 10 * (len(line_h) - 1)
        top = c["y"] - block / 2
        for row, asc, desc in layout:
            for t, f, x, wd in row:
                pad = 28
                im = Image.new("RGBA", (int(wd) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
                d = ImageDraw.Draw(im)
                d.text((pad, pad + asc), t, font=f, fill=glow + (255,), anchor="ls", direction="rtl", language="he")
                ga = im.getchannel("A").filter(ImageFilter.GaussianBlur(16)).point(lambda v: min(255, int(v * 2.2)))
                g = Image.new("RGBA", im.size, glow + (0,))
                g.putalpha(ga)
                txt = Image.new("RGBA", im.size, (0, 0, 0, 0))
                ImageDraw.Draw(txt).text((pad, pad + asc), t, font=f, fill=col + (255,), anchor="ls",
                                         direction="rtl", language="he")
                spr = Image.alpha_composite(g, txt)
                sprites.append((spr, int(x - pad), int(top - pad)))
            top += asc + desc + 10
        cards.append((c, sprites, c["y"] - block / 2))

    n = int(round(P["duration"] * fps))
    out = sys.stdout.buffer
    for i in range(n):
        t = i / fps
        frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for c, sprites, block_top in cards:
            s, e = c["start"], c["end"]
            if not (s <= t <= e):
                continue
            exit_p = ease_out((t - (e - .32)) / .32) if t > e - .32 else 0.0
            if c.get("accent"):
                p = ease_out((t - s) / .6)
                wline = int(90 * p)
                a = int(255 * p * (1 - exit_p))
                if wline > 0:
                    ImageDraw.Draw(frame).rectangle(
                        (int(c.get("x", W / 2)) - wline // 2, int(block_top - 46), int(c.get("x", W / 2)) + wline // 2, int(block_top - 43)),
                        fill=acc + (a,))
            for k, (spr, x, y) in enumerate(sprites):
                p = ease_out((t - s - .08 * k) / .5)
                if p <= 0:
                    continue
                alpha = p * (1 - exit_p)
                dy = int(34 * (1 - p) - 12 * exit_p)
                sp = spr
                if alpha < .999:
                    sp = spr.copy()
                    sp.putalpha(spr.getchannel("A").point(lambda v, a=alpha: int(v * a)))
                frame.alpha_composite(sp, (x, y + dy))
        out.write(frame.tobytes())


if __name__ == "__main__":
    main(sys.argv[1])
