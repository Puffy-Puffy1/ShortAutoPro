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

STOCK_CONTEXT_MODIFIERS = {
    "old", "antique", "vintage", "historic", "historical", "archive",
    "archival", "dark", "empty", "ornate", "golden", "classic",
    "dramatic", "mysterious", "traditional", "ancient",
}


def _conservative_stock_anchor(term: str, mode: str) -> str:
    raw = str(term or "").strip().casefold()
    if not raw:
        return ""
    if mode == "object" and raw in OBJECT_STRICT_ANCHORS:
        return OBJECT_STRICT_ANCHORS[raw]

    tokens = _tokens(raw)
    if len(tokens) <= 1:
        return raw

    kept = [token for token in tokens if token not in STOCK_CONTEXT_MODIFIERS]
    # Never reduce a multiword contract to nothing. A one-word central object
    # is acceptable only when every removed token was a known visual modifier.
    if not kept:
        return raw
    if len(kept) == len(tokens):
        return raw
    return " ".join(kept)


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
    mode = str(visual_mode or "").strip().casefold()

    if not original:
        return {"strict": [], "context": []}

    if mode not in STOCK_MODES:
        strict = []
        context = []
        for item in original:
            anchor = _conservative_stock_anchor(item, mode)
            strict.append(anchor)
            if anchor != item:
                context.append(item)
        return {"strict": strict, "context": context}

    ranked = sorted(original, key=_score, reverse=True)
    strict_count = 1
    if mode in {"human_context", "human context"} and len(original) >= 3:
        strict_count = 2

    strict_original = ranked[:strict_count]
    context = [item for item in original if item not in strict_original]
    strict = []

    for item in strict_original:
        anchor = _conservative_stock_anchor(item, mode)
        strict.append(anchor)
        if anchor != item and item not in context:
            context.append(item)

    return {"strict": strict, "context": context}


__all__ = ["prioritize", "_conservative_stock_anchor"]
