#!/usr/bin/env python3

import os
import sys
import glob
import json
import subprocess
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")


SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)


# =========================================
# SUPERVISOR QUALITY 5.0
# =========================================

SUPERVISOR = os.path.join(
    BASE,
    "roteiros",
    f"supervisor_{SHORT_ID}.json"
)

VIDEO_V6 = os.path.join(
    BASE,
    "videos",
    f"short_v6_{SHORT_ID}.mp4"
)

VIDEO_V5 = os.path.join(
    BASE,
    "videos",
    f"short_v5_{SHORT_ID}.mp4"
)

MEDIA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

try:
    QTD_CENAS = int(
        os.getenv(
            "SHORT_QTD_CENAS",
            "12"
        )
    )
except ValueError:
    QTD_CENAS = 12


# =========================================
# ENCONTRAR VÍDEO
# =========================================

if os.path.exists(VIDEO_V6):
    VIDEO = VIDEO_V6
elif os.path.exists(VIDEO_V5):
    VIDEO = VIDEO_V5
else:
    sys.exit(
        "QUALITY FAIL: vídeo final não encontrado."
    )


erros = []
avisos = []


def ffprobe_json(arquivo):

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        arquivo
    ]

    try:
        saida = subprocess.check_output(
            cmd,
            text=True
        )

        return json.loads(saida)

    except Exception as e:

        erros.append(
            f"ffprobe falhou: {e}"
        )

        return {}


# =========================================
# ARQUIVO
# =========================================

if not os.path.isfile(VIDEO):

    erros.append(
        "Vídeo final não existe."
    )

else:

    tamanho = os.path.getsize(
        VIDEO
    )

    if tamanho < 500_000:

        erros.append(
            "Arquivo final pequeno demais."
        )


# =========================================
# FFPROBE
# =========================================

info = ffprobe_json(
    VIDEO
)

streams = info.get(
    "streams",
    []
)

formato = info.get(
    "format",
    {}
)

video_streams = [
    s
    for s in streams
    if s.get("codec_type") == "video"
]

audio_streams = [
    s
    for s in streams
    if s.get("codec_type") == "audio"
]


# =========================================
# VIDEO STREAM
# =========================================

if not video_streams:

    erros.append(
        "Nenhuma faixa de vídeo encontrada."
    )

else:

    v = video_streams[0]

    width = int(
        v.get("width", 0)
        or 0
    )

    height = int(
        v.get("height", 0)
        or 0
    )

    codec = v.get(
        "codec_name",
        "?"
    )

    fps_raw = v.get(
        "avg_frame_rate",
        "0/1"
    )

    try:
        num, den = fps_raw.split("/")

        fps = (
            float(num)
            / float(den)
            if float(den) != 0
            else 0
        )

    except Exception:
        fps = 0


    if width != 1080:

        erros.append(
            f"Largura incorreta: {width}"
        )

    if height != 1920:

        erros.append(
            f"Altura incorreta: {height}"
        )

    if codec != "h264":

        avisos.append(
            f"Codec inesperado: {codec}"
        )

    if not (
        29.0 <= fps <= 31.0
    ):

        erros.append(
            f"FPS fora do esperado: {fps:.2f}"
        )


# =========================================
# AUDIO STREAM
# =========================================

if not audio_streams:

    erros.append(
        "Nenhuma faixa de áudio encontrada."
    )

else:

    a = audio_streams[0]

    audio_codec = a.get(
        "codec_name",
        "?"
    )

    if audio_codec != "aac":

        avisos.append(
            f"Codec de áudio: {audio_codec}"
        )


# =========================================
# DURAÇÃO
# =========================================

try:
    duracao = float(
        formato.get(
            "duration",
            0
        )
        or 0
    )
except Exception:
    duracao = 0


if duracao < 15:

    erros.append(
        f"Vídeo curto demais: {duracao:.2f}s"
    )

if duracao > 60:

    avisos.append(
        f"Vídeo acima de 60s: {duracao:.2f}s"
    )


# =========================================
# 12 CENAS FÍSICAS
# =========================================

arquivos_cena = []

if os.path.isdir(
    MEDIA_DIR
):

    for ext in (
        "*.jpg",
        "*.jpeg",
        "*.png",
        "*.mp4"
    ):

        arquivos_cena.extend(
            glob.glob(
                os.path.join(
                    MEDIA_DIR,
                    f"scene_*{ext[1:]}"
                )
            )
        )


# fallback mais simples
arquivos_cena = glob.glob(
    os.path.join(
        MEDIA_DIR,
        "scene_*"
    )
)

arquivos_cena = [
    x
    for x in arquivos_cena
    if os.path.splitext(
        x
    )[1].lower()
    in (
        ".jpg",
        ".jpeg",
        ".png",
        ".mp4"
    )
]


if len(arquivos_cena) != QTD_CENAS:

    erros.append(
        f"Cenas físicas: "
        f"{len(arquivos_cena)}/{QTD_CENAS}"
    )


# =========================================
# SCENE MAP
# =========================================

if not os.path.exists(
    SCENE_MAP
):

    erros.append(
        "scene_map não encontrado."
    )

else:

    try:

        with open(
            SCENE_MAP,
            "r",
            encoding="utf-8"
        ) as f:

            mapa = json.load(f)

        mapa_cenas = mapa.get(
            "scenes",
            []
        )

        if len(mapa_cenas) != QTD_CENAS:

            erros.append(
                f"Scene map: "
                f"{len(mapa_cenas)}/{QTD_CENAS}"
            )

    except Exception as e:

        erros.append(
            f"scene_map inválido: {e}"
        )


# =========================================
# RESULTADO
# =========================================

print()
print("================================")
print("SHORTAUTO PRO - QUALITY GATE")
print("================================")
print()

print(
    f"Arquivo: {VIDEO}"
)

print(
    f"Duração: {duracao:.2f}s"
)

if video_streams:

    print(
        f"Resolução: "
        f"{width}x{height}"
    )

    print(
        f"FPS: {fps:.2f}"
    )

print(
    f"Cenas físicas: "
    f"{len(arquivos_cena)}/{QTD_CENAS}"
)

print()


if avisos:

    print("AVISOS:")

    for aviso in avisos:

        print(
            f"- {aviso}"
        )

    print()


if erros:

    print("QUALITY FAIL")

    for erro in erros:

        print(
            f"- {erro}"
        )

    print()

    sys.exit(1)


print("QUALITY PASS")
print()
