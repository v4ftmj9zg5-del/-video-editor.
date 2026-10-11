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
