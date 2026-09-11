#!/usr/bin/env python3

import os
import sys
import json
import glob
from datetime import datetime

BASE = os.path.expanduser("~/ShortAutoPro")

MANIFEST_DIR = os.path.join(
    BASE,
    "manifests"
)

REPORT_DIR = os.path.join(
    BASE,
    "reports"
)

os.makedirs(
    REPORT_DIR,
    exist_ok=True
)

try:
    QTD = int(
        sys.argv[1]
        if len(sys.argv) > 1
        else os.getenv("SHORT_LOTE", "3")
    )
except ValueError:
    QTD = 3

QTD = max(
    1,
    min(QTD, 10)
)


# =========================================
# LER MANIFESTS
# =========================================

arquivos = sorted(
    glob.glob(
        os.path.join(
            MANIFEST_DIR,
            "*.json"
        )
    ),
    key=os.path.getmtime,
    reverse=True
)[:QTD]


if not arquivos:

    sys.exit(
        "ERRO: nenhum manifest encontrado."
    )


producoes = []


for arquivo in reversed(arquivos):

    try:

        with open(
            arquivo,
            "r",
            encoding="utf-8"
        ) as f:

            dados = json.load(f)

    except Exception:
        continue


    publish = dados.get(
        "publish",
        {}
    )

    video = dados.get(
        "video",
        {}
    )

    quality = dados.get(
        "quality",
        {}
    )


    producoes.append(
        {
            "short_id":
                dados.get(
                    "short_id",
                    ""
                ),

            "status":
                dados.get(
                    "status",
                    ""
                ),

            "topic":
                dados.get(
                    "topic",
                    ""
                ),

            "hook":
                dados.get(
                    "hook",
                    ""
                ),

            "title":
                publish.get(
                    "chosen_title",
                    ""
                ),

            "duration":
                video.get(
                    "duration_seconds"
                ),

            "video":
                video.get(
                    "path",
                    ""
                ),

            "resolution_ok":
                quality.get(
                    "resolution_ok",
                    False
                ),

            "fps_ok":
                quality.get(
                    "fps_ok",
                    False
                ),

            "audio_ok":
                quality.get(
                    "audio_exists",
                    False
                ),

            "scenes":
                quality.get(
                    "physical_scene_count",
                    0
                )
        }
    )


if not producoes:

    sys.exit(
        "ERRO: nenhum manifest válido."
    )


# =========================================
# RESUMO
# =========================================

total = len(
    producoes
)

passes = sum(
    1
    for p in producoes
    if p["status"] == "QUALITY_PASS"
)

falhas = (
    total
    - passes
)


duracoes = [
    p["duration"]
    for p in producoes
    if isinstance(
        p["duration"],
        (int, float)
    )
]


duracao_media = (
    sum(duracoes)
    / len(duracoes)
    if duracoes
    else 0
)


timestamp = datetime.now().strftime(
    "%Y-%m-%d_%H%M%S"
)

JSON_PATH = os.path.join(
    REPORT_DIR,
    f"batch_report_{timestamp}.json"
)

TXT_PATH = os.path.join(
    REPORT_DIR,
    f"batch_report_{timestamp}.txt"
)


relatorio = {
    "created_at":
        datetime.now().isoformat(),

    "total":
        total,

    "quality_pass":
        passes,

    "failures":
        falhas,

    "average_duration":
        round(
            duracao_media,
            2
        ),

    "productions":
        producoes
}


with open(
    JSON_PATH,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        relatorio,
        f,
        ensure_ascii=False,
        indent=2
    )


# =========================================
# TXT
# =========================================

linhas = []

linhas.append(
    "SHORTAUTO PRO - BATCH REPORT"
)

linhas.append(
    "=" * 32
)

linhas.append("")

linhas.append(
    f"Produções analisadas: {total}"
)

linhas.append(
    f"Quality Pass: {passes}"
)

linhas.append(
    f"Falhas/incompletos: {falhas}"
)

linhas.append(
    f"Duração média: {duracao_media:.2f}s"
)

linhas.append("")


for numero, p in enumerate(
    producoes,
    start=1
):

    linhas.append(
        f"{numero}. {p['topic']}"
    )

    linhas.append(
        f"   ID: {p['short_id']}"
    )

    linhas.append(
        f"   Status: {p['status']}"
    )

    linhas.append(
        f"   Título: {p['title']}"
    )

    if isinstance(
        p["duration"],
        (int, float)
    ):

        linhas.append(
            f"   Duração: {p['duration']:.2f}s"
        )

    else:

        linhas.append(
            "   Duração: ?"
        )

    linhas.append(
        f"   Cenas: {p['scenes']}/12"
    )

    linhas.append(
        f"   Vídeo: {p['video']}"
    )

    linhas.append("")


with open(
    TXT_PATH,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(linhas)
    )


# =========================================
# TERMINAL
# =========================================

print()
print("================================")
print("BATCH REPORT - STABLE 2.2")
print("================================")
print()

print(
    f"Produções: {total}"
)

print(
    f"Quality Pass: {passes}"
)

print(
    f"Falhas: {falhas}"
)

print(
    f"Duração média: "
    f"{duracao_media:.2f}s"
)

print()


for numero, p in enumerate(
    producoes,
    start=1
):

    print(
        f"{numero}. "
        f"{p['topic']}"
    )

    print(
        f"   {p['status']} | "
        f"{p['scenes']}/12 cenas"
    )

    if p["title"]:

        print(
            f"   {p['title']}"
        )

    print()


print(
    f"TXT:\n{TXT_PATH}"
)

print()

print(
    f"JSON:\n{JSON_PATH}"
)

print()

print(
    "BATCH REPORT: OK"
)

print()
