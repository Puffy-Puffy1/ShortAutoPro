#!/usr/bin/env python3
"""Deterministic source-coverage contract for visual scene segmentation."""
from __future__ import annotations

import re
from typing import Any

_WORD = re.compile(r"\b[\wÀ-ÿ'-]+\b", flags=re.UNICODE)


def _tokens(value: Any) -> list[str]:
    return [item.casefold() for item in _WORD.findall(str(value or ""))]


def scenes_cover_script(scenes: Any, script: str) -> bool:
    """Require ordered scene segments to cover the script exactly once.

    This rejects duplicated, omitted, reordered, or invented scene narration.
    Punctuation and capitalization are intentionally ignored; every word and
    its order must remain identical to the source script.
    """
    if not isinstance(scenes, list) or not scenes:
        return False
    expected = _tokens(script)
    if not expected:
        return False

    actual: list[str] = []
    for scene in scenes:
        if not isinstance(scene, dict):
            return False
        segment = scene.get("segment")
        if not str(segment or "").strip():
            return False
        actual.extend(_tokens(segment))
    return actual == expected


__all__ = ["scenes_cover_script"]
