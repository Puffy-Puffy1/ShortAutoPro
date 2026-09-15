#!/usr/bin/env python3
"""Professional editing director for ShortAutoPro.

Builds a deterministic, Termux-safe edit plan on top of the already approved
scene/motion/rhythm plans. It never changes facts or selects new media; it only
controls pacing, transition restraint, motion curve and finish policy.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
PROFILE = os.getenv("SAP_CHANNEL_PROFILE", "default").strip() or "default"

SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
RHYTHM_PLAN = BASE / "roteiros" / f"rhythm_plan_{SHORT_ID}.json"
MOTION_PLAN = BASE / "roteiros" / f"motion_plan_{SHORT_ID}.json"
OUTPUT = BASE / "roteiros" / f"pro_edit_plan_{SHORT_ID}.json"


def scene_count() -> int:
    try:
        value = int(os.getenv("SHORT_QTD_CENAS", "12"))
    except (TypeError, ValueError):
        value = 12
    return max(6, min(20, value))


EXPECTED = scene_count()

PROFILE_PRESETS: dict[str, dict[str, Any]] = {
    "default": {
        "style": "premium_documentary",
        "contrast": 1.035,
        "saturation": 0.99,
        "brightness": -0.004,
        "sharpness": 0.12,
        "hook_scale": 1.025,
        "caption_pop": 106,
        "music_volume": 0.045,
    },
    "true_crime": {
        "style": "documentary_suspense",
        "contrast": 1.055,
        "saturation": 0.92,
        "brightness": -0.010,
        "sharpness": 0.14,
        "hook_scale": 1.030,
        "caption_pop": 106,
        "music_volume": 0.042,
    },
    "cinepulsar": {
        "style": "cinematic_entertainment",
        "contrast": 1.045,
        "saturation": 1.06,
        "brightness": 0.000,
        "sharpness": 0.14,
        "hook_scale": 1.040,
        "caption_pop": 108,
        "music_volume": 0.055,
    },
    "psicotoon": {
        "style": "retro_editorial",
        "contrast": 1.050,
        "saturation": 0.98,
        "brightness": -0.004,
        "sharpness": 0.10,
        "hook_scale": 1.035,
        "caption_pop": 107,
        "music_volume": 0.050,
    },
}

HIGH_ROLES = {"hook", "cold_open", "escalation", "turn", "turning_point", "climax"}
CALM_ROLES = {"context", "background", "evidence", "explanation", "reflection", "aftermath", "conclusion", "payoff"}
REVEAL_ROLES = {"reveal", "turn", "turning_point", "climax", "payoff"}

ROLE_PACING = {
    "hook": 0.82,
    "cold_open": 0.86,
    "escalation": 0.92,
    "turn": 0.96,
    "turning_point": 0.96,
    "climax": 0.96,
    "reveal": 1.08,
    "evidence": 1.10,
    "explanation": 1.06,
    "reflection": 1.10,
    "aftermath": 1.08,
    "conclusion": 1.06,
    "payoff": 1.08,
    "cta": 0.88,
}


def norm(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"arquivo ausente: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"JSON inválido em {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} precisa conter objeto JSON")
    return data


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def valid_scenes(data: dict[str, Any], label: str) -> list[dict[str, Any]]:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != EXPECTED:
        raise ValueError(f"{label} precisa ter {EXPECTED} cenas")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(scenes, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{label} cena {index} inválida")
        try:
            number = int(item.get("scene"))
        except (TypeError, ValueError):
            raise ValueError(f"{label} cena {index} sem número válido")
        if number != index:
            raise ValueError(f"{label} numeração inválida na cena {index}")
        result.append(item)
    return result


def safe_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        number = default
    if not math.isfinite(number):
        number = default
    return max(low, min(high, number))


def narrative_role(scene: dict[str, Any], index: int, total: int) -> str:
    role = norm(scene.get("narrative_role"))
    if role:
        return role
    if index == 1:
        return "hook"
    if index == total:
        return "conclusion"
    return "development"


def pace_for(role: str, energy: int, index: int, total: int) -> float:
    pace = ROLE_PACING.get(role, 1.0)
    if role == "development":
        progress = index / max(1, total)
        pace = 0.96 if progress < 0.35 else 1.0 if progress < 0.75 else 1.04
    if energy >= 4 and role not in CALM_ROLES:
        pace *= 0.96
    elif energy <= 2 and role not in HIGH_ROLES:
        pace *= 1.03
    return round(max(0.78, min(1.14, pace)), 3)


def transition_for(role: str, energy: int, index: int, total: int) -> tuple[str, float, str]:
    if index == total:
        return "none", 0.0, "closing_hold"
    if role in HIGH_ROLES or energy >= 4:
        return "fade", 0.045, "near_cut"
    if role in CALM_ROLES or energy <= 2:
        return "fade", 0.120, "soft_fade"
    return "fade", 0.075, "editorial_cut"


def load_base_plan() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    map_scenes = valid_scenes(read_json(SCENE_MAP), "scene_map")
    source = RHYTHM_PLAN if RHYTHM_PLAN.is_file() else MOTION_PLAN
    motion_scenes = valid_scenes(read_json(source), source.stem)
    return map_scenes, motion_scenes


def build_plan() -> dict[str, Any]:
    map_scenes, motion_scenes = load_base_plan()
    preset = dict(PROFILE_PRESETS.get(PROFILE, PROFILE_PRESETS["default"]))
    total = len(map_scenes)
    scenes: list[dict[str, Any]] = []

    for index, (scene_map, motion) in enumerate(zip(map_scenes, motion_scenes), start=1):
        role = narrative_role(scene_map, index, total)
        media_type = norm(motion.get("media_type")) or "photo"
        shot_type = norm(motion.get("shot_type")) or norm(scene_map.get("shot_type")) or "medium"
        visual_mode = norm(scene_map.get("visual_mode")) or norm(motion.get("visual_mode")) or "environment"
        try:
            energy = int(motion.get("energy", motion.get("visual_energy", 2)) or 2)
        except (TypeError, ValueError):
            energy = 2
        energy = max(0 if media_type == "video" else 1, min(4, energy))
        transition, transition_duration, cut_style = transition_for(role, energy, index, total)

        zoom_start = safe_float(motion.get("zoom_start", 1.0), 1.0, 1.0, 1.08)
        zoom_end = safe_float(motion.get("zoom_end", zoom_start), zoom_start, zoom_start, 1.10)
        if media_type == "video":
            zoom_start = zoom_end = 1.0
        else:
            amplitude = max(0.0, zoom_end - zoom_start)
            # Professional layer caps still motion to avoid template-like movement.
            amplitude_cap = 0.028 if role in HIGH_ROLES | REVEAL_ROLES else 0.022
            if visual_mode in {"document", "evidence", "map_context", "archive", "archival"}:
                amplitude_cap = min(amplitude_cap, 0.014)
            zoom_end = round(zoom_start + min(amplitude, amplitude_cap), 4)

        micro_punch = media_type == "photo" and (index == 1 or role in REVEAL_ROLES)
        scenes.append({
            "scene": index,
            "narrative_role": role,
            "visual_mode": visual_mode,
            "shot_type": shot_type,
            "media_type": media_type,
            "media": motion.get("media"),
            "energy": energy,
            "pace_multiplier": pace_for(role, energy, index, total),
            "transition": transition,
            "transition_duration": transition_duration,
            "cut_style": cut_style,
            "motion_profile": motion.get("motion_profile", "professional_hold"),
            "motion_curve": "native" if media_type == "video" else "smoothstep",
            "zoom_start": zoom_start,
            "zoom_end": zoom_end,
            "pan": norm(motion.get("pan")) if norm(motion.get("pan")) in {"left", "right", "center", "none"} else "center",
            "micro_punch": micro_punch,
            "micro_punch_strength": 0.010 if micro_punch else 0.0,
        })

    score, issues = audit_plan(scenes)
    return {
        "short_id": SHORT_ID,
        "version": "PRO_EDIT_1.0",
        "profile": PROFILE,
        "style": preset["style"],
        "expected_scenes": EXPECTED,
        "scene_count": len(scenes),
        "professional_score": score,
        "professional_target": 88.0,
        "status": "PASS" if score >= 88.0 else "REVIEW",
        "issues": issues,
        "finish": {
            "contrast": preset["contrast"],
            "saturation": preset["saturation"],
            "brightness": preset["brightness"],
            "sharpness": preset["sharpness"],
            "hook_scale": preset["hook_scale"],
            "caption_pop": preset["caption_pop"],
        },
        "audio": {
            "music_volume": preset["music_volume"],
            "target_lufs": safe_float(os.getenv("SAP_AUDIO_TARGET_LUFS", -14), -14, -20, -10),
            "true_peak_db": safe_float(os.getenv("SAP_AUDIO_TRUE_PEAK_DB", -1.5), -1.5, -6, -0.5),
            "curated_sfx_only": os.getenv("SAP_PRO_ALLOW_GENERATED_SFX", "0") != "1",
        },
        "scenes": scenes,
    }


def audit_plan(scenes: list[dict[str, Any]]) -> tuple[float, list[str]]:
    issues: list[str] = []
    penalty = 0.0
    if len(scenes) != EXPECTED:
        return 0.0, [f"scene_count={len(scenes)}/{EXPECTED}"]

    # Framing variety: tolerate portraits/evidence continuity, penalize neutral triples.
    for index in range(2, len(scenes)):
        triple = scenes[index - 2 : index + 1]
        shots = [x.get("shot_type") for x in triple]
        modes = [x.get("visual_mode") for x in triple]
        if len(set(shots)) == 1 and shots[0] not in {"portrait", "detail", "overhead"}:
            issues.append(f"repeated_shot_triplet_scene_{index + 1}")
            penalty += 3.0
        pans = [x.get("pan") for x in triple]
        if pans[0] == pans[1] == pans[2] and pans[0] in {"left", "right"}:
            issues.append(f"repeated_directional_pan_scene_{index + 1}")
            penalty += 4.0

    pace_values = {round(float(x.get("pace_multiplier", 1.0)), 2) for x in scenes}
    if len(pace_values) < 3:
        issues.append("pacing_variety_low")
        penalty += 6.0

    high_motion = sum(1 for x in scenes if x.get("media_type") == "photo" and float(x.get("zoom_end", 1)) - float(x.get("zoom_start", 1)) > 0.024)
    if high_motion > max(2, len(scenes) // 4):
        issues.append("high_motion_density")
        penalty += min(8.0, (high_motion - 2) * 2.0)

    slow_transitions = sum(1 for x in scenes[:-1] if float(x.get("transition_duration", 0)) >= 0.12)
    if slow_transitions > len(scenes) // 2:
        issues.append("soft_fade_density_high")
        penalty += 4.0

    punches = sum(1 for x in scenes if x.get("micro_punch"))
    if punches > 3:
        issues.append("micro_punch_overuse")
        penalty += (punches - 3) * 2.5

    score = round(max(0.0, 100.0 - penalty), 1)
    return score, issues


def main() -> int:
    try:
        if not SHORT_ID:
            raise ValueError("SHORT_ID vazio")
        plan = build_plan()
        atomic_json(OUTPUT, plan)
    except Exception as exc:
        print(f"ERRO PROFESSIONAL EDIT DIRECTOR: {exc}")
        return 1

    print("\n================================")
    print("PROFESSIONAL EDIT DIRECTOR 1.0")
    print("================================")
    print(f"Perfil: {plan['profile']} | estilo: {plan['style']}")
    print(f"Professional score: {plan['professional_score']}/100")
    print(f"Status: {plan['status']}")
    print()
    for item in plan["scenes"]:
        print(
            f"{item['scene']:02d}. role={item['narrative_role']:<14} "
            f"pace={item['pace_multiplier']:.2f} cut={item['cut_style']:<13} "
            f"motion={item['motion_curve']} {item['zoom_start']:.3f}->{item['zoom_end']:.3f}"
        )
    if plan["issues"]:
        print("\nObservações: " + ", ".join(plan["issues"]))
    print(f"\nPlano: {OUTPUT}")
    print("PROFESSIONAL EDIT DIRECTOR: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
