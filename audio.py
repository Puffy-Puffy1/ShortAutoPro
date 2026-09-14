#!/usr/bin/env python3

import math
import os
import shutil
import subprocess
import sys
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat())
ROTEIRO = os.path.join(BASE, "roteiros", f"short_{SHORT_ID}.txt")
AUDIO_DIR = os.path.join(BASE, "audios")
VOICE_DIR = os.path.join(BASE, "piper", "voice")
os.makedirs(AUDIO_DIR, exist_ok=True)

MP3 = os.path.join(AUDIO_DIR, f"short_{SHORT_ID}.mp3")
MODEL = os.getenv("PIPER_MODEL", "pt_BR-faber-medium").strip() or "pt_BR-faber-medium"
PID = os.getpid()
RAW = os.path.join(AUDIO_DIR, f".short_{SHORT_ID}.{PID}.raw")
WAV = os.path.join(AUDIO_DIR, f".short_{SHORT_ID}.{PID}.wav")
MP3_TMP = os.path.join(AUDIO_DIR, f".short_{SHORT_ID}.{PID}.mp3")
TEMP_FILES = [RAW, WAV, MP3_TMP]


def cleanup():
    for path in TEMP_FILES:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def fail(message):
    cleanup()
    raise SystemExit(f"ERRO: {message}")


def audio_duration(path):
    try:
        raw = subprocess.check_output(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        ).strip()
        value = float(raw)
    except Exception as exc:
        fail(f"não foi possível validar o áudio: {exc}")
    if not math.isfinite(value) or value < 5.0:
        fail(f"duração de áudio inválida: {value!r}s")
    return value


if not os.path.isfile(ROTEIRO):
    fail(f"roteiro não encontrado: {ROTEIRO}")

try:
    with open(ROTEIRO, "r", encoding="utf-8") as f:
        texto = f.read().strip()
except Exception as exc:
    fail(f"não foi possível ler o roteiro: {exc}")

if not texto:
    fail("roteiro vazio")
if len(texto) > 20000:
    fail("roteiro excede limite de segurança para TTS")

if shutil.which("piper") is None:
    fail("comando piper não encontrado")
if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
    fail("ffmpeg/ffprobe não encontrados")
if not os.path.isdir(VOICE_DIR):
    fail(f"pasta de voz Piper não encontrada: {VOICE_DIR}")

cleanup()
env = os.environ.copy()
env["PIPER_VOICE_PATH"] = VOICE_DIR

print()
print("================================")
print("GERANDO VOZ COM PIPER - 2.1")
print("================================")
print(f"Modelo: {MODEL}")
print()

try:
    subprocess.run(
        ["piper", "-m", MODEL, "-f", RAW, "--", texto],
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=180,
    )
except subprocess.TimeoutExpired:
    fail("Piper excedeu 180 segundos")
except subprocess.CalledProcessError as exc:
    detalhe = (exc.stderr or "").strip()[-1000:]
    fail(f"Piper falhou (código {exc.returncode}): {detalhe}")
except Exception as exc:
    fail(f"Piper falhou: {exc}")

if not os.path.isfile(RAW) or os.path.getsize(RAW) <= 0:
    fail("Piper não produziu áudio RAW válido")

try:
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "f32le", "-ar", "22050", "-ac", "1",
            "-i", RAW, WAV,
        ],
        check=True,
        timeout=120,
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", WAV, "-codec:a", "libmp3lame", "-b:a", "128k",
            MP3_TMP,
        ],
        check=True,
        timeout=120,
    )
except subprocess.TimeoutExpired:
    fail("conversão de áudio excedeu o tempo limite")
except subprocess.CalledProcessError as exc:
    fail(f"FFmpeg falhou convertendo áudio (código {exc.returncode})")
except Exception as exc:
    fail(f"falha convertendo áudio: {exc}")

if not os.path.isfile(MP3_TMP) or os.path.getsize(MP3_TMP) <= 0:
    fail("MP3 temporário não foi criado")

duration = audio_duration(MP3_TMP)

try:
    os.replace(MP3_TMP, MP3)
except Exception as exc:
    fail(f"não foi possível publicar o MP3 final: {exc}")
finally:
    cleanup()

print()
print("ÁUDIO PIPER GERADO!")
print(f"Duração: {duration:.2f}s")
print(MP3)
print()
