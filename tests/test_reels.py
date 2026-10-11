"""End-to-end checks of both styles and Auto on the fixture videos.

Usage: test_reels.py FIXTURE_DIR OUT_DIR      (run make_fixtures.py first)

Every feature is checked by measuring the output, not by trusting the logs:
  export      ffprobe: 1080x1920, H.264 High, yuv420p, 30 fps, AAC 48 kHz, faststart, < 30 MB
  silences    no pause in the finished voice track longer than the style allows
  retakes     the false start is gone and the full sentence is kept
  subtitles   caption text vs. the known script (word accuracy), Hebrew in the ASS file
  audio       voice at -14 LUFS, true peak <= -1 dBTP, 50 Hz hum and hiss reduced,
              voice not time-stretched (kept pieces add up to the output length)
  B-roll      the right files placed on the right words; unrelated file not used;
              the frame on screen at that moment really is the B-roll
  music       Elegant has a ducked bed under the voice; Dynamic has none
  auto        calm clip -> Elegant, lively clip -> Dynamic
"""
import json
import os
import re
import subprocess
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
import make_reel  # noqa: E402
from reels import audio as A  # noqa: E402
from reels import transcribe as T  # noqa: E402
from reels.cuts import norm  # noqa: E402

RESULTS = []


def check(name, ok, detail):
    RESULTS.append((name, bool(ok), detail))
    print(("PASS " if ok else "FAIL ") + name + " - " + detail, flush=True)


def probe(path):
    out = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                                              "-of", "json", path]))
    v = next(s for s in out["streams"] if s["codec_type"] == "video")
    a = next(s for s in out["streams"] if s["codec_type"] == "audio")
    return v, a, out["format"]


def moov_first(path):
    with open(path, "rb") as f:
        data = f.read(1 << 20)
    m, d = data.find(b"moov"), data.find(b"mdat")
    return m != -1 and (d == -1 or m < d)


def word_accuracy(ref, hyp):
    r, h = norm(ref), norm(hyp)
    d = np.arange(len(h) + 1)
    for i, rw in enumerate(r, 1):
        prev, d[0] = d.copy(), i
        for j, hw in enumerate(h, 1):
            d[j] = min(prev[j] + 1, d[j - 1] + 1, prev[j - 1] + (rw != hw))
    return 1 - d[len(h)] / max(len(r), 1)


def band_db(wav, lo, hi, t0=None, t1=None):
    sr = 48000
    pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", wav, "-ac", "1", "-ar", str(sr),
                                   "-f", "f32le", "-"])
    y = np.frombuffer(pcm, np.float32)
    if t0 is not None:
        y = y[int(t0 * sr):int(t1 * sr)]
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
    f = np.fft.rfftfreq(len(y), 1 / sr)
    return 10 * np.log10(spec[(f >= lo) & (f <= hi)].sum() / len(y) + 1e-20)


def frame_at(path, t):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3)


def colour_match(frame, img_path):
    """Mean-colour distance between a frame's centre and the B-roll image."""
    img = cv2.imread(img_path)
    a = frame[700:1200, 300:780].reshape(-1, 3).mean(0)
    b = img.reshape(-1, 3).mean(0)
    return float(np.abs(a - b).mean())


def run_case(fx, out_dir, clip, style, title):
    work = os.path.join(out_dir, f"work_{clip}_{style}")
    out = os.path.join(out_dir, f"{clip}_{style}.mp4")
    res = make_reel.main([os.path.join(fx, clip + ".mp4"), out, "--style", style,
                          "--broll", os.path.join(fx, "broll"), "--title", title, "--keep-work", work])
    return out, work, res["style"]


def verify(fx, meta, clip, style_req, out, work, style):
    tag = f"[{clip}/{style}]"
    edit = json.load(open(os.path.join(work, "edit.json")))
    v, a, fmt = probe(out)
    size = os.path.getsize(out) / 1e6
    ok = (v["width"], v["height"]) == (1080, 1920) and v["codec_name"] == "h264" and \
        v["profile"] == "High" and v["pix_fmt"] == "yuv420p" and v["r_frame_rate"] == "30/1" and \
        a["codec_name"] == "aac" and a["sample_rate"] == "48000" and moov_first(out) and size < 30
    check(f"{tag} export", ok, f"{v['width']}x{v['height']} {v['codec_name']} {v['profile']} {v['pix_fmt']} "
          f"{v['r_frame_rate']} fps, {a['codec_name']} {a['sample_rate']} Hz, faststart={moov_first(out)}, "
          f"{size:.1f} MB, {float(fmt['duration']):.1f}s")

    # silences: pauses left in the finished voice, found with the same VAD (not a dB gate,
    # since levelling lifts the room tone)
    from reels.presets import PRESETS
    p = PRESETS[style]
    allowed = p["pad_before"] + p["pad_after"] + p["merge_gap"] + 0.15
    segs = T.speech_segments(T.load_audio(os.path.join(work, "voice.wav")))
    gaps = [b[0] - a[1] for a, b in zip(segs, segs[1:])]
    lp = max(gaps, default=0.0)
    src_gaps = [s2["s"] - s1["e"] for s1, s2 in zip(meta["script"], meta["script"][1:])]
    out_dur = float(fmt["duration"])
    check(f"{tag} silence removal", lp <= allowed,
          f"pauses in source up to {max(src_gaps):.2f}s -> longest left {lp:.2f}s (limit {allowed:.2f}s); "
          f"{meta['duration']:.1f}s -> {out_dur:.1f}s")

    # retakes: the false start's source time must not be in the edit; the full sentence must be
    retake = next(s for s in meta["script"] if s["retake"])
    full = next(s for s in meta["script"] if not s["retake"] and s["s"] > retake["s"])
    tl = edit["timeline"]
    covered = lambda t: any(c["src_s"] <= t <= c["src_e"] for c in tl)  # noqa: E731
    gone = not covered((retake["s"] + retake["e"]) / 2)
    kept_full = covered((full["s"] + full["e"]) / 2)
    check(f"{tag} retake removal", gone and kept_full,
          f"false start {retake['text']!r} removed={gone}; full sentence kept={kept_full}")

    # subtitles: caption text in the ASS file vs. the known script (minus the retake)
    ref = " ".join(s["text"] for s in meta["script"] if not s["retake"])
    ass = open(os.path.join(work, "captions.ass"), encoding="utf-8").read()
    caps = []
    for line in ass.splitlines():
        if line.startswith("Dialogue: 2"):
            txt = re.sub(r"\{[^}]*\}", "", line.split(",", 9)[9])
            if not caps or caps[-1] != txt:
                caps.append(txt)
    acc = word_accuracy(ref, " ".join(caps))
    heb = sum(1 for c in caps if re.search(r"[\u05d0-\u05ea]", c))
    check(f"{tag} Hebrew subtitles", acc >= 0.8 and heb > 0,
          f"caption word accuracy {acc:.0%} vs script; {heb} Hebrew caption chunks")

    # audio
    m = A.measure(os.path.join(work, "voice.wav"))
    lufs, tp = float(m["input_i"]), float(m["input_tp"])
    check(f"{tag} voice loudness", abs(lufs - p["loudness"]) <= 1.0 and tp <= -1.0,
          f"{lufs:.1f} LUFS (target {p['loudness']}), true peak {tp:.1f} dBTP")
    raw = os.path.join(work, "voice_cut.wav")
    voice = os.path.join(work, "voice.wav")
    tl = edit["timeline"]
    if clip == "calm":  # the fixture with hum, hiss and a quiet recording
        hum_before = band_db(raw, 45, 55) - band_db(raw, 300, 3000)
        hum_after = band_db(voice, 45, 55) - band_db(voice, 300, 3000)
        check(f"{tag} hum removed", hum_after <= hum_before - 15,
              f"50 Hz vs speech: {hum_before:.1f} dB -> {hum_after:.1f} dB")
        gap_t = tl[0]["out_e"] - 0.05
        nb = band_db(raw, 2000, 8000, gap_t - 0.06, gap_t) - band_db(raw, 300, 3000)
        na = band_db(voice, 2000, 8000, gap_t - 0.06, gap_t) - band_db(voice, 300, 3000)
        check(f"{tag} hiss reduced", na <= nb - 3,
              f"hiss in pauses vs speech: {nb:.1f} dB -> {na:.1f} dB")
    pieces = sum(c["src_e"] - c["src_s"] for c in tl)
    vd = float(probe_audio_dur(os.path.join(work, "voice.wav")))
    check(f"{tag} natural voice (no time-stretch)", abs(vd - pieces) < 0.05,
          f"kept pieces {pieces:.2f}s = voice track {vd:.2f}s; chain: {A.VOICE_CHAIN}")

    # B-roll: only files whose name matches a spoken word; the frame on screen is the B-roll
    from reels.broll import stems
    placed = edit["broll"]
    bad_word, notes = [], []
    for b0, b1, name, word in placed:
        tags = {x for tg in re.split(r"[-_ ,.]+", os.path.splitext(name)[0]) for x in stems(tg.lower())}
        if not (stems(norm(word)[0].lower()) & tags):
            bad_word.append(name)
        fr = frame_at(out, (b0 + b1) / 2)
        ref_img = os.path.join(fx, "broll", name)
        if name.endswith(".mp4"):
            ref_img = os.path.join(work, "_ref.png")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(b1 - b0) / 2:.2f}", "-i",
                            os.path.join(fx, "broll", name), "-frames:v", "1", ref_img], check=True)
        notes.append((name, word, round(colour_match(fr, ref_img))))
    on_screen = all(d < 30 for _, _, d in notes)
    unrelated = any(x[2].startswith("מטבח") for x in placed)
    check(f"{tag} B-roll", placed and on_screen and not bad_word and not unrelated,
          f"placed (file, word, colour diff on screen): {notes}; never-said file used: {unrelated}")

    # music: mix minus voice leaves music + sfx; measure it under speech vs. in pauses
    sr = 48000
    mixs = np.frombuffer(subprocess.check_output(["ffmpeg", "-v", "error", "-i", os.path.join(work, "mix.wav"),
                                                  "-af", "pan=mono|c0=c0", "-ar", str(sr), "-f", "f32le", "-"]), np.float32)
    vo = np.frombuffer(subprocess.check_output(["ffmpeg", "-v", "error", "-i", voice, "-ar", str(sr),
                                                "-f", "f32le", "-"]), np.float32)
    # the limiter's look-ahead delays the mix by a few ms: align before subtracting
    seg = slice(sr, min(len(vo), 6 * sr))
    lags = range(0, int(0.02 * sr))
    lag = max(lags, key=lambda L: float(np.dot(mixs[seg.start + L:seg.stop + L], vo[seg])))
    mixs = mixs[lag:]
    n = min(len(mixs), len(vo))
    res = mixs[:n] - vo[:n]
    mask = np.ones(n, bool)  # exclude sound-effect windows
    for t0, _k in edit["sfx"]:
        mask[max(0, int((t0 - 0.6) * sr)):int((t0 + 1.5) * sr)] = False
    speech = np.zeros(n, bool)
    for a0, a1 in segs:
        speech[int(a0 * sr):int(a1 * sr)] = True
    db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -120  # noqa: E731
    v_db, under, pauses = db(vo[:n][speech]), db(res[mask & speech]), db(res[mask & ~speech])
    if style == "elegant":
        check(f"{tag} music", edit["music"] and 12 <= v_db - under <= 30 and pauses - under >= 3,
              f"bed {v_db - under:.1f} dB under the voice while she talks, {pauses - under:.1f} dB louder "
              f"in pauses (ducking)")
    else:
        check(f"{tag} music", not edit["music"] and db(res[mask]) < -50,
              f"no music bed (residual outside sound effects {db(res[mask]):.0f} dBFS); "
              f"{len(edit['sfx'])} sound effects")
    return edit


def probe_audio_dur(path):
    return subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                    "-of", "csv=p=0", path]).decode()


def main(fx, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    meta = json.load(open(os.path.join(fx, "fixtures.json")))
    cases = [("calm", "elegant", "סלון קטן, מרגיש גדול"), ("lively", "dynamic", "3 טעויות בסלון"),
             ("calm", "dynamic", "סלון קטן, מרגיש גדול"), ("lively", "elegant", "3 טעויות בסלון")]
    for clip, style, title in cases:
        out, work, got = run_case(fx, out_dir, clip, style, title)
        verify(fx, meta[clip], clip, style, out, work, got)
    for clip, expect in (("calm", "elegant"), ("lively", "dynamic")):
        out, work, got = run_case(fx, out_dir, clip, "auto", "")
        why = json.load(open(os.path.join(work, "auto.json")))
        check(f"[{clip}/auto] auto style", got == expect,
              f"chose {got} (score {why['score']:+d}): {', '.join(why['why'])}")
    json.dump(RESULTS, open(os.path.join(out_dir, "results.json"), "w"), ensure_ascii=False, indent=1)
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
