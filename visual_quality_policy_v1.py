#!/usr/bin/env python3
"""ShortAutoPro Visual Quality Policy V1.

Late-stage, metadata-only visual quality policy used by the final VSE4.2
reranker. The policy never downloads or mutates media. Its goal is to prefer
assets whose descriptive evidence matches the scene, while avoiding generic
stock, weak metadata and near-duplicate visuals.

Important design rule: search/query fields are scene intent, not evidence that
an asset actually contains the requested content. Candidate evidence therefore
excludes query/search_query/visual_query and URL/provider boilerplate.
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Iterable
from urllib.parse import urlparse


STOP = {
    "a", "ao", "aos", "as", "com", "como", "da", "das", "de", "do",
    "dos", "e", "em", "entre", "era", "essa", "esse", "esta", "este",
    "foi", "na", "nas", "no", "nos", "o", "os", "para", "pela", "pelas",
    "pelo", "pelos", "por", "que", "se", "sem", "um", "uma", "uns", "umas",
    "sua", "seu", "seus", "suas", "ele", "ela", "eles", "elas", "isso",
    "isto", "aquela", "aquele", "apos", "depois", "antes", "quando",
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was",
    "were", "with", "his", "her", "their", "after", "before", "when",
}

BOILERPLATE = {
    "http", "https", "www", "com", "org", "net", "pexels", "pixabay",
    "coverr", "wikimedia", "commons", "image", "images", "photo", "photos",
    "video", "videos", "stock", "download", "user", "profile", "page",
    "url", "cdn", "static", "media",
}

GENERIC_LIFESTYLE = {
    "lifestyle", "relaxing", "relax", "smiling", "happy", "casual", "fashion",
    "beauty", "wellness", "leisure", "vacation", "coffee", "cafe", "shopping",
    "bed", "bedroom", "sofa", "couch", "selfie", "influencer", "posing",
    "portrait", "model", "romantic", "couple", "dating", "hookah", "shisha",
    "narguile", "narguileh", "estilo", "vida", "relaxando", "sorrindo",
    "feliz", "moda", "beleza", "lazer", "ferias", "compras", "cama", "quarto",
    "retrato", "modelo", "casal",
}

CONCEPTS = {
    "phone": {"phone", "smartphone", "cellphone", "telephone", "mobile", "celular", "telefone", "ligacao", "ligou", "calling", "call"},
    "airport": {"airport", "terminal", "aviation", "flight", "gate", "aeroporto", "aviacao", "voo", "embarque"},
    "hospital": {"hospital", "medical", "doctor", "clinic", "emergency", "medico", "medica", "clinica", "emergencia"},
    "police": {"police", "officer", "detective", "investigation", "investigator", "policia", "policial", "detetive", "investigacao"},
    "camera": {"camera", "cctv", "surveillance", "security", "vigilancia", "seguranca"},
    "document": {"document", "documents", "passport", "record", "records", "paper", "documento", "documentos", "passaporte", "registro", "arquivo"},
    "luggage": {"luggage", "baggage", "suitcase", "bag", "mala", "bagagem", "mochila"},
    "hotel": {"hotel", "hostel", "resort", "room", "quarto", "hospedagem"},
    "travel": {"travel", "trip", "tourist", "tourism", "journey", "viagem", "ferias", "turista", "turismo"},
    "person": {"person", "people", "man", "woman", "male", "female", "pessoa", "homem", "mulher"},
    "running": {"running", "run", "runner", "fleeing", "escape", "correndo", "correu", "fugindo", "fugiu", "disparou"},
    "building": {"building", "office", "corridor", "hallway", "door", "predio", "edificio", "corredor", "porta"},
    "ocean": {"ocean", "sea", "water", "wave", "waves", "beach", "oceano", "mar", "agua", "onda", "ondas", "praia"},
    "forest": {"forest", "woods", "tree", "trees", "floresta", "mata", "arvore", "arvores"},
    "mountain": {"mountain", "mountains", "hill", "hills", "montanha", "montanhas", "serra"},
    "city": {"city", "street", "urban", "cidade", "rua", "urbano", "urbana"},
    "smoking": {"smoking", "smoke", "hookah", "shisha", "tobacco", "fumando", "fumaca", "narguile"},
}

SPECIFIC_ACTION_CONCEPTS = {
    "phone", "airport", "hospital", "police", "camera", "document", "luggage",
    "hotel", "running",
}

GENERIC_SCENERY_CONCEPTS = {"ocean", "forest", "mountain", "city", "building"}
STOCK_PROVIDERS = {"pexels", "pixabay", "coverr", "unsplash"}

CANDIDATE_EVIDENCE_FIELDS = (
    "descricao", "description", "title", "name", "caption", "alt", "alt_text",
    "tags", "keywords", "subject", "topic", "category", "location", "local",
    "city", "cidade", "country", "pais", "place",
)

NESTED_EVIDENCE_FIELDS = ("metadata", "meta", "source_metadata", "provenance")

SCENE_FIELDS = (
    "segmento", "segment", "texto", "text", "scene_text", "texto_cena",
    "visual_query", "query", "busca", "search_query", "must_have", "must",
    "location", "local", "topic", "tema", "narrative",
)


def normalize(value: Any) -> str:
    text = str(value or "").casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"www\.\S+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _flatten_text(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, bytes):
        return [value.decode("utf-8", errors="ignore")]
    if isinstance(value, dict):
        output: list[str] = []
        for item in value.values():
            output.extend(_flatten_text(item))
        return output
    if isinstance(value, (list, tuple, set)):
        output: list[str] = []
        for item in value:
            output.extend(_flatten_text(item))
        return output
    return [str(value)]


def tokens(value: Any) -> set[str]:
    result: set[str] = set()
    for part in _flatten_text(value):
        for token in normalize(part).split():
            if not token or token in STOP or token in BOILERPLATE:
                continue
            if token.isdigit() or len(token) >= 2:
                result.add(token)
    return result


def _append_field(parts: list[str], value: Any) -> None:
    for item in _flatten_text(value):
        item = re.sub(r"https?://\S+", " ", item, flags=re.IGNORECASE)
        item = re.sub(r"www\.\S+", " ", item, flags=re.IGNORECASE)
        item = " ".join(item.split())
        if item:
            parts.append(item)


def candidate_evidence_text(candidate: Any) -> str:
    """Return asset evidence only; never trusts search/query intent fields."""
    if candidate is None:
        return ""
    if isinstance(candidate, str):
        return " ".join(re.sub(r"https?://\S+", " ", candidate).split())

    parts: list[str] = []
    if isinstance(candidate, dict):
        for field in CANDIDATE_EVIDENCE_FIELDS:
            if field in candidate:
                _append_field(parts, candidate.get(field))
        for nested_name in NESTED_EVIDENCE_FIELDS:
            nested = candidate.get(nested_name)
            if not isinstance(nested, dict):
                continue
            for field in CANDIDATE_EVIDENCE_FIELDS:
                if field in nested:
                    _append_field(parts, nested.get(field))
    else:
        for field in CANDIDATE_EVIDENCE_FIELDS:
            try:
                _append_field(parts, getattr(candidate, field, None))
            except Exception:
                pass
    return " ".join(parts).strip()


def scene_text(scene: Any) -> str:
    if scene is None:
        return ""
    if isinstance(scene, str):
        return scene
    parts: list[str] = []
    if isinstance(scene, dict):
        for field in SCENE_FIELDS:
            if field in scene:
                _append_field(parts, scene.get(field))
    else:
        for field in SCENE_FIELDS:
            try:
                _append_field(parts, getattr(scene, field, None))
            except Exception:
                pass
    return " ".join(parts).strip()


def concept_hits(value: Any) -> set[str]:
    current = tokens(value)
    result: set[str] = set()
    for concept, aliases in CONCEPTS.items():
        alias_tokens = {normalize(alias) for alias in aliases}
        if current & alias_tokens:
            result.add(concept)
    return result


def provider_name(candidate: Any) -> str:
    if isinstance(candidate, dict):
        for key in ("provider", "fonte", "source", "site", "platform"):
            value = candidate.get(key)
            if value:
                return normalize(value)
        for key in ("url", "source_url", "download_url"):
            raw = candidate.get(key)
            if not raw:
                continue
            try:
                host = urlparse(str(raw)).netloc.casefold().removeprefix("www.")
            except Exception:
                host = ""
            for known in STOCK_PROVIDERS | {"wikimedia"}:
                if known in host:
                    return known
            if host:
                return host
    return "unknown"


def evidence_class(candidate: Any) -> str:
    if not isinstance(candidate, dict):
        return ""
    return str(candidate.get("evidence_class", "") or "").strip().upper()


def dimensions(candidate: Any) -> tuple[int, int]:
    if not isinstance(candidate, dict):
        return 0, 0

    def one(*keys: str) -> int:
        for key in keys:
            value = candidate.get(key)
            try:
                parsed = int(float(value))
            except (TypeError, ValueError, OverflowError):
                continue
            if parsed > 0:
                return parsed
        return 0

    return one("width", "largura"), one("height", "altura")


def signature_for_candidate(candidate: Any) -> str:
    return " ".join(sorted(tokens(candidate_evidence_text(candidate))))


def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    left = set(a)
    right = set(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def evaluate(candidate: Any, scene: Any, history: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return metadata-only adjustment for the final visual reranker."""
    history = history if isinstance(history, dict) else {}
    scene_raw = scene_text(scene)
    asset_raw = candidate_evidence_text(candidate)
    scene_tokens = tokens(scene_raw)
    asset_tokens = tokens(asset_raw)
    scene_concepts = concept_hits(scene_raw)
    asset_concepts = concept_hits(asset_raw)
    direct_overlap = len(scene_tokens & asset_tokens)
    concept_overlap = len(scene_concepts & asset_concepts)
    source = provider_name(candidate)
    stock = any(name in source for name in STOCK_PROVIDERS)
    cls = evidence_class(candidate)

    adjustment = 0.0
    reasons: list[str] = []

    if cls == "CASE_DIRECT":
        adjustment += 40.0
        reasons.append("CASE_DIRECT")
    elif cls == "CONTEXTUAL":
        adjustment += 18.0
        reasons.append("CONTEXTUAL")

    if direct_overlap >= 4:
        adjustment += 30.0
        reasons.append("DIRECT_OVERLAP_STRONG")
    elif direct_overlap >= 2:
        adjustment += 18.0
        reasons.append("DIRECT_OVERLAP")
    elif direct_overlap == 1:
        adjustment += 7.0

    if concept_overlap >= 2:
        adjustment += 30.0
        reasons.append("CONCEPT_OVERLAP_STRONG")
    elif concept_overlap == 1:
        adjustment += 14.0
        reasons.append("CONCEPT_OVERLAP")

    specific_scene = len(scene_tokens) >= 4 or bool(scene_concepts & SPECIFIC_ACTION_CONCEPTS)

    if not asset_tokens:
        adjustment -= 70.0 if stock else 35.0
        reasons.append("WEAK_ASSET_METADATA")
    elif specific_scene and direct_overlap == 0 and concept_overlap == 0:
        adjustment -= 78.0 if stock else 52.0
        reasons.append("UNANCHORED_ASSET")
    elif specific_scene and direct_overlap == 0:
        adjustment -= 22.0
        reasons.append("LOW_LITERAL_ANCHOR")

    generic_hits = asset_tokens & {normalize(x) for x in GENERIC_LIFESTYLE}
    if generic_hits:
        scene_generic_hits = scene_tokens & generic_hits
        if not scene_generic_hits and concept_overlap == 0:
            adjustment -= 58.0
            reasons.append("GENERIC_LIFESTYLE")

    scene_actions = scene_concepts & SPECIFIC_ACTION_CONCEPTS
    asset_scenery = asset_concepts & GENERIC_SCENERY_CONCEPTS
    if scene_actions and asset_scenery and not (scene_actions & asset_concepts):
        adjustment -= 48.0
        reasons.append("GENERIC_SCENERY_FOR_ACTION")

    width, height = dimensions(candidate)
    pixels = width * height
    if pixels >= 1920 * 1080:
        adjustment += 12.0
        reasons.append("RESOLUTION_1080P_PLUS")
    elif pixels >= 1280 * 720:
        adjustment += 6.0
    elif 0 < pixels < 640 * 360:
        adjustment -= 22.0
        reasons.append("LOW_RESOLUTION_METADATA")

    if width > 0 and height > width:
        adjustment += 4.0

    signature = signature_for_candidate(candidate)
    signature_tokens = signature.split()
    max_similarity = 0.0
    for old in list(history.get("semantic_signatures", []) or [])[-4:]:
        old_tokens = str(old or "").split()
        max_similarity = max(max_similarity, _jaccard(signature_tokens, old_tokens))

    if max_similarity >= 0.75:
        adjustment -= 90.0
        reasons.append("NEAR_DUPLICATE_STRONG")
    elif max_similarity >= 0.55:
        adjustment -= 48.0
        reasons.append("NEAR_DUPLICATE")
    elif max_similarity >= 0.35:
        adjustment -= 20.0
        reasons.append("VISUAL_SIMILARITY")

    if not math.isfinite(adjustment):
        adjustment = 0.0
        reasons = ["NONFINITE_FAIL_OPEN"]

    return {
        "adjustment": round(adjustment, 3),
        "reasons": reasons,
        "asset_text": asset_raw,
        "scene_text": scene_raw,
        "signature": signature,
        "direct_overlap": direct_overlap,
        "concept_overlap": concept_overlap,
        "scene_concepts": sorted(scene_concepts),
        "asset_concepts": sorted(asset_concepts),
        "provider": source,
        "evidence_class": cls,
        "max_recent_similarity": round(max_similarity, 4),
        "width": width,
        "height": height,
    }
