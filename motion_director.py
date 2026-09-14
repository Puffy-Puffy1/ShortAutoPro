#!/usr/bin/env python3
import json, os, math, tempfile
from datetime import date
from pathlib import Path


def _scene_count():
    try:
        value = int(os.getenv("SHORT_QTD_CENAS", "12"))
    except (TypeError, ValueError):
        value = 12
    return max(6, min(20, value))


EXPECTED_SCENES = _scene_count()
BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
MEDIA_DIR = BASE / "imagens" / f"short_{SHORT_ID}"
OUTPUT = BASE / "roteiros" / f"motion_plan_{SHORT_ID}.json"
MEDIA_EXTENSIONS = {".mp4", ".jpg", ".jpeg", ".png", ".webp"}

PERFIS = {
    "still": {"zoom_start": 1.00, "zoom_end": 1.015, "pan": "none", "intensity": 1},
    "document_push": {"zoom_start": 1.00, "zoom_end": 1.045, "pan": "center", "intensity": 2},
    "slow_push": {"zoom_start": 1.00, "zoom_end": 1.065, "pan": "center", "intensity": 3},
    "slow_pan_left": {"zoom_start": 1.03, "zoom_end": 1.07, "pan": "left", "intensity": 3},
    "slow_pan_right": {"zoom_start": 1.03, "zoom_end": 1.07, "pan": "right", "intensity": 3},
    "hook_push": {"zoom_start": 1.00, "zoom_end": 1.095, "pan": "center", "intensity": 4},
}


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


def validate_scenes(raw_scenes):
    if not isinstance(raw_scenes, list):
        raise ValueError("scene_map.scenes deve ser lista")
    if len(raw_scenes) != EXPECTED_SCENES:
        raise ValueError(f"scene_map deve ter {EXPECTED_SCENES} cenas; recebeu {len(raw_scenes)}")
    scenes, numbers = [], []
    for index, scene in enumerate(raw_scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"cena {index} não é objeto JSON")
        try:
            number = int(scene.get("scene"))
        except (TypeError, ValueError):
            raise ValueError(f"cena {index} possui número inválido")
        numbers.append(number)
        scenes.append(scene)
    expected = list(range(1, EXPECTED_SCENES + 1))
    if numbers != expected:
        raise ValueError(f"numeração de cenas inválida: esperado {expected}, recebido {numbers}")
    return scenes


def locate_media(media_dir, number):
    if not media_dir.is_dir():
        raise ValueError(f"diretório de mídia ausente: {media_dir}")
    prefix = f"scene_{number:02d}"
    matches = sorted(
        p for p in media_dir.iterdir()
        if p.is_file() and p.stem == prefix and p.suffix.lower() in MEDIA_EXTENSIONS
    )
    if not matches:
        raise ValueError(f"mídia ausente para cena {number:02d}")
    if len(matches) > 1:
        raise ValueError(f"mídia ambígua para cena {number:02d}: " + ", ".join(p.name for p in matches))
    return matches[0]


def media_type(path):
    ext = path.suffix.lower()
    if ext == ".mp4":
        return "video"
    if ext in {".jpg", ".jpeg", ".png", ".webp"}:
        return "photo"
    raise ValueError(f"extensão de mídia não suportada: {ext}")


def choose_profile(number, visual_mode, kind):
    if kind == "video":
        return "native_video", {"zoom_start": 1.0, "zoom_end": 1.0, "pan": "none", "intensity": 0}
    if number == 1:
        return "hook_push", PERFIS["hook_push"]
    if visual_mode in {"document", "evidence", "map_context"}:
        return "document_push", PERFIS["document_push"]
    if visual_mode in {"location", "environment"}:
        return ("slow_pan_left", PERFIS["slow_pan_left"]) if number % 2 == 0 else ("slow_pan_right", PERFIS["slow_pan_right"])
    if visual_mode in {"architecture", "transport", "object"}:
        return "slow_push", PERFIS["slow_push"]
    if visual_mode == "human_context":
        return "still", PERFIS["still"]
    return "slow_push", PERFIS["slow_push"]


def build_plan(scenes, media_dir):
    plan = []
    for scene in scenes:
        number = int(scene["scene"])
        visual_mode = str(scene.get("visual_mode", "environment")).strip().lower()
        shot_type = str(scene.get("shot_type", "medium")).strip().lower()
        media = locate_media(media_dir, number)
        kind = media_type(media)
        profile_name, profile = choose_profile(number, visual_mode, kind)
        plan.append({
            "scene": number,
            "visual_mode": visual_mode,
            "shot_type": shot_type,
            "media_type": kind,
            "media": str(media),
            "motion_profile": profile_name,
            "zoom_start": profile["zoom_start"],
            "zoom_end": profile["zoom_end"],
            "pan": profile["pan"],
            "intensity": profile["intensity"],
        })
    for index in range(2, len(plan)):
        current = plan[index]["motion_profile"]
        if current == plan[index-1]["motion_profile"] == plan[index-2]["motion_profile"] and current not in {"native_video", "document_push"}:
            if current == "slow_pan_left":
                plan[index]["motion_profile"], plan[index]["pan"] = "slow_pan_right", "right"
            elif current == "slow_pan_right":
                plan[index]["motion_profile"], plan[index]["pan"] = "slow_pan_left", "left"
    return plan


def audit_plan(plan):
    problems = []
    if len(plan) != EXPECTED_SCENES:
        problems.append(f"scene_count_mismatch:{len(plan)}/{EXPECTED_SCENES}")
    if [item.get("scene") for item in plan] != list(range(1, EXPECTED_SCENES + 1)):
        problems.append("scene_numbering_invalid")
    for item in plan:
        media = item.get("media")
        if not isinstance(media, str) or not Path(media).is_file():
            problems.append(f"missing_media_scene_{item.get('scene')}")
        for key in ("zoom_start", "zoom_end"):
            value = item.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                problems.append(f"invalid_{key}_scene_{item.get('scene')}")
    return problems


def main():
    try:
        if not SHORT_ID:
            raise ValueError("SHORT_ID vazio")
        scene_map = load_json(SCENE_MAP)
        scenes = validate_scenes(scene_map.get("scenes"))
        plan = build_plan(scenes, MEDIA_DIR)
        problems = audit_plan(plan)
        if problems:
            raise ValueError("; ".join(problems))
        result = {
            "short_id": SHORT_ID, "version": "3.9",
            "expected_scenes": EXPECTED_SCENES,
            "scene_count": len(plan), "problems": [], "scenes": plan,
        }
        atomic_json(OUTPUT, result)
    except Exception as exc:
        print(f"ERRO MOTION DIRECTOR: {exc}")
        return 1
    print()
    print("================================")
    print("CINEMATIC MOTION DIRECTOR 3.9")
    print("================================")
    print()
    for item in plan:
        print(f"{item['scene']:02d}. {item['visual_mode']:<16} {item['media_type']:<7} -> {item['motion_profile']}")
        print(f"    zoom {item['zoom_start']:.3f} -> {item['zoom_end']:.3f} | pan={item['pan']} | intensity={item['intensity']}")
    print()
    print(f"Cenas: {len(plan)}/{EXPECTED_SCENES}")
    print("MOTION PLAN: PASS")
    print(f"Plano:\n{OUTPUT}")
    print()
    print("CINEMATIC MOTION DIRECTOR: OK")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
