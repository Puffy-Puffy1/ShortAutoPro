#!/usr/bin/env python3

import os
import re
import html
import tempfile
import time
import requests

from media_resilience import (
    cache_query_result,
    get_cached_query,
    provider_allowed,
    record_provider_result,
)
from wikimedia_query_bridge import (
    gerar_buscas_commons,
    gerar_buscas_commons_ancoradas
)


# =====================================================
# SHORTAUTO PRO
# WIKIMEDIA EVIDENCE SOURCE 3.5
# =====================================================

API = "https://commons.wikimedia.org/w/api.php"

WIKIMEDIA_CONTACT = str(
    os.getenv(
        "SAP_WIKIMEDIA_CONTACT",
        "https://github.com/Puffy-Puffy1",
    )
    or "https://github.com/Puffy-Puffy1"
).strip()

HEADERS = {
    "User-Agent":
        "ShortAutoPro/3.5 "
        f"(documentary-media-research; {WIKIMEDIA_CONTACT})"
}

try:
    TIMEOUT = float(os.getenv("SAP_WIKIMEDIA_TIMEOUT", "10") or 10)
except (TypeError, ValueError):
    TIMEOUT = 10.0

TIMEOUT = max(4.0, min(TIMEOUT, 30.0))

try:
    SEARCH_DEADLINE = float(
        os.getenv("SAP_WIKIMEDIA_SEARCH_DEADLINE", "8") or 8
    )
except (TypeError, ValueError):
    SEARCH_DEADLINE = 8.0

SEARCH_DEADLINE = max(5.0, min(SEARCH_DEADLINE, 20.0))

BASE = os.path.abspath(
    os.path.expanduser(
        os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro")
    )
)

CREDIT_DIR = os.path.join(
    BASE,
    "credits"
)

os.makedirs(
    CREDIT_DIR,
    exist_ok=True
)


# =====================================================
# TEXTO
# =====================================================

STOP = {
    "the", "a", "an", "of", "in", "on",
    "at", "with", "and", "or", "to",
    "for", "from", "by",

    "cinematic",
    "dramatic",
    "dark",
    "moody",
    "shot",
    "view",
    "scene",
    "vintage",
    "historic",
    "historical",
    "archive",
    "archival"
}


def limpar_html(texto):

    texto = html.unescape(
        str(texto or "")
    )

    texto = re.sub(
        r"<[^>]+>",
        " ",
        texto
    )

    return " ".join(
        texto.split()
    )


def tokens(texto):

    return {
        x
        for x in re.findall(
            r"[a-z0-9]+",
            str(texto).lower()
        )
        if (
            x not in STOP
            and len(x) >= 2
        )
    }


def termo_presente(
    descricao,
    termo
):

    tt = tokens(
        termo
    )

    dt = tokens(
        descricao
    )

    if not tt:
        return False

    hits = len(
        tt.intersection(
            dt
        )
    )

    return (
        hits
        / len(tt)
    ) >= 0.60


# =====================================================
# LICENÇA
# =====================================================

def licencia_livre(ext):

    nome = limpar_html(
        ext.get(
            "LicenseShortName",
            {}
        ).get(
            "value",
            ""
        )
    ).lower()

    uso = limpar_html(
        ext.get(
            "UsageTerms",
            {}
        ).get(
            "value",
            ""
        )
    ).lower()

    texto = (
        nome
        + " "
        + uso
    )

    permitidas = [
        "cc by",
        "cc-by",
        "cc by-sa",
        "cc-by-sa",
        "cc0",
        "public domain",
        "public-domain",
        "pd",
        "gfdl"
    ]

    proibidas = [
        "non-commercial",
        "noncommercial",
        "nc only",
        "no derivatives",
        "nd only"
    ]

    if any(
        x in texto
        for x in proibidas
    ):
        return False

    return any(
        x in texto
        for x in permitidas
    )


# =====================================================
# BUSCAS MAIS INTELIGENTES
# =====================================================

def limpar_query(texto):

    toks = [
        x
        for x in re.findall(
            r"[A-Za-zÀ-ÿ0-9'-]+",
            str(texto)
        )
        if x.lower() not in STOP
    ]

    return " ".join(
        toks[:7]
    )


def gerar_queries(
    busca,
    assunto,
    segmento,
    visual_mode
):

    candidatos = []

    assunto = str(
        assunto
    ).strip()

    busca = str(
        busca
    ).strip()

    segmento = str(
        segmento
    ).strip()


    # 1. Nome real do assunto
    if assunto:

        candidatos.append(
            limpar_query(
                assunto
            )
        )


    # 2. Nome + conceito principal
    if assunto and busca:

        busca_curta = limpar_query(
            busca
        )

        if busca_curta:

            candidatos.append(
                limpar_query(
                    assunto
                    + " "
                    + busca_curta
                )
            )


    # 3. Busca visual sem o assunto
    if busca:

        candidatos.append(
            limpar_query(
                busca
            )
        )


    # 4. Trecho narrativo
    if segmento:

        candidatos.append(
            limpar_query(
                segmento
            )
        )


    # 5. Para documentos/local/mapa,
    # tenta o assunto puro novamente.
    if (
        assunto
        and visual_mode in {
            "document",
            "evidence",
            "location",
            "architecture",
            "transport",
            "map_context"
        }
    ):

        candidatos.append(
            assunto
        )


    saida = []

    for q in candidatos:

        q = " ".join(
            str(q).split()
        )

        if (
            q
            and q.lower()
            not in [
                x.lower()
                for x in saida
            ]
        ):
            saida.append(
                q
            )

    return saida[:5]


# =====================================================
# CONSULTA COMMONS
# =====================================================

def consultar_commons(
    query,
    limite
):
    cache_payload = {
        "query": " ".join(str(query or "").split()),
        "limit": int(limite or 0),
        "props": "url|size|mime|extmetadata",
        "thumb_width": 1200,
    }

    cached, cache_state = get_cached_query(
        "wikimedia",
        cache_payload,
        allow_stale=False,
    )
    if cached is not None:
        print(
            "SAP_WIKIMEDIA_QUERY_CACHE="
            f"{cache_state} query={cache_payload['query'][:80]}"
        )
        return cached

    allowed, circuit_reason = provider_allowed("wikimedia")
    if not allowed:
        stale, stale_state = get_cached_query(
            "wikimedia",
            cache_payload,
            allow_stale=True,
        )
        print(
            "SAP_WIKIMEDIA_CIRCUIT=OPEN "
            f"reason={circuit_reason} cache={stale_state}"
        )
        return stale or []

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limite,
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": 1200,
        "format": "json",
        "formatversion": 2,
    }

    r = None
    for attempt in range(2):
        try:
            r = requests.get(
                API,
                headers=HEADERS,
                params=params,
                timeout=(min(4.0, TIMEOUT), min(TIMEOUT, 8.0)),
            )
        except requests.Timeout:
            record_provider_result(
                "wikimedia",
                ok=False,
                reason="timeout",
            )
            if attempt == 0:
                continue
            stale, stale_state = get_cached_query(
                "wikimedia",
                cache_payload,
                allow_stale=True,
            )
            print(
                "SAP_WIKIMEDIA_NETWORK_FALLBACK="
                f"{stale_state} reason=timeout"
            )
            return stale or []
        except requests.RequestException as exc:
            record_provider_result(
                "wikimedia",
                ok=False,
                reason="network",
            )
            stale, stale_state = get_cached_query(
                "wikimedia",
                cache_payload,
                allow_stale=True,
            )
            print(
                "SAP_WIKIMEDIA_NETWORK_FALLBACK="
                f"{stale_state} reason={type(exc).__name__}"
            )
            return stale or []

        if r.ok:
            try:
                pages = (
                    r.json()
                    .get("query", {})
                    .get("pages", [])
                )
                if not isinstance(pages, list):
                    raise ValueError("pages_not_list")
            except Exception:
                record_provider_result(
                    "wikimedia",
                    ok=False,
                    reason="invalid_json",
                )
                stale, stale_state = get_cached_query(
                    "wikimedia",
                    cache_payload,
                    allow_stale=True,
                )
                print(
                    "SAP_WIKIMEDIA_INVALID_RESPONSE_FALLBACK="
                    f"{stale_state}"
                )
                return stale or []

            record_provider_result(
                "wikimedia",
                ok=True,
                status_code=r.status_code,
            )
            cache_query_result(
                "wikimedia",
                cache_payload,
                pages,
            )
            return pages

        code = int(r.status_code or 0)
        retry_after = None
        if code == 429:
            try:
                retry_after = float(r.headers.get("Retry-After") or 0)
            except (TypeError, ValueError):
                retry_after = None

        reason = (
            "auth"
            if code in {401, 403}
            else "rate_limit"
            if code == 429
            else "server"
            if code in {500, 502, 503, 504}
            else f"http_{code}"
        )
        record_provider_result(
            "wikimedia",
            ok=False,
            status_code=code,
            reason=reason,
            retry_after=retry_after,
        )

        # Auth/rate-limit errors are not helped by immediate repeated calls.
        if code in {401, 403, 429}:
            stale, stale_state = get_cached_query(
                "wikimedia",
                cache_payload,
                allow_stale=True,
            )
            print(
                "SAP_WIKIMEDIA_HTTP_FALLBACK "
                f"status={code} cache={stale_state}"
            )
            return stale or []

        if code not in {500, 502, 503, 504} or attempt == 1:
            stale, stale_state = get_cached_query(
                "wikimedia",
                cache_payload,
                allow_stale=True,
            )
            return stale or []

        time.sleep(0.35)

    stale, stale_state = get_cached_query(
        "wikimedia",
        cache_payload,
        allow_stale=True,
    )
    return stale or []



# =====================================================
# DOCUMENTARY MODE MATCH 3.4.2
# =====================================================

MODE_HINTS = {

    "transport": {
        "airplane",
        "aircraft",
        "plane",
        "aviation",
        "vehicle",
        "ship",
        "boat",
        "car",
        "train",
        "helicopter"
    },

    "location": {
        "landscape",
        "city",
        "street",
        "mountain",
        "ocean",
        "sea",
        "building",
        "location",
        "aerial",
        "valley"
    },

    "architecture": {
        "building",
        "house",
        "hotel",
        "room",
        "interior",
        "exterior",
        "architecture"
    },

    "document": {
        "document",
        "report",
        "newspaper",
        "file",
        "letter",
        "archive",
        "paper",
        "record"
    },

    "evidence": {
        "evidence",
        "report",
        "document",
        "investigation",
        "file",
        "photograph",
        "object"
    },

    "map_context": {
        "map",
        "route",
        "location",
        "chart",
        "diagram"
    },

    "human_context": {
        "person",
        "people",
        "man",
        "woman",
        "portrait",
        "photograph"
    }
}


def score_visual_mode(
    descricao,
    visual_mode
):

    hints = MODE_HINTS.get(
        visual_mode,
        set()
    )

    if not hints:
        return 0.0


    desc = tokens(
        descricao
    )


    hits = len(
        desc.intersection(
            hints
        )
    )


    if hits >= 2:
        return 35.0

    if hits == 1:
        return 20.0

    return -18.0


def score_assunto(
    descricao,
    assunto
):

    assunto_t = tokens(
        assunto
    )

    descricao_t = tokens(
        descricao
    )


    if not assunto_t:
        return 0.0


    overlap = (
        len(
            assunto_t.intersection(
                descricao_t
            )
        )
        / len(
            assunto_t
        )
    )


    if overlap >= 0.75:
        return 90.0

    if overlap >= 0.50:
        return 60.0

    if overlap >= 0.25:
        return 30.0

    return 0.0


# =====================================================
# CASE-ANCHORED SEARCH 5.4
# =====================================================

QUERY_TIER_BONUS = {
    "CASE":
        85.0,

    "CASE_VISUAL":
        65.0,

    "CONTEXT_COMBINED":
        60.0,

    "CONTEXT":
        45.0,

    "CONTEXT_VISUAL":
        35.0,

    "GENERIC":
        -20.0
}


QUERY_TIER_RANK = {
    "CASE":
        6,

    "CASE_VISUAL":
        5,

    "CONTEXT_COMBINED":
        5,

    "CONTEXT":
        4,

    "CONTEXT_VISUAL":
        3,

    "GENERIC":
        1
}


def anchor_stats_5_4(
    descricao,
    spec
):

    desc_tokens = tokens(
        descricao
    )


    grupos = spec.get(
        "anchor_groups",
        []
    )


    # Compatibilidade com specs antigos.
    if not grupos:

        antigos = list(
            spec.get(
                "anchor_tokens",
                []
            )
        )


        if antigos:

            grupos = [
                {
                    "text":
                        spec.get(
                            "anchor_text",
                            ""
                        ),

                    "tokens":
                        antigos,

                    "required":
                        int(
                            spec.get(
                                "anchor_required",
                                len(
                                    antigos
                                )
                            )
                            or len(
                                antigos
                            )
                        )
                }
            ]


    if not grupos:

        return {
            "hits":
                0,

            "total":
                0,

            "ratio":
                0.0,

            "required":
                0,

            "ok":
                True,

            "groups_ok":
                True,

            "group_results":
                []
        }


    resultados = []

    total_hits = 0
    total_tokens = 0
    total_required = 0


    for grupo in grupos:

        toks = set(
            grupo.get(
                "tokens",
                []
            )
        )


        if not toks:
            continue


        required = int(
            grupo.get(
                "required",
                len(
                    toks
                )
            )
            or len(
                toks
            )
        )


        hits = len(
            toks.intersection(
                desc_tokens
            )
        )


        ok = (
            hits
            >= required
        )


        resultados.append(
            {
                "text":
                    grupo.get(
                        "text",
                        ""
                    ),

                "hits":
                    hits,

                "total":
                    len(
                        toks
                    ),

                "required":
                    required,

                "ok":
                    ok
            }
        )


        total_hits += hits
        total_tokens += len(
            toks
        )
        total_required += required


    groups_ok = all(
        item[
            "ok"
        ]
        for item in resultados
    )


    ratio = (
        total_hits
        / total_tokens
        if total_tokens
        else 0.0
    )


    return {
        "hits":
            total_hits,

        "total":
            total_tokens,

        "ratio":
            ratio,

        "required":
            total_required,

        "ok":
            groups_ok,

        "groups_ok":
            groups_ok,

        "group_results":
            resultados
    }


# =====================================================
# TEMPORAL COHERENCE 5.4.1
# =====================================================

def anos_texto_5_4(
    texto
):

    return {
        int(x)
        for x in re.findall(
            r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b",
            str(
                texto or ""
            )
        )
    }


def temporal_stats_5_4(
    busca,
    segmento,
    descricao
):

    pedidos = anos_texto_5_4(
        (
            str(
                busca or ""
            )
            + " "
            + str(
                segmento or ""
            )
        )
    )


    encontrados = anos_texto_5_4(
        descricao
    )


    if not pedidos:

        return {
            "requested":
                [],

            "asset":
                sorted(
                    encontrados
                ),

            "conflict":
                False
        }


    # Se o arquivo não possui data,
    # não inventamos conflito.
    if not encontrados:

        return {
            "requested":
                sorted(
                    pedidos
                ),

            "asset":
                [],

            "conflict":
                False
        }


    conflito = not bool(
        pedidos.intersection(
            encontrados
        )
    )


    return {
        "requested":
            sorted(
                pedidos
            ),

        "asset":
            sorted(
                encontrados
            ),

        "conflict":
            conflito
    }


def origem_rank_5_4(
    candidato
):

    return (
        int(
            candidato.get(
                "wiki_query_tier_rank",
                0
            )
            or 0
        ),

        int(
            candidato.get(
                "wiki_anchor_ok",
                False
            )
        ),

        float(
            candidato.get(
                "wiki_anchor_ratio",
                0.0
            )
            or 0.0
        ),

        int(
            candidato.get(
                "must_hits",
                0
            )
            or 0
        ),

        float(
            candidato.get(
                "score",
                -999
            )
            or -999
        )
    )


# =====================================================
# BUSCA PRINCIPAL 5.4
# =====================================================

def buscar_wikimedia_fotos(
    busca,
    must_have,
    avoid,
    assunto="",
    segmento="",
    visual_mode="",
    limite=12
):

    query_specs = (
        gerar_buscas_commons_ancoradas(
            assunto,
            busca,
            must_have,
            visual_mode,
            segmento
        )
    )


    if not query_specs:
        return []


    encontrados = {}
    search_started = time.monotonic()


    for spec in query_specs:

        if time.monotonic() - search_started >= SEARCH_DEADLINE:
            print(
                "SAP_WIKIMEDIA_DEADLINE=REACHED "
                f"limit={SEARCH_DEADLINE:.1f}s "
                f"queries_total={len(query_specs)} "
                f"assets={len(encontrados)}"
            )
            break

        query = str(
            spec.get(
                "query",
                ""
            )
        ).strip()


        if not query:
            continue


        tier = str(
            spec.get(
                "tier",
                "GENERIC"
            )
        )


        tier_rank = int(
            spec.get(
                "tier_rank",
                QUERY_TIER_RANK.get(
                    tier,
                    0
                )
            )
            or 0
        )


        pages = consultar_commons(
            query,
            limite
        )


        for page in pages:

            infos = page.get(
                "imageinfo",
                []
            )


            if not infos:
                continue


            info = infos[0]


            ext = info.get(
                "extmetadata",
                {}
            )


            # ---------------------------------
            # LICENÇA
            # ---------------------------------

            if not licencia_livre(
                ext
            ):
                continue


            # ---------------------------------
            # TIPO
            # ---------------------------------

            mime = str(
                info.get(
                    "mime",
                    ""
                )
            ).lower()


            if mime and not (
                "jpeg" in mime
                or "jpg" in mime
                or "png" in mime
            ):
                continue


            # ---------------------------------
            # URL
            # ---------------------------------

            url = (
                info.get(
                    "thumburl"
                )
                or info.get(
                    "url"
                )
            )


            if not url:
                continue


            # ---------------------------------
            # METADATA REAL DO ARQUIVO
            # ---------------------------------

            titulo = str(
                page.get(
                    "title",
                    ""
                )
            )


            descricao = " ".join(
                [
                    titulo,

                    limpar_html(
                        ext.get(
                            "ImageDescription",
                            {}
                        ).get(
                            "value",
                            ""
                        )
                    ),

                    limpar_html(
                        ext.get(
                            "ObjectName",
                            {}
                        ).get(
                            "value",
                            ""
                        )
                    ),

                    limpar_html(
                        ext.get(
                            "Categories",
                            {}
                        ).get(
                            "value",
                            ""
                        )
                    )
                ]
            )


            # ---------------------------------
            # MUST / AVOID
            # ---------------------------------

            must_hits = sum(
                1
                for termo in must_have
                if termo_presente(
                    descricao,
                    termo
                )
            )


            avoid_hits = sum(
                1
                for termo in avoid
                if termo_presente(
                    descricao,
                    termo
                )
            )


            if avoid_hits > 0:
                continue


            # ---------------------------------
            # QUERY OVERLAP
            # ---------------------------------

            query_tokens = tokens(
                query
            )

            desc_tokens = tokens(
                descricao
            )


            if query_tokens:

                query_overlap = (
                    len(
                        query_tokens.intersection(
                            desc_tokens
                        )
                    )
                    / len(
                        query_tokens
                    )
                )

            else:

                query_overlap = 0.0


            # ---------------------------------
            # CASE/CONTEXT ANCHOR
            # ---------------------------------

            anchor = anchor_stats_5_4(
                descricao,
                spec
            )


            # Uma busca específica que retornou
            # algo sem a âncora pedida é ruído
            # do Commons e não entra no pool.
            if (
                tier != "GENERIC"
                and not anchor[
                    "ok"
                ]
            ):

                continue


            # ---------------------------------
            # TEMPORAL COHERENCE 5.4.1
            # ---------------------------------

            temporal = temporal_stats_5_4(
                busca,
                segmento,
                descricao
            )


            if (
                temporal[
                    "conflict"
                ]
                and visual_mode in {
                    "location",
                    "architecture",
                    "transport",
                    "map_context"
                }
            ):

                continue


            # ---------------------------------
            # SCORE BASE
            # ---------------------------------

            score = (
                query_overlap * 35
                + must_hits * 38
            )


            topic_bonus = score_assunto(
                descricao,
                assunto
            )


            mode_bonus = score_visual_mode(
                descricao,
                visual_mode
            )


            score += topic_bonus
            score += mode_bonus


            # Fonte documental candidata
            if visual_mode in {
                "document",
                "evidence",
                "location",
                "architecture",
                "transport",
                "map_context"
            }:

                score += 20


            # ---------------------------------
            # QUERY TIER 5.4
            # ---------------------------------

            tier_bonus = (
                QUERY_TIER_BONUS.get(
                    tier,
                    0.0
                )
            )


            anchor_bonus = (
                anchor[
                    "ratio"
                ]
                * 75.0
            )


            score += tier_bonus
            score += anchor_bonus


            # Resultado ancorado confirmado
            if (
                tier != "GENERIC"
                and anchor[
                    "ok"
                ]
            ):

                score += 15.0


            # ---------------------------------
            # FILTRO GENÉRICO
            # ---------------------------------
            #
            # Só o fallback genérico continua
            # sujeito à regra antiga.
            #
            # Uma foto direta de Elisa Lam,
            # por exemplo, não deve ser jogada
            # fora apenas por não conter
            # "elevator" no metadata.
            # ---------------------------------

            if (
                tier == "GENERIC"
                and must_have
                and must_hits == 0
                and query_overlap < 0.18
            ):

                continue


            # ---------------------------------
            # ID / CRÉDITOS
            # ---------------------------------

            ident = (
                page.get(
                    "pageid"
                )
                or titulo
            )


            autor = limpar_html(
                ext.get(
                    "Artist",
                    {}
                ).get(
                    "value",
                    ""
                )
            )


            licenca = limpar_html(
                ext.get(
                    "LicenseShortName",
                    {}
                ).get(
                    "value",
                    ""
                )
            )


            pagina = (
                "https://commons.wikimedia.org/wiki/"
                + titulo.replace(
                    " ",
                    "_"
                )
            )


            # ---------------------------------
            # CANDIDATO 5.4
            # ---------------------------------

            candidato = {
                "score":
                    score,

                "must_hits":
                    must_hits,

                "avoid_hits":
                    avoid_hits,

                "id":
                    ident,

                "url":
                    url,

                "fonte":
                    "Wikimedia",

                "tipo":
                    "foto",

                "titulo":
                    titulo,

                "descricao":
                    descricao,

                "credit_author":
                    autor,

                "credit_license":
                    licenca,

                "credit_page":
                    pagina,

                # ---------------------------------
                # PROVENANCE 5.4
                # ---------------------------------

                "wiki_query":
                    query,

                "wiki_query_tier":
                    tier,

                "wiki_query_tier_rank":
                    tier_rank,

                "wiki_anchor_text":
                    spec.get(
                        "anchor_text",
                        ""
                    ),

                "wiki_anchor_hits":
                    anchor[
                        "hits"
                    ],

                "wiki_anchor_total":
                    anchor[
                        "total"
                    ],

                "wiki_anchor_required":
                    anchor[
                        "required"
                    ],

                "wiki_anchor_ratio":
                    anchor[
                        "ratio"
                    ],

                "wiki_anchor_ok":
                    anchor[
                        "ok"
                    ],

                "wiki_anchor_groups":
                    anchor.get(
                        "group_results",
                        []
                    ),

                "wiki_temporal_requested":
                    temporal.get(
                        "requested",
                        []
                    ),

                "wiki_temporal_asset":
                    temporal.get(
                        "asset",
                        []
                    ),

                "wiki_temporal_conflict":
                    temporal.get(
                        "conflict",
                        False
                    ),

                "wiki_query_overlap":
                    query_overlap,

                "wiki_topic_bonus":
                    topic_bonus,

                "wiki_mode_bonus":
                    mode_bonus,

                "wiki_tier_bonus":
                    tier_bonus,

                "wiki_anchor_bonus":
                    anchor_bonus
            }


            chave = str(
                ident
            )


            atual = encontrados.get(
                chave
            )


            # =================================
            # DEDUPLICAÇÃO ORIENTADA À ORIGEM
            # =================================
            #
            # Uma versão encontrada pela query
            # específica vence uma versão
            # encontrada por query genérica,
            # mesmo que a genérica tenha
            # alguns pontos a mais de MUST.
            # =================================

            if (
                atual is None
                or origem_rank_5_4(
                    candidato
                )
                > origem_rank_5_4(
                    atual
                )
            ):

                encontrados[
                    chave
                ] = candidato


    saida = list(
        encontrados.values()
    )


    # =====================================
    # ORDENAÇÃO FINAL 5.4
    # =====================================

    saida.sort(
        key=lambda x: (
            x.get(
                "wiki_query_tier_rank",
                0
            ),

            int(
                x.get(
                    "wiki_anchor_ok",
                    False
                )
            ),

            x.get(
                "wiki_anchor_ratio",
                0.0
            ),

            x.get(
                "must_hits",
                0
            ),

            x.get(
                "score",
                -999
            )
        ),
        reverse=True
    )


    return saida[:15]


# =====================================================
# CRÉDITOS
# =====================================================

def salvar_credito(
    short_id,
    scene_number,
    candidato
):

    if candidato.get(
        "fonte"
    ) != "Wikimedia":

        return


    path = os.path.join(
        CREDIT_DIR,
        f"short_{short_id}.txt"
    )


    bloco = (
        f"\nSCENE {scene_number:02d}\n"
        f"Source: Wikimedia Commons\n"
        f"Author: "
        f"{candidato.get('credit_author', '')}\n"
        f"License: "
        f"{candidato.get('credit_license', '')}\n"
        f"Page: "
        f"{candidato.get('credit_page', '')}\n"
    )


    try:
        existing = ""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                existing = f.read()

        # Keep exactly one credit block per scene. Retries/resumes may select
        # a new Wikimedia asset for the same scene, so replace the old block
        # instead of appending another one.
        blocks = re.split(
            r"\n(?=\s*SCENE\s+\d+)",
            existing.strip(),
            flags=re.IGNORECASE,
        ) if existing.strip() else []

        kept = []
        for item in blocks:
            match = re.search(
                r"^\s*SCENE\s+(\d+)\s*$",
                item,
                flags=re.MULTILINE | re.IGNORECASE,
            )
            if match and int(match.group(1)) == int(scene_number):
                continue
            if item.strip():
                kept.append(item.strip())

        content = ""
        if kept:
            content = "\n\n".join(kept).rstrip() + "\n"
        content += bloco.lstrip("\n")

        directory = os.path.dirname(path) or "."
        fd, temp_path = tempfile.mkstemp(
            prefix=".wikimedia_credit_",
            suffix=".tmp",
            dir=directory,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, path)
        finally:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    except Exception:

        pass


# =====================================================
# TESTE
# =====================================================

if __name__ == "__main__":

    print(
        "WIKIMEDIA EVIDENCE SOURCE 3.5: OK"
    )
