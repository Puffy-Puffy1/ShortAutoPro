#!/usr/bin/env python3
"""Deterministic editorial motion policy for ShortAutoPro.

Termux-safe rules for a less template-like documentary edit:
- narrative-role-aware visual energy;
- calmer evidence, maps, documents and human portraits;
- restrained hook/reveal emphasis;
- non-mechanical directional grammar with deliberate breathing beats;
- smaller, more editorial zoom amplitudes;
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
CENTER_ROLES = {"evidence", "reflection", "conclusion", "payoff", "aftermath"}


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

    # A professional hook should feel intentional, not like a template punch.
    if scene_number == 1:
        return 4
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

    # Two subtle breathing beats in a 10-14 scene short keep the arc from feeling
    # mechanically energetic all the way through. They never suppress a reveal.
    if total >= 10 and scene_number in {4, max(5, total - 3)} and role not in HIGH_ROLES:
        energy = min(energy, 2)

    return max(1, min(4, energy))


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
        or role in CENTER_ROLES
        or scene_number == total
    ):
        return "center"

    # Deliberate centered holds make the edit breathe and break predictable
    # left/right alternation. Avoid forcing them on wide establishing shots.
    if (scene_number % 3 == 0 or scene_number in {4, max(5, total - 3)}) and shot not in WIDE_SHOTS:
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

    # Humanized v3 intentionally stays below the previous 7% ceiling. Small
    # movements read more like editorial reframing and less like Ken Burns.
    if mode in CALM_MODES or role in CENTER_ROLES:
        table = {1: 0.008, 2: 0.014, 3: 0.021, 4: 0.029}
    elif mode in HUMAN_MODES:
        table = {1: 0.008, 2: 0.014, 3: 0.022, 4: 0.031}
    elif shot in DETAIL_SHOTS:
        table = {1: 0.010, 2: 0.017, 3: 0.026, 4: 0.036}
    elif shot in WIDE_SHOTS:
        table = {1: 0.011, 2: 0.019, 3: 0.029, 4: 0.041}
    else:
        table = {1: 0.012, 2: 0.021, 3: 0.033, 4: 0.048}
    return table.get(int(energy), 0.03)


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
    if mode in CALM_MODES or role in CENTER_ROLES:
        return "documentary_hold"
    if mode in HUMAN_MODES:
        return "human_hold"
    if shot in DETAIL_SHOTS:
        return "detail_emphasis"
    if int(energy) >= 4:
        return "editorial_dynamic"
    if int(energy) <= 2:
        return "editorial_breath"
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
    new["editorial_policy"] = "humanized_v3"
    new["editorial_amplitude"] = (
        0.0 if media == "video" else zoom_amplitude(energy, mode, shot, role)
    )
    return new
