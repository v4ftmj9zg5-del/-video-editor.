"""Voice: cut to the edit, clean it up while keeping it natural, level it for
Instagram. Then lay music (ducked under the voice) and sound effects on top."""
import json
import os
import re
import subprocess

import numpy as np

SR = 48000
# Gentle chain: rumble/hum cut (steep 80 Hz high-pass + narrow 50/60 Hz notches, all
# below a speaking voice's fundamental), light broadband denoise, soft compression.
# No EQ tricks, pitch or "radio" processing, so the voice stays the user's own.
VOICE_CHAIN = ("highpass=f=80,highpass=f=80,bandreject=f=50:w=6,bandreject=f=60:w=6,"
               "afftdn=nr=10:nf=-50:tn=1,"
               "acompressor=threshold=-22dB:ratio=2:attack=15:release=220:makeup=1.5")


def run(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, check=True)


def cut_voice(src, timeline, out):
    """Concatenate the kept pieces with 12 ms fades so cuts never click."""
    parts, labels = [], []
    for i, c in enumerate(timeline):
        d = c["src_e"] - c["src_s"]
        parts.append(f"[0:a]atrim={c['src_s']:.4f}:{c['src_e']:.4f},asetpts=PTS-STARTPTS,"
                     f"aresample={SR},afade=t=in:d=0.012,afade=t=out:st={max(0, d - 0.012):.4f}:d=0.012[a{i}]")
        labels.append(f"[a{i}]")
    fc = ";".join(parts) + f";{''.join(labels)}concat=n={len(timeline)}:v=0:a=1,aformat=channel_layouts=mono[v]"
    run(["-i", src, "-filter_complex", fc, "-map", "[v]", "-ar", str(SR), out])


def measure(path, extra=""):
    """EBU R128 stats of a file (integrated LUFS, true peak, LRA, threshold)."""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                        (extra + "," if extra else "") + "loudnorm=print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    return json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))


def enhance_voice(src, out, target=-14):
    """Clean + two-pass loudnorm (linear) so dynamics are not squashed."""
    m = measure(src, VOICE_CHAIN)
    ln = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
          f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
          f":offset={m['target_offset']}:linear=true")
    run(["-i", src, "-af", f"{VOICE_CHAIN},{ln},aresample={SR}", "-ac", "1", "-ar", str(SR), out])


def generate_bed(out, dur, seed=1):
    """Soft, slow piano-pad bed (synthesised, so no licensing questions):
    Fmaj9 - Am7 - Dm9 - Bbmaj7, each chord 4 s, warm low-passed, gentle swell."""
    rng = np.random.default_rng(seed)
    chords = [[53, 57, 60, 64, 67], [57, 60, 64, 67, 72], [50, 57, 60, 64, 65], [46, 53, 57, 62, 65]]
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    seg = 4.0
    for k in range(int(np.ceil(dur / seg)) + 1):
        notes = chords[k % len(chords)]
        t0 = k * seg - 0.6  # overlap so chords breathe into each other
        a, b = max(0, int(t0 * SR)), min(n, int((t0 + seg + 1.6) * SR))
        if a >= b:
            continue
        tt = t[a:b] - t0
        env = np.minimum(1, tt / 1.2) * np.exp(-tt / 6.0) * np.clip((seg + 1.6 - tt) / 1.0, 0, 1)
        for i, m in enumerate(notes):
            f = 440 * 2 ** ((m - 69) / 12)
            det = 1 + rng.uniform(-0.0015, 0.0015)
            tone = (np.sin(2 * np.pi * f * det * tt) + 0.35 * np.sin(4 * np.pi * f * tt + 0.3)
                    + 0.12 * np.sin(6 * np.pi * f * tt + 1.1))
            y[a:b] += tone * env * (0.9 if i == 0 else 0.55)
    # simple low-pass + stereo-ish fades
    y = np.convolve(y, np.ones(24) / 24, mode="same")
    y *= np.minimum(1, t / 1.5) * np.minimum(1, (dur - t) / 1.8).clip(0, 1)
    y = y / (np.abs(y).max() + 1e-9) * 0.5
    pcm = (y * 32767).astype(np.int16)
    raw = out + ".raw"
    pcm.tofile(raw)
    run(["-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", raw,
         "-af", "aecho=0.8:0.7:60|130:0.25|0.18,lowpass=f=5000", "-ac", "2", out])
    os.remove(raw)


def sfx_source(kind):
    if kind == "whoosh":
        return ("anoisesrc=c=pink:d=0.6:a=0.6:r=48000,highpass=f=300,lowpass=f=5000,"
                "afade=t=in:d=0.4:curve=exp,afade=t=out:st=0.4:d=0.2,volume=0.30")
    if kind == "air":
        return ("anoisesrc=c=pink:d=1.0:a=0.5:r=48000,highpass=f=700,lowpass=f=3000,"
                "afade=t=in:d=0.5,afade=t=out:st=0.5:d=0.5,volume=0.10")
    if kind == "tick":  # short soft click on punch-ins
        return "sine=f=1900:d=0.05:r=48000,afade=t=out:d=0.05:curve=exp,volume=0.10"
    if kind == "hit":
        return "sine=f=55:d=1.2:r=48000,afade=t=out:d=1.2:curve=exp,volume=0.5"
    raise ValueError(kind)


LEAD = {"whoosh": 0.4, "air": 0.5, "tick": 0.0, "hit": 0.0}


def mix(voice, out, dur, preset, sfx=(), music=None):
    """voice (mono, levelled) + ducked music + sfx -> stereo 48 kHz wav."""
    args = ["-i", voice]
    chains = ["[0:a]pan=stereo|c0=c0|c1=c0,asplit=2[v][vk]"]
    mixin = ["[v]"]
    idx = 1
    if music:
        args += ["-stream_loop", "-1", "-i", music]
        g = 10 ** ((preset["music_lufs"] - float(measure(music)["input_i"])) / 20)
        chains.append(f"[{idx}:a]aresample={SR},aformat=channel_layouts=stereo,atrim=0:{dur:.3f},"
                      f"volume={g:.4f},afade=t=out:st={max(0, dur - 1.5):.3f}:d=1.5[m0]")
        chains.append("[m0][vk]sidechaincompress=threshold=0.06:ratio=4:attack=40:release=450[m]")
        mixin.append("[m]")
        idx += 1
    else:
        chains.append("[vk]anullsink")
    for t, kind in sfx:
        args += ["-f", "lavfi", "-i", sfx_source(kind)]
        d = max(0, int((t - LEAD[kind]) * 1000))
        chains.append(f"[{idx}:a]pan=stereo|c0=c0|c1=c0,adelay={d}|{d}[s{idx}]")
        mixin.append(f"[s{idx}]")
        idx += 1
    fc = ";".join(chains) + f";{''.join(mixin)}amix=inputs={len(mixin)}:normalize=0:duration=first," \
        f"atrim=0:{dur:.3f},alimiter=limit=0.89:level=false[a]"
    run(args + ["-filter_complex", fc, "-map", "[a]", "-ar", str(SR), "-ac", "2", out])
