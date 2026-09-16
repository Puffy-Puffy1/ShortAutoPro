#!/usr/bin/env python3
"""Strict explicit-MUST verification for the canonical media selector.

Provider/search metadata may declare ``must_hits`` for backward compatibility,
but an explicit scene ``must_have`` must be proven again from asset evidence.
Search/query fields are intentionally excluded.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import visual_selection_engine_v4 as vse


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _tokens(value: Any) -> set[str]:
    stop = {
        "a", "an", "and", "at", "by", "for", "from", "in", "of", "on",
        "or", "the", "to", "with", "de", "da", "do", "das", "dos", "e",
        "em", "na", "no", "nas", "nos", "para", "por", "com",
    }
    return {t for t in _norm(value).split() if t and t not in stop}


def asset_evidence_text(candidate: Any) -> str:
    """Return only descriptive evidence about the returned asset."""
    if not isinstance(candidate, dict):
        return str(candidate or "")

    fields = (
        "description", "descricao", "title", "name", "caption", "alt",
        "alt_text", "tags", "keywords", "subject", "category", "location",
        "local", "city", "cidade", "country", "pais", "place", "geo",
        "filename",
    )
    nested_fields = ("metadata", "meta", "source_metadata", "provenance")
    parts: list[str] = []

    def add(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                # Never treat a search/query echo as asset evidence.
                if str(key).casefold() in {"query", "search_query", "visual_query", "busca"}:
                    continue
                add(item)
            return
        if isinstance(value, (list, tuple, set)):
            for item in value:
                add(item)
            return
        text = str(value).strip()
        if text:
            parts.append(text)

    for field in fields:
        add(candidate.get(field))
    for nested in nested_fields:
        value = candidate.get(nested)
        if isinstance(value, dict):
            add(value)

    return " ".join(parts)


def _phrase_present(text: str, phrase: str) -> bool:
    normalized_text = f" {_norm(text)} "
    normalized_phrase = _norm(phrase)
    return bool(normalized_phrase) and f" {normalized_phrase} " in normalized_text


def strict_concept_hits(text: Any) -> set[str]:
    """Phrase-aware concept matcher.

    Unlike the legacy token-based concept helper, a multiword alias such as
    ``police tape`` is matched as a phrase. Single-word aliases still work.
    """
    raw = str(text or "")
    found: set[str] = set()
    for concept, aliases in getattr(vse, "CONCEPTS", {}).items():
        for alias in aliases:
            if _phrase_present(raw, str(alias)):
                found.add(str(concept))
                break
    return found


def explicit_must_list(scene: Any) -> list[str]:
    if not isinstance(scene, dict):
        return []
    raw = scene.get("must_have", [])
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple, set)):
        return []
    return [str(item).strip() for item in raw if item is not None and str(item).strip()]


def requirement_matches(requirement: str, candidate: Any) -> bool:
    evidence = asset_evidence_text(candidate)
    if not evidence:
        return False

    # Geographic MUSTs require compatible real asset geography.
    req_geo = set(vse.geo_hits(requirement))
    if req_geo:
        cand_geo = set(vse.geo_hits(evidence))
        return bool(req_geo & cand_geo)

    req_tokens = _tokens(requirement)
    cand_tokens = _tokens(evidence)
    if req_tokens and req_tokens.issubset(cand_tokens):
        return True

    # Synonym rescue is strict: every phrase-aware concept expressed by the
    # requirement must also be expressed by the asset. For "police tape" this
    # includes crime_tape, so a generic detective image cannot pass.
    req_concepts = strict_concept_hits(requirement)
    if not req_concepts:
        return False
    cand_concepts = strict_concept_hits(evidence)
    return req_concepts.issubset(cand_concepts)


def verified_must(candidate: Any, scene: Any) -> dict[str, Any]:
    requirements = explicit_must_list(scene)
    if not requirements:
        return {
            "explicit": False,
            "total": 0,
            "hits": 0,
            "tier": None,
            "coverage": None,
            "matched": [],
            "missing": [],
        }

    matched = [req for req in requirements if requirement_matches(req, candidate)]
    missing = [req for req in requirements if req not in matched]
    hits = len(matched)
    total = len(requirements)
    coverage = hits / total if total else 0.0
    tier = 2 if coverage >= 0.90 else 1 if coverage >= 0.45 else 0

    return {
        "explicit": True,
        "total": total,
        "hits": hits,
        "tier": tier,
        "coverage": round(coverage, 4),
        "matched": matched,
        "missing": missing,
    }


__all__ = [
    "asset_evidence_text",
    "strict_concept_hits",
    "explicit_must_list",
    "requirement_matches",
    "verified_must",
]
