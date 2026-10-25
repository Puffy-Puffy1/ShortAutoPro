#!/usr/bin/env python3
"""Fail-closed image-pixel verification for Media Engine V2.

Provider metadata is used for discovery only. This module checks the downloaded,
validated image bytes against explicit MUST/AVOID anchors and never treats search
queries, filenames, or catalog descriptions as visual evidence.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path
from typing import Any

from gemini_runtime import generate_text

MAX_IMAGE_BYTES = 6 * 1024 * 1024
MIN_CONFIDENCE = 0.90
IMAGE_SIGNATURES = {
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}


def _blocked(
    reason: str,
    mime_type: str = "",
    **details: Any,
) -> dict[str, Any]:
    result = {
        "status": "BLOCK",
        "method": "gemini_image_pixels",
        "reason": reason,
        "mime_type": mime_type,
    }
    result.update(details)
    return result


def _read_image(path: Path) -> tuple[bytes, str] | None:
    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size < 16 or size > MAX_IMAGE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None

    suffix = path.suffix.casefold()
    if suffix in IMAGE_SIGNATURES:
        mime_type, signature = IMAGE_SIGNATURES[suffix]
        return (data, mime_type) if data.startswith(signature) else None

    if suffix == ".webp" and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return data, "image/webp"
    return None


def _parse_payload(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(str(raw or "").strip())
    except (TypeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _validated_rows(
    payload: dict[str, Any],
    field: str,
    expected: list[str],
    expected_visible: bool,
) -> tuple[list[dict[str, Any]] | None, str]:
    rows = payload.get(field)
    if not isinstance(rows, list):
        return None, f"invalid_{field}_schema"

    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            return None, f"invalid_{field}_row"
        anchor = str(row.get("anchor") or "").strip()
        key = anchor.casefold()
        if not key or key in indexed:
            return None, f"duplicate_or_empty_{field}_anchor"
        indexed[key] = row

    expected_keys = {anchor.casefold() for anchor in expected}
    if set(indexed) != expected_keys:
        return None, f"{field}_anchors_mismatch"

    checked: list[dict[str, Any]] = []
    errors: list[str] = []
    for anchor in expected:
        row = indexed[anchor.casefold()]
        visible = row.get("visible")
        confidence = row.get("confidence")
        evidence = str(row.get("evidence") or "").strip()

        if type(visible) is not bool:
            return None, f"{field}_visibility_uncertain"
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            return None, f"{field}_confidence_invalid"

        confidence_value = float(confidence)
        checked.append({
            "anchor": anchor,
            "visible": visible,
            "confidence": round(confidence_value, 3),
            "evidence": evidence[:320],
        })

        # Collect policy failures rather than returning at the first mismatch.
        # The blocked report can then explain exactly which anchor failed.
        if confidence_value < MIN_CONFIDENCE:
            errors.append(f"{field}_confidence_below_threshold")
        if visible is not expected_visible:
            errors.append(f"{field}_visibility_failed")
        if not evidence:
            errors.append(f"{field}_evidence_missing")

    return checked, errors[0] if errors else ""


def _validated_scene_match(
    payload: dict[str, Any],
    expected_intent: str,
) -> tuple[dict[str, Any] | None, str]:
    """Validate the high-level scene composition separately from object MUSTs."""
    if not expected_intent:
        return None, ""

    row = payload.get("scene_match")
    if not isinstance(row, dict):
        return None, "invalid_scene_match_schema"

    matches = row.get("matches")
    confidence = row.get("confidence")
    evidence = str(row.get("evidence") or "").strip()
    if type(matches) is not bool:
        return None, "scene_intent_match_uncertain"
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        return None, "scene_intent_confidence_invalid"

    confidence_value = float(confidence)
    if not math.isfinite(confidence_value) or not 0.0 <= confidence_value <= 1.0:
        return None, "scene_intent_confidence_invalid"

    checked = {
        "intent": expected_intent[:320],
        "matches": matches,
        "confidence": round(confidence_value, 3),
        "evidence": evidence[:320],
    }
    if confidence_value < MIN_CONFIDENCE:
        return checked, "scene_intent_confidence_below_threshold"
    if not evidence:
        return checked, "scene_intent_evidence_missing"
    if not matches:
        return checked, "scene_intent_mismatch"
    return checked, ""



def verify_image_requirements(
    path: str | Path,
    must: list[str],
    avoid: list[str],
    *,
    scene_intent: str = "",
) -> dict[str, Any]:
    """Verify visible objects and high-level scene intent independently."""
    requirements = [str(item).strip() for item in must if str(item).strip()]
    forbidden = [str(item).strip() for item in avoid if str(item).strip()]
    intent = str(scene_intent or "").strip()
    if not requirements and not intent:
        return _blocked("must_requirements_empty")

    image = _read_image(Path(path))
    if image is None:
        return _blocked("image_missing_invalid_or_too_large")
    image_data, mime_type = image

    # The model receives only the actual image and grounded visual requirements.
    # Scene intent is a composition check, not a literal phrase that must appear
    # in the pixels or a separate list of every word in the query.
    schema = (
        '{"must":[{"anchor":"...","visible":true,"confidence":0.95,"evidence":"..."}],'
        '"avoid":[{"anchor":"...","visible":false,"confidence":0.95,"evidence":"..."}]'
    )
    if intent:
        schema += ',"scene_match":{"matches":true,"confidence":0.95,"evidence":"..." }'
    schema += "}"

    instructions = (
        "You are a strict visual evidence checker for a video production pipeline. "
        "Judge only pixels in the attached image. Do not infer from filenames, provider "
        "metadata, search results, or unstated historical knowledge. For each MUST "
        "anchor, visible=true only when that object is clearly visible. For each AVOID "
        "anchor, visible=true means the forbidden element appears anywhere. Return each "
        "requested anchor exactly once. Evidence must describe an observable visual cue. "
        "Use confidence below 0.90 when uncertain. "
    )
    if intent:
        instructions += (
            "Also compare the image's main visible subject, setting, and composition "
            "with the scene intent. This is a high-level visual match, not a literal text "
            "match. Country, named town/province, and exact decade are contextual hints that "
            "usually cannot be authenticated from pixels alone; do not mark a mismatch solely "
            "because that exact location or year cannot be proven visually. A snowy provincial "
            "street with old buildings is compatible with a winter-town scene when no visible "
            "detail contradicts it. Mark matches=false only for a clear conflict with the core "
            "subject or setting, such as underwater dolphins for an empty ocean horizon, a "
            "tropical beach for a snow-covered town, or a modern skyscraper skyline for a "
            "low-rise historic village. Explicit MUST and AVOID anchors remain separately "
            "strict. Cite observable visual evidence in scene_match. "
        )

    constraints = {"must": requirements, "avoid": forbidden}
    if intent:
        constraints["scene_intent"] = intent
    prompt = instructions + "Return only valid JSON with this exact shape: " + schema + ". "
    prompt += "Requested constraints: " + json.dumps(constraints, ensure_ascii=False)

    raw = None
    for attempt in range(3):
        try:
            raw = generate_text(
                prompt,
                temperature=0.0,
                max_output_tokens=1100,
                response_mime_type="application/json",
                component="Media Visual Verifier",
                image_data=image_data,
                image_mime_type=mime_type,
                attempts_per_model=1,
            )
            break
        except Exception as exc:
            # Retry only transient transport/service failures. Permanent errors
            # still fail closed, and no retry can turn a rejected image into PASS.
            transient = (
                type(exc).__name__ in {
                    "GeminiTemporaryUnavailable", "TimeoutError", "ConnectionError"
                }
                or any(code in str(exc) for code in ("429", "500", "502", "503", "504"))
            )
            if not transient or attempt == 2:
                return _blocked(
                    f"visual_model_unavailable:{type(exc).__name__}", mime_type
                )
            time.sleep(0.25 * (attempt + 1))

    payload = _parse_payload(raw)
    if payload is None:
        return _blocked("visual_model_invalid_json", mime_type)

    must_rows, must_error = _validated_rows(payload, "must", requirements, True)
    avoid_rows, avoid_error = _validated_rows(payload, "avoid", forbidden, False)
    scene_match, scene_error = _validated_scene_match(payload, intent)
    if must_error:
        return _blocked(
            must_error,
            mime_type,
            must=must_rows or [],
            avoid=avoid_rows or [],
            scene_match=scene_match,
        )
    if avoid_error:
        return _blocked(
            avoid_error,
            mime_type,
            must=must_rows or [],
            avoid=avoid_rows or [],
            scene_match=scene_match,
        )
    if scene_error:
        return _blocked(
            scene_error,
            mime_type,
            must=must_rows or [],
            avoid=avoid_rows or [],
            scene_match=scene_match,
        )

    result = {
        "status": "PASS",
        "method": "gemini_image_pixels",
        "mime_type": mime_type,
        "confidence_threshold": MIN_CONFIDENCE,
        "must": must_rows or [],
        "avoid": avoid_rows or [],
    }
    if scene_match is not None:
        result["scene_match"] = scene_match
    return result


__all__ = ["verify_image_requirements", "MAX_IMAGE_BYTES", "MIN_CONFIDENCE"]
