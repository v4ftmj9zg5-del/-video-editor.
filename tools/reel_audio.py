"""Original music bed + sound design + voice-over mix for a Reel (48 kHz stereo WAV).

The music is synthesised here (no third-party audio): soft keys arpeggio, pad and bass
over Dmaj7-Bm7-Gmaj7-A at a fixed BPM, a light shaker after the hook, synthetic
reverb, ducked under the voice. SFX: whoosh on every cut, tick on step numbers,
paper slides, a sparkle on the call to action.

Usage: reel_audio.py PLAN.json OUT.wav
PLAN = {"bpm": 90, "style": "gentle" (optional: felt piano, no shaker), "scenes": [beats...], "vo": [{"file": path, "scene": i, "offset": s}], "whooshes": [i, ...],
        "papers": [[scene, offset], ...], "ticks": [scene, ...], "sparkle": [scene, offset]}
"""
import json
import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(11)


def note(n):            # MIDI -> Hz
    return 440.0 * 2 ** ((n - 69) / 12)


def env_adsr(n, a, d, s, r, sr=SR):
    a, d, r = int(a * sr), int(d * sr), int(r * sr)
    e = np.ones(n) * s
    e[:a] = np.linspace(0, 1, a, endpoint=False) if a else e[:a]
    e[a:a + d] = np.linspace(1, s, d, endpoint=False)[: max(0, min(d, n - a))]
    if r:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def keys(freq, dur, vel, soft=False):
    """Soft electric-piano tine: decaying fundamental + quickly decaying overtone (soft=True: felt piano)."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * freq * t) * np.exp(-t * (1.1 if soft else 2.2))
    if soft:
        att = np.minimum(1, t / .03)
        return vel * att * (body + .08 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 6))
    tine = .35 * np.sin(2 * np.pi * freq * 2 * t) * np.exp(-t * 9) + .12 * np.sin(2 * np.pi * freq * 3.01 * t) * np.exp(-t * 14)
    att = np.minimum(1, t / .006)
    return vel * att * (body + tine)


def pad(freqs, dur):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f in freqs:
        for det in (-.12, .12):
            out += np.sin(2 * np.pi * (f + det) * t + rng.uniform(0, 6.28))
    out *= env_adsr(n, .7, .3, .85, .9) / (2 * len(freqs))
    return out


def bass(freq, dur, vel):
    n = int(dur * SR)
    t = np.arange(n) / SR
    return vel * np.sin(2 * np.pi * freq * t) * np.exp(-t * 1.6) * np.minimum(1, t / .01)


def noise_burst(dur, lp=.08, level=1.0):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):           # one-pole low-pass
        acc += lp * (x[i] - acc)
        y[i] = acc
    return level * y / (np.abs(y).max() + 1e-9)


def whoosh(dur=.5, level=.5):
    n = int(dur * SR)
    x = rng.standard_normal(n)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):           # cutoff sweeps up then down
        p = i / n
        a = .015 + .22 * np.sin(np.pi * p) ** 2
        acc += a * (x[i] - acc)
        y[i] = acc
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.6
    return level * y * e / (np.abs(y).max() + 1e-9)


def tick(level=.35):
    n = int(.09 * SR)
    t = np.arange(n) / SR
    f = 1500 - 600 * t / .09
    return level * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 55)


def thud(level=.5):
    """Soft landing: low sine knock + a little felt noise."""
    n = int(.35 * SR)
    t = np.arange(n) / SR
    f = 95 - 40 * t / .35
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 16)
    felt = noise_burst(.35, lp=.05, level=.35) * np.exp(-t * 30)
    return level * (body + felt) * np.minimum(1, t / .003)


def pop(level=.22):
    """Gentle pop for small decor."""
    n = int(.12 * SR)
    t = np.arange(n) / SR
    f = 620 + 900 * np.exp(-t * 40)
    return level * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 38)


def sparkle(level=.25):
    out = np.zeros(int(1.6 * SR))
    for k, m in enumerate((86, 90, 93, 98)):          # D6 F#6 A6 D7
        s = keys(note(m), 1.2, level * (1 - .12 * k))
        o = int(k * .07 * SR)
        out[o:o + len(s)] += s[: len(out) - o]
    return out


def reverb(x, secs=1.9, wet=.28):
    n = int(secs * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir = np.convolve(ir, np.ones(24) / 24, mode="same")      # darker tail
    ir /= np.sqrt((ir ** 2).sum())
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[: len(x)]
    return (1 - wet) * x + wet * y * .9


def read_wav(path):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
        assert w.getframerate() == SR, path
    return a


def music(total_beats, bpm, hook_beats, gentle=False):
    beat = 60 / bpm
    total = total_beats * beat + 2.5
    out = np.zeros(int(total * SR))
    perc = np.zeros_like(out)
    # Dmaj7, Bm7, Gmaj7, A(add9) ; voicings in MIDI
    chords = [([50], [62, 66, 69, 73]), ([47], [62, 66, 69, 71]), ([43], [62, 67, 71, 74]), ([45], [61, 64, 69, 71])]
    arp = [0, 2, 1, 3, 2, 1, 3, 2]                     # eighth-note pattern over chord tones
    bars = int(np.ceil(total_beats / 4))
    for b in range(bars):
        root, tones = chords[b % 4]
        t0 = b * 4 * beat
        last = b == bars - 1
        p = pad([note(m - 12) for m in tones[:3]], 4 * beat + (2.2 if last else .9))
        i0 = int(t0 * SR)
        out[i0:i0 + len(p)] += (.8 if gentle else .55) * p[: len(out) - i0]
        bs = bass(note(root[0]), 2 * beat + .3, .18 if gentle else .5)
        for k in (0, 2):
            j = int((t0 + k * beat) * SR)
            out[j:j + len(bs)] += bs[: len(out) - j]
        for e in range(8):
            te = t0 + e * beat / 2
            if te >= total_beats * beat:
                break
            m = tones[arp[e]] + (12 if e in (3, 6) else 0)
            vel = .16 if e % 2 else .22
            if gentle and e % 2:                       # gentle: quarter notes only
                continue
            if b * 4 < hook_beats and e % 2:          # sparser during the hook
                continue
            s = keys(note(m), 2.4 if gentle else 1.6, vel * (.8 if gentle else 1), soft=gentle)
            j = int(te * SR)
            out[j:j + len(s)] += s[: len(out) - j]
            if not gentle and b * 4 >= hook_beats and not last and e % 2:   # shaker on off-beats after the hook
                sh = noise_burst(.05, lp=.6, level=.05) * np.exp(-np.arange(int(.05 * SR)) / SR * 70)
                perc[j:j + len(sh)] += sh[: len(perc) - j]
    end_chord = keys(note(74), 2.2, .18, soft=gentle) + keys(note(78), 2.2, .14, soft=gentle)   # final D/F# shimmer
    j = int((total_beats * beat - .05) * SR)
    out[j:j + len(end_chord)] += end_chord[: len(out) - j]
    mix = (reverb(out, secs=2.6, wet=.4) if gentle else reverb(out)) + perc
    fade = int(1.2 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix


def main(plan_path, out):
    P = json.load(open(plan_path))
    bpm, beats = P["bpm"], P["scenes"]
    beat = 60 / bpm
    starts = np.concatenate([[0], np.cumsum(beats)[:-1]]) * beat
    total = sum(beats) * beat
    n = int(total * SR)

    mus = music(sum(beats), bpm, beats[0], gentle=P.get("style") == "gentle")[:n]
    mus = np.pad(mus, (0, max(0, n - len(mus))))

    vo = np.zeros(n)
    for v in P.get("vo", []):
        a = read_wav(v["file"])
        a = a / (np.abs(a).max() + 1e-9) * .7
        j = int((starts[v["scene"]] + v["offset"]) * SR)
        vo[j:j + len(a)] += a[: n - j]

    sfx = np.zeros(n)

    def put(sig, t):
        j = max(0, int(t * SR))
        sfx[j:j + len(sig)] += sig[: max(0, n - j)]

    for i in P.get("whooshes", range(1, len(starts))):    # default: a whoosh on every cut
        put(whoosh(.55, .32), starts[i] - .36)
    for i in P.get("ticks", []):
        put(tick(.28), starts[i] + .06)
    for i, off in P.get("papers", []):
        put(noise_burst(.22, lp=.25, level=.11) * np.linspace(1, 0, int(.22 * SR)) ** 2, starts[i] + off)
    for i, off in P.get("thuds", []):
        put(thud(.5), starts[i] + off)
    for i, off in P.get("pops", []):
        put(pop(.2), starts[i] + off)
    if "sparkle" in P:
        i, off = P["sparkle"]
        put(sparkle(.2), starts[i] + off)

    # duck music under the voice
    env = np.convolve(np.abs(vo), np.ones(int(.12 * SR)) / int(.12 * SR), mode="same")
    env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
    env = np.convolve(env, np.ones(int(.25 * SR)) / int(.25 * SR), mode="same")
    mus_d = mus * (1 - .55 * env)

    mono = .55 * mus_d / (np.abs(mus).max() + 1e-9) + vo + sfx
    # gentle stereo: music/sfx slightly widened with a 9 ms offset, voice centred
    d = int(.009 * SR)
    side = np.concatenate([np.zeros(d), (.55 * mus_d / (np.abs(mus).max() + 1e-9) + sfx)[:-d]])
    left = mono
    right = vo + .5 * (.55 * mus_d / (np.abs(mus).max() + 1e-9) + sfx) + .5 * side
    st = np.stack([left, right], 1)
    st /= np.abs(st).max() / .89
    with wave.open(out, "w") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print(f"wrote {out} ({total:.2f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
