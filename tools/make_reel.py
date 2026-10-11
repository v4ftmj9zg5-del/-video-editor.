"""Raw talking video -> finished 1080x1920 Instagram Reel in one of two styles.

Usage:
  make_reel.py INPUT OUT.mp4 [--style dynamic|elegant|auto] [--broll DIR]
               [--music FILE | --no-music] [--title "כותרת"] [--keep-work DIR]

Without --style it asks:  1 = Dynamic, 2 = Elegant, 3 = Auto.

Steps: transcribe (Whisper, Hebrew) -> drop silences, fillers and retakes ->
clean + level the voice -> captions / title (ASS) -> B-roll matched to the words ->
render camera moves, cuts, grade -> mux with music + sfx -> MP4 (H.264 High, AAC 48 kHz).
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reels import analyze, audio, broll, captions, cuts, render, transcribe  # noqa: E402
from reels.presets import PRESETS  # noqa: E402

CHOICES = {"1": "dynamic", "2": "elegant", "3": "auto"}


def ask_style():
    print("איזה סגנון עריכה?\n  1. דינמי (Dynamic Reels)\n  2. אלגנטי (Elegant Editorial)\n"
          "  3. אוטומטי - לנתח את הסרטון ולבחור")
    while True:
        a = input("> ").strip().lower()
        if a in CHOICES:
            return CHOICES[a]
        if a in CHOICES.values():
            return a


def sfx_cues(preset, timeline, placements, title):
    cues = []
    if preset["sfx"] == "dynamic":
        if title:
            cues.append((0.15, "hit"))
        cues += [(c["out_s"], "tick") for c in timeline[1:]]
        cues += [(b0, "whoosh") for b0, _, _, _ in placements]
    else:
        cues += [(b0 + 0.2, "air") for b0, _, _, _ in placements]
    return cues


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--style", choices=["dynamic", "elegant", "auto"])
    ap.add_argument("--broll", help="folder of photos/renders/clips named by what they show")
    ap.add_argument("--music", help="music file you have the rights to")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--title", help="hook title shown in the first 2.5 s")
    ap.add_argument("--keep-work", help="keep intermediate files (transcript, ass, wav) here")
    a = ap.parse_args(argv)

    style = a.style or ask_style()
    t0 = time.time()
    work = a.keep_work or tempfile.mkdtemp(prefix="reel_")
    os.makedirs(work, exist_ok=True)
    log = lambda m: print(m, flush=True)  # noqa: E731

    log("1/6 transcribing (Whisper, Hebrew)")
    phrases, total = transcribe.transcribe(a.input, log)

    if style == "auto":
        f = analyze.features(a.input, phrases, transcribe.load_audio(a.input), total)
        style, score, why = analyze.choose(f)
        log(f"  auto -> {style} (score {score:+d}): {', '.join(why) or 'no strong signal'}")
        json.dump(dict(features=f, style=style, score=score, why=why),
                  open(os.path.join(work, "auto.json"), "w"), ensure_ascii=False, indent=1)
    p = PRESETS[style]
    log(f"  style: {p['label']}")

    log("2/6 removing silences, fillers and retakes")
    kept, timeline = cuts.plan(phrases, total, p, log)
    out_dur = timeline[-1]["out_e"]
    log(f"  {total:.1f}s -> {out_dur:.1f}s in {len(timeline)} clips")

    log("3/6 voice clean-up and levelling")
    raw_v, voice = os.path.join(work, "voice_cut.wav"), os.path.join(work, "voice.wav")
    audio.cut_voice(a.input, timeline, raw_v)
    audio.enhance_voice(raw_v, voice, p["loudness"])

    log("4/6 captions, title and B-roll")
    ass = os.path.join(work, "captions.ass")
    captions.write(ass, kept, timeline, p, a.title, out_dur)
    placements = broll.place(kept, timeline, broll.library(a.broll), p, out_dur, log)

    music = None if a.no_music else a.music
    if not music and not a.no_music and p["music_auto"]:
        music = os.path.join(work, "bed.wav")
        audio.generate_bed(music, out_dur + 1)
    mixwav = os.path.join(work, "mix.wav")
    cues = sfx_cues(p, timeline, placements, a.title)
    audio.mix(voice, mixwav, out_dur, p, cues, music)

    log("5/6 rendering")
    render.render(a.input, timeline, placements, p, ass, mixwav, a.output, log)
    log("6/6 checking size")
    mb = render.fit_size(a.output, log=log)

    json.dump(dict(style=style, phrases=phrases, kept=[k["text"] for k in kept], timeline=timeline,
                   broll=[(b0, b1, os.path.basename(it["path"]), w) for b0, b1, it, w in placements],
                   sfx=cues, music=bool(music)),
              open(os.path.join(work, "edit.json"), "w"), ensure_ascii=False, indent=1)
    log(f"done: {a.output} ({out_dur:.1f}s, {mb:.1f} MB, {time.time() - t0:.0f}s)")
    if not a.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return dict(style=style, work=work)


if __name__ == "__main__":
    main()
