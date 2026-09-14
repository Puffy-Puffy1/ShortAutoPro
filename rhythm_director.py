#!/usr/bin/env python3
import json, math, os, tempfile
from datetime import date
from pathlib import Path

from visual_editorial_policy import apply_editorial_policy
from visual_shot_policy import resolve_shot_type


def _scene_count():
    try:
        value = int(os.getenv("SHORT_QTD_CENAS", "12"))
    except (TypeError, ValueError):
        value = 12
    return max(6, min(20, value))


EXPECTED_SCENES = _scene_count()
BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
MOTION_PLAN = BASE / "roteiros" / f"motion_plan_{SHORT_ID}.json"
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
OUTPUT = BASE / "roteiros" / f"rhythm_plan_{SHORT_ID}.json"
BACKUP = BASE / "roteiros" / f"motion_plan_pre_rhythm_{SHORT_ID}.json"


def load_json(path):
    if not path.is_file():
        raise ValueError(f"arquivo ausente: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"JSON inválido em {path.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} deve conter objeto JSON")
    return data


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def validate_numbering(scenes, label):
    if not isinstance(scenes, list):
        raise ValueError(f"{label}.scenes deve ser lista")
    if len(scenes) != EXPECTED_SCENES:
        raise ValueError(f"{label} deve ter {EXPECTED_SCENES} cenas; recebeu {len(scenes)}")
    numbers = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"{label} cena {index} não é objeto")
        try:
            numbers.append(int(scene.get("scene")))
        except (TypeError, ValueError):
            raise ValueError(f"{label} cena {index} possui número inválido")
    expected = list(range(1, EXPECTED_SCENES + 1))
    if numbers != expected:
        raise ValueError(f"{label} numeração inválida: esperado {expected}, recebido {numbers}")
    return scenes


def finite_float(value, label):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} inválido: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} não finito: {value!r}")
    return result


def build_rhythm(motion_scenes, map_scenes):
    total = len(motion_scenes)
    result = []
    previous_pan = None
    previous_shot = None

    for index, (motion_scene, map_scene) in enumerate(zip(motion_scenes, map_scenes), start=1):
        new = dict(motion_scene)
        for key in ("visual_mode", "narrative_role", "segment"):
            if key in map_scene:
                new[key] = map_scene[key]

        new["shot_type"] = resolve_shot_type(
            map_scene.get("shot_type"),
            motion_scene.get("shot_type"),
            index,
            new.get("visual_mode", "environment"),
            previous_shot,
        )

        media = str(new.get("media_type", "")).strip().lower()
        if media not in {"photo", "video"}:
            raise ValueError(f"media_type inválido na cena {index}: {media!r}")

        start = finite_float(new.get("zoom_start", 1.0), f"zoom_start cena {index}")
        finite_float(new.get("zoom_end", 1.06), f"zoom_end cena {index}")

        new = apply_editorial_policy(new, index, total, previous_pan)

        if media == "video":
            new["zoom_start"] = 1.0
            new["zoom_end"] = 1.0
            new["pan"] = "none"
        else:
            start = max(1.0, min(start, 1.020))
            amplitude = finite_float(
                new.get("editorial_amplitude", 0.014),
                f"editorial_amplitude cena {index}",
            )
            end = max(start, min(start + amplitude, 1.050))
            new["zoom_start"] = round(start, 4)
            new["zoom_end"] = round(end, 4)

        result.append(new)
        previous_pan = new.get("pan")
        previous_shot = new.get("shot_type")

    return result


def audit_result(result):
    problems = []
    if len(result) != EXPECTED_SCENES:
        problems.append(f"scene_count_mismatch:{len(result)}/{EXPECTED_SCENES}")
    if [item.get("scene") for item in result] != list(range(1, EXPECTED_SCENES + 1)):
        problems.append("scene_numbering_invalid")

    photo_profiles = []
    centered_human_photos = 0
    human_photo_count = 0
    canonical_shots = {"wide", "medium", "closeup", "detail", "portrait", "overhead"}
    for item in result:
        media = str(item.get("media_type", "")).strip().lower()
        if media == "photo":
            photo_profiles.append(item.get("rhythm_profile"))
        if item.get("editorial_policy") != "humanized_v5":
            problems.append(f"editorial_policy_missing_scene_{item.get('scene')}")
        if item.get("shot_type") not in canonical_shots:
            problems.append(f"shot_type_invalid_scene_{item.get('scene')}")
        if media == "photo":
            try:
                amplitude = float(item.get("zoom_end", 1.0)) - float(item.get("zoom_start", 1.0))
            except (TypeError, ValueError):
                amplitude = 999.0
            if amplitude > 0.0301:
                problems.append(f"zoom_amplitude_excess_scene_{item.get('scene')}")
        mode = str(item.get("visual_mode", "")).strip().lower()
        if media == "photo" and mode in {"human_context", "portrait", "person", "people"}:
            human_photo_count += 1
            if item.get("pan") == "center":
                centered_human_photos += 1

    for index in range(2, len(result)):
        pans = [result[index-2].get("pan"), result[index-1].get("pan"), result[index].get("pan")]
        if pans[0] == pans[1] == pans[2] and pans[0] in {"left", "right"}:
            problems.append(f"pan_triplo_cena_{index + 1}")

    if len(photo_profiles) >= 4 and len(set(photo_profiles)) < 2:
        problems.append("editorial_profile_variety_low")
    if human_photo_count and centered_human_photos != human_photo_count:
        problems.append("human_subject_pan_not_centered")
    return problems


def main():
    try:
        if not SHORT_ID:
            raise ValueError("SHORT_ID vazio")
        motion = load_json(MOTION_PLAN)
        scene_map = load_json(SCENE_MAP)
        motion_scenes = validate_numbering(motion.get("scenes"), "motion_plan")
        map_scenes = validate_numbering(scene_map.get("scenes"), "scene_map")

        if [int(x["scene"]) for x in motion_scenes] != [int(x["scene"]) for x in map_scenes]:
            raise ValueError("motion_plan e scene_map divergem na numeração")

        result = build_rhythm(motion_scenes, map_scenes)
        problems = audit_result(result)
        if problems:
            raise ValueError("; ".join(problems))

        original_motion = dict(motion)
        updated_motion = dict(motion)
        updated_motion["version"] = "5.5"
        updated_motion["rhythm_director"] = {
            "applied": True,
            "policy": "humanized_v5_documentary_motion",
            "problems": [],
        }
        updated_motion["scenes"] = result

        rhythm_payload = {
            "short_id": SHORT_ID,
            "version": "5.5",
            "expected_scenes": EXPECTED_SCENES,
            "policy": "humanized_v5_documentary_motion",
            "problems": [],
            "scenes": result,
        }

        atomic_json(BACKUP, original_motion)
        atomic_json(MOTION_PLAN, updated_motion)
        atomic_json(OUTPUT, rhythm_payload)
    except Exception as exc:
        print(f"ERRO RHYTHM DIRECTOR: {exc}")
        return 1

    print()
    print("================================")
    print("MONTAGE RHYTHM DIRECTOR 5.5")
    print("================================")
    print()
    for scene in result:
        print(f"{scene['scene']:02d}. energy={scene['energy']} {scene['rhythm_profile']:<20} {scene['media_type']}")
        print(f"    shot={scene['shot_type']} | motion={scene['motion_profile']} | zoom={scene['zoom_start']:.3f}->{scene['zoom_end']:.3f} | pan={scene['pan']}")
    print()
    print("EDITORIAL POLICY: humanized_v5_documentary_motion")
    print("RHYTHM QUALITY: PASS")
    print(f"Plano:\n{OUTPUT}")
    print()
    print("MONTAGE RHYTHM DIRECTOR: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
