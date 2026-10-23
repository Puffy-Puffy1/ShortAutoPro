#!/usr/bin/env python3
"""Fail-closed image-pixel verification for Media Engine V2.

Provider metadata is used for discovery only. This module checks the downloaded,
validated image bytes against explicit MUST/AVOID anchors and never treats search
queries, filenames, or catalog descriptions as visual evidence.
"""
from __future__ import annotations

import json
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


def _blocked(reason: str, mime_type: str = "") -> dict[str, Any]:
    return {
        "status": "BLOCK",
        "method": "gemini_image_pixels",
        "reason": reason,
        "mime_type": mime_type,
    }


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
    for anchor in expected:
        row = indexed[anchor.casefold()]
        visible = row.get("visible")
        confidence = row.get("confidence")
        evidence = str(row.get("evidence") or "").strip()
        if type(visible) is not bool:
            return None, f"{field}_visibility_uncertain"
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            return None, f"{field}_confidence_invalid"
        if float(confidence) < MIN_CONFIDENCE:
            return None, f"{field}_confidence_below_threshold"
        if visible is not expected_visible:
            return None, f"{field}_visibility_failed"
        if not evidence:
            return None, f"{field}_evidence_missing"
        checked.append({
            "anchor": anchor,
            "visible": visible,
            "confidence": round(float(confidence), 3),
            "evidence": evidence[:320],
        })
    return checked, ""


def verify_image_requirements(
    path: str | Path,
    must: list[str],
    avoid: list[str],
) -> dict[str, Any]:
    """Verify explicit visual requirements from pixels; uncertain responses block."""
    requirements = [str(item).strip() for item in must if str(item).strip()]
    forbidden = [str(item).strip() for item in avoid if str(item).strip()]
    if not requirements:
        return _blocked("must_requirements_empty")

    image = _read_image(Path(path))
    if image is None:
        return _blocked("image_missing_invalid_or_too_large")
    image_data, mime_type = image

    # Do not pass topic, search query, filename, or provider metadata. The model
    # receives only the actual image and the exact visible-object constraints.
    prompt = (
        "You are a strict visual evidence checker for a video production pipeline. "
        "Judge only pixels in the attached image. Do not infer from the topic, "
        "filename, search query, provider, historical context, or metadata. "
        "For every MUST anchor, visible=true only if the requested object or scene "
        "element is clearly visible. For every AVOID anchor, visible=true means "
        "the forbidden element appears anywhere in the image. Return each requested "
        "anchor exactly once, without adding or renaming anchors. If uncertain, use "
        "confidence below 0.90. Evidence must describe an observable visual cue; "
        "for an absent AVOID element, briefly state what is not visible. Return only "
        "valid JSON with this exact shape: "
        '{"must":[{"anchor":"...","visible":true,"confidence":0.95,"evidence":"..."}],'
        '"avoid":[{"anchor":"...","visible":false,"confidence":0.95,"evidence":"..."}]}. '
        "Requested constraints: "
        + json.dumps({"must": requirements, "avoid": forbidden}, ensure_ascii=False)
    )

    try:
        raw = generate_text(
            prompt,
            temperature=0.0,
            max_output_tokens=900,
            response_mime_type="application/json",
            component="Media Visual Verifier",
            image_data=image_data,
            image_mime_type=mime_type,
        )
    except Exception as exc:
        return _blocked(f"visual_model_unavailable:{type(exc).__name__}", mime_type)

    payload = _parse_payload(raw)
    if payload is None:
        return _blocked("visual_model_invalid_json", mime_type)

    must_rows, must_error = _validated_rows(payload, "must", requirements, True)
    if must_error:
        return _blocked(must_error, mime_type)
    avoid_rows, avoid_error = _validated_rows(payload, "avoid", forbidden, False)
    if avoid_error:
        return _blocked(avoid_error, mime_type)

    return {
        "status": "PASS",
        "method": "gemini_image_pixels",
        "mime_type": mime_type,
        "confidence_threshold": MIN_CONFIDENCE,
        "must": must_rows,
        "avoid": avoid_rows or [],
    }


__all__ = ["verify_image_requirements", "MAX_IMAGE_BYTES", "MIN_CONFIDENCE"]
