#!/usr/bin/env python3
"""Deterministic factual script fallback built only from a verified source."""

from __future__ import annotations

import re
import unicodedata
from typing import Callable


WORD_RE = re.compile(r"\b[\wÀ-ÿ'-]+\b", flags=re.UNICODE)

_TOPIC_STOPWORDS = {
    "a", "as", "o", "os", "um", "uma", "uns", "umas", "de", "do", "da",
    "dos", "das", "em", "no", "na", "nos", "nas", "por", "para", "e",
    "ou", "com", "que", "ao", "aos", "à", "às", "the", "an", "of", "in",
    "on", "at", "by", "for", "from", "and", "or", "to", "with", "about",
    "caso", "case", "incidente", "incident", "misterioso", "misteriosa",
    "mysterious", "mistério", "mystery",
}
_TOPIC_EVENT_ALIASES = {
    "voo": {
        "voo", "flight", "avião", "aeronave", "aviation", "aircraft",
    },
    "flight": {
        "voo", "flight", "avião", "aeronave", "aviation", "aircraft",
    },
    "desaparecimento": {
        "desaparecimento", "desaparecer", "desapareceu", "desaparecida",
        "desaparecido", "sumiu", "sumico", "ausencia", "ausente", "missing",
        "disappearance", "disappeared", "disappear", "vanished",
    },
    "disappearance": {
        "desaparecimento", "desaparecer", "desapareceu", "desaparecida",
        "desaparecido", "sumiu", "sumico", "ausencia", "ausente", "missing",
        "disappearance", "disappeared", "disappear", "vanished",
    },
    "morte": {
        "morte", "mortes", "morto", "morta", "mortos", "mortas", "morreram",
        "morreu", "death", "deaths", "dead", "died", "killed", "murder",
        "murdered", "assassinato", "assassinada", "assassinado",
    },
    "mortes": {
        "morte", "mortes", "morto", "morta", "mortos", "mortas", "morreram",
        "morreu", "death", "deaths", "dead", "died", "killed", "murder",
        "murdered", "assassinato", "assassinada", "assassinado",
    },
    "death": {
        "morte", "mortes", "morto", "morta", "mortos", "mortas", "morreram",
        "morreu", "death", "deaths", "dead", "died", "killed", "murder",
        "murdered", "assassinato", "assassinada", "assassinado",
    },
    "assassinato": {
        "morte", "mortes", "morto", "morta", "mortos", "mortas", "morreram",
        "morreu", "death", "deaths", "dead", "died", "killed", "murder",
        "murdered", "assassinato", "assassinada", "assassinado",
    },
}


def _normalized_tokens(text: str) -> list[str]:
    result = []
    for token in WORD_RE.findall(str(text or "")):
        decomposed = unicodedata.normalize("NFKD", token)
        result.append(
            "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()
        )
    return result


def _topic_terms(topic: str) -> list[str]:
    return [
        token for token in _normalized_tokens(topic)
        if token not in _TOPIC_STOPWORDS and len(token) > 1
    ]


def topic_relevance_score(text: str, topic: str) -> int:
    """Score source text for the requested topic without rewriting its facts."""
    terms = _topic_terms(topic)
    if not terms:
        return 0

    counts: dict[str, int] = {}
    for token in _normalized_tokens(text):
        counts[token] = counts.get(token, 0) + 1

    score = 0
    counted_groups: set[frozenset[str]] = set()
    for term in terms:
        aliases = _TOPIC_EVENT_ALIASES.get(term)
        if aliases:
            group = frozenset(aliases)
            if group in counted_groups:
                continue
            counted_groups.add(group)
            score += 4 * min(3, sum(counts.get(alias, 0) for alias in aliases))
        else:
            score += 3 * counts.get(term, 0)
    return score


def is_topic_relevant(text: str, topic: str) -> bool:
    """Require event-specific evidence when the topic names a known event class."""
    terms = _topic_terms(topic)
    if not terms:
        return True

    body = set(_normalized_tokens(text))
    # Numeric identifiers in a selected topic (for example, Flight 19 or
    # an incident year) are identity anchors, not optional relevance boosts.
    required_numbers = {
        term for term in terms if term.isdigit() and len(term) >= 2
    }
    if not required_numbers <= body:
        return False

    event_groups = {
        frozenset(_TOPIC_EVENT_ALIASES[term])
        for term in terms if term in _TOPIC_EVENT_ALIASES
    }
    if any(not (group & body) for group in event_groups):
        return False
    return topic_relevance_score(text, topic) > 0



def count_words(text: str) -> int:
    return len(WORD_RE.findall(str(text or "")))


def source_sentences(text: str) -> list[str]:
    raw = re.sub(r"\s+", " ", str(text or "")).strip()
    if not raw:
        return []

    # Wikipedia extracts can place section headings inline. Stop at reference
    # and navigation sections so repeated names in link lists cannot outrank
    # the article's actual event narrative during topic-window selection.
    non_story_section = re.search(
        r"={2,}\s*(?:ver\s+tamb[eé]m|refer[eê]ncias|"
        r"liga[cç][oõ]es\s+externas|notas|bibliografia|fontes|"
        r"leitura\s+adicional)\s*={2,}",
        raw,
        flags=re.IGNORECASE,
    )
    if non_story_section:
        raw = raw[:non_story_section.start()].strip()
    if not raw:
        return []

    # Remove inline Wikipedia section labels before sentence extraction; they
    # are navigation metadata, not narration or factual evidence.
    raw = re.sub(r"={2,}\s*[^=\n]+?\s*={2,}", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()

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
    topic: str = "",
) -> str:
    """Return a sentence-preserving script assembled only from source text.

    The algorithm scans all contiguous source-sentence windows, preserving order.
    When a topic is supplied, it prefers matching windows and refuses an unrelated
    extract if event-specific topic terms cannot be found. A CTA adds no factual claim.
    """

    sentences = source_sentences(source)
    if not sentences:
        return ""

    cta_words = count_words(cta)
    candidates: list[tuple[tuple[int, int, int], str]] = []

    limit = len(sentences)
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
                if topic and not is_topic_relevant(" ".join(chosen), topic):
                    continue
                score = (
                    -topic_relevance_score(" ".join(chosen), topic),
                    abs(count_words(text) - 116),
                    start,
                )
                candidates.append((score, text))

            if total > max_words:
                break

    if candidates:
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    # Second pass without CTA; retain source order and topic relevance.
    fallback_candidates: list[tuple[tuple[int, int, int], str]] = []
    for start in range(limit):
        chosen = []
        factual_words = 0
        for end in range(start, limit):
            sentence = sentences[end]
            factual_words += count_words(sentence)
            chosen.append(sentence)
            if min_words <= factual_words <= max_words:
                text = " ".join(chosen).strip()
                if topic and not is_topic_relevant(text, topic):
                    continue
                score = (
                    -topic_relevance_score(text, topic),
                    abs(count_words(text) - 116),
                    start,
                )
                fallback_candidates.append((score, text))
            if factual_words > max_words:
                break

    if fallback_candidates:
        fallback_candidates.sort(key=lambda item: item[0])
        return fallback_candidates[0][1]
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



def build_extractive_long_script(
    source: str,
    *,
    min_words: int,
    max_words: int,
    target_words: int | None = None,
    cta: str = "Comente o que achou!",
    topic: str = "",
) -> str:
    """Build a long narration from ordered, source-verbatim sentences.

    It never repeats sentences or invents facts. If the verified source does not
    contain enough relevant material, it returns an empty string instead of
    padding the video with unsupported narration.
    """
    try:
        minimum = max(200, int(min_words))
        maximum = max(minimum, min(int(max_words), 12000))
        target = int(target_words) if target_words is not None else (minimum + maximum) // 2
    except (TypeError, ValueError):
        return ""

    target = max(minimum, min(maximum, target))
    sentences = source_sentences(source)
    if not sentences:
        return ""

    cta_text = str(cta or "").strip()
    cta_count = count_words(cta_text)
    counts = [count_words(sentence) for sentence in sentences]
    if sum(counts) + cta_count < minimum:
        return ""

    best_score = None
    best_text = ""
    for start in range(len(sentences)):
        selected: list[str] = []
        words = cta_count
        for end in range(start, len(sentences)):
            sentence = sentences[end]
            words += counts[end]
            if words > maximum:
                break
            selected.append(sentence)
            if words < minimum:
                continue

            body = " ".join(selected)
            if topic and not is_topic_relevant(body, topic):
                continue

            # Prefer a window near the requested spoken length; use source
            # relevance and original order only as deterministic tie-breakers.
            relevance = topic_relevance_score(body, topic) if topic else 0
            score = (abs(words - target), -relevance, start)
            if best_score is None or score < best_score:
                best_score = score
                best_text = (body + (" " + cta_text if cta_text else "")).strip()

    return best_text



__all__ = [
    "count_words",
    "source_sentences",
    "build_extractive_script",
    "build_extractive_long_script",
    "build_scene_queries",
]
