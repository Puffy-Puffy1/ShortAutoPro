#!/usr/bin/env python3
"""Legacy compatibility shim.

Canonical Wikimedia acquisition is owned by media_v3.providers.WikimediaAdapter.
This module remains only as a compatibility import boundary and must not be
used by the canonical pipeline.
"""
from __future__ import annotations

from media_v3.providers import WikimediaAdapter


def consultar_commons(query, limite=20, deadline_at=None):
    """Compatibility wrapper terminating at the canonical V3 provider."""
    rows = WikimediaAdapter().search(str(query or ""), [], [], [])
    return list(rows or [])[: max(1, int(limite or 20))]


def gerar_queries(busca, assunto="", segmento="", visual_mode=""):
    values = [str(x or "").strip() for x in (assunto, busca, segmento)]
    out = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out[:5]
