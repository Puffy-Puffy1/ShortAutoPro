#!/usr/bin/env python3
import json, math, os, tempfile
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
MOTION_PLAN = BASE / "roteiros" / f"motion_plan_{SHORT_ID}.json"
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
OUTPUT = BASE / "roteiros" / f"rhythm_plan_{SHORT_ID}.json"
BACKUP = BASE / "roteiros" / f"motion_plan_pre_rhythm_{SHORT_ID}.json"

CALMOS = {"document", "evidence", "map_context"}
DINAMICOS = {"location", "environment", "transport", "architecture"}


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


def energia_base(numero, total):
    if numero == 1:
        return 5
    proporcao = numero / max(total, 1)
    if proporcao <= 0.25:
        return 2
    if proporcao <= 0.50:
        return 3
    if proporcao <= 0.75:
        return 4
    if numero == total:
        return 2
    return 3


def ajustar_zoom(scene, energia):
    numero = scene.get("scene", "?")
    inicio = finite_float(scene.get("zoom_start", 1.0), f"zoom_start cena {numero}")
    fim_original = finite_float(scene.get("zoom_end", 1.06), f"zoom_end cena {numero}")
    modo = str(scene.get("visual_mode", "")).strip().lower()
    media = str(scene.get("media_type", "")).strip().lower()

    if media == "video":
        return 1.0, 1.0
    if media != "photo":
        raise ValueError(f"media_type inválido na cena {numero}: {media!r}")

    if modo in CALMOS:
        amplitude = {1: 0.015, 2: 0.025, 3: 0.035, 4: 0.045, 5: 0.055}.get(energia, 0.035)
    elif modo in DINAMICOS:
        amplitude = {1: 0.025, 2: 0.040, 3: 0.055, 4: 0.070, 5: 0.090}.get(energia, 0.055)
    else:
        amplitude = {1: 0.020, 2: 0.035, 3: 0.050, 4: 0.065, 5: 0.080}.get(energia, 0.050)

    inicio = max(1.0, min(inicio, 1.05))
    _ = fim_original
    fim = max(inicio, min(inicio + amplitude, 1.11))
    return inicio, fim


def build_rhythm(motion_scenes):
    total = len(motion_scenes)
    result = []
    previous_profile = None
    previous_pan = None

    for index, scene in enumerate(motion_scenes, start=1):
        new = dict(scene)
        mode = str(new.get("visual_mode", "")).strip().lower()
        media = str(new.get("media_type", "")).strip().lower()
        profile = str(new.get("motion_profile", "")).strip()
        pan = str(new.get("pan", "center")).strip().lower()

        if not profile:
            raise ValueError(f"motion_profile ausente na cena {index}")
        if media not in {"photo", "video"}:
            raise ValueError(f"media_type inválido na cena {index}: {media!r}")
        if pan not in {"none", "center", "left", "right"}:
            raise ValueError(f"pan inválido na cena {index}: {pan!r}")

        energy = energia_base(index, total)
        if index == 1:
            energy = 5
        if mode in CALMOS:
            energy = min(energy, 3)
        visual_energy = 0 if media == "video" else energy

        if media == "photo" and pan in {"left", "right"} and pan == previous_pan:
            pan = "right" if pan == "left" else "left"

        if media == "photo" and profile == previous_profile and mode not in CALMOS and pan == "center":
            pan = "left" if index % 2 == 0 else "right"

        zoom_start, zoom_end = ajustar_zoom(new, energy)
        new["energy"] = energy
        new["visual_energy"] = visual_energy
        new["zoom_start"] = round(zoom_start, 4)
        new["zoom_end"] = round(zoom_end, 4)
        new["pan"] = pan

        if media == "photo":
            new["rhythm_profile"] = (
                "hook" if index == 1 else
                "calm_documentary" if mode in CALMOS else
                "dynamic" if energy >= 4 else
                "balanced"
            )
        else:
            new["rhythm_profile"] = "native_video"

        result.append(new)
        previous_profile = profile
        previous_pan = pan

    return result


def audit_result(result):
    problems = []
    if len(result) != EXPECTED_SCENES:
        problems.append(f"scene_count_mismatch:{len(result)}/{EXPECTED_SCENES}")
    if [item.get("scene") for item in result] != list(range(1, EXPECTED_SCENES + 1)):
        problems.append("scene_numbering_invalid")

    for index in range(2, len(result)):
        pans = [result[index-2].get("pan"), result[index-1].get("pan"), result[index].get("pan")]
        if pans[0] == pans[1] == pans[2] and pans[0] in {"left", "right"}:
            problems.append(f"pan_triplo_cena_{index + 1}")
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

        result = build_rhythm(motion_scenes)
        problems = audit_result(result)
        if problems:
            raise ValueError("; ".join(problems))

        original_motion = dict(motion)
        updated_motion = dict(motion)
        updated_motion["version"] = "4.4"
        updated_motion["rhythm_director"] = {"applied": True, "problems": []}
        updated_motion["scenes"] = result

        rhythm_payload = {
            "short_id": SHORT_ID,
            "version": "4.4",
            "expected_scenes": EXPECTED_SCENES,
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
    print("MONTAGE RHYTHM DIRECTOR 4.4")
    print("================================")
    print()
    for scene in result:
        print(f"{scene['scene']:02d}. energy={scene['energy']} {scene['rhythm_profile']:<18} {scene['media_type']}")
        print(f"    motion={scene['motion_profile']} | zoom={scene['zoom_start']:.3f}->{scene['zoom_end']:.3f} | pan={scene['pan']}")
    print()
    print("RHYTHM QUALITY: PASS")
    print(f"Plano:\n{OUTPUT}")
    print()
    print("MONTAGE RHYTHM DIRECTOR: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
