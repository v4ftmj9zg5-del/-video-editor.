"""Calm, warm lullaby bed for soft Reels (original, synthesised: no third-party audio).

Soft felt piano (broken chords + simple melody), a quiet celesta doubling the melody an
octave up, a warm sustained pad and a natural stereo room reverb. I-V-vi-IV in F major,
one chord per bar, so cuts on bar lines land on the music.

Usage: lullaby_music.py OUT.wav [--bpm 93.75] [--bars 6]
"""
import argparse
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def piano(f, dur, vel):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k in range(1, 7):
        fk = f * k * (1 + .0004 * k * k)               # slight string inharmonicity
        out += (1 / k ** 1.7) * np.sin(2 * np.pi * fk * t) * np.exp(-t * (.9 + .7 * k))
    att = np.minimum(1, t / .012)                      # felt hammer: soft attack
    rel = np.minimum(1, (dur - t) / .25)
    return vel * att * rel * out


def celesta(f, dur, vel):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t * 2.4) + .25 * np.sin(2 * np.pi * f * 4.01 * t) * np.exp(-t * 7)
    return vel * np.minimum(1, t / .004) * s


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for det in (-.15, .15):
            ph = rng.uniform(0, 6.28)
            out += np.sin(2 * np.pi * (f + det) * t + ph) + .18 * np.sin(2 * np.pi * 2 * (f + det) * t + ph)
    a, r = int(1.2 * SR), int(1.4 * SR)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a) ** 2
    env[-r:] *= np.linspace(1, 0, r) ** 2
    return out * env / (2 * len(freqs))


def room(x, secs=2.8, wet=.32):
    """Stereo convolution reverb with decorrelated exponentially decaying noise."""
    n = int(secs * SR)
    t = np.arange(n) / SR
    outs = []
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t * 6.9 / secs)
        ir = np.convolve(ir, np.ones(8) / 8, mode="same")   # darken the tail
        ir[: int(.012 * SR)] = 0                              # 12 ms pre-delay
        ir /= np.sqrt((ir ** 2).sum())
        L = len(x) + n
        N = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[: len(x)]
        outs.append((1 - wet) * x + wet * y * 2.2)
    return np.stack(outs, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--bpm", type=float, default=93.75)
    ap.add_argument("--bars", type=int, default=6)
    a = ap.parse_args()
    beat = 60 / a.bpm
    total = a.bars * 4 * beat
    n = int((total + 3) * SR)
    x = np.zeros(n)

    def put(sig, t0):
        j = int(t0 * SR)
        x[j:j + len(sig)] += sig[: max(0, n - j)]

    # F, C/E, Dm, Bb, F/C, F  (bass note, broken-chord tones)
    chords = [(41, [53, 57, 60, 65]), (40, [52, 55, 60, 64]), (38, [50, 57, 62, 65]),
              (34, [46, 53, 58, 62]), (36, [48, 57, 60, 65]), (41, [53, 57, 60, 65])]
    melody = [[(69, 2), (72, 1), (69, 1)], [(67, 2), (64, 1), (67, 1)], [(65, 2), (69, 1), (74, 1)],
              [(72, 3), (70, 1)], [(69, 2), (67, 1), (65, 1)], [(65, 4)]]
    for b in range(a.bars):
        bass, tones = chords[b % len(chords)]
        t0 = b * 4 * beat
        last = b == a.bars - 1
        p = pad([hz(m) for m in tones[:3]], 4 * beat + (2.5 if last else 1.0))
        put(.10 * p, t0)
        put(piano(hz(bass), 4 * beat + 1.5, .16), t0)
        pattern = [0, 2, 1, 3] if not last else [0, 1, 2, 3]
        for k, i in enumerate(pattern):                  # broken chord on each beat
            if b == 0 and k % 2:                         # sparser opening
                continue
            put(piano(hz(tones[i]), 2.6, .10 if k else .13), t0 + k * beat + (.02 if k else 0))
        tm = t0
        for m, d in melody[b % len(melody)]:
            if b == 0 and tm < t0 + beat:                # let the first beat breathe
                tm += d * beat
                continue
            put(piano(hz(m), d * beat + 1.2, .24), tm)
            put(celesta(hz(m + 12), 1.4, .035), tm + .01)
            tm += d * beat

    st = room(np.tanh(x * 1.4) / 1.4)
    st = st[: int((total + 2.2) * SR)]
    fade = int(2.0 * SR)
    st[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 1.5
    st /= np.abs(st).max() / .85
    with wave.open(a.out, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print(f"wrote {a.out} ({len(st) / SR:.2f}s)")


if __name__ == "__main__":
    main()
