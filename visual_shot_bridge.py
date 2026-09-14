#!/usr/bin/env python3
"""Persist visual-director framing decisions into the active scene map.

The Visual Director already asks Gemini for a shot_type, but historically that
field lived only in its report. This bridge makes framing part of the production
contract without changing query facts, must-have constraints, or scene text.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path

from visual_shot_policy import resolve_shot_type


BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro")))
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
try:
    EXPECTED = int(os.getenv("SHORT_QTD_CENAS", "12"))
except (TypeError, ValueError):
    EXPECTED = 12
EXPECTED = max(6, min(20, EXPECTED))

R = BASE / "roteiros"
SCENE_MAP = R / f"scene_map_{SHORT_ID}.json"
REPORT = R / f"visual_director_{SHORT_ID}.json"
OUTPUT_REPORT = R / f"visual_shot_bridge_{SHORT_ID}.json"


def load_object(path: Path, label: str) -> dict:
    if not path.is_file():
        raise ValueError(f"{label} ausente: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"{label} inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{label} deve ser objeto JSON")
    return data


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def numbered_scenes(data: dict, label: str):
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != EXPECTED:
        raise ValueError(f"{label} deve ter {EXPECTED} cenas")
    numbers = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"{label} cena {index} inválida")
        try:
            numbers.append(int(scene.get("scene")))
        except (TypeError, ValueError):
            raise ValueError(f"{label} cena {index} sem número válido")
    if numbers != list(range(1, EXPECTED + 1)):
        raise ValueError(f"{label} numeração inválida")
    return scenes


def suggestions_by_scene(report: dict):
    out = {}
    scenes = report.get("scenes", [])
    if not isinstance(scenes, list):
        return out
    for item in scenes:
        if not isinstance(item, dict):
            continue
        try:
            number = int(item.get("scene"))
        except (TypeError, ValueError):
            continue
        if 1 <= number <= EXPECTED:
            out[number] = str(item.get("shot_type", "") or "")
    return out


def apply_shot_bridge(scene_map: dict, report: dict):
    scenes = numbered_scenes(scene_map, "scene_map")
    suggested = suggestions_by_scene(report)
    result = []
    changes = []
    previous = ""

    for index, scene in enumerate(scenes, start=1):
        new = dict(scene)
        original = str(scene.get("shot_type", "") or "")
        resolved = resolve_shot_type(
            suggested.get(index, ""),
            original,
            index,
            scene.get("visual_mode", ""),
            previous,
        )
        new["shot_type"] = resolved
        result.append(new)
        changes.append(
            {
                "scene": index,
                "suggested": suggested.get(index, ""),
                "original": original,
                "resolved": resolved,
            }
        )
        previous = resolved

    updated = dict(scene_map)
    updated["scenes"] = result
    updated["visual_shot_bridge"] = {
        "version": "1.0",
        "policy": "humanized_documentary_shot_grammar",
        "applied": True,
    }
    return updated, changes


def main() -> int:
    try:
        if not SHORT_ID:
            raise ValueError("SHORT_ID vazio")
        scene_map = load_object(SCENE_MAP, "scene_map")
        report = load_object(REPORT, "visual_director report")
        updated, changes = apply_shot_bridge(scene_map, report)
        atomic_json(SCENE_MAP, updated)
        atomic_json(
            OUTPUT_REPORT,
            {
                "short_id": SHORT_ID,
                "version": "1.0",
                "policy": "humanized_documentary_shot_grammar",
                "scenes": changes,
            },
        )
    except Exception as exc:
        print(f"ERRO VISUAL SHOT BRIDGE: {exc}")
        return 1

    unique = len({item["resolved"] for item in changes if item["resolved"]})
    print()
    print("================================")
    print("VISUAL SHOT BRIDGE 1.0")
    print("================================")
    print(f"Cenas: {len(changes)}/{EXPECTED}")
    print(f"Planos únicos: {unique}")
    print("SHOT GRAMMAR: humanized_documentary_shot_grammar")
    print("VISUAL SHOT BRIDGE: OK")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
