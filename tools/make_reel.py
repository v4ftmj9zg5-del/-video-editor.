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

from reels import analyze, audio, broll, captions, cuts, motion, render, story, transcribe  # noqa: E402
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


def sfx_cues(preset, timeline, placements, title, scenes=()):
    cues = []
    dyn = preset["sfx"] == "dynamic"
    if dyn:
        if title:
            cues.append((0.15, "hit"))
        starts = {round(sc["s"], 1) for sc in scenes}
        cues += [(c["out_s"], "tick") for c in timeline[1:] if round(c["out_s"], 1) not in starts]
        cues += [(b0, "whoosh") for b0, _, _, _ in placements]
    else:
        cues += [(b0 + 0.2, "air") for b0, _, _, _ in placements]
    for sc in scenes:  # sound follows the motion graphics
        s, d, k = sc["s"], sc["e"] - sc["s"], sc["kind"]
        if sc["transition"] in ("flash", "whip"):
            cues.append((s, "whoosh"))
        elif sc["transition"] in ("leak", "fade"):
            cues.append((s, "air"))
        if k == "number":
            cues += [(s + 0.1, "hit" if dyn else "air"), (s + (0.7 if dyn else 1.1), "pop")]
        elif k == "mistake":
            cues.append((s + 0.35, "pop"))
        elif k == "palette":
            cues += [(s + 0.25 + i * (0.13 if dyn else 0.23), "tick") for i in range(len(sc["params"].get("colors", [])))]
        elif k == "lighting":
            on = s + min(round(d * 30 * 0.35), 30) / 30
            cues += [(on, "click"), (on + 0.05, "shimmer")]
        elif k == "cta":
            cues.append((s + 22 / 30, "click"))
        elif k == "furniture" and sc["params"].get("mark"):
            cues.append((s + (1.0 if dyn else 1.5), "pop"))
        elif k == "kinetic" and dyn:
            cues.append((s + 0.08, "hit"))
    return sorted((round(t, 3), k) for t, k in cues if t < timeline[-1]["out_e"] - 0.1)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--style", choices=["dynamic", "elegant", "auto"])
    ap.add_argument("--broll", help="folder of photos/renders/clips named by what they show "
                                    "(name a pair לפני-*.jpg / אחרי-*.jpg for before/after)")
    ap.add_argument("--music", help="music file you have the rights to")
    ap.add_argument("--no-music", action="store_true")
    ap.add_argument("--title", help="hook title shown in the first seconds")
    ap.add_argument("--engine", choices=["remotion", "ffmpeg"],
                    help="remotion = full motion graphics (default when installed); ffmpeg = captions only")
    ap.add_argument("--plan-only", action="store_true", help="write the storyboard and stop before rendering")
    ap.add_argument("--keep-work", help="keep intermediate files (transcript, storyboard, wav) here")
    a = ap.parse_args(argv)

    style = a.style or ask_style()
    engine = a.engine or ("remotion" if motion.available() else "ffmpeg")
    t0 = time.time()
    work = a.keep_work or tempfile.mkdtemp(prefix="reel_")
    os.makedirs(work, exist_ok=True)
    log = lambda m: print(m, flush=True)  # noqa: E731

    os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
    log("1/7 transcribing (Whisper, Hebrew)")
    st = os.stat(a.input)
    key = f"{os.path.abspath(a.input)}|{st.st_size}|{st.st_mtime}"
    cache = os.path.join(work, "transcript.json")
    if os.path.exists(cache) and json.load(open(cache)).get("key") == key:
        c = json.load(open(cache))
        phrases, total = c["phrases"], c["total"]
        log("  (reusing transcript from work folder)")
    else:
        phrases, total = transcribe.transcribe(a.input, log)
        json.dump(dict(key=key, phrases=phrases, total=total), open(cache, "w"), ensure_ascii=False)

    if style == "auto":
        f = analyze.features(a.input, phrases, transcribe.load_audio(a.input), total)
        style, score, why = analyze.choose(f)
        log(f"  auto -> {style} (score {score:+d}): {', '.join(why) or 'no strong signal'}")
        json.dump(dict(features=f, style=style, score=score, why=why),
                  open(os.path.join(work, "auto.json"), "w"), ensure_ascii=False, indent=1)
    p = PRESETS[style]
    log(f"  style: {p['label']}, engine: {engine}")

    log("2/7 removing silences, fillers and retakes")
    kept, timeline = cuts.plan(phrases, total, p, log)
    out_dur = timeline[-1]["out_e"]
    log(f"  {total:.1f}s -> {out_dur:.1f}s in {len(timeline)} clips")

    log("3/7 storyboard (what to show for each sentence)")
    lib = broll.library(a.broll)
    ba = {k: next((it for it in lib if it["tags"] & tags and not it["video"]), None)
          for k, tags in (("before", {"לפני", "before"}), ("after", {"אחרי", "after"}))}
    lib = [it for it in lib if it not in ba.values()]
    ba_imgs = {}
    if ba["before"] and ba["after"]:
        ba_imgs = {"before": "ba_before" + os.path.splitext(ba["before"]["path"])[1],
                   "after": "ba_after" + os.path.splitext(ba["after"]["path"])[1]}
    placements = broll.place(kept, timeline, lib, p, out_dur, log)
    scenes, punches = ([], [])
    if engine == "remotion":
        scenes, punches = story.plan(kept, timeline, p, out_dur, placements, ba_imgs)
        if a.title:
            scenes = [sc for sc in scenes if sc["s"] > 2.2]
            scenes.insert(0, dict(id=-1, kind="kinetic", s=0.0, e=min(2.4, out_dur), text=a.title, layout="full",
                                  transition="none", params=dict(words=a.title.split(), key=story.key_word(
                                      [dict(w=w) for w in a.title.split()])), phrase=0))
            for i, sc in enumerate(scenes):
                sc["id"] = i
    rows = story.storyboard(kept, timeline, scenes, placements, style)
    md = story.storyboard_md(rows, style, a.title or "")
    open(os.path.join(work, "storyboard.md"), "w", encoding="utf-8").write(md)
    open(os.path.splitext(a.output)[0] + ".storyboard.md", "w", encoding="utf-8").write(md)
    json.dump(dict(scenes=scenes, punches=punches, rows=rows), open(os.path.join(work, "storyboard.json"), "w"),
              ensure_ascii=False, indent=1)
    for r in rows:
        log(f"  {r['time']}  {r['visual']}  [{r['transition']}]")
    if a.plan_only:
        log(f"storyboard: {os.path.splitext(a.output)[0] + '.storyboard.md'}")
        return dict(style=style, work=work, scenes=scenes)

    log("4/7 voice clean-up and levelling")
    raw_v, voice = os.path.join(work, "voice_cut.wav"), os.path.join(work, "voice.wav")
    audio.cut_voice(a.input, timeline, raw_v)
    audio.enhance_voice(raw_v, voice, p["loudness"])

    music = None if a.no_music else a.music
    if not music and not a.no_music and p["music_auto"]:
        music = os.path.join(work, "bed.wav")
        audio.generate_bed(music, out_dur + 1)
    mixwav = os.path.join(work, "mix.wav")
    cues = sfx_cues(p, timeline, placements, a.title, scenes)
    audio.mix(voice, mixwav, out_dur, p, cues, music)

    if engine == "remotion":
        log("5/7 rendering base video (cuts, camera, grade, B-roll)")
        base = os.path.join(work, "base.mp4")
        render.render(a.input, timeline, placements, p, None, None, base, log, progress_bar=False)
        log("6/7 motion graphics (Remotion)")
        props = dict(style=style, durationInFrames=int(round(out_dur * motion.FPS)), title=a.title or "",
                     captions=motion.captions_props(captions.chunks(kept, timeline, p)),
                     scenes=scenes, punches=punches)
        imgs = [(ba[k]["path"], ba_imgs[k]) for k in ("before", "after")] if ba_imgs else []
        silent = os.path.join(work, "motion.mp4")
        motion.render(work, base, props, silent, log, imgs)
        motion.mux(silent, mixwav, a.output)
    else:
        log("5/7 captions")
        ass = os.path.join(work, "captions.ass")
        captions.write(ass, kept, timeline, p, a.title, out_dur)
        log("6/7 rendering")
        render.render(a.input, timeline, placements, p, ass, mixwav, a.output, log)
    log("7/7 checking size")
    mb = render.fit_size(a.output, log=log)

    json.dump(dict(style=style, engine=engine, phrases=phrases, kept=[k["text"] for k in kept], timeline=timeline,
                   broll=[(b0, b1, os.path.basename(it["path"]), w) for b0, b1, it, w in placements],
                   scenes=scenes, sfx=cues, music=bool(music)),
              open(os.path.join(work, "edit.json"), "w"), ensure_ascii=False, indent=1)
    log(f"done: {a.output} ({out_dur:.1f}s, {mb:.1f} MB, {time.time() - t0:.0f}s)")
    if not a.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return dict(style=style, work=work)


if __name__ == "__main__":
    main()
