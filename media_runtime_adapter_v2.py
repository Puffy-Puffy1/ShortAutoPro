#!/usr/bin/env python3
"""ShortAutoPro media runtime reliability layer 3.0.3.

Installed after media_runtime_adapter_v1. This layer hardens production-only
Termux behavior without weakening explicit scene truth requirements:

- contextual rescue is available only after the canonical strict pool is empty;
- repeated empty Coverr responses open a process-local circuit breaker so one
  unavailable provider is not called again for every scene/retry;
- Visual Unified may prefer a video only when it preserves the winning MUST
  tier, safety constraints and semantic score within a small bounded tolerance;
- blind previous-scene reuse is disabled by default. A scene with explicit MUST
  requirements can never silently fall back to an unrelated local asset;
- every successful canonical download is persisted in a per-Short selection
  manifest so downstream scoring evaluates the asset that was actually chosen;
- the safe Visual Unified winner cannot be rejected by a stale pre-rerank
  reference;
- retired VSE42 aliases remain passthrough/no-op while query expansion stays
  candidate enrichment only.
"""
from __future__ import annotations

import functools
import inspect
import json
import os
from pathlib import Path
from typing import Any

import media_runtime_adapter_v1 as v1

VERSION = "2.2"
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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return default


def _media_type(candidate: Any) -> str:
    if not isinstance(candidate, dict):
        return ""
    value = str(
        candidate.get("media_type")
        or candidate.get("tipo")
        or candidate.get("type")
        or ""
    ).casefold()
    if "video" in value or "vídeo" in value:
        return "video"
    if any(token in value for token in ("foto", "photo", "image", "imagem")):
        return "photo"
    return value


def neutral_context_score(candidate: dict[str, Any]) -> float:
    """Return score before only the legacy missing-MUST penalty."""
    base = _float(candidate.get("score", 0.0), 0.0)
    total = _int(candidate.get("_sap_must_total", 0), 0)
    verified = _int(
        candidate.get("_sap_verified_must_hits", candidate.get("must_hits", 0)),
        0,
    )
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
        ok, semantic, _reason = v1._contextual_metrics(
            probe,
            query,
            must,
            visual_mode,
        )
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
        namespace["_SAP_LAST_SEARCH_QUERY"] = query
        namespace["_SAP_LAST_SEARCH_MUST"] = _must_list(must)
        namespace["_SAP_LAST_VISUAL_MODE"] = visual_mode
        result = original(*args, **kwargs)
        return _mark_neutral_rescue(result, query, must, visual_mode)

    wrapped._sap_media_adapter_v2 = True
    namespace["buscar_todos_candidatos"] = wrapped
    return True


def _wrap_failover(namespace: dict[str, Any]) -> bool:
    """Expose safe contextual rescue only when canonical failover is empty."""
    original = namespace.get("ordenar_failover_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(candidates, total_must, route, previous_description=""):
        namespace["_SAP_CURRENT_TOTAL_MUST"] = max(0, _int(total_must, 0))
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


def _wrap_coverr_circuit(namespace: dict[str, Any]) -> bool:
    """Stop repeatedly calling Coverr after the first empty/unavailable result."""
    original = namespace.get("coverr_video")
    if not callable(original) or getattr(original, "_sap_coverr_circuit_v2", False):
        return False
    state = {"open": False, "skip_printed": False}

    @functools.wraps(original)
    def wrapped(*args: Any, **kwargs: Any):
        enabled = os.getenv("SAP_COVERR_CIRCUIT_BREAKER", "1") == "1"
        if enabled and state["open"]:
            if not state["skip_printed"]:
                print("SAP_PROVIDER_SKIP provider=coverr reason=CIRCUIT_OPEN")
                state["skip_printed"] = True
            return []
        result = original(*args, **kwargs)
        if enabled and not result:
            state["open"] = True
            print(
                "SAP_PROVIDER_CIRCUIT_OPEN provider=coverr "
                "reason=FIRST_EMPTY_RESULT"
            )
        return result

    wrapped._sap_coverr_circuit_v2 = True
    namespace["coverr_video"] = wrapped
    return True


def _motion_balance_result(unified: Any, result: list[Any], ctx: Any) -> list[Any]:
    """Prefer video only when it preserves semantic/MUST quality."""
    if os.getenv("SAP_MOTION_BALANCE", "1") != "1":
        return result
    if not result or not isinstance(ctx, dict):
        return result

    videos_total = _int(ctx.get("videos_total"), 0)
    target = _int(ctx.get("VIDEO_META"), 0)
    if target <= 0 or videos_total >= target or _media_type(result[0]) == "video":
        return result

    scene = unified.scene_from_runtime(ctx)
    state = unified._load_state(unified._sid(ctx))
    winner = result[0]
    winner_score = unified._score(winner, scene, state)
    if bool(winner_score.get("hard_mismatch", False)):
        return result

    winner_must = _int(winner_score.get("must"), 0)
    winner_effective = _float(winner_score.get("effective"), 0.0)
    winner_evidence = str(winner.get("evidence_class", "") or "").upper()
    tolerance = _float(os.getenv("SAP_MOTION_SEMANTIC_TOLERANCE", "18"), 18.0)
    remaining = max(1, _int(ctx.get("cenas_restantes"), 1))
    needed = max(0, target - videos_total)
    if needed >= remaining:
        tolerance = max(tolerance, 28.0)

    choices: list[tuple[float, int, Any, dict[str, Any]]] = []
    for index, candidate in enumerate(result[1:], 1):
        if _media_type(candidate) != "video" or not isinstance(candidate, dict):
            continue
        if int(candidate.get("avoid_hits", 0) or 0) > 0:
            continue
        score = unified._score(candidate, scene, state)
        if bool(score.get("hard_mismatch", False)):
            continue
        must = _int(score.get("must"), 0)
        effective = _float(score.get("effective"), -9999.0)
        if must < winner_must:
            continue
        if effective < winner_effective - tolerance:
            continue
        if winner_evidence == "CASE_DIRECT":
            candidate_evidence = str(candidate.get("evidence_class", "") or "").upper()
            if candidate_evidence != "CASE_DIRECT":
                continue
        choices.append((effective, -index, candidate, score))

    if not choices:
        return result
    choices.sort(key=lambda item: (item[0], item[1]), reverse=True)
    effective, _neg_index, selected, selected_score = choices[0]
    selected_index = result.index(selected)
    balanced = [selected] + result[:selected_index] + result[selected_index + 1 :]
    print(
        "SAP_MOTION_BALANCE_OVERRIDE=YES "
        f"videos={videos_total}/{target} "
        f"must={selected_score.get('must', 0)} "
        f"effective={effective:.1f} winner_effective={winner_effective:.1f} "
        f"tolerance={tolerance:.1f}"
    )
    return balanced


def _wrap_unified_winner() -> bool:
    """Tag only a safe first-place Visual Unified candidate after motion balance."""
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
        result = _motion_balance_result(unified, result, ctx)
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
            if candidate.get("_sap_contextual_rescue"):
                return True
        return original(candidate, reference)

    wrapped._sap_media_adapter_v2 = True
    namespace["fallback_preserva_5_2"] = wrapped
    return True


def _disable_legacy_vse42_authority(namespace: dict[str, Any]) -> dict[str, bool]:
    patched = {"enabled": False, "finalize": False, "note_success": False, "commit_media": False}
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


def _selection_manifest_path() -> Path:
    base = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
    sid = str(os.getenv("SHORT_ID", "") or "default").strip()
    return base / "roteiros" / f"media_selection_{sid}.json"


def _write_selection_record(
    candidate: Any,
    scene_number: int,
    destination: Any,
    label: str,
) -> None:
    if not isinstance(candidate, dict):
        return
    path = _selection_manifest_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    scenes = payload.get("scenes", [])
    if not isinstance(scenes, list):
        scenes = []
    scenes = [
        item for item in scenes
        if isinstance(item, dict) and _int(item.get("scene"), -1) != int(scene_number)
    ]

    description = str(
        candidate.get("description")
        or candidate.get("descricao")
        or candidate.get("title")
        or candidate.get("name")
        or ""
    ).strip()
    must_total = _int(candidate.get("_sap_must_total"), 0)
    must_hits = _int(
        candidate.get("_sap_verified_must_hits", candidate.get("must_hits", 0)),
        0,
    )
    record = {
        "scene": int(scene_number),
        "provider": str(candidate.get("provider") or candidate.get("fonte") or ""),
        "media_type": _media_type(candidate),
        "description": description,
        "score": round(_float(candidate.get("score"), 0.0), 3),
        "must_hits": must_hits,
        "must_total": must_total,
        "must_coverage": round(must_hits / must_total, 4) if must_total > 0 else 1.0,
        "avoid_hits": _int(candidate.get("avoid_hits"), 0),
        "evidence_class": str(candidate.get("evidence_class") or ""),
        "topic_overlap": round(_float(candidate.get("topic_overlap"), 0.0), 4),
        "segment_overlap": round(_float(candidate.get("segment_overlap"), 0.0), 4),
        "semantic_score": round(
            _float(candidate.get("_semantic_score", candidate.get("_sap_contextual_score", 0.0)), 0.0),
            4,
        ),
        "contextual_rescue": bool(candidate.get("_sap_contextual_rescue")),
        "local_path": str(destination or ""),
        "selection_label": str(label or ""),
    }
    scenes.append(record)
    scenes.sort(key=lambda item: _int(item.get("scene"), 9999))
    payload = {
        "short_id": str(os.getenv("SHORT_ID", "") or ""),
        "version": "MEDIA_SELECTION_1.0",
        "scenes": scenes,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _wrap_download_tracking(namespace: dict[str, Any]) -> bool:
    original = namespace.get("baixar_candidato_5_2")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, scene_number: int, label: str):
        ok, destination = original(candidate, scene_number, label)
        if ok and destination:
            namespace["_SAP_LAST_VALID_MEDIA_PATH"] = str(destination)
            try:
                _write_selection_record(candidate, scene_number, destination, label)
            except Exception as exc:
                print(
                    "SAP_MEDIA_SELECTION_MANIFEST=FAIL_OPEN "
                    f"{type(exc).__name__}:{exc}"
                )
        return ok, destination

    wrapped._sap_media_adapter_v2 = True
    namespace["baixar_candidato_5_2"] = wrapped
    return True


def _wrap_local_continuity(namespace: dict[str, Any]) -> bool:
    original = namespace.get("buscar_local")
    if not callable(original) or getattr(original, "_sap_media_adapter_v2", False):
        return False

    @functools.wraps(original)
    def wrapped(prefer_video: bool):
        total_must = max(0, _int(namespace.get("_SAP_CURRENT_TOTAL_MUST"), 0))
        allow_unverified = os.getenv("SAP_ALLOW_UNVERIFIED_LOCAL_FALLBACK", "0") == "1"
        local = original(prefer_video)
        if local and (total_must == 0 or allow_unverified):
            return local
        if local and total_must > 0:
            print(
                "SAP_LOCAL_FALLBACK_REJECTED reason=EXPLICIT_MUST_UNVERIFIED "
                f"must_total={total_must}"
            )

        allow_previous = os.getenv("SAP_ALLOW_LOW_TRUST_CONTINUITY", "0") == "1"
        if not allow_previous:
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
            f"path={path.name} trust=LOW explicit_opt_in=YES"
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
    os.environ.setdefault("SAP_CONTEXTUAL_RESCUE_MIN_SCORE", "20")
    os.environ.setdefault("SAP_CONTEXTUAL_RESCUE_MIN_SEMANTIC", "0.20")
    os.environ.setdefault("SAP_COVERR_CIRCUIT_BREAKER", "1")
    os.environ.setdefault("SAP_MOTION_BALANCE", "1")
    os.environ.setdefault("SAP_MOTION_SEMANTIC_TOLERANCE", "18")
    os.environ.setdefault("SAP_ALLOW_UNVERIFIED_LOCAL_FALLBACK", "0")
    os.environ.setdefault("SAP_ALLOW_LOW_TRUST_CONTINUITY", "0")

    base = v1.install(namespace)
    coverr_circuit = _wrap_coverr_circuit(namespace)
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
        "provider_circuit": coverr_circuit,
        "neutral_contextual_rescue": search,
        "contextual_failover": failover,
        "unified_winner_guard": unified_winner,
        "motion_balance": unified_winner,
        "reference_guard": reference_guard,
        "download_tracking": download_tracking,
        "selection_manifest": download_tracking,
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
        f"version={VERSION} provider_circuit={coverr_circuit} "
        f"neutral_rescue={search} failover={failover} "
        f"unified_guard={unified_winner and reference_guard} "
        f"motion_balance={unified_winner} selection_manifest={download_tracking} "
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
