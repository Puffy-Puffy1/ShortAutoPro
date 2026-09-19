#!/usr/bin/env python3
from __future__ import annotations

import re
from typing import Any

STOCK_MODES = {
    "human_context",
    "human context",
    "environment",
    "object",
    "abstract_context",
    "abstract context",
}

GENERIC_CONTEXT = {
    "hand", "hands", "wall", "room", "cell", "prison", "bars",
    "night", "dark", "water", "ocean", "island", "fog", "waves",
    "corridor", "passage", "person", "people", "man", "men",
}

OBJECT_STRICT_ANCHORS = {
    "empty golden frames": "picture frame",
    "empty golden frame": "picture frame",
    "golden picture frames": "picture frame",
    "ornate golden frames": "picture frame",
}


def _tokens(value: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(value or "").casefold())


def _score(term: str) -> tuple[int, int, int]:
    tokens = _tokens(term)
    multiword = 1 if len(tokens) > 1 else 0
    generic = sum(1 for token in tokens if token in GENERIC_CONTEXT)
    distinctive = sum(1 for token in tokens if token not in GENERIC_CONTEXT)
    # Prefer specific multiword visual anchors; generic context is demoted.
    return (
        distinctive * 10 + multiword * 6 - generic * 5,
        len(tokens),
        len(term),
    )


def prioritize(
    must_have: list[str],
    *,
    query: str = "",
    visual_mode: str = "",
) -> dict[str, list[str]]:
    original = [str(x).strip().lower() for x in must_have if str(x).strip()]
    if len(original) <= 1:
        return {"strict": original, "context": []}

    mode = str(visual_mode or "").strip().casefold()
    if mode not in STOCK_MODES:
        return {"strict": original, "context": []}

    ranked = sorted(original, key=_score, reverse=True)
    strict_count = 1
    if mode in {"human_context", "human context"} and len(original) >= 3:
        strict_count = 2

    strict = ranked[:strict_count]
    context = [item for item in original if item not in strict]

    if mode == "object":
        rewritten = []
        for item in strict:
            anchor = OBJECT_STRICT_ANCHORS.get(item, item)
            rewritten.append(anchor)
            if anchor != item and item not in context:
                context.append(item)
        strict = rewritten

    return {"strict": strict, "context": context}


__all__ = ["prioritize"]
