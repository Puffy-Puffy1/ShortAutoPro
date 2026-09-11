#!/usr/bin/env python3

import os
import re
import json
import math
import unicodedata


# =====================================================
# SHORTAUTO PRO
# VISUAL INTELLIGENCE 6.0
# SHADOW / STORYBOARD ENGINE
# =====================================================


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

REPORT_DIR = os.path.join(
    BASE,
    "roteiros"
)


# =====================================================
# CONSTANTES
# =====================================================

DOCUMENTARY_CLASSES = {
    "CASE_DIRECT",
    "CONTEXTUAL"
}


SOURCE_STOCK = {
    "Pexels",
    "Pixabay",
    "Coverr"
}


CTA_TERMS = {
    "comente",
    "comentario",
    "comentário",
    "acha",
    "voce",
    "você",
    "teoria",
    "opina",
    "opinião",
    "opiniao",
    "qual",
    "subscribe",
    "comment",
    "what do you think",
    "your theory"
}


HUMAN_TERMS = {
    "person",
    "people",
    "man",
    "woman",
    "girl",
    "boy",
    "child",
    "children",
    "portrait",
    "face",
    "human",
    "student",
    "doctor",
    "nurse",
    "patient",
    "homem",
    "mulher",
    "pessoa",
    "menina",
    "menino",
    "rosto"
}


MASK_TERMS = {
    "gas mask",
    "respirator",
    "hazmat",
    "protective mask",
    "máscara de gás",
    "mascara de gas"
}


CREATURE_TERMS = {
    "alien",
    "creature",
    "monster",
    "humanoid",
    "ufo being",
    "extraterrestrial",
    "monstro",
    "criatura",
    "humanoide",
    "alienigena",
    "alienígena"
}


MEDICAL_LAB_TERMS = {
    "laboratory",
    "lab",
    "test tube",
    "test tubes",
    "chemical",
    "chemistry",
    "microscope",
    "scientist",
    "laboratorio",
    "laboratório",
    "tubo de ensaio",
    "quimica",
    "química"
}


DOCUMENT_TERMS = {
    "document",
    "report",
    "paper",
    "papers",
    "file",
    "record",
    "newspaper",
    "letter",
    "autopsy",
    "coroner",
    "documento",
    "relatorio",
    "relatório",
    "arquivo",
    "jornal"
}


LOCATION_TERMS = {
    "street",
    "city",
    "building",
    "hotel",
    "hospital",
    "house",
    "road",
    "mountain",
    "forest",
    "lake",
    "river",
    "rooftop",
    "corridor",
    "hallway",
    "rua",
    "cidade",
    "predio",
    "prédio",
    "hospital",
    "hotel",
    "estrada",
    "floresta",
    "corredor"
}


ATMOSPHERE_TERMS = {
    "fog",
    "mist",
    "smoke",
    "dark",
    "night",
    "shadow",
    "storm",
    "rain",
    "nevoa",
    "névoa",
    "fumaca",
    "fumaça",
    "escuro",
    "noite"
}


# =====================================================
# TEXTO
# =====================================================

STOP = {
    "the", "a", "an", "of", "in", "on", "at",
    "with", "and", "or", "to", "for", "from",
    "by", "this", "that",

    "o", "a", "os", "as", "um", "uma",
    "de", "da", "do", "das", "dos",
    "em", "no", "na", "nos", "nas",
    "com", "sem", "para", "por", "e", "ou",

    "cinematic", "dramatic", "dark",
    "vintage", "historic", "historical",
    "shot", "scene", "view"
}


def normalizar(
    texto
):

    texto = unicodedata.normalize(
        "NFKD",
        str(
            texto or ""
        )
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(
            c
        )
    )

    return texto.lower()


def tokens(
    texto
):

    return {
        x
        for x in re.findall(
            r"[a-z0-9]+",
            normalizar(
                texto
            )
        )
        if (
            len(x) >= 3
            and x not in STOP
        )
    }


def contains_any(
    texto,
    termos
):

    t = normalizar(
        texto
    )

    return any(
        normalizar(
            termo
        ) in t
        for termo in termos
    )


def overlap(
    a,
    b
):

    ta = tokens(
        a
    )

    tb = tokens(
        b
    )

    if not ta:
        return 0.0

    return (
        len(
            ta & tb
        )
        / len(
            ta
        )
    )


def similarity(
    a,
    b
):

    ta = tokens(
        a
    )

    tb = tokens(
        b
    )

    if not ta or not tb:
        return 0.0

    return (
        len(
            ta & tb
        )
        / len(
            ta | tb
        )
    )


# =====================================================
# INTENÇÃO DA CENA
# =====================================================

def detectar_intent(
    numero,
    total,
    query,
    segmento,
    visual_mode
):

    texto = (
        str(
            query
        )
        + " "
        + str(
            segmento
        )
    )


    if (
        numero == total
        or contains_any(
            texto,
            CTA_TERMS
        )
    ):

        return "CTA"


    mode = str(
        visual_mode or ""
    ).lower()


    if mode == "human_context":

        return "PERSON"


    if mode in {
        "location",
        "architecture",
        "map_context"
    }:

        return "LOCATION"


    if mode in {
        "document",
        "evidence"
    }:

        return "EVIDENCE"


    if mode == "transport":

        return "TRANSPORT"


    if contains_any(
        texto,
        ATMOSPHERE_TERMS
    ):

        return "ATMOSPHERE"


    if contains_any(
        texto,
        DOCUMENT_TERMS
    ):

        return "EVIDENCE"


    if contains_any(
        texto,
        LOCATION_TERMS
    ):

        return "LOCATION"


    return "EVENT"


# =====================================================
# RISCO DE REPRESENTAÇÃO
# =====================================================

def risco_representacional(
    candidato,
    intent,
    query,
    segmento,
    visual_mode
):

    fonte = str(
        candidato.get(
            "fonte",
            ""
        )
    )

    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )

    narrativa = (
        str(
            query
        )
        + " "
        + str(
            segmento
        )
    )


    evidence_class = str(
        candidato.get(
            "evidence_class",
            ""
        )
    )


    # ---------------------------------
    # DOCUMENTÁRIO REAL
    # ---------------------------------

    if (
        fonte == "Wikimedia"
        and evidence_class
        in DOCUMENTARY_CLASSES
    ):

        return {
            "class":
                "REAL_DOCUMENTARY",

            "risk":
                "LOW",

            "penalty":
                0.0,

            "reason":
                "verified_documentary_context"
        }


    # ---------------------------------
    # CTA
    # ---------------------------------

    if intent == "CTA":

        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -35.0,

            "reason":
                "cta_should_prefer_visual_reuse"
        }


    # ---------------------------------
    # PESSOA GENÉRICA
    # ---------------------------------

    if (
        contains_any(
            desc,
            HUMAN_TERMS
        )
        and intent == "PERSON"
    ):

        return {
            "class":
                "MISLEADING_REENACTMENT",

            "risk":
                "HIGH",

            "penalty":
                -95.0,

            "reason":
                "generic_person_could_imply_real_identity"
        }


    # ---------------------------------
    # CRIATURA / ALIEN
    # ---------------------------------

    if contains_any(
        desc,
        CREATURE_TERMS
    ):

        if not contains_any(
            narrativa,
            CREATURE_TERMS
        ):

            return {
                "class":
                    "MISLEADING_REENACTMENT",

                "risk":
                    "HIGH",

                "penalty":
                    -120.0,

                "reason":
                    "creature_not_asserted_by_narrative"
            }


        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -35.0,

            "reason":
                "creature_is_illustrative_not_evidence"
        }


    # ---------------------------------
    # MÁSCARA / HAZMAT
    # ---------------------------------

    if contains_any(
        desc,
        MASK_TERMS
    ):

        if not contains_any(
            narrativa,
            MASK_TERMS
        ):

            return {
                "class":
                    "MISLEADING_REENACTMENT",

                "risk":
                    "HIGH",

                "penalty":
                    -110.0,

                "reason":
                    "protective_equipment_not_in_narrative"
            }


    # ---------------------------------
    # LABORATÓRIO
    # ---------------------------------

    if contains_any(
        desc,
        MEDICAL_LAB_TERMS
    ):

        if (
            intent
            not in {
                "EVIDENCE",
                "EVENT"
            }
        ):

            return {
                "class":
                    "ILLUSTRATIVE",

                "risk":
                    "MEDIUM",

                "penalty":
                    -28.0,

                "reason":
                    "laboratory_visual_is_symbolic"
            }


        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -16.0,

            "reason":
                "medical_visual_is_illustrative"
        }


    # ---------------------------------
    # DOCUMENTO STOCK
    # ---------------------------------

    if (
        contains_any(
            desc,
            DOCUMENT_TERMS
        )
        and fonte
        in SOURCE_STOCK
    ):

        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -20.0,

            "reason":
                "generic_document_not_case_evidence"
        }


    # ---------------------------------
    # CONTEXTO SEGURO
    # ---------------------------------

    return {
        "class":
            "SAFE_CONTEXT",

        "risk":
            "LOW",

        "penalty":
            0.0,

        "reason":
            "generic_context_without_identity_claim"
    }


# =====================================================
# PROVENIÊNCIA
# =====================================================

def provenance_score(
    candidato
):

    fonte = str(
        candidato.get(
            "fonte",
            ""
        )
    )


    evidence = str(
        candidato.get(
            "evidence_class",
            ""
        )
    )


    if (
        fonte == "Wikimedia"
        and evidence == "CASE_DIRECT"
    ):

        return 100.0


    if (
        fonte == "Wikimedia"
        and evidence == "CONTEXTUAL"
    ):

        tier = str(
            candidato.get(
                "wiki_query_tier",
                ""
            )
        )


        bonus = {
            "CASE": 88,
            "CASE_VISUAL": 84,
            "CONTEXT_COMBINED": 82,
            "CONTEXT": 62,
            "CONTEXT_VISUAL": 54,
            "GENERIC": 30
        }.get(
            tier,
            50
        )


        anchor = float(
            candidato.get(
                "wiki_anchor_ratio",
                0.0
            )
            or 0.0
        )


        return (
            bonus
            + anchor * 15
        )


    return 25.0


# =====================================================
# CONTINUIDADE
# =====================================================

def continuity_score(
    candidato,
    history
):

    if not history:
        return 85.0


    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )


    anterior = history[
        -1
    ]


    desc_ant = str(
        anterior.get(
            "descricao",
            ""
        )
    )


    sim = similarity(
        desc,
        desc_ant
    )


    # Muito parecido = monotonia.
    if sim >= 0.70:
        return 25.0


    if sim >= 0.50:
        return 48.0


    if sim >= 0.30:
        return 68.0


    return 90.0


# =====================================================
# DIVERSIDADE GLOBAL
# =====================================================

def diversity_score(
    candidato,
    history
):

    if not history:
        return 90.0


    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )


    max_sim = 0.0


    for item in history:

        s = similarity(
            desc,
            item.get(
                "descricao",
                ""
            )
        )

        max_sim = max(
            max_sim,
            s
        )


    if max_sim >= 0.75:
        return 15.0


    if max_sim >= 0.55:
        return 42.0


    if max_sim >= 0.35:
        return 65.0


    return 92.0


# =====================================================
# SCORE SEMÂNTICO 6.0
# =====================================================

def semantic_score(
    candidato,
    query,
    segmento,
    must_have
):

    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )


    base = float(
        candidato.get(
            "_semantic_score",
            candidato.get(
                "score",
                0.0
            )
        )
        or 0.0
    )


    query_match = overlap(
        query,
        desc
    )


    segment_match = overlap(
        segmento,
        desc
    )


    total_must = len(
        must_have
    )


    if total_must:

        must_cov = (
            float(
                candidato.get(
                    "must_hits",
                    0
                )
                or 0
            )
            / total_must
        )

    else:

        must_cov = 1.0


    # Normalização suave para 0–100.
    normalized_base = max(
        0.0,
        min(
            100.0,
            50.0
            + (
                base
                / 5.0
            )
        )
    )


    return (
        normalized_base * 0.40
        + query_match * 100 * 0.20
        + segment_match * 100 * 0.15
        + must_cov * 100 * 0.25
    )


# =====================================================
# MOTION
# =====================================================

def motion_score(
    candidato,
    videos_total,
    video_meta
):

    tipo = str(
        candidato.get(
            "tipo",
            ""
        )
    )


    if tipo != "vídeo":

        return 55.0


    if videos_total < video_meta:

        return 85.0


    return 70.0


# =====================================================
# SCORE FINAL
# =====================================================

def avaliar_candidato(
    candidato,
    intent,
    query,
    segmento,
    visual_mode,
    must_have,
    history,
    videos_total,
    video_meta
):

    safety = risco_representacional(
        candidato,
        intent,
        query,
        segmento,
        visual_mode
    )


    semantic = semantic_score(
        candidato,
        query,
        segmento,
        must_have
    )


    provenance = provenance_score(
        candidato
    )


    continuity = continuity_score(
        candidato,
        history
    )


    diversity = diversity_score(
        candidato,
        history
    )


    motion = motion_score(
        candidato,
        videos_total,
        video_meta
    )


    risk_penalty = float(
        safety.get(
            "penalty",
            0.0
        )
    )


    total = (
        semantic * 0.38
        + provenance * 0.24
        + continuity * 0.14
        + diversity * 0.14
        + motion * 0.10
        + risk_penalty
    )


    # HARD FLOOR para reenactment muito enganoso.
    if (
        safety[
            "class"
        ]
        == "MISLEADING_REENACTMENT"
    ):

        total -= 45.0


    return {
        "candidate":
            candidato,

        "class":
            safety[
                "class"
            ],

        "risk":
            safety[
                "risk"
            ],

        "reason":
            safety[
                "reason"
            ],

        "semantic":
            round(
                semantic,
                2
            ),

        "provenance":
            round(
                provenance,
                2
            ),

        "continuity":
            round(
                continuity,
                2
            ),

        "diversity":
            round(
                diversity,
                2
            ),

        "motion":
            round(
                motion,
                2
            ),

        "score":
            round(
                total,
                2
            )
    }


# =====================================================
# CTA REUSE
# =====================================================

def criar_cta_reuse(
    history
):

    if not history:
        return None


    fortes = [
        x
        for x in history
        if x.get(
            "_vi6_class"
        )
        in {
            "REAL_DOCUMENTARY",
            "SAFE_CONTEXT"
        }
    ]


    pool = (
        fortes
        if fortes
        else history
    )


    melhor = max(
        pool,
        key=lambda x: float(
            x.get(
                "_vi6_score",
                0.0
            )
            or 0.0
        )
    )


    novo = dict(
        melhor
    )


    novo[
        "_vi6_reuse"
    ] = True


    novo[
        "id"
    ] = (
        str(
            melhor.get(
                "id",
                ""
            )
        )
        + "_cta_reuse"
    )


    return novo


# =====================================================
# AUDITORIA DA CENA
# =====================================================

def audit_scene(
    numero,
    total_cenas,
    cena,
    candidatos,
    history,
    videos_total,
    video_meta
):

    query = str(
        cena.get(
            "query",
            ""
        )
    )


    segmento = str(
        cena.get(
            "segment",
            ""
        )
    )


    visual_mode = str(
        cena.get(
            "visual_mode",
            ""
        )
    )


    must_have = [
        str(
            x
        ).lower()
        for x in cena.get(
            "must_have",
            []
        )
    ]


    intent = detectar_intent(
        numero,
        total_cenas,
        query,
        segmento,
        visual_mode
    )


    pool = list(
        candidatos
    )


    if intent == "CTA":

        reuse = criar_cta_reuse(
            history
        )

        if reuse:

            pool.append(
                reuse
            )


    avaliados = []


    for candidato in pool:

        item = avaliar_candidato(
            candidato,
            intent,
            query,
            segmento,
            visual_mode,
            must_have,
            history,
            videos_total,
            video_meta
        )


        # CTA reuse recebe bônus grande.
        if candidato.get(
            "_vi6_reuse"
        ):

            item[
                "class"
            ] = "SAFE_CONTEXT"

            item[
                "risk"
            ] = "LOW"

            item[
                "reason"
            ] = "cta_reuses_strong_story_visual"

            item[
                "score"
            ] += 55.0


        avaliados.append(
            item
        )


    avaliados.sort(
        key=lambda x: x[
            "score"
        ],
        reverse=True
    )


    vencedor = (
        avaliados[0]
        if avaliados
        else None
    )


    # Enriquecemos SOMENTE o candidato shadow.
    if vencedor:

        c = vencedor[
            "candidate"
        ]

        c[
            "_vi6_class"
        ] = vencedor[
            "class"
        ]

        c[
            "_vi6_risk"
        ] = vencedor[
            "risk"
        ]

        c[
            "_vi6_score"
        ] = vencedor[
            "score"
        ]


    return {
        "scene":
            numero,

        "intent":
            intent,

        "query":
            query,

        "segment":
            segmento,

        "visual_mode":
            visual_mode,

        "candidate_count":
            len(
                candidatos
            ),

        "winner":
            serializar_avaliacao(
                vencedor
            ),

        "top":
            [
                serializar_avaliacao(
                    x
                )
                for x in avaliados[:5]
            ]
    }


def serializar_avaliacao(
    item
):

    if not item:
        return None


    candidato = item[
        "candidate"
    ]


    return {
        "fonte":
            candidato.get(
                "fonte"
            ),

        "tipo":
            candidato.get(
                "tipo"
            ),

        "id":
            str(
                candidato.get(
                    "id",
                    ""
                )
            ),

        "descricao":
            str(
                candidato.get(
                    "descricao",
                    ""
                )
            )[:500],

        "class":
            item[
                "class"
            ],

        "risk":
            item[
                "risk"
            ],

        "reason":
            item[
                "reason"
            ],

        "semantic":
            item[
                "semantic"
            ],

        "provenance":
            item[
                "provenance"
            ],

        "continuity":
            item[
                "continuity"
            ],

        "diversity":
            item[
                "diversity"
            ],

        "motion":
            item[
                "motion"
            ],

        "score":
            item[
                "score"
            ],

        "reuse":
            bool(
                candidato.get(
                    "_vi6_reuse"
                )
            ),

        "wiki_query_tier":
            candidato.get(
                "wiki_query_tier"
            ),

        "wiki_anchor_ratio":
            candidato.get(
                "wiki_anchor_ratio"
            ),

        "evidence_class":
            candidato.get(
                "evidence_class"
            )
    }


# =====================================================
# HISTORY
# =====================================================

def push_shadow_history(
    report_scene,
    history
):

    winner = report_scene.get(
        "winner"
    )


    if not winner:
        return


    history.append(
        {
            "descricao":
                winner.get(
                    "descricao",
                    ""
                ),

            "fonte":
                winner.get(
                    "fonte"
                ),

            "tipo":
                winner.get(
                    "tipo"
                ),

            "_vi6_class":
                winner.get(
                    "class"
                ),

            "_vi6_score":
                winner.get(
                    "score"
                )
        }
    )


# =====================================================
# SCORE GLOBAL
# =====================================================

def storyboard_score(
    scenes
):

    if not scenes:
        return 0


    winners = [
        x.get(
            "winner"
        )
        for x in scenes
        if x.get(
            "winner"
        )
    ]


    if not winners:
        return 0


    misleading = sum(
        1
        for x in winners
        if x.get(
            "class"
        )
        == "MISLEADING_REENACTMENT"
    )


    avg = sum(
        max(
            0.0,
            min(
                100.0,
                float(
                    x.get(
                        "score",
                        0
                    )
                )
            )
        )
        for x in winners
    ) / len(
        winners
    )


    penalty = (
        misleading
        * 12
    )


    return round(
        max(
            0,
            min(
                100,
                avg - penalty
            )
        ),
        1
    )


# =====================================================
# RELATÓRIO
# =====================================================

def salvar_report(
    short_id,
    scenes
):

    os.makedirs(
        REPORT_DIR,
        exist_ok=True
    )


    winners = [
        x.get(
            "winner"
        )
        for x in scenes
        if x.get(
            "winner"
        )
    ]


    summary = {
        "storyboard_score":
            storyboard_score(
                scenes
            ),

        "real_documentary":
            sum(
                1
                for x in winners
                if x.get(
                    "class"
                )
                == "REAL_DOCUMENTARY"
            ),

        "safe_context":
            sum(
                1
                for x in winners
                if x.get(
                    "class"
                )
                == "SAFE_CONTEXT"
            ),

        "illustrative":
            sum(
                1
                for x in winners
                if x.get(
                    "class"
                )
                == "ILLUSTRATIVE"
            ),

        "misleading":
            sum(
                1
                for x in winners
                if x.get(
                    "class"
                )
                == "MISLEADING_REENACTMENT"
            ),

        "videos":
            sum(
                1
                for x in winners
                if x.get(
                    "tipo"
                )
                == "vídeo"
            ),

        "photos":
            sum(
                1
                for x in winners
                if x.get(
                    "tipo"
                )
                == "foto"
            ),

        "cta_reuse":
            any(
                bool(
                    x.get(
                        "reuse"
                    )
                )
                for x in winners
            )
    }


    report = {
        "version":
            "6.0-shadow",

        "short_id":
            short_id,

        "summary":
            summary,

        "scenes":
            scenes
    }


    path = os.path.join(
        REPORT_DIR,
        f"visual_intelligence_6_{short_id}.json"
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )


    return (
        path,
        summary
    )


# =====================================================
# SHORTAUTO PRO
# VISUAL INTELLIGENCE 6.1
# TRUTH & STORY COHERENCE OVERRIDES
# =====================================================


# =====================================================
# TERMOS NOVOS
# =====================================================

EVIDENCE_STOCK_TERMS_6_1 = {
    "contract",
    "agreement",
    "paperwork",
    "form",
    "forms",
    "clipboard",
    "signature",
    "document",
    "documents",
    "report",
    "reports",
    "file",
    "files",
    "record",
    "records",
    "paper",
    "papers"
}


SUPERNATURAL_TERMS_6_1 = {
    "paranormal",
    "ghost",
    "apparition",
    "alien",
    "ufo",
    "monster",
    "creature",
    "humanoid",
    "supernatural",
    "fantasy",
    "fantasma",
    "alienigena",
    "alienígena",
    "monstro",
    "criatura",
    "humanoide",
    "sobrenatural"
}


FAMILY_TERMS_6_1 = {

    "ELEVATOR": {
        "elevator",
        "lift",
        "elevador"
    },

    "CORRIDOR": {
        "corridor",
        "hallway",
        "hall",
        "lobby",
        "passage",
        "corredor"
    },

    "HOTEL": {
        "hotel",
        "motel"
    },

    "CAMERA": {
        "camera",
        "cctv",
        "surveillance",
        "security camera"
    },

    "WATER_TANK": {
        "water tank",
        "tank",
        "reservoir",
        "rooftop tank"
    },

    "DOCUMENT": {
        "document",
        "report",
        "contract",
        "paper",
        "paperwork",
        "file",
        "record",
        "autopsy",
        "coroner"
    },

    "PERSON": {
        "person",
        "people",
        "woman",
        "man",
        "girl",
        "boy",
        "portrait",
        "silhouette"
    },

    "CITY": {
        "city",
        "street",
        "skyline",
        "downtown",
        "avenue"
    },

    "LAB": {
        "laboratory",
        "lab",
        "test tube",
        "microscope",
        "chemistry"
    },

    "FOREST": {
        "forest",
        "woods",
        "trees",
        "woodland"
    }
}


# =====================================================
# NAMED CONTEXT ANCHORS 6.1
# =====================================================

def extrair_ancoras_query_6_1(
    query
):

    texto = str(
        query or ""
    )


    palavras = re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        texto
    )


    ignorar = {
        "The",
        "A",
        "An",
        "Old",
        "Historic",
        "Historical",
        "Vintage",
        "Dark",
        "Mysterious",
        "Official",
        "Large",
        "Small"
    }


    grupos = []

    atual = []


    for palavra in palavras:

        primeira = (
            palavra[:1]
        )


        capitalizada = (
            primeira
            and primeira.isalpha()
            and primeira
            == primeira.upper()
        )


        if (
            capitalizada
            and palavra not in ignorar
        ):

            atual.append(
                palavra
            )

        else:

            if len(
                atual
            ) >= 2:

                grupos.append(
                    " ".join(
                        atual
                    )
                )

            atual = []


    if len(
        atual
    ) >= 2:

        grupos.append(
            " ".join(
                atual
            )
        )


    saida = []
    vistos = set()


    for grupo in grupos:

        chave = normalizar(
            grupo
        )


        if chave in vistos:
            continue


        vistos.add(
            chave
        )

        saida.append(
            grupo
        )


    return saida


def named_context_match_6_1(
    candidato,
    query
):

    anchors = extrair_ancoras_query_6_1(
        query
    )


    if not anchors:

        return {
            "anchors":
                [],

            "matched":
                [],

            "ratio":
                1.0,

            "ok":
                True
        }


    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )


    desc_tokens = tokens(
        desc
    )


    matched = []


    for anchor in anchors:

        at = tokens(
            anchor
        )


        if (
            at
            and at.issubset(
                desc_tokens
            )
        ):

            matched.append(
                anchor
            )


    ratio = (
        len(
            matched
        )
        / len(
            anchors
        )
    )


    return {
        "anchors":
            anchors,

        "matched":
            matched,

        "ratio":
            ratio,

        "ok":
            ratio >= 1.0
    }


# =====================================================
# CONCEPT FAMILY 6.1
# =====================================================

def concept_family_6_1(
    descricao
):

    texto = normalizar(
        descricao
    )


    melhor = "OTHER"
    melhor_hits = 0


    for family, terms in (
        FAMILY_TERMS_6_1.items()
    ):

        hits = sum(
            1
            for termo in terms
            if normalizar(
                termo
            ) in texto
        )


        if hits > melhor_hits:

            melhor = family
            melhor_hits = hits


    return melhor


# =====================================================
# REPRESENTATIONAL SAFETY 6.1
# =====================================================

def risco_representacional(
    candidato,
    intent,
    query,
    segmento,
    visual_mode
):

    fonte = str(
        candidato.get(
            "fonte",
            ""
        )
    )


    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )


    narrativa = (
        str(
            query
        )
        + " "
        + str(
            segmento
        )
    )


    evidence = str(
        candidato.get(
            "evidence_class",
            ""
        )
    )


    tier = str(
        candidato.get(
            "wiki_query_tier",
            ""
        )
    )


    # =================================
    # DOCUMENTÁRIO WIKIMEDIA
    # =================================

    if (
        fonte == "Wikimedia"
        and evidence
        in DOCUMENTARY_CLASSES
    ):

        named = named_context_match_6_1(
            candidato,
            query
        )


        # ---------------------------------
        # CONTEXT simples não pode alegar
        # local específico se a query possui
        # um local/nome composto e o metadata
        # não contém essa âncora.
        #
        # Exemplo:
        # Los Angeles -> Seattle = bloqueado.
        # ---------------------------------

        if (
            intent == "LOCATION"
            and tier
            in {
                "CONTEXT",
                "CONTEXT_VISUAL"
            }
            and named[
                "anchors"
            ]
            and not named[
                "ok"
            ]
        ):

            return {
                "class":
                    "MISLEADING_REENACTMENT",

                "risk":
                    "HIGH",

                "penalty":
                    -220.0,

                "blocked":
                    True,

                "reason":
                    "named_context_conflict"
            }


        return {
            "class":
                "REAL_DOCUMENTARY",

            "risk":
                "LOW",

            "penalty":
                0.0,

            "blocked":
                False,

            "reason":
                "verified_documentary_context"
        }


    # =================================
    # CTA
    # =================================

    if intent == "CTA":

        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -50.0,

            "blocked":
                False,

            "reason":
                "cta_should_reuse_story_visual"
        }


    # =================================
    # STOCK HUMANO
    # =================================

    if (
        fonte in SOURCE_STOCK
        and contains_any(
            desc,
            HUMAN_TERMS
        )
    ):

        if intent == "PERSON":

            return {
                "class":
                    "MISLEADING_REENACTMENT",

                "risk":
                    "HIGH",

                "penalty":
                    -180.0,

                "blocked":
                    True,

                "reason":
                    "generic_person_could_imply_real_identity"
            }


        if intent == "EVENT":

            return {
                "class":
                    "ILLUSTRATIVE",

                "risk":
                    "MEDIUM",

                "penalty":
                    -45.0,

                "blocked":
                    False,

                "reason":
                    "generic_person_is_reenactment_like"
            }


    # =================================
    # CRIATURA / ALIEN
    # =================================

    if contains_any(
        desc,
        CREATURE_TERMS
    ):

        if not contains_any(
            narrativa,
            CREATURE_TERMS
        ):

            return {
                "class":
                    "MISLEADING_REENACTMENT",

                "risk":
                    "HIGH",

                "penalty":
                    -220.0,

                "blocked":
                    True,

                "reason":
                    "creature_not_asserted_by_narrative"
            }


        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -60.0,

            "blocked":
                False,

            "reason":
                "creature_visual_is_reconstruction"
        }


    # =================================
    # MÁSCARA / HAZMAT
    # =================================

    if contains_any(
        desc,
        MASK_TERMS
    ):

        if not contains_any(
            narrativa,
            MASK_TERMS
        ):

            return {
                "class":
                    "MISLEADING_REENACTMENT",

                "risk":
                    "HIGH",

                "penalty":
                    -220.0,

                "blocked":
                    True,

                "reason":
                    "protective_equipment_not_in_narrative"
            }


    # =================================
    # EVIDÊNCIA STOCK
    # =================================

    if (
        fonte in SOURCE_STOCK
        and intent == "EVIDENCE"
    ):

        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -42.0,

            "blocked":
                False,

            "reason":
                "stock_cannot_be_case_evidence"
        }


    # =================================
    # DOCUMENTOS GENÉRICOS
    # =================================

    if (
        fonte in SOURCE_STOCK
        and contains_any(
            desc,
            EVIDENCE_STOCK_TERMS_6_1
        )
    ):

        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -30.0,

            "blocked":
                False,

            "reason":
                "generic_document_is_illustrative"
        }


    # =================================
    # SOBRENATURAL STOCK
    # =================================

    if (
        fonte in SOURCE_STOCK
        and contains_any(
            narrativa,
            SUPERNATURAL_TERMS_6_1
        )
        and contains_any(
            desc,
            SUPERNATURAL_TERMS_6_1
        )
    ):

        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -35.0,

            "blocked":
                False,

            "reason":
                "supernatural_visual_is_not_evidence"
        }


    # =================================
    # LAB
    # =================================

    if contains_any(
        desc,
        MEDICAL_LAB_TERMS
    ):

        return {
            "class":
                "ILLUSTRATIVE",

            "risk":
                "MEDIUM",

            "penalty":
                -25.0,

            "blocked":
                False,

            "reason":
                "laboratory_visual_is_symbolic"
        }


    return {
        "class":
            "SAFE_CONTEXT",

        "risk":
            "LOW",

        "penalty":
            0.0,

        "blocked":
            False,

        "reason":
            "generic_context_without_identity_claim"
    }


# =====================================================
# PROVENANCE 6.1
# =====================================================

def provenance_score(
    candidato
):

    fonte = str(
        candidato.get(
            "fonte",
            ""
        )
    )


    evidence = str(
        candidato.get(
            "evidence_class",
            ""
        )
    )


    tier = str(
        candidato.get(
            "wiki_query_tier",
            ""
        )
    )


    if (
        fonte == "Wikimedia"
        and evidence == "CASE_DIRECT"
    ):

        return 100.0


    if (
        fonte == "Wikimedia"
        and evidence == "CONTEXTUAL"
    ):

        base = {
            "CASE":
                94.0,

            "CASE_VISUAL":
                91.0,

            "CONTEXT_COMBINED":
                96.0,

            "CONTEXT":
                48.0,

            "CONTEXT_VISUAL":
                42.0,

            "GENERIC":
                20.0
        }.get(
            tier,
            35.0
        )


        anchor = float(
            candidato.get(
                "wiki_anchor_ratio",
                0.0
            )
            or 0.0
        )


        return min(
            100.0,
            base
            + anchor * 4.0
        )


    return 25.0


# =====================================================
# CONTINUITY 6.1
# =====================================================

def continuity_score(
    candidato,
    history
):

    if not history:
        return 85.0


    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )


    family = concept_family_6_1(
        desc
    )


    anterior = history[
        -1
    ]


    family_ant = (
        anterior.get(
            "_vi6_family"
        )
        or concept_family_6_1(
            anterior.get(
                "descricao",
                ""
            )
        )
    )


    if (
        family != "OTHER"
        and family == family_ant
    ):

        return 48.0


    sim = similarity(
        desc,
        anterior.get(
            "descricao",
            ""
        )
    )


    if sim >= 0.70:
        return 25.0

    if sim >= 0.50:
        return 45.0

    if sim >= 0.30:
        return 67.0


    return 90.0


# =====================================================
# GLOBAL DIVERSITY 6.1
# =====================================================

def diversity_score(
    candidato,
    history
):

    if not history:
        return 90.0


    desc = str(
        candidato.get(
            "descricao",
            ""
        )
    )


    family = concept_family_6_1(
        desc
    )


    family_count = sum(
        1
        for item in history
        if (
            item.get(
                "_vi6_family"
            )
            or concept_family_6_1(
                item.get(
                    "descricao",
                    ""
                )
            )
        )
        == family
        and family != "OTHER"
    )


    if family_count >= 3:
        family_score = 20.0

    elif family_count == 2:
        family_score = 42.0

    elif family_count == 1:
        family_score = 68.0

    else:
        family_score = 94.0


    max_sim = 0.0


    for item in history:

        max_sim = max(
            max_sim,
            similarity(
                desc,
                item.get(
                    "descricao",
                    ""
                )
            )
        )


    if max_sim >= 0.75:
        lexical = 20.0

    elif max_sim >= 0.55:
        lexical = 45.0

    elif max_sim >= 0.35:
        lexical = 68.0

    else:
        lexical = 94.0


    return min(
        family_score,
        lexical
    )


# =====================================================
# CANDIDATE SCORE 6.1
# =====================================================

def avaliar_candidato(
    candidato,
    intent,
    query,
    segmento,
    visual_mode,
    must_have,
    history,
    videos_total,
    video_meta
):

    safety = risco_representacional(
        candidato,
        intent,
        query,
        segmento,
        visual_mode
    )


    semantic = semantic_score(
        candidato,
        query,
        segmento,
        must_have
    )


    provenance = provenance_score(
        candidato
    )


    continuity = continuity_score(
        candidato,
        history
    )


    diversity = diversity_score(
        candidato,
        history
    )


    motion = motion_score(
        candidato,
        videos_total,
        video_meta
    )


    named = named_context_match_6_1(
        candidato,
        query
    )


    named_score = (
        100.0
        if named[
            "ok"
        ]
        else (
            30.0
            if named[
                "anchors"
            ]
            else 75.0
        )
    )


    total = (
        semantic * 0.36
        + provenance * 0.24
        + continuity * 0.11
        + diversity * 0.11
        + motion * 0.08
        + named_score * 0.10
        + float(
            safety.get(
                "penalty",
                0.0
            )
        )
    )


    if safety.get(
        "blocked",
        False
    ):

        total -= 300.0


    return {
        "candidate":
            candidato,

        "class":
            safety[
                "class"
            ],

        "risk":
            safety[
                "risk"
            ],

        "reason":
            safety[
                "reason"
            ],

        "blocked":
            bool(
                safety.get(
                    "blocked",
                    False
                )
            ),

        "semantic":
            round(
                semantic,
                2
            ),

        "provenance":
            round(
                provenance,
                2
            ),

        "continuity":
            round(
                continuity,
                2
            ),

        "diversity":
            round(
                diversity,
                2
            ),

        "motion":
            round(
                motion,
                2
            ),

        "named_context":
            round(
                named[
                    "ratio"
                ],
                2
            ),

        "family":
            concept_family_6_1(
                candidato.get(
                    "descricao",
                    ""
                )
            ),

        "score":
            round(
                total,
                2
            )
    }


# =====================================================
# SERIALIZATION 6.1
# =====================================================

def serializar_avaliacao(
    item
):

    if not item:
        return None


    candidato = item[
        "candidate"
    ]


    return {
        "fonte":
            candidato.get(
                "fonte"
            ),

        "tipo":
            candidato.get(
                "tipo"
            ),

        "id":
            str(
                candidato.get(
                    "id",
                    ""
                )
            ),

        "url":
            candidato.get(
                "url"
            ),

        "descricao":
            str(
                candidato.get(
                    "descricao",
                    ""
                )
            )[:700],

        "class":
            item[
                "class"
            ],

        "risk":
            item[
                "risk"
            ],

        "reason":
            item[
                "reason"
            ],

        "blocked":
            item.get(
                "blocked",
                False
            ),

        "semantic":
            item[
                "semantic"
            ],

        "provenance":
            item[
                "provenance"
            ],

        "continuity":
            item[
                "continuity"
            ],

        "diversity":
            item[
                "diversity"
            ],

        "motion":
            item[
                "motion"
            ],

        "named_context":
            item.get(
                "named_context",
                1.0
            ),

        "family":
            item.get(
                "family",
                "OTHER"
            ),

        "score":
            item[
                "score"
            ],

        "reuse":
            bool(
                candidato.get(
                    "_vi6_reuse"
                )
            ),

        "wiki_query_tier":
            candidato.get(
                "wiki_query_tier"
            ),

        "wiki_anchor_ratio":
            candidato.get(
                "wiki_anchor_ratio"
            ),

        "evidence_class":
            candidato.get(
                "evidence_class"
            )
    }


# =====================================================
# HISTORY 6.1
# =====================================================

def push_shadow_history(
    report_scene,
    history
):

    winner = report_scene.get(
        "winner"
    )


    if not winner:
        return


    if winner.get(
        "blocked"
    ):

        return


    history.append(
        {
            "descricao":
                winner.get(
                    "descricao",
                    ""
                ),

            "fonte":
                winner.get(
                    "fonte"
                ),

            "tipo":
                winner.get(
                    "tipo"
                ),

            "id":
                winner.get(
                    "id"
                ),

            "url":
                winner.get(
                    "url"
                ),

            "_vi6_class":
                winner.get(
                    "class"
                ),

            "_vi6_risk":
                winner.get(
                    "risk"
                ),

            "_vi6_score":
                winner.get(
                    "score"
                ),

            "_vi6_family":
                winner.get(
                    "family"
                )
        }
    )


# =====================================================
# CTA REUSE 6.1
# =====================================================

def criar_cta_reuse(
    history
):

    if not history:
        return None


    fortes = [
        x
        for x in history
        if (
            x.get(
                "_vi6_risk"
            )
            == "LOW"
            and x.get(
                "_vi6_class"
            )
            in {
                "REAL_DOCUMENTARY",
                "SAFE_CONTEXT"
            }
            and x.get(
                "url"
            )
        )
    ]


    if not fortes:

        fortes = [
            x
            for x in history
            if x.get(
                "url"
            )
        ]


    if not fortes:
        return None


    documentais = [
        x
        for x in fortes
        if x.get(
            "_vi6_class"
        )
        == "REAL_DOCUMENTARY"
    ]


    pool = (
        documentais
        if documentais
        else fortes
    )


    melhor = max(
        pool,
        key=lambda x: float(
            x.get(
                "_vi6_score",
                0.0
            )
            or 0.0
        )
    )


    novo = dict(
        melhor
    )


    novo[
        "_vi6_reuse"
    ] = True


    novo[
        "id"
    ] = (
        str(
            melhor.get(
                "id",
                ""
            )
        )
        + "_cta_reuse"
    )


    return novo


print(
    "VISUAL INTELLIGENCE 6.1 "
    "TRUTH & STORY COHERENCE LOADED"
)


# =====================================================
# VISUAL INTELLIGENCE 6.2 - END TO END VISUAL TRUTH
# =====================================================
#
# Objetivos:
#
# - impedir falso documental;
# - não escolher mídia ruim só porque é a melhor disponível;
# - manter 4-6 vídeos como faixa ideal;
# - preservar fotografia documental real;
# - impedir CTA de reutilizar mídia insegura;
# - devolver decisão ao seletor 5.x quando necessário.
# =====================================================


# Guarda implementações 6.1.
_vi61_audit_scene = audit_scene
_vi61_salvar_report = salvar_report


VI62_NORMAL_FLOOR = 55.0
VI62_CONTROLLED_FLOOR = 40.0

VI62_VIDEO_MIN = 4
VI62_VIDEO_IDEAL_MAX = 6


# =====================================================
# UTIL
# =====================================================

def _vi62_float(
    value,
    default=0.0
):

    try:
        return float(
            value
        )

    except Exception:
        return float(
            default
        )


def _vi62_int(
    value,
    default=0
):

    try:
        return int(
            value
        )

    except Exception:
        return int(
            default
        )


# =====================================================
# DOCUMENTARY TRUTH ANCHOR
# =====================================================

def documentary_truth_anchor_6_2(
    candidato
):

    fonte = str(
        candidato.get(
            "fonte",
            ""
        )
    )

    evidence = str(
        candidato.get(
            "evidence_class",
            ""
        )
    )

    tier = str(
        candidato.get(
            "wiki_query_tier",
            ""
        )
    )

    anchor = _vi62_float(
        candidato.get(
            "wiki_anchor_ratio",
            0.0
        )
    )

    topic = _vi62_float(
        candidato.get(
            "topic_overlap",
            0.0
        )
    )

    segment = _vi62_float(
        candidato.get(
            "segment_overlap",
            0.0
        )
    )


    if fonte != "Wikimedia":

        return {
            "truth_ok":
                True,

            "documentary":
                False,

            "penalty":
                0.0,

            "reason":
                "not_wikimedia"
        }


    if evidence == "CASE_DIRECT":

        return {
            "truth_ok":
                True,

            "documentary":
                True,

            "penalty":
                0.0,

            "reason":
                "case_direct_verified"
        }


    if evidence != "CONTEXTUAL":

        return {
            "truth_ok":
                False,

            "documentary":
                False,

            "penalty":
                -35.0,

            "reason":
                "wikimedia_without_documentary_evidence"
        }


    # ---------------------------------
    # CONTEXT_COMBINED
    #
    # Exemplo:
    # Hotel Cecil + Los Angeles
    #
    # Esta é a forma contextual mais
    # confiável porque exige duas âncoras.
    # ---------------------------------

    if (
        tier == "CONTEXT_COMBINED"
        and anchor >= 0.75
    ):

        return {
            "truth_ok":
                True,

            "documentary":
                True,

            "penalty":
                0.0,

            "reason":
                "combined_context_verified"
        }


    # ---------------------------------
    # CASE / CASE_VISUAL
    # ---------------------------------

    if tier in {
        "CASE",
        "CASE_VISUAL"
    }:

        if (
            anchor >= 0.75
            or topic >= 0.50
        ):

            return {
                "truth_ok":
                    True,

                "documentary":
                    True,

                "penalty":
                    0.0,

                "reason":
                    "case_anchor_verified"
            }


        return {
            "truth_ok":
                False,

            "documentary":
                False,

            "penalty":
                -60.0,

            "reason":
                "weak_case_anchor"
        }


    # ---------------------------------
    # CONTEXT sozinho NÃO é evidência
    # suficiente para chamar o arquivo
    # de REAL_DOCUMENTARY.
    #
    # Foi exatamente o que permitiu:
    #
    # São Paulo policial
    # -> REAL_DOCUMENTARY
    #
    # no teste anterior.
    # ---------------------------------

    if tier in {
        "CONTEXT",
        "CONTEXT_VISUAL"
    }:

        if topic >= 0.50:

            return {
                "truth_ok":
                    True,

                "documentary":
                    True,

                "penalty":
                    0.0,

                "reason":
                    "context_with_topic_identity"
            }


        return {
            "truth_ok":
                False,

            "documentary":
                False,

            "penalty":
                -42.0,

            "reason":
                "context_without_case_identity"
        }


    return {
        "truth_ok":
            False,

        "documentary":
            False,

        "penalty":
            -48.0,

        "reason":
            "unverified_documentary_provenance"
    }


# =====================================================
# MOTION BALANCE
# =====================================================

def motion_balance_6_2(
    candidato,
    videos_total
):

    tipo = str(
        candidato.get(
            "tipo",
            ""
        )
    )


    if tipo == "vídeo":

        if videos_total < VI62_VIDEO_MIN:

            return {
                "adjustment":
                    10.0,

                "reason":
                    "video_needed"
            }


        if videos_total < VI62_VIDEO_IDEAL_MAX:

            return {
                "adjustment":
                    4.0,

                "reason":
                    "video_inside_target"
            }


        if videos_total == VI62_VIDEO_IDEAL_MAX:

            return {
                "adjustment":
                    -10.0,

                "reason":
                    "video_target_reached"
            }


        return {
            "adjustment":
                -24.0,

            "reason":
                "video_overuse"
        }


    # Depois de muitos vídeos,
    # uma boa foto ganha leve incentivo.

    if videos_total >= VI62_VIDEO_IDEAL_MAX:

        return {
            "adjustment":
                7.0,

            "reason":
                "photo_restores_visual_balance"
        }


    return {
        "adjustment":
            0.0,

        "reason":
            "neutral_motion"
    }


# =====================================================
# SCORE 6.2
# =====================================================

def avaliar_candidato_6_2(
    candidato,
    intent,
    query,
    segmento,
    visual_mode,
    must_have,
    history,
    videos_total,
    video_meta
):

    base = avaliar_candidato(
        candidato,
        intent,
        query,
        segmento,
        visual_mode,
        must_have,
        history,
        videos_total,
        video_meta
    )


    truth = documentary_truth_anchor_6_2(
        candidato
    )

    motion_balance = motion_balance_6_2(
        candidato,
        videos_total
    )


    score = (
        _vi62_float(
            base.get(
                "score",
                -999
            ),
            -999
        )
        + _vi62_float(
            truth.get(
                "penalty",
                0
            )
        )
        + _vi62_float(
            motion_balance.get(
                "adjustment",
                0
            )
        )
    )


    classe = str(
        base.get(
            "class",
            "SAFE_CONTEXT"
        )
    )


    # ---------------------------------
    # Nunca permitir que um Wikimedia
    # contextual não confirmado continue
    # sendo REAL_DOCUMENTARY.
    # ---------------------------------

    if (
        classe == "REAL_DOCUMENTARY"
        and not truth.get(
            "documentary"
        )
    ):

        classe = "SAFE_CONTEXT"


    # ---------------------------------
    # Um candidato bloqueado pelo Safety
    # continua bloqueado.
    # ---------------------------------

    blocked = bool(
        base.get(
            "blocked",
            False
        )
    )


    risk = str(
        base.get(
            "risk",
            "LOW"
        )
    )


    if blocked:

        score -= 300


    # ---------------------------------
    # QUALITY TIER
    # ---------------------------------

    if (
        not blocked
        and risk != "HIGH"
        and score >= VI62_NORMAL_FLOOR
    ):

        quality_tier = "NORMAL"


    elif (
        not blocked
        and risk == "LOW"
        and score >= VI62_CONTROLLED_FLOOR
    ):

        quality_tier = "CONTROLLED_FALLBACK"


    else:

        quality_tier = "REJECT"


    return {
        **base,

        "class":
            classe,

        "score":
            round(
                score,
                2
            ),

        "truth_anchor":
            truth,

        "truth_ok":
            bool(
                truth.get(
                    "truth_ok",
                    False
                )
            ),

        "motion_balance":
            motion_balance,

        "quality_tier":
            quality_tier
    }


# =====================================================
# SERIALIZAÇÃO 6.2
# =====================================================

def serializar_avaliacao_6_2(
    item
):

    if not item:
        return None


    candidato = item.get(
        "candidate",
        {}
    )


    return {
        "fonte":
            candidato.get(
                "fonte"
            ),

        "tipo":
            candidato.get(
                "tipo"
            ),

        "id":
            str(
                candidato.get(
                    "id",
                    ""
                )
            ),

        "url":
            candidato.get(
                "url"
            ),

        "descricao":
            str(
                candidato.get(
                    "descricao",
                    ""
                )
            )[:900],

        "class":
            item.get(
                "class"
            ),

        "risk":
            item.get(
                "risk"
            ),

        "blocked":
            bool(
                item.get(
                    "blocked",
                    False
                )
            ),

        "reason":
            item.get(
                "reason"
            ),

        "score":
            item.get(
                "score"
            ),

        "semantic":
            item.get(
                "semantic"
            ),

        "provenance":
            item.get(
                "provenance"
            ),

        "continuity":
            item.get(
                "continuity"
            ),

        "diversity":
            item.get(
                "diversity"
            ),

        "motion":
            item.get(
                "motion"
            ),

        "family":
            item.get(
                "family"
            ),

        "named_context":
            item.get(
                "named_context"
            ),

        "truth_ok":
            item.get(
                "truth_ok"
            ),

        "truth_anchor":
            item.get(
                "truth_anchor"
            ),

        "motion_balance":
            item.get(
                "motion_balance"
            ),

        "quality_tier":
            item.get(
                "quality_tier"
            ),

        "wiki_query_tier":
            candidato.get(
                "wiki_query_tier"
            ),

        "wiki_anchor_ratio":
            candidato.get(
                "wiki_anchor_ratio"
            ),

        "evidence_class":
            candidato.get(
                "evidence_class"
            ),

        "topic_overlap":
            candidato.get(
                "topic_overlap"
            ),

        "segment_overlap":
            candidato.get(
                "segment_overlap"
            ),

        "reuse":
            bool(
                candidato.get(
                    "_vi6_reuse",
                    False
                )
            )
    }


# =====================================================
# SAFE CTA REUSE 6.2
# =====================================================

def criar_cta_reuse_6_2(
    history
):

    if not history:
        return None


    validos = [
        x
        for x in history
        if (
            not x.get(
                "_vi6_blocked",
                False
            )
            and x.get(
                "_vi6_risk"
            ) == "LOW"
            and _vi62_float(
                x.get(
                    "_vi6_score",
                    0
                )
            ) >= VI62_NORMAL_FLOOR
            and x.get(
                "url"
            )
        )
    ]


    if not validos:

        return None


    # REAL_DOCUMENTARY verdadeiro vence.
    documentais = [
        x
        for x in validos
        if (
            x.get(
                "_vi6_class"
            )
            == "REAL_DOCUMENTARY"
            and x.get(
                "_vi6_truth_ok",
                False
            )
        )
    ]


    pool = (
        documentais
        if documentais
        else validos
    )


    melhor = max(
        pool,
        key=lambda x:
            _vi62_float(
                x.get(
                    "_vi6_score",
                    0
                )
            )
    )


    winner = dict(
        melhor
    )


    winner[
        "_vi6_reuse"
    ] = True


    winner[
        "id"
    ] = (
        str(
            winner.get(
                "id",
                ""
            )
        )
        + "_cta_reuse_6_2"
    )


    return winner


# =====================================================
# HISTORY 6.2
# =====================================================

def push_shadow_history(
    report_scene,
    history
):

    winner = report_scene.get(
        "winner"
    )


    if not winner:
        return


    if winner.get(
        "blocked",
        False
    ):
        return


    history.append(
        {
            "descricao":
                winner.get(
                    "descricao",
                    ""
                ),

            "fonte":
                winner.get(
                    "fonte"
                ),

            "tipo":
                winner.get(
                    "tipo"
                ),

            "id":
                winner.get(
                    "id"
                ),

            "url":
                winner.get(
                    "url"
                ),

            "_vi6_class":
                winner.get(
                    "class"
                ),

            "_vi6_risk":
                winner.get(
                    "risk"
                ),

            "_vi6_score":
                winner.get(
                    "score"
                ),

            "_vi6_family":
                winner.get(
                    "family"
                ),

            "_vi6_truth_ok":
                winner.get(
                    "truth_ok",
                    False
                ),

            "_vi6_quality_tier":
                winner.get(
                    "quality_tier"
                ),

            "_vi6_blocked":
                winner.get(
                    "blocked",
                    False
                )
        }
    )


# =====================================================
# AUDIT SCENE 6.2
# =====================================================

def audit_scene(
    numero,
    total_scenes,
    cena,
    candidatos,
    history,
    videos_total,
    video_meta
):

    # Usa o 6.1 somente para interpretar
    # o INTENT e manter compatibilidade
    # com o restante da arquitetura.

    antigo = _vi61_audit_scene(
        numero,
        total_scenes,
        cena,
        candidatos,
        history,
        videos_total,
        video_meta
    )


    intent = str(
        antigo.get(
            "intent",
            "ATMOSPHERE"
        )
    )


    query = str(
        cena.get(
            "query",
            ""
        )
    )


    segmento = str(
        cena.get(
            "segment",
            ""
        )
    )


    visual_mode = str(
        cena.get(
            "visual_mode",
            ""
        )
    )


    must_have = list(
        cena.get(
            "must_have",
            []
        )
        or []
    )


    # =================================
    # CTA
    # =================================

    if intent == "CTA":

        reuse = criar_cta_reuse_6_2(
            history
        )


        if reuse:

            winner = {
                "fonte":
                    reuse.get(
                        "fonte"
                    ),

                "tipo":
                    reuse.get(
                        "tipo"
                    ),

                "id":
                    reuse.get(
                        "id"
                    ),

                "url":
                    reuse.get(
                        "url"
                    ),

                "descricao":
                    reuse.get(
                        "descricao"
                    ),

                "class":
                    reuse.get(
                        "_vi6_class",
                        "SAFE_CONTEXT"
                    ),

                "risk":
                    "LOW",

                "blocked":
                    False,

                "reason":
                    "cta_reuses_verified_story_visual",

                "score":
                    reuse.get(
                        "_vi6_score",
                        55.0
                    ),

                "semantic":
                    55.0,

                "provenance":
                    (
                        95.0
                        if reuse.get(
                            "_vi6_class"
                        )
                        == "REAL_DOCUMENTARY"
                        else 35.0
                    ),

                "continuity":
                    90.0,

                "diversity":
                    15.0,

                "motion":
                    (
                        85.0
                        if reuse.get(
                            "tipo"
                        )
                        == "vídeo"
                        else 55.0
                    ),

                "family":
                    reuse.get(
                        "_vi6_family",
                        "OTHER"
                    ),

                "truth_ok":
                    reuse.get(
                        "_vi6_truth_ok",
                        True
                    ),

                "quality_tier":
                    "NORMAL",

                "reuse":
                    True
            }


            antigo[
                "winner"
            ] = winner

            antigo[
                "top"
            ] = [
                winner
            ]

            antigo[
                "fallback_to_5x"
            ] = False

            antigo[
                "vi_version"
            ] = "6.2"

            return antigo


    # =================================
    # RE-SCORE DE TODO O POOL
    # =================================

    avaliados = []


    for candidato in candidatos:

        try:

            item = avaliar_candidato_6_2(
                candidato,
                intent,
                query,
                segmento,
                visual_mode,
                must_have,
                history,
                videos_total,
                video_meta
            )

        except Exception:

            continue


        avaliados.append(
            item
        )


    avaliados.sort(
        key=lambda x:
            _vi62_float(
                x.get(
                    "score",
                    -999
                ),
                -999
            ),
        reverse=True
    )


    normais = [
        x
        for x in avaliados
        if x.get(
            "quality_tier"
        ) == "NORMAL"
    ]


    controlados = [
        x
        for x in avaliados
        if x.get(
            "quality_tier"
        ) == "CONTROLLED_FALLBACK"
    ]


    if normais:

        escolhido = normais[0]
        fallback = False
        decision = "NORMAL"


    elif controlados:

        escolhido = controlados[0]
        fallback = False
        decision = "CONTROLLED_FALLBACK"


    else:

        escolhido = None
        fallback = True
        decision = "FALLBACK_TO_5X"


    top_serializado = [
        serializar_avaliacao_6_2(
            x
        )
        for x in avaliados[:5]
    ]


    winner_serializado = (
        serializar_avaliacao_6_2(
            escolhido
        )
        if escolhido
        else None
    )


    antigo[
        "winner"
    ] = winner_serializado


    antigo[
        "top"
    ] = top_serializado


    antigo[
        "fallback_to_5x"
    ] = fallback


    antigo[
        "decision"
    ] = decision


    antigo[
        "quality_floor"
    ] = {
        "normal":
            VI62_NORMAL_FLOOR,

        "controlled":
            VI62_CONTROLLED_FLOOR
    }


    antigo[
        "motion_target"
    ] = {
        "min":
            VI62_VIDEO_MIN,

        "max":
            VI62_VIDEO_IDEAL_MAX,

        "videos_before_scene":
            videos_total
    }


    antigo[
        "vi_version"
    ] = "6.2"


    return antigo


# =====================================================
# REPORT 6.2
# =====================================================

def salvar_report(
    short_id,
    scenes
):

    path, summary = (
        _vi61_salvar_report(
            short_id,
            scenes
        )
    )


    normal = 0
    controlled = 0
    fallback = 0
    truth_fail = 0

    videos = 0
    photos = 0


    for scene in scenes:

        if scene.get(
            "fallback_to_5x"
        ):

            fallback += 1


        winner = scene.get(
            "winner"
        ) or {}


        tier = winner.get(
            "quality_tier"
        )


        if tier == "NORMAL":
            normal += 1

        elif tier == "CONTROLLED_FALLBACK":
            controlled += 1


        if (
            winner
            and winner.get(
                "truth_ok"
            ) is False
            and winner.get(
                "fonte"
            )
            == "Wikimedia"
        ):

            truth_fail += 1


        if winner.get(
            "tipo"
        ) == "vídeo":
            videos += 1

        elif winner.get(
            "tipo"
        ) == "foto":
            photos += 1


    summary[
        "vi_version"
    ] = "6.2"


    summary[
        "quality_normal"
    ] = normal


    summary[
        "quality_controlled"
    ] = controlled


    summary[
        "fallback_to_5x"
    ] = fallback


    summary[
        "truth_anchor_failures"
    ] = truth_fail


    summary[
        "videos_6_2"
    ] = videos


    summary[
        "photos_6_2"
    ] = photos


    summary[
        "motion_target_ok"
    ] = (
        VI62_VIDEO_MIN
        <= videos
        <= VI62_VIDEO_IDEAL_MAX
    )


    # Atualiza relatório já criado pelo 6.1.

    try:

        import json

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            report = json.load(
                f
            )


        report[
            "summary"
        ] = summary


        report[
            "vi_version"
        ] = "6.2"


        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                report,
                f,
                ensure_ascii=False,
                indent=2
            )

    except Exception:
        pass


    return (
        path,
        summary
    )


print(
    "VISUAL INTELLIGENCE 6.2 "
    "END TO END VISUAL TRUTH LOADED"
)
