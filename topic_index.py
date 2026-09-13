#!/usr/bin/env python3

import os
import json
import glob
import math
from datetime import datetime

from topic_memory import encontrar_duplicata


BASE = os.path.expanduser("~/ShortAutoPro")

ROTEIROS = os.path.join(
    BASE,
    "roteiros"
)

HISTORICO = os.path.join(
    BASE,
    "historico_assuntos.json"
)

INDEX = os.path.join(
    BASE,
    "topic_index.json"
)


def carregar_historico():

    if not os.path.exists(HISTORICO):
        return []

    try:
        with open(
            HISTORICO,
            "r",
            encoding="utf-8"
        ) as f:
            dados = json.load(f)

    except Exception:
        return []

    if isinstance(dados, list):
        return dados

    return []


def score_seguro(valor):

    try:
        score = float(valor)
    except (TypeError, ValueError):
        return 0.0

    if not math.isfinite(score):
        return 0.0

    return score


historico = carregar_historico()

arquivos = glob.glob(
    os.path.join(
        ROTEIROS,
        "topic_verified_*.json"
    )
)

indice = {}

for arquivo in arquivos:

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

    candidatos = (
        dados.get("ranking")
        or dados.get("approved")
        or []
    )

    if not isinstance(
        candidatos,
        list
    ):
        continue

    for item in candidatos:

        if not isinstance(
            item,
            dict
        ):
            continue

        topic = str(
            item.get(
                "topic",
                ""
            )
        ).strip()

        if not topic:
            continue

        wiki_title = str(
            item.get(
                "wiki_title",
                ""
            )
        ).strip()

        score = score_seguro(
            item.get(
                "score",
                0
            )
        )

        chave = topic.lower()

        duplicata = encontrar_duplicata(
            topic,
            historico,
            limite=0.72
        )

        registro = {
            "topic": topic,
            "wiki_title": wiki_title,
            "score": score,
            "used": bool(
                duplicata["duplicate"]
            ),
            "source": os.path.basename(
                arquivo
            )
        }

        atual = indice.get(
            chave
        )

        if (
            atual is None
            or score > atual[
                "score"
            ]
        ):
            indice[chave] = registro


saida = list(
    indice.values()
)

saida.sort(
    key=lambda x: (
        x["used"],
        -x["score"]
    )
)


dados_saida = {
    "updated_at": datetime.now().isoformat(),
    "total": len(saida),
    "unused": sum(
        1
        for x in saida
        if not x["used"]
    ),
    "used": sum(
        1
        for x in saida
        if x["used"]
    ),
    "topics": saida
}


temporario = INDEX + ".tmp"

try:
    with open(
        temporario,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            dados_saida,
            f,
            ensure_ascii=False,
            indent=2
        )
        f.flush()
        os.fsync(
            f.fileno()
        )

    os.replace(
        temporario,
        INDEX
    )

finally:
    if os.path.exists(
        temporario
    ):
        try:
            os.remove(
                temporario
            )
        except OSError:
            pass


print()
print("================================")
print("TOPIC INDEX - STABLE 2.2.6")
print("================================")
print()

print(
    f"Total verificados: {dados_saida['total']}"
)
print(
    f"Não usados: {dados_saida['unused']}"
)
print(
    f"Já usados: {dados_saida['used']}"
)
print()
print(
    f"Índice:\n{INDEX}"
)
print()
print(
    "TOPIC INDEX: OK"
)
