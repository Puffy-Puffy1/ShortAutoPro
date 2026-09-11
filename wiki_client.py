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
        "ShortAutoPro/2.2.1 "
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

    try:

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                dados,
                f,
                ensure_ascii=False
            )

    except Exception:
        pass


def _get(
    params,
    tentativas=5
):

    global _ultima_requisicao

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

        return r.json()


    raise WikiRateLimit(
        "Wikipedia indisponível por excesso de requisições."
    )


def search(
    query,
    limit=5
):

    chave = (
        query.strip().lower()
        + f"|{limit}"
    )

    cache = _ler_cache(
        "search",
        chave
    )

    if cache is not None:
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


    resultados = (
        dados
        .get(
            "query",
            {}
        )
        .get(
            "search",
            []
        )
    )


    _salvar_cache(
        "search",
        chave,
        resultados
    )

    return resultados


def extract(
    title
):

    chave = title.strip().lower()

    cache = _ler_cache(
        "extract",
        chave
    )

    if cache is not None:

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


    pages = (
        dados
        .get(
            "query",
            {}
        )
        .get(
            "pages",
            {}
        )
    )


    texto = ""

    for page in pages.values():

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
