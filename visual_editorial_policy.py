#!/usr/bin/env python3
"""Deterministic editorial motion policy for ShortAutoPro.

Termux-safe rules for a less template-like documentary edit:
- narrative-role-aware visual energy;
- calmer evidence, maps, documents and human portraits;
- restrained hook/reveal emphasis;
- non-mechanical directional grammar;
- gentler zoom amplitudes;
- deliberate ending hold.
"""

from __future__ import annotations

CALM_MODES = {"document", "evidence", "map_context"}
DETAIL_SHOTS = {"detail", "close", "closeup", "close_up", "macro"}
WIDE_SHOTS = {"wide", "wide_shot", "establishing", "long", "long_shot", "aerial", "landscape"}
HUMAN_MODES = {"human_context", "portrait", "person"}
CALM_ROLES = {
    "context",
    "background",
    "evidence",
    "explanation",
    "aftermath",
    "reflection",
    "conclusion",
    "payoff",
}
HIGH_ROLES = {"hook", "cold_open", "escalation", "reveal", "turn", "turning_point", "climax"}


def _norm(value):
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def editorial_energy(
    scene_number,
    total,
    visual_mode,
    shot_type,
    media_type,
    narrative_role="",
):
    if _norm(media_type) == "video":
        return 0

    mode = _norm(visual_mode)
    shot = _norm(shot_type)
    role = _norm(narrative_role)

    if scene_number == 1:
        return 5
    if scene_number == total:
        return 2

    progress = scene_number / max(total, 1)
    energy = 2 if progress <= 0.25 else 3 if progress <= 0.55 else 4 if progress <= 0.78 else 3

    if role in HIGH_ROLES:
        energy = max(energy, 4)
    if role in CALM_ROLES:
        energy = min(energy, 3)

    if mode in CALM_MODES:
        energy = min(energy, 2 if shot in DETAIL_SHOTS else 3)
    elif mode in HUMAN_MODES:
        energy = min(energy, 3)

    if shot in DETAIL_SHOTS and mode not in CALM_MODES:
        energy = min(energy + 1, 4)
    elif shot in WIDE_SHOTS:
        energy = max(2, energy - 1)

    return max(1, min(5, energy))


def editorial_pan(
    scene_number,
    total,
    visual_mode,
    shot_type,
    current_pan,
    previous_pan=None,
    narrative_role="",
):
    mode = _norm(visual_mode)
    shot = _norm(shot_type)
    role = _norm(narrative_role)
    pan = _norm(current_pan)
    prev = _norm(previous_pan)

    if (
        mode in CALM_MODES
        or mode in HUMAN_MODES
        or shot in DETAIL_SHOTS
        or role in {"evidence", "reflection", "conclusion", "payoff"}
        or scene_number == total
    ):
        return "center"

    # Avoid robotic left/right ping-pong: every third photo gets a centered hold.
    if scene_number % 3 == 0 and shot not in WIDE_SHOTS:
        return "center"

    if shot in WIDE_SHOTS:
        preferred = "right" if scene_number % 2 else "left"
    else:
        preferred = "left" if scene_number % 2 else "right"

    if pan in {"left", "right"}:
        preferred = pan
    if preferred == prev:
        preferred = "right" if preferred == "left" else "left"
    return preferred


def zoom_amplitude(energy, visual_mode, shot_type, narrative_role=""):
    mode = _norm(visual_mode)
    shot = _norm(shot_type)
    role = _norm(narrative_role)

    if mode in CALM_MODES or role in {"evidence", "reflection", "conclusion", "payoff"}:
        table = {1: 0.010, 2: 0.018, 3: 0.027, 4: 0.036, 5: 0.044}
    elif mode in HUMAN_MODES:
        table = {1: 0.010, 2: 0.018, 3: 0.028, 4: 0.038, 5: 0.048}
    elif shot in DETAIL_SHOTS:
        table = {1: 0.014, 2: 0.022, 3: 0.032, 4: 0.043, 5: 0.054}
    elif shot in WIDE_SHOTS:
        table = {1: 0.014, 2: 0.024, 3: 0.034, 4: 0.046, 5: 0.060}
    else:
        table = {1: 0.016, 2: 0.027, 3: 0.040, 4: 0.054, 5: 0.070}
    return table.get(int(energy), 0.04)


def rhythm_label(
    scene_number,
    total,
    visual_mode,
    shot_type,
    media_type,
    energy,
    narrative_role="",
):
    mode = _norm(visual_mode)
    shot = _norm(shot_type)
    role = _norm(narrative_role)

    if _norm(media_type) == "video":
        return "native_video"
    if scene_number == 1:
        return "hook_editorial"
    if scene_number == total:
        return "closing_hold"
    if role in {"reveal", "turn", "turning_point", "climax"}:
        return "reveal_emphasis"
    if mode in CALM_MODES or role in {"evidence", "reflection", "payoff"}:
        return "documentary_hold"
    if mode in HUMAN_MODES:
        return "human_hold"
    if shot in DETAIL_SHOTS:
        return "detail_emphasis"
    if int(energy) >= 4:
        return "editorial_dynamic"
    return "editorial_balanced"


def apply_editorial_policy(scene, scene_number, total, previous_pan=None):
    new = dict(scene)
    mode = _norm(new.get("visual_mode", "environment"))
    shot = _norm(new.get("shot_type", "medium"))
    media = _norm(new.get("media_type", "photo"))
    role = _norm(new.get("narrative_role", ""))

    energy = editorial_energy(scene_number, total, mode, shot, media, role)
    pan = editorial_pan(
        scene_number,
        total,
        mode,
        shot,
        new.get("pan", "center"),
        previous_pan,
        role,
    )

    new["energy"] = energy
    new["visual_energy"] = 0 if media == "video" else energy
    new["pan"] = "none" if media == "video" else pan
    new["rhythm_profile"] = rhythm_label(
        scene_number,
        total,
        mode,
        shot,
        media,
        energy,
        role,
    )
    new["editorial_policy"] = "humanized_v2"
    new["editorial_amplitude"] = (
        0.0 if media == "video" else zoom_amplitude(energy, mode, shot, role)
    )
    return new
