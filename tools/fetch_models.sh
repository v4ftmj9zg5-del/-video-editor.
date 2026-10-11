#!/usr/bin/env bash
# Download the speech models make_reel.py needs into $MODELS (default ~/models).
#   Silero VAD (silence detection)        ~0.6 MB
#   Whisper large-v3-turbo, int8 (Hebrew)  ~560 MB download, ~1 GB unpacked
# Optional, slower and not more accurate on our tests:  WHISPER=large-v3 ./fetch_models.sh
set -euo pipefail
MODELS="${MODELS:-$HOME/models}"
WHISPER="${WHISPER:-turbo}"
BASE=https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models
mkdir -p "$MODELS"
cd "$MODELS"
[ -f silero_vad.onnx ] || curl -fsSL -o silero_vad.onnx "$BASE/silero_vad.onnx"
if [ ! -d "sherpa-onnx-whisper-$WHISPER" ]; then
  curl -fsSL "$BASE/sherpa-onnx-whisper-$WHISPER.tar.bz2" | tar xj
fi
echo "models ready in $MODELS"
