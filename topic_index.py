#!/usr/bin/env python3

import os
import json
import glob
from datetime import datetime

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

        if isinstance(dados, list):
            return dados

    except Exception:
        pass

    return []


historico = carregar_historico()

usados = {
    str(
        item.get(
            "topic",
            ""
        )
    ).strip().lower()
    for item in historico
    if isinstance(item, dict)
}


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


        try:

            score = float(
                item.get(
                    "score",
                    0
                )
            )

        except Exception:

            score = 0.0


        chave = topic.lower()


        registro = {
            "topic":
                topic,

            "wiki_title":
                wiki_title,

            "score":
                score,

            "used":
                chave in usados,

            "source":
                os.path.basename(
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
    "updated_at":
        datetime.now().isoformat(),

    "total":
        len(saida),

    "unused":
        sum(
            1
            for x in saida
            if not x["used"]
        ),

    "used":
        sum(
            1
            for x in saida
            if x["used"]
        ),

    "topics":
        saida
}


with open(
    INDEX,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        dados_saida,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("================================")
print("TOPIC INDEX - STABLE 2.2.5")
print("================================")
print()

print(
    f"Total verificados: "
    f"{dados_saida['total']}"
)

print(
    f"Não usados: "
    f"{dados_saida['unused']}"
)

print(
    f"Já usados: "
    f"{dados_saida['used']}"
)

print()

print(
    f"Índice:\n{INDEX}"
)

print()

print(
    "TOPIC INDEX: OK"
)
