#!/usr/bin/env python3
"""Shot grammar helpers for a less repetitive documentary edit.

This module is intentionally deterministic and dependency-free so the same
rules run on Termux and in CI. It does not invent scene facts: it only
normalizes framing labels returned by the visual director and supplies a
conservative fallback when that label is unusable.
"""

from __future__ import annotations


CANONICAL_SHOTS = {
    "wide",
    "medium",
    "closeup",
    "detail",
    "portrait",
    "overhead",
}

ALIASES = {
    "wide": "wide",
    "wide_shot": "wide",
    "establishing": "wide",
    "establishing_shot": "wide",
    "long": "wide",
    "long_shot": "wide",
    "aerial": "wide",
    "drone": "wide",
    "landscape": "wide",
    "medium": "medium",
    "medium_shot": "medium",
    "interior": "medium",
    "exterior": "medium",
    "close": "closeup",
    "close_up": "closeup",
    "closeup": "closeup",
    "macro": "detail",
    "detail": "detail",
    "document": "detail",
    "evidence": "detail",
    "portrait": "portrait",
    "face": "portrait",
    "overhead": "overhead",
    "top_down": "overhead",
}

CALM_MODES = {"document", "evidence", "map_context", "archive", "archival"}
HUMAN_MODES = {"human_context", "portrait", "person", "people"}
ENVIRONMENT_MODES = {"environment", "location", "architecture", "transport"}


def _norm(value):
    return (
        str(value or "")
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def normalize_shot_type(value):
    """Return one canonical framing label or an empty string."""
    key = _norm(value)
    if key in CANONICAL_SHOTS:
        return key
    return ALIASES.get(key, "")


def fallback_shot(scene_number, visual_mode="", previous_shot=""):
    """Choose a conservative framing fallback without changing scene facts."""
    mode = _norm(visual_mode)
    previous = normalize_shot_type(previous_shot)

    if mode in CALM_MODES:
        preferred = "detail" if scene_number % 2 == 0 else "medium"
    elif mode in HUMAN_MODES:
        preferred = "portrait"
    elif mode in ENVIRONMENT_MODES:
        preferred = "wide" if scene_number % 2 else "medium"
    else:
        preferred = "medium" if scene_number % 2 else "closeup"

    if preferred == previous and preferred != "portrait":
        if preferred == "wide":
            return "medium"
        if preferred in {"medium", "closeup", "detail", "overhead"}:
            return "wide"
    return preferred


def rebalance_repeated_shot(shot, scene_number, visual_mode="", previous_shot=""):
    """Reduce mechanical consecutive framing while preserving documentary intent."""
    current = normalize_shot_type(shot)
    previous = normalize_shot_type(previous_shot)
    mode = _norm(visual_mode)
    if not current or current != previous:
        return current

    # Portraits and evidence/details often need visual continuity more than
    # artificial variety, so do not force a framing change there.
    if current == "portrait" or mode in HUMAN_MODES:
        return current
    if mode in CALM_MODES and current in {"detail", "overhead"}:
        return current

    if current == "wide":
        return "medium"
    if current == "medium":
        return "wide" if mode in ENVIRONMENT_MODES else "closeup"
    if current == "closeup":
        return "medium"
    if current == "detail":
        return "medium"
    if current == "overhead":
        return "detail"
    return current


def resolve_shot_type(candidate, original, scene_number, visual_mode="", previous_shot=""):
    """Resolve framing and gently de-template consecutive neutral shots."""
    shot = normalize_shot_type(candidate)
    if not shot:
        shot = normalize_shot_type(original)
    if not shot:
        shot = fallback_shot(scene_number, visual_mode, previous_shot)
    return rebalance_repeated_shot(shot, scene_number, visual_mode, previous_shot)
