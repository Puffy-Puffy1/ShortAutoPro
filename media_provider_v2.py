#!/usr/bin/env python3
"""Compatibility facade for the independent Media Acquisition V2 router."""
from __future__ import annotations
from typing import Any
from media_provider_router_v2 import MediaProviderRouterV2

class MediaProviderV2:
    name = "provider-router-v2"

    def __init__(self, router=None):
        self.router = router or MediaProviderRouterV2()

    def search(self, query: str, must: list[str], avoid: list[str], *, segmento: str = "", visual_mode: str = "") -> list[dict[str, Any]]:
        return self.router.search(query, must, avoid, segmento=segmento, visual_mode=visual_mode)

    def prepare(self, candidates: list[dict[str, Any]], total_must: int) -> list[dict[str, Any]]:
        return [
            c for c in candidates
            if int(c.get("must_hits", 0) or 0) >= total_must
            and int(c.get("avoid_hits", 0) or 0) == 0
        ]

    def download(self, candidate: dict[str, Any], scene_number: int, short_id: str) -> tuple[bool, str]:
        ok, path, _ = self.router.download(candidate, scene_number, short_id)
        return ok, path
