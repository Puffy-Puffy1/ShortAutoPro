#!/usr/bin/env python3
"""Canonical runtime adapter for ShortAutoPro media acquisition.

This adapter is installed once by ``vg4x_bridge`` after ``midia.py`` has
defined its acquisition/selection functions and before the scene loop starts.
It keeps strict MUST verification authoritative, makes Visual Unified the sole
production reranker, and supplies safe retry/continuity fallbacks without
fabricating semantic coverage.
"""
from __future__ import annotations

import functools
import inspect
import os
import re
from pathlib import Path
from typing import Any

from media_must_verifier import verified_must

VERSION = "1.4"

_CANONICAL_ENV = {
    "SAP_VISUAL_UNIFIED": "1",
    "SAP_VSE4": "0",
    "SAP_VSE4_RESCUE": "0",
    "SAP_VSE_V42": "0",
    "SAP_VSE42": "0",
    "SAP_VSE42_RUNTIME": "0",
    "SAP_VSE42_BRIDGE": "0",
    "SAP_VSE42_RESCUE": "0",
    "SAP_VSE4_QUERY_EXPANSION": "1",
    "SAP_VG4X": "0",
    "VISUAL_INTELLIGENCE_MODE": "SHADOW",
    "SAP_MEDIA_CONTINUITY_FALLBACK": "1",
}

_PROVIDER_SKIP_PRINTED: set[str] = set()


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _norm(value: Any) -> str:
    text = str(value or "").casefold()
    return " ".join(re.findall(r"[a-z0-9à-ÿ]+", text))


def _tokens(value: Any) -> set[str]:
    stop = {
        "a", "an", "and", "at", "by", "for", "from", "in", "of", "on",
        "or", "the", "to", "with", "de", "da", "do", "das", "dos", "e",
        "em", "na", "no", "nas", "nos", "para", "por", "com",
        "cinematic", "dramatic", "moody", "shot", "scene", "view", "close",
        "documentary", "footage",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9à-ÿ]+", _norm(value))
        if len(token) >= 2 and token not in stop
    }


def _asset_text(candidate: dict[str, Any]) -> str:
    values: list[str] = []
    for key in (
        "description", "descricao", "title", "name", "caption", "alt",
        "alt_text", "tags", "keywords", "category", "location", "local",
        "city", "country", "filename",
    ):
        value = candidate.get(key)
        if value:
            if isinstance(value, (list, tuple, set)):
                values.extend(str(item) for item in value if item)
            else:
                values.append(str(value))
    return " ".join(values)


def _strict_must_into_candidate(candidate: dict[str, Any], must: list[str]) -> None:
    if not must:
        return
    try:
        current_declared = int(candidate.get("must_hits", 0) or 0)
    except (TypeError, ValueError):
        current_declared = 0
    try:
        original_declared = int(
            candidate.get("_sap_declared_must_hits", current_declared) or 0
        )
    except (TypeError, ValueError):
        original_declared = current_declared

    check = verified_must(candidate, {"must_have": must})
    verified = int(check.get("hits", 0) or 0)
    total = max(1, int(check.get("total", len(must)) or len(must)))

    candidate.setdefault("_sap_declared_must_hits", original_declared)
    candidate["_sap_verified_must_hits"] = verified
    candidate["_sap_verified_must_missing"] = list(check.get("missing", []))
    candidate["_sap_must_total"] = total
    candidate["_sap_must_corrected"] = verified != original_declared
    candidate["must_hits"] = verified
    candidate["must_coverage"] = max(0.0, min(1.0, verified / total))


def normalize_candidate(
    candidate: Any,
    *,
    query: str = "",
    must_have: list[str] | tuple[str, ...] | None = None,
) -> Any:
    if not isinstance(candidate, dict):
        return candidate

    description = candidate.get("description") or candidate.get("descricao")
    if description and not candidate.get("description"):
        candidate["description"] = description

    provider = candidate.get("provider") or candidate.get("fonte")
    if provider and not candidate.get("provider"):
        candidate["provider"] = provider

    media = candidate.get("media_type") or candidate.get("tipo") or candidate.get("type")
    if media and not candidate.get("media_type"):
        media_norm = _norm(media)
        candidate["media_type"] = (
            "video"
            if "video" in media_norm or "vídeo" in str(media).casefold()
            else "photo"
            if any(x in media_norm for x in ("foto", "photo", "image", "imagem"))
            else str(media)
        )

    if candidate.get("width") is None and candidate.get("largura") is not None:
        candidate["width"] = candidate.get("largura")
    if candidate.get("height") is None and candidate.get("altura") is not None:
        candidate["height"] = candidate.get("altura")

    must = [str(x).strip() for x in (must_have or []) if str(x).strip()]
    _strict_must_into_candidate(candidate, must)
    if query:
        candidate["_sap_search_query"] = str(query)
    if must:
        candidate["_sap_search_must"] = list(must)
    candidate.setdefault("_sap_schema", "MEDIA_RUNTIME_ADAPTER_V1")
    return candidate


def _normalize_result(result: Any, query: str, must_have: Any) -> Any:
    must = list(must_have or []) if isinstance(must_have, (list, tuple, set)) else []
    if isinstance(result, (list, tuple)):
        for candidate in result:
            normalize_candidate(candidate, query=query, must_have=must)
    return result


def _argument(
    signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    names: tuple[str, ...],
    default: Any = None,
) -> Any:
    try:
        bound = signature.bind_partial(*args, **kwargs)
    except Exception:
        return default
    for name in names:
        if name in bound.arguments:
            return bound.arguments[name]
    return default


def _wrap_provider(namespace: dict[str, Any], name: str) -> bool:
    original = namespace.get(name)
    if not callable(original) or getattr(original, "_sap_media_adapter", False):
        return False
    signature = inspect.signature(original)

    @functools.wraps(original)
    def wrapped(*args: Any, **kwargs: Any):
        if name.startswith("pexels_"):
            enabled = bool(namespace.get("USAR_PEXELS", True))
            key = str(namespace.get("PEXELS_KEY", "") or "").strip()
            if not enabled or not key:
                if "pexels" not in _PROVIDER_SKIP_PRINTED:
                    reason = "DISABLED" if not enabled else "NO_API_KEY"
                    print(f"SAP_PROVIDER_SKIP provider=pexels reason={reason}")
                    _PROVIDER_SKIP_PRINTED.add("pexels")
                return []

        query = _argument(signature, args, kwargs, ("busca", "query", "search"), "")
        must = _argument(signature, args, kwargs, ("must_have", "must"), [])
        result = original(*args, **kwargs)
        return _normalize_result(result, str(query or ""), must)

    wrapped._sap_media_adapter = True
    namespace[name] = wrapped
    return True


def _identity_sensitive(visual_mode: str) -> bool:
    mode = _norm(visual_mode)
    return any(
        token in mode
        for token in (
            "named person", "person identity", "identity", "specific person",
            "victim identity", "suspect identity", "real person",
        )
    )


def _contextual_metrics(
    candidate: dict[str, Any],
    query: str,
    must_have: list[str],
    visual_mode: str,
) -> tuple[bool, float, str]:
    if int(candidate.get("avoid_hits", 0) or 0) > 0:
        return False, 0.0, "AVOID_HIT"
    if int(candidate.get("must_hits", 0) or 0) > 0:
        return False, 0.0, "HAS_VERIFIED_MUST"
    if _identity_sensitive(visual_mode):
        return False, 0.0, "IDENTITY_SENSITIVE"

    evidence_class = str(candidate.get("evidence_class", "") or "").upper()
    if evidence_class in {"RISKY_IDENTITY", "BLOCKED", "MISLEADING_REENACTMENT"}:
        return False, 0.0, "EVIDENCE_RISK"

    scene_text = " ".join([query, *must_have]).strip()
    asset_text = _asset_text(candidate)
    scene_tokens = _tokens(scene_text)
    asset_tokens = _tokens(asset_text)
    if not scene_tokens or not asset_tokens:
        return False, 0.0, "NO_SEMANTIC_TEXT"

    overlap_count = len(scene_tokens & asset_tokens)
    overlap = overlap_count / max(1, min(len(scene_tokens), 4))
    concept_overlap = 0
    geo_conflict = False
    generic_mismatch = False

    try:
        import visual_selection_engine_v4 as vse
        scene_concepts = set(vse.concept_hits(scene_text))
        asset_concepts = set(vse.concept_hits(asset_text))
        concept_overlap = len(scene_concepts & asset_concepts)
        scene_geo = set(vse.geo_hits(scene_text))
        asset_geo = set(vse.geo_hits(asset_text))
        geo_conflict = bool(scene_geo and asset_geo and scene_geo.isdisjoint(asset_geo))

        generic_terms = set()
        for term in getattr(vse, "GENERIC_LIFESTYLE", set()):
            generic_terms.update(_tokens(term))
        generic_hits = bool(asset_tokens & generic_terms)
        documentary = bool(
            scene_concepts
            & {
                "police", "investigation", "crime_scene", "evidence",
                "forensics", "court", "prison", "law",
            }
        )
        generic_mismatch = (
            generic_hits and documentary and not (scene_concepts & asset_concepts)
        )
    except Exception:
        pass

    if geo_conflict:
        return False, 0.0, "GEO_CONTRADICTION"
    if generic_mismatch:
        return False, 0.0, "GENERIC_LIFESTYLE"

    semantic = overlap + min(0.50, concept_overlap * 0.20)
    min_semantic = _env_float("SAP_CONTEXTUAL_RESCUE_MIN_SEMANTIC", 0.25)
    if semantic < min_semantic:
        return False, semantic, "LOW_CONTEXT_OVERLAP"

    try:
        base_score = float(candidate.get("score", 0.0) or 0.0)
    except (TypeError, ValueError):
        base_score = 0.0
    min_score = _env_float("SAP_CONTEXTUAL_RESCUE_MIN_SCORE", 8.0)
    strong_semantic = _env_float("SAP_CONTEXTUAL_RESCUE_STRONG_SEMANTIC", 0.50)
    if base_score < min_score and semantic < strong_semantic:
        return False, semantic, "LOW_BASE_SCORE"
    if overlap_count <= 0 and concept_overlap <= 0:
        return False, semantic, "NO_DIRECT_CONTEXT"

    return True, semantic, "SAFE_CONTEXTUAL_RESCUE"


def _mark_contextual_rescue(
    result: Any,
    query: str,
    must_have: Any,
    visual_mode: str,
) -> Any:
    must = (
        [str(x) for x in must_have if str(x).strip()]
        if isinstance(must_have, (list, tuple, set))
        else []
    )
    candidates = result if isinstance(result, (list, tuple)) else []
    marked = 0
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        normalize_candidate(candidate, query=query, must_have=must)
        candidate["_sap_visual_mode"] = visual_mode
        ok, semantic, reason = _contextual_metrics(candidate, query, must, visual_mode)
        if not ok:
            continue
        candidate["_sap_contextual_rescue"] = True
        candidate["_sap_contextual_score"] = round(semantic, 4)
        candidate["_sap_contextual_reason"] = reason
        marked += 1
    if marked:
        print(f"SAP_CONTEXTUAL_RESCUE_POOL={marked} query={query}")
    return result


def _wrap_search(namespace: dict[str, Any]) -> bool:
    original = namespace.get("buscar_todos_candidatos")
    if not callable(original) or getattr(original, "_sap_media_adapter", False):
        return False
    signature = inspect.signature(original)

    @functools.wraps(original)
    def wrapped(*args: Any, **kwargs: Any):
        query = str(
            _argument(signature, args, kwargs, ("busca", "query", "search"), "") or ""
        )
        must = _argument(signature, args, kwargs, ("must_have", "must"), [])
        visual_mode = str(
            _argument(signature, args, kwargs, ("visual_mode", "modo_visual"), "") or ""
        )
        result = original(*args, **kwargs)
        result = _normalize_result(result, query, must)
        return _mark_contextual_rescue(result, query, must, visual_mode)

    wrapped._sap_media_adapter = True
    namespace["buscar_todos_candidatos"] = wrapped
    return True


def _wrap_semantic_policy(namespace: dict[str, Any]) -> tuple[bool, bool]:
    original_validator = namespace.get("candidato_semanticamente_valido")
    original_metadata = namespace.get("metadata_confiavel")
    validator_installed = False
    metadata_installed = False

    if callable(original_validator) and not getattr(
        original_validator, "_sap_media_adapter", False
    ):
        @functools.wraps(original_validator)
        def validator(candidate: Any, total_must: int, relaxado: bool = False):
            if isinstance(candidate, dict) and candidate.get("_sap_contextual_rescue"):
                if not relaxado:
                    return False
                if int(candidate.get("avoid_hits", 0) or 0) > 0:
                    return False
                return float(
                    candidate.get("_sap_contextual_score", 0.0) or 0.0
                ) >= _env_float("SAP_CONTEXTUAL_RESCUE_MIN_SEMANTIC", 0.25)
            return original_validator(candidate, total_must, relaxado=relaxado)

        validator._sap_media_adapter = True
        namespace["candidato_semanticamente_valido"] = validator
        validator_installed = True

    if callable(original_metadata) and not getattr(
        original_metadata, "_sap_media_adapter", False
    ):
        @functools.wraps(original_metadata)
        def metadata(candidate: Any):
            if isinstance(candidate, dict) and candidate.get("_sap_contextual_rescue"):
                return False
            return original_metadata(candidate)

        metadata._sap_media_adapter = True
        namespace["metadata_confiavel"] = metadata
        metadata_installed = True

    return validator_installed, metadata_installed


def _wrap_failover(namespace: dict[str, Any]) -> bool:
    original = namespace.get("ordenar_failover_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter", False):
        return False

    @functools.wraps(original)
    def wrapped(candidatos, total_must, rota_fonte, descricao_anterior=""):
        result = original(candidatos, total_must, rota_fonte, descricao_anterior)
        if result:
            return result

        pool = candidatos if isinstance(candidatos, (list, tuple)) else []
        rescue = [
            c
            for c in pool
            if isinstance(c, dict)
            and c.get("_sap_contextual_rescue")
            and int(c.get("avoid_hits", 0) or 0) == 0
        ]
        rescue.sort(
            key=lambda c: (
                float(c.get("_sap_contextual_score", 0.0) or 0.0),
                float(c.get("score", -999.0) or -999.0),
                1 if str(c.get("tipo", "")).casefold() in {"vídeo", "video"} else 0,
            ),
            reverse=True,
        )
        if rescue:
            print(
                "SAP_CONTEXTUAL_RESCUE_ACTIVATED="
                f"{len(rescue)} best={rescue[0].get('_sap_contextual_score', 0)}"
            )
        return rescue

    wrapped._sap_media_adapter = True
    namespace["ordenar_failover_5_2"] = wrapped
    return True


def _patch_unified_reranker() -> bool:
    try:
        import visual_engine_unified as unified
    except Exception:
        return False

    original = getattr(unified, "rerank_pool_runtime", None)
    if not callable(original) or getattr(original, "_sap_media_adapter", False):
        return bool(callable(original))

    @functools.wraps(original)
    def wrapped(pool: Any, ctx: Any = None):
        result = original(pool, ctx)
        if isinstance(result, list):
            for candidate in result:
                if isinstance(candidate, dict):
                    candidate.pop("_sap_visual_unified_winner", None)
            if result and isinstance(result[0], dict):
                result[0]["_sap_visual_unified_winner"] = True
        return result

    wrapped._sap_media_adapter = True
    unified.rerank_pool_runtime = wrapped
    return True


def _wrap_reference_guard(namespace: dict[str, Any]) -> bool:
    original = namespace.get("fallback_preserva_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, reference: Any):
        if isinstance(candidate, dict) and candidate.get("_sap_visual_unified_winner"):
            if int(candidate.get("avoid_hits", 0) or 0) > 0:
                return False
            return True
        return original(candidate, reference)

    wrapped._sap_media_adapter = True
    namespace["fallback_preserva_5_2"] = wrapped
    return True


def _patch_legacy_decision_bridges(namespace: dict[str, Any]) -> bool:
    patched = 0

    if "_vse42_finalize_pool" in namespace:
        namespace["_vse42_finalize_pool"] = lambda pool, escolhido, ctx=None: pool
        patched += 1
    if "_vse42_enabled" in namespace:
        namespace["_vse42_enabled"] = lambda *args, **kwargs: False
        patched += 1

    try:
        import visual_selection_engine_v4 as module
        module.choose_from_context = lambda ctx, globals_ns, current: current
        patched += 1
    except Exception:
        pass

    try:
        import visual_selection_runtime_v42 as module

        def no_enhance(escolhido, pool, *args, **kwargs):
            return escolhido, pool, {"disabled": True, "authority": "VISUAL_UNIFIED"}

        module.enhance_selection = no_enhance
        module.note_commit = lambda *args, **kwargs: None
        patched += 1
    except Exception:
        pass

    try:
        import visual_selection_bridge_v42 as module

        def no_rank(pool, escolhido, *args, **kwargs):
            return pool, escolhido, {"disabled": True, "authority": "VISUAL_UNIFIED"}

        module.rank_pool = no_rank
        module.commit_candidate = lambda *args, **kwargs: True
        patched += 1
    except Exception:
        pass

    try:
        import visual_gate_v4x as module

        def no_gate(ctx, pool, escolhido, *args, **kwargs):
            return escolhido, pool, {"disabled": True, "authority": "VISUAL_UNIFIED"}

        module.choose_from_locals = no_gate
        patched += 1
    except Exception:
        pass

    try:
        import visual_selection_runtime_bridge_v42 as module
        module.rerank_pool = lambda pool, ctx=None: (
            pool,
            {"disabled": True, "authority": "VISUAL_UNIFIED"},
        )
        module.note_selected = lambda *args, **kwargs: None
        patched += 1
    except Exception:
        pass

    print(
        "MEDIA_LEGACY_DECISION_BRIDGES=DISABLED "
        f"patched={patched} authority=VISUAL_UNIFIED"
    )
    return patched > 0


def _wrap_download_tracking(namespace: dict[str, Any]) -> bool:
    original = namespace.get("baixar_candidato_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, numero: int, rotulo: str):
        ok, destino = original(candidate, numero, rotulo)
        if ok and destino:
            namespace["_SAP_LAST_SUCCESS_PATH"] = str(destino)
            namespace["_SAP_LAST_SUCCESS_CANDIDATE"] = candidate
        return ok, destino

    wrapped._sap_media_adapter = True
    namespace["baixar_candidato_5_2"] = wrapped
    return True


def _wrap_local_continuity_fallback(namespace: dict[str, Any]) -> bool:
    original = namespace.get("buscar_local")
    if not callable(original) or getattr(original, "_sap_media_adapter", False):
        return False

    @functools.wraps(original)
    def wrapped(preferir_video: bool):
        result = original(preferir_video)
        if result:
            return result
        if os.getenv("SAP_MEDIA_CONTINUITY_FALLBACK", "1") != "1":
            return None

        previous = str(namespace.get("_SAP_LAST_SUCCESS_PATH", "") or "")
        if not previous:
            return None
        path = Path(previous)
        if not path.is_file():
            return None

        print(
            "SAP_MEDIA_CONTINUITY_FALLBACK=REUSE_PREVIOUS_SCENE "
            f"path={path.name}"
        )
        return str(path)

    wrapped._sap_media_adapter = True
    namespace["buscar_local"] = wrapped
    return True


def install(namespace: dict[str, Any]) -> dict[str, Any]:
    for key, value in _CANONICAL_ENV.items():
        os.environ[key] = value

    if "VI6_MODE" in namespace:
        namespace["VI6_MODE"] = "SHADOW"

    provider_names = (
        "pexels_video", "pexels_foto", "pixabay_video", "pixabay_foto",
        "coverr_video", "buscar_wikimedia_fotos",
    )
    providers = [name for name in provider_names if _wrap_provider(namespace, name)]
    search = _wrap_search(namespace)
    validator, metadata = _wrap_semantic_policy(namespace)
    failover = _wrap_failover(namespace)
    unified = _patch_unified_reranker()
    reference_guard = _wrap_reference_guard(namespace)
    legacy_disabled = _patch_legacy_decision_bridges(namespace)
    download_tracking = _wrap_download_tracking(namespace)
    continuity = _wrap_local_continuity_fallback(namespace)

    result = {
        "version": VERSION,
        "installed": True,
        "providers": providers,
        "search": search,
        "validator": validator,
        "metadata": metadata,
        "failover": failover,
        "unified": unified,
        "reference_guard": reference_guard,
        "legacy_disabled": legacy_disabled,
        "download_tracking": download_tracking,
        "continuity": continuity,
        "legacy_vse4": False,
        "legacy_vse42": False,
        "legacy_vg4x": False,
        "query_expansion": True,
        "vi6_mode": "SHADOW",
    }
    print(
        "MEDIA_RUNTIME_ADAPTER=INSTALLED "
        f"version={VERSION} providers={len(providers)} search={search} "
        f"contextual_policy={validator and metadata} failover={failover} "
        f"continuity={continuity} query_expansion=True "
        "authority=VISUAL_UNIFIED vi6=SHADOW"
    )
    return result


__all__ = [
    "VERSION",
    "install",
    "normalize_candidate",
    "_contextual_metrics",
    "_mark_contextual_rescue",
]
