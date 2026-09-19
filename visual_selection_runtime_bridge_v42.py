#!/usr/bin/env python3

import os
from collections import Counter

from visual_selection_engine_v4 import (
    score_candidate,
    must_tier,
    provider,
    source_group,
    media_type,
    candidate_key,
)

try:
    from visual_quality_policy_v1 import (
        evaluate as evaluate_visual_quality,
        signature_for_candidate,
    )
except Exception:
    evaluate_visual_quality = None
    signature_for_candidate = None


_HISTORY = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
    "semantic_signatures": [],
}


def _scene_from_context(ctx):
    if not isinstance(ctx, dict):
        ctx = {}

    def first(*names):
        for name in names:
            value = ctx.get(name)
            if value not in (None, "", [], {}):
                return value
        return ""

    return {
        "texto": first("segmento", "segment", "texto", "scene_text", "texto_cena"),
        "visual_query": first("busca", "visual_query", "query"),
        "must_have": first("must_have", "must") or [],
        "avoid": first("avoid", "avoid_terms") or [],
        "location": first("location", "localizacao", "geo", "local"),
        "topic": first("topic", "tema", "ASSUNTO"),
    }


def _effective(result):
    if not isinstance(result, dict):
        return 0.0
    for key in ("effective", "effective_score", "final_score", "score"):
        value = result.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return 0.0


def _visual_quality(candidate, scene):
    if os.environ.get("SAP_VISUAL_QUALITY_V1", "1") == "0":
        return {
            "adjustment": 0.0,
            "reasons": ["QUALITY_POLICY_DISABLED"],
            "signature": "",
        }

    if not callable(evaluate_visual_quality):
        return {
            "adjustment": 0.0,
            "reasons": ["QUALITY_POLICY_IMPORT_FAIL_OPEN"],
            "signature": "",
        }

    try:
        result = evaluate_visual_quality(candidate, scene, _HISTORY)
        if not isinstance(result, dict):
            raise TypeError("quality policy returned non-dict")
        value = float(result.get("adjustment", 0.0) or 0.0)
        result["adjustment"] = value
        return result
    except Exception as exc:
        return {
            "adjustment": 0.0,
            "reasons": [f"QUALITY_POLICY_FAIL_OPEN:{type(exc).__name__}"],
            "signature": "",
        }


def rerank_pool(pool, context=None):
    if os.environ.get("SAP_VSE42_RUNTIME", "1") == "0":
        return list(pool or []), {
            "enabled": False,
            "summary": "kill-switch",
        }

    pool = list(pool or [])
    if len(pool) <= 1:
        return pool, {
            "enabled": True,
            "summary": f"pool={len(pool)}",
        }

    scene = _scene_from_context(context or {})
    state = {
        key: list(value)
        for key, value in _HISTORY.items()
    }

    provider_counts = Counter(_HISTORY["providers"])
    group_counts = Counter(_HISTORY["groups"])
    key_counts = Counter(_HISTORY["keys"])
    ranked = []

    for index, candidate in enumerate(pool):
        try:
            result = score_candidate(candidate, scene, state)
        except Exception as exc:
            result = {
                "hard_mismatch": False,
                "effective": -100000.0,
                "bridge_error": f"{type(exc).__name__}: {exc}",
            }

        hard = bool(result.get("hard_mismatch", False))

        try:
            tier = int(must_tier(candidate, scene))
        except Exception:
            tier = 0

        try:
            prov = provider(candidate)
        except Exception:
            prov = "unknown"

        try:
            group = source_group(candidate)
        except Exception:
            group = "unknown"

        try:
            typ = media_type(candidate)
        except Exception:
            typ = "unknown"

        try:
            key = candidate_key(candidate)
        except Exception:
            key = f"{prov}:{typ}:{index}"

        effective = _effective(result)

        # Diversity adjustments.
        adjusted = effective

        if _HISTORY["providers"] and prov == _HISTORY["providers"][-1]:
            adjusted -= 12.0

        adjusted -= provider_counts[prov] * 3.0

        if group and group != "unknown":
            adjusted -= group_counts[group] * 4.0

        if key_counts[key]:
            adjusted -= 160.0 * key_counts[key]

        # Evita longas sequências visualmente repetitivas e ajuda o pipeline
        # a recuperar movimento quando já existem várias fotos seguidas.
        recent_types = _HISTORY["types"][-4:]
        if len(recent_types) >= 3 and all(x == "photo" for x in recent_types[-3:]):
            if typ == "video":
                adjusted += 28.0
            elif typ == "photo":
                adjusted -= 14.0
        elif (
            len(recent_types) >= 3
            and len(set(recent_types[-3:])) == 1
            and typ == recent_types[-1]
        ):
            adjusted -= 10.0

        # Visual Quality Policy V1.
        # Esta política tardia usa somente evidência descritiva do asset e não
        # trata a query de busca como prova de que a mídia contém o alvo.
        quality = _visual_quality(candidate, scene)
        adjusted += float(quality.get("adjustment", 0.0) or 0.0)

        ranked.append(
            {
                "candidate": candidate,
                "original_index": index,
                "hard": hard,
                "tier": tier,
                "effective": effective,
                "adjusted": adjusted,
                "provider": prov,
                "group": group,
                "type": typ,
                "key": key,
                "details": result,
                "visual_quality": quality,
            }
        )

    ranked.sort(
        key=lambda item: (
            item["hard"] is False,
            item["tier"],
            item["adjusted"],
            -item["original_index"],
        ),
        reverse=True,
    )

    # Hard anti-repeat: an already-used exact asset must not win again when
    # an unseen safe candidate exists at the same MUST tier.
    if ranked and key_counts[ranked[0]["key"]]:
        top_tier = ranked[0]["tier"]
        replacement_index = next(
            (
                idx for idx, item in enumerate(ranked[1:], 1)
                if not item["hard"]
                and item["tier"] >= top_tier
                and not key_counts[item["key"]]
            ),
            None,
        )
        if replacement_index is not None:
            ranked.insert(0, ranked.pop(replacement_index))

    # Motion recovery: after three photos, prefer a safe video at the same
    # MUST tier unless it is clearly weaker semantically.
    recent_types = _HISTORY["types"][-3:]
    if ranked and len(recent_types) == 3 and all(x == "photo" for x in recent_types):
        top = ranked[0]
        video_index = next(
            (
                idx for idx, item in enumerate(ranked)
                if item["type"] == "video"
                and not item["hard"]
                and item["tier"] >= top["tier"]
                and item["adjusted"] >= top["adjusted"] - 45.0
            ),
            None,
        )
        if video_index not in (None, 0):
            ranked.insert(0, ranked.pop(video_index))

    output = [item["candidate"] for item in ranked]
    top = ranked[0]
    max_tier = max(item["tier"] for item in ranked)
    provider_pool = Counter(item["provider"] for item in ranked)

    top_quality = top.get("visual_quality", {}) or {}
    top_quality_adjust = float(top_quality.get("adjustment", 0.0) or 0.0)
    top_quality_reasons = list(top_quality.get("reasons", []) or [])
    weak_top = any(
        reason in {
            "WEAK_ASSET_METADATA",
            "UNANCHORED_ASSET",
            "GENERIC_LIFESTYLE",
            "GENERIC_SCENERY_FOR_ACTION",
            "NEAR_DUPLICATE_STRONG",
        }
        for reason in top_quality_reasons
    )

    meta = {
        "enabled": True,
        "pool": len(ranked),
        "max_tier": max_tier,
        "rescue_needed": max_tier < 2 or weak_top,
        "top_provider": top["provider"],
        "top_type": top["type"],
        "top_tier": top["tier"],
        "top_hard_mismatch": top["hard"],
        "top_visual_quality_adjustment": round(top_quality_adjust, 3),
        "top_visual_quality_reasons": top_quality_reasons,
        "provider_pool": dict(provider_pool),
        "summary": (
            f"pool={len(ranked)} "
            f"top={top['provider']}/{top['type']} "
            f"tier={top['tier']} "
            f"hard={top['hard']} "
            f"vq={top_quality_adjust:+.1f} "
            f"vq_reasons={','.join(top_quality_reasons[:4]) or 'NONE'} "
            f"providers={dict(provider_pool)}"
        ),
    }

    return output, meta


def note_selected(candidate):
    try:
        prov = provider(candidate)
    except Exception:
        prov = "unknown"

    try:
        group = source_group(candidate)
    except Exception:
        group = "unknown"

    try:
        typ = media_type(candidate)
    except Exception:
        typ = "unknown"

    try:
        key = candidate_key(candidate)
    except Exception:
        key = f"{prov}:{typ}:{len(_HISTORY['keys'])}"

    signature = ""
    if callable(signature_for_candidate):
        try:
            signature = str(signature_for_candidate(candidate) or "")
        except Exception:
            signature = ""

    _HISTORY["providers"].append(prov)
    _HISTORY["groups"].append(group)
    _HISTORY["types"].append(typ)
    _HISTORY["keys"].append(key)
    if signature:
        _HISTORY["semantic_signatures"].append(signature)

    for name in _HISTORY:
        if len(_HISTORY[name]) > 30:
            _HISTORY[name] = _HISTORY[name][-30:]


def history():
    return {
        key: list(value)
        for key, value in _HISTORY.items()
    }
