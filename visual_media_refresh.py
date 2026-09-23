#!/usr/bin/env python3
"""Bounded refresh of weak/repeated primary visual assets.

Backs up only selected scene assets and removes them so the canonical Stage 6
incremental controller must reacquire those scenes. Narration and factual scene
contracts are never modified here.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from runtime_config import env_int

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
R = BASE / "roteiros"
E = BASE / "reports" / "evolution"
MEDIA = BASE / "imagens" / f"short_{SID}"
BACKUPS = BASE / "backups" / "visual_refresh" / SID
OUT = BASE / "reports" / "repair" / f"visual_media_refresh_{SID}.json"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}

def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

def scene_assets(number: int) -> list[Path]:
    if not MEDIA.is_dir():
        return []
    return sorted(
        p for p in MEDIA.glob(f"scene_{number:02d}.*")
        if p.is_file() and p.suffix.lower() in EXTS
    )

def choose_targets() -> tuple[list[int], dict[str, Any]]:
    visual = load(R / f"visual_score_{SID}.json")
    media_quality = load(R / f"media_quality_{SID}.json")
    vqa = load(E / f"visual_qa_{SID}.json")
    weak = [int(x) for x in visual.get("weak_scenes", []) if str(x).isdigit()]
    rows = visual.get("scenes", []) if isinstance(visual.get("scenes"), list) else []
    scores: dict[int, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            scene = int(row.get("scene"))
            score = float(row.get("visual_score", 100))
        except (TypeError, ValueError):
            continue
        scores[scene] = score

    diversity = (
        vqa.get("measurements", {}).get("scene_diversity", {})
        if isinstance(vqa.get("measurements"), dict)
        else {}
    )
    cluster_ids = diversity.get("cluster_ids", []) if isinstance(diversity.get("cluster_ids"), list) else []
    duplicate_cluster_scenes: list[int] = []
    first_by_cluster: dict[int, int] = {}
    for idx, raw in enumerate(cluster_ids, 1):
        try:
            cluster = int(raw)
        except (TypeError, ValueError):
            continue
        if cluster in first_by_cluster:
            duplicate_cluster_scenes.append(idx)
        else:
            first_by_cluster[cluster] = idx

    media_targets: list[int] = []
    media_items = []
    if isinstance(media_quality.get("critical"), list):
        media_items.extend(str(x) for x in media_quality.get("critical", []))
    if isinstance(media_quality.get("warnings"), list):
        media_items.extend(str(x) for x in media_quality.get("warnings", []))
    for item in media_items:
        for match in __import__("re").findall(r"scene_(\\d{2})", item):
            try:
                scene = int(match)
            except ValueError:
                continue
            if scene not in media_targets:
                media_targets.append(scene)

    priority: list[int] = []
    for scene in duplicate_cluster_scenes + media_targets:
        if scene not in priority:
            priority.append(scene)
    for scene in sorted(set(weak), key=lambda x: (scores.get(x, 100.0), x)):
        if scene not in priority:
            priority.append(scene)

    max_refresh = env_int("SAP_VISUAL_REFRESH_MAX_SCENES", 6, 1, 12)
    targets = priority[:max_refresh]
    return targets, {
        "weak_scenes": weak,
        "duplicate_cluster_scenes": duplicate_cluster_scenes,
        "media_quality_targets": media_targets,
        "visual_scores": scores,
        "max_refresh": max_refresh,
    }

def main() -> int:
    if not SID:
        print("VISUAL_MEDIA_REFRESH=BLOCK short_id_empty")
        return 1
    targets, evidence = choose_targets()
    if not targets:
        payload = {
            "short_id": SID,
            "version": "VISUAL_MEDIA_REFRESH_1.0",
            "status": "PASS",
            "reason": "no_refresh_targets",
            "targets": [],
            "evidence": evidence,
        }
        atomic(OUT, payload)
        print("VISUAL_MEDIA_REFRESH=PASS targets=0")
        return 0

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUPS / stamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    moved: list[dict[str, str]] = []
    missing: list[int] = []

    for scene in targets:
        assets = scene_assets(scene)
        if not assets:
            missing.append(scene)
            continue
        for path in assets:
            destination = backup_dir / path.name
            shutil.move(str(path), str(destination))
            moved.append({"scene": str(scene), "from": str(path), "backup": str(destination)})

    payload = {
        "short_id": SID,
        "version": "VISUAL_MEDIA_REFRESH_1.0",
        "status": "PASS",
        "targets": targets,
        "moved_count": len(moved),
        "missing_before_refresh": missing,
        "backup_dir": str(backup_dir),
        "moved": moved,
        "evidence": evidence,
    }
    atomic(OUT, payload)
    print(
        "VISUAL_MEDIA_REFRESH=PASS "
        f"targets={','.join(map(str, targets))} moved={len(moved)} backup={backup_dir}"
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
