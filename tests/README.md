# Tests for make_reel.py

```
pip install -r requirements.txt
tools/fetch_models.sh
python3 tests/make_fixtures.py /tmp/fx          # builds the test videos + B-roll
python3 tests/test_reels.py /tmp/fx /tmp/out     # renders 4 style runs + 2 Auto runs, checks them
```

The fixtures are two synthetic "talking" videos with Hebrew speech (Google TTS,
cached in `tests/fixtures/tts/` so no network is needed), each with a known script,
long pauses and one deliberate retake. `calm` is landscape 25 fps with hum, hiss
and a low recording level; `lively` is portrait, fast, handheld with hard cuts.

Each check measures the output file; see the docstring at the top of
`test_reels.py` for the list. Results land in `OUT/results.json`.
A full run takes about 15 minutes on 4 CPU cores.

## Motion graphics (Remotion) demo

```
cd remotion && npm install && cd ..                       # Remotion 4 + React, once
python3 tests/make_demo.py /tmp/demo                      # 24 s Hebrew voice-over + illustrated room + before/after pair
python3 tools/make_reel.py /tmp/demo/demo_raw.mp4 /tmp/demo/dyn.mp4 --style dynamic \
        --broll /tmp/demo/broll --keep-work /tmp/demo/w_dyn
python3 tests/test_motion.py /tmp/demo/dyn.mp4 /tmp/demo/w_dyn /tmp/demo/sheet.png
```

`test_motion.py` takes each storyboard scene and compares the final video with the
plain base video at the same moments: the overlay must cover a clear part of the frame
(not just a caption) and must change inside the scene (animated, not a static card).
It passes when every scene passes and at least 5 different animation types are present,
and it writes a contact sheet (three frames per scene) to look at.

`test_reels.py` checks captions from `captions.ass`, so it runs with `--engine ffmpeg`.
