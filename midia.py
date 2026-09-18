#!/usr/bin/env python3

# SHORTAUTOPRO VSE42 IMPORT
from visual_pipeline_bridge_v42 import (
    enabled as _vse42_enabled,
    finalize_pool as _vse42_finalize_pool,
    note_success as _vse42_note_success,
    commit_media as _vse42_commit_media,
    install_search_rescue as _vse42_install_search_rescue,
)


import subprocess
import os
import sys
import time
import random
import shutil
import re
import json
import requests
from datetime import date

from wikimedia_source import (
    buscar_wikimedia_fotos,
    salvar_credito
)


from source_router import (
    escolher_rota
)


from evidence_guard import (
    avaliar_evidencia
)



from visual_intelligence_6 import (
    audit_scene as vi6_audit_scene,
    push_shadow_history as vi6_push_history,
    salvar_report as vi6_salvar_report
)


# =========================================
# VI6.8 + VI6.9 RUNTIME SAFETY STACK
# =========================================
import vi6_8_runtime_policy
import vi6_9_runtime_policy

# ==================================================
# CONFIG
# ==================================================

BASE = os.path.expanduser("~/ShortAutoPro")

SHORT_ID = os.getenv(
    "SHORT_ID",
    date.today().isoformat()
)

PEXELS_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_KEY = os.getenv("PIXABAY_API_KEY", "")
COVERR_KEY = os.getenv("COVERR_API_KEY", "")

USAR_PEXELS = os.getenv(
    "SHORT_USAR_PEXELS",
    "1"
) == "1"

USAR_PIXABAY = os.getenv(
    "SHORT_USAR_PIXABAY",
    "1"
) == "1"

USAR_COVERR = os.getenv(
    "SHORT_USAR_COVERR",
    "1"
) == "1"

USAR_LOCAL = os.getenv(
    "SHORT_USAR_LOCAL",
    "1"
) == "1"

USAR_VIDEOS = os.getenv(
    "SHORT_USAR_VIDEOS",
    "1"
) == "1"

try:
    VIDEO_META = int(
        os.getenv(
            "SHORT_VIDEO_META",
            "5"
        )
    )
except ValueError:
    VIDEO_META = 5

VIDEO_META = max(
    2,
    min(VIDEO_META, 8)
)

try:
    VIDEO_BONUS = float(
        os.getenv(
            "SHORT_VIDEO_BONUS",
            "18"
        )
    )
except ValueError:
    VIDEO_BONUS = 18.0

try:
    VIDEO_TOLERANCIA = float(
        os.getenv(
            "SHORT_VIDEO_TOLERANCIA",
            "18"
        )
    )
except ValueError:
    VIDEO_TOLERANCIA = 18.0


# ==================================================
# PATHS
# ==================================================

SCENE_MAP = os.path.join(
    BASE,
    "roteiros",
    f"scene_map_{SHORT_ID}.json"
)


TOPIC_REAL = os.path.join(
    BASE,
    "roteiros",
    f"used_topic_{SHORT_ID}.txt"
)

TOPIC_FALLBACK = os.path.join(
    BASE,
    "roteiros",
    f"topic_{SHORT_ID}.txt"
)


def _ler_topic(path):

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return f.read().strip()

    except Exception:

        return ""


ASSUNTO = (
    _ler_topic(TOPIC_REAL)
    or _ler_topic(TOPIC_FALLBACK)
)

SAIDA_DIR = os.path.join(
    BASE,
    "imagens",
    f"short_{SHORT_ID}"
)

LOCAL_DIR = os.path.join(
    BASE,
    "midia_local"
)

os.makedirs(
    SAIDA_DIR,
    exist_ok=True
)

os.makedirs(
    LOCAL_DIR,
    exist_ok=True
)

if not os.path.exists(SCENE_MAP):
    sys.exit(
        f"ERRO: scene_map não encontrado:\n{SCENE_MAP}"
    )

try:
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

    # =========================================
    # VI6.7 + VI6.8 ACTIVE VISUAL PLANNING
    # =========================================

    try:

        from vi6_7_retrieval_planner import (
            plan as _vi67_plan
        )

        from vi6_8_storyboard_director import (
            build_global_plan as _vi68_build
        )

        # Importar ativa a política global
        # sobre o evaluator do VI6.6.
        import vi6_8_runtime_policy


        if isinstance(
            cenas,
            list
        ):

            _vi68_global = (
                _vi68_build(
                    cenas
                )
            )


            _vi68_scene_map = {

                int(
                    item.get(
                        "scene",
                        0
                    )
                    or 0
                ):
                item

                for item
                in _vi68_global.get(
                    "scenes",
                    []
                )

            }


            _vi67_overrides = 0


            for (
                _vi67_index,
                _vi67_scene
            ) in enumerate(
                cenas,
                1
            ):

                if not isinstance(
                    _vi67_scene,
                    dict
                ):

                    continue


                _vi67_plan_result = (
                    _vi67_plan(
                        _vi67_scene
                    )
                )


                # =====================================
                # RETRIEVAL METADATA
                # =====================================

                _vi67_scene[
                    "retrieval_version"
                ] = "6.7"


                _vi67_scene[
                    "retrieval_role_6_7"
                ] = (
                    _vi67_plan_result.get(
                        "role"
                    )
                )


                _vi67_scene[
                    "retrieval_strategy_6_7"
                ] = (
                    _vi67_plan_result.get(
                        "strategy"
                    )
                )


                _vi67_scene[
                    "retrieval_anchor_strength_6_7"
                ] = (
                    _vi67_plan_result.get(
                        "strength"
                    )
                )


                _vi67_scene[
                    "retrieval_anchors_6_7"
                ] = (
                    _vi67_plan_result.get(
                        "anchors",
                        []
                    )
                )


                _vi67_scene[
                    "retrieval_queries_6_7"
                ] = (
                    _vi67_plan_result.get(
                        "queries",
                        []
                    )
                )


                _vi67_scene[
                    "retrieval_primary_query_6_7"
                ] = (
                    _vi67_plan_result.get(
                        "primary"
                    )
                )


                _vi67_scene[
                    "retrieval_query_overridden_6_7"
                ] = bool(
                    _vi67_plan_result.get(
                        "override",
                        False
                    )
                )


                # =====================================
                # GLOBAL STORYBOARD METADATA
                # =====================================

                _vi67_scene[
                    "_vi68_storyboard"
                ] = (
                    _vi68_scene_map.get(
                        _vi67_index,
                        {}
                    )
                )


                # =====================================
                # ACTIVE QUERY OVERRIDE
                # =====================================

                if (
                    _vi67_plan_result.get(
                        "override",
                        False
                    )

                    and _vi67_plan_result.get(
                        "primary"
                    )
                ):

                    if (
                        "visual_query_original_6_7"
                        not in _vi67_scene
                    ):

                        _vi67_scene[
                            "visual_query_original_6_7"
                        ] = (
                            _vi67_scene.get(
                                "visual_query"
                            )

                            or _vi67_scene.get(
                                "query"
                            )

                            or ""
                        )


                    _vi67_scene[
                        "visual_query"
                    ] = (
                        _vi67_plan_result[
                            "primary"
                        ]
                    )


                    _vi67_overrides += 1


            print()
            print(
                "======================================"
            )
            print(
                " VI6.7 + VI6.8 ACTIVE PLANNING"
            )
            print(
                "======================================"
            )

            print(
                f"CENAS={len(cenas)}"
            )

            print(
                f"QUERY_OVERRIDES="
                f"{_vi67_overrides}"
            )

            print(
                f"DOCUMENTARY_TARGET="
                f"{_vi68_global.get('documentary_target')}"
            )

            print(
                f"MOTION_TARGET="
                f"{_vi68_global.get('motion_target')}"
            )

            print(
                "CTA_STRATEGY="
                f"{_vi68_global.get('cta_strategy')}"
            )

            print()


        else:

            print(
                "VI6.7/6.8 WARNING: "
                "`cenas` não é list; "
                "planejamento ignorado."
            )


    except Exception as _vi678_error:

        print(
            "VI6.7/6.8 WARNING: "
            f"{type(_vi678_error).__name__}: "
            f"{str(_vi678_error)[:180]}"
        )

        print(
            "VI6.7/6.8 -> pipeline original preservado"
        )

except Exception as e:
    sys.exit(
        f"ERRO lendo scene_map: {e}"
    )

if not cenas:
    sys.exit(
        "ERRO: scene_map sem cenas."
    )


# ==================================================
# LIMPAR MÍDIA ANTIGA
# ==================================================

for nome in os.listdir(
    SAIDA_DIR
):

    caminho = os.path.join(
        SAIDA_DIR,
        nome
    )

    if nome.lower().endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4"
        )
    ):
        try:
            os.remove(caminho)
        except Exception:
            pass


# ==================================================
# TEXTO
# ==================================================

STOP = {
    "a", "an", "the", "of", "in",
    "on", "at", "with", "and", "or",
    "to", "for", "from", "by",
    "cinematic", "dramatic", "moody",
    "dark", "night", "close", "up",
    "shot", "view", "scene"
}


def normalizar(texto):

    return " ".join(
        re.findall(
            r"[a-z0-9]+",
            str(texto).lower()
        )
    )


def tokenizar(texto):

    return {
        x
        for x in re.findall(
            r"[a-z0-9]+",
            str(texto).lower()
        )
        if x not in STOP
    }


def similaridade(
    a,
    b
):

    ta = tokenizar(a)
    tb = tokenizar(b)

    if not ta:
        return 0.0

    return (
        len(
            ta.intersection(tb)
        )
        / len(ta)
    )


def similaridade_conjuntos(
    a,
    b
):

    ta = tokenizar(a)
    tb = tokenizar(b)

    if not ta or not tb:
        return 0.0

    uniao = ta.union(tb)

    if not uniao:
        return 0.0

    return (
        len(
            ta.intersection(tb)
        )
        / len(uniao)
    )


def termo_presente(
    descricao,
    termo
):

    desc = normalizar(
        descricao
    )

    termo_n = normalizar(
        termo
    )

    if not termo_n:
        return False

    if termo_n in desc:
        return True

    termo_tokens = tokenizar(
        termo_n
    )

    desc_tokens = tokenizar(
        desc
    )

    if not termo_tokens:
        return False

    encontrados = len(
        termo_tokens.intersection(
            desc_tokens
        )
    )

    return (
        encontrados
        / len(termo_tokens)
    ) >= 0.75


# ==================================================
# SCORE DE RELEVÂNCIA
# ==================================================

def avaliar_relevancia(
    busca,
    descricao,
    must_have,
    avoid
):

    score = (
        similaridade(
            busca,
            descricao
        )
        * 60
    )

    must_hits = 0

    for termo in must_have:

        if termo_presente(
            descricao,
            termo
        ):
            must_hits += 1
            score += 40

        else:
            score -= 20


    avoid_hits = 0

    for termo in avoid:

        if termo_presente(
            descricao,
            termo
        ):
            avoid_hits += 1
            score -= 55


    return (
        score,
        must_hits,
        avoid_hits
    )


# ==================================================
# DOWNLOAD
# ==================================================

def baixar(
    url,
    destino,
    timeout=120
):

    temporario = (
        destino
        + ".part"
    )

    try:

        if not url:
            raise RuntimeError(
                "URL vazia"
            )

        if os.path.exists(
            temporario
        ):
            os.remove(
                temporario
            )

        headers = {
            "User-Agent":
                "ShortAutoPro/5.2 "
                "DocumentaryMediaClient/1.0",

            "Accept":
                "image/*,video/*,"
                "application/octet-stream;q=0.9,*/*;q=0.5"
        }

        r = requests.get(
            url,
            timeout=timeout,
            stream=True,
            allow_redirects=True,
            headers=headers
        )

        r.raise_for_status()

        content_type = (
            r.headers.get(
                "Content-Type",
                ""
            )
            .split(";")[0]
            .strip()
            .lower()
        )

        if (
            content_type.startswith(
                "text/"
            )
            or content_type
            in {
                "application/json",
                "application/xml"
            }
        ):
            raise RuntimeError(
                f"content-type inválido: "
                f"{content_type}"
            )

        with open(
            temporario,
            "wb"
        ) as f:

            for bloco in r.iter_content(
                chunk_size=256 * 1024
            ):

                if bloco:
                    f.write(
                        bloco
                    )

        if (
            not os.path.exists(
                temporario
            )
            or os.path.getsize(
                temporario
            ) <= 1000
        ):
            raise RuntimeError(
                "arquivo vazio ou muito pequeno"
            )

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "json",
                temporario
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        if probe.returncode != 0:
            raise RuntimeError(
                "arquivo visual rejeitado pelo ffprobe"
            )

        dados = json.loads(
            probe.stdout
        )

        streams = dados.get(
            "streams",
            []
        )

        if not streams:
            raise RuntimeError(
                "arquivo sem stream visual"
            )

        largura = int(
            streams[0].get(
                "width",
                0
            )
            or 0
        )

        altura = int(
            streams[0].get(
                "height",
                0
            )
            or 0
        )

        if largura <= 0 or altura <= 0:
            raise RuntimeError(
                "dimensões inválidas"
            )

        if largura * altura < 320 * 180:
            raise RuntimeError(
                f"mídia abaixo do piso técnico: {largura}x{altura}"
            )

        os.replace(
            temporario,
            destino
        )

        return True

    except Exception as e:

        print(
            f"    DOWNLOAD FAIL: "
            f"{type(e).__name__}: "
            f"{str(e)[:180]}"
        )

        for arquivo in [
            temporario,
            destino
        ]:

            if os.path.exists(
                arquivo
            ):

                try:
                    os.remove(
                        arquivo
                    )

                except Exception:
                    pass

        return False


# ==================================================
# ANTI REPETIÇÃO
# ==================================================

usados = set()


def penalidade_usado(
    fonte,
    ident
):

    if (
        fonte,
        str(ident)
    ) in usados:
        return -120

    return 0


def marcar_usado(
    fonte,
    ident
):

    usados.add(
        (
            fonte,
            str(ident)
        )
    )


# ==================================================
# PEXELS VIDEO
# ==================================================


# SHORTAUTOPRO VSE421 SCENE SUCCESS FINALIZER

def _vse42_cleanup_scene_sibling(destino):
    """
    Após um download BEM-SUCEDIDO, mantém apenas uma
    mídia para o scene_XX.

    Nunca remove arquivos antes do sucesso.
    Nunca opera fora de imagens/short_*.
    """

    if not destino:
        return []


    try:

        from pathlib import Path

        target = Path(
            destino
        )


        if not target.is_file():
            return []


        parent = target.parent

        stem = target.stem


        if not stem.startswith(
            "scene_"
        ):
            return []


        parent_text = str(
            parent
        )


        if (
            "/imagens/short_"
            not in parent_text
        ):
            return []


        allowed = (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
        )


        removed = []


        for suffix in allowed:

            sibling = (
                parent
                /
                (
                    stem
                    +
                    suffix
                )
            )


            if sibling == target:
                continue


            if not sibling.is_file():
                continue


            sibling.unlink()

            removed.append(
                str(sibling)
            )


        if removed:

            print(
                "  VSE421_STALE_SIBLING_REMOVED="
                +
                ",".join(
                    removed
                )
            )


        return removed


    except Exception as exc:

        print(
            "  VSE421_SIBLING_WARNING="
            +
            type(exc).__name__
            +
            ":"
            +
            str(exc)
        )

        return []


def _vse42_commit_safe(candidate):
    """
    Commit fail-open do candidato vencedor.
    """

    try:

        from visual_selection_bridge_v42 import (
            commit_candidate
            as _commit_candidate
        )


        _commit_candidate(
            candidate
        )


        print(
            "  VSE421_SCENE_COMMIT=FIRST_SUCCESS"
        )


        return True


    except Exception as exc:

        print(
            "  VSE421_COMMIT_WARNING="
            +
            type(exc).__name__
            +
            ":"
            +
            str(exc)
        )


        return False





# ============================================================
# SAP_PROVIDER_DIAGNOSTICS_V1
# ============================================================

def _sap_provider_diag_v1(
    provider,
    reason,
    line=None,
    exc=None,
    response=None,
):
    try:
        parts = [
            "SAP_PROVIDER_DIAG",
            f"provider={provider}",
            f"reason={reason}",
        ]

        if line is not None:
            parts.append(
                f"line={line}"
            )

        if response is not None:
            parts.append(
                "http="
                + str(
                    getattr(
                        response,
                        "status_code",
                        None,
                    )
                )
            )

        if exc is not None:
            parts.append(
                "error="
                + type(exc).__name__
                + ":"
                + str(exc)
            )

        print(
            " ".join(parts)
        )

    except Exception:
        pass

def pexels_video(
    busca,
    must_have,
    avoid
):

    if not USAR_PEXELS or not PEXELS_KEY:
        _sap_provider_diag_v1('pexels_video', 'EMPTY_RETURN', line=1105, response=locals().get('r'))
        return []

    try:

        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={
                "Authorization":
                PEXELS_KEY
            },
            params={
                "query": busca,
                "orientation": "portrait",
                "per_page": 20
            },
            timeout=30
        )

    except Exception as _sap_provider_exc_v1:
        _sap_provider_diag_v1('pexels_video', 'EXCEPTION', line=1123, exc=_sap_provider_exc_v1, response=locals().get('r'))
        return []

    if not r.ok:
        _sap_provider_diag_v1('pexels_video', 'EMPTY_RETURN', line=1127, response=locals().get('r'))
        return []

    saida = []

    for item in r.json().get(
        "videos",
        []
    ):

        ident = item.get("id")

        descricao = " ".join(
            [
                str(item.get("url", "")),
                str(
                    item.get(
                        "user",
                        {}
                    ).get(
                        "name",
                        ""
                    )
                )
            ]
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        for arq in item.get(
            "video_files",
            []
        ):

            url = arq.get("link")

            if not url:
                continue

            w = arq.get(
                "width"
            ) or 0

            h = arq.get(
                "height"
            ) or 0

            score = rel

            if h > w:
                score += 28

            if h >= 1280:
                score += 16

            if w >= 720:
                score += 8

            score += penalidade_usado(
                "Pexels",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits": must_hits,
                    "avoid_hits": avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte": "Pexels",
                    "tipo": "vídeo",
                    "descricao": descricao
                }
            )

    return saida


# ==================================================
# PEXELS FOTO
# ==================================================

def pexels_foto(
    busca,
    must_have,
    avoid
):

    if not USAR_PEXELS or not PEXELS_KEY:
        _sap_provider_diag_v1('pexels_foto', 'EMPTY_RETURN', line=1223, response=locals().get('r'))
        return []

    try:

        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={
                "Authorization":
                PEXELS_KEY
            },
            params={
                "query": busca,
                "orientation": "portrait",
                "per_page": 25
            },
            timeout=30
        )

    except Exception as _sap_provider_exc_v1:
        _sap_provider_diag_v1('pexels_foto', 'EXCEPTION', line=1241, exc=_sap_provider_exc_v1, response=locals().get('r'))
        return []

    if not r.ok:
        _sap_provider_diag_v1('pexels_foto', 'EMPTY_RETURN', line=1245, response=locals().get('r'))
        return []

    saida = []

    for item in r.json().get(
        "photos",
        []
    ):

        ident = item.get("id")

        descricao = str(
            item.get(
                "alt",
                ""
            )
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        src = item.get(
            "src",
            {}
        )

        url = (
            src.get("portrait")
            or src.get("large2x")
            or src.get("large")
            or src.get("original")
        )

        if not url:
            continue

        w = item.get(
            "width"
        ) or 0

        h = item.get(
            "height"
        ) or 0

        score = rel

        if h > w:
            score += 28

        if h >= 1280:
            score += 16

        score += penalidade_usado(
            "Pexels",
            ident
        )

        saida.append(
            {
                "score": score,
                "must_hits": must_hits,
                "avoid_hits": avoid_hits,
                "id": ident,
                "url": url,
                "fonte": "Pexels",
                "tipo": "foto",
                "descricao": descricao
            }
        )

    return saida


# ==================================================
# PIXABAY VIDEO
# ==================================================

def pixabay_video(
    busca,
    must_have,
    avoid
):

    if not USAR_PIXABAY or not PIXABAY_KEY:
        _sap_provider_diag_v1('pixabay_video', 'EMPTY_RETURN', line=1335, response=locals().get('r'))
        return []

    try:

        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={
                "key": PIXABAY_KEY,
                "q": busca,
                "video_type": "film",
                "safesearch": "true",
                "order": "popular",
                "per_page": 20
            },
            timeout=30
        )

    except Exception as _sap_provider_exc_v1:
        _sap_provider_diag_v1('pixabay_video', 'EXCEPTION', line=1352, exc=_sap_provider_exc_v1, response=locals().get('r'))
        return []

    if not r.ok:
        _sap_provider_diag_v1('pixabay_video', 'EMPTY_RETURN', line=1356, response=locals().get('r'))
        return []

    saida = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = item.get("id")

        descricao = " ".join(
            [
                str(item.get("tags", "")),
                str(item.get("pageURL", ""))
            ]
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        formatos = item.get(
            "videos",
            {}
        )

        for chave in [
            "large",
            "medium",
            "small",
            "tiny"
        ]:

            info = formatos.get(
                chave,
                {}
            )

            url = info.get("url")

            if not url:
                continue

            w = info.get(
                "width"
            ) or 0

            h = info.get(
                "height"
            ) or 0

            score = rel

            if h > w:
                score += 28

            if h >= 720:
                score += 12

            if h >= 1080:
                score += 8

            score += penalidade_usado(
                "Pixabay",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits": must_hits,
                    "avoid_hits": avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte": "Pixabay",
                    "tipo": "vídeo",
                    "descricao": descricao
                }
            )

    return saida


# ==================================================
# PIXABAY FOTO
# ==================================================

def pixabay_foto(
    busca,
    must_have,
    avoid
):

    if not USAR_PIXABAY or not PIXABAY_KEY:
        _sap_provider_diag_v1('pixabay_foto', 'EMPTY_RETURN', line=1456, response=locals().get('r'))
        return []

    try:

        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_KEY,
                "q": busca,
                "image_type": "photo",
                "orientation": "vertical",
                "safesearch": "true",
                "order": "popular",
                "per_page": 25
            },
            timeout=30
        )

    except Exception as _sap_provider_exc_v1:
        _sap_provider_diag_v1('pixabay_foto', 'EXCEPTION', line=1474, exc=_sap_provider_exc_v1, response=locals().get('r'))
        return []

    if not r.ok:
        _sap_provider_diag_v1('pixabay_foto', 'EMPTY_RETURN', line=1478, response=locals().get('r'))
        return []

    saida = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = item.get("id")

        descricao = str(
            item.get(
                "tags",
                ""
            )
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        url = (
            item.get("largeImageURL")
            or item.get("webformatURL")
        )

        if not url:
            continue

        w = item.get(
            "imageWidth"
        ) or 0

        h = item.get(
            "imageHeight"
        ) or 0

        score = rel

        if h > w:
            score += 28

        if h >= 1280:
            score += 16

        score += penalidade_usado(
            "Pixabay",
            ident
        )

        saida.append(
            {
                "score": score,
                "must_hits": must_hits,
                "avoid_hits": avoid_hits,
                "id": ident,
                "url": url,
                "fonte": "Pixabay",
                "tipo": "foto",
                "descricao": descricao
            }
        )

    return saida


# ==================================================
# COVERR
# ==================================================

def coverr_video(
    busca,
    must_have,
    avoid
):

    if not USAR_COVERR or not COVERR_KEY:
        _sap_provider_diag_v1('coverr_video', 'EMPTY_RETURN', line=1561, response=locals().get('r'))
        return []

    try:

        r = requests.get(
            "https://api.coverr.co/videos",
            headers={
                "Authorization":
                f"Bearer {COVERR_KEY}"
            },
            params={
                "query": busca,
                "page": 0,
                "page_size": 20,
                "urls": "true"
            },
            timeout=30
        )

    except Exception as _sap_provider_exc_v1:
        _sap_provider_diag_v1('coverr_video', 'EXCEPTION', line=1580, exc=_sap_provider_exc_v1, response=locals().get('r'))
        return []

    if not r.ok:
        _sap_provider_diag_v1('coverr_video', 'EMPTY_RETURN', line=1584, response=locals().get('r'))
        return []

    saida = []

    for item in r.json().get(
        "hits",
        []
    ):

        ident = (
            item.get("id")
            or item.get("slug")
            or item.get("title")
        )

        descricao = " ".join(
            [
                str(item.get("title", "")),
                str(item.get("description", "")),
                str(item.get("tags", ""))
            ]
        )

        rel, must_hits, avoid_hits = (
            avaliar_relevancia(
                busca,
                descricao,
                must_have,
                avoid
            )
        )

        urls = item.get(
            "urls",
            {}
        )

        if not isinstance(
            urls,
            dict
        ):
            continue

        for _, url in urls.items():

            if not isinstance(
                url,
                str
            ):
                continue

            score = rel

            if ".mp4" in url.lower():
                score += 8

            score += penalidade_usado(
                "Coverr",
                ident
            )

            saida.append(
                {
                    "score": score,
                    "must_hits": must_hits,
                    "avoid_hits": avoid_hits,
                    "id": ident,
                    "url": url,
                    "fonte": "Coverr",
                    "tipo": "vídeo",
                    "descricao": descricao
                }
            )

    return saida


# ==================================================
# LOCAL
# ==================================================

def buscar_local(
    preferir_video
):

    if not USAR_LOCAL:
        return None

    videos = []
    fotos = []

    for nome in os.listdir(
        LOCAL_DIR
    ):

        caminho = os.path.join(
            LOCAL_DIR,
            nome
        )

        ext = os.path.splitext(
            nome
        )[1].lower()

        if ext == ".mp4":
            videos.append(caminho)

        elif ext in [
            ".jpg",
            ".jpeg",
            ".png"
        ]:
            fotos.append(caminho)

    random.shuffle(videos)
    random.shuffle(fotos)

    candidatos = (
        videos + fotos
        if preferir_video
        else fotos + videos
    )

    if not candidatos:
        return None

    return candidatos[0]


# ==================================================
# FILTRO DE QUALIDADE
# ==================================================

def aceitavel(
    candidato,
    must_total
):

    hits = candidato[
        "must_hits"
    ]

    avoid_hits = candidato[
        "avoid_hits"
    ]

    score = candidato[
        "score"
    ]

    if avoid_hits >= 2:
        return False

    if must_total > 0 and hits == 0:
        return False

    if (
        must_total > 0
        and hits == must_total
    ):
        return True

    if (
        must_total > 0
        and hits >= 1
        and score >= 45
    ):
        return True

    if (
        must_total == 0
        and score >= 20
    ):
        return True

    return False


# ==================================================
# MOTION PREFERENCE
# ==================================================



    # Compara foto x vídeo.
# ==================================================
# ZERO MISSING SCENES V6.5.3
# ==================================================

def simplificar_busca(busca, must_have):

    candidatos = []

    # 1. must_have juntos
    if must_have:
        candidatos.append(
            " ".join(must_have)
        )

    # 2. primeiros termos úteis da busca
    toks = [
        x
        for x in re.findall(
            r"[a-z0-9]+",
            busca.lower()
        )
        if x not in STOP
    ]

    if toks:
        candidatos.append(
            " ".join(toks[:4])
        )

    if len(toks) >= 2:
        candidatos.append(
            " ".join(toks[:2])
        )

    # 3. MUST combinados primeiro.
    #
    # Exemplo:
    # men + rugby team
    # vira:
    # "men rugby team"

    if must_have:

        combinada = " ".join(
            must_have
        ).strip()

        if combinada:
            candidatos.append(
                combinada
            )


    # 4. cada MUST isoladamente
    for termo in must_have:
        candidatos.append(
            termo
        )

    # remove duplicatas
    saida = []

    for item in candidatos:

        item = item.strip()

        if (
            item
            and item.lower()
            not in [
                x.lower()
                for x in saida
            ]
        ):
            saida.append(item)

    return saida


def buscar_todos_candidatos(
    busca,
    must_have,
    avoid,
    segmento="",
    visual_mode=""
):

    todos = []

    # SOURCE ROUTER 4.2
    # Necessário também nos retries.
    rota_fonte = escolher_rota(
        visual_mode,
        must_have
    )


    # Wikimedia primeiro para tentar
    # obter mídia documental real.
    try:

        wiki_candidatos = (
            buscar_wikimedia_fotos(
                busca,
                must_have,
                avoid,
                assunto=ASSUNTO,
                segmento=segmento,
                visual_mode=visual_mode
            )
        )

        wiki_aprovados = []

        for candidato in wiki_candidatos:

            autenticidade = (
                avaliar_evidencia(
                    candidato,
                    ASSUNTO,
                    segmento,
                    must_have,
                    visual_mode
                )
            )

            candidato[
                "evidence_class"
            ] = autenticidade[
                "class"
            ]

            candidato[
                "topic_overlap"
            ] = autenticidade[
                "topic_overlap"
            ]

            candidato[
                "segment_overlap"
            ] = autenticidade[
                "segment_overlap"
            ]

            candidato[
                "evidence_must_coverage"
            ] = autenticidade[
                "must_coverage"
            ]


            if not autenticidade[
                "allowed"
            ]:

                continue


            candidato[
                "score"
            ] += (
                rota_fonte.get(
                    "wikimedia_bonus",
                    0.0
                )
                + autenticidade[
                    "bonus"
                ]
            )


            wiki_aprovados.append(
                candidato
            )


        todos.extend(
            wiki_aprovados
        )

    except Exception:
        pass

    if USAR_VIDEOS:

        todos.extend(
            pexels_video(
                busca,
                must_have,
                avoid
            )
        )

        todos.extend(
            pixabay_video(
                busca,
                must_have,
                avoid
            )
        )

        todos.extend(
            coverr_video(
                busca,
                must_have,
                avoid
            )
        )

    todos.extend(
        pexels_foto(
            busca,
            must_have,
            avoid
        )
    )

    todos.extend(
        pixabay_foto(
            busca,
            must_have,
            avoid
        )
    )

    return todos


# SHORTAUTOPRO VSE42 SEARCH RESCUE
_vse42_install_search_rescue(globals())


# SHORTAUTOPRO VSE4.2 QUERY EXPANSION HOOK
try:
    from visual_query_expansion_v4 import (
        wrap_search_function as _vse42_wrap_search,
    )

    buscar_todos_candidatos = (
        _vse42_wrap_search(
            buscar_todos_candidatos
        )
    )

    print(
        "VSE42_QUERY_EXPANSION_HOOK=ON"
    )

except Exception as _vse42_qe_exc:

    print(
        "VSE42_QUERY_EXPANSION_HOOK=FAIL_OPEN "
        +
        type(_vse42_qe_exc).__name__
        +
        ":"
        +
        str(_vse42_qe_exc)
    )




# ==================================================
# VISUAL SEMANTIC GUARD 2.3
# ==================================================

def metadata_confiavel(candidato):

    fonte = str(
        candidato.get(
            "fonte",
            ""
        )
    ).lower()

    tipo = str(
        candidato.get(
            "tipo",
            ""
        )
    ).lower()

    # Pexels vídeo normalmente não oferece
    # descrição semântica adequada.
    if (
        fonte == "pexels"
        and tipo == "vídeo"
    ):
        return False

    return True


def cobertura_must(
    candidato,
    total_must
):

    if total_must <= 0:
        return 1.0

    return (
        candidato.get(
            "must_hits",
            0
        )
        / total_must
    )


def candidato_semanticamente_valido(
    candidato,
    total_must,
    relaxado=False
):

    confiavel = metadata_confiavel(
        candidato
    )

    avoid_hits = candidato.get(
        "avoid_hits",
        0
    )

    must_hits = candidato.get(
        "must_hits",
        0
    )

    cobertura = cobertura_must(
        candidato,
        total_must
    )

    # ----------------------------------
    # HARD AVOID
    # ----------------------------------
    #
    # Se temos metadados confiáveis e
    # eles dizem que há algo proibido,
    # a mídia é descartada completamente.

    if (
        confiavel
        and avoid_hits > 0
    ):
        return False


    if total_must <= 0:
        return True


    # ----------------------------------
    # MUST COVERAGE
    # ----------------------------------

    if not relaxado:

        if total_must == 1:

            if (
                confiavel
                and must_hits < 1
            ):
                return False

        else:

            # Em cenas com vários elementos,
            # exige pelo menos metade dos MUST
            # quando os metadados são confiáveis.

            if (
                confiavel
                and cobertura < 0.50
            ):
                return False


    else:

        # Retry pode relaxar,
        # mas um resultado confiável ainda
        # precisa representar algo do MUST.

        if (
            confiavel
            and must_hits == 0
        ):
            return False


    return True



# ==================================================
# SCENE DIVERSITY GUARD 2.4.1
# ==================================================

def score_diversidade(
    candidato,
    descricao_anterior
):

    if not descricao_anterior:
        return 0.0

    atual = str(
        candidato.get(
            "descricao",
            ""
        )
    )

    if not atual:
        return 0.0

    sim = similaridade_conjuntos(
        atual,
        descricao_anterior
    )

    # Quanto mais parecido com a cena anterior,
    # maior a penalidade.
    if sim >= 0.75:
        return -28.0

    if sim >= 0.55:
        return -18.0

    if sim >= 0.35:
        return -9.0

    return 0.0


def score_semantico(
    candidato,
    total_must,
    descricao_anterior=""


):

    score = float(
        candidato.get(
            "score",
            -999
        )
    )

    cobertura = cobertura_must(
        candidato,
        total_must
    )

    confiavel = metadata_confiavel(
        candidato
    )


    # Bônus explícito por cobertura.
    score += cobertura * 35


    if confiavel:

        score += 12

    else:

        # Pexels vídeo continua permitido,
        # porém sua relevância não é
        # considerada comprovada.
        score -= 38


    score += score_diversidade(
        candidato,
        descricao_anterior
    )


    return score


def preparar_candidatos(
    candidatos,
    total_must,
    relaxado=False,
    descricao_anterior=""
):

    validos = [
        c
        for c in candidatos
        if candidato_semanticamente_valido(
            c,
            total_must,
            relaxado=relaxado
        )
    ]

    if not validos:
        return []


    # ----------------------------------
    # PROTEÇÃO CONTRA PEXELS VÍDEO
    # ----------------------------------
    #
    # Se existe mídia com metadados
    # confiáveis e cobertura boa dos MUST,
    # Pexels vídeo incerto não participa
    # da decisão final.

    confiaveis_fortes = [
        c
        for c in validos
        if (
            metadata_confiavel(c)
            and (
                total_must == 0
                or cobertura_must(
                    c,
                    total_must
                ) >= 0.50
            )
        )
    ]


    if confiaveis_fortes:

        validos = [
            c
            for c in validos
            if metadata_confiavel(c)
        ]


    for c in validos:

        c[
            "_semantic_score"
        ] = score_semantico(
            c,
            total_must,
            descricao_anterior
        )


    validos.sort(
        key=lambda c: (
            c.get(
                "must_hits",
                0
            ),

            1
            if metadata_confiavel(c)
            else 0,

            c.get(
                "_semantic_score",
                -999
            )
        ),
        reverse=True
    )


    return validos




# =====================================================
# DOCUMENTARY PROVENANCE PRIORITY LOCK 5.4.2
# =====================================================

def documentary_provenance_rank_5_4_2(
    candidato
):

    tier = str(
        candidato.get(
            "wiki_query_tier",
            ""
        )
    )


    fallback_tiers = {
        "CASE": 6,
        "CASE_VISUAL": 5,
        "CONTEXT_COMBINED": 5,
        "CONTEXT": 4,
        "CONTEXT_VISUAL": 3,
        "GENERIC": 1
    }


    tier_rank = int(
        candidato.get(
            "wiki_query_tier_rank",
            fallback_tiers.get(
                tier,
                0
            )
        )
        or 0
    )


    anchor_ok = int(
        bool(
            candidato.get(
                "wiki_anchor_ok",
                False
            )
        )
    )


    try:

        anchor_ratio = float(
            candidato.get(
                "wiki_anchor_ratio",
                0.0
            )
            or 0.0
        )

    except Exception:

        anchor_ratio = 0.0


    try:

        semantic = float(
            candidato.get(
                "_semantic_score",
                candidato.get(
                    "score",
                    -999
                )
            )
        )

    except Exception:

        semantic = -999.0


    must_hits = int(
        candidato.get(
            "must_hits",
            0
        )
        or 0
    )


    evidence = str(
        candidato.get(
            "evidence_class",
            ""
        )
    )


    evidence_rank = {
        "CASE_DIRECT": 3,
        "CONTEXTUAL": 2
    }.get(
        evidence,
        0
    )


    return (
        evidence_rank,
        tier_rank,
        anchor_ok,
        anchor_ratio,
        must_hits,
        semantic
    )


def ordenar_documentais_5_4_2(
    candidatos
):

    return sorted(
        candidatos,
        key=documentary_provenance_rank_5_4_2,
        reverse=True
    )



# =====================================================
# DOCUMENTARY SOURCE PRESELECTION 4.2
# =====================================================

def escolher_documental_prioritario(
    candidatos,
    rota_fonte,
    total_must,
    descricao_anterior=""
):

    if not candidatos:
        return None


    if rota_fonte.get(
        "route"
    ) != "documentary_first":

        return None


    # Usa apenas candidatos que já passaram
    # pelo Evidence Authenticity Guard.
    wiki = [
        c
        for c in candidatos
        if (
            c.get(
                "fonte"
            ) == "Wikimedia"
            and c.get(
                "evidence_class"
            )
            in {
                "CASE_DIRECT",
                "CONTEXTUAL"
            }
        )
    ]


    if not wiki:
        return None


    # Aplica o mesmo Semantic Guard usado
    # pelo restante do seletor.
    wiki_validos = preparar_candidatos(
        wiki,
        total_must,
        relaxado=False,
        descricao_anterior=descricao_anterior
    )


    if not wiki_validos:

        wiki_validos = preparar_candidatos(
            wiki,
            total_must,
            relaxado=True,
            descricao_anterior=descricao_anterior
        )


    if not wiki_validos:
        return None


    # ---------------------------------
    # 1. CASE DIRECT
    # ---------------------------------

    diretos = [
        c
        for c in wiki_validos
        if c.get(
            "evidence_class"
        ) == "CASE_DIRECT"
    ]



    diretos = ordenar_documentais_5_4_2(
        diretos
    )

    if diretos:

        melhor = diretos[0]

        cobertura = cobertura_must(
            melhor,
            total_must
        )

        topic_match = float(
            melhor.get(
                "topic_overlap",
                0.0
            )
        )


        # Ativo diretamente relacionado
        # ao caso pode ser usado mesmo quando
        # o MUST representa outro detalhe,
        # mas exige forte identidade temática.
        if (
            cobertura >= 0.50
            or topic_match >= 0.75
        ):

            return melhor


    # ---------------------------------
    # 2. CONTEXTUAL
    # ---------------------------------

    contextuais = [
        c
        for c in wiki_validos
        if c.get(
            "evidence_class"
        ) == "CONTEXTUAL"
    ]



    contextuais = ordenar_documentais_5_4_2(
        contextuais
    )

    if contextuais:

        melhor = contextuais[0]

        cobertura = cobertura_must(
            melhor,
            total_must
        )

        semantic_score = float(
            melhor.get(
                "_semantic_score",
                melhor.get(
                    "score",
                    -999
                )
            )
        )


        if (
            cobertura >= 0.50
            and semantic_score >= 65
        ):

            print(
                "  DOCUMENTARY PROVENANCE 5.4.2: "
                f"{melhor.get('wiki_query_tier', '?')} "
                f"anchor="
                f"{melhor.get('wiki_anchor_ratio', 0.0) * 100:.0f}% "
                f"query="
                f"{melhor.get('wiki_query', '?')}"
            )

            return melhor


    return None


def escolher_relaxado(
    candidatos,
    total_must=None
):

    if not candidatos:
        return None


    if total_must is None:

        total_must = max(
            [
                c.get(
                    "must_hits",
                    0
                )
                for c in candidatos
            ]
            + [0]
        )


    validos = preparar_candidatos(
        candidatos,
        total_must,
        relaxado=True
    )


    if not validos:
        return None


    return validos[0]


def escolher_com_movimento(
    candidatos,
    total_must,
    videos_total,
    cenas_restantes,
    descricao_anterior=""
):

    if not candidatos:
        return None


    validos = preparar_candidatos(
        candidatos,
        total_must,
        relaxado=False,
        descricao_anterior=descricao_anterior
    )


    if not validos:

        validos = preparar_candidatos(
            candidatos,
            total_must,
            relaxado=True,
            descricao_anterior=descricao_anterior
        )


    if not validos:
        return None


    melhor = validos[0]


    # ----------------------------------
    # META DE MOVIMENTO
    # ----------------------------------

    videos_faltando = max(
        0,
        VIDEO_META - videos_total
    )


    if videos_faltando <= 0:

        return melhor


    videos = [
        c
        for c in validos
        if c.get(
            "tipo"
        ) == "vídeo"
    ]


    if not videos:

        return melhor


    melhor_video = videos[0]


    # ----------------------------------
    # REGRA PRINCIPAL
    # ----------------------------------
    #
    # Movimento nunca pode custar
    # cobertura semântica.

    if (
        melhor_video.get(
            "must_hits",
            0
        )
        < melhor.get(
            "must_hits",
            0
        )
    ):

        return melhor


    # Pexels vídeo com metadata fraca
    # não substitui uma mídia confiável
    # semanticamente equivalente.

    if (
        not metadata_confiavel(
            melhor_video
        )
        and metadata_confiavel(
            melhor
        )
    ):

        return melhor


    diferenca = (
        melhor.get(
            "_semantic_score",
            melhor.get(
                "score",
                -999
            )
        )
        -
        melhor_video.get(
            "_semantic_score",
            melhor_video.get(
                "score",
                -999
            )
        )
    )


    # Só usa o bônus de movimento
    # quando os candidatos já são
    # semanticamente comparáveis.

    if diferenca <= VIDEO_TOLERANCIA:

        melhor_video[
            "_semantic_score"
        ] = (
            melhor_video.get(
                "_semantic_score",
                melhor_video.get(
                    "score",
                    0
                )
            )
            + VIDEO_BONUS
        )

        return melhor_video


    return melhor




# ==================================================
# DOCUMENTARY AUTHENTICITY CORE 5.2
# ==================================================

EVIDENCE_RANK_5_2 = {
    "CASE_DIRECT": 5,
    "CONTEXTUAL": 4,
    "GENERIC_DOCUMENT": 2,
    "GENERIC": 1,
    "STOCK": 0,
    "RISKY_IDENTITY": -5
}


def score_real_5_2(candidato):

    try:

        return float(
            candidato.get(
                "_semantic_score",
                candidato.get(
                    "score",
                    -999
                )
            )
        )

    except Exception:

        return -999.0


def chave_candidato_5_2(candidato):

    return (
        str(
            candidato.get(
                "fonte",
                ""
            )
        ),

        str(
            candidato.get(
                "id",
                ""
            )
        ),

        str(
            candidato.get(
                "url",
                ""
            )
        )
    )


def evidence_rank_5_2(candidato):

    return EVIDENCE_RANK_5_2.get(
        str(
            candidato.get(
                "evidence_class",
                ""
            )
        ),
        0
    )


def enriquecer_wikimedia_5_2(
    candidatos,
    rota_fonte,
    segmento,
    must_have,
    visual_mode
):

    saida = []

    aprovados = 0
    rejeitados = 0

    classes = {}


    for candidato in candidatos:

        if candidato.get(
            "fonte"
        ) != "Wikimedia":

            saida.append(
                candidato
            )

            continue


        if candidato.get(
            "_evidence_guard_5_2"
        ):

            saida.append(
                candidato
            )

            continue


        try:

            ev = avaliar_evidencia(
                candidato,
                ASSUNTO,
                segmento,
                must_have,
                visual_mode
            )

        except Exception as e:

            rejeitados += 1

            print(
                f"  WIKIMEDIA EVIDENCE ERROR: "
                f"{type(e).__name__}: "
                f"{str(e)[:120]}"
            )

            continue


        classe = ev.get(
            "class",
            "GENERIC"
        )

        candidato[
            "evidence_class"
        ] = classe

        candidato[
            "topic_overlap"
        ] = float(
            ev.get(
                "topic_overlap",
                0.0
            )
        )

        candidato[
            "segment_overlap"
        ] = float(
            ev.get(
                "segment_overlap",
                0.0
            )
        )

        candidato[
            "evidence_must_coverage"
        ] = float(
            ev.get(
                "must_coverage",
                0.0
            )
        )

        candidato[
            "_evidence_guard_5_2"
        ] = True


        classes[
            classe
        ] = (
            classes.get(
                classe,
                0
            )
            + 1
        )


        if not ev.get(
            "allowed",
            False
        ):

            rejeitados += 1

            continue


        candidato[
            "score"
        ] = (
            float(
                candidato.get(
                    "score",
                    0.0
                )
            )
            + float(
                rota_fonte.get(
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


        aprovados += 1

        saida.append(
            candidato
        )


    if aprovados or rejeitados:

        print(
            f"  WIKIMEDIA EVIDENCE: "
            f"{aprovados} aprovados / "
            f"{rejeitados} rejeitados"
        )


        if classes:

            resumo = ", ".join(
                f"{k}={v}"
                for k, v
                in sorted(
                    classes.items()
                )
            )

            print(
                f"  EVIDENCE CLASSES: "
                f"{resumo}"
            )


    return saida


def ordenar_failover_5_2(
    candidatos,
    total_must,
    rota_fonte,
    descricao_anterior=""
):

    if not candidatos:
        return []


    validos = preparar_candidatos(
        candidatos,
        total_must,
        relaxado=False,
        descricao_anterior=
            descricao_anterior
    )


    if not validos:

        validos = preparar_candidatos(
            candidatos,
            total_must,
            relaxado=True,
            descricao_anterior=
                descricao_anterior
        )


    documental = (
        rota_fonte.get(
            "route"
        )
        == "documentary_first"
    )


    validos.sort(
        key=lambda c: (
            (
                evidence_rank_5_2(c)
                if (
                    documental
                    and c.get(
                        "fonte"
                    )
                    == "Wikimedia"
                )
                else 0
            ),

            c.get(
                "must_hits",
                0
            ),

            -c.get(
                "avoid_hits",
                0
            ),

            score_real_5_2(c)
        ),
        reverse=True
    )


    saida = []
    vistos = set()


    for candidato in validos:

        chave = chave_candidato_5_2(
            candidato
        )

        if chave in vistos:
            continue

        vistos.add(
            chave
        )

        saida.append(
            candidato
        )


    return saida


def fallback_preserva_5_2(
    candidato,
    referencia
):

    if referencia is None:
        return True


    must_c = int(
        candidato.get(
            "must_hits",
            0
        )
        or 0
    )

    must_r = int(
        referencia.get(
            "must_hits",
            0
        )
        or 0
    )


    if must_c < must_r:
        return False


    avoid_c = int(
        candidato.get(
            "avoid_hits",
            0
        )
        or 0
    )

    avoid_r = int(
        referencia.get(
            "avoid_hits",
            0
        )
        or 0
    )


    if avoid_c > avoid_r:
        return False


    score_c = score_real_5_2(
        candidato
    )

    score_r = score_real_5_2(
        referencia
    )


    tolerancia = max(
        28.0,
        abs(score_r) * 0.20
    )


    return (
        score_c
        >= score_r - tolerancia
    )


def fallback_degradado_ok_5_2(
    candidato,
    total_must
):

    if int(
        candidato.get(
            "avoid_hits",
            0
        )
        or 0
    ) > 0:

        return False


    must = int(
        candidato.get(
            "must_hits",
            0
        )
        or 0
    )


    if total_must:

        if (
            must
            / total_must
        ) < 0.50:

            return False


    return (
        score_real_5_2(
            candidato
        )
        >= 40
    )



def _sap_professional_media_accept_v1(candidato, destino):
    if str(os.getenv("SAP_PRO_EDIT", "0")).strip() != "1":
        return True

    try:
        floor = int(os.getenv("SAP_PRO_MEDIA_MIN_PIXELS", str(1280 * 720)))
    except (TypeError, ValueError):
        floor = 1280 * 720

    floor = max(320 * 180, min(floor, 3840 * 2160))

    try:
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "json", destino,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if probe.returncode != 0:
            raise RuntimeError("ffprobe_failed")
        payload = json.loads(probe.stdout)
        streams = payload.get("streams", [])
        if not streams:
            raise RuntimeError("visual_stream_missing")
        width = int(streams[0].get("width", 0) or 0)
        height = int(streams[0].get("height", 0) or 0)
    except Exception as exc:
        print(
            "    PRO_MEDIA_FLOOR=REJECT probe="
            + type(exc).__name__
            + ":"
            + str(exc)
        )
        try:
            os.remove(destino)
        except OSError:
            pass
        return False

    pixels = width * height
    if pixels >= floor:
        print(
            f"    PRO_MEDIA_FLOOR=PASS dimensions={width}x{height} "
            f"pixels={pixels} floor={floor}"
        )
        return True

    source_name = str(candidato.get("fonte", "")).strip().lower()
    evidence_class = str(candidato.get("evidence_class", "")).strip().upper()
    if source_name == "wikimedia" and evidence_class == "CASE_DIRECT":
        print(
            f"    PRO_MEDIA_FLOOR=EVIDENCE_EXCEPTION dimensions={width}x{height} "
            f"pixels={pixels} floor={floor} class={evidence_class}"
        )
        candidato["_professional_resolution_exception"] = True
        return True

    print(
        f"    PRO_MEDIA_FLOOR=REJECT dimensions={width}x{height} "
        f"pixels={pixels} floor={floor} source={candidato.get('fonte', '?')} "
        f"evidence={evidence_class or 'NONE'}"
    )
    try:
        os.remove(destino)
    except OSError:
        pass
    return False

def baixar_candidato_5_2(
    candidato,
    numero,
    rotulo
):

    ext = (
        ".mp4"
        if candidato.get(
            "tipo"
        ) == "vídeo"
        else ".jpg"
    )


    destino = os.path.join(
        SAIDA_DIR,
        f"scene_{numero:02d}{ext}"
    )


    print(
        f"  {rotulo}: "
        f"{candidato.get('fonte', '?')} / "
        f"{candidato.get('tipo', '?')} "
        f"score="
        f"{score_real_5_2(candidato):.1f} "
        f"must="
        f"{candidato.get('must_hits', 0)}"
    )


    if candidato.get(
        "fonte"
    ) == "Wikimedia":

        print(
            f"    EVIDENCE="
            f"{candidato.get('evidence_class', '?')} "
            f"topic="
            f"{candidato.get('topic_overlap', 0.0) * 100:.0f}% "
            f"segment="
            f"{candidato.get('segment_overlap', 0.0) * 100:.0f}%"
        )


    ok = baixar(
        candidato.get(
            "url",
            ""
        ),
        destino
    )

    if ok:
        ok = _sap_professional_media_accept_v1(
            candidato,
            destino
        )


    print(
        "    DOWNLOAD: "
        + (
            "OK"
            if ok
            else "FALHOU"
        )
    )


    return ok, destino


# SHORTAUTOPRO SOURCE PROVENANCE EARLY HOOK V1
from media_provenance_capture_v1 import (
    install as _sap_install_source_provenance_early_v1,
)

_sap_install_source_provenance_early_v1(
    globals()
)


# SHORTAUTOPRO MEDIA DIVERSITY GUARD V1
from media_diversity_guard_v1 import (
    install as _sap_install_media_diversity_v1,
)

_sap_install_media_diversity_v1(
    globals()
)





# ==================================================
# VISUAL INTELLIGENCE 6.3 ACTIVE
# ==================================================

VI6_MODE = str(
    os.getenv(
        "VISUAL_INTELLIGENCE_MODE",
        "SHADOW"
    )
).strip().upper()


if VI6_MODE not in {
    "OFF",
    "SHADOW",
    "ACTIVE"
}:
    VI6_MODE = "SHADOW"


def reencontrar_vi6_original_6_3(
    winner,
    candidatos
):
    if not winner:
        return None

    fonte = str(
        winner.get(
            "fonte",
            ""
        )
    )

    ident = str(
        winner.get(
            "id",
            ""
        )
    )

    url = str(
        winner.get(
            "url",
            ""
        )
    )


    # match exato
    for c in candidatos:

        if (
            str(
                c.get(
                    "fonte",
                    ""
                )
            ) == fonte
            and str(
                c.get(
                    "id",
                    ""
                )
            ) == ident
            and str(
                c.get(
                    "url",
                    ""
                )
            ) == url
        ):
            return c


    # fallback fonte + id
    if ident:

        matches = [
            c
            for c in candidatos
            if (
                str(
                    c.get(
                        "fonte",
                        ""
                    )
                ) == fonte
                and str(
                    c.get(
                        "id",
                        ""
                    )
                ) == ident
            )
        ]

        if len(matches) == 1:
            return matches[0]


        for c in matches:

            if (
                url
                and str(
                    c.get(
                        "url",
                        ""
                    )
                ) == url
            ):
                return c


    return None


def decidir_vi6_3_active(
    vi6_scene,
    candidatos
):

    if VI6_MODE != "ACTIVE":

        return (
            None,
            "not_active"
        )


    if not vi6_scene:

        return (
            None,
            "no_vi6_scene"
        )


    if vi6_scene.get(
        "fallback_to_5x",
        False
    ):

        return (
            None,
            "quality_floor_fallback"
        )


    winner = (
        vi6_scene.get(
            "winner"
        )
        or {}
    )


    if not winner:

        return (
            None,
            "no_winner"
        )


    if winner.get(
        "blocked",
        False
    ):

        return (
            None,
            "blocked"
        )


    classe = str(
        winner.get(
            "class",
            ""
        )
    ).upper()


    risk = str(
        winner.get(
            "risk",
            ""
        )
    ).upper()


    quality = str(
        winner.get(
            "quality_tier",
            ""
        )
    ).upper()


    truth_ok = bool(
        winner.get(
            "truth_ok",
            False
        )
    )


    if (
        "MISLEADING" in classe
        or risk == "HIGH"
    ):

        return (
            None,
            "risk_block"
        )


    if quality not in {
        "NORMAL",
        "CONTROLLED_FALLBACK"
    }:

        return (
            None,
            f"quality_{quality or 'missing'}"
        )


    # primeira ativação conservadora
    if classe not in {
        "REAL_DOCUMENTARY",
        "SAFE_CONTEXT"
    }:

        return (
            None,
            f"class_{classe or 'unknown'}"
        )


    if (
        classe == "REAL_DOCUMENTARY"
        and not truth_ok
    ):

        return (
            None,
            "truth_anchor_failed"
        )


    original = reencontrar_vi6_original_6_3(
        winner,
        candidatos
    )


    if original is None:

        return (
            None,
            "original_not_found"
        )


    original[
        "_vi6_active_6_3"
    ] = True

    original[
        "_vi6_class"
    ] = classe

    original[
        "_vi6_risk"
    ] = risk

    original[
        "_vi6_quality_tier"
    ] = quality

    original[
        "_vi6_truth_ok"
    ] = truth_ok

    original[
        "_vi6_score"
    ] = winner.get(
        "score"
    )

    original[
        "_vi6_reason"
    ] = winner.get(
        "reason"
    )


    return (
        original,
        "vi6_active_winner"
    )

# SHORTAUTOPRO VISUAL GATE V4X BRIDGE
try:
    from vg4x_bridge import install as _vg4x_install_bridge
    _VG4X_BRIDGE_RESULT = _vg4x_install_bridge(globals())
except Exception as _vg4x_bridge_error:
    print(
        "VG4X_BRIDGE=FAIL_OPEN "
        + type(_vg4x_bridge_error).__name__
        + ":"
        + str(_vg4x_bridge_error)
    )



# ==================================================
# EXECUÇÃO
# ==================================================

print()
print("================================")
print("VISUAL SEMANTIC GUARD 2.3.1")
print("================================")
print()

print(
    f"Meta vídeos: "
    f"{VIDEO_META}/{len(cenas)}"
)

print(
    f"Tolerância vídeo: "
    f"{VIDEO_TOLERANCIA:.1f}"
)

print()


total = 0
videos_total = 0
fotos_total = 0
missing_scenes = []

descricao_anterior = ""


# ==================================================
# VISUAL INTELLIGENCE 6.0 - SHADOW STATE
# ==================================================

VI6_SHADOW = (
    os.getenv(
        "VISUAL_INTELLIGENCE_6_SHADOW",
        "1"
    )
    != "0"
)

vi6_history = []
vi6_scenes = []

contagem = {
    "Pexels": 0,
    "Pixabay": 0,
    "Coverr": 0,
    "Wikimedia": 0,
    "Local": 0
}


for numero, cena in enumerate(
    cenas,
    start=1
):

    busca = str(
        cena.get(
            "query",
            ""
        )
    ).strip()

    must_have = [
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


    print()
    print(
        f"[{numero}/{len(cenas)}] "
        f"{busca}"
    )

    print(
        f"  MUST: "
        f"{', '.join(must_have)}"
    )


    # =================================
    # TODAS AS FONTES COMPETEM
    # =================================

    todos = []

    segmento = str(
        cena.get(
            "segment",
            ""
        )
    ).strip()

    visual_mode = str(
        cena.get(
            "visual_mode",
            ""
        )
    ).strip()


    rota_fonte = escolher_rota(
        visual_mode,
        must_have
    )

    print(
        f"  SOURCE ROUTE: "
        f"{rota_fonte['route']}"
    )


    try:

        todos.extend(
            buscar_wikimedia_fotos(
                busca,
                must_have,
                avoid,
                assunto=ASSUNTO,
                segmento=segmento,
                visual_mode=visual_mode
            )
        )

    except Exception:

        pass


    if USAR_VIDEOS:

        todos.extend(
            pexels_video(
                busca,
                must_have,
                avoid
            )
        )

        todos.extend(
            pixabay_video(
                busca,
                must_have,
                avoid
            )
        )

        todos.extend(
            coverr_video(
                busca,
                must_have,
                avoid
            )
        )


    todos.extend(
        pexels_foto(
            busca,
            must_have,
            avoid
        )
    )

    todos.extend(
        pixabay_foto(
            busca,
            must_have,
            avoid
        )
    )

    # =================================
    # MAIN WIKIMEDIA EVIDENCE 5.2
    # =================================

    todos = enriquecer_wikimedia_5_2(
        todos,
        rota_fonte,
        segmento,
        must_have,
        visual_mode
    )

    stock_penalty = rota_fonte.get(
        "stock_penalty",
        0.0
    )

    if stock_penalty:

        for candidato in todos:

            if candidato.get(
                "fonte"
            ) in {
                "Pexels",
                "Pixabay",
                "Coverr"
            }:

                candidato[
                    "score"
                ] += stock_penalty


    # =================================
    # =================================
    # VISUAL INTELLIGENCE 6.0
    # SHADOW STORYBOARD
    # =================================

    vi6_scene = None

    if (
        VI6_SHADOW
        or VI6_MODE == "ACTIVE"
    ):

        try:

            vi6_scene = vi6_audit_scene(
                numero,
                len(cenas),
                cena,
                todos,
                vi6_history,
                videos_total,
                VIDEO_META
            )

            vi6_scenes.append(
                vi6_scene
            )

            vi6_winner = (
                vi6_scene.get(
                    "winner"
                )
                or {}
            )

            print()
            print(
                "  VI6 SHADOW:"
            )

            print(
                f"    INTENT="
                f"{vi6_scene.get('intent', '?')}"
            )

            if vi6_winner:

                print(
                    f"    WINNER="
                    f"{vi6_winner.get('fonte', '?')} / "
                    f"{vi6_winner.get('tipo', '?')}"
                )

                print(
                    f"    CLASS="
                    f"{vi6_winner.get('class', '?')} "
                    f"RISK="
                    f"{vi6_winner.get('risk', '?')}"
                )

                print(
                    f"    SCORE="
                    f"{vi6_winner.get('score', 0):.1f} "
                    f"SEM="
                    f"{vi6_winner.get('semantic', 0):.1f} "
                    f"PROV="
                    f"{vi6_winner.get('provenance', 0):.1f}"
                )

                print(
                    f"    CONT="
                    f"{vi6_winner.get('continuity', 0):.1f} "
                    f"DIV="
                    f"{vi6_winner.get('diversity', 0):.1f} "
                    f"MOTION="
                    f"{vi6_winner.get('motion', 0):.1f}"
                )

                print(
                    f"    REASON="
                    f"{vi6_winner.get('reason', '?')}"
                )

                if vi6_winner.get(
                    "reuse"
                ):

                    print(
                        "    CTA REUSE: YES"
                    )

            for item in (
                vi6_scene.get(
                    "top",
                    []
                )[1:5]
            ):

                if item.get(
                    "class"
                ) == "MISLEADING_REENACTMENT":

                    print(
                        f"    REJECT/RISK: "
                        f"{item.get('fonte', '?')} / "
                        f"{item.get('tipo', '?')} "
                        f"reason="
                        f"{item.get('reason', '?')}"
                    )

            vi6_push_history(
                vi6_scene,
                vi6_history
            )

            vi6_path, vi6_summary = (
                vi6_salvar_report(
                    SHORT_ID,
                    vi6_scenes
                )
            )

            print(
                f"    STORYBOARD="
                f"{vi6_summary.get('storyboard_score', 0)}/100"
            )

        except Exception as e:

            print(
                f"  VI6 SHADOW ERROR: "
                f"{type(e).__name__}: "
                f"{str(e)[:160]}"
            )

    # WIKIMEDIA DIAGNOSTIC 4.2
    # =================================

    wiki_lista = [
        c
        for c in todos
        if c.get(
            "fonte"
        ) == "Wikimedia"
    ]


    print(
        f"  WIKIMEDIA CANDIDATOS: "
        f"{len(wiki_lista)}"
    )


    if wiki_lista:

        wiki_top = sorted(
            wiki_lista,
            key=lambda c: (
                c.get(
                    "must_hits",
                    0
                ),
                c.get(
                    "_semantic_score",
                    c.get(
                        "score",
                        -999
                    )
                )
            ),
            reverse=True
        )[:2]


        for pos_wiki, item in enumerate(
            wiki_top,
            start=1
        ):

            print(
                f"  WIKI{pos_wiki}: "
                f"{item.get('evidence_class', '?')} "
                f"score="
                f"{item.get('score', 0):.1f} "
                f"must="
                f"{item.get('must_hits', 0)}/"
                f"{len(must_have)} "
                f"topic="
                f"{item.get('topic_overlap', 0.0) * 100:.0f}%"
            )


    # =================================
    # TOP 3 BRUTO
    # =================================

    todos.sort(
        key=lambda x: (
            x["must_hits"],
            -x["avoid_hits"],
            x["score"]
        ),
        reverse=True
    )


    for pos, c in enumerate(
        todos[:3],
        1
    ):

        print(
            f"  TOP{pos}: "
            f"{c['fonte']} "
            f"{c['tipo']} "
            f"score={c['score']:.1f} "
            f"must={c['must_hits']}/"
            f"{len(must_have)}"
        )


    cenas_restantes = (
        len(cenas)
        - numero
        + 1
    )


    escolhido = (
        escolher_documental_prioritario(
            todos,
            rota_fonte,
            len(must_have),
            descricao_anterior
        )
    )


    if escolhido:

        print(
            "  DOCUMENTARY PRIORITY: ATIVADA"
        )

        print(
            f"  EVIDENCE CLASS: "
            f"{escolhido.get('evidence_class', '?')}"
        )

        print(
            f"  TOPIC MATCH: "
            f"{escolhido.get('topic_overlap', 0.0) * 100:.0f}%"
        )

    else:
        escolhido = escolher_com_movimento(
            todos,
            len(must_have),
            videos_total,
            cenas_restantes,
            descricao_anterior
        )



    # =================================
    # VI6.3 ACTIVE MEDIA BRAIN
    # =================================

    vi6_active_candidate = None
    vi6_active_reason = "not_evaluated"

    if VI6_MODE == "ACTIVE":

        vi6_active_candidate, vi6_active_reason = (
            decidir_vi6_3_active(
                vi6_scene,
                todos
            )
        )

        # =========================================
        # VI6.6 STANDALONE ACTIVE SUPERVISOR
        # =========================================

        from vi6_6_active_brain import (
            supervisionar_vi6_6
        )

        (
            vi6_active_candidate,
            vi6_active_reason,
            vi66_meta
        ) = supervisionar_vi6_6(
            vi6_scene,
            todos,
            cena,
            vi6_active_candidate,
            vi6_active_reason
        )

        print(
            "  VI6.6 SUPERVISOR:"
        )

        print(
            f"    DECISION="
            f"{vi66_meta.get('decision', '?')}"
        )

        print(
            f"    REASON="
            f"{vi6_active_reason}"
        )

        if vi66_meta.get('score') is not None:
            print(
                f"    SCORE="
                f"{vi66_meta.get('score')}"
            )

        if vi66_meta.get('role'):
            print(
                f"    ROLE="
                f"{vi66_meta.get('role')}"
            )

        if vi66_meta.get('anchor') is not None:
            print(
                f"    ANCHOR="
                f"{vi66_meta.get('anchor')}"
            )


        print()
        print(
            "  VI6.3 ACTIVE DECISION:"
        )

        print(
            f"    REASON="
            f"{vi6_active_reason}"
        )


        if vi6_active_candidate is not None:

            escolhido = (
                vi6_active_candidate
            )

            print(
                "    DECISION=VI6"
            )

            print(
                f"    ACTIVE WINNER="
                f"{escolhido.get('fonte', '?')} / "
                f"{escolhido.get('tipo', '?')}"
            )

            print(
                f"    CLASS="
                f"{escolhido.get('_vi6_class', '?')} "
                f"RISK="
                f"{escolhido.get('_vi6_risk', '?')}"
            )

            print(
                f"    QUALITY="
                f"{escolhido.get('_vi6_quality_tier', '?')} "
                f"TRUTH_OK="
                f"{escolhido.get('_vi6_truth_ok', False)}"
            )

            print(
                f"    VI6_SCORE="
                f"{escolhido.get('_vi6_score', '?')}"
            )

        else:

            print(
                "    DECISION=5X_FALLBACK"
            )


    sucesso = False
    destino = None

    referencia = escolhido

    falhas_download = set()
    degradados = []


    # =================================
    # PRIMEIRA TENTATIVA
    # + FAILOVER DE MESMA QUALIDADE
    # =================================

    if escolhido:

        # SHORTAUTOPRO VSE4.17 FINAL GATE
        try:
            from visual_selection_engine_v4 import choose_from_context as _vse417_choose
            _vse417_before = escolhido
            escolhido = _vse417_choose(locals(), globals(), escolhido)
            if escolhido is not _vse417_before:
                print('VSE417_REAL_OVERRIDE=YES')
            else:
                print('VSE417_REAL_OVERRIDE=NO')
        except Exception as _vse417_exc:
            print(f'VSE417_FAIL_OPEN={type(_vse417_exc).__name__}: {_vse417_exc}')
        
        pool = ordenar_failover_5_2(
            todos,
            len(must_have),
            rota_fonte,
            descricao_anterior
        )
        # SHORTAUTOPRO VISUAL UNIFIED V5 RERANK
        try:
            from visual_engine_unified import rerank_pool_runtime as _sap_visual_rerank
            pool = _sap_visual_rerank(pool, locals())
        except Exception as _sap_visual_error:
            print(f"VISUAL_UNIFIED_RERANK=FAIL_OPEN {type(_sap_visual_error).__name__}: {_sap_visual_error}")

        # SHORTAUTOPRO VSE42 FINAL GATE
        try:
            from visual_selection_runtime_v42 import (
                enhance_selection as _vse42_enhance_selection,
            )
        
            escolhido, pool, _vse42_meta = (
                _vse42_enhance_selection(
                    escolhido,
                    pool,
                    locals(),
                    buscar_todos_candidatos,
                )
            )
        
            print(
                "VSE42_OVERRIDE_ACTIVE=YES"
            )
        
        except Exception as _vse42_exc:
        
            print(
                "VSE42_FAIL_OPEN="
                + type(_vse42_exc).__name__
                + ": "
                + str(_vse42_exc)
            )

        # SHORTAUTOPRO VSE42 PRIMARY RANK
        try:
            from visual_selection_bridge_v42 import rank_pool as _vse42_rank_pool
            pool, escolhido, _vse42_meta = _vse42_rank_pool(
                pool,
                escolhido,
                locals(),
            )
            if escolhido is not None:
                referencia = escolhido
        except Exception as _vse42_exc:
            print(
                "  VSE42_FAIL_OPEN_PRIMARY="
                + type(_vse42_exc).__name__
                + ":"
                + str(_vse42_exc)
            )


        # Escolha original sempre primeiro.
        
        # SHORTAUTOPRO VISUAL GATE V4X FINAL DECISION
        try:
            from visual_gate_v4x import choose_from_locals as _vg4x_choose_from_locals
            escolhido, pool, _vg4x_meta = _vg4x_choose_from_locals(
                locals(),
                pool,
                escolhido,
            )
        except Exception as _vg4x_gate_error:
            print(
                "VG4X_FINAL_GATE=FAIL_OPEN "
                + type(_vg4x_gate_error).__name__
                + ":"
                + str(_vg4x_gate_error)
            )
        
        # SHORTAUTOPRO VSE42 FINAL POOL
        pool = _vse42_finalize_pool(pool, escolhido, locals())

        # SHORTAUTOPRO VSE4.2 FINAL POOL GATE
        try:
            import os as _sap_visual_os_v42
            if _sap_visual_os_v42.getenv('SAP_VSE4', '1') != '0':
                from media_diversity_guard_v1 import install_runtime as _sap_visual_install_v42
                from media_diversity_guard_v1 import rerank_pool as _sap_visual_rerank_v42
                _sap_visual_install_v42(globals())
                pool = _sap_visual_rerank_v42(
                    pool,
                    locals(),
                    escolhido,
                )

                # SHORTAUTOPRO VSE42 FINAL RERANK
                try:
                    from visual_selection_runtime_bridge_v42 import rerank_pool as _sap_vse42_rerank_pool
                    pool, _sap_vse42_meta = _sap_vse42_rerank_pool(pool, locals())
                    if pool:
                        escolhido = pool[0]
                    print("VSE42_RERANK=PASS " + str(_sap_vse42_meta.get("summary", "")))
                    if _sap_vse42_meta.get("rescue_needed"):
                        print("VSE42_RESCUE_NEEDED=YES")
                except Exception as _sap_vse42_exc:
                    print(f"VSE42_RERANK=FAIL_OPEN {type(_sap_vse42_exc).__name__}: {_sap_vse42_exc}")
                if pool:
                    escolhido = pool[0]
                    print('VSE42_FINAL_POOL_GATE=PASS')
                else:
                    print('VSE42_FINAL_POOL_GATE=EMPTY_FAIL_OPEN')
            else:
                print('VSE42_FINAL_POOL_GATE=DISABLED')
        except Exception as _sap_visual_error_v42:
            print(
                'VSE42_FINAL_POOL_GATE=FAIL_OPEN ' +
                type(_sap_visual_error_v42).__name__ +
                ': ' +
                str(_sap_visual_error_v42)
            )

        # SHORTAUTOPRO VISUAL STACK FINAL POOL V2
        try:
            from media_diversity_guard_v1 import install_runtime as _sap_visual_install_v2
            from media_diversity_guard_v1 import rerank_pool as _sap_visual_rerank_v2
            _sap_visual_install_v2(globals())
            # SHORTAUTOPRO VSE42 SINGLE FINALIZER V1
            # Legacy rerank bypassed: VSE4.2 final pool is authoritative.
        except Exception as _sap_visual_stack_error:
            print(
                'VISUAL_STACK_FAILOPEN=' +
                type(_sap_visual_stack_error).__name__ +
                ':' + str(_sap_visual_stack_error)
            )


        for candidato in pool:

            chave = chave_candidato_5_2(
                candidato
            )


            if chave in falhas_download:
                continue


            if not fallback_preserva_5_2(
                candidato,
                referencia
            ):

                degradados.append(
                    candidato
                )

                continue


            ok, destino_teste = (
                baixar_candidato_5_2(
                    candidato,
                    numero,
                    "DOWNLOAD PRIORITÁRIO"
                )
            )


            if ok:

                sucesso = True
                escolhido = candidato
                # SHORTAUTOPRO VISUAL UNIFIED V5 COMMIT
                try:
                    from visual_engine_unified import note_commit_runtime as _sap_visual_commit
                    _sap_visual_commit(candidato, locals())
                except Exception as _sap_visual_commit_error:
                    print(f"VISUAL_UNIFIED_COMMIT=FAIL_OPEN {type(_sap_visual_commit_error).__name__}: {_sap_visual_commit_error}")
                # Primeiro download válido vence.
                # Impede foto -> vídeo ou vídeo -> foto depois do sucesso.
                destino = destino_teste

                marcar_usado(
                    escolhido[
                        "fonte"
                    ],
                    escolhido[
                        "id"
                    ]
                )


                if (
                    chave_candidato_5_2(
                        candidato
                    )
                    != chave_candidato_5_2(
                        referencia
                    )
                ):

                    print(
                        "  FAILOVER: "
                        "QUALIDADE PRESERVADA"
                    )

                # SHORTAUTOPRO VSE42 SCENE COMMIT
                try:
                    from visual_selection_bridge_v42 import commit_candidate as _vse42_commit_candidate
                    _vse42_commit_candidate(
                        escolhido
                    )
                except Exception as _vse42_commit_exc:
                    print(
                        "  VSE42_COMMIT_WARNING="
                        + type(_vse42_commit_exc).__name__
                        + ":"
                        + str(_vse42_commit_exc)
                    )
                print(
                    "  VSE42_SCENE_COMMIT=FIRST_SUCCESS"
                )


                # SHORTAUTOPRO VSE42 SUCCESS COMMIT
                try:
                    from visual_selection_runtime_v42 import (
                        note_commit as _vse42_note_commit,
                    )
                
                    _vse42_note_commit(
                        candidato,
                        locals(),
                    )
                
                except Exception as _vse42_commit_exc:
                
                    print(
                        "VSE42_COMMIT_FAIL_OPEN="
                        + type(_vse42_commit_exc).__name__
                    )
                
                print(
                    "VSE42_FIRST_SUCCESS_LOCK=COMMITTED"
                )
                
                _vse42_cleanup_scene_sibling(destino)
                break


            falhas_download.add(
                chave
            )
        _vse42_cleanup_scene_sibling(destino)


    # =================================
    # RETRY COM QUERY SIMPLIFICADA
    # =================================

    if not sucesso:

        alternativas = simplificar_busca(
            busca,
            must_have
        )


        for busca_alt in alternativas:

            print(
                f"  RETRY: {busca_alt}"
            )


            candidatos_alt = (
                buscar_todos_candidatos(
                    busca_alt,
                    must_have,
                    avoid,
                    segmento=segmento,
                    visual_mode=visual_mode
                )
            )


            escolhido_alt = (
                escolher_documental_prioritario(
                    candidatos_alt,
                    rota_fonte,
                    len(must_have),
                    descricao_anterior
                )
            )


            if not escolhido_alt:

                escolhido_alt = (
                    escolher_relaxado(
                        candidatos_alt,
                        len(must_have)
                    )
                )


            pool_alt = ordenar_failover_5_2(
                candidatos_alt,
                len(must_have),
                rota_fonte,
                descricao_anterior
            )

            # SHORTAUTOPRO VSE42 ALT RANK
            try:
                from visual_selection_bridge_v42 import rank_pool as _vse42_rank_pool
                pool_alt, escolhido_alt, _vse42_alt_meta = _vse42_rank_pool(
                    pool_alt,
                    escolhido_alt,
                    locals(),
                )
            except Exception as _vse42_exc:
                print(
                    "  VSE42_FAIL_OPEN_ALT="
                    + type(_vse42_exc).__name__
                    + ":"
                    + str(_vse42_exc)
                )


            if escolhido_alt:

                pool_alt = [
                    escolhido_alt
                ] + [
                    c
                    for c in pool_alt
                    if chave_candidato_5_2(c)
                    != chave_candidato_5_2(
                        escolhido_alt
                    )
                ]


            for candidato in pool_alt:

                chave = chave_candidato_5_2(
                    candidato
                )


                if chave in falhas_download:
                    continue


                if (
                    referencia
                    and not fallback_preserva_5_2(
                        candidato,
                        referencia
                    )
                ):

                    degradados.append(
                        candidato
                    )

                    continue


                ok, destino_teste = (
                    baixar_candidato_5_2(
                        candidato,
                        numero,
                        "RETRY QUALIFICADO"
                    )
                )


                if ok:

                    sucesso = True
                    escolhido = candidato
                    destino = destino_teste

                    marcar_usado(
                        escolhido[
                            "fonte"
                        ],
                        escolhido[
                            "id"
                        ]
                    )


                    print(
                        "  RECUPERADA COM BUSCA "
                        "SIMPLIFICADA SEM PERDER "
                        "QUALIDADE"
                    )

                    # SHORTAUTOPRO VSE42 SCENE COMMIT
                    try:
                        from visual_selection_bridge_v42 import commit_candidate as _vse42_commit_candidate
                        _vse42_commit_candidate(
                            escolhido
                        )
                    except Exception as _vse42_commit_exc:
                        print(
                            "  VSE42_COMMIT_WARNING="
                            + type(_vse42_commit_exc).__name__
                            + ":"
                            + str(_vse42_commit_exc)
                        )
                    print(
                        "  VSE42_SCENE_COMMIT=FIRST_SUCCESS"
                    )
                    _vse42_cleanup_scene_sibling(destino)
                    # SHORTAUTOPRO SCENE COMMIT V42
                    try:
                        from visual_selection_runtime_bridge_v42 import note_selected as _sap_vse42_note_selected
                        _sap_vse42_note_selected(candidato)
                        print("SCENE_COMMIT_V42=YES")
                    except Exception as _sap_vse42_commit_exc:
                        print(f"SCENE_COMMIT_V42=HISTORY_FAIL_OPEN {type(_sap_vse42_commit_exc).__name__}: {_sap_vse42_commit_exc}")
                    break



                falhas_download.add(
                    chave
                )


            if sucesso:
                break


            for candidato in pool_alt:

                if fallback_degradado_ok_5_2(
                    candidato,
                    len(must_have)
                ):

                    degradados.append(
                        candidato
                    )
        _vse42_cleanup_scene_sibling(destino)


    # =================================
    # EXPLICIT-MUST LATE STRICT RECOVERY 1.0
    # =================================
    # Preserve the normal provider/selection path first. Only scenes that are
    # still unresolved reach the contextual MUST recovery. This avoids
    # multiplying provider calls for scenes that already had a viable asset.
    if not sucesso and must_have:
        try:
            print(
                "SAP_MUST_LATE_RECOVERY=START "
                f"scene={numero} must_total={len(must_have)}"
            )

            candidatos_rescue = buscar_todos_candidatos(
                busca,
                must_have,
                avoid,
                segmento=segmento,
                visual_mode=visual_mode,
            )

            candidatos_rescue = enriquecer_wikimedia_5_2(
                candidatos_rescue,
                rota_fonte,
                segmento,
                must_have,
                visual_mode,
            )

            pool_rescue = ordenar_failover_5_2(
                candidatos_rescue,
                len(must_have),
                rota_fonte,
                descricao_anterior,
            )

            print(
                "SAP_MUST_LATE_RECOVERY=POOL "
                f"scene={numero} candidates={len(candidatos_rescue)} "
                f"strict_pool={len(pool_rescue)}"
            )

            for candidato in pool_rescue:
                chave = chave_candidato_5_2(candidato)

                if chave in falhas_download:
                    continue

                ok, destino_teste = baixar_candidato_5_2(
                    candidato,
                    numero,
                    "RESCUE MUST ESTRITO",
                )

                if ok:
                    sucesso = True
                    escolhido = candidato
                    destino = destino_teste

                    marcar_usado(
                        escolhido["fonte"],
                        escolhido["id"],
                    )

                    try:
                        from visual_selection_bridge_v42 import commit_candidate as _vse42_commit_candidate
                        _vse42_commit_candidate(escolhido)
                    except Exception as _vse42_commit_exc:
                        print(
                            "  VSE42_COMMIT_WARNING="
                            + type(_vse42_commit_exc).__name__
                            + ":"
                            + str(_vse42_commit_exc)
                        )

                    print(
                        "SAP_MUST_LATE_RECOVERY=FOUND "
                        f"scene={numero} source={escolhido.get('fonte','?')} "
                        f"type={escolhido.get('tipo','?')}"
                    )
                    _vse42_cleanup_scene_sibling(destino)
                    break

                falhas_download.add(chave)

            if not sucesso:
                print(
                    "SAP_MUST_LATE_RECOVERY=EXHAUSTED "
                    f"scene={numero} strict_pool={len(pool_rescue)}"
                )

        except Exception as _sap_late_recovery_exc:
            print(
                "SAP_MUST_LATE_RECOVERY=FAIL_OPEN "
                f"scene={numero} "
                f"{type(_sap_late_recovery_exc).__name__}:"
                f"{str(_sap_late_recovery_exc)[:160]}"
            )


    # =================================
    # DEGRADAÇÃO CONTROLADA
    # =================================

    if (
        not sucesso
        and degradados
    ):

        unicos = {}


        for candidato in degradados:

            chave = chave_candidato_5_2(
                candidato
            )


            if chave in falhas_download:
                continue


            if not fallback_degradado_ok_5_2(
                candidato,
                len(must_have)
            ):

                continue


            velho = unicos.get(
                chave
            )


            if (
                velho is None
                or score_real_5_2(
                    candidato
                )
                > score_real_5_2(
                    velho
                )
            ):

                unicos[
                    chave
                ] = candidato


        candidatos_degradados = list(
            unicos.values()
        )


        candidatos_degradados.sort(
            key=lambda c: (
                c.get(
                    "must_hits",
                    0
                ),

                evidence_rank_5_2(
                    c
                ),

                score_real_5_2(
                    c
                )
            ),
            reverse=True
        )


        for candidato in candidatos_degradados:

            print(
                "  QUALITY DEGRADE: "
                f"{score_real_5_2(referencia):.1f}/"
                f"{referencia.get('must_hits', 0)} "
                "-> "
                f"{score_real_5_2(candidato):.1f}/"
                f"{candidato.get('must_hits', 0)}"
            )


            ok, destino_teste = (
                baixar_candidato_5_2(
                    candidato,
                    numero,
                    "FALLBACK CONTROLADO"
                )
            )


            if ok:

                sucesso = True
                escolhido = candidato
                destino = destino_teste

                marcar_usado(
                    escolhido[
                        "fonte"
                    ],
                    escolhido[
                        "id"
                    ]
                )


                print(
                    "  FALLBACK QUALITY "
                    "DEGRADE: JUSTIFICADO"
                )

                # SHORTAUTOPRO VSE42 SCENE COMMIT
                try:
                    from visual_selection_bridge_v42 import commit_candidate as _vse42_commit_candidate
                    _vse42_commit_candidate(
                        escolhido
                    )
                except Exception as _vse42_commit_exc:
                    print(
                        "  VSE42_COMMIT_WARNING="
                        + type(_vse42_commit_exc).__name__
                        + ":"
                        + str(_vse42_commit_exc)
                    )
                print(
                    "  VSE42_SCENE_COMMIT=FIRST_SUCCESS"
                )
                _vse42_cleanup_scene_sibling(destino)
                break



            falhas_download.add(
                chave_candidato_5_2(
                    candidato
                )
            )
        _vse42_cleanup_scene_sibling(destino)


    # =================================
    # FALLBACK LOCAL FINAL
    # =================================

    if not sucesso:

        origem = buscar_local(
            videos_total
            < VIDEO_META
        )


        if origem:

            ext = os.path.splitext(
                origem
            )[1].lower()


            destino = os.path.join(
                SAIDA_DIR,
                f"scene_{numero:02d}{ext}"
            )


            try:

                shutil.copy2(
                    origem,
                    destino
                )


                sucesso = True

                escolhido = {
                    "fonte":
                        "Local",

                    "tipo":
                        (
                            "vídeo"
                            if ext == ".mp4"
                            else "foto"
                        ),

                    "score":
                        0,

                    "must_hits":
                        0,

                    "avoid_hits":
                        0,

                    "descricao":
                        os.path.basename(
                            origem
                        ),

                    "id":
                        os.path.basename(
                            origem
                        )
                }


                print(
                    "  FALLBACK LOCAL: OK"
                )


            except Exception as e:

                sucesso = False

                print(
                    f"  FALLBACK LOCAL FAIL: "
                    f"{type(e).__name__}: "
                    f"{str(e)[:120]}"
                )
            _vse42_cleanup_scene_sibling(destino)
            _vse42_commit_safe(escolhido)
        _vse42_cleanup_scene_sibling(destino)
        _vse42_commit_safe(escolhido)


    if sucesso:

        fonte = escolhido[
            "fonte"
        ]

        tipo = escolhido[
            "tipo"
        ]

        descricao_anterior = (
            escolhido.get(
                "descricao",
                ""
            )
        )


        if tipo == "vídeo":
            videos_total += 1
        else:
            fotos_total += 1


        if fonte == "Wikimedia":

            salvar_credito(
                SHORT_ID,
                numero,
                escolhido
            )


        if fonte not in contagem:

            contagem[
                fonte
            ] = 0


        contagem[
            fonte
        ] += 1

        total += 1


        print(
            f"  ESCOLHIDO: "
            f"{fonte} / {tipo}"
        )

        print(
            f"  score="
            f"{escolhido['score']:.1f} "
            f"must="
            f"{escolhido['must_hits']}/"
            f"{len(must_have)}"
        )

        cobertura = (
            escolhido.get("must_hits", 0)
            / len(must_have)
            if len(must_have) > 0
            else 1.0
        )

        confiavel = metadata_confiavel(
            escolhido
        )

        if confiavel:
            trust = "HIGH"
        else:
            trust = "LOW"

        print(
            f"  SEMANTIC TRUST: {trust}"
        )

        if fonte == "Wikimedia":

            print(
                f"  EVIDENCE CLASS: "
                f"{escolhido.get('evidence_class', '?')}"
            )

            print(
                f"  TOPIC MATCH: "
                f"{escolhido.get('topic_overlap', 0) * 100:.0f}%"
            )

        print(
            f"  MUST COVERAGE: "
            f"{escolhido.get('must_hits', 0)}/"
            f"{len(must_have)} "
            f"({cobertura * 100:.0f}%)"
        )

        print(
            f"  AVOID HITS: "
            f"{escolhido.get('avoid_hits', 0)}"
        )

        if (
            escolhido.get("tipo") == "foto"
            and videos_total < VIDEO_META
        ):

            print(
                "  MOTION OVERRIDE: "
                "BLOQUEADO/PREFERÊNCIA SEMÂNTICA"
            )

        print(
            f"  MOVIMENTO: "
            f"{videos_total}/"
            f"{VIDEO_META} vídeos"
        )


    else:

        missing_scenes.append(
            {
                "scene": numero,
                "query": busca,
                "must_have": must_have,
                "avoid": avoid,
                "visual_mode": visual_mode,
                "candidate_count": len(todos),
                "failed_downloads": len(falhas_download),
                "degraded_candidates": len(degradados),
            }
        )

        print(
            "  ERRO: nenhuma mídia disponível."
        )
        print(
            "  SAP_MEDIA_SCENE_MISSING "
            f"scene={numero} candidates={len(todos)} "
            f"must={len(must_have)} downloads_failed={len(falhas_download)}"
        )


    time.sleep(
        0.20
    )


# ==================================================
# RESUMO
# ==================================================

print()
print("================================")
print("VISUAL GUARD 2.3.1 - RESUMO")
print("================================")
print()

print(
    f"Total: "
    f"{total}/{len(cenas)}"
)

print(
    f"Pexels: "
    f"{contagem['Pexels']}"
)

print(
    f"Pixabay: "
    f"{contagem['Pixabay']}"
)

print(
    f"Coverr: "
    f"{contagem['Coverr']}"
)

print(
    f"Local: "
    f"{contagem['Local']}"
)

print(
    f"Vídeos: "
    f"{videos_total}"
)

print(
    f"Fotos: "
    f"{fotos_total}"
)

print()


if missing_scenes:
    try:
        _diag_dir = os.path.join(BASE, "reports", "media")
        os.makedirs(_diag_dir, exist_ok=True)
        _diag_path = os.path.join(
            _diag_dir,
            f"acquisition_missing_{SHORT_ID}.json"
        )
        with open(_diag_path, "w", encoding="utf-8") as _diag:
            json.dump(
                {
                    "short_id": SHORT_ID,
                    "total": total,
                    "expected": len(cenas),
                    "missing_scenes": missing_scenes,
                },
                _diag,
                ensure_ascii=False,
                indent=2,
            )
        print(
            "SAP_MEDIA_MISSING_SCENES="
            + ",".join(str(item["scene"]) for item in missing_scenes)
        )
        print(f"SAP_MEDIA_MISSING_REPORT={_diag_path}")
    except Exception as _diag_exc:
        print(
            "SAP_MEDIA_MISSING_REPORT=FAIL_OPEN "
            + type(_diag_exc).__name__
            + ":"
            + str(_diag_exc)[:160]
        )

if total != len(cenas):

    sys.exit(
        f"ERRO: mídia incompleta: "
        f"{total}/{len(cenas)}"
    )

# SHORTAUTOPRO SOURCE PROVENANCE CAPTURE V1
from media_provenance_capture_v1 import (
    install as _sap_install_source_provenance_v1,
)

_sap_install_source_provenance_v1(
    globals()
)

