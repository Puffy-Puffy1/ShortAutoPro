#!/usr/bin/env python3

import os
import sys
import subprocess
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

ROTEIRO = os.path.join(
    BASE,
    "roteiros",
    f"short_{SHORT_ID}.txt"
)

AUDIO_DIR = os.path.join(
    BASE,
    "audios"
)

VOICE_DIR = os.path.join(
    BASE,
    "piper",
    "voice"
)

os.makedirs(AUDIO_DIR, exist_ok=True)

RAW = os.path.join(
    AUDIO_DIR,
    f"short_{SHORT_ID}.raw"
)

WAV = os.path.join(
    AUDIO_DIR,
    f"short_{SHORT_ID}.wav"
)

MP3 = os.path.join(
    AUDIO_DIR,
    f"short_{SHORT_ID}.mp3"
)

MODEL = "pt_BR-faber-medium"

if not os.path.exists(ROTEIRO):
    sys.exit(
        f"ERRO: roteiro não encontrado:\n{ROTEIRO}"
    )

with open(
    ROTEIRO,
    encoding="utf-8"
) as f:
    texto = f.read().strip()

if not texto:
    sys.exit("ERRO: roteiro vazio.")

env = os.environ.copy()

env["PIPER_VOICE_PATH"] = VOICE_DIR

print()
print("================================")
print("GERANDO VOZ COM PIPER...")
print("================================")
print()

try:

    subprocess.run(
        [
            "piper",
            "-m",
            MODEL,
            "-f",
            RAW,
            "--",
            texto
        ],
        env=env,
        check=True
    )

except Exception as e:
    sys.exit(
        f"ERRO PIPER: {e}"
    )

try:

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "f32le",
            "-ar",
            "22050",
            "-ac",
            "1",
            "-i",
            RAW,
            WAV
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            WAV,
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "128k",
            MP3
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

except Exception as e:

    sys.exit(
        f"ERRO convertendo áudio: {e}"
    )

for arquivo in [RAW, WAV]:

    if os.path.exists(arquivo):
        os.remove(arquivo)

print()
print("ÁUDIO PIPER GERADO!")
print(MP3)
print()
