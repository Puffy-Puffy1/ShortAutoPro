#!/usr/bin/env python3

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path

import requests


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
CACHE_DIR = BASE / "cache" / "wikipedia"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

API = "https://pt.wikipedia.org/w/api.php"
HEADERS = {
    "User-Agent": "ShortAutoPro/2.3 (educational-video-automation)"
}

try:
    MIN_INTERVAL = max(0.0, float(os.getenv("SAP_WIKI_MIN_INTERVAL", "1.4")))
except (TypeError, ValueError):
    MIN_INTERVAL = 1.4

_ultima_requisicao = 0.0


class WikiRateLimit(Exception):
    pass


def _esperar_intervalo():
    global _ultima_requisicao
    agora = time.time()
    restante = MIN_INTERVAL - (agora - _ultima_requisicao)
    if restante > 0:
        time.sleep(restante)
    _ultima_requisicao = time.time()


def _cache_path(tipo, chave):
    digest = hashlib.sha1(str(chave).encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{tipo}_{digest}.json"


def _ler_cache(tipo, chave):
    path = _cache_path(tipo, chave)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _salvar_cache(tipo, chave, dados):
    """Best-effort atomic cache write using a unique temp file."""
    path = _cache_path(tipo, chave)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = None
    temp_name = None
    try:
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            json.dump(dados, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
        temp_name = None
    except Exception:
        # Cache failure must not break factual retrieval.
        pass
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        if temp_name:
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def _get(params, tentativas=5):
    espera = 4

    for tentativa in range(1, tentativas + 1):
        _esperar_intervalo()

        try:
            response = requests.get(
                API,
                params=params,
                headers=HEADERS,
                timeout=30,
            )
        except Exception as exc:
            if tentativa == tentativas:
                raise RuntimeError(f"Wikipedia conexão: {exc}") from exc
            time.sleep(espera)
            espera = min(espera * 2, 30)
            continue

        if response.status_code == 429:
            retry_header = response.headers.get("Retry-After")
            try:
                retry = int(retry_header)
            except (TypeError, ValueError):
                retry = espera

            retry = max(5, min(retry, 60))
            print(f"Wikipedia 429. Aguardando {retry}s...")
            if tentativa == tentativas:
                raise WikiRateLimit(
                    "Wikipedia indisponível por excesso de requisições."
                )
            time.sleep(retry)
            espera = min(espera * 2, 60)
            continue

        if response.status_code in {500, 502, 503, 504}:
            if tentativa == tentativas:
                raise RuntimeError(f"Wikipedia HTTP {response.status_code}")
            time.sleep(espera)
            espera = min(espera * 2, 30)
            continue

        response.raise_for_status()

        try:
            data = response.json()
        except Exception as exc:
            raise RuntimeError(f"Wikipedia JSON inválido: {exc}") from exc

        if not isinstance(data, dict):
            raise RuntimeError("Wikipedia respondeu em formato inesperado.")
        return data

    raise WikiRateLimit("Wikipedia indisponível por excesso de requisições.")


def search(query, limit=5):
    query = str(query or "").strip()
    if not query:
        return []

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = 5
    limit = max(1, min(limit, 20))

    key = query.casefold() + f"|{limit}"
    cached = _ler_cache("search", key)
    if isinstance(cached, list):
        return [item for item in cached if isinstance(item, dict)]

    data = _get(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": limit,
        }
    )

    query_data = data.get("query", {})
    if not isinstance(query_data, dict):
        query_data = {}
    results = query_data.get("search", [])
    if not isinstance(results, list):
        results = []
    results = [item for item in results if isinstance(item, dict)]

    _salvar_cache("search", key, results)
    return results


def extract(title):
    title = str(title or "").strip()
    if not title:
        return ""

    key = title.casefold()
    cached = _ler_cache("extract", key)
    if isinstance(cached, dict):
        return str(cached.get("text", "") or "")

    data = _get(
        {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "titles": title,
            "redirects": 1,
            "format": "json",
        }
    )

    query_data = data.get("query", {})
    if not isinstance(query_data, dict):
        query_data = {}
    pages = query_data.get("pages", {})
    if not isinstance(pages, dict):
        pages = {}

    text = ""
    for page in pages.values():
        if not isinstance(page, dict):
            continue
        text = str(page.get("extract", "") or "").strip()
        if text:
            break

    _salvar_cache("extract", key, {"text": text})
    return text
