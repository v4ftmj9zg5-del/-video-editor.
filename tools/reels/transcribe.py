"""Speech detection (Silero VAD) + Hebrew transcription (Whisper large-v3-turbo),
both run on CPU through sherpa-onnx. Models come from GitHub releases, see
tools/fetch_models.sh.

Whisper in sherpa-onnx returns text per segment but no word timestamps, so each
VAD phrase is transcribed on its own and word times are spread across the
phrase in proportion to word length. Phrases are short (VAD splits on 0.25 s
pauses), which keeps caption timing within a few hundred ms.
"""
import os
import re
import subprocess

import numpy as np

SR = 16000
MODELS = os.path.expanduser(os.environ.get("MODELS", "~/models"))
WHISPER = os.environ.get("WHISPER_DIR", os.path.join(MODELS, "sherpa-onnx-whisper-turbo"))


# Whisper hears better through the same light clean-up the final voice gets
ASR_CLEAN = "highpass=f=80,highpass=f=80,afftdn=nr=12:nf=-50:tn=1,loudnorm=I=-18:TP=-2"


def load_audio(path, sr=SR, clean=False):
    af = ["-af", ASR_CLEAN] if clean else []
    pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1"] + af +
                                  ["-ar", str(sr), "-f", "s16le", "-"])
    return np.frombuffer(pcm, np.int16).astype(np.float32) / 32768


def speech_segments(audio, min_silence=0.25, min_speech=0.15, threshold=0.5):
    """[(start, end)] in seconds of every spoken phrase."""
    import sherpa_onnx
    cfg = sherpa_onnx.VadModelConfig()
    cfg.silero_vad.model = os.path.join(MODELS, "silero_vad.onnx")
    cfg.silero_vad.threshold = threshold
    cfg.silero_vad.min_silence_duration = min_silence
    cfg.silero_vad.min_speech_duration = min_speech
    cfg.silero_vad.max_speech_duration = 20
    cfg.sample_rate = SR
    vad = sherpa_onnx.VoiceActivityDetector(cfg, buffer_size_in_seconds=120)
    win = cfg.silero_vad.window_size
    out = []

    def drain():
        while not vad.empty():
            s = vad.front
            out.append((s.start / SR, (s.start + len(s.samples)) / SR))
            vad.pop()

    for i in range(0, len(audio), win):
        chunk = audio[i:i + win]
        if len(chunk) < win:
            chunk = np.pad(chunk, (0, win - len(chunk)))
        vad.accept_waveform(chunk)
        drain()
    vad.flush()
    drain()
    return out


_recognizer = None


def recognizer():
    global _recognizer
    if _recognizer is None:
        import sherpa_onnx
        pre = os.path.basename(WHISPER).replace("sherpa-onnx-whisper-", "")
        _recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
            encoder=f"{WHISPER}/{pre}-encoder.int8.onnx",
            decoder=f"{WHISPER}/{pre}-decoder.int8.onnx",
            tokens=f"{WHISPER}/{pre}-tokens.txt",
            language="he", task="transcribe", num_threads=os.cpu_count())
    return _recognizer


def transcribe_segment(audio, start, end, pad=0.15):
    a = audio[max(0, int((start - pad) * SR)):int((end + pad) * SR)]
    # Whisper drops a phrase's last word when the audio stops abruptly; trailing
    # silence lets it finish the sentence
    a = np.concatenate([np.zeros(int(0.2 * SR), np.float32), a, np.zeros(int(0.6 * SR), np.float32)])
    s = recognizer().create_stream()
    s.accept_waveform(SR, a)
    recognizer().decode_stream(s)
    return s.result.text.strip()


def spread_words(text, start, end):
    """Word timings inside a phrase, proportional to word length."""
    words = text.split()
    if not words:
        return []
    weights = np.array([len(re.sub(r"[^\w]", "", w)) + 1.5 for w in words], float)
    edges = start + (end - start) * np.concatenate([[0], np.cumsum(weights) / weights.sum()])
    return [dict(w=w, s=float(edges[i]), e=float(edges[i + 1])) for i, w in enumerate(words)]


def transcribe(path, log=print):
    """Phrases: [{s, e, text, words:[{w,s,e}]}] in source seconds."""
    audio = load_audio(path, clean=True)
    segs = speech_segments(audio)
    log(f"  {len(segs)} spoken phrases found")
    phrases = []
    for s, e in segs:
        text = transcribe_segment(audio, s, e)
        phrases.append(dict(s=s, e=e, text=text, words=spread_words(text, s, e)))
    return phrases, len(audio) / SR
