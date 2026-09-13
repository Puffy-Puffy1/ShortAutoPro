#!/usr/bin/env python3

import os
import json
import time
import hashlib
import requests


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)

CACHE_DIR = os.path.join(
    BASE,
    "cache",
    "wikipedia"
)

os.makedirs(
    CACHE_DIR,
    exist_ok=True
)

API = "https://pt.wikipedia.org/w/api.php"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/2.2.2 "
        "(educational-video-automation)"
}

MIN_INTERVAL = 1.4

_ultima_requisicao = 0.0


class WikiRateLimit(Exception):
    pass


def _esperar_intervalo():

    global _ultima_requisicao

    agora = time.time()

    restante = (
        MIN_INTERVAL
        - (agora - _ultima_requisicao)
    )

    if restante > 0:
        time.sleep(
            restante
        )

    _ultima_requisicao = time.time()


def _cache_path(
    tipo,
    chave
):

    digest = hashlib.sha1(
        chave.encode(
            "utf-8"
        )
    ).hexdigest()

    return os.path.join(
        CACHE_DIR,
        f"{tipo}_{digest}.json"
    )


def _ler_cache(
    tipo,
    chave
):

    path = _cache_path(
        tipo,
        chave
    )

    if not os.path.exists(
        path
    ):
        return None

    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            )

    except Exception:

        return None


def _salvar_cache(
    tipo,
    chave,
    dados
):

    path = _cache_path(
        tipo,
        chave
    )

    temporario = path + ".tmp"

    try:

        with open(
            temporario,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                dados,
                f,
                ensure_ascii=False
            )
            f.flush()
            os.fsync(
                f.fileno()
            )

        os.replace(
            temporario,
            path
        )

    except Exception:
        pass

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


def _get(
    params,
    tentativas=5
):

    espera = 4

    for tentativa in range(
        1,
        tentativas + 1
    ):

        _esperar_intervalo()

        try:

            r = requests.get(
                API,
                params=params,
                headers=HEADERS,
                timeout=30
            )

        except Exception as e:

            if tentativa == tentativas:
                raise RuntimeError(
                    f"Wikipedia conexão: {e}"
                )

            time.sleep(
                espera
            )

            espera = min(
                espera * 2,
                30
            )

            continue

        if r.status_code == 429:

            retry = r.headers.get(
                "Retry-After"
            )

            try:
                retry = int(
                    retry
                )
            except Exception:
                retry = espera

            retry = max(
                5,
                min(
                    retry,
                    60
                )
            )

            print(
                f"Wikipedia 429. "
                f"Aguardando {retry}s..."
            )

            time.sleep(
                retry
            )

            espera = min(
                espera * 2,
                60
            )

            continue

        if r.status_code in [
            500,
            502,
            503,
            504
        ]:

            if tentativa == tentativas:
                raise RuntimeError(
                    f"Wikipedia HTTP "
                    f"{r.status_code}"
                )

            time.sleep(
                espera
            )

            espera = min(
                espera * 2,
                30
            )

            continue

        r.raise_for_status()

        try:
            dados = r.json()
        except Exception as e:
            raise RuntimeError(
                f"Wikipedia JSON inválido: {e}"
            )

        if not isinstance(
            dados,
            dict
        ):
            raise RuntimeError(
                "Wikipedia respondeu em formato inesperado."
            )

        return dados

    raise WikiRateLimit(
        "Wikipedia indisponível por excesso de requisições."
    )


def search(
    query,
    limit=5
):

    query = str(
        query or ""
    ).strip()

    if not query:
        return []

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5

    limit = max(
        1,
        min(limit, 20)
    )

    chave = (
        query.lower()
        + f"|{limit}"
    )

    cache = _ler_cache(
        "search",
        chave
    )

    if isinstance(
        cache,
        list
    ):
        return cache

    dados = _get(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": limit
        }
    )

    query_data = dados.get(
        "query",
        {}
    )

    if not isinstance(
        query_data,
        dict
    ):
        query_data = {}

    resultados = query_data.get(
        "search",
        []
    )

    if not isinstance(
        resultados,
        list
    ):
        resultados = []

    resultados = [
        item
        for item in resultados
        if isinstance(item, dict)
    ]

    _salvar_cache(
        "search",
        chave,
        resultados
    )

    return resultados


def extract(
    title
):

    title = str(
        title or ""
    ).strip()

    if not title:
        return ""

    chave = title.lower()

    cache = _ler_cache(
        "extract",
        chave
    )

    if isinstance(
        cache,
        dict
    ):

        return str(
            cache.get(
                "text",
                ""
            )
        )

    dados = _get(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "titles": title,
            "redirects": 1,
            "format": "json"
        }
    )

    query_data = dados.get(
        "query",
        {}
    )

    if not isinstance(
        query_data,
        dict
    ):
        query_data = {}

    pages = query_data.get(
        "pages",
        {}
    )

    if not isinstance(
        pages,
        dict
    ):
        pages = {}

    texto = ""

    for page in pages.values():

        if not isinstance(
            page,
            dict
        ):
            continue

        texto = str(
            page.get(
                "extract",
                ""
            )
        ).strip()

        if texto:
            break

    _salvar_cache(
        "extract",
        chave,
        {
            "text": texto
        }
    )

    return texto
