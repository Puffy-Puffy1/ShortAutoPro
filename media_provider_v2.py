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
        """Verify strictly first, then use a bounded progressive fallback.

        Provider metadata is not guaranteed to contain every visual term. When
        strict verification has no candidate, a real provider asset may still
        be usable if it has at least one MUST hit, no avoid hits, and a strong
        query score. No placeholders or synthetic media are created here.
        """
        clean = [
            c for c in candidates
            if int(c.get("avoid_hits", 0) or 0) == 0
        ]
        strict = [
            c for c in clean
            if int(c.get("must_hits", 0) or 0) >= total_must
        ]
        if strict or total_must <= 0:
            if total_must <= 0:
                return [
                    c for c in clean
                    if float(c.get("score", 0) or 0) >= 20
                ]
            return strict

        progressive = [
            c for c in clean
            if int(c.get("must_hits", 0) or 0) >= 1
            and float(c.get("score", 0) or 0) >= 45
        ]
        progressive.sort(
            key=lambda c: (
                int(c.get("must_hits", 0) or 0),
                float(c.get("score", 0) or 0),
                str(c.get("fonte", "")),
                str(c.get("id", "")),
            ),
            reverse=True,
        )
        for candidate in progressive:
            candidate["verification_mode"] = "progressive_must"
            candidate["verification_note"] = (
                f"strict_must={total_must};"
                f"verified_must={int(candidate.get('must_hits', 0) or 0)}"
            )
        return progressive

    def download(self, candidate: dict[str, Any], scene_number: int, short_id: str) -> tuple[bool, str, dict[str, Any]]:
        return self.router.download(candidate, scene_number, short_id)
