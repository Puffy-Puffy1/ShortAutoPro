#!/usr/bin/env python3
"""ShortAutoPro Visual Engine Unified V5.2.

Sole production reranker between media acquisition and scene commit. Explicit
scene MUST requirements are re-verified from real asset evidence and override
legacy provider-declared must_hits/must_coverage values.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

import visual_selection_engine_v4 as vse
from media_must_verifier import verified_must

ROOT = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
VERSION = "5.3_CANONICAL_COMMIT_LEDGER"
_MUST_WEIGHT = 115.0  # same weight used by the legacy VSE effective score


def _sid(ctx: Any = None) -> str:
    if isinstance(ctx, dict):
        for key in ("SHORT_ID", "short_id"):
            value = ctx.get(key)
            if value:
                return str(value)
    return os.getenv("SHORT_ID", "default")


def _state_path(sid: str) -> Path:
    return ROOT / "temp" / f"visual_unified_state_{sid}.json"


def _empty_state() -> dict[str, list[Any]]:
    return {"providers": [], "groups": [], "types": [], "keys": []}


def _selection_path(sid: str) -> Path:
    return ROOT / "roteiros" / f"selected_media_{sid}.json"


def _safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _load_selection(sid: str) -> dict[str, Any]:
    path = _selection_path(sid)
    if not path.is_file():
        return {"short_id": sid, "version": "CANONICAL_SELECTED_MEDIA_1.0", "scenes": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"short_id": sid, "version": "CANONICAL_SELECTED_MEDIA_1.0", "scenes": {}}
    if not isinstance(data, dict):
        data = {}
    scenes = data.get("scenes") if isinstance(data.get("scenes"), dict) else {}
    return {
        "short_id": sid,
        "version": "CANONICAL_SELECTED_MEDIA_1.0",
        "scenes": dict(scenes),
    }


def _save_selection(sid: str, payload: dict[str, Any]) -> None:
    path = _selection_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def _load_state(sid: str) -> dict[str, list[Any]]:
    path = _state_path(sid)
    if not path.is_file():
        return _empty_state()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _empty_state()
    state = _empty_state()
    if isinstance(data, dict):
        for key in state:
            value = data.get(key, [])
            if isinstance(value, list):
                state[key] = value[-24:]
    return state


def _save_state(sid: str, state: dict[str, list[Any]]) -> None:
    path = _state_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {key: list(state.get(key, []))[-24:] for key in _empty_state()}
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def _context_value(ctx: Any, names: tuple[str, ...]) -> Any:
    if not isinstance(ctx, dict):
        return None
    for name in names:
        value = ctx.get(name)
        if value not in (None, "", [], {}):
            return value
    return None


def scene_from_runtime(ctx: Any) -> dict[str, Any]:
    """Build the structured scene contract consumed by canonical scoring."""
    if not isinstance(ctx, dict):
        return {"texto": str(ctx or "")}

    scene: dict[str, Any] = {}
    for name in ("cena", "scene"):
        value = ctx.get(name)
        if isinstance(value, dict):
            scene.update(value)
            break

    mapping = (
        ("texto", ("texto", "text", "narracao", "narration", "segmento")),
        ("visual_query", ("visual_query", "busca", "query")),
        ("must_have", ("must_have", "must")),
        ("avoid", ("avoid", "avoid_terms")),
        ("location", ("location", "local", "geo")),
        ("visual_mode", ("visual_mode", "modo_visual")),
        ("topic", ("topic", "tema", "ASSUNTO")),
    )
    for target, names in mapping:
        value = _context_value(ctx, names)
        if value is not None:
            scene[target] = value
    return scene


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _candidate_provider(candidate: Any) -> str:
    if isinstance(candidate, dict):
        value = (
            candidate.get("fonte")
            or candidate.get("provider")
            or candidate.get("source")
        )
        if value:
            return str(value).strip().lower()
    return str(vse.provider(candidate) or "unknown").strip().lower()


def _candidate_media_type(candidate: Any) -> str:
    if isinstance(candidate, dict):
        value = candidate.get("tipo") or candidate.get("media_type") or candidate.get("type")
        if value:
            return str(value).strip().lower()
    return str(vse.media_type(candidate) or "unknown").strip().lower()


def _candidate_key(candidate: Any) -> str:
    provider = _candidate_provider(candidate)
    if isinstance(candidate, dict):
        for key in ("id", "asset_id", "photo_id", "video_id", "source_url", "url", "path"):
            value = candidate.get(key)
            if value not in (None, ""):
                return f"{provider}:{str(value).strip()}"
    value = str(vse.candidate_key(candidate) or "").strip()
    return value or f"{provider}:{_candidate_media_type(candidate)}:unknown"


def _apply_verified_must(result: dict[str, Any], candidate: Any, scene: Any) -> dict[str, Any]:
    """Make real asset evidence authoritative for explicit MUST requirements."""
    check = verified_must(candidate, scene)
    if not check.get("explicit"):
        return result

    upgraded = dict(result)
    old_must = int(max(0, min(2, _number(upgraded.get("must", 0), 0.0))))
    new_must = int(check.get("tier", 0) or 0)
    old_effective = _number(upgraded.get("effective", 0.0), 0.0)

    upgraded["must_pre_verification"] = old_must
    upgraded["must"] = new_must
    upgraded["must_verified_hits"] = int(check.get("hits", 0) or 0)
    upgraded["must_verified_total"] = int(check.get("total", 0) or 0)
    upgraded["must_verified_coverage"] = check.get("coverage", 0.0)
    upgraded["must_verified_matched"] = list(check.get("matched", []))
    upgraded["must_verified_missing"] = list(check.get("missing", []))

    # Remove exactly the legacy MUST contribution and add the verified one.
    # Preserve hard-guard sentinel scores such as -10000.
    if old_effective > -9000.0:
        upgraded["effective_pre_must_verification"] = old_effective
        upgraded["effective"] = round(
            old_effective + (new_must - old_must) * _MUST_WEIGHT,
            3,
        )

    if check.get("missing"):
        reasons = list(upgraded.get("mismatch_reasons", []) or [])
        marker = "EXPLICIT_MUST_UNVERIFIED"
        if marker not in reasons:
            reasons.append(marker)
        upgraded["mismatch_reasons"] = reasons

    return upgraded


def _score(candidate: Any, scene: Any, state: dict[str, Any]) -> dict[str, Any]:
    try:
        result = vse.score_candidate(candidate, scene, state)
        if not isinstance(result, dict):
            result = {}
    except Exception as exc:
        result = {
            "hard_mismatch": False,
            "effective": vse.base_score(candidate),
            "must": vse.must_tier(candidate, scene),
            "error": f"{type(exc).__name__}: {exc}",
        }

    if "must" not in result:
        result["must"] = vse.must_tier(candidate, scene)
    if "effective" not in result:
        result["effective"] = vse.base_score(candidate)

    return _apply_verified_must(result, candidate, scene)


def rerank_pool_runtime(pool: Any, ctx: Any = None):
    if os.getenv("SAP_VISUAL_UNIFIED", "1") != "1":
        return pool
    if not isinstance(pool, list):
        try:
            pool = list(pool)
        except Exception:
            return pool
    if len(pool) <= 1:
        return pool

    scene = scene_from_runtime(ctx or {})
    state = _load_state(_sid(ctx))
    ranked = []
    for index, candidate in enumerate(pool):
        result = _score(candidate, scene, state)
        hard = bool(result.get("hard_mismatch", False))
        must = int(max(0, min(2, _number(result.get("must", 0), 0.0))))
        effective = _number(result.get("effective", 0.0), 0.0)
        ranked.append((hard, -must, -effective, index, candidate, result))

    if all(item[0] for item in ranked):
        print("VISUAL_UNIFIED=ALL_HARD_FAIL_OPEN")
        return pool

    ranked.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    result_pool = [item[4] for item in ranked]
    winner = ranked[0]
    winner_result = winner[5]

    print("VISUAL_UNIFIED_V5=ACTIVE")
    print(f"VISUAL_UNIFIED_POOL={len(pool)}")
    print(f"VISUAL_UNIFIED_WINNER={vse.provider(winner[4])}/{vse.media_type(winner[4])}")
    print(f"VISUAL_UNIFIED_MUST={winner_result.get('must', 0)}")
    if winner_result.get("must_verified_total") is not None:
        print(
            "VISUAL_UNIFIED_MUST_VERIFIED="
            f"{winner_result.get('must_verified_hits', 0)}/"
            f"{winner_result.get('must_verified_total', 0)}"
        )
    print(f"VISUAL_UNIFIED_EFFECTIVE={winner_result.get('effective', 0)}")
    print(f"VISUAL_UNIFIED_HARD={winner_result.get('hard_mismatch', False)}")

    reasons = winner_result.get("mismatch_reasons") or winner_result.get("safety_reasons") or []
    if reasons:
        print("VISUAL_UNIFIED_REASONS=" + ",".join(map(str, reasons)))
    return result_pool


def note_commit_runtime(candidate: Any, ctx: Any = None) -> None:
    sid = _sid(ctx)
    state = _load_state(sid)
    scene = scene_from_runtime(ctx or {})
    scored = _score(candidate, scene, state)

    values = {
        "providers": _candidate_provider(candidate),
        "groups": vse.source_group(candidate),
        "types": _candidate_media_type(candidate),
        "keys": _candidate_key(candidate),
    }

    scene_number = 0
    if isinstance(ctx, dict):
        for key in ("numero", "scene_number", "scene"):
            raw = ctx.get(key)
            if isinstance(raw, dict):
                raw = raw.get("scene")
            try:
                scene_number = int(raw)
            except (TypeError, ValueError):
                continue
            if scene_number > 0:
                break

    if scene_number > 0:
        selection = _load_selection(sid)
        candidate_dict = candidate if isinstance(candidate, dict) else {}
        description = (
            candidate_dict.get("descricao")
            or candidate_dict.get("description")
            or candidate_dict.get("title")
            or candidate_dict.get("name")
            or ""
        )
        query = _context_value(ctx, ("busca", "visual_query", "query")) if isinstance(ctx, dict) else ""
        segment = _context_value(ctx, ("segmento", "texto", "segment")) if isinstance(ctx, dict) else ""
        record = {
            "scene": scene_number,
            "provider": candidate_dict.get("fonte") or _candidate_provider(candidate),
            "media_type": candidate_dict.get("tipo") or _candidate_media_type(candidate),
            "candidate_key": _candidate_key(candidate),
            "description": str(description or ""),
            "query": str(query or scene.get("visual_query") or ""),
            "segment": str(segment or scene.get("texto") or ""),
            "base_score": _safe_scalar(vse.base_score(candidate)),
            "effective_score": _safe_scalar(scored.get("effective")),
            "hard_mismatch": bool(scored.get("hard_mismatch", False)),
            "must_tier": _safe_scalar(scored.get("must")),
            "must_verified_hits": _safe_scalar(scored.get("must_verified_hits")),
            "must_verified_total": _safe_scalar(scored.get("must_verified_total")),
            "must_verified_coverage": _safe_scalar(scored.get("must_verified_coverage")),
            "safety_reasons": list(scored.get("safety_reasons", []) or scored.get("mismatch_reasons", []) or []),
            "evidence_class": _safe_scalar(candidate_dict.get("evidence_class")),
            "risk": _safe_scalar(candidate_dict.get("_vi6_risk") or candidate_dict.get("risk")),
            "vi6_class": _safe_scalar(candidate_dict.get("_vi6_class")),
            "raw_semantic_score": _safe_scalar(
                candidate_dict.get("_semantic_score")
                if candidate_dict.get("_semantic_score") is not None
                else candidate_dict.get("semantic_score")
            ),
        }
        selection["scenes"][str(scene_number)] = record
        _save_selection(sid, selection)

    for bucket, value in values.items():
        if value in (None, "", "unknown"):
            continue
        state[bucket].append(value)
        state[bucket] = state[bucket][-24:]
    _save_state(sid, state)
    if scene_number > 0:
        print(f"VISUAL_UNIFIED_COMMIT=PASS scene={scene_number} ledger=CANONICAL")
    else:
        print("VISUAL_UNIFIED_COMMIT=PASS ledger=SKIPPED_NO_SCENE")


def reset_state(sid: str) -> None:
    try:
        _state_path(sid).unlink()
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    print("VISUAL_ENGINE_UNIFIED_V5=PASS")
    print(f"VERSION={VERSION}")
