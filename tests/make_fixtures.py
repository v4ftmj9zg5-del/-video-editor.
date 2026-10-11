"""Build the test footage: two Hebrew "talking" videos with known content.

calm.mp4   1920x1080 25 fps, slow delivery, long pauses, a retake, steady camera,
           hum + hiss + low level (to test audio clean-up and levelling)
lively.mp4 1080x1920 30 fps, fast delivery, short pauses, a retake, handheld
           camera with hard cuts
broll/     photos + one clip named by what they show, plus one that is never said

Speech is Google TTS (cached in tests/fixtures/tts so the suite runs offline);
each video burns its source timecode in the corner so cuts can be checked by eye.

Usage: make_fixtures.py OUT_DIR
"""
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TTS = os.path.join(HERE, "fixtures", "tts")

# (text, pause_after_seconds); "RETAKE:" lines are cut short on purpose
CALM = [
    ("שלום לכולם, היום אני רוצה להראות לכם איך לעצב סלון קטן שמרגיש גדול.", 1.6),
    ("RETAKE:הדבר הראשון שאני", 0.9),
    ("הדבר הראשון שאני עושה הוא לבחור ספה בהירה ונמוכה.", 2.2),
    ("אחר כך אני מוסיפה מנורה רכה בפינה, שנותנת אור חם בערב.", 1.4),
    ("וצמחים ירוקים מכניסים חיים לכל חדר.", 1.8),
    ("תשמרו את הסרטון, ותכתבו לי בתגובות מה הכי אהבתם.", 1.0),
]
LIVELY = [
    ("שלוש טעויות שכולם עושים בעיצוב הסלון!", 0.35),
    ("טעות ראשונה: ספה ענקית בחדר קטן.", 0.4),
    ("RETAKE:טעות שנייה", 0.5),
    ("טעות שנייה: מנורה אחת בתקרה וזהו.", 1.5),
    ("טעות שלישית: אין צמחים בכלל!", 0.35),
    ("תעקבו לעוד טיפים!", 0.6),
]


def tts(text):
    os.makedirs(TTS, exist_ok=True)
    import hashlib
    path = os.path.join(TTS, hashlib.md5(text.encode()).hexdigest()[:12] + ".mp3")
    if not os.path.exists(path):
        q = urllib.parse.urlencode(dict(ie="UTF-8", client="gtx", tl="iw", q=text))
        with urllib.request.urlopen("https://translate.googleapis.com/translate_tts?" + q) as r:
            open(path, "wb").write(r.read())
    return path


def build_audio(lines, tempo, out, noisy):
    """Speech with exact pauses; returns the script with source timings."""
    parts, script, t = [], [], 0.6
    sr = 48000
    lead = np.zeros(int(0.6 * sr), np.float32)
    parts.append(lead)
    for text, pause in lines:
        retake = text.startswith("RETAKE:")
        text = text.replace("RETAKE:", "")
        pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", tts(text), "-af",
                                       f"atempo={tempo},silenceremove=start_periods=1:start_threshold=-50dB,"
                                       "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse",
                                       "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"])
        a = np.frombuffer(pcm, np.float32)
        if retake:  # speaker stops mid-sentence
            a = a[:int(len(a) * 0.95)] * np.linspace(1, 0.2, int(len(a) * 0.95))
        script.append(dict(text=text, retake=retake, s=t, e=t + len(a) / sr))
        parts += [a, np.zeros(int(pause * sr), np.float32)]
        t += len(a) / sr + pause
    y = np.concatenate(parts + [np.zeros(int(0.4 * sr), np.float32)])
    if noisy:
        n = np.arange(len(y)) / sr
        rng = np.random.default_rng(0)
        hiss = np.cumsum(rng.normal(0, 1, len(y)))  # brown-ish room noise
        hiss = (hiss - np.convolve(hiss, np.ones(400) / 400, "same")) * 0.0012
        y = y * 0.35 + 0.004 * np.sin(2 * np.pi * 50 * n) + hiss  # quiet voice, hum, hiss
    y.astype(np.float32).tofile(out + ".f32")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "1",
                    "-i", out + ".f32", out], check=True)
    os.remove(out + ".f32")
    return script, len(y) / sr


def room(w, h, variant):
    """A simple interior 'shot' with a person-like figure in the middle."""
    img = np.zeros((h, w, 3), np.uint8)
    wall = [(200, 214, 226), (170, 190, 205)][variant % 2]
    img[:] = wall
    floor_y = int(h * 0.72)
    img[floor_y:] = (120, 150, 175)
    cv2.rectangle(img, (int(w * 0.08), int(h * 0.15)), (int(w * 0.3), int(h * 0.55)), (235, 230, 215), -1)
    cv2.rectangle(img, (int(w * 0.62), int(h * 0.55)), (int(w * 0.95), int(h * 0.75)), (90, 110, 140), -1)
    cx = int(w * (0.5 if variant == 0 else 0.45))
    cv2.ellipse(img, (cx, int(h * 0.88)), (int(w * 0.17), int(h * 0.3)), 0, 180, 360, (70, 80, 95), -1)
    cv2.circle(img, (cx, int(h * 0.45)), int(min(w, h) * 0.11), (150, 175, 215), -1)
    return cv2.GaussianBlur(img, (0, 0), 1.2)


def build_video(out, audio, dur, w, h, fps, lively):
    shots = [room(int(w * 1.2), int(h * 1.2), v) for v in (0, 1)]
    rng = np.random.default_rng(1)
    ph = rng.uniform(0, 6.28, 6)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                          "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-i", audio,
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-c:a", "aac", "-b:a", "192k", "-shortest", out], stdin=subprocess.PIPE)
    for k in range(int(dur * fps)):
        t = k / fps
        sh = shots[int(t / 1.6) % 2] if lively else shots[0]
        amp = 0.035 if lively else 0.002
        dx = (np.sin(2.1 * t + ph[0]) + 0.5 * np.sin(5.3 * t + ph[1])) * amp * w
        dy = (np.sin(1.7 * t + ph[2]) + 0.5 * np.sin(4.1 * t + ph[3])) * amp * h
        x0, y0 = int(w * 0.1 + dx), int(h * 0.1 + dy)
        f = sh[y0:y0 + h, x0:x0 + w].copy()
        cv2.putText(f, f"SRC {t:06.2f}", (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (30, 30, 30), 3)
        p.stdin.write(f.tobytes())
    p.stdin.close()
    p.wait()


def build_broll(folder):
    os.makedirs(folder, exist_ok=True)
    specs = {"ספה-sofa.jpg": ((60, 90, 140), "SOFA"), "מנורה.png": ((40, 60, 70), "LAMP"),
             "צמחים-plant.jpg": ((60, 120, 60), "PLANTS"), "מטבח-kitchen.jpg": ((30, 30, 120), "KITCHEN")}
    for name, (col, label) in specs.items():
        img = np.zeros((1600, 1200, 3), np.uint8)
        img[:] = col
        for i in range(12):
            cv2.circle(img, (100 * i, 300 + 90 * i), 160, tuple(int(c * 1.6) % 255 for c in col), 6)
        cv2.putText(img, label, (200, 800), cv2.FONT_HERSHEY_DUPLEX, 5, (255, 255, 255), 10)
        cv2.imwrite(os.path.join(folder, name), img)
    # a short moving clip for "סלון"
    clip = os.path.join(folder, "סלון-living.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "testsrc2=s=1280x720:r=30:d=4", "-vf", "hue=s=0.4,drawtext=text=LIVING:fontsize=120:"
                    "fontcolor=white:x=(w-tw)/2+80*sin(t):y=(h-th)/2", "-pix_fmt", "yuv420p", clip], check=True)


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    meta = {}
    for name, lines, tempo, (w, h, fps), lively in (
            ("calm", CALM, 0.88, (1920, 1080, 25), False),
            ("lively", LIVELY, 1.35, (1080, 1920, 30), True)):
        wav = os.path.join(out_dir, name + ".wav")
        script, dur = build_audio(lines, tempo, wav, noisy=not lively)
        build_video(os.path.join(out_dir, name + ".mp4"), wav, dur, w, h, fps, lively)
        meta[name] = dict(script=script, duration=dur)
        print(name, f"{dur:.1f}s")
    build_broll(os.path.join(out_dir, "broll"))
    json.dump(meta, open(os.path.join(out_dir, "fixtures.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
