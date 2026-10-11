"""Build the 20-second motion-graphics demo input.

Hebrew voice-over (Google TTS, cached in tests/fixtures/tts) over an illustrated
living room rendered by Remotion (DemoRoom), plus a before/after pair in the
B-roll folder. The script is written so the storyboard should trigger at least
seven different animations: big number, mistake badges, furniture illustration,
lighting change, colour palette, before/after slider and call to action.

Usage: make_demo.py OUT_DIR      -> OUT_DIR/demo_raw.mp4, OUT_DIR/broll/, OUT_DIR/demo.json
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from make_fixtures import tts  # noqa: E402
from reels import motion  # noqa: E402

SCRIPT = [
    ("חמש טעויות שהורסות כל סלון.", 0.5),
    ("טעות ראשונה: ספה ענקית שתופסת את כל החדר.", 0.45),
    ("טעות שנייה: תאורה אחת מהתקרה. תוסיפו מנורה רכה בפינה.", 1.3),  # long pause: gets cut
    ("טעות שלישית: יותר מדי צבעים. תבחרו בז', ירוק זית וטרקוטה.", 0.45),
    ("ככה זה נראה לפני, וככה אחרי.", 0.4),
    ("תשמרו את הסרטון ותעקבו לעוד טיפים!", 0.5),
]
SR = 48000


def main(out):
    os.makedirs(os.path.join(out, "broll"), exist_ok=True)
    parts, t, script = [np.zeros(int(0.4 * SR), np.float32)], 0.4, []
    for text, pause in SCRIPT:
        pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", tts(text), "-af",
                                       "atempo=1.25,silenceremove=start_periods=1:start_threshold=-50dB,"
                                       "areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse",
                                       "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"])
        a = np.frombuffer(pcm, np.float32)
        script.append(dict(text=text, s=t, e=t + len(a) / SR))
        parts += [a, np.zeros(int(pause * SR), np.float32)]
        t += len(a) / SR + pause
    y = np.concatenate(parts)
    dur = len(y) / SR
    wav = os.path.join(out, "voice.wav")
    y.tofile(wav + ".f32")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", wav + ".f32", wav],
                   check=True)
    os.remove(wav + ".f32")
    frames = int(np.ceil(dur * 30)) + 2
    room = os.path.join(out, "room.mp4")
    cmd = ["npx", "remotion", "render", "src/index.ts", "DemoRoom", os.path.abspath(room),
           f"--props={json.dumps(dict(variant='styled', durationInFrames=frames))}", "--codec=h264", "--crf=16",
           "--muted", "--log=error", f"--concurrency={os.cpu_count()}"]
    if motion.browser():
        cmd.append(f"--browser-executable={motion.browser()}")
    subprocess.run(cmd, cwd=motion.ROOT, check=True)
    for variant, name in (("bare", "לפני-before.png"), ("styled", "אחרי-after.png")):
        motion.still("DemoRoom", dict(variant=variant, durationInFrames=600), os.path.join(out, "broll", name), 300)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", room, "-i", wav, "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", os.path.join(out, "demo_raw.mp4")], check=True)
    json.dump(dict(script=script, duration=dur), open(os.path.join(out, "demo.json"), "w"), ensure_ascii=False, indent=1)
    print(f"demo input {dur:.1f}s -> {out}/demo_raw.mp4")


if __name__ == "__main__":
    main(sys.argv[1])
