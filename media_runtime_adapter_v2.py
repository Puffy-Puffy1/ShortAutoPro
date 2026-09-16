#!/usr/bin/env python3
"""ShortAutoPro media runtime reliability layer 3.0.2.

This adapter is installed after media_runtime_adapter_v1.  It fixes two
production-only failure modes seen on Termux:

1. Contextual rescue used the already MUST-penalized provider score.  A safe
   contextual candidate could therefore score ~60 before a missing-MUST
   penalty, fall to ~20, and be discarded before relaxed retry could use it.
   V2 evaluates rescue against a neutral contextual score that adds back only
   the missing-MUST penalty.  It never fabricates MUST hits.

2. The retired VSE42 finalizer could still restore the legacy ``chosen`` item
   to the front of a pool after Visual Unified had ranked it.  V2 turns the
   VSE42 decision/commit aliases in the live midia.py namespace into strict
   passthrough/no-op hooks. Query expansion stays enabled as pool enrichment.
"""
from __future__ import annotations

import functools
import inspect
from typing import Any

import media_runtime_adapter_v1 as v1

VERSION = "2.0"
MISSING_MUST_PENALTY = 20.0


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


def _must_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def neutral_context_score(candidate: dict[str, Any]) -> float:
    """Return score before only the legacy missing-MUST penalty.

    This does not alter ``candidate['score']`` and does not change MUST
    coverage.  Other penalties/rewards remain intact.
    """
    try:
        base = float(candidate.get("score", 0.0) or 0.0)
    except (TypeError, ValueError):
        base = 0.0

    try:
        total = int(candidate.get("_sap_must_total", 0) or 0)
    except (TypeError, ValueError):
        total = 0
    try:
        verified = int(candidate.get("_sap_verified_must_hits", candidate.get("must_hits", 0)) or 0)
    except (TypeError, ValueError):
        verified = 0

    missing = max(0, total - verified)
    return base + (MISSING_MUST_PENALTY * missing)


def _mark_neutral_rescue(
    result: Any,
    query: str,
    must_have: Any,
    visual_mode: str,
) -> Any:
    must = _must_list(must_have)
    candidates = result if isinstance(result, (list, tuple)) else []
    marked = 0

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        v1.normalize_candidate(candidate, query=query, must_have=must)

        # A real verified MUST candidate does not need rescue, and an item
        # already rescued by V1 should keep its original diagnostics.
        if int(candidate.get("must_hits", 0) or 0) > 0:
            continue
        if candidate.get("_sap_contextual_rescue"):
            continue

        neutral = neutral_context_score(candidate)
        probe = dict(candidate)
        probe["score"] = neutral

        ok, semantic, reason = v1._contextual_metrics(probe, query, must, visual_mode)
        if not ok:
            continue

        candidate["_sap_contextual_rescue"] = True
        candidate["_sap_contextual_score"] = round(float(semantic), 4)
        candidate["_sap_contextual_reason"] = "SAFE_CONTEXTUAL_RESCUE_NEUTRAL_MUST"
        candidate["_sap_contextual_neutral_score"] = round(neutral, 3)
        candidate["_sap_contextual_original_score"] = candidate.get("score", 0.0)
        marked += 1

    if marked:
        print(
            "SAP_CONTEXTUAL_RESCUE_V2_POOL="
            f"{marked} query={query} policy=NEUTRAL_MISSING_MUST"
        )
    return result


def _wrap_search(namespace: dict[str, Any]) -> bool:
    original = namespace.get("buscar_todos_candidatos")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    signature = inspect.signature(original)

    @functools.wraps(original)
    def wrapped(*args: Any, **kwargs: Any):
        query = str(_argument(signature, args, kwargs, ("busca", "query", "search"), "") or "")
        must = _argument(signature, args, kwargs, ("must_have", "must"), [])
        visual_mode = str(_argument(signature, args, kwargs, ("visual_mode", "modo_visual"), "") or "")
        result = original(*args, **kwargs)
        return _mark_neutral_rescue(result, query, must, visual_mode)

    wrapped._sap_media_adapter_v2 = True
    namespace["buscar_todos_candidatos"] = wrapped
    return True


def _disable_legacy_vse42_authority(namespace: dict[str, Any]) -> dict[str, bool]:
    """Patch imported VSE42 aliases in midia.py after all imports happened.

    Query expansion is intentionally not touched.  Only final decision/order,
    commit telemetry and sibling commit authority are retired here.
    """
    patched = {
        "enabled": False,
        "finalize": False,
        "note_success": False,
        "commit_media": False,
    }

    if "_vse42_enabled" in namespace:
        def disabled() -> bool:
            return False
        namespace["_vse42_enabled"] = disabled
        patched["enabled"] = True

    if "_vse42_finalize_pool" in namespace:
        def passthrough(pool: Any, chosen: Any, local_context: Any = None):
            del local_context
            if isinstance(pool, (list, tuple)):
                ordered = list(pool)
                if ordered:
                    return ordered
            return [chosen] if chosen is not None else []
        namespace["_vse42_finalize_pool"] = passthrough
        patched["finalize"] = True

    if "_vse42_note_success" in namespace:
        def no_note(candidate: Any):
            del candidate
            return None
        namespace["_vse42_note_success"] = no_note
        patched["note_success"] = True

    if "_vse42_commit_media" in namespace:
        def no_commit(path: Any):
            del path
            return []
        namespace["_vse42_commit_media"] = no_commit
        patched["commit_media"] = True

    return patched


def install(namespace: dict[str, Any]) -> dict[str, Any]:
    base = v1.install(namespace)
    search = _wrap_search(namespace)
    vse42 = _disable_legacy_vse42_authority(namespace)

    result = {
        "version": VERSION,
        "installed": True,
        "base": base,
        "neutral_contextual_rescue": search,
        "vse42_authority_disabled": all(vse42.values()) if vse42 else False,
        "vse42_hooks": vse42,
        "authority": "VISUAL_UNIFIED",
        "query_expansion": True,
        "vi6_mode": "SHADOW",
    }

    print(
        "MEDIA_RUNTIME_ADAPTER_V2=INSTALLED "
        f"neutral_rescue={search} "
        f"vse42_decision_disabled={result['vse42_authority_disabled']} "
        "query_expansion=True authority=VISUAL_UNIFIED"
    )
    return result


__all__ = ["VERSION", "install", "neutral_context_score"]
