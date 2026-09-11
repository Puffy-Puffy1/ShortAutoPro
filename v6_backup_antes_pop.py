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

SFX_DIR = os.path.join(
    BASE,
    "sfx"
)

SAIDA = os.path.join(
    BASE,
    "videos",
    f"short_v6_{SHORT_ID}.mp4"
)

USAR_MUSICA = (
    os.getenv("SHORT_USAR_MUSICA", "1") == "1"
)

USAR_SFX = (
    os.getenv("SHORT_USAR_SFX", "1") == "1"
)

try:
    MUSICA_VOLUME = float(
        os.getenv(
            "SHORT_MUSICA_VOLUME",
            "0.055"
        )
    )
except ValueError:
    MUSICA_VOLUME = 0.055

try:
    SFX_VOLUME = float(
        os.getenv(
            "SHORT_SFX_VOLUME",
            "0.22"
        )
    )
except ValueError:
    SFX_VOLUME = 0.22

MUSICA_VOLUME = max(
    0.01,
    min(MUSICA_VOLUME, 0.25)
)

SFX_VOLUME = max(
    0.01,
    min(SFX_VOLUME, 0.60)
)

for arquivo in [
    VIDEO_BASE,
    AUDIO,
    ASS
]:
    if not os.path.exists(arquivo):
        sys.exit(
            f"ERRO: arquivo não encontrado:\n{arquivo}"
        )

os.makedirs(
    MUSIC_DIR,
    exist_ok=True
)

os.makedirs(
    SFX_DIR,
    exist_ok=True
)


# =========================================
# DURAÇÃO
# =========================================

def duracao_arquivo(arquivo):

    return float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                arquivo
            ],
            text=True
        ).strip()
    )


duracao = duracao_arquivo(AUDIO)


# =========================================
# LEGENDA
# =========================================

ass = (
    os.path.abspath(ASS)
    .replace("\\", "\\\\")
    .replace(":", "\\:")
    .replace("'", "\\'")
)


# =========================================
# MÚSICAS
# =========================================

musicas = []

for ext in (
    "*.mp3",
    "*.wav",
    "*.m4a",
    "*.aac",
    "*.ogg"
):
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
    and bool(musicas)
)

musica = (
    random.choice(musicas)
    if usar_musica_agora
    else None
)


# =========================================
# EFEITOS SONOROS
# =========================================

efeitos = []

for ext in (
    "*.mp3",
    "*.wav",
    "*.m4a",
    "*.aac",
    "*.ogg"
):
    efeitos.extend(
        glob.glob(
            os.path.join(
                SFX_DIR,
                ext
            )
        )
    )

usar_sfx_agora = (
    USAR_SFX
    and bool(efeitos)
)

sfx = (
    random.choice(efeitos)
    if usar_sfx_agora
    else None
)


print()
print("================================")
print("SHORTAUTO PRO V6")
print("================================")
print()

print(
    f"Duração: {duracao:.2f}s"
)

print(
    f"Música: "
    f"{'ON' if usar_musica_agora else 'OFF'}"
)

if musica:
    print(
        f"Faixa: {os.path.basename(musica)}"
    )

print(
    f"SFX hook: "
    f"{'ON' if usar_sfx_agora else 'OFF'}"
)

if sfx:
    print(
        f"Efeito: {os.path.basename(sfx)}"
    )

print()


# =========================================
# HOOK VISUAL
# =========================================
#
# 0 - 0.18s  zoom rápido
# 0.18 - 0.38 estabiliza
# depois segue normal
#
# O efeito é propositalmente curto.
# =========================================

VIDEO_FILTER = (
    "[0:v]"
    "scale=1080:1920:"
    "force_original_aspect_ratio=increase,"
    "crop=1080:1920,"
    
    # pequeno punch visual inicial
    "scale="
    "'if(lt(t,0.18),"
    "1080+80*(1-t/0.18),"
    "1080)':"
    "'if(lt(t,0.18),"
    "1920+142*(1-t/0.18),"
    "1920)':"
    "eval=frame,"
    
    "crop=1080:1920,"
    
    # contraste cinematográfico leve
    "eq="
    "contrast=1.04:"
    "saturation=0.96:"
    "brightness=-0.008,"
    
    f"ass='{ass}'"
    "[v]"
)


# =========================================
# INPUTS
# =========================================

cmd = [
    "ffmpeg",
    "-y",

    "-i",
    VIDEO_BASE,

    "-i",
    AUDIO
]

musica_input = None
sfx_input = None
proximo_input = 2


if usar_musica_agora:

    musica_input = proximo_input

    cmd.extend(
        [
            "-stream_loop",
            "-1",
            "-i",
            musica
        ]
    )

    proximo_input += 1


if usar_sfx_agora:

    sfx_input = proximo_input

    cmd.extend(
        [
            "-i",
            sfx
        ]
    )

    proximo_input += 1


# =========================================
# ÁUDIO
# =========================================

audio_filters = []

# voz principal
audio_filters.append(
    "[1:a]"
    "volume=1.0,"
    "highpass=f=70,"
    "alimiter=limit=0.95"
    "[voz]"
)

mix_inputs = [
    "[voz]"
]


# música
if musica_input is not None:

    fade_out = max(
        0,
        duracao - 1.5
    )

    audio_filters.append(
        f"[{musica_input}:a]"
        f"volume={MUSICA_VOLUME},"
        "afade=t=in:st=0:d=1.0,"
        f"afade=t=out:"
        f"st={fade_out}:d=1.5"
        "[music]"
    )

    mix_inputs.append(
        "[music]"
    )


# SFX somente no começo
if sfx_input is not None:

    audio_filters.append(
        f"[{sfx_input}:a]"
        "atrim=start=0:end=1.2,"
        "asetpts=PTS-STARTPTS,"
        f"volume={SFX_VOLUME},"
        "afade=t=out:st=0.65:d=0.45"
        "[sfx]"
    )

    mix_inputs.append(
        "[sfx]"
    )


audio_filters.append(
    "".join(mix_inputs)
    +
    f"amix="
    f"inputs={len(mix_inputs)}:"
    "duration=first:"
    "dropout_transition=2,"
    "alimiter=limit=0.95"
    "[a]"
)


FILTER_COMPLEX = (
    VIDEO_FILTER
    + ";"
    + ";".join(
        audio_filters
    )
)


# =========================================
# RENDER
# =========================================

cmd.extend(
    [
        "-filter_complex",
        FILTER_COMPLEX,

        "-map",
        "[v]",

        "-map",
        "[a]",

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
            "20"
        ),

        "-profile:v",
        "high",

        "-level",
        "4.1",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-ar",
        "48000",

        "-t",
        str(duracao),

        "-movflags",
        "+faststart",

        SAIDA
    ]
)


print(
    "Renderizando V6..."
)

try:

    subprocess.run(
        cmd,
        check=True
    )

except subprocess.CalledProcessError:

    sys.exit(
        "\nERRO: FFmpeg não conseguiu "
        "renderizar o V6."
    )


print()
print("================================")
print("SHORT V6 CRIADO!")
print("================================")
print()
print(SAIDA)
print()
