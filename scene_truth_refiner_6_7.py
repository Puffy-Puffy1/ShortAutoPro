#!/usr/bin/env python3

import os
import re
import json
import unicodedata
from datetime import date


# =====================================================
# SHORTAUTO PRO
# SCENE TRUTH REFINER 6.7
# =====================================================

BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

R = os.path.join(
    BASE,
    "roteiros"
)

MAPA = os.path.join(
    R,
    f"scene_map_{SHORT_ID}.json"
)

BACKUP = os.path.join(
    R,
    f"scene_map_pre_truth_refiner_{SHORT_ID}.json"
)

REPORT = os.path.join(
    R,
    f"scene_truth_refiner_{SHORT_ID}.json"
)


def normalizar(texto):

    texto = unicodedata.normalize(
        "NFKD",
        str(texto or "")
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    return re.sub(
        r"\s+",
        " ",
        texto.lower()
    ).strip()


def clean_list(
    valores,
    limite=6
):

    if not isinstance(
        valores,
        list
    ):
        return []

    saida = []

    for x in valores:

        x = str(x).strip().lower()

        if (
            x
            and x not in saida
        ):
            saida.append(x)

    return saida[:limite]


def add_avoid(
    cena,
    *termos
):

    atual = clean_list(
        cena.get(
            "avoid",
            []
        ),
        12
    )

    for termo in termos:

        termo = str(
            termo
        ).strip().lower()

        if (
            termo
            and termo not in atual
        ):
            atual.append(
                termo
            )

    cena["avoid"] = atual[:12]


def set_visual(
    cena,
    query,
    must,
    mode,
    intent,
    reason
):

    cena["query"] = query

    cena["must_have"] = [
        str(x).lower()
        for x in must
    ]

    cena["visual_mode"] = mode

    cena["visual_intent_6_7"] = intent

    cena["truth_refiner_6_7"] = reason


if not os.path.exists(
    MAPA
):
    raise SystemExit(
        f"ERRO: scene_map ausente: {MAPA}"
    )


with open(
    MAPA,
    "r",
    encoding="utf-8"
) as f:
    mapa = json.load(f)


cenas = mapa.get(
    "scenes",
    []
)

if len(cenas) != 12:
    raise SystemExit(
        f"ERRO: esperado 12 cenas; encontrado {len(cenas)}."
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


alteracoes = []


for numero, cena in enumerate(
    cenas,
    1
):

    segmento = str(
        cena.get(
            "segment",
            ""
        )
    ).strip()

    seg = normalizar(
        segmento
    )

    original = {
        "query":
            cena.get(
                "query"
            ),

        "must_have":
            cena.get(
                "must_have"
            ),

        "visual_mode":
            cena.get(
                "visual_mode"
            )
    }


    # =============================================
    # 1. PESSOA REAL / MENOR NOMEADO
    # =============================================

    if (
        "mary kellerman" in seg
        or (
            "primeira vitima" in seg
            and "anos" in seg
        )
    ):

        set_visual(
            cena,

            (
                "1980s Tylenol medicine bottle "
                "capsules archival newspaper context"
            ),

            [
                "medicine bottle",
                "capsules"
            ],

            "evidence",

            "EVIDENCE",

            "named_minor_no_generic_portrait"
        )

        add_avoid(
            cena,
            "generic child portrait",
            "young girl portrait",
            "random child",
            "reenactment",
            "actor"
        )


    # =============================================
    # 2. FAMÍLIA REAL NOMEADA
    # =============================================

    elif "familia janus" in seg:

        set_visual(
            cena,

            (
                "1982 Chicago Tylenol poisoning "
                "newspaper archive medicine bottles"
            ),

            [
                "newspaper",
                "medicine"
            ],

            "document",

            "DOCUMENT",

            "named_family_no_generic_family"
        )

        add_avoid(
            cena,
            "generic family",
            "sad family",
            "random people",
            "reenactment",
            "actors"
        )


    # =============================================
    # 3. CULPADO NÃO IDENTIFICADO
    # =============================================

    elif (
        "culpado" in seg
        and (
            "jamais" in seg
            or "nunca" in seg
            or "nao foi encontrado" in seg
        )
    ):

        set_visual(
            cena,

            (
                "unsolved investigation case files "
                "police documents newspaper archive"
            ),

            [
                "case files",
                "documents"
            ],

            "document",

            "EVIDENCE",

            "unsolved_case_no_fictional_suspect"
        )

        add_avoid(
            cena,
            "mysterious man",
            "shadow person",
            "dark alley suspect",
            "hooded man",
            "criminal portrait"
        )


    # =============================================
    # 4. RECALL HISTÓRICO
    # =============================================

    elif (
        "johnson" in seg
        and "recall" in seg
    ):

        set_visual(
            cena,

            (
                "1982 Tylenol recall medicine bottles "
                "pharmacy newspaper archive"
            ),

            [
                "medicine bottles",
                "pharmacy"
            ],

            "document",

            "EVENT",

            "historical_recall_context"
        )

        add_avoid(
            cena,
            "generic warehouse only",
            "modern ecommerce warehouse"
        )


    # =============================================
    # 5. MUDANÇA DE SEGURANÇA FARMACÊUTICA
    # =============================================

    elif (
        "seguranca" in seg
        and "industria farmaceutica" in seg
    ):

        set_visual(
            cena,

            (
                "tamper resistant medicine packaging "
                "sealed pharmaceutical bottle close up"
            ),

            [
                "medicine packaging",
                "safety seal"
            ],

            "evidence",

            "EVIDENCE",

            "industry_change_visualized_by_packaging"
        )

        add_avoid(
            cena,
            "generic laboratory scientist",
            "medical experiment"
        )


    # =============================================
    # 6. EMBALAGEM LACRADA
    # =============================================

    elif (
        "embalagens lacradas" in seg
        or "lacre" in seg
    ):

        set_visual(
            cena,

            (
                "tamper evident medicine bottle "
                "safety seal packaging close up"
            ),

            [
                "medicine bottle",
                "safety seal"
            ],

            "evidence",

            "EVIDENCE",

            "direct_visual_consequence"
        )


    # =============================================
    # 7. CTA
    # =============================================

    elif (
        "comente" in seg
        or "siga" in seg
        or "mais historias reais" in seg
    ):

        cena[
            "visual_intent_6_7"
        ] = "CTA"

        cena[
            "visual_mode"
        ] = "cta_reuse"

        cena[
            "truth_refiner_6_7"
        ] = "reuse_verified_story_visual"

        cena[
            "cta_reuse_6_7"
        ] = True

        add_avoid(
            cena,
            "social media icon",
            "thumbs up",
            "generic influencer",
            "random person"
        )


    # =============================================
    # 8. PERGUNTA FINAL SOBRE REMÉDIO
    # =============================================

    elif (
        "qual remedio" in seg
        or "tem em casa" in seg
    ):

        set_visual(
            cena,

            (
                "sealed medicine bottles "
                "home medicine cabinet close up"
            ),

            [
                "medicine bottles",
                "cabinet"
            ],

            "object",

            "CTA",

            "question_visual_without_identity_claim"
        )


    # =============================================
    # 9. CENA INICIAL
    # =============================================

    elif (
        "cianeto" in seg
        and "chicago" in seg
    ):

        set_visual(
            cena,

            (
                "1982 medicine capsules "
                "Tylenol bottle archival evidence"
            ),

            [
                "capsules",
                "medicine bottle"
            ],

            "evidence",

            "EVIDENCE",

            "remove_conflicting_table_street_concepts"
        )


    # =============================================
    # REGISTRA MUDANÇA
    # =============================================

    novo = {
        "query":
            cena.get(
                "query"
            ),

        "must_have":
            cena.get(
                "must_have"
            ),

        "visual_mode":
            cena.get(
                "visual_mode"
            )
    }


    if novo != original:

        alteracoes.append(
            {
                "scene":
                    numero,

                "segment":
                    segmento,

                "before":
                    original,

                "after":
                    novo,

                "reason":
                    cena.get(
                        "truth_refiner_6_7"
                    )
            }
        )


mapa[
    "scenes"
] = cenas


mapa[
    "scene_truth_refiner_6_7"
] = {
    "changed":
        len(
            alteracoes
        ),

    "version":
        "6.7"
}


with open(
    MAPA,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        mapa,
        f,
        ensure_ascii=False,
        indent=2
    )


report = {
    "short_id":
        SHORT_ID,

    "version":
        "6.7",

    "changed":
        len(
            alteracoes
        ),

    "changes":
        alteracoes,

    "backup":
        BACKUP
}


with open(
    REPORT,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        report,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("======================================")
print(" SCENE TRUTH REFINER 6.7")
print("======================================")
print()

print(
    "Cenas:",
    len(cenas)
)

print(
    "Ajustadas:",
    len(alteracoes)
)

print()


for item in alteracoes:

    print(
        f"CENA {item['scene']:02d}: "
        f"{item['reason']}"
    )

    print(
        "  QUERY:",
        item[
            "after"
        ][
            "query"
        ]
    )

    print(
        "  MODE:",
        item[
            "after"
        ][
            "visual_mode"
        ]
    )

    print()


print(
    "Mapa:",
    MAPA
)

print(
    "Relatório:",
    REPORT
)

print()
print(
    "SCENE TRUTH REFINER: PASS"
)
