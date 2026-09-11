#!/usr/bin/env python3

import os
import re
import json
import glob

from wikimedia_source import (
    buscar_wikimedia_fotos
)

from evidence_guard import (
    avaliar_evidencia
)

from source_router import (
    escolher_rota
)


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

ROTEIROS = os.path.join(
    BASE,
    "roteiros"
)


# =====================================================
# LOCALIZAR ÚLTIMO SHORT
# =====================================================

videos = sorted(
    glob.glob(
        os.path.join(
            BASE,
            "videos",
            "short_v6_*.mp4"
        )
    ),
    key=os.path.getmtime,
    reverse=True
)


if videos:

    nome = os.path.basename(
        videos[0]
    )

    short_id = (
        nome
        .replace(
            "short_v6_",
            "",
            1
        )
        .rsplit(
            ".mp4",
            1
        )[0]
    )

else:

    mapas = sorted(
        glob.glob(
            os.path.join(
                ROTEIROS,
                "scene_map_*.json"
            )
        ),
        key=os.path.getmtime,
        reverse=True
    )

    if not mapas:

        raise SystemExit(
            "ERRO: nenhuma produção encontrada."
        )

    nome = os.path.basename(
        mapas[0]
    )

    short_id = (
        nome
        .replace(
            "scene_map_",
            "",
            1
        )
        .rsplit(
            ".json",
            1
        )[0]
    )


# =====================================================
# ARQUIVOS
# =====================================================

scene_path = os.path.join(
    ROTEIROS,
    f"scene_map_{short_id}.json"
)

topic_real = os.path.join(
    ROTEIROS,
    f"used_topic_{short_id}.txt"
)

topic_alt = os.path.join(
    ROTEIROS,
    f"topic_{short_id}.txt"
)

report_path = os.path.join(
    ROTEIROS,
    f"documentary_test_5_2_{short_id}.json"
)


with open(
    scene_path,
    "r",
    encoding="utf-8"
) as f:

    mapa = json.load(f)


def ler(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


assunto = (
    ler(topic_real)
    or ler(topic_alt)
)


scenes = mapa.get(
    "scenes",
    []
)


if not assunto:

    raise SystemExit(
        "ERRO: assunto não encontrado."
    )


if len(scenes) != 12:

    raise SystemExit(
        f"ERRO: scene_map possui "
        f"{len(scenes)} cenas."
    )


# =====================================================
# RANK
# =====================================================

CLASS_RANK = {
    "CASE_DIRECT": 5,
    "CONTEXTUAL": 4,
    "GENERIC_DOCUMENT": 2,
    "GENERIC": 1,
    "RISKY_IDENTITY": -5
}


def cobertura_must(
    candidato,
    total
):

    if total <= 0:
        return 1.0

    hits = int(
        candidato.get(
            "must_hits",
            0
        )
        or 0
    )

    return min(
        1.0,
        hits / total
    )


# =====================================================
# EXECUÇÃO
# =====================================================

print()
print("======================================")
print(" DOCUMENTARY AUTHENTICITY TEST 5.2")
print(" SEM GERAR VIDEO")
print("======================================")
print()

print(
    f"SHORT_ID: {short_id}"
)

print(
    f"ASSUNTO: {assunto}"
)

print()


resumo = {
    "short_id":
        short_id,

    "topic":
        assunto,

    "documentary_scenes":
        0,

    "raw_wikimedia":
        0,

    "approved":
        0,

    "rejected":
        0,

    "case_direct":
        0,

    "contextual":
        0,

    "generic_document":
        0,

    "priority_ready":
        0,

    "scenes":
        []
}


for numero, cena in enumerate(
    scenes,
    start=1
):

    query = str(
        cena.get(
            "query",
            ""
        )
    ).strip()

    segmento = str(
        cena.get(
            "segment",
            ""
        )
    ).strip()

    mode = str(
        cena.get(
            "visual_mode",
            ""
        )
    ).strip()

    must = [
        str(x).strip().lower()
        for x in cena.get(
            "must_have",
            []
        )
        if str(x).strip()
    ]

    avoid = [
        str(x).strip().lower()
        for x in cena.get(
            "avoid",
            []
        )
        if str(x).strip()
    ]


    rota = escolher_rota(
        mode,
        must
    )


    if rota.get(
        "route"
    ) != "documentary_first":

        continue


    resumo[
        "documentary_scenes"
    ] += 1


    print(
        "--------------------------------------"
    )

    print(
        f"CENA {numero}/12"
    )

    print(
        f"MODE: {mode}"
    )

    print(
        f"QUERY: {query}"
    )

    print(
        f"MUST: {', '.join(must)}"
    )

    print()


    try:

        raw = buscar_wikimedia_fotos(
            query,
            must,
            avoid,
            assunto=assunto,
            segmento=segmento,
            visual_mode=mode,
            limite=12
        )

    except Exception as e:

        print(
            f"WIKIMEDIA ERROR: "
            f"{type(e).__name__}: "
            f"{str(e)[:180]}"
        )

        raw = []


    resumo[
        "raw_wikimedia"
    ] += len(
        raw
    )


    print(
        f"WIKIMEDIA RAW: {len(raw)}"
    )


    aprovados = []


    for candidato in raw:

        try:

            ev = avaliar_evidencia(
                candidato,
                assunto,
                segmento,
                must,
                mode
            )

        except Exception as e:

            print(
                f"  EVIDENCE ERROR: "
                f"{type(e).__name__}: "
                f"{str(e)[:120]}"
            )

            continue


        classe = ev.get(
            "class",
            "GENERIC"
        )

        allowed = bool(
            ev.get(
                "allowed",
                False
            )
        )


        if allowed:

            resumo[
                "approved"
            ] += 1

        else:

            resumo[
                "rejected"
            ] += 1


        if classe == "CASE_DIRECT":

            resumo[
                "case_direct"
            ] += 1

        elif classe == "CONTEXTUAL":

            resumo[
                "contextual"
            ] += 1

        elif classe == "GENERIC_DOCUMENT":

            resumo[
                "generic_document"
            ] += 1


        enriched = dict(
            candidato
        )

        enriched[
            "evidence_class"
        ] = classe

        enriched[
            "topic_overlap"
        ] = float(
            ev.get(
                "topic_overlap",
                0.0
            )
        )

        enriched[
            "segment_overlap"
        ] = float(
            ev.get(
                "segment_overlap",
                0.0
            )
        )

        enriched[
            "evidence_must_coverage"
        ] = float(
            ev.get(
                "must_coverage",
                0.0
            )
        )


        enriched[
            "_test_score"
        ] = (
            float(
                enriched.get(
                    "score",
                    0.0
                )
            )
            + float(
                rota.get(
                    "wikimedia_bonus",
                    0.0
                )
            )
            + float(
                ev.get(
                    "bonus",
                    0.0
                )
            )
        )


        if allowed:

            aprovados.append(
                enriched
            )


    aprovados.sort(
        key=lambda c: (
            CLASS_RANK.get(
                c.get(
                    "evidence_class",
                    ""
                ),
                0
            ),

            c.get(
                "must_hits",
                0
            ),

            c.get(
                "_test_score",
                -999
            )
        ),
        reverse=True
    )


    priority = None


    for candidato in aprovados:

        classe = candidato.get(
            "evidence_class"
        )

        coverage = cobertura_must(
            candidato,
            len(must)
        )

        topic_overlap = float(
            candidato.get(
                "topic_overlap",
                0.0
            )
        )

        score = float(
            candidato.get(
                "_test_score",
                -999
            )
        )


        if (
            classe == "CASE_DIRECT"
            and (
                coverage >= 0.50
                or topic_overlap >= 0.75
            )
        ):

            priority = candidato
            break


        if (
            classe == "CONTEXTUAL"
            and coverage >= 0.50
            and score >= 65
        ):

            priority = candidato
            break


    print(
        f"APROVADOS: {len(aprovados)}"
    )


    for pos, candidato in enumerate(
        aprovados[:3],
        start=1
    ):

        print(
            f"  {pos}. "
            f"{candidato.get('evidence_class', '?')} "
            f"score="
            f"{candidato.get('_test_score', 0):.1f} "
            f"must="
            f"{candidato.get('must_hits', 0)}/"
            f"{len(must)} "
            f"topic="
            f"{candidato.get('topic_overlap', 0) * 100:.0f}% "
            f"segment="
            f"{candidato.get('segment_overlap', 0) * 100:.0f}%"
        )

        print(
            "     "
            + str(
                candidato.get(
                    "descricao",
                    ""
                )
            )[:150]
        )


    if priority:

        resumo[
            "priority_ready"
        ] += 1

        print()
        print(
            "DOCUMENTARY PRIORITY TEST: ATIVARIA"
        )

        print(
            f"  CLASS: "
            f"{priority.get('evidence_class')}"
        )

        print(
            f"  SCORE: "
            f"{priority.get('_test_score', 0):.1f}"
        )

        print(
            f"  MUST: "
            f"{priority.get('must_hits', 0)}/"
            f"{len(must)}"
        )

        print(
            f"  TOPIC: "
            f"{priority.get('topic_overlap', 0) * 100:.0f}%"
        )

    else:

        print()
        print(
            "DOCUMENTARY PRIORITY TEST: NÃO ATIVARIA"
        )

        if raw and not aprovados:

            print(
                "  MOTIVO: Wikimedia encontrada, "
                "mas Evidence Guard rejeitou."
            )

        elif aprovados:

            print(
                "  MOTIVO: candidatos permitidos, "
                "mas sem força suficiente."
            )

        else:

            print(
                "  MOTIVO: nenhum candidato Wikimedia."
            )


    resumo[
        "scenes"
    ].append(
        {
            "scene":
                numero,

            "visual_mode":
                mode,

            "raw":
                len(raw),

            "approved":
                len(aprovados),

            "priority":
                bool(priority),

            "priority_class":
                (
                    priority.get(
                        "evidence_class"
                    )
                    if priority
                    else None
                ),

            "priority_score":
                (
                    round(
                        priority.get(
                            "_test_score",
                            0
                        ),
                        2
                    )
                    if priority
                    else None
                )
        }
    )


    print()


# =====================================================
# RESULTADO
# =====================================================

with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        resumo,
        f,
        ensure_ascii=False,
        indent=2
    )


print()
print("======================================")
print(" RESULTADO DOCUMENTARY 5.2")
print("======================================")
print()

print(
    f"Cenas documentary_first: "
    f"{resumo['documentary_scenes']}"
)

print(
    f"Wikimedia encontrados: "
    f"{resumo['raw_wikimedia']}"
)

print(
    f"Evidence aprovados: "
    f"{resumo['approved']}"
)

print(
    f"Evidence rejeitados: "
    f"{resumo['rejected']}"
)

print(
    f"CASE_DIRECT: "
    f"{resumo['case_direct']}"
)

print(
    f"CONTEXTUAL: "
    f"{resumo['contextual']}"
)

print(
    f"GENERIC_DOCUMENT: "
    f"{resumo['generic_document']}"
)

print(
    f"Cenas que ativariam prioridade: "
    f"{resumo['priority_ready']}"
)

print()

print(
    f"Relatório:\n"
    f"{report_path}"
)

print()

print(
    "NENHUMA MIDIA FOI SUBSTITUIDA"
)

print(
    "NENHUM VIDEO FOI GERADO"
)

print()
