#!/usr/bin/env python3
"""Deterministic editorial motion policy for ShortAutoPro.

Termux-safe rules for a less template-like documentary edit:
- narrative-role-aware visual energy;
- calm faces, evidence, documents and close details;
- pans reserved mainly for establishing/wide frames;
- restrained hook/reveal emphasis instead of aggressive Ken Burns presets;
- deliberate breathing beats and stable endings;
- small shot-aware zoom amplitudes suitable for vertical documentary edits.
"""

from __future__ import annotations

CALM_MODES = {"document", "evidence", "map_context", "archive", "archival"}
DETAIL_SHOTS = {"detail", "close", "closeup", "close_up", "macro"}
WIDE_SHOTS = {"wide", "wide_shot", "establishing", "long", "long_shot", "aerial", "landscape"}
HUMAN_MODES = {"human_context", "portrait", "person", "people"}
OBJECT_MODES = {"object", "architecture", "transport"}
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

    # A hook should feel intentional, not like an automatic zoom preset.
    if scene_number == 1:
        if mode in CALM_MODES | HUMAN_MODES or shot in DETAIL_SHOTS:
            return 3
        return 4
    if scene_number == total:
        return 1 if role in CENTER_ROLES or mode in CALM_MODES | HUMAN_MODES else 2

    progress = scene_number / max(total, 1)
    energy = 2 if progress <= 0.25 else 3 if progress <= 0.58 else 4 if progress <= 0.78 else 3

    if role in HIGH_ROLES:
        energy = max(energy, 4)
    if role in CALM_ROLES:
        energy = min(energy, 3)

    if mode in CALM_MODES:
        energy = min(energy, 2)
    elif mode in HUMAN_MODES:
        energy = min(energy, 2 if shot in DETAIL_SHOTS else 3)
    elif mode in OBJECT_MODES and shot in DETAIL_SHOTS:
        energy = min(energy, 3)

    if shot in DETAIL_SHOTS and mode not in CALM_MODES | HUMAN_MODES:
        energy = min(energy + 1, 4)
    elif shot in WIDE_SHOTS:
        # Establishing images need time to read; motion can exist without being fast.
        energy = max(2, energy - 1)

    breathing = {4, max(5, total - 3)}
    if total >= 10 and scene_number in breathing and role not in HIGH_ROLES:
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

    # Professional documentary grammar: faces, documents, evidence and close
    # details are read, not scanned. Keep them centered and let a tiny push do
    # the visual work.
    if (
        mode in CALM_MODES
        or mode in HUMAN_MODES
        or shot in DETAIL_SHOTS
        or role in CENTER_ROLES
        or scene_number == total
    ):
        return "center"

    # Medium frames are also mostly held. This is the main difference from a
    # mechanical Ken Burns template that slides almost every still image.
    if shot not in WIDE_SHOTS:
        if role not in HIGH_ROLES:
            return "center"
        # High narrative beats may use one restrained directional reframe on
        # architecture/transport/object scenes, but not on generic context.
        if mode not in OBJECT_MODES:
            return "center"

    # Wide establishing frames are the natural place for directional movement.
    preferred = "right" if scene_number % 2 else "left"
    if pan in {"left", "right"}:
        preferred = pan
    if preferred == prev:
        preferred = "right" if preferred == "left" else "left"
    return preferred


def zoom_amplitude(energy, visual_mode, shot_type, narrative_role=""):
    mode = _norm(visual_mode)
    shot = _norm(shot_type)
    role = _norm(narrative_role)
    energy = int(energy)

    # Humanized v5 uses smaller, more photographic reframes. The renderer runs
    # at 30 fps, so even 1–3% change is clearly visible over a multi-second shot.
    if mode in CALM_MODES or role in CENTER_ROLES:
        table = {1: 0.003, 2: 0.006, 3: 0.011, 4: 0.016}
    elif mode in HUMAN_MODES:
        table = {1: 0.003, 2: 0.007, 3: 0.012, 4: 0.018}
    elif shot in DETAIL_SHOTS:
        table = {1: 0.004, 2: 0.008, 3: 0.014, 4: 0.021}
    elif shot in WIDE_SHOTS:
        table = {1: 0.006, 2: 0.011, 3: 0.018, 4: 0.027}
    elif mode in OBJECT_MODES:
        table = {1: 0.004, 2: 0.009, 3: 0.015, 4: 0.023}
    else:
        table = {1: 0.005, 2: 0.010, 3: 0.017, 4: 0.026}
    return table.get(energy, 0.014)


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
        return "portrait_hold"
    if shot in DETAIL_SHOTS:
        return "detail_emphasis"
    if shot in WIDE_SHOTS and int(energy) >= 3:
        return "establishing_drift"
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
    new["editorial_policy"] = "humanized_v5"
    new["editorial_amplitude"] = (
        0.0 if media == "video" else zoom_amplitude(energy, mode, shot, role)
    )
    return new
