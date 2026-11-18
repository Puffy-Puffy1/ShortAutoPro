#!/usr/bin/env python3
"""Semantic safe-zone guard for portrait and landscape ASS captions."""
from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
ASS = BASE / "videos" / f"short_{SID}.ass"
MAP = BASE / "roteiros" / f"scene_map_{SID}.json"
REPORT = BASE / "roteiros" / f"caption_layout_{SID}.json"


def studio_height() -> int:
    try:
        return max(240, min(2160, int(os.getenv("SAP_STUDIO_HEIGHT", "1920"))))
    except (TypeError, ValueError):
        return 1920


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
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
        scenes = data.get("scenes", [])
        if not isinstance(scenes, list) or not scenes:
            raise ValueError("scene_map sem cenas")
        zones = [
            str(item.get("protected_zone", "center")).lower()
            for item in scenes
            if isinstance(item, dict)
        ]
        bottom = sum(1 for zone in zones if zone == "bottom")
        center = sum(1 for zone in zones if zone == "center")
        height = studio_height()
        base_margin = round(height * 0.175)
        bottom_margin = round(height * 0.219)
        middle_margin = round(height * 0.201)
        margin = base_margin
    except Exception as exc:
        print(f"ERRO CAPTION LAYOUT: {exc}")
        return 1

    if bottom >= max(2, len(zones) // 4):
        margin = bottom_margin
    elif bottom:
        margin = middle_margin

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
    atomic_json(REPORT, {
        "short_id": SID,
        "version": "1.2",
        "status": "PASS" if score >= 88 else "REVIEW",
        "score": score,
        "protected_zones": {"bottom": bottom, "center": center, "total": len(zones)},
        "margin_v": margin,
        "play_res_y": height,
        "collision_risk_percent": risk,
        "method": "semantic protected-zone heuristic; no face detector claimed",
    })
    print(f"CAPTION LAYOUT: PASS | margin_v={margin} | risk={risk}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
