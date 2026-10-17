"""Normalize overly restrictive MUST phrases to searchable visual anchors.

Only known non-essential visual qualifiers are removed. This is not a media
acceptance bypass: the resulting anchor is still independently verified against
the asset's own metadata by media_must_verifier.
"""
from __future__ import annotations

import re
from typing import Any

# Exact mappings keep this conservative: do not strip arbitrary words from
# entity phrases such as "police car", "female pilot", or "cargo ship".
_NON_ATOMIC_VISUAL_MUSTS = {
    "single engine aircraft": "aircraft",
    "single-engine aircraft": "aircraft",
    "single engine airplane": "airplane",
    "single-engine airplane": "airplane",
    "dark horizon": "horizon",
    "bright horizon": "horizon",
    "dark ocean": "ocean",
    "dark sea": "sea",
    "vintage aircraft": "aircraft",
    "historic aircraft": "aircraft",
    "historical aircraft": "aircraft",
    "antique aircraft": "aircraft",
}


def normalize_visual_musts(value: Any) -> tuple[list[str], list[dict[str, str]]]:
    """Return deduplicated concrete anchors and auditable normalization events."""
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = []

    normalized: list[str] = []
    events: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in values:
        original = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not original:
            continue
        anchor = _NON_ATOMIC_VISUAL_MUSTS.get(original.casefold(), original)
        if anchor != original:
            events.append({"from": original, "to": anchor, "reason": "NON_ATOMIC_VISUAL_QUALIFIER"})
        key = anchor.casefold()
        if key not in seen:
            seen.add(key)
            normalized.append(anchor)
    return normalized, events
