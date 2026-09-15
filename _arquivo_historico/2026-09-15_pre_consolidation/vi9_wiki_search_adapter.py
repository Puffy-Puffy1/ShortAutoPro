#!/usr/bin/env python3

import time
import requests

VI9_ADAPTER_VERSION = "9.00.4"

API = 'https://pt.wikipedia.org/w/api.php'
HEADERS = {'User-Agent': 'ShortAutoPro/2.2.1 (educational-video-automation)'}

VI9_DOWNLOAD_ALLOWED = False
VI9_MEDIA_WRITE_ALLOWED = False
VI9_CACHE_WRITE_ALLOWED = False
VI9_RENDER_ALLOWED = False
VI9_SOURCE_RECOVERY_ALLOWED = False


def wiki_search(query, limit=5):
    query = str(query or "").strip()

    if not query:
        return []

    try:
        limit = int(limit)
    except Exception:
        limit = 5

    limit = max(1, min(limit, 10))

    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "utf8": 1,
        "srlimit": limit,
    }

    wait = 3

    for attempt in range(1, 4):
        try:
            response = requests.get(
                API,
                params=params,
                headers=HEADERS,
                timeout=15
            )
        except Exception as exc:
            if attempt == 3:
                raise RuntimeError(
                    "Wikipedia connection: "
                    + str(exc)
                )

            time.sleep(wait)
            wait = min(wait * 2, 12)
            continue

        if response.status_code == 429:
            retry = response.headers.get(
                "Retry-After"
            )

            try:
                retry = int(retry)
            except Exception:
                retry = wait

            retry = max(
                3,
                min(retry, 20)
            )

            if attempt == 3:
                raise RuntimeError(
                    "Wikipedia HTTP 429"
                )

            time.sleep(retry)
            wait = min(wait * 2, 12)
            continue

        if response.status_code in {
            500, 502, 503, 504
        }:
            if attempt == 3:
                raise RuntimeError(
                    "Wikipedia HTTP "
                    + str(response.status_code)
                )

            time.sleep(wait)
            wait = min(wait * 2, 12)
            continue

        response.raise_for_status()

        data = response.json()

        return (
            data.get("query", {})
            .get("search", [])
        )

    return []


def adapter_status():
    return {
        "status": "READ_ONLY_WIKI_ADAPTER_READY",
        "version": VI9_ADAPTER_VERSION,
        "download_allowed": False,
        "media_write_allowed": False,
        "cache_write_allowed": False,
        "renderer_allowed": False,
        "source_recovery_allowed": False,
    }
