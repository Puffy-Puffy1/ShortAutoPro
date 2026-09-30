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
    )
    return buscar_todos_candidatos, preparar_candidatos, baixar_candidato_5_2


class MediaProviderV2:
    """Bounded adapter; no render, batch, or SHORT_ID responsibilities."""

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
        search, _, _ = _legacy()
        result = search(query, must, avoid, segmento=segmento, visual_mode=visual_mode)
        return result if isinstance(result, list) else []

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
