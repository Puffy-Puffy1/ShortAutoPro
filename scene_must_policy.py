"""Normalize strict visual MUSTs into concrete, auditable search anchors.

Context-specific normalization may merge overlapping labels for the same visible
object. It never supplies asset evidence: media_must_verifier still checks the
selected asset's own metadata before acceptance.
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
    # Overlapping manuscript descriptors must resolve to one visible object.
    "medieval manuscript": "manuscript",
    "aged parchment pages": "manuscript",
    "aged parchment page": "manuscript",
    "medieval manuscript pages": "manuscript",
    "illuminated manuscript pages": "manuscript",
}

_MANUSCRIPT_CONTEXT = re.compile(r"\b(?:manuscript|manuscripts|voynich)\b", re.IGNORECASE)
_CONTEXTUAL_MANUSCRIPT_MUSTS = {
    "book": "manuscript",
    "books": "manuscript",
    "parchment page": "manuscript",
    "parchment pages": "manuscript",
}
_TENT_CONTEXT = re.compile(r"\b(?:tent|tents|camping)\b", re.IGNORECASE)
_TORN_TENT_CONTEXT = re.compile(r"\b(?:torn|ripped|damaged|cut|slashed|split)\b.{0,45}\b(?:tent|canvas|fabric)\b|\b(?:tent|canvas|fabric)\b.{0,45}\b(?:torn|ripped|damaged|cut|slashed|split)\b", re.IGNORECASE)
_SNOW_CONTEXT = re.compile(r"\b(?:snow|snowy|snowfall|snow-covered|snow covered)\b", re.IGNORECASE)
_OCEAN_CONTEXT = re.compile(r"\b(?:ocean|oceans|sea|seas|open water)\b", re.IGNORECASE)
_RIB_CAGE_CONTEXT = re.compile(r"\b(?:rib cage|ribcage)\b", re.IGNORECASE)
_SOVIET_TRAIN_CONTEXT = re.compile(
    r"\b(?:soviet|ussr)\b.*\b(?:train|railway|locomotive)\b"
    r"|\b(?:train|railway|locomotive)\b.*\b(?:soviet|ussr)\b",
    re.IGNORECASE,
)
_SKI_CONTEXT = re.compile(r"\b(?:ski|skis|skiing|skier|skiers)\b", re.IGNORECASE)
_COMMUNICATION_EQUIPMENT_CONTEXT = re.compile(r"\b(?:radio|microphone|headset|transceiver|communications equipment)\b", re.IGNORECASE)
_VISIBLE_PILOT_CONTEXT = re.compile(r"\b(?:pilot|aviator|person|people|man|woman|figure|crew|cockpit)\b", re.IGNORECASE)
_BOOK_PAGE_CONTEXT = re.compile(r"\b(?:book\s+pages?|printed\s+pages?|page\s+(?:with|of)\s+(?:printed\s+)?text|(?:persian|printed)\s+text)\b", re.IGNORECASE)
_DOCUMENT_TEXT_CONTEXT = re.compile(
    r"\b(?:document|documents|report|reports|paper|papers|investigation|archive|letter|letters)\b",
    re.IGNORECASE,
)


def normalize_visual_musts(
    value: Any,
    context: str = "",
) -> tuple[list[str], list[dict[str, str]]]:
    """Normalize visual anchors without letting a MUST prove itself.

    The scene query and other distinct MUSTs can provide context. The current
    MUST is excluded to prevent self-referential matches such as "pilot"
    making itself look like a visible person. Asset metadata is still verified
    independently before a candidate can be accepted.
    """
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple)):
        values = list(value)
    else:
        values = []

    normalized: list[str] = []
    events: list[dict[str, str]] = []
    seen: set[str] = set()

    for index, raw in enumerate(values):
        original = re.sub(r"\s+", " ", str(raw or "")).strip()
        if not original:
            continue

        other_values = [
            str(other).strip()
            for other_index, other in enumerate(values)
            if other_index != index and str(other).strip()
        ]
        item_context = " ".join([str(context or "").strip(), *other_values]).strip()
        manuscript_context = bool(_MANUSCRIPT_CONTEXT.search(item_context))
        key = original.casefold()
        anchor = _NON_ATOMIC_VISUAL_MUSTS.get(key, original)
        reason = "NON_ATOMIC_VISUAL_QUALIFIER"

        if anchor == original and manuscript_context and key in _CONTEXTUAL_MANUSCRIPT_MUSTS:
            anchor = _CONTEXTUAL_MANUSCRIPT_MUSTS[key]
            reason = "CONTEXTUAL_MANUSCRIPT_ANCHOR"
        elif anchor == original and key == "ripped canvas" and _TENT_CONTEXT.search(item_context):
            anchor = "torn tent"
            reason = "CONTEXTUAL_TENT_ANCHOR"
        elif anchor == original and key == "tent fabric" and _TORN_TENT_CONTEXT.search(item_context):
            anchor = "torn tent"
            reason = "CONTEXTUAL_TENT_ANCHOR"
        elif anchor == original and key == "snowy background" and _SNOW_CONTEXT.search(item_context):
            anchor = "snow"
            reason = "CONTEXTUAL_SNOW_ANCHOR"
        elif anchor == original and key == "water" and _OCEAN_CONTEXT.search(item_context):
            anchor = "ocean"
            reason = "CONTEXTUAL_OCEAN_ANCHOR"
        elif anchor == original and key == "skeleton" and _RIB_CAGE_CONTEXT.search(item_context):
            anchor = "rib cage"
            reason = "CONTEXTUAL_RIB_CAGE_ANCHOR"
        elif anchor == original and key == "vintage equipment" and _SKI_CONTEXT.search(str(context or "")):
            anchor = "vintage"
            reason = "CONTEXTUAL_VINTAGE_SKI_CONTEXT"
        elif anchor == original and key == "skis" and _SKI_CONTEXT.search(item_context):
            anchor = "ski equipment"
            reason = "CONTEXTUAL_SKI_EQUIPMENT_ANCHOR"
        elif anchor == original and key == "winter gear" and _SKI_CONTEXT.search(item_context):
            anchor = "ski equipment"
            reason = "CONTEXTUAL_SKI_EQUIPMENT_ANCHOR"
        elif anchor == original and key in {"book page", "book pages"} and _BOOK_PAGE_CONTEXT.search(item_context):
            anchor = "page"
            reason = "CONTEXTUAL_BOOK_PAGE_ANCHOR"
        elif (
            anchor == original
            and key == "text"
            and any(
                re.sub(r"\s+", " ", other).strip().casefold() == "document"
                for other in other_values
            )
            and _DOCUMENT_TEXT_CONTEXT.search(str(context or ""))
        ):
            # A generic "text" anchor duplicates a document object in archive
            # queries; the document itself must still pass independent evidence.
            anchor = "document"
            reason = "CONTEXTUAL_DOCUMENT_TEXT_ANCHOR"
        elif (
            anchor == original
            and key == "pilot"
            and _COMMUNICATION_EQUIPMENT_CONTEXT.search(item_context)
            and not _VISIBLE_PILOT_CONTEXT.search(item_context)
        ):
            anchor = "microphone"
            reason = "CONTEXTUAL_PILOT_EQUIPMENT_ANCHOR"

        elif anchor == original and key == "soviet train" and _SOVIET_TRAIN_CONTEXT.search(item_context):
            anchor = "train"
            reason = "CONTEXTUAL_SOVIET_TRAIN_ANCHOR"

        if anchor != original:
            events.append({"from": original, "to": anchor, "reason": reason})

        anchor_key = anchor.casefold()
        if anchor_key not in seen:
            seen.add(anchor_key)
            normalized.append(anchor)

    return normalized, events
