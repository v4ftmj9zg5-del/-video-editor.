"""Animated Hebrew captions and hook title as an ASS file (rendered by libass,
which handles RTL via fribidi/harfbuzz)."""
import re

from .cuts import to_out

W, H = 1080, 1920


def ts(t):
    t = max(0.0, t)
    return f"{int(t // 3600)}:{int(t % 3600 // 60):02d}:{t % 60:05.2f}"


def header(p):
    bold = -1 if p["caption_bold"] else 0
    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{p['caption_font']},{p['caption_size']},{p['caption_colour']},{p['caption_colour']},&H00101010,&H90000000,{bold},0,0,0,100,100,{1 if p['caption_bold'] else 3},0,1,{6 if p['caption_bold'] else 0},{0 if p['caption_bold'] else 2},5,60,140,0,-1
Style: Display,Frank Ruhl Libre,118,&H00F7F4F0,&H00F7F4F0,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,5,0,0,0,-1
Style: Label,Heebo,44,&H00F7F4F0,&H00F7F4F0,&H00000000,&H00000000,0,0,0,0,100,100,10,0,1,0,0,5,0,0,0,-1
Style: Punch,Rubik,92,&H00141414,&H00141414,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,0,0,5,0,0,0,-1
Style: Box,Rubik,92,&H0047D9FF,&H0047D9FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def clean(w):
    return re.sub(r"[.…]+$", "", w)  # drop trailing full stops / ellipses


def chunks(phrases, timeline, p):
    """Caption chunks [(out_s, out_e, [(word, out_s, out_e)])] of a few words."""
    out = []
    for ph in phrases:
        words = []
        for w in ph["words"]:
            s, e = to_out(timeline, w["s"]), to_out(timeline, w["e"])
            if s is None or e is None:
                continue
            words.append((clean(w["w"]), s, e))
        cur = []
        for i, wd in enumerate(words):
            cur.append(wd)
            n_chars = sum(len(x[0]) + 1 for x in cur)
            last = i == len(words) - 1
            brk = (len(cur) >= p["caption_max_words"] or n_chars >= p["caption_max_chars"]
                   or re.search(r"[,?!:;]$", wd[0]))
            if brk or last:
                out.append(cur)
                cur = []
    res = []
    for i, c in enumerate(out):
        s, e = c[0][1], c[-1][2]
        nxt = out[i + 1][0][1] if i + 1 < len(out) else e + 0.6
        e = min(max(e + 0.15, s + 0.5), nxt)  # hold briefly, never overlap the next
        res.append((s, e, c))
    return res


def caption_events(phrases, timeline, p):
    ev = []
    y = p["caption_y"]
    for s, e, words in chunks(phrases, timeline, p):
        text = " ".join(w for w, _, _ in words)
        if p["caption_mode"] == "pop":
            # one event per spoken word: whole chunk visible, active word in accent colour;
            # the chunk pops in (scale overshoot) on its first word only
            for i, (w, ws, we) in enumerate(words):
                a = s if i == 0 else ws
                b = e if i == len(words) - 1 else words[i + 1][1]
                parts = []
                for j, (wj, _, _) in enumerate(words):
                    col = p["caption_accent"] if j == i else p["caption_colour"]
                    parts.append(f"{{\\1c{col[2:]}&}}{wj}")
                anim = (f"\\an5\\pos({W // 2},{y})" +
                        ("\\fscx72\\fscy72\\t(0,90,\\fscx108\\fscy108)\\t(90,170,\\fscx100\\fscy100)"
                         if i == 0 else ""))
                ev.append(f"Dialogue: 2,{ts(a)},{ts(b)},Cap,,0,0,0,,{{{anim}}}" + " ".join(parts))
        else:
            # soft fade with a small rise and slight letter-spacing settle
            anim = (f"\\an5\\move({W // 2},{y + 14},{W // 2},{y},0,420)\\fad(260,220)"
                    f"\\fsp6\\t(0,600,\\fsp3)")
            # soft dark halo underneath keeps thin type readable on bright rooms
            ev.append(f"Dialogue: 1,{ts(s)},{ts(e)},Cap,,0,0,0,,"
                      f"{{{anim}\\bord9\\3c&H000000&\\blur20\\alpha&HB4&\\1a&HFF&\\shad0}}{text}")
            ev.append(f"Dialogue: 2,{ts(s)},{ts(e)},Cap,,0,0,0,,{{{anim}}}{text}")
    return ev


def title_events(title, p, dur):
    """Hook title over the first ~2.4 s."""
    if not title:
        return []
    st, en = 0.15, min(2.6, dur)
    if p["title_mode"] == "serif":
        y = 760
        anim = (f"\\an5\\fad(450,350)\\move({W // 2},{y + 28},{W // 2},{y},0,800)"
                f"\\fsp14\\t(0,1100,0.45,\\fsp2)")
        return [
            f"Dialogue: 1,{ts(st)},{ts(en)},Label,,0,0,0,,{{\\an5\\pos({W // 2},{y - 110})"
            f"\\fscx0\\fad(0,350)\\t(0,700,0.5,\\fscx100)\\p1}}m -90 0 l 90 0 90 2 -90 2{{\\p0}}",
            f"Dialogue: 0,{ts(st)},{ts(en)},Display,,0,0,0,,"
            f"{{{anim}\\bord10\\3c&H000000&\\blur22\\alpha&HC8&\\1a&HFF&}}{title}",
            f"Dialogue: 1,{ts(st)},{ts(en)},Display,,0,0,0,,{{{anim}\\blur0.6}}{title}",
        ]
    # dynamic: accent box wipes open, bold text pops in on top
    y = 700
    wbox = min(980, 60 + 54 * len(title))
    hb = 70
    box = f"m 0 0 l {wbox} 0 {wbox} {2 * hb} 0 {2 * hb}"  # \an5 centres it on \pos
    return [
        f"Dialogue: 0,{ts(st)},{ts(en)},Box,,0,0,0,,{{\\an5\\pos({W // 2},{y})\\fscx0"
        f"\\t(0,220,0.5,\\fscx100)\\fad(0,200)\\p1}}{box}{{\\p0}}",
        f"Dialogue: 1,{ts(st + 0.12)},{ts(en)},Punch,,0,0,0,,{{\\an5\\pos({W // 2},{y})"
        f"\\fscx60\\fscy60\\t(0,120,\\fscx106\\fscy106)\\t(120,200,\\fscx100\\fscy100)"
        f"\\fad(80,200)}}{title}",
    ]


def write(path, phrases, timeline, p, title, dur):
    lines = title_events(title, p, dur) + caption_events(phrases, timeline, p)
    with open(path, "w", encoding="utf-8") as f:
        f.write(header(p) + "\n".join(lines) + "\n")
    return len(lines)
