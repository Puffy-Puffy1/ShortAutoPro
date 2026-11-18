#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

BASE="${SHORTAUTOPRO_BASE:-$HOME/ShortAutoPro}"
WHISPER_DIR="${WHISPER_DIR:-$HOME/whisper.cpp}"
VOICE_DIR="$BASE/piper/voice"
WHISPER_CLI="$WHISPER_DIR/build/bin/whisper-cli"
WHISPER_MODEL="$WHISPER_DIR/models/ggml-base.bin"
VOICE_MODEL="$VOICE_DIR/pt_BR-faber-medium.onnx"
VOICE_CONFIG="$VOICE_MODEL.json"
VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx"
VOICE_CONFIG_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx.json"
VOICE_SHA256="75e913eb463db0b6ac7ddf68d3e4c9ac19ace36dc3b710a81039b448352b8ffc"

log() { printf '\n[ShortAutoPro Termux] %s\n' "$*"; }
fail() { printf '\nERRO: %s\n' "$*" >&2; exit 1; }
need_termux() {
    [ -n "${PREFIX:-}" ] && command -v pkg >/dev/null 2>&1 \
        || fail "Execute este arquivo dentro do aplicativo Termux."
}
download() {
    local url="$1" output="$2"
    curl --fail --location --retry 3 --connect-timeout 20 --output "$output.tmp" "$url"
    [ -s "$output.tmp" ] || fail "Download vazio: $url"
    mv "$output.tmp" "$output"
}
need_termux

case "$(uname -m)" in
    aarch64|arm64) ;;
    *) fail "Piper empacotado para Termux exige Android ARM64 (aarch64). Detectado: $(uname -m)" ;;
esac

log "Instalando ferramentas gratuitas do repositório Termux..."
pkg update -y
pkg install -y python ffmpeg git cmake clang make pkg-config curl wget coreutils

log "Instalando dependência Python usada pela pesquisa pública..."
python -m pip install --upgrade requests

log "Preparando Whisper.cpp (código aberto, processamento local)..."
if [ ! -d "$WHISPER_DIR/.git" ]; then
    git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git "$WHISPER_DIR"
fi
if [ ! -x "$WHISPER_CLI" ]; then
    cmake -S "$WHISPER_DIR" -B "$WHISPER_DIR/build" -DCMAKE_BUILD_TYPE=Release
    JOBS="${SAP_BUILD_JOBS:-2}"
    case "$JOBS" in ''|*[!0-9]*) JOBS=2;; esac
    [ "$JOBS" -ge 1 ] && [ "$JOBS" -le 4 ] || JOBS=2
    cmake --build "$WHISPER_DIR/build" --config Release --target whisper-cli -j "$JOBS"
fi
[ -x "$WHISPER_CLI" ] || fail "Whisper CLI não foi compilado."
if [ ! -s "$WHISPER_MODEL" ]; then
    (cd "$WHISPER_DIR" && bash ./models/download-ggml-model.sh base)
fi
[ -s "$WHISPER_MODEL" ] || fail "Modelo Whisper base não encontrado após o download."

log "Instalando a voz neural pt-BR usada pelo projeto..."
mkdir -p "$VOICE_DIR"
if [ ! -s "$VOICE_MODEL" ]; then
    download "$VOICE_URL" "$VOICE_MODEL"
fi
actual_sha="$(sha256sum "$VOICE_MODEL" | awk '{print $1}')"
[ "$actual_sha" = "$VOICE_SHA256" ] || {
    rm -f "$VOICE_MODEL"
    fail "SHA-256 da voz Piper não confere. O download foi removido."
}
if [ ! -s "$VOICE_CONFIG" ]; then
    download "$VOICE_CONFIG_URL" "$VOICE_CONFIG"
fi
python - "$VOICE_CONFIG" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
rate = int(data.get("audio", {}).get("sample_rate", 0))
if not 8000 <= rate <= 48000:
    raise SystemExit("Configuração da voz Piper inválida.")
print(f"Voz pt-BR validada; sample_rate={rate} Hz")
PY

log "Conferindo ferramentas..."
for cmd in python ffmpeg ffprobe git cmake; do
    command -v "$cmd" >/dev/null 2>&1 || fail "$cmd não encontrado após a instalação."
done
[ -x "$WHISPER_CLI" ] || fail "whisper-cli ausente."
[ -s "$WHISPER_MODEL" ] || fail "modelo Whisper base ausente."
[ -s "$VOICE_MODEL" ] && [ -s "$VOICE_CONFIG" ] || fail "arquivos da voz Piper ausentes."

if ! command -v piper >/dev/null 2>&1; then
    cat <<'EOF'

FALTA UMA PEÇA: o executável Piper ainda não está instalado.
O binário de Termux é distribuído separadamente pela comunidade:
https://github.com/gyroing/piper-tts-for-termux/releases/latest

Confira se o pacote é ARM64/aarch64 e revise o repositório antes de instalar.
Depois, dentro da pasta onde salvou o .deb, execute:
  apt install -f ./NOME-DO-PACOTE.deb

Em seguida rode novamente:
  bash ~/ShortAutoPro/termux_setup.sh

O modelo de voz já foi baixado e verificado; não é necessário baixá-lo novamente.
EOF
    exit 2
fi

log "Instalação local concluída. Rodando pré-verificação do projeto..."
if [ -f "$BASE/preflight_check.sh" ]; then
    SHORTAUTOPRO_BASE="$BASE" bash "$BASE/preflight_check.sh"
else
    log "Clone o branch Studio e repita a pré-verificação."
fi
