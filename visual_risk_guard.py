#!/usr/bin/env python3

import os
import sys
import json
import re
from datetime import date


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

REPORT = os.path.join(
    BASE,
    "roteiros",
    f"visual_risk_{SHORT_ID}.json"
)


if not os.path.exists(
    SCENE_MAP
):

    sys.exit(
        "ERRO: scene_map não encontrado."
    )


try:

    with open(
        SCENE_MAP,
        "r",
        encoding="utf-8"
    ) as f:

        mapa = json.load(f)

except Exception as e:

    sys.exit(
        f"ERRO lendo scene_map: {e}"
    )


cenas = mapa.get(
    "scenes",
    []
)


if not isinstance(
    cenas,
    list
):

    sys.exit(
        "ERRO: scenes inválido."
    )


# =====================================================
# TERMOS DE RISCO
# =====================================================

RISCOS = {
    "ufo": "mysterious unidentified light",
    "flying saucer": "unidentified distant light",
    "alien spacecraft": "mysterious light in distance",
    "alien": "unidentified distant figure",
    "extraterrestrial": "unexplained distant light",

    "ghost": "shadowy silhouette",
    "paranormal entity": "unexplained shadow",
    "spirit": "shadowy atmosphere",

    "dead body": "covered stretcher",
    "corpse": "forensic scene context",

    "blood": "crime scene evidence",
    "bloody": "forensic scene",

    "murder scene": "police investigation scene"
}


TERMOS_ALEGACAO = [
    "alleged",
    "claimed",
    "reported",
    "reportedly",
    "theory",
    "theories",
    "speculation",
    "speculated",
    "mysterious",
    "unexplained",
    "unknown",
    "possible",
    "possibly",

    "alegou",
    "alegação",
    "alegacoes",
    "alegações",
    "relatou",
    "relato",
    "teoria",
    "teorias",
    "especulação",
    "especulacao",
    "mistério",
    "misterio",
    "inexplicável",
    "inexplicavel",
    "desconhecido"
]


# =====================================================
# HELPERS
# =====================================================

def normalizar(
    texto
):

    return " ".join(
        str(texto)
        .replace("\n", " ")
        .split()
    )


def tem_contexto_incerto(
    segmento
):

    texto = normalizar(
        segmento
    ).lower()

    return any(
        termo in texto
        for termo in TERMOS_ALEGACAO
    )


def remover_duplicatas(
    lista
):

    saida = []

    for x in lista:

        x = normalizar(
            x
        ).lower()

        if (
            x
            and x not in saida
        ):

            saida.append(
                x
            )

    return saida


# =====================================================
# PROCESSAR
# =====================================================

mudancas = []


for cena in cenas:

    numero = cena.get(
        "scene"
    )

    segmento = normalizar(
        cena.get(
            "segment",
            ""
        )
    )

    query_original = normalizar(
        cena.get(
            "query",
            ""
        )
    )

    query = query_original

    must = [
        normalizar(x).lower()
        for x in cena.get(
            "must_have",
            []
        )
    ]

    avoid = [
        normalizar(x).lower()
        for x in cena.get(
            "avoid",
            []
        )
    ]


    contexto_incerto = (
        tem_contexto_incerto(
            segmento
        )
    )


    alterada = False
    motivos = []


    # ---------------------------------
    # QUERY
    # ---------------------------------

    query_lower = query.lower()


    for termo, substituto in RISCOS.items():

        if termo not in query_lower:
            continue


        # UFO / paranormal sempre devem
        # ser contextualizados visualmente.
        if (
            contexto_incerto
            or termo in [
                "ufo",
                "flying saucer",
                "alien spacecraft",
                "alien",
                "extraterrestrial",
                "ghost",
                "paranormal entity",
                "spirit"
            ]
        ):

            query = re.sub(
                re.escape(
                    termo
                ),
                substituto,
                query,
                flags=re.IGNORECASE
            )

            motivos.append(
                f"query:{termo}"
            )

            alterada = True


    # ---------------------------------
    # MUST
    # ---------------------------------

    must_novo = []


    for item in must:

        novo_item = item


        for termo, substituto in RISCOS.items():

            if termo in novo_item:

                if (
                    contexto_incerto
                    or termo in [
                        "ufo",
                        "flying saucer",
                        "alien spacecraft",
                        "alien",
                        "extraterrestrial",
                        "ghost",
                        "paranormal entity",
                        "spirit"
                    ]
                ):

                    novo_item = (
                        substituto
                    )

                    motivos.append(
                        f"must:{termo}"
                    )

                    alterada = True


        must_novo.append(
            novo_item
        )


    # ---------------------------------
    # AVOID EXTRA
    # ---------------------------------

    if contexto_incerto:

        extras = [
            "detailed alien spacecraft",
            "flying saucer",
            "visible ghost",
            "alien creature"
        ]


        for x in extras:

            if x not in avoid:

                avoid.append(
                    x
                )


    must_novo = remover_duplicatas(
        must_novo
    )

    avoid = remover_duplicatas(
        avoid
    )


    # ---------------------------------
    # SALVAR CENA
    # ---------------------------------

    cena[
        "query"
    ] = normalizar(
        query
    )

    cena[
        "must_have"
    ] = must_novo

    cena[
        "avoid"
    ] = avoid


    if alterada:

        mudancas.append(
            {
                "scene":
                    numero,

                "segment":
                    segmento,

                "query_before":
                    query_original,

                "query_after":
                    cena[
                        "query"
                    ],

                "reasons":
                    motivos
            }
        )


# =====================================================
# SALVAR
# =====================================================

mapa[
    "visual_risk_guard"
] = {
    "version":
        "3.0.2",

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
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "short_id":
                SHORT_ID,

            "changes":
                mudancas
        },
        f,
        ensure_ascii=False,
        indent=2
    )


# =====================================================
# TERMINAL
# =====================================================

print()
print("================================")
print("FACTUAL VISUAL RISK GUARD 3.0.2")
print("================================")
print()

print(
    f"Cenas analisadas: "
    f"{len(cenas)}"
)

print(
    f"Cenas ajustadas: "
    f"{len(mudancas)}"
)

print()


for item in mudancas:

    print(
        f"Cena {item['scene']:02d}:"
    )

    print(
        f"  ANTES: "
        f"{item['query_before']}"
    )

    print(
        f"  DEPOIS: "
        f"{item['query_after']}"
    )

    print()


print(
    "VISUAL RISK GUARD: OK"
)

print()
