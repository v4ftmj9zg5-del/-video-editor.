"""Fast unit checks for retake/filler detection (no models needed).
Run: python3 tests/test_cuts.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from reels.cuts import is_filler, is_retake  # noqa: E402

P = lambda t: {"text": t}  # noqa: E731

RETAKES = [  # (false start, what follows, is it a retake?)
    ("תאות שניה.", "טעות שנייה, מורה אחת בתקרה וזהו.", True),   # Whisper spelled it differently
    ("הדבר הראשון שאני...", "הדבר הראשון שאני עושה הוא לבחור ספה", True),
    ("טעות", "טעות שנייה: מנורה אחת", True),
    ("טעות ראשונה, ספה ענקית בחדר קטן.", "תאות שניה.", False),
    ("טעות ראשונה, ספה ענקית", "טעות שנייה, מנורה אחת", False),  # same opening word only
    ("שלום לכולם.", "היום אני רוצה", False),
    ("תשמרו את הסרטון.", "ותכתבו לי בתגובות", False),
    ("אחר כך אני מוסיפה מנורה רכה בפינה.", "שנותנת אור חם בערב.", False),
]
FILLERS = [("אממ...", True), ("אה, אה", True), ("", True), ("אה, הספה", False)]


def main():
    bad = 0
    for a, b, want in RETAKES:
        got = is_retake(P(a), P(b))
        bad += got != want
        print("PASS" if got == want else "FAIL", "retake", want, a, "|", b)
    for t, want in FILLERS:
        got = is_filler(P(t))
        bad += got != want
        print("PASS" if got == want else "FAIL", "filler", want, repr(t))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
