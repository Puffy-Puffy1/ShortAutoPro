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

ASS_ORIGINAL = os.path.join(
    BASE,
    "videos",
    f"short_{SHORT_ID}.ass"
)

TEMP = os.path.join(
    BASE,
    "temp",
    SHORT_ID
)

ASS_RETENTION = os.path.join(
    TEMP,
    "legenda_retention.ass"
)

MUSIC_DIR = os.path.join(
    BASE,
    "musicas"
)

SFX_DIR = os.path.join(
    BASE,
    "sfx"
)

SFX_GERADO = os.path.join(
    TEMP,
    "hook_impact.wav"
)

SAIDA = os.path.join(
    BASE,
    "videos",
    f"short_v6_{SHORT_ID}.mp4"
)

os.makedirs(TEMP, exist_ok=True)
os.makedirs(MUSIC_DIR, exist_ok=True)
os.makedirs(SFX_DIR, exist_ok=True)


# =========================================
# CONFIG
# =========================================

USAR_MUSICA = (
    os.getenv(
        "SHORT_USAR_MUSICA",
        "1"
    ) == "1"
)

USAR_SFX = (
    os.getenv(
        "SHORT_USAR_SFX",
        "1"
    ) == "1"
)

USAR_POP = (
    os.getenv(
        "SHORT_USAR_POP",
        "1"
    ) == "1"
)

USAR_RETENTION = (
    os.getenv(
        "SHORT_RETENTION_ENGINE",
        "1"
    ) == "1"
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
            "0.18"
        )
    )
except ValueError:
    SFX_VOLUME = 0.18


try:
    POP_ESCALA = int(
        os.getenv(
            "SHORT_POP_ESCALA",
            "110"
        )
    )
except ValueError:
    POP_ESCALA = 110


try:
    HOOK_DURACAO = float(
        os.getenv(
            "SHORT_HOOK_DURACAO",
            "3.0"
        )
    )
except ValueError:
    HOOK_DURACAO = 3.0


MUSICA_VOLUME = max(
    0.01,
    min(MUSICA_VOLUME, 0.25)
)

SFX_VOLUME = max(
    0.01,
    min(SFX_VOLUME, 0.50)
)

POP_ESCALA = max(
    102,
    min(POP_ESCALA, 120)
)

HOOK_DURACAO = max(
    1.5,
    min(HOOK_DURACAO, 4.0)
)


# =========================================
# VERIFICAÇÕES
# =========================================

for arquivo in [
    VIDEO_BASE,
    AUDIO,
    ASS_ORIGINAL
]:

    if not os.path.exists(arquivo):

        sys.exit(
            f"ERRO: arquivo não encontrado:\n"
            f"{arquivo}"
        )


# =========================================
# FUNÇÕES
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


def escapar_ass(path):

    return (
        os.path.abspath(path)
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
    )


duracao = duracao_arquivo(
    AUDIO
)


# =========================================
# LEGENDA RETENTION
# =========================================

with open(
    ASS_ORIGINAL,
    "r",
    encoding="utf-8"
) as f:

    ass_texto = f.read()


if USAR_POP:

    tag_amarela = (
        r"{\c&H00FFFF&\b1}"
    )

    tag_pop = (
        r"{\c&H00FFFF&\b1"
        rf"\fscx{POP_ESCALA}"
        rf"\fscy{POP_ESCALA}"
        r"\t(0,120,\fscx100\fscy100)}"
    )

    tag_normal = (
        r"{\c&HFFFFFF&\b1}"
    )

    tag_normal_reset = (
        r"{\c&HFFFFFF&\b1"
        r"\fscx100\fscy100}"
    )

    ass_texto = ass_texto.replace(
        tag_amarela,
        tag_pop
    )

    ass_texto = ass_texto.replace(
        tag_normal,
        tag_normal_reset
    )


# deixa a primeira legenda um pouco mais forte
if USAR_RETENTION:

    linhas = ass_texto.splitlines()

    primeira_dialogue = True

    novas = []

    for linha in linhas:

        if (
            primeira_dialogue
            and linha.startswith(
                "Dialogue:"
            )
        ):

            partes = linha.split(
                ",",
                9
            )

            if len(partes) == 10:

                texto = partes[9]

                texto = (
                    r"{\fscx112\fscy112"
                    r"\bord3"
                    r"\shad2}"
                    + texto
                    + r"{\fscx100\fscy100}"
                )

                partes[9] = texto

                linha = ",".join(
                    partes
                )

                primeira_dialogue = False

        novas.append(
            linha
        )

    ass_texto = "\n".join(
        novas
    )


with open(
    ASS_RETENTION,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        ass_texto
    )


ASS_USADO = ASS_RETENTION

ass = escapar_ass(
    ASS_USADO
)


# =========================================
# MÚSICA
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
# SFX
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


sfx = None
sfx_tipo = "OFF"


if USAR_SFX:

    if efeitos:

        sfx = random.choice(
            efeitos
        )

        sfx_tipo = "ARQUIVO"

    else:

        try:

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",

                    "-f",
                    "lavfi",

                    "-i",
                    "sine=frequency=70:"
                    "sample_rate=48000:"
                    "duration=0.8",

                    "-af",
                    "volume=0.75,"
                    "afade=t=in:st=0:d=0.01,"
                    "afade=t=out:st=0.20:d=0.55",

                    "-c:a",
                    "pcm_s16le",

                    SFX_GERADO
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            if os.path.exists(
                SFX_GERADO
            ):

                sfx = SFX_GERADO
                sfx_tipo = "GERADO"

        except Exception:

            sfx = None


usar_sfx_agora = (
    USAR_SFX
    and sfx is not None
)


# =========================================
# INFO
# =========================================

print()
print("================================")
print("RETENTION ENGINE - STABLE 2.3.5")
print("================================")
print()

print(
    f"Duração: {duracao:.2f}s"
)

print(
    f"Retention Engine: "
    f"{'ON' if USAR_RETENTION else 'OFF'}"
)

print(
    f"Hook visual: "
    f"{HOOK_DURACAO:.1f}s"
)

print(
    f"Legenda POP: "
    f"{'ON' if USAR_POP else 'OFF'}"
)

print(
    f"Música: "
    f"{'ON' if usar_musica_agora else 'OFF'}"
)

print(
    f"SFX: "
    f"{'ON' if usar_sfx_agora else 'OFF'}"
)

print()


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


proximo_input = 2
musica_input = None
sfx_input = None


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
# VÍDEO - RETENTION HOOK
# =========================================

if USAR_RETENTION:

    # 0.00-0.20s:
    # punch forte

    # 0.20-0.75s:
    # estabiliza

    # 0.75-3s:
    # micro zoom contínuo

    zoom_expr_w = (
        "'if(lt(t,0.20),"
        "1080+105*(1-t/0.20),"
        "if(lt(t,3.0),"
        "1080+20*(t/3.0),"
        "1080))'"
    )

    zoom_expr_h = (
        "'if(lt(t,0.20),"
        "1920+187*(1-t/0.20),"
        "if(lt(t,3.0),"
        "1920+36*(t/3.0),"
        "1920))'"
    )

else:

    zoom_expr_w = "1080"
    zoom_expr_h = "1920"


VIDEO_FILTER = (
    "[0:v]"
    "scale=1080:1920:"
    "force_original_aspect_ratio=increase,"
    "crop=1080:1920,"

    "scale="
    f"{zoom_expr_w}:"
    f"{zoom_expr_h}:"
    "eval=frame,"

    "crop=1080:1920,"

    "eq="
    "contrast=1.045:"
    "saturation=0.97:"
    "brightness=-0.006,"

    f"ass='{ass}'"

    "[v]"
)


# =========================================
# BROADCAST AUDIO DIRECTOR 3.9
# =========================================

audio_filters = []


# -----------------------------------------
# VOZ
# -----------------------------------------
#
# High-pass remove graves inúteis.
# Compressor reduz diferenças entre
# palavras fortes/fracas.
# Limiter protege contra picos.

if musica_input is not None:

    # Precisamos de duas cópias:
    # uma vai para o mix;
    # outra controla o ducking da música.

    audio_filters.append(
        "[1:a]"
        "highpass=f=70,"
        "acompressor="
        "threshold=0.18:"
        "ratio=2.5:"
        "attack=20:"
        "release=180:"
        "makeup=1.15,"
        "alimiter=limit=0.95,"
        "asplit=2"
        "[voz][voz_sidechain]"
    )

else:

    audio_filters.append(
        "[1:a]"
        "highpass=f=70,"
        "acompressor="
        "threshold=0.18:"
        "ratio=2.5:"
        "attack=20:"
        "release=180:"
        "makeup=1.15,"
        "alimiter=limit=0.95"
        "[voz]"
    )


mix_inputs = [
    "[voz]"
]


# -----------------------------------------
# MÚSICA + DUCKING
# -----------------------------------------

if musica_input is not None:

    fade_out_inicio = max(
        0,
        duracao - 1.5
    )


    # Primeiro prepara a música.
    audio_filters.append(
        f"[{musica_input}:a]"
        f"volume={MUSICA_VOLUME},"
        "highpass=f=35,"
        "lowpass=f=15500,"
        "afade="
        "t=in:"
        "st=0:"
        "d=1.0,"
        "afade="
        "t=out:"
        f"st={fade_out_inicio}:"
        "d=1.5"
        "[musica_pre]"
    )


    # A voz funciona como sidechain.
    # Quando a narração sobe, a música
    # é automaticamente reduzida.
    audio_filters.append(
        "[musica_pre]"
        "[voz_sidechain]"
        "sidechaincompress="
        "threshold=0.035:"
        "ratio=6:"
        "attack=20:"
        "release=300:"
        "makeup=1"
        "[musica]"
    )


    mix_inputs.append(
        "[musica]"
    )


# -----------------------------------------
# SFX
# -----------------------------------------

if sfx_input is not None:

    audio_filters.append(
        f"[{sfx_input}:a]"
        "atrim="
        "start=0:"
        "end=1.0,"
        "asetpts=PTS-STARTPTS,"
        f"volume={SFX_VOLUME},"
        "afade="
        "t=out:"
        "st=0.30:"
        "d=0.50,"
        "alimiter=limit=0.90"
        "[sfx]"
    )


    mix_inputs.append(
        "[sfx]"
    )


# -----------------------------------------
# MIX
# -----------------------------------------

audio_filters.append(
    "".join(
        mix_inputs
    )
    +
    f"amix="
    f"inputs={len(mix_inputs)}:"
    "duration=first:"
    "dropout_transition=2,"
    "loudnorm="
    "I=-16:"
    "LRA=7:"
    "TP=-1.5,"
    "alimiter=limit=0.95"
    "[a]"
)


print()
print("================================")
print("BROADCAST AUDIO DIRECTOR 3.9")
print("================================")
print()

print(
    "Voz: compressor + limiter"
)

print(
    "Música: "
    + (
        "ducking automático"
        if musica_input is not None
        else "OFF"
    )
)

print(
    "SFX: "
    + (
        "mix controlado"
        if sfx_input is not None
        else "OFF"
    )
)

print(
    "Loudness final: -16 LUFS"
)

print(
    "True peak alvo: -1.5 dB"
)

print()


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
        str(
            duracao
        ),

        "-movflags",
        "+faststart",

        SAIDA
    ]
)


print(
    "Renderizando Stable 1.3..."
)

try:

    subprocess.run(
        cmd,
        check=True
    )

except subprocess.CalledProcessError:

    sys.exit(
        "ERRO: FFmpeg falhou "
        "no Retention Engine."
    )


if not os.path.exists(
    SAIDA
):

    sys.exit(
        "ERRO: vídeo final não foi criado."
    )


print()
print("================================")
print("RETENTION ENGINE FINALIZADO!")
print("================================")
print()

print(
    SAIDA
)

print()
