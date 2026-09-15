#!/usr/bin/env python3
"""Deterministic self-repair for the professional edit plan.

Repairs editing-pattern problems only. It never changes factual text, visual
queries or media identity.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import professional_edit_director as director

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
PLAN = BASE / "roteiros" / f"pro_edit_plan_{SHORT_ID}.json"
BACKUP = BASE / "roteiros" / f"pro_edit_plan_pre_repair_{SHORT_ID}.json"


def read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"plano inválido: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("plano precisa ser objeto JSON")
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


def repair(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) != director.EXPECTED:
        raise ValueError(f"plano precisa ter {director.EXPECTED} cenas")
    fixed = [dict(x) for x in scenes if isinstance(x, dict)]
    if len(fixed) != len(scenes):
        raise ValueError("cena inválida no plano")
    repairs: list[str] = []

    # Break mechanical directional triplets.
    for index in range(2, len(fixed)):
        pans = [str(fixed[j].get("pan", "")) for j in (index - 2, index - 1, index)]
        if pans[0] == pans[1] == pans[2] and pans[0] in {"left", "right"}:
            fixed[index]["pan"] = "right" if pans[0] == "left" else "left"
            repairs.append(f"scene_{index + 1}:directional_pan_flip")

    # When three neutral shot labels repeat, compensate with a quieter third beat.
    for index in range(2, len(fixed)):
        triple = fixed[index - 2 : index + 1]
        shots = [str(x.get("shot_type", "")) for x in triple]
        if len(set(shots)) == 1 and shots[0] not in {"portrait", "detail", "overhead"}:
            current = fixed[index]
            current["pan"] = "center"
            start = float(current.get("zoom_start", 1.0))
            end = float(current.get("zoom_end", start))
            current["zoom_end"] = round(start + min(max(0.0, end - start), 0.012), 4)
            current["cut_style"] = "editorial_breath"
            current["transition_duration"] = min(0.12, max(0.09, float(current.get("transition_duration", 0.075))))
            repairs.append(f"scene_{index + 1}:framing_repeat_compensated")

    # Limit the density of strong still motion to the strongest narrative beats.
    strong = [
        i for i, item in enumerate(fixed)
        if item.get("media_type") == "photo"
        and float(item.get("zoom_end", 1.0)) - float(item.get("zoom_start", 1.0)) > 0.024
    ]
    allowed = max(2, len(fixed) // 4)
    for index in strong[allowed:]:
        item = fixed[index]
        start = float(item.get("zoom_start", 1.0))
        item["zoom_end"] = round(start + 0.020, 4)
        repairs.append(f"scene_{index + 1}:strong_motion_reduced")

    # Too many 120ms fades feels templated. Shorten alternating calm transitions.
    slow = [i for i, item in enumerate(fixed[:-1]) if float(item.get("transition_duration", 0.0)) >= 0.12]
    if len(slow) > len(fixed) // 2:
        for index in slow[1::2]:
            fixed[index]["transition_duration"] = 0.085
            fixed[index]["cut_style"] = "editorial_cut"
            repairs.append(f"scene_{index + 1}:soft_fade_shortened")

    # Ensure visible pace contrast if upstream roles were unusually uniform.
    pace_values = {round(float(x.get("pace_multiplier", 1.0)), 2) for x in fixed}
    if len(pace_values) < 3 and len(fixed) >= 3:
        fixed[0]["pace_multiplier"] = min(float(fixed[0].get("pace_multiplier", 1.0)), 0.86)
        fixed[len(fixed) // 2]["pace_multiplier"] = 0.98
        fixed[-1]["pace_multiplier"] = max(float(fixed[-1].get("pace_multiplier", 1.0)), 1.06)
        repairs.append("global:pacing_contrast_rebuilt")

    score, issues = director.audit_plan(fixed)
    result = dict(data)
    result["version"] = "PRO_EDIT_1.1_REPAIRED"
    result["scenes"] = fixed
    result["repairs_applied"] = repairs
    result["professional_score"] = score
    result["issues"] = issues
    result["status"] = "PASS" if score >= float(result.get("professional_target", 88.0)) else "REVIEW"
    return result, repairs


def main() -> int:
    try:
        if not PLAN.is_file():
            raise ValueError(f"plano ausente: {PLAN}")
        data = read_json(PLAN)
        shutil.copy2(PLAN, BACKUP)
        result, repairs = repair(data)
        atomic_json(PLAN, result)
    except Exception as exc:
        print(f"ERRO PROFESSIONAL EDIT REPAIR: {exc}")
        return 1

    print("\n================================")
    print("PROFESSIONAL EDIT AUTO-REPAIR 1.0")
    print("================================")
    print(f"Repairs: {len(repairs)}")
    for item in repairs:
        print(f"- {item}")
    print(f"Professional score: {result['professional_score']}/100")
    print(f"Status: {result['status']}")
    print("PROFESSIONAL EDIT AUTO-REPAIR: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
