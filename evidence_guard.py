#!/usr/bin/env python3

import re
import unicodedata


# =====================================================
# SHORTAUTO PRO
# DOCUMENTARY PRECISION GUARD 5.3
# =====================================================
#
# Objetivo:
#
# Wikimedia NÃO recebe prioridade só por ser Wikimedia.
#
# CASE_DIRECT:
#   mídia realmente ligada ao assunto/caso.
#
# CONTEXTUAL:
#   mídia não diretamente do caso, mas com
#   ligação comprovável ao segmento narrado.
#
# GENERIC_DOCUMENT:
#   documento genérico. Não entra no pool.
#
# GENERIC:
#   Wikimedia genérica. Não entra no pool.
#
# RISKY_IDENTITY:
#   pessoa genérica que poderia ser confundida
#   com uma pessoa real do caso.
# =====================================================


STOP = {

    # inglês
    "the", "a", "an",
    "of", "in", "on",
    "at", "with", "and",
    "or", "to", "for",
    "from", "by",

    "case",
    "mystery",
    "incident",
    "disappearance",
    "missing",
    "death",
    "murder",
    "crime",

    "historic",
    "historical",
    "vintage",
    "archive",
    "archival",

    "cinematic",
    "dramatic",

    "photo",
    "image",
    "picture",
    "view",
    "scene",
    "shot",

    # português
    "o", "a", "os", "as",
    "um", "uma",
    "de", "da", "do",
    "das", "dos",
    "em", "no", "na",
    "nos", "nas",
    "com", "sem",
    "para", "por",
    "e", "ou",

    "caso",
    "misterio",
    "mistério",
    "incidente",
    "desaparecimento",
    "desaparecido",
    "desaparecida",
    "morte",
    "assassinato",
    "crime",

    # termos genéricos de tópico
    "flight",
    "voo"
}


IDENTITY_TERMS = {
    "portrait",
    "photograph",
    "person",
    "man",
    "woman",
    "family",
    "children",
    "child",
    "girl",
    "boy",
    "student",
    "tourist"
}


DOCUMENT_TERMS = {
    "report",
    "document",
    "file",
    "newspaper",
    "archive",
    "record",
    "letter",
    "map",
    "investigation",
    "certificate",
    "register",
    "paper",
    "papers",
    "folder",
    "coroner",
    "autopsy"
}


CONTEXT_MODES = {
    "location",
    "architecture",
    "transport",
    "map_context",
    "environment"
}

# Wikimedia can safely be used as illustrative context in these modes when
# the asset metadata itself proves the requested visual concept. This is
# intentionally narrower than CONTEXT_MODES: locations, transport, maps and
# architecture can imply a specific factual place/object and remain strict.
ILLUSTRATIVE_CONTEXT_MODES = {
    "environment",
    "object",
    "abstract_context",
}


DOCUMENT_MODES = {
    "document",
    "evidence"
}


# =====================================================
# NORMALIZAÇÃO
# =====================================================

def normalizar(texto):

    texto = str(
        texto or ""
    )

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        c
        for c in texto
        if not unicodedata.combining(c)
    )

    return texto.lower()


def tokens(texto):

    return {
        x
        for x in re.findall(
            r"[a-z0-9]+",
            normalizar(texto)
        )
        if (
            x not in STOP
            and len(x) >= 3
        )
    }


# =====================================================
# TEXTO REAL DO CANDIDATO
# =====================================================
#
# Importante:
# NÃO usamos wiki_query / query de busca aqui.
#
# A query pode conter o nome do caso e produziria
# uma falsa prova de identidade.
# =====================================================

def texto_candidato(
    candidato
):

    campos = [
        "descricao",
        "titulo",
        "title",
        "name",
        "page_title",
        "wiki_title",
        "caption"
    ]

    partes = []

    for campo in campos:

        valor = candidato.get(
            campo
        )

        if valor:

            partes.append(
                str(valor)
            )


    return " ".join(
        partes
    )


# =====================================================
# MÉTRICAS DE SOBREPOSIÇÃO
# =====================================================

def overlap(
    origem,
    destino
):

    a = tokens(
        origem
    )

    b = tokens(
        destino
    )

    if not a:
        return 0.0

    return (
        len(
            a.intersection(b)
        )
        / len(a)
    )


def shared_stats(
    origem,
    destino
):

    a = tokens(
        origem
    )

    b = tokens(
        destino
    )

    if not a:

        return {
            "hits": 0,
            "total": 0,
            "coverage": 0.0
        }


    hits = len(
        a.intersection(b)
    )


    return {
        "hits":
            hits,

        "total":
            len(a),

        "coverage":
            hits / len(a)
    }


# =====================================================
# IDENTIDADE DO CASO
# =====================================================

def topic_identity_stats(
    assunto,
    descricao
):

    assunto_tokens = tokens(
        assunto
    )

    desc_tokens = tokens(
        descricao
    )


    total = len(
        assunto_tokens
    )


    if total == 0:

        return {
            "hits": 0,
            "required": 999,
            "coverage": 0.0,
            "direct": False
        }


    hits = len(
        assunto_tokens.intersection(
            desc_tokens
        )
    )


    if total == 1:

        required = 1

    else:

        # Aproximadamente 2/3 dos termos
        # específicos do assunto.
        #
        # 2 termos -> exige 2
        # 3 termos -> exige 2
        # 4 termos -> exige 3
        required = max(
            2,
            (
                2 * total
                + 2
            ) // 3
        )


    coverage = (
        hits
        / total
    )


    return {
        "hits":
            hits,

        "required":
            required,

        "coverage":
            coverage,

        "direct":
            hits >= required
    }


# =====================================================
# MUST COVERAGE
# =====================================================

def must_coverage(
    descricao,
    must_have
):

    if not must_have:
        return 1.0


    desc = tokens(
        descricao
    )


    hits = 0
    validos = 0


    for termo in must_have:

        tt = tokens(
            termo
        )


        if not tt:
            continue


        validos += 1


        cobertura = (
            len(
                tt.intersection(
                    desc
                )
            )
            / len(tt)
        )


        if cobertura >= 0.60:

            hits += 1


    if validos == 0:
        return 1.0


    return (
        hits
        / validos
    )


# =====================================================
# TIPOS VISUAIS
# =====================================================

def possui_identidade_visual(
    descricao
):

    desc = tokens(
        descricao
    )

    return bool(
        desc.intersection(
            IDENTITY_TERMS
        )
    )


def possui_documento(
    descricao
):

    desc = tokens(
        descricao
    )

    return bool(
        desc.intersection(
            DOCUMENT_TERMS
        )
    )


# =====================================================
# RETORNO PADRÃO
# =====================================================

def resultado(
    classe,
    bonus,
    allowed,
    topic_overlap,
    segment_overlap,
    cobertura_must,
    reason,
    topic_hits=0,
    topic_required=0,
    segment_hits=0
):

    return {
        "class":
            classe,

        "bonus":
            float(
                bonus
            ),

        "allowed":
            bool(
                allowed
            ),

        "topic_overlap":
            float(
                topic_overlap
            ),

        "segment_overlap":
            float(
                segment_overlap
            ),

        "must_coverage":
            float(
                cobertura_must
            ),

        "reason":
            reason,

        "topic_anchor_hits":
            int(
                topic_hits
            ),

        "topic_anchor_required":
            int(
                topic_required
            ),

        "segment_anchor_hits":
            int(
                segment_hits
            )
    }


# =====================================================
# EVIDENCE AUTHENTICITY
# =====================================================

def avaliar_evidencia(
    candidato,
    assunto,
    segmento,
    must_have,
    visual_mode
):

    fonte = str(
        candidato.get(
            "fonte",
            ""
        )
    )


    # =================================================
    # STOCK
    # =================================================

    if fonte != "Wikimedia":

        return resultado(
            "STOCK",
            0.0,
            True,
            0.0,
            0.0,
            0.0,
            "stock_source"
        )


    descricao = texto_candidato(
        candidato
    )


    topic = topic_identity_stats(
        assunto,
        descricao
    )


    topic_overlap = topic[
        "coverage"
    ]


    seg = shared_stats(
        segmento,
        descricao
    )


    segment_overlap = seg[
        "coverage"
    ]


    cobertura_must = must_coverage(
        descricao,
        must_have
    )


    mode = str(
        visual_mode or ""
    ).lower()


    # =================================================
    # IDENTIDADE HUMANA ARRISCADA
    # =================================================
    #
    # Uma foto de uma pessoa aleatória não pode
    # representar uma pessoa real do caso.
    # =================================================

    if (
        mode == "human_context"
        and possui_identidade_visual(
            descricao
        )
        and not topic[
            "direct"
        ]
    ):

        return resultado(
            "RISKY_IDENTITY",
            -999.0,
            False,
            topic_overlap,
            segment_overlap,
            cobertura_must,
            "generic_person_could_imply_case_identity",
            topic[
                "hits"
            ],
            topic[
                "required"
            ],
            seg[
                "hits"
            ]
        )


    # =================================================
    # CASE DIRECT
    # =================================================
    #
    # O próprio metadata do arquivo precisa conter
    # identidade suficiente do assunto.
    #
    # Não basta a QUERY ter o nome do caso.
    # =================================================

    if topic[
        "direct"
    ]:

        bonus = 90.0


        if cobertura_must >= 0.50:

            bonus += 25.0


        if segment_overlap >= 0.15:

            bonus += 10.0


        return resultado(
            "CASE_DIRECT",
            bonus,
            True,
            topic_overlap,
            segment_overlap,
            cobertura_must,
            "case_identity_present_in_asset_metadata",
            topic[
                "hits"
            ],
            topic[
                "required"
            ],
            seg[
                "hits"
            ]
        )


    # =================================================
    # CONTEXTUAL
    # =================================================
    #
    # Agora visual_mode sozinho NÃO é suficiente.
    #
    # É necessário:
    #
    # - cobertura visual do MUST
    # - E uma âncora textual real do segmento
    #   ou parte específica do assunto.
    # =================================================

    partial_topic = (
        topic[
            "hits"
        ] >= 1
        and topic_overlap >= 0.34
    )


    segment_context = (
        seg[
            "hits"
        ] >= 1
        and segment_overlap >= 0.15
    )


    strong_segment_context = (
        seg[
            "hits"
        ] >= 2
        and segment_overlap >= 0.20
    )


    # ---------------------------------
    # LOCAL / ARQUITETURA / MAPA
    # ---------------------------------

    if (
        mode in CONTEXT_MODES
        and cobertura_must >= 0.50
        and (
            segment_context
            or partial_topic
        )
    ):

        bonus = 24.0


        if strong_segment_context:

            bonus += 8.0


        if partial_topic:

            bonus += 8.0


        return resultado(
            "CONTEXTUAL",
            bonus,
            True,
            topic_overlap,
            segment_overlap,
            cobertura_must,
            "contextual_asset_with_real_narrative_anchor",
            topic[
                "hits"
            ],
            topic[
                "required"
            ],
            seg[
                "hits"
            ]
        )


    # ---------------------------------
    # DOCUMENTO / EVIDÊNCIA
    # ---------------------------------

    if (
        mode in DOCUMENT_MODES
        and cobertura_must >= 0.50
        and (
            strong_segment_context
            or partial_topic
        )
    ):

        bonus = 28.0


        if possui_documento(
            descricao
        ):

            bonus += 6.0


        return resultado(
            "CONTEXTUAL",
            bonus,
            True,
            topic_overlap,
            segment_overlap,
            cobertura_must,
            "document_has_case_or_segment_context",
            topic[
                "hits"
            ],
            topic[
                "required"
            ],
            seg[
                "hits"
            ]
        )


    # =================================================
    # SAFE ILLUSTRATIVE CONTEXT
    # =================================================
    #
    # Stock-first scenes must still be able to use the keyless Wikimedia
    # engine when paid/keyed stock providers are unavailable or empty.
    # We allow this only for non-identity illustrative modes, and only when
    # the asset metadata itself proves the requested visual concept.
    # The search query is never accepted as evidence by itself.
    # =================================================

    if mode in ILLUSTRATIVE_CONTEXT_MODES:

        try:
            wiki_query_overlap = float(
                candidato.get(
                    "wiki_query_overlap",
                    0.0
                )
                or 0.0
            )
        except (TypeError, ValueError):
            wiki_query_overlap = 0.0

        wiki_anchor_ok = bool(
            candidato.get(
                "wiki_anchor_ok",
                False
            )
        )

        metadata_proves_visual = (
            cobertura_must >= 1.0
            or (
                cobertura_must >= 0.50
                and wiki_anchor_ok
            )
            or (
                not must_have
                and wiki_anchor_ok
                and wiki_query_overlap >= 0.45
            )
        )

        if metadata_proves_visual:

            bonus = 12.0

            if cobertura_must >= 1.0:
                bonus += 8.0

            if wiki_anchor_ok:
                bonus += 5.0

            return resultado(
                "ILLUSTRATIVE_CONTEXT",
                bonus,
                True,
                topic_overlap,
                segment_overlap,
                cobertura_must,
                "generic_wikimedia_metadata_proves_visual_context",
                topic[
                    "hits"
                ],
                topic[
                    "required"
                ],
                seg[
                    "hits"
                ]
            )


    # =================================================
    # GENERIC DOCUMENT
    # =================================================
    #
    # Pode ser visualmente um documento,
    # mas não temos base para chamá-lo de
    # documento relacionado à história.
    #
    # Portanto NÃO entra no pool Wikimedia.
    # =================================================

    if (
        mode in DOCUMENT_MODES
        and possui_documento(
            descricao
        )
    ):

        return resultado(
            "GENERIC_DOCUMENT",
            -80.0,
            False,
            topic_overlap,
            segment_overlap,
            cobertura_must,
            "generic_document_without_case_anchor",
            topic[
                "hits"
            ],
            topic[
                "required"
            ],
            seg[
                "hits"
            ]
        )


    # =================================================
    # GENERIC WIKIMEDIA
    # =================================================

    return resultado(
        "GENERIC",
        -100.0,
        False,
        topic_overlap,
        segment_overlap,
        cobertura_must,
        "wikimedia_asset_without_case_or_context_anchor",
        topic[
            "hits"
        ],
        topic[
            "required"
        ],
        seg[
            "hits"
        ]
    )
