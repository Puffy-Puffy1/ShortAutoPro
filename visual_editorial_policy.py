#!/usr/bin/env python3
"""Deterministic editorial motion policy for ShortAutoPro.

Keeps Termux rendering simple while making photo scenes feel less template-like:
- shot-aware motion strength;
- calmer evidence/document treatment;
- stronger hook/reveal beats;
- alternating directional grammar;
- restrained ending hold.
"""

from __future__ import annotations

CALM_MODES = {"document", "evidence", "map_context"}
DETAIL_SHOTS = {"detail", "close", "closeup", "close_up", "macro"}
WIDE_SHOTS = {"wide", "establishing", "long", "long_shot"}
HUMAN_MODES = {"human_context", "portrait", "person"}


def _norm(value):
    return str(value or "").strip().lower().replace("-", "_")


def editorial_energy(scene_number, total, visual_mode, shot_type, media_type):
    if _norm(media_type) == "video":
        return 0

    mode = _norm(visual_mode)
    shot = _norm(shot_type)

    if scene_number == 1:
        return 5
    if scene_number == total:
        return 2

    progress = scene_number / max(total, 1)
    energy = 2 if progress <= 0.25 else 3 if progress <= 0.55 else 4 if progress <= 0.78 else 3

    if mode in CALM_MODES:
        energy = min(energy, 2 if shot in DETAIL_SHOTS else 3)
    elif mode in HUMAN_MODES:
        energy = min(energy, 3)

    if shot in DETAIL_SHOTS:
        energy = min(energy + 1, 4)
    elif shot in WIDE_SHOTS:
        energy = max(2, energy - 1)

    return max(1, min(5, energy))


def editorial_pan(scene_number, total, visual_mode, shot_type, current_pan, previous_pan=None):
    mode = _norm(visual_mode)
    shot = _norm(shot_type)
    pan = _norm(current_pan)
    prev = _norm(previous_pan)

    if mode in CALM_MODES or shot in DETAIL_SHOTS or scene_number == total:
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


def zoom_amplitude(energy, visual_mode, shot_type):
    mode = _norm(visual_mode)
    shot = _norm(shot_type)

    if mode in CALM_MODES:
        table = {1: 0.012, 2: 0.020, 3: 0.030, 4: 0.040, 5: 0.050}
    elif shot in DETAIL_SHOTS:
        table = {1: 0.018, 2: 0.026, 3: 0.036, 4: 0.048, 5: 0.060}
    elif shot in WIDE_SHOTS:
        table = {1: 0.018, 2: 0.030, 3: 0.042, 4: 0.055, 5: 0.070}
    else:
        table = {1: 0.020, 2: 0.034, 3: 0.050, 4: 0.066, 5: 0.084}
    return table.get(int(energy), 0.05)


def rhythm_label(scene_number, total, visual_mode, shot_type, media_type, energy):
    if _norm(media_type) == "video":
        return "native_video"
    if scene_number == 1:
        return "hook_editorial"
    if scene_number == total:
        return "closing_hold"
    if _norm(visual_mode) in CALM_MODES:
        return "documentary_hold"
    if _norm(shot_type) in DETAIL_SHOTS:
        return "detail_emphasis"
    if int(energy) >= 4:
        return "editorial_dynamic"
    return "editorial_balanced"


def apply_editorial_policy(scene, scene_number, total, previous_pan=None):
    new = dict(scene)
    mode = _norm(new.get("visual_mode", "environment"))
    shot = _norm(new.get("shot_type", "medium"))
    media = _norm(new.get("media_type", "photo"))

    energy = editorial_energy(scene_number, total, mode, shot, media)
    pan = editorial_pan(
        scene_number,
        total,
        mode,
        shot,
        new.get("pan", "center"),
        previous_pan,
    )

    new["energy"] = energy
    new["visual_energy"] = 0 if media == "video" else energy
    new["pan"] = "none" if media == "video" else pan
    new["rhythm_profile"] = rhythm_label(scene_number, total, mode, shot, media, energy)
    new["editorial_policy"] = "humanized_v1"
    new["editorial_amplitude"] = 0.0 if media == "video" else zoom_amplitude(energy, mode, shot)
    return new
