#!/usr/bin/env python3
"""Provider compatibility boundary for Media Engine V2.

The engine owns acquisition policy; this module owns the adapter to the
repository's existing provider implementation. Keeping the import here makes
the V2 engine independently testable and gives us one seam for provider
extraction without changing mature provider behavior in the first migration.
"""
from __future__ import annotations

from typing import Any


def _legacy():
    from midia import (
        buscar_todos_candidatos,
        preparar_candidatos,
        baixar_candidato_5_2,
        simplificar_busca,
    )
    return buscar_todos_candidatos, preparar_candidatos, baixar_candidato_5_2, simplificar_busca


class MediaProviderV2:
    """Bounded adapter; no render, batch, or production-ID responsibilities."""

    name = "legacy-provider-adapter"

    def search(
        self,
        query: str,
        must: list[str],
        avoid: list[str],
        *,
        segmento: str = "",
        visual_mode: str = "",
    ) -> list[dict[str, Any]]:
        search, _, _, simplify = _legacy()

        # Bounded retrieval recovery: a transiently empty exact query must not
        # immediately become a fatal scene failure. Retry only with deterministic
        # query variants; explicit MUST terms are always preserved and are still
        # verified later by Media Engine V2. No relaxed semantic acceptance.
        queries = [str(query or "").strip()]
        try:
            for variant in simplify(str(query or ""), must):
                variant = str(variant or "").strip()
                if variant and variant not in queries:
                    queries.append(variant)
        except Exception:
            pass

        merged: list[dict[str, Any]] = []
        seen: set[str] = set()
        max_queries = 3
        for attempt, current_query in enumerate(queries[:max_queries], 1):
            if not current_query:
                continue
            result = search(
                current_query,
                must,
                avoid,
                segmento=segmento,
                visual_mode=visual_mode,
            )
            rows = result if isinstance(result, list) else []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                key = str(
                    row.get("id")
                    or row.get("url")
                    or row.get("arquivo")
                    or row.get("file")
                    or ""
                )
                if key and key in seen:
                    continue
                if key:
                    seen.add(key)
                merged.append(row)
            if merged:
                break
        return merged

    def prepare(
        self,
        candidates: list[dict[str, Any]],
        total_must: int,
    ) -> list[dict[str, Any]]:
        _, prepare, _ = _legacy()
        result = prepare(candidates, total_must, relaxado=False, descricao_anterior="")
        return result if isinstance(result, list) else []

    def download(
        self,
        candidate: dict[str, Any],
        scene_number: int,
    ) -> tuple[bool, str]:
        _, _, download = _legacy()
        ok, destination = download(candidate, scene_number, "MEDIA_ENGINE_V2")
        return bool(ok), str(destination or "")
