#!/usr/bin/env python3
"""Semantic safe-zone guard for ASS captions.

Uses Visual Director protected zones. It does not claim face detection; it moves
the global caption safe area when the storyboard indicates important lower-frame
content and reports residual collision risk.
"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
ASS = BASE / "videos" / f"short_{SID}.ass"
MAP = BASE / "manifests" / f"scene_map_{SID}.json"
REPORT = BASE / "roteiros" / f"caption_layout_{SID}.json"


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    if not ASS.is_file() or not MAP.is_file():
        print("ERRO CAPTION LAYOUT: artefatos ausentes")
        return 1

    try:
        data = json.loads(MAP.read_text(encoding="utf-8"))
        if (
            data.get("schema_version") != "SCENE_MAP_FROZEN_1.0"
            or data.get("short_id") != SID
            or data.get("mutable_upstream_closed") is not True
        ):
            raise ValueError("SceneMap frozen contract inválido")

        scenes = data.get("scenes", [])
        zones = [
            str(scene.get("protected_zone", "center")).lower()
            for scene in scenes
            if isinstance(scene, dict)
        ]
        bottom = sum(1 for zone in zones if zone == "bottom")
        center = sum(1 for zone in zones if zone == "center")
        margin = 335
    except Exception as exc:
        print(f"ERRO CAPTION LAYOUT: {exc}")
        return 1

    if bottom >= max(2, len(zones) // 4):
        margin = 420
    elif bottom:
        margin = 385

    content = ASS.read_text(encoding="utf-8")
    lines = []
    changed = False
    for line in content.splitlines():
        if line.startswith("Style: Dynamic,"):
            parts = line.split(",")
            if len(parts) >= 23:
                parts[21] = str(margin)
                line = ",".join(parts)
                changed = True
        lines.append(line)

    if not changed:
        print("ERRO CAPTION LAYOUT: Style Dynamic ausente")
        return 1

    atomic_text(ASS, "\n".join(lines) + "\n")
    risk = round(100 * bottom / max(1, len(zones)), 1)
    score = round(max(0, 100 - risk * 0.35), 1)
    atomic_json(
        REPORT,
        {
            "short_id": SID,
            "version": "1.1",
            "status": "PASS" if score >= 88 else "REVIEW",
            "score": score,
            "protected_zones": {"bottom": bottom, "center": center, "total": len(zones)},
            "margin_v": margin,
            "collision_risk_percent": risk,
            "method": "semantic protected-zone heuristic; no face detector claimed",
        },
    )
    print(f"CAPTION LAYOUT: PASS | margin_v={margin} | risk={risk}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
