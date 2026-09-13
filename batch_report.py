#!/usr/bin/env python3

import os
import sys
import json
import glob
import math
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


def dict_seguro(valor):
    return valor if isinstance(valor, dict) else {}


def numero_seguro(valor):
    if not isinstance(valor, (int, float)):
        return None

    valor = float(valor)

    if not math.isfinite(valor):
        return None

    return valor


# =========================================
# LER MANIFESTS
# =========================================

# final_quality.py também grava JSON em manifests/, com sufixo
# _quality.json. Esses arquivos não são manifests de produção e
# não podem entrar no cálculo do lote.
todos_arquivos = glob.glob(
    os.path.join(
        MANIFEST_DIR,
        "*.json"
    )
)

arquivos = [
    path
    for path in todos_arquivos
    if not os.path.basename(path).endswith(
        "_quality.json"
    )
]

arquivos = sorted(
    arquivos,
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

    if not isinstance(
        dados,
        dict
    ):
        continue

    publish = dict_seguro(
        dados.get(
            "publish",
            {}
        )
    )

    video = dict_seguro(
        dados.get(
            "video",
            {}
        )
    )

    quality = dict_seguro(
        dados.get(
            "quality",
            {}
        )
    )

    duracao = numero_seguro(
        video.get(
            "duration_seconds"
        )
    )

    producoes.append(
        {
            "short_id": str(
                dados.get(
                    "short_id",
                    ""
                )
            ),

            "status": str(
                dados.get(
                    "status",
                    ""
                )
            ),

            "topic": str(
                dados.get(
                    "topic",
                    ""
                )
            ),

            "hook": str(
                dados.get(
                    "hook",
                    ""
                )
            ),

            "title": str(
                publish.get(
                    "chosen_title",
                    ""
                )
            ),

            "duration": duracao,

            "video": str(
                video.get(
                    "path",
                    ""
                )
            ),

            "resolution_ok": bool(
                quality.get(
                    "resolution_ok",
                    False
                )
            ),

            "fps_ok": bool(
                quality.get(
                    "fps_ok",
                    False
                )
            ),

            "audio_ok": bool(
                quality.get(
                    "audio_exists",
                    False
                )
            ),

            "scenes": quality.get(
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
    "created_at": datetime.now().isoformat(),
    "total": total,
    "quality_pass": passes,
    "failures": falhas,
    "average_duration": round(
        duracao_media,
        2
    ),
    "productions": producoes
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
print("BATCH REPORT - STABLE 2.2.1")
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
    f"Duração média: {duracao_media:.2f}s"
)

print()


for numero, p in enumerate(
    producoes,
    start=1
):

    print(
        f"{numero}. {p['topic']}"
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
