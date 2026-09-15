#!/usr/bin/env python3

import os
import sys
import glob
import re
import subprocess
from datetime import date


# =====================================================
# CONFIG
# =====================================================

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

ASS = os.path.join(
    BASE,
    "videos",
    f"short_{SHORT_ID}.ass"
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

VIDEO_SEM_AUDIO = os.path.join(
    TEMP,
    "video_sem_audio.mp4"
)

os.makedirs(TEMP, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

FPS = 30
TRANSICAO = 0.25

PRESET = os.getenv(
    "SHORT_PRESET_CENAS",
    "veryfast"
)

CRF_CENAS = os.getenv(
    "SHORT_CRF_CENAS",
    "23"
)


# =====================================================
# VERIFICAÇÕES
# =====================================================

if not os.path.exists(AUDIO):
    sys.exit(
        "ERRO: áudio não encontrado."
    )

if not os.path.isdir(MEDIA_DIR):
    sys.exit(
        "ERRO: pasta de mídia não encontrada."
    )


# =====================================================
# MÍDIAS
# =====================================================

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


# =====================================================
# DURAÇÃO DO ÁUDIO
# =====================================================

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


# =====================================================
# ASS -> SEGUNDOS
# =====================================================

def ass_para_segundos(valor):

    # formato ASS:
    # 0:00:03.25

    try:

        h, m, resto = valor.split(":")

        s, cent = resto.split(".")

        return (
            int(h) * 3600
            + int(m) * 60
            + int(s)
            + int(cent) / 100
        )

    except Exception:

        return None


# =====================================================
# EXTRAIR TEMPOS DAS PALAVRAS
# =====================================================

def extrair_eventos_ass():

    if not os.path.exists(ASS):
        return []

    eventos = []

    try:

        with open(
            ASS,
            "r",
            encoding="utf-8"
        ) as f:

            for linha in f:

                if not linha.startswith(
                    "Dialogue:"
                ):
                    continue

                partes = linha.split(
                    ",",
                    9
                )

                if len(partes) < 10:
                    continue

                inicio = ass_para_segundos(
                    partes[1].strip()
                )

                fim = ass_para_segundos(
                    partes[2].strip()
                )

                if (
                    inicio is None
                    or fim is None
                ):
                    continue

                if fim <= inicio:
                    continue

                eventos.append(
                    (
                        inicio,
                        fim
                    )
                )

    except Exception:

        return []

    eventos.sort(
        key=lambda x: x[0]
    )

    return eventos


# =====================================================
# CALCULAR DURAÇÃO DE CADA CENA
# =====================================================

def calcular_duracoes():

    quantidade = len(
        arquivos
    )

    eventos = extrair_eventos_ass()

    # ---------------------------------
    # FALLBACK ANTIGO
    # ---------------------------------

    if len(eventos) < quantidade:

        uniforme = (
            duracao_total
            / quantidade
        )

        return (
            [uniforme] * quantidade,
            "UNIFORME"
        )


    # ---------------------------------
    # SINCRONIZAÇÃO COM FALA
    # ---------------------------------

    total_eventos = len(
        eventos
    )

    limites = [
        0.0
    ]


    for cena in range(
        1,
        quantidade
    ):

        indice = round(
            cena
            * total_eventos
            / quantidade
        )

        indice = max(
            1,
            min(
                indice,
                total_eventos - 1
            )
        )

        tempo = eventos[
            indice
        ][0]

        limites.append(
            tempo
        )


    limites.append(
        duracao_total
    )


    # ---------------------------------
    # GARANTIR ORDEM
    # ---------------------------------

    for i in range(
        1,
        len(limites)
    ):

        if limites[i] <= limites[i - 1]:

            limites[i] = (
                limites[i - 1]
                + 0.20
            )


    # O último sempre termina
    # exatamente junto do áudio.

    limites[-1] = (
        duracao_total
    )


    duracoes = []

    for i in range(
        quantidade
    ):

        dur = (
            limites[i + 1]
            - limites[i]
        )

        duracoes.append(
            max(
                0.70,
                dur
            )
        )


    # Corrige pequena diferença criada
    # pelos mínimos.

    soma = sum(
        duracoes
    )

    if soma > 0:

        fator = (
            duracao_total
            / soma
        )

        duracoes = [
            d * fator
            for d in duracoes
        ]


    return (
        duracoes,
        "FALA REAL"
    )


duracoes_cena, modo_sync = (
    calcular_duracoes()
)


# =====================================================
# INFO
# =====================================================

print()
print("================================")
print("VIDEO V6.2 - SINCRONIZAÇÃO")
print("================================")
print()

print(
    f"Mídias: {len(arquivos)}"
)

print(
    f"Duração total: "
    f"{duracao_total:.2f}s"
)

print(
    f"Sincronização: "
    f"{modo_sync}"
)

print(
    f"Transição: "
    f"{TRANSICAO:.2f}s"
)

print()


for i, dur in enumerate(
    duracoes_cena,
    1
):

    print(
        f"Cena {i:02d}: "
        f"{dur:.2f}s"
    )


print()


# =====================================================
# RENDER DAS CENAS
# =====================================================

cenas = []


for numero, arquivo in enumerate(
    arquivos
):

    ext = os.path.splitext(
        arquivo
    )[1].lower()

    duracao_logica = (
        duracoes_cena[
            numero
        ]
    )

    # adiciona trecho usado
    # na sobreposição do crossfade

    duracao_render = (
        duracao_logica
        + TRANSICAO
    )

    frames_foto = max(
        1,
        round(
            duracao_render
            * FPS
        )
    )

    cena = os.path.join(
        TEMP,
        f"sync_cena_{numero:02d}.mp4"
    )


    print(
        f"Render "
        f"{numero + 1}/"
        f"{len(arquivos)} "
        f"({duracao_logica:.2f}s)"
    )


    # =================================================
    # FOTO
    # =================================================

    if ext in [
        ".jpg",
        ".jpeg",
        ".png"
    ]:

        # alterna zoom-in / zoom-out

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
            str(
                frames_foto
            ),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            PRESET,

            "-crf",
            CRF_CENAS,

            "-pix_fmt",
            "yuv420p",

            cena
        ]


    # =================================================
    # VÍDEO
    # =================================================

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
            str(
                duracao_render
            ),

            "-vf",
            filtro,

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            PRESET,

            "-crf",
            CRF_CENAS,

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


    cenas.append(
        cena
    )


# =====================================================
# CROSSFADE
# =====================================================

print()
print(
    "Aplicando transições sincronizadas..."
)
print()


if len(cenas) == 1:

    subprocess.run(
        [
            "ffmpeg",
            "-y",

            "-i",
            cenas[0],

            "-t",
            str(
                duracao_total
            ),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            PRESET,

            "-crf",
            CRF_CENAS,

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


    # Offset é a soma das durações
    # lógicas das cenas anteriores.

    acumulado = (
        duracoes_cena[0]
    )


    filtros.append(
        f"[0:v][1:v]"
        f"xfade="
        f"transition=fade:"
        f"duration={TRANSICAO}:"
        f"offset={acumulado:.4f}"
        f"[v1]"
    )


    for i in range(
        2,
        len(cenas)
    ):

        acumulado += (
            duracoes_cena[
                i - 1
            ]
        )

        filtros.append(
            f"[v{i-1}]"
            f"[{i}:v]"
            f"xfade="
            f"transition=fade:"
            f"duration={TRANSICAO}:"
            f"offset={acumulado:.4f}"
            f"[v{i}]"
        )


    saida_final = (
        f"[v{len(cenas)-1}]"
    )


    filtro_complexo = (
        ";".join(
            filtros
        )
    )


    comando.extend(
        [
            "-filter_complex",
            filtro_complexo,

            "-map",
            saida_final,

            "-t",
            str(
                duracao_total
            ),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            PRESET,

            "-crf",
            CRF_CENAS,

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
            "ERRO aplicando crossfade "
            "sincronizado."
        )


# =====================================================
# VERIFICAÇÃO FINAL
# =====================================================

if not os.path.exists(
    VIDEO_SEM_AUDIO
):

    sys.exit(
        "ERRO: vídeo sem áudio "
        "não foi criado."
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
print("VIDEO V6.2 PRONTO!")
print("================================")
print()

print(
    f"Sincronização: "
    f"{modo_sync}"
)

print(
    f"Duração: "
    f"{dur_final:.2f}s"
)

print(
    f"Arquivo:\n"
    f"{VIDEO_SEM_AUDIO}"
)

print()
