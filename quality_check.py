#!/usr/bin/env python3

import os
import sys
import glob
import json
import re
import subprocess
from datetime import date

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

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

QTD_CENAS = max(
    6,
    min(QTD_CENAS, 20)
)

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
        dados = json.loads(saida)
        return dados if isinstance(dados, dict) else {}

    except Exception as e:
        erros.append(
            f"ffprobe falhou: {e}"
        )
        return {}


if not os.path.isfile(VIDEO):
    erros.append(
        "Vídeo final não existe."
    )
else:
    tamanho = os.path.getsize(VIDEO)
    if tamanho < 500_000:
        erros.append(
            "Arquivo final pequeno demais."
        )

info = ffprobe_json(VIDEO)
streams = info.get("streams", [])
formato = info.get("format", {})

if not isinstance(streams, list):
    streams = []
if not isinstance(formato, dict):
    formato = {}

video_streams = [
    s for s in streams
    if isinstance(s, dict)
    and s.get("codec_type") == "video"
]

audio_streams = [
    s for s in streams
    if isinstance(s, dict)
    and s.get("codec_type") == "audio"
]

width = 0
height = 0
fps = 0.0

if not video_streams:
    erros.append(
        "Nenhuma faixa de vídeo encontrada."
    )
else:
    v = video_streams[0]
    width = int(v.get("width", 0) or 0)
    height = int(v.get("height", 0) or 0)
    codec = v.get("codec_name", "?")
    fps_raw = str(v.get("avg_frame_rate", "0/1"))

    try:
        num, den = fps_raw.split("/", 1)
        den_f = float(den)
        fps = float(num) / den_f if den_f else 0.0
    except Exception:
        fps = 0.0

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
    if not 29.0 <= fps <= 31.0:
        erros.append(
            f"FPS fora do esperado: {fps:.2f}"
        )

if not audio_streams:
    erros.append(
        "Nenhuma faixa de áudio encontrada."
    )
else:
    audio_codec = audio_streams[0].get(
        "codec_name",
        "?"
    )
    if audio_codec != "aac":
        avisos.append(
            f"Codec de áudio: {audio_codec}"
        )

try:
    duracao = float(
        formato.get("duration", 0)
        or 0
    )
except Exception:
    duracao = 0.0

if duracao < 15:
    erros.append(
        f"Vídeo curto demais: {duracao:.2f}s"
    )
if duracao > 60:
    avisos.append(
        f"Vídeo acima de 60s: {duracao:.2f}s"
    )

arquivos_cena = []

if os.path.isdir(MEDIA_DIR):
    arquivos_cena = [
        x
        for x in glob.glob(
            os.path.join(
                MEDIA_DIR,
                "scene_*"
            )
        )
        if os.path.splitext(x)[1].lower()
        in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4"
        }
    ]

if len(arquivos_cena) != QTD_CENAS:
    erros.append(
        f"Cenas físicas: {len(arquivos_cena)}/{QTD_CENAS}"
    )

numeros = []
for path in arquivos_cena:
    m = re.match(
        r"^scene_(\d+)",
        os.path.basename(path),
        flags=re.IGNORECASE
    )
    if m:
        numeros.append(int(m.group(1)))

esperadas = set(range(1, QTD_CENAS + 1))
encontradas = set(numeros)

faltando = sorted(esperadas - encontradas)
extras = sorted(encontradas - esperadas)

duplicadas = sorted({
    n
    for n in numeros
    if numeros.count(n) > 1
})

if faltando:
    erros.append(
        "Cenas ausentes: "
        + ", ".join(f"{n:02d}" for n in faltando)
    )
if extras:
    erros.append(
        "Cenas fora da faixa: "
        + ", ".join(f"{n:02d}" for n in extras)
    )
if duplicadas:
    erros.append(
        "Cenas duplicadas: "
        + ", ".join(f"{n:02d}" for n in duplicadas)
    )

if not os.path.exists(SCENE_MAP):
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

        mapa_cenas = mapa.get("scenes", [])
        if not isinstance(mapa_cenas, list):
            raise ValueError("campo scenes não é lista")

        if len(mapa_cenas) != QTD_CENAS:
            erros.append(
                f"Scene map: {len(mapa_cenas)}/{QTD_CENAS}"
            )

    except Exception as e:
        erros.append(
            f"scene_map inválido: {e}"
        )

if os.path.exists(SUPERVISOR):
    try:
        with open(
            SUPERVISOR,
            "r",
            encoding="utf-8"
        ) as f:
            supervisor = json.load(f)

        if not isinstance(supervisor, dict):
            raise ValueError("relatório não é objeto")

        if supervisor.get("status") == "BLOCK":
            erros.append(
                "Production Supervisor marcou BLOCK."
            )

    except Exception as e:
        erros.append(
            f"supervisor inválido: {e}"
        )
else:
    avisos.append(
        "Relatório do Production Supervisor não encontrado."
    )

print()
print("================================")
print("SHORTAUTO PRO - QUALITY GATE 5.1")
print("================================")
print()
print(f"Arquivo: {VIDEO}")
print(f"Duração: {duracao:.2f}s")

if video_streams:
    print(f"Resolução: {width}x{height}")
    print(f"FPS: {fps:.2f}")

print(
    f"Cenas físicas: {len(arquivos_cena)}/{QTD_CENAS}"
)
print()

if avisos:
    print("AVISOS:")
    for aviso in avisos:
        print(f"- {aviso}")
    print()

if erros:
    print("QUALITY FAIL")
    for erro in erros:
        print(f"- {erro}")
    print()
    sys.exit(1)

print("QUALITY PASS")
print()
