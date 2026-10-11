"""Bridge to the Remotion motion-graphics layer (remotion/ in this repo).

Python renders the cut, graded base video; Remotion draws everything on top
(kinetic captions, content-aware scenes, layouts, transitions); FFmpeg then muxes
the mixed audio and encodes the Instagram spec.
"""
import glob
import json
import os
import shutil
import subprocess

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "remotion")
ROOT = os.path.abspath(ROOT)
FPS = 30


def available():
    return os.path.isdir(os.path.join(ROOT, "node_modules", "remotion")) and shutil.which("npx") is not None


def browser():
    """Chrome for Remotion: $REMOTION_BROWSER, a Playwright headless shell if present,
    else None (Remotion downloads its own on first use)."""
    if os.environ.get("REMOTION_BROWSER"):
        return os.environ["REMOTION_BROWSER"]
    for pat in ("/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell",
                os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell")):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    return None


def captions_props(chunks):
    return [dict(s=round(s, 3), e=round(e, 3), words=[dict(w=w, s=round(a, 3), e=round(b, 3)) for w, a, b in ws])
            for s, e, ws in chunks]


def render(work, base_mp4, props, out, log=print, images=()):
    """Render the Reel composition to `out` (silent H.264)."""
    pub = os.path.join(work, "public")
    os.makedirs(pub, exist_ok=True)
    shutil.copytree(os.path.join(ROOT, "public", "fonts"), os.path.join(pub, "fonts"), dirs_exist_ok=True)
    shutil.copy(base_mp4, os.path.join(pub, "base.mp4"))
    for src, name in images:
        shutil.copy(src, os.path.join(pub, name))
    props = dict(props, base="base.mp4", fps=FPS)
    pfile = os.path.join(work, "props.json")
    json.dump(props, open(pfile, "w"), ensure_ascii=False)
    cmd = ["npx", "remotion", "render", "src/index.ts", "Reel", os.path.abspath(out),
           f"--props={os.path.abspath(pfile)}", f"--public-dir={os.path.abspath(pub)}",
           "--codec=h264", "--crf=15", "--muted", f"--concurrency={max(1, (os.cpu_count() or 2))}",
           "--log=error"]
    b = browser()
    if b:
        cmd.append(f"--browser-executable={b}")
    log(f"  remotion: {props['durationInFrames']} frames, {len(props['scenes'])} scenes")
    subprocess.run(cmd, cwd=ROOT, check=True)
    return out


def still(composition, props, out, frame=0, public_dir=None):
    cmd = ["npx", "remotion", "still", "src/index.ts", composition, os.path.abspath(out),
           f"--props={json.dumps(props, ensure_ascii=False)}", f"--frame={frame}", "--log=error"]
    if public_dir:
        cmd.append(f"--public-dir={os.path.abspath(public_dir)}")
    b = browser()
    if b:
        cmd.append(f"--browser-executable={b}")
    subprocess.run(cmd, cwd=ROOT, check=True)
    return out


def mux(video, audio, out):
    """Final Instagram encode: H.264 High yuv420p 30 fps + AAC 48 kHz, faststart."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "11M", "-bufsize", "22M",
                    "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", out],
                   check=True)
    return out
