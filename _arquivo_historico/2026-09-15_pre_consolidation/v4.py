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

VIDEO_BASE = os.path.join(
    BASE,
    "temp",
    SHORT_ID,
    "video_sem_audio.mp4"
)

AUDIO = os.path.join(
    BASE,
    "audios",
    f"short_{SHORT_ID}.mp3"
)

SRT = os.path.join(
    BASE,
    "videos",
    f"short_{SHORT_ID}.srt"
)

SAIDA = os.path.join(
    BASE,
    "videos",
    f"short_v4_{SHORT_ID}.mp4"
)

for arquivo in [VIDEO_BASE, AUDIO, SRT]:
    if not os.path.exists(arquivo):
        sys.exit(
            f"ERRO: arquivo não encontrado:\n{arquivo}"
        )

if os.path.getsize(SRT) < 20:
    sys.exit(
        "ERRO: arquivo de legenda vazio."
    )

duracao = float(
    subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            AUDIO
        ],
        text=True
    ).strip()
)

srt = (
    os.path.abspath(SRT)
    .replace("\\", "\\\\")
    .replace(":", "\\:")
    .replace("'", "\\'")
)

# Alignment=2: centralizado embaixo
# MarginV=70: coloca a legenda na zona segura
# FontSize=14: tamanho adequado para 3 palavras
filtro = (
    f"subtitles='{srt}':"
    "force_style="
    "'FontName=DejaVu Sans,"
    "FontSize=14,"
    "Bold=1,"
    "Alignment=2,"
    "MarginL=45,"
    "MarginR=45,"
    "MarginV=70,"
    "Outline=3,"
    "Shadow=1'"
)

print()
print("================================")
print("CORRIGINDO POSICAO DA LEGENDA...")
print("================================")
print()

try:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i", VIDEO_BASE,
            "-i", AUDIO,

            "-vf", filtro,

            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",

            "-c:a", "aac",
            "-b:a", "128k",

            "-t", str(duracao),

            "-movflags", "+faststart",

            SAIDA
        ],
        check=True
    )

except subprocess.CalledProcessError:
    sys.exit(
        "ERRO: FFmpeg não conseguiu criar o vídeo."
    )

print()
print("================================")
print("VIDEO COM LEGENDA CORRIGIDA!")
print("================================")
print()
print(SAIDA)
print()
