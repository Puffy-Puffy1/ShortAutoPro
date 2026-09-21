#!/usr/bin/env python3
"""Deterministic factual script fallback built only from a verified source."""

from __future__ import annotations

import re
from typing import Callable


WORD_RE = re.compile(r"\b[\wÀ-ÿ'-]+\b", flags=re.UNICODE)


def count_words(text: str) -> int:
    return len(WORD_RE.findall(str(text or "")))


def source_sentences(text: str) -> list[str]:
    raw = re.sub(r"\s+", " ", str(text or "")).strip()
    if not raw:
        return []

    parts = re.split(
        r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9])",
        raw,
    )
    out: list[str] = []
    for part in parts:
        part = re.sub(r"\[[0-9]+\]", "", part).strip()
        if count_words(part) < 5:
            continue
        if part.casefold().startswith(
            ("ver também", "referências", "ligações externas")
        ):
            continue
        out.append(part)
    return out


def build_extractive_script(
    source: str,
    *,
    min_words: int = 105,
    max_words: int = 125,
    cta: str = "Qual detalhe desse caso mais chama sua atenção? Comente.",
) -> str:
    """Return a sentence-preserving script assembled only from source text.

    The algorithm searches contiguous sentence windows first, preserving source
    order and avoiding cherry-picking unrelated sentences. A CTA is optional
    editorial text and contains no factual claim.
    """

    sentences = source_sentences(source)
    if not sentences:
        return ""

    cta_words = count_words(cta)
    candidates: list[tuple[tuple[int, int, int], str]] = []

    limit = min(len(sentences), 40)
    for start in range(limit):
        chosen: list[str] = []
        factual_words = 0

        for end in range(start, limit):
            sentence = sentences[end]
            factual_words += count_words(sentence)
            chosen.append(sentence)

            total = factual_words + cta_words
            if min_words <= total <= max_words:
                text = (" ".join(chosen) + " " + cta).strip()
                # Prefer a result near 116 words, then earlier source windows,
                # then fewer sentences for cleaner narration.
                score = (
                    abs(count_words(text) - 116),
                    start,
                    len(chosen),
                )
                candidates.append((score, text))

            if total > max_words:
                break

    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    # Second pass without CTA, useful when the source sentences naturally form
    # a complete 105-125 word block.
    for start in range(limit):
        chosen = []
        factual_words = 0
        for end in range(start, limit):
            sentence = sentences[end]
            factual_words += count_words(sentence)
            chosen.append(sentence)
            if min_words <= factual_words <= max_words:
                return " ".join(chosen).strip()
            if factual_words > max_words:
                break

    return ""


def build_scene_queries(
    topic: str,
    quantity: int,
    *,
    clean_topic: Callable[[str], str] | None = None,
) -> str:
    base = clean_topic(topic) if clean_topic else str(topic or "").strip()
    base = base or "documentary case"
    words = WORD_RE.findall(base)
    term = " ".join(words[:5]).strip() or "documentary case"

    templates = [
        f"{term} archival documentary footage",
        f"{term} historical location exterior",
        f"{term} investigation documents archive",
        f"{term} night sky documentary context",
        f"{term} official records close up",
        f"{term} historical news archive",
    ]
    quantity = max(1, int(quantity))
    return "\n".join(templates[i % len(templates)] for i in range(quantity))


__all__ = [
    "count_words",
    "source_sentences",
    "build_extractive_script",
    "build_scene_queries",
]
