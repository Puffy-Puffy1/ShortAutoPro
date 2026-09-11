#!/usr/bin/env python3

import os
import json
import re
from datetime import date


# =====================================================
# SHORTAUTO PRO
# EDITORIAL CONTINUITY GUARD 4.4
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)

OUTPUT = os.path.join(
    BASE,
    "roteiros",
    f"continuity_{SHORT_ID}.json"
)

BACKUP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_pre_continuity_{SHORT_ID}.json"
)


STOP = {
    "cinematic", "dramatic", "dark",
    "vintage", "historic", "historical",
    "view", "scene", "shot", "close",
    "medium", "wide", "old", "retro",
    "the", "a", "an", "of", "in",
    "on", "with", "and", "or", "to"
}


def tokens(texto):

    return {
        x
        for x in re.findall(
            r"[a-z0-9]+",
            str(texto).lower()
        )
        if (
            x not in STOP
            and len(x) >= 3
        )
    }


def similaridade(
    a,
    b
):

    ta = tokens(a)
    tb = tokens(b)

    if not ta or not tb:
        return 0.0

    return (
        len(
            ta.intersection(tb)
        )
        / len(
            ta.union(tb)
        )
    )


def limpar_lista(valor):

    if not isinstance(
        valor,
        list
    ):
        return []

    saida = []

    for x in valor:

        x = " ".join(
            str(x).split()
        ).lower()

        if x and x not in saida:
            saida.append(x)

    return saida


if not os.path.exists(
    SCENE_MAP
):

    raise SystemExit(
        "ERRO: scene_map não encontrado."
    )


with open(
    SCENE_MAP,
    "r",
    encoding="utf-8"
) as f:

    mapa = json.load(f)


cenas = mapa.get(
    "scenes",
    []
)


if not isinstance(
    cenas,
    list
) or not cenas:

    raise SystemExit(
        "ERRO: scene_map sem cenas."
    )


with open(
    BACKUP,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        mapa,
        f,
        ensure_ascii=False,
        indent=2
    )


mudancas = []


for i in range(
    1,
    len(cenas)
):

    anterior = cenas[
        i - 1
    ]

    atual = cenas[
        i
    ]


    query_ant = str(
        anterior.get(
            "query",
            ""
        )
    )

    query_atual = str(
        atual.get(
            "query",
            ""
        )
    )


    sim = similaridade(
        query_ant,
        query_atual
    )


    if sim < 0.45:
        continue


    modo_ant = str(
        anterior.get(
            "visual_mode",
            ""
        )
    ).lower()

    modo_atual = str(
        atual.get(
            "visual_mode",
            ""
        )
    ).lower()


    shot_ant = str(
        anterior.get(
            "shot_type",
            ""
        )
    ).lower()

    shot_atual = str(
        atual.get(
            "shot_type",
            ""
        )
    ).lower()


    novo_query = query_atual
    novo_shot = shot_atual


    # =============================================
    # DIFERENCIAR ENQUADRAMENTO
    # =============================================

    if shot_ant == shot_atual:

        if shot_atual in {
            "wide",
            "exterior",
            "aerial"
        }:

            novo_shot = "detail"

        elif shot_atual in {
            "detail",
            "close_up"
        }:

            novo_shot = "wide"

        else:

            novo_shot = "close_up"


    # =============================================
    # ALTERAR PERSPECTIVA DA QUERY
    # =============================================

    if novo_shot == "detail":

        novo_query = (
            query_atual
            + " detailed close view texture object detail"
        )

    elif novo_shot == "close_up":

        novo_query = (
            query_atual
            + " close up detail"
        )

    elif novo_shot == "wide":

        novo_query = (
            query_atual
            + " wide establishing view"
        )


    # =============================================
    # EVITAR MESMO OBJETO DOMINANTE
    # =============================================

    must_ant = limpar_lista(
        anterior.get(
            "must_have",
            []
        )
    )

    must_atual = limpar_lista(
        atual.get(
            "must_have",
            []
        )
    )


    comuns = set(
        must_ant
    ).intersection(
        must_atual
    )


    # Quando as duas cenas exigem exatamente
    # o mesmo objeto, a segunda ganha
    # uma instrução visual de detalhe/contexto.
    if comuns:

        if novo_shot in {
            "detail",
            "close_up"
        }:

            novo_query += (
                " material surface architectural detail"
            )

        else:

            novo_query += (
                " surrounding environment context"
            )


    novo_query = " ".join(
        novo_query.split()
    )


    mudancas.append(
        {
            "scene":
                atual.get(
                    "scene"
                ),

            "similarity":
                round(
                    sim,
                    3
                ),

            "before":
                query_atual,

            "after":
                novo_query,

            "shot_before":
                shot_atual,

            "shot_after":
                novo_shot
        }
    )


    atual[
        "query"
    ] = novo_query

    atual[
        "shot_type"
    ] = novo_shot


mapa[
    "editorial_continuity"
] = {
    "version":
        "4.4",

    "changes":
        len(
            mudancas
        )
}


with open(
    SCENE_MAP,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        mapa,
        f,
        ensure_ascii=False,
        indent=2
    )


with open(
    OUTPUT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "short_id":
                SHORT_ID,

            "version":
                "4.4",

            "changes":
                mudancas
        },
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("================================")
print("EDITORIAL CONTINUITY GUARD 4.4")
print("================================")
print()

print(
    f"Cenas analisadas: "
    f"{len(cenas)}"
)

print(
    f"Repetições ajustadas: "
    f"{len(mudancas)}"
)

print()


for item in mudancas:

    print(
        f"Cena {item['scene']:02d}:"
    )

    print(
        f"  Similaridade: "
        f"{item['similarity']:.3f}"
    )

    print(
        f"  ANTES: "
        f"{item['before']}"
    )

    print(
        f"  DEPOIS: "
        f"{item['after']}"
    )

    print(
        f"  SHOT: "
        f"{item['shot_before']} "
        f"-> "
        f"{item['shot_after']}"
    )

    print()


print(
    "EDITORIAL CONTINUITY: OK"
)

print()
