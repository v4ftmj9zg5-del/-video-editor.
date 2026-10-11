"""Auto mode: look at the raw video and pick the style that suits it.

Signals (all measured, printed with the decision):
  speech rate   words per second of speech  - fast talk suits Dynamic
  pause share   share of the video that is silence - long calm pauses suit Elegant
  motion        mean frame-to-frame change - a moving, energetic camera suits Dynamic
  scene cuts    hard cuts per minute already in the footage
  energy        loudness variation of the voice (punchy vs. even delivery)
"""
import subprocess

import numpy as np

from .transcribe import SR


def video_motion(path, fps=5, w=96, h=170):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-vf",
                                   f"fps={fps},scale={w}:{h},format=gray", "-f", "rawvideo", "-"])
    fr = np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)
    if len(fr) < 2:
        return 0.0, 0.0
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    cuts = int((d > 28).sum())
    minutes = len(fr) / fps / 60
    return float(np.median(d)), cuts / max(minutes, 1e-6)


def features(path, phrases, audio, total):
    speech = sum(p["e"] - p["s"] for p in phrases)
    words = sum(len(p["text"].split()) for p in phrases)
    motion, cuts = video_motion(path)
    # voice energy variation: std of 50 ms RMS (in dB) over speech
    hop = int(0.05 * SR)
    rms = np.sqrt(np.add.reduceat(audio ** 2, np.arange(0, len(audio), hop)) / hop + 1e-12)
    db = 20 * np.log10(rms + 1e-9)
    db = db[db > db.max() - 35]
    return dict(speech_rate=words / max(speech, 1e-6), pause_share=1 - speech / max(total, 1e-6),
                motion=motion, cuts_per_min=cuts, energy_db_std=float(db.std()) if len(db) else 0.0)


# Thresholds. First calibration is on the synthetic test clips only (calm 1.8 w/s,
# motion 0.2; lively 2.4 w/s, motion 3.0); re-check them against real footage.
FAST_WPS, CALM_WPS = 2.3, 1.9          # Hebrew words are long: ~2 w/s is relaxed talk
LIVELY_MOTION, STEADY_MOTION = 2.5, 1.0
LONG_PAUSES, FEW_PAUSES = 0.35, 0.15
MANY_CUTS = 8
PUNCHY_DB = 9


def choose(f):
    score, why = 0, []
    if f["speech_rate"] >= FAST_WPS:
        score += 1; why.append(f"fast speech ({f['speech_rate']:.1f} words/s)")
    elif f["speech_rate"] <= CALM_WPS:
        score -= 1; why.append(f"calm speech ({f['speech_rate']:.1f} words/s)")
    if f["pause_share"] >= LONG_PAUSES:
        score -= 1; why.append(f"long pauses ({f['pause_share']:.0%} silence)")
    elif f["pause_share"] <= FEW_PAUSES:
        score += 1; why.append(f"few pauses ({f['pause_share']:.0%} silence)")
    if f["motion"] >= LIVELY_MOTION:
        score += 1; why.append(f"lively camera (motion {f['motion']:.1f})")
    elif f["motion"] <= STEADY_MOTION:
        score -= 1; why.append(f"steady camera (motion {f['motion']:.1f})")
    if f["cuts_per_min"] >= MANY_CUTS:
        score += 1; why.append(f"{f['cuts_per_min']:.0f} cuts/min in the footage")
    if f["energy_db_std"] >= PUNCHY_DB:
        score += 1; why.append("punchy delivery")
    # ties go to Elegant: it is the brand's home look
    return ("dynamic" if score > 0 else "elegant"), score, why
