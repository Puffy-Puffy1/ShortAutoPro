#!/usr/bin/env python3

import os
import sys
import glob
import subprocess
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

MEDIA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

AUDIO = os.path.join(
    BASE,
    "audios",
    f"short_{SHORT_ID}.mp3"
)

TEMP = os.path.join(
    BASE,
    "temp",
    SHORT_ID
)

VIDEO_DIR = os.path.join(
    BASE,
    "videos"
)

os.makedirs(TEMP, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

VIDEO_SEM_AUDIO = os.path.join(
    TEMP,
    "video_sem_audio.mp4"
)

if not os.path.exists(AUDIO):
    sys.exit("ERRO: áudio não encontrado.")

arquivos = []

for caminho in glob.glob(
    os.path.join(
        MEDIA_DIR,
        "scene_*"
    )
):

    ext = os.path.splitext(
        caminho
    )[1].lower()

    if ext in [
        ".jpg",
        ".jpeg",
        ".png",
        ".mp4"
    ]:
        arquivos.append(caminho)

arquivos = sorted(arquivos)

if not arquivos:
    sys.exit(
        "ERRO: nenhuma mídia encontrada."
    )

try:

    duracao_total = float(
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

except Exception as e:

    sys.exit(
        f"ERRO lendo duração do áudio: {e}"
    )


FPS = 30

# duração real que cada cena ocuparia
duracao_cena = (
    duracao_total
    / len(arquivos)
)

# crossfade entre cenas
TRANSICAO = 0.25

# cada cena precisa ficar um pouco maior,
# porque o crossfade sobrepõe trechos
duracao_render = (
    duracao_cena
    + TRANSICAO
)

frames_foto = max(
    1,
    round(
        duracao_render
        * FPS
    )
)


print()
print("================================")
print("RENDERIZANDO CENAS...")
print("================================")
print()

print(
    f"Mídias: {len(arquivos)}"
)

print(
    f"Duração final: "
    f"{duracao_total:.2f}s"
)

print(
    f"Tempo por cena: "
    f"{duracao_cena:.2f}s"
)

print(
    f"Transição: "
    f"{TRANSICAO:.2f}s"
)

print()


cenas = []


for numero, arquivo in enumerate(
    arquivos
):

    ext = os.path.splitext(
        arquivo
    )[1].lower()

    cena = os.path.join(
        TEMP,
        f"fade_cena_{numero:02d}.mp4"
    )

    print(
        f"Cena "
        f"{numero + 1}/"
        f"{len(arquivos)} "
        f"{ext}"
    )


    # ===========================
    # FOTO
    # ===========================

    if ext in [
        ".jpg",
        ".jpeg",
        ".png"
    ]:

        if numero % 2 == 0:

            movimento = (
                "zoompan="
                "z='min(zoom+0.0008,1.08)':"
                "x='iw/2-(iw/zoom/2)':"
                "y='ih/2-(ih/zoom/2)':"
            )

        else:

            movimento = (
                "zoompan="
                "z='if(eq(on,1),1.08,"
                "max(zoom-0.0008,1.0))':"
                "x='iw/2-(iw/zoom/2)':"
                "y='ih/2-(ih/zoom/2)':"
            )


        filtro = (
            "scale=1200:2133:"
            "force_original_aspect_ratio=increase,"
            "crop=1200:2133,"
            + movimento
            + f"d={frames_foto}:"
            "s=1080x1920:"
            f"fps={FPS},"
            "setsar=1,"
            "format=yuv420p"
        )


        comando = [
            "ffmpeg",
            "-y",

            "-loop",
            "1",

            "-i",
            arquivo,

            "-vf",
            filtro,

            "-frames:v",
            str(frames_foto),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "24",

            "-pix_fmt",
            "yuv420p",

            cena
        ]


    # ===========================
    # VÍDEO
    # ===========================

    else:

        filtro = (
            "scale=1080:1920:"
            "force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            f"fps={FPS},"
            "setsar=1,"
            "format=yuv420p"
        )


        comando = [
            "ffmpeg",
            "-y",

            "-stream_loop",
            "-1",

            "-i",
            arquivo,

            "-t",
            str(duracao_render),

            "-vf",
            filtro,

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "24",

            "-pix_fmt",
            "yuv420p",

            cena
        ]


    try:

        subprocess.run(
            comando,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    except subprocess.CalledProcessError:

        sys.exit(
            f"ERRO renderizando cena "
            f"{numero + 1}."
        )


    cenas.append(cena)


# ===============================
# CROSSFADE
# ===============================

print()
print("Aplicando transições...")
print()

if len(cenas) == 1:

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            cenas[0],
            "-t",
            str(duracao_total),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            VIDEO_SEM_AUDIO
        ],
        check=True
    )

else:

    comando = [
        "ffmpeg",
        "-y"
    ]

    for cena in cenas:

        comando.extend(
            [
                "-i",
                cena
            ]
        )


    filtros = []


    # primeira transição
    offset = (
        duracao_render
        - TRANSICAO
    )

    filtros.append(
        f"[0:v][1:v]"
        f"xfade="
        f"transition=fade:"
        f"duration={TRANSICAO}:"
        f"offset={offset}"
        f"[v1]"
    )


    # restantes
    for i in range(
        2,
        len(cenas)
    ):

        offset = (
            i
            * (
                duracao_render
                - TRANSICAO
            )
        )

        filtros.append(
            f"[v{i-1}]"
            f"[{i}:v]"
            f"xfade="
            f"transition=fade:"
            f"duration={TRANSICAO}:"
            f"offset={offset}"
            f"[v{i}]"
        )


    saida_final = (
        f"[v{len(cenas)-1}]"
    )


    filtro_complexo = (
        ";".join(filtros)
    )


    comando.extend(
        [
            "-filter_complex",
            filtro_complexo,

            "-map",
            saida_final,

            "-t",
            str(duracao_total),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "veryfast",

            "-crf",
            "23",

            "-pix_fmt",
            "yuv420p",

            "-movflags",
            "+faststart",

            VIDEO_SEM_AUDIO
        ]
    )


    try:

        subprocess.run(
            comando,
            check=True
        )

    except subprocess.CalledProcessError:

        sys.exit(
            "ERRO aplicando crossfade."
        )


if not os.path.exists(
    VIDEO_SEM_AUDIO
):

    sys.exit(
        "ERRO: vídeo sem áudio não foi criado."
    )


try:

    dur_final = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                VIDEO_SEM_AUDIO
            ],
            text=True
        ).strip()
    )

except Exception:

    dur_final = 0


print()
print("================================")
print("CENAS COM TRANSICAO PRONTAS!")
print("================================")
print()

print(
    f"Duração: "
    f"{dur_final:.2f}s"
)

print(
    f"Arquivo:\n"
    f"{VIDEO_SEM_AUDIO}"
)

print()
