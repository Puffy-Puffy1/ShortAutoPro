#!/usr/bin/env python3

import os
import sys
import glob
import random
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

ASS = os.path.join(
    BASE,
    "videos",
    f"short_{SHORT_ID}.ass"
)

MUSIC_DIR = os.path.join(
    BASE,
    "musicas"
)

SAIDA = os.path.join(
    BASE,
    "videos",
    f"short_v5_{SHORT_ID}.mp4"
)

USAR_MUSICA = (
    os.getenv(
        "SHORT_USAR_MUSICA",
        "0"
    ) == "1"
)

try:
    MUSICA_VOLUME = float(
        os.getenv(
            "SHORT_MUSICA_VOLUME",
            "0.08"
        )
    )
except ValueError:
    MUSICA_VOLUME = 0.08

MUSICA_VOLUME = max(
    0.01,
    min(
        MUSICA_VOLUME,
        0.30
    )
)

for arquivo in [
    VIDEO_BASE,
    AUDIO,
    ASS
]:
    if not os.path.exists(arquivo):

        sys.exit(
            f"ERRO: arquivo não encontrado:\n"
            f"{arquivo}"
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

ass = (
    os.path.abspath(ASS)
    .replace("\\", "\\\\")
    .replace(":", "\\:")
    .replace("'", "\\'")
)

filtro_video = (
    f"ass='{ass}'"
)

os.makedirs(
    MUSIC_DIR,
    exist_ok=True
)

musicas = []

for ext in [
    "*.mp3",
    "*.wav",
    "*.m4a",
    "*.aac",
    "*.ogg"
]:

    musicas.extend(
        glob.glob(
            os.path.join(
                MUSIC_DIR,
                ext
            )
        )
    )

usar_musica_agora = (
    USAR_MUSICA
    and len(musicas) > 0
)

print()
print("================================")
print("CRIANDO SHORT V5...")
print("================================")
print()

print(
    f"Música: "
    f"{'ON' if usar_musica_agora else 'OFF'}"
)

if USAR_MUSICA and not musicas:

    print(
        "AVISO: música ativada, "
        "mas nenhuma faixa foi encontrada."
    )

if usar_musica_agora:

    musica = random.choice(
        musicas
    )

    print(
        "Faixa:"
    )

    print(
        musica
    )

    fade_out_inicio = max(
        0,
        duracao - 1.5
    )

    filtro_audio = (
        f"[1:a]"
        f"volume=1.0"
        f"[voz];"
        f"[2:a]"
        f"volume={MUSICA_VOLUME},"
        f"afade=t=in:"
        f"st=0:"
        f"d=1.2,"
        f"afade=t=out:"
        f"st={fade_out_inicio}:"
        f"d=1.5"
        f"[musica];"
        f"[voz][musica]"
        f"amix="
        f"inputs=2:"
        f"duration=first:"
        f"dropout_transition=2"
        f"[mix]"
    )

    comando = [
        "ffmpeg",
        "-y",

        "-i",
        VIDEO_BASE,

        "-i",
        AUDIO,

        "-stream_loop",
        "-1",

        "-i",
        musica,

        "-filter_complex",
        filtro_audio,

        "-vf",
        filtro_video,

        "-map",
        "0:v",

        "-map",
        "[mix]",

        "-c:v",
        "libx264",

        "-preset",
        os.getenv(
            "SHORT_PRESET",
            "fast"
        ),

        "-crf",
        os.getenv(
            "SHORT_CRF",
            "21"
        ),

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "160k",

        "-t",
        str(duracao),

        "-movflags",
        "+faststart",

        SAIDA
    ]

else:

    comando = [
        "ffmpeg",
        "-y",

        "-i",
        VIDEO_BASE,

        "-i",
        AUDIO,

        "-vf",
        filtro_video,

        "-c:v",
        "libx264",

        "-preset",
        os.getenv(
            "SHORT_PRESET",
            "fast"
        ),

        "-crf",
        os.getenv(
            "SHORT_CRF",
            "21"
        ),

        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",

        "-b:a",
        "160k",

        "-t",
        str(duracao),

        "-movflags",
        "+faststart",

        SAIDA
    ]

try:

    subprocess.run(
        comando,
        check=True
    )

except subprocess.CalledProcessError:

    sys.exit(
        "ERRO: FFmpeg não conseguiu "
        "criar o V5."
    )

print()
print("================================")
print("SHORT V5 CRIADO!")
print("================================")
print()
print(SAIDA)
print()
