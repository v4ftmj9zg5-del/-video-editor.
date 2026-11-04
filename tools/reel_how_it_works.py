"""'How it works' Reel for Room Story Tell (1080x1920, 30 fps, ~24.5 s).

Scenes: hook on a real photo -> 4 process steps (questionnaire, CAD plan, moodboard,
render + shopping list) -> the designer's own kids' room -> CTA on her portrait.
All motion is eased; text stays inside Instagram's safe area.

Usage: reel_how_it_works.py ASSETS_DIR OUT.mp4
"""
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30
BG = (240, 238, 231)
INK = (43, 33, 28)
ROSE = (185, 133, 123)
SAFE_R = W - 140          # right edge for text (IG action rail)
FONTS = os.path.expanduser("~/.fonts")
XF = 0.32                 # crossfade seconds


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size, layout_engine=ImageFont.Layout.RAQM)
    if weight:
        f.set_variation_by_axes([weight])
    return f


def ease_out(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def ease_io(t):
    t = min(max(t, 0), 1)
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def text_layer(lines, fnt, fill, align="right", spacing=1.18, shadow=False, width=W):
    """RGBA strip with RTL lines right-aligned at SAFE_R (or centred)."""
    asc, desc = fnt.getmetrics()
    lh = int((asc + desc) * spacing)
    img = Image.new("RGBA", (width, lh * len(lines) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        x, anchor = (SAFE_R, "ra") if align == "right" else (width // 2, "ma")
        d.text((x, i * lh + 6), "‏" + ln, font=fnt, fill=fill, anchor=anchor, direction="rtl", language="he")
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(10)).point(lambda a: a * .55))
        out = Image.new("RGBA", img.size, (0, 0, 0, 0))
        out.alpha_composite(sh)
        out.alpha_composite(img)
        return out
    return img


def paste_fade(base, layer, xy, alpha):
    if alpha <= 0:
        return
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda a: int(a * alpha)))
    base.alpha_composite(layer, (int(xy[0]), int(xy[1])))


def cover(img, w, h, zoom=1.0, fx=.5, fy=.5):
    """Crop-to-fill with zoom, focus point fx/fy (0..1)."""
    sw, sh = img.size
    s = max(w / sw, h / sh) * zoom
    cw, ch = w / s, h / s
    x0 = min(max(fx * sw - cw / 2, 0), sw - cw)
    y0 = min(max(fy * sh - ch / 2, 0), sh - ch)
    return img.resize((w, h), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))


def card(img, w, h, radius=18):
    """Rounded card with soft shadow -> RGBA (w+60, h+60), content offset 30."""
    c = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), radius, fill=255)
    sh = Image.new("L", (w + 60, h + 60), 0)
    sh.paste(m.point(lambda a: int(a * .22)), (30, 40))
    sh = sh.filter(ImageFilter.GaussianBlur(16))
    c.paste((60, 45, 35, 255), (0, 0), sh)
    body = img.convert("RGBA").resize((w, h), Image.LANCZOS)
    body.putalpha(m)
    c.alpha_composite(body, (30, 30))
    return c


def gradient(h0, h1, a0, a1):
    g = Image.new("L", (1, H), 0)
    for y in range(H):
        t = min(max((y - h0) / max(h1 - h0, 1), 0), 1)
        g.putpixel((0, y), int(255 * (a0 + (a1 - a0) * t)))
    layer = Image.new("RGBA", (W, H), (20, 14, 10, 255))
    layer.putalpha(g.resize((W, H)))
    return layer


def grade(img):
    """Shared warm, gentle grade for photos."""
    r, g, b = img.split()
    r = r.point(lambda v: min(255, int(v * 1.02 + 3)))
    b = b.point(lambda v: int(v * .97))
    return Image.merge("RGB", (r, g, b))


class Reel:
    def __init__(self, A):
        L = lambda f: Image.open(os.path.join(A, f)).convert("RGB")
        self.shelf, self.stroller, self.bear, self.bed = (grade(L(f)) for f in ("shelf.png", "stroller.png", "bear.jpg", "bed.png"))
        self.portrait = L("portrait.jpg")
        self.render = grade(L("render.jpg"))
        cad = L("cad.png")
        self.cad = cad.crop((900, 110, 2210, 1420))
        lst = L("list-1.png")
        self.list = lst.crop((470, 285, 1815, 870))
        self.q, self.m, self.mood = L("q-1.png"), L("m-1.png"), L("mood-2.png")

        self.f_hook = font("Heebo.ttf", 92, 300)
        self.f_title = font("Heebo.ttf", 64, 400)
        self.f_num = font("GveretLevin.ttf", 190)
        self.f_hand = font("GveretLevin.ttf", 132)
        self.f_small = font("Heebo.ttf", 44, 300)
        self.f_handle = font("Heebo.ttf", 38, 400)

        self.t_hook = text_layer(["החדר של הילדים", "מחכה כבר חודשים?"], self.f_hook, (255, 255, 255, 255), shadow=True)
        self.g_bottom = gradient(800, 1700, 0, .72)
        self.g_hook = gradient(650, 1500, 0, .82)
        self.steps = [
            ("1", ["שולחת לי תמונות", "ומידות של החדר"]),
            ("2", ["מקבלת תוכנית", "העמדה מדויקת"]),
            ("3", ["בוחרות יחד", "את הכיוון"]),
            ("4", ["הדמיה + רשימת קניות", "לפי התקציב"]),
        ]
        self.t_steps = [(text_layer([n], self.f_num, ROSE + (255,)), text_layer(t, self.f_title, INK + (255,))) for n, t in self.steps]
        self.t_room = text_layer(["ואת יוצרת את החדר", "בעצמך"], self.f_hook, (255, 255, 255, 255), shadow=True)
        self.t_cta1 = text_layer(["רוצה להיות מהראשונות?"], self.f_small, (255, 255, 255, 255), shadow=True)
        self.t_cta2 = text_layer(["כתבו לי ״חדר״"], self.f_hand, (255, 255, 255, 255), shadow=True)
        self.t_handle = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
        ImageDraw.Draw(self.t_handle).text((SAFE_R, 8), "@roomstorytell_", font=self.f_handle, fill=(255, 255, 255, 230), anchor="ra")

        self.cta_times = (.15, .45, .8)   # question, "כתבו לי חדר", handle (overridable to sync with VO)
        # cards prepared once
        self.c_m = card(self.m, 520, 736)
        self.c_q = card(self.q, 520, 736)
        self.c_mood = card(self.mood, 860, 688)
        self.c_render = card(self.render, 500, 666)
        self.c_list = card(self.list, 560, 244, radius=12)

    # ------------------------------------------------------------------ scenes (t in seconds, local)
    def hook(self, t, d):
        img = cover(self.shelf, W, H, zoom=1.0 + .07 * ease_io(t / d), fx=.56, fy=.45).convert("RGBA")
        img.alpha_composite(self.g_hook)
        k = max(.85, ease_out(t / .3))   # hook readable from frame 1
        paste_fade(img, self.t_hook, (0, 1150 + 40 * (1 - k)), k)
        return img

    def step_frame(self, i, t):
        img = Image.new("RGBA", (W, H), BG + (255,))
        num, title = self.t_steps[i]
        k1, k2 = ease_out(t / .5), ease_out((t - .12) / .55)
        paste_fade(img, num, (0, 250 + 30 * (1 - k1)), k1)
        paste_fade(img, title, (0, 470 + 30 * (1 - k2)), k2)
        return img

    def step1(self, t, d):
        img = self.step_frame(0, t)
        a, b = ease_out((t - .25) / .6), ease_out((t - .7) / .6)
        paste_fade(img, self.c_m, (90, 690 + 80 * (1 - a)), a)
        paste_fade(img, self.c_q, (390, 760 + 80 * (1 - b)), b)
        return img

    def step2(self, t, d):
        img = self.step_frame(1, t)
        a = ease_out((t - .25) / .6)
        z = 1.0 + .22 * ease_io((t - .5) / (d - .5))
        inner = cover(self.cad, 800, 800, zoom=z, fx=.62, fy=.55)
        paste_fade(img, card(inner, 800, 800), (110 - 30, 670 + 70 * (1 - a)), a)
        return img

    def step3(self, t, d):
        img = self.step_frame(2, t)
        a = ease_out((t - .2) / .5)
        c = self.c_mood.copy()
        reveal = ease_io((t - .25) / 1.1)          # right-to-left wipe
        if reveal < 1:
            keep = int(c.width * reveal)
            mask = Image.new("L", c.size, 0)
            ImageDraw.Draw(mask).rectangle((c.width - keep, 0, c.width, c.height), fill=255)
            c.putalpha(Image.composite(c.getchannel("A"), mask, mask))
        paste_fade(img, c, (80 - 30, 700 + 40 * (1 - a)), a)
        return img

    def step4(self, t, d):
        img = self.step_frame(3, t)
        a, b = ease_out((t - .2) / .6), ease_out((t - .9) / .6)
        paste_fade(img, self.c_render, (390, 690 + 70 * (1 - a)), a)
        paste_fade(img, self.c_list, (40 - 120 * (1 - b), 1240), b)
        return img

    def room(self, t, d):
        cuts = [(self.bear, .5, .45), (self.stroller, .5, .55), (self.bed, .55, .6)]
        seg = d / len(cuts)
        i = min(int(t / seg), len(cuts) - 1)
        src, fx, fy = cuts[i]
        lt = (t - i * seg) / seg
        img = cover(src, W, H, zoom=1.04 + .05 * lt, fx=fx, fy=fy).convert("RGBA")
        img.alpha_composite(self.g_bottom)
        k = ease_out((t - .2) / .5)
        paste_fade(img, self.t_room, (0, 1180 + 30 * (1 - k)), k)
        return img

    def cta(self, t, d):
        img = cover(self.portrait, W, H, zoom=1.0 + .05 * ease_io(t / d), fx=.5, fy=.42).convert("RGBA")
        img.alpha_composite(self.g_bottom)
        k1, k2, k3 = (ease_out((t - s) / .5) for s in self.cta_times)
        paste_fade(img, self.t_cta1, (0, 1060 + 25 * (1 - k1)), k1)
        paste_fade(img, self.t_cta2, (0, 1140 + 30 * (1 - k2)), k2)
        paste_fade(img, self.t_handle, (0, 1390), k3)
        return img

    def timeline(self):
        return [(self.hook, 2.4), (self.step1, 3.8), (self.step2, 3.8), (self.step3, 3.8),
                (self.step4, 4.0), (self.room, 3.2), (self.cta, 3.5)]


def render(A, out, durations=None, cta_times=None):
    r = Reel(A)
    if cta_times:
        r.cta_times = tuple(cta_times)
    tl = r.timeline()
    if durations:
        tl = [(fn, d) for (fn, _), d in zip(tl, durations)]
    starts, s = [], 0.0
    for _, d in tl:
        starts.append(s)
        s += d
    total = s
    n = int(round(total * FPS))
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
           "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-preset", "slow", "-crf", "19", "-maxrate", "11M", "-bufsize", "16M",
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(n):
        t = f / FPS
        i = max(k for k, st in enumerate(starts) if st <= t)
        fn, d = tl[i]
        frame = fn(t - starts[i], d)
        # crossfade into the next scene during the last XF seconds
        if i + 1 < len(tl) and t > starts[i + 1] - XF:
            nxt = tl[i + 1][0](t - starts[i + 1], tl[i + 1][1])   # negative local time = pre-roll
            k = ease_io((t - (starts[i + 1] - XF)) / XF)
            frame = Image.blend(frame, nxt, k)
        p.stdin.write(frame.convert("RGB").tobytes())
    p.stdin.close()
    p.wait()
    print(f"wrote {out} ({total:.1f}s, {n} frames)")


if __name__ == "__main__":
    # optional 3rd arg: JSON {"durations": [...], "cta_times": [...]} to sync with a soundtrack
    opts = __import__("json").load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
    render(sys.argv[1], sys.argv[2], opts.get("durations"), opts.get("cta_times"))
