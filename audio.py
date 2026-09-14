#!/usr/bin/env python3

import json
import math
import os
import shutil
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path

BASE = os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))
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
REPORT = Path(BASE) / "reports" / "evolution" / f"audio_{SHORT_ID}.json"


def bounded_env_float(name, default, low, high):
    try:
        value = float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = float(default)
    if not math.isfinite(value):
        value = float(default)
    return max(float(low), min(float(high), value))


# Voz falada para Shorts: forte o suficiente no celular, com pico seguro.
TARGET_LUFS = bounded_env_float("SAP_AUDIO_TARGET_LUFS", -14.0, -24.0, -10.0)
TRUE_PEAK_DB = bounded_env_float("SAP_AUDIO_TRUE_PEAK_DB", -1.5, -3.0, -0.5)
LRA = bounded_env_float("SAP_AUDIO_LRA", 7.0, 1.0, 20.0)


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


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


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
print("GERANDO VOZ COM PIPER - 3.0")
print("PIPER + LOUDNESS MASTERING")
print("================================")
print(f"Modelo: {MODEL}")
print(f"Master: {TARGET_LUFS:.1f} LUFS | TP {TRUE_PEAK_DB:.1f} dB | LRA {LRA:.1f}")
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

    loudnorm = f"loudnorm=I={TARGET_LUFS:.1f}:TP={TRUE_PEAK_DB:.1f}:LRA={LRA:.1f}"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", WAV,
            "-af", loudnorm,
            "-ar", "44100", "-ac", "1",
            "-codec:a", "libmp3lame", "-b:a", "160k",
            MP3_TMP,
        ],
        check=True,
        timeout=120,
    )
except subprocess.TimeoutExpired:
    fail("conversão/masterização de áudio excedeu o tempo limite")
except subprocess.CalledProcessError as exc:
    fail(f"FFmpeg falhou convertendo/masterizando áudio (código {exc.returncode})")
except Exception as exc:
    fail(f"falha convertendo/masterizando áudio: {exc}")

if not os.path.isfile(MP3_TMP) or os.path.getsize(MP3_TMP) <= 0:
    fail("MP3 temporário não foi criado")

duration = audio_duration(MP3_TMP)

try:
    os.replace(MP3_TMP, MP3)
except Exception as exc:
    fail(f"não foi possível publicar o MP3 final: {exc}")
finally:
    cleanup()

report = {
    "short_id": SHORT_ID,
    "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    "model": MODEL,
    "duration_seconds": round(duration, 3),
    "mastering": {
        "filter": "loudnorm",
        "target_lufs": TARGET_LUFS,
        "true_peak_db": TRUE_PEAK_DB,
        "lra": LRA,
        "bitrate": "160k",
        "sample_rate": 44100,
        "channels": 1
    },
    "status": "PASS"
}
try:
    atomic_json(REPORT, report)
except Exception as exc:
    print(f"AVISO: não foi possível gravar relatório de áudio: {exc}")

print()
print("ÁUDIO PIPER GERADO E MASTERIZADO!")
print(f"Duração: {duration:.2f}s")
print(f"Loudness alvo: {TARGET_LUFS:.1f} LUFS")
print(MP3)
print()
