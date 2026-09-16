#!/usr/bin/env python3
"""Multidimensional selected-visual scoring for ShortAutoPro 3.0.3.

The score is based on the media that was actually committed by the canonical
selector. VI6 SHADOW data is used only when an older run has no selection
manifest, never as if it were the final chosen asset.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
R = BASE / "roteiros"
MAP = R / f"scene_map_{SID}.json"
VI = R / f"visual_intelligence_6_{SID}.json"
SELECTION = R / f"media_selection_{SID}.json"
MEDIA = BASE / "imagens" / f"short_{SID}"
OUT = R / f"visual_score_{SID}.json"

GENERIC = {
    "coffee", "cafe", "lifestyle", "smiling", "happy", "model", "shopping",
    "basket", "laundry", "generic", "stock", "office worker", "sunset",
    "landscape",
}


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(
        "".join(char for char in text if not unicodedata.combining(char)).lower().split()
    )


def toks(value: Any) -> set[str]:
    stop = {
        "the", "and", "for", "with", "from", "into", "over", "under", "of",
        "in", "on", "at", "a", "an", "de", "da", "do", "das", "dos", "em",
        "com", "para", "por",
    }
    return {
        item for item in re.findall(r"[a-z0-9]+", norm(value))
        if len(item) >= 3 and item not in stop
    }


def overlap(a: Any, b: Any) -> float:
    left = toks(a)
    right = toks(b)
    if not left:
        return 1.0
    return len(left & right) / len(left)


def number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def atomic(path: Path, payload: Any) -> None:
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


def media_for(number_: int) -> Path | None:
    hits = [
        path for path in MEDIA.glob(f"scene_{number_:02d}.*")
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
    ]
    return hits[0] if len(hits) == 1 else None


def probe(path: Path | None) -> tuple[int, int]:
    if not path:
        return 0, 0
    try:
        proc = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        streams = json.loads(proc.stdout).get("streams", [])
        if streams:
            return int(streams[0].get("width", 0)), int(streams[0].get("height", 0))
    except Exception:
        pass
    return 0, 0


def selection_index(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    scenes = data.get("scenes", []) if isinstance(data, dict) else []
    result: dict[int, dict[str, Any]] = {}
    if not isinstance(scenes, list):
        return result
    for item in scenes:
        if not isinstance(item, dict):
            continue
        try:
            scene_number = int(item.get("scene"))
        except (TypeError, ValueError):
            continue
        if scene_number > 0:
            result[scene_number] = item
    return result


def selected_relevance(scene: dict[str, Any], selected: dict[str, Any]) -> float:
    description = str(selected.get("description", "") or "")
    must = scene.get("must_have", []) if isinstance(scene.get("must_have"), list) else []
    total = int(number(selected.get("must_total"), len(must)))
    hits = int(number(selected.get("must_hits"), 0))
    coverage = number(selected.get("must_coverage"), hits / total if total else 1.0)
    coverage = max(0.0, min(1.0, coverage))

    query_overlap = overlap(scene.get("query", ""), description) if description else 0.0
    segment_overlap = max(0.0, min(1.0, number(selected.get("segment_overlap"), 0.0)))
    topic_overlap = max(0.0, min(1.0, number(selected.get("topic_overlap"), 0.0)))

    # Explicit verified MUST coverage is authoritative. Text overlap supplements
    # it, rather than replacing real asset-evidence verification.
    score = 42.0 + 38.0 * coverage + 12.0 * max(query_overlap, segment_overlap) + 8.0 * topic_overlap
    if selected.get("contextual_rescue") and coverage <= 0.0:
        score = min(score, 70.0)
    return clamp(score)


def main() -> int:
    scene_map = load(MAP)
    vi = load(VI)
    selection = selection_index(load(SELECTION))
    scenes = scene_map.get("scenes", []) if isinstance(scene_map.get("scenes"), list) else []
    vi_scenes = vi.get("scenes", []) if isinstance(vi.get("scenes"), list) else []
    if not scenes:
        print("ERRO VISUAL SCORE: scene_map ausente")
        return 1

    rows: list[dict[str, Any]] = []
    all_scores: list[float] = []
    selected_count = 0

    for index, scene in enumerate(scenes, 1):
        shadow = vi_scenes[index - 1] if index <= len(vi_scenes) and isinstance(vi_scenes[index - 1], dict) else {}
        shadow_winner = shadow.get("winner", {}) if isinstance(shadow.get("winner"), dict) else {}
        selected = selection.get(index, {})
        physical = media_for(index)
        width, height = probe(physical)
        pixels = width * height

        if selected:
            selected_count += 1
            basis = "ACTUAL_SELECTION_MANIFEST"
            description = str(selected.get("description", "") or "")
            source = str(selected.get("provider", "") or "")
            evidence_class = str(selected.get("evidence_class", "") or "")
            media_type = str(selected.get("media_type", "") or "")
            relevance = selected_relevance(scene, selected)
            must = scene.get("must_have", []) if isinstance(scene.get("must_have"), list) else []
            must_total = int(number(selected.get("must_total"), len(must)))
            must_hits = int(number(selected.get("must_hits"), 0))
            subject = clamp(100.0 * must_hits / must_total) if must_total > 0 else 90.0
            risk = "LOW" if int(number(selected.get("avoid_hits"), 0)) == 0 else "HIGH"
            klass = "REAL_DOCUMENTARY" if evidence_class == "CASE_DIRECT" else "SELECTED_MEDIA"
        else:
            # Backward-compatible diagnostics for older runs only.
            basis = "VI6_SHADOW_FALLBACK"
            description = str(shadow_winner.get("descricao", "") or "")
            source = str(shadow_winner.get("fonte", "") or "")
            evidence_class = str(shadow_winner.get("evidence_class", "") or "")
            media_type = "video" if physical and physical.suffix.lower() == ".mp4" else "photo"
            relevance = clamp(number(shadow_winner.get("semantic"), 65.0)) if shadow_winner else 65.0
            subject_text = " ".join([
                str(scene.get("main_subject", "")),
                " ".join(str(item) for item in scene.get("must_have", []) if str(item).strip()),
            ])
            subject = clamp(100 * overlap(subject_text, description)) if subject_text.strip() else 85.0
            risk = str(shadow_winner.get("risk", "LOW") or "LOW").upper()
            klass = str(shadow_winner.get("class", "") or "")

        location = clamp(100 * overlap(scene.get("location", ""), description)) if scene.get("location") else 90.0
        era = clamp(100 * overlap(scene.get("era", ""), description)) if scene.get("era") else 90.0
        quality = 100.0 if pixels >= 1280 * 720 else 90.0 if pixels >= 921600 else 75.0 if pixels >= 640 * 360 else 35.0
        orientation = 100.0 if height > width else 86.0 if height and width else 50.0
        safety = 100.0 if risk in {"LOW", ""} and "MISLEADING" not in klass else 70.0 if risk == "MEDIUM" else 0.0

        generic_hits = sum(1 for term in GENERIC if term in norm(description))
        generic_penalty = 0.0
        if source.casefold() in {"pexels", "pixabay", "coverr"} and relevance < 72:
            generic_penalty += 12.0
        generic_penalty += min(24.0, generic_hits * 6.0)
        evidence_bonus = 8.0 if evidence_class == "CASE_DIRECT" or klass == "REAL_DOCUMENTARY" else 3.0 if klass == "SAFE_CONTEXT" else 0.0

        components = {
            "relevance": relevance,
            "location": location,
            "character_object": subject,
            "era": era,
            "quality": quality,
            "orientation": orientation,
            "safety": safety,
        }
        weights = {
            "relevance": 0.28,
            "location": 0.12,
            "character_object": 0.18,
            "era": 0.08,
            "quality": 0.14,
            "orientation": 0.08,
            "safety": 0.12,
        }
        score = clamp(sum(components[key] * weights[key] for key in weights) - generic_penalty + evidence_bonus)
        all_scores.append(score)
        rows.append({
            "scene": index,
            "media": str(physical) if physical else None,
            "media_type": media_type,
            "provider": source or None,
            "evidence_basis": basis,
            "evidence_class": evidence_class or None,
            "components": components,
            "generic_penalty": generic_penalty,
            "documentary_bonus": evidence_bonus,
            "visual_score": score,
        })

    average = round(sum(all_scores) / len(all_scores), 1)
    minimum = float(os.getenv("SAP_VISUAL_SCORE_MIN", "72"))
    weak = [row["scene"] for row in rows if row["visual_score"] < minimum]
    manifest_coverage = selected_count / max(1, len(scenes))
    payload = {
        "short_id": SID,
        "version": "1.1",
        "visual_score": average,
        "threshold": minimum,
        "status": "PASS" if not weak and average >= minimum else "REVIEW",
        "weak_scenes": weak,
        "selection_manifest_coverage": round(manifest_coverage, 4),
        "scenes": rows,
    }
    atomic(OUT, payload)
    print(
        f"VISUAL MULTISCORE 1.1: {payload['status']} | {average}/100 | "
        f"weak={weak} | actual_selection={selected_count}/{len(scenes)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
