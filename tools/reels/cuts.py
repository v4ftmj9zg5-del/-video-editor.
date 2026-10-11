"""Decide what to keep: drop silences, filler-only phrases and retakes
(a phrase the speaker restarted), then map source time to output time."""
import difflib
import re

# Hebrew hesitation sounds Whisper sometimes writes out
FILLERS = {"אה", "אהה", "אההה", "אמ", "אממ", "אמממ", "הממ", "מממ", "אם", "eh", "um", "uh"}


def norm(text):
    text = re.sub(r"[֑-ׇ]", "", text)  # niqqud / cantillation
    return [w for w in re.sub(r"[^\w\s]", " ", text).split() if w]


def is_filler(p):
    words = norm(p["text"])
    return not words or all(w in FILLERS for w in words)


# Sound-alike letters Whisper swaps between takes (טעות/תאות, שנייה/שניה)
_SOUND = str.maketrans({"ט": "ת", "ק": "כ", "ח": "כ", "ע": "", "א": "", "ו": "", "י": "",
                        "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ", "ס": "ש"})


def sound_key(words):
    return " ".join(w.translate(_SOUND) for w in words)


def is_retake(a, b):
    """True when phrase a is a false start that phrase b says again.

    Compared by sound, letter by letter (Whisper may spell a repeated word
    differently, e.g. טעות / תאות): a must match the opening of b, which carries on."""
    wa, wb = norm(a["text"]), norm(b["text"])
    if not wa or not wb:
        return False
    if len(wa) == 1:  # one-word false start: must be b's first word
        return len(wb) > 1 and sound_key(wa) == sound_key(wb[:1])
    ra, rb = sound_key(wa), sound_key(wb)
    r = difflib.SequenceMatcher(None, ra, rb[:len(ra) + 2]).ratio()
    return (r >= 0.75 and len(rb) > len(ra) + 2) or (r >= 0.9 and len(rb) >= len(ra))


def plan(phrases, total, preset, log=print):
    keep = []
    for i, p in enumerate(phrases):
        if is_filler(p):
            log(f"  drop filler {p['s']:.2f}-{p['e']:.2f}: {p['text']!r}")
            continue
        nxt = next((q for q in phrases[i + 1:i + 3] if not is_filler(q)), None)
        if nxt is not None and is_retake(p, nxt):
            log(f"  drop retake {p['s']:.2f}-{p['e']:.2f}: {p['text']!r}")
            continue
        keep.append(p)

    clips = []
    for p in keep:
        s = max(0.0, p["s"] - preset["pad_before"])
        e = min(total, p["e"] + preset["pad_after"])
        if clips and s - clips[-1][1] < preset["merge_gap"]:
            clips[-1][1] = max(clips[-1][1], e)
        else:
            clips.append([s, e])
    timeline, t = [], 0.0
    for s, e in clips:
        timeline.append(dict(src_s=s, src_e=e, out_s=t, out_e=t + (e - s)))
        t += e - s
    return keep, timeline


def to_out(timeline, src_t):
    """Map a source time to output time (None if it was cut)."""
    for c in timeline:
        if c["src_s"] <= src_t <= c["src_e"]:
            return c["out_s"] + src_t - c["src_s"]
    return None
