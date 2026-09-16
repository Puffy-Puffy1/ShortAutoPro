#!/usr/bin/env python3
"""ShortAutoPro media runtime reliability layer 3.0.2.

Installed after media_runtime_adapter_v1.  This layer closes production-only
Termux gaps without weakening strict MUST verification:

- contextual rescue uses a neutral score that restores only the legacy
  missing-MUST penalty and never fabricates MUST coverage;
- a marked rescue is allowed into failover only after the strict/relaxed
  canonical pool is otherwise empty;
- the safe Visual Unified winner cannot be rejected by a stale pre-rerank
  reference;
- retired VSE42 aliases remain passthrough/no-op while query expansion stays
  available only as candidate enrichment;
- if every provider and rescue is exhausted, the last successfully validated
  scene asset may be reused as an explicit low-trust continuity fallback so a
  single sparse query does not crash an otherwise complete production.  Final
  QA/release gates still retain authority to repair/block the output.
"""
from __future__ import annotations

import functools
import inspect
import os
from pathlib import Path
from typing import Any

import media_runtime_adapter_v1 as v1

VERSION = "2.1"
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
    """Return score before only the legacy missing-MUST penalty."""
    try:
        base = float(candidate.get("score", 0.0) or 0.0)
    except (TypeError, ValueError):
        base = 0.0

    try:
        total = int(candidate.get("_sap_must_total", 0) or 0)
    except (TypeError, ValueError):
        total = 0
    try:
        verified = int(
            candidate.get("_sap_verified_must_hits", candidate.get("must_hits", 0)) or 0
        )
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

        if int(candidate.get("must_hits", 0) or 0) > 0:
            continue
        if candidate.get("_sap_contextual_rescue"):
            continue

        neutral = neutral_context_score(candidate)
        probe = dict(candidate)
        probe["score"] = neutral

        ok, semantic, _reason = v1._contextual_metrics(probe, query, must, visual_mode)
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
        query = str(
            _argument(signature, args, kwargs, ("busca", "query", "search"), "") or ""
        )
        must = _argument(signature, args, kwargs, ("must_have", "must"), [])
        visual_mode = str(
            _argument(signature, args, kwargs, ("visual_mode", "modo_visual"), "") or ""
        )
        result = original(*args, **kwargs)
        return _mark_neutral_rescue(result, query, must, visual_mode)

    wrapped._sap_media_adapter_v2 = True
    namespace["buscar_todos_candidatos"] = wrapped
    return True


def _wrap_failover(namespace: dict[str, Any]) -> bool:
    """Expose marked contextual rescue only when canonical failover is empty."""
    original = namespace.get("ordenar_failover_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(candidates, total_must, route, previous_description=""):
        result = original(candidates, total_must, route, previous_description)
        if result:
            return result

        source = candidates if isinstance(candidates, (list, tuple)) else []
        rescue = [
            candidate
            for candidate in source
            if isinstance(candidate, dict)
            and candidate.get("_sap_contextual_rescue")
            and int(candidate.get("avoid_hits", 0) or 0) == 0
        ]

        rescue.sort(
            key=lambda candidate: (
                float(candidate.get("_sap_contextual_score", 0.0) or 0.0),
                float(
                    candidate.get(
                        "_sap_contextual_neutral_score",
                        neutral_context_score(candidate),
                    )
                    or 0.0
                ),
                float(candidate.get("score", -999.0) or -999.0),
            ),
            reverse=True,
        )

        if rescue:
            print(
                "SAP_CONTEXTUAL_RESCUE_V2_ACTIVATED="
                f"{len(rescue)} best={rescue[0].get('_sap_contextual_score', 0)} "
                "must=0 policy=STRICT_POOL_EMPTY"
            )
        return rescue

    wrapped._sap_media_adapter_v2 = True
    namespace["ordenar_failover_5_2"] = wrapped
    return True


def _wrap_unified_winner() -> bool:
    """Tag only a safe first-place Visual Unified candidate."""
    try:
        import visual_engine_unified as unified
    except Exception:
        return False

    original = getattr(unified, "rerank_pool_runtime", None)
    if not callable(original):
        return False
    if getattr(original, "_sap_media_adapter_v2", False):
        return True

    @functools.wraps(original)
    def wrapped(pool: Any, ctx: Any = None):
        result = original(pool, ctx)
        if not isinstance(result, list):
            return result

        for candidate in result:
            if isinstance(candidate, dict):
                candidate.pop("_sap_visual_unified_winner", None)
                candidate.pop("_sap_visual_unified_hard", None)

        if result and isinstance(result[0], dict):
            hard = False
            try:
                scene = unified.scene_from_runtime(ctx or {})
                state = unified._load_state(unified._sid(ctx))
                score = unified._score(result[0], scene, state)
                hard = bool(score.get("hard_mismatch", False))
            except Exception:
                hard = False

            result[0]["_sap_visual_unified_hard"] = hard
            if not hard and int(result[0].get("avoid_hits", 0) or 0) == 0:
                result[0]["_sap_visual_unified_winner"] = True
        return result

    wrapped._sap_media_adapter_v2 = True
    unified.rerank_pool_runtime = wrapped
    return True


def _wrap_reference_guard(namespace: dict[str, Any]) -> bool:
    """Prevent stale pre-rerank reference from defeating canonical decisions."""
    original = namespace.get("fallback_preserva_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, reference: Any):
        if isinstance(candidate, dict):
            if int(candidate.get("avoid_hits", 0) or 0) > 0:
                return False
            if candidate.get("_sap_visual_unified_winner") and not candidate.get(
                "_sap_visual_unified_hard", False
            ):
                return True
            # Contextual rescue is produced only by the retry/search path and
            # already passed identity/avoid/geography safeguards.
            if candidate.get("_sap_contextual_rescue"):
                return True
        return original(candidate, reference)

    wrapped._sap_media_adapter_v2 = True
    namespace["fallback_preserva_5_2"] = wrapped
    return True


def _disable_legacy_vse42_authority(namespace: dict[str, Any]) -> dict[str, bool]:
    """Patch imported VSE42 aliases; query expansion remains untouched."""
    patched = {
        "enabled": False,
        "finalize": False,
        "note_success": False,
        "commit_media": False,
    }

    if "_vse42_enabled" in namespace:
        namespace["_vse42_enabled"] = lambda: False
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
        namespace["_vse42_note_success"] = lambda candidate: None
        patched["note_success"] = True

    if "_vse42_commit_media" in namespace:
        namespace["_vse42_commit_media"] = lambda path: []
        patched["commit_media"] = True

    return patched


def _wrap_download_tracking(namespace: dict[str, Any]) -> bool:
    original = namespace.get("baixar_candidato_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, scene_number: int, label: str):
        ok, destination = original(candidate, scene_number, label)
        if ok and destination:
            namespace["_SAP_LAST_VALID_MEDIA_PATH"] = str(destination)
        return ok, destination

    wrapped._sap_media_adapter_v2 = True
    namespace["baixar_candidato_5_2"] = wrapped
    return True


def _wrap_local_continuity(namespace: dict[str, Any]) -> bool:
    """Last-resort reuse of the previous validated scene media."""
    original = namespace.get("buscar_local")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(prefer_video: bool):
        local = original(prefer_video)
        if local:
            return local
        if os.getenv("SAP_MEDIA_CONTINUITY_FALLBACK", "1") != "1":
            return None

        previous = str(namespace.get("_SAP_LAST_VALID_MEDIA_PATH", "") or "")
        if not previous:
            return None
        path = Path(previous)
        if not path.is_file():
            return None

        namespace["_SAP_CONTINUITY_REUSE_ID"] = path.name
        print(
            "SAP_MEDIA_CONTINUITY_FALLBACK=REUSE_PREVIOUS_SCENE "
            f"path={path.name} trust=LOW"
        )
        return str(path)

    wrapped._sap_media_adapter_v2 = True
    namespace["buscar_local"] = wrapped
    return True


def _wrap_continuity_metadata(namespace: dict[str, Any]) -> bool:
    original = namespace.get("metadata_confiavel")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any):
        if isinstance(candidate, dict):
            reuse_id = str(namespace.get("_SAP_CONTINUITY_REUSE_ID", "") or "")
            if (
                reuse_id
                and str(candidate.get("fonte", "")).casefold() == "local"
                and str(candidate.get("id", "")) == reuse_id
            ):
                return False
        return original(candidate)

    wrapped._sap_media_adapter_v2 = True
    namespace["metadata_confiavel"] = wrapped
    return True


def install(namespace: dict[str, Any]) -> dict[str, Any]:
    os.environ.setdefault("SAP_MEDIA_CONTINUITY_FALLBACK", "1")

    base = v1.install(namespace)
    search = _wrap_search(namespace)
    failover = _wrap_failover(namespace)
    unified_winner = _wrap_unified_winner()
    reference_guard = _wrap_reference_guard(namespace)
    vse42 = _disable_legacy_vse42_authority(namespace)
    download_tracking = _wrap_download_tracking(namespace)
    continuity = _wrap_local_continuity(namespace)
    continuity_metadata = _wrap_continuity_metadata(namespace)

    result = {
        "version": VERSION,
        "installed": True,
        "base": base,
        "neutral_contextual_rescue": search,
        "contextual_failover": failover,
        "unified_winner_guard": unified_winner,
        "reference_guard": reference_guard,
        "download_tracking": download_tracking,
        "continuity_fallback": continuity,
        "continuity_low_trust": continuity_metadata,
        "vse42_authority_disabled": all(vse42.values()) if vse42 else False,
        "vse42_hooks": vse42,
        "authority": "VISUAL_UNIFIED",
        "query_expansion": True,
        "vi6_mode": "SHADOW",
    }

    print(
        "MEDIA_RUNTIME_ADAPTER_V2=INSTALLED "
        f"version={VERSION} neutral_rescue={search} failover={failover} "
        f"unified_guard={unified_winner and reference_guard} "
        f"continuity={continuity} "
        f"vse42_decision_disabled={result['vse42_authority_disabled']} "
        "query_expansion=True authority=VISUAL_UNIFIED"
    )
    return result


__all__ = [
    "VERSION",
    "install",
    "neutral_context_score",
    "_mark_neutral_rescue",
    "_wrap_failover",
]
