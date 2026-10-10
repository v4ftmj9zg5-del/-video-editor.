"""Elegant animated Hebrew titles (ASS/libass) + synthesized transition SFX.

Usage:
  titles.py ass OUT.ass               write the subtitle/titles file
  titles.py sfx OUT.wav DURATION      write the sound-design track
  titles.py mux BASE.mp4 OUT.mp4      burn titles + add sfx onto a rendered base
"""
import os
import subprocess
import sys
import tempfile

W, H = 1080, 1920

# Editorial pairing: serif display (Frank Ruhl Libre) + clean sans labels (Heebo).
HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Display,Frank Ruhl Libre,128,&H00F7F4F0,&H00F7F4F0,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,5,0,0,0,-1
Style: Label,Heebo,46,&H00F7F4F0,&H00F7F4F0,&H00000000,&H00000000,0,0,0,0,100,100,10,0,1,0,0,5,0,0,0,-1
Style: Glow,Frank Ruhl Libre,128,&H00000000,&H00000000,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,0,0,5,0,0,0,-1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

# (start, end, kind, text, y)  — kinds: display / label / rule
TITLES = [
    # hook
    (0.35, 2.75, "label", "סיור בבית", 780),
    (0.55, 2.75, "rule", "", 830),
    (0.75, 2.75, "display", "הבית שעיצבתי", 920),
    # chapter captions
    (5.85, 8.15, "rule", "", 1380),
    (5.95, 8.15, "label", "חומרים טבעיים", 1430),
    (11.55, 13.65, "rule", "", 1380),
    (11.65, 13.65, "label", "טקסטורות חמות", 1430),
    # end card
    (19.2, 22.6, "label", "עיצוב פנים", 760),
    (19.4, 22.6, "rule", "", 810),
    (19.6, 22.6, "display", "בית שמרגיש כמוך", 900),
    (20.3, 22.6, "label", "לתיאום פגישת ייעוץ · שלחו הודעה", 1010),
]


def ts(t):
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def ass_lines():
    out = []
    for st, en, kind, text, y in TITLES:
        a, b = ts(st), ts(en)
        if kind == "rule":
            # thin hairline that grows from the centre
            out.append(f"Dialogue: 1,{a},{b},Label,,0,0,0,,"
                       f"{{\\an5\\pos({W // 2},{y})\\fscx0\\fad(0,350)"
                       f"\\t(0,700,0.5,\\fscx100)\\p1}}m -90 0 l 90 0 90 2 -90 2{{\\p0}}")
            continue
        style = "Display" if kind == "display" else "Label"
        sp0, sp1 = (14, 2) if kind == "display" else (22, 10)
        anim = (f"\\an5\\fad(450,350)\\move({W // 2},{y + 28},{W // 2},{y},0,800)"
                f"\\fsp{sp0}\\t(0,1100,0.45,\\fsp{sp1})")
        if kind == "display":
            # soft dark halo underneath for legibility on bright frames
            out.append(f"Dialogue: 0,{a},{b},Glow,,0,0,0,,"
                       f"{{{anim}\\bord10\\3c&H000000&\\blur22\\alpha&HC8&\\1a&HFF&}}{text}")
        else:
            out.append(f"Dialogue: 0,{a},{b},Label,,0,0,0,,"
                       f"{{{anim}\\bord6\\3c&H000000&\\blur16\\alpha&HD0&\\1a&HFF&}}{text}")
        out.append(f"Dialogue: 1,{a},{b},{style},,0,0,0,,{{{anim}\\blur0.6}}{text}")
    return HEADER + "\n".join(out) + "\n"


# --------------------------------------------------------------- sound design
# (time, kind): whoosh on hard cuts, soft air on dissolves, low hit under the hook
SFX = [(0.35, "hit"), (2.87, "air"), (5.47, "whoosh"), (8.47, "whoosh"),
       (11.27, "whoosh"), (13.87, "whoosh"), (16.13, "air"), (18.6, "whoosh"),
       (19.2, "shimmer")]


def sfx_filter(kind):
    if kind == "whoosh":  # filtered pink-noise swell peaking on the cut
        return ("anoisesrc=c=pink:d=0.7:a=0.6,highpass=f=300,lowpass=f=4500,"
                "afade=t=in:d=0.45:curve=exp,afade=t=out:st=0.45:d=0.25,volume=0.35")
    if kind == "air":
        return ("anoisesrc=c=pink:d=1.0:a=0.5,highpass=f=600,lowpass=f=3000,"
                "afade=t=in:d=0.5,afade=t=out:st=0.5:d=0.5,volume=0.18")
    if kind == "hit":  # soft sub thump
        return ("sine=f=55:d=1.4,afade=t=out:d=1.4:curve=exp,volume=0.6")
    if kind == "shimmer":
        return ("sine=f=1760:d=1.6,tremolo=f=9:d=0.4,afade=t=in:d=0.05,"
                "afade=t=out:st=0.1:d=1.5:curve=exp,volume=0.05")
    raise ValueError(kind)


LEAD = {"whoosh": 0.45, "air": 0.5, "hit": 0.0, "shimmer": 0.0}


def write_sfx(out, dur):
    args, chains = ["ffmpeg", "-loglevel", "error", "-y"], []
    for i, (t, kind) in enumerate(SFX):
        args += ["-f", "lavfi", "-i", sfx_filter(kind)]
        d = max(0, int((t - LEAD[kind]) * 1000))
        chains.append(f"[{i}]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay={d}|{d}[s{i}]")
    mix = "".join(f"[s{i}]" for i in range(len(SFX)))
    fc = ";".join(chains) + f";{mix}amix=inputs={len(SFX)}:normalize=0,apad,atrim=0:{dur}," \
        "alimiter=limit=0.7[a]"
    subprocess.run(args + ["-filter_complex", fc, "-map", "[a]", "-ar", "48000", out], check=True)


def mux(base, out):
    dur = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base]))
    with tempfile.TemporaryDirectory() as td:
        ass, wav = os.path.join(td, "t.ass"), os.path.join(td, "s.wav")
        open(ass, "w", encoding="utf-8").write(ass_lines())
        write_sfx(wav, dur)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", base, "-i", wav,
                        "-vf", f"ass={ass}", "-map", "0:v", "-map", "1:a",
                        "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-maxrate", "11M",
                        "-bufsize", "22M", "-pix_fmt", "yuv420p", "-profile:v", "high",
                        "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", out],
                       check=True)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "ass":
        open(sys.argv[2], "w", encoding="utf-8").write(ass_lines())
    elif cmd == "sfx":
        write_sfx(sys.argv[2], float(sys.argv[3]))
    elif cmd == "mux":
        mux(sys.argv[2], sys.argv[3])
