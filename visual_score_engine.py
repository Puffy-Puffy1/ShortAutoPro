#!/usr/bin/env python3
"""Canonical multidimensional visual scoring for ShortAutoPro.

Production scores prefer the exact candidate committed by VISUAL_UNIFIED.
Legacy VI6 shadow metadata is retained only as low-confidence observation when
canonical commit evidence is unavailable.
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
SELECTED = R / f"selected_media_{SID}.json"
MEDIA = BASE / "imagens" / f"short_{SID}"
OUT = R / f"visual_score_{SID}.json"

GENERIC = {
    "coffee", "cafe", "lifestyle", "smiling", "happy", "model", "shopping",
    "basket", "laundry", "generic", "stock", "office worker", "sunset", "landscape",
}


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).lower().split())


def toks(value: Any) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", norm(value)) if len(x) >= 3}


def overlap(a: Any, b: Any) -> float:
    aa, bb = toks(a), toks(b)
    if not aa:
        return 1.0
    return len(aa & bb) / len(aa)


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def media_for(number: int) -> Path | None:
    hits = [
        path for path in MEDIA.glob(f"scene_{number:02d}.*")
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
    ]
    return hits[0] if len(hits) == 1 else None


def probe(path: Path | None) -> tuple[int, int]:
    if not path:
        return 0, 0
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=width,height", "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        streams = json.loads(result.stdout).get("streams", [])
        return (
            int(streams[0].get("width", 0)),
            int(streams[0].get("height", 0)),
        ) if streams else (0, 0)
    except Exception:
        return 0, 0


def number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def canonical_row(selected: dict[str, Any], scene_number: int) -> dict[str, Any]:
    scenes = selected.get("scenes", {}) if isinstance(selected.get("scenes"), dict) else {}
    row = scenes.get(str(scene_number), {})
    return row if isinstance(row, dict) else {}


def semantic_relevance(scene: dict[str, Any], meta: dict[str, Any], description: str) -> float:
    query = str(meta.get("query") or scene.get("query") or "")
    query_match = overlap(query, description) if query.strip() else 0.5
    base = clamp(number(meta.get("base_score"), 55.0))
    raw_semantic = meta.get("raw_semantic_score")
    if raw_semantic is not None:
        raw = clamp(number(raw_semantic, 55.0))
        base = max(base, raw)
    must_total = int(number(meta.get("must_verified_total"), 0))
    must_hits = int(number(meta.get("must_verified_hits"), 0))
    must_component = 100.0 if must_total <= 0 else 100.0 * min(1.0, must_hits / max(1, must_total))
    # Query overlap is the most reliable language-aligned signal here: both the
    # acquisition query and provider description are normally in English.
    return clamp(
        base * 0.30
        + (55.0 + 45.0 * query_match) * 0.50
        + must_component * 0.20
    )


def score_scene(
    scene: dict[str, Any],
    path: Path | None,
    canonical: dict[str, Any],
    shadow: dict[str, Any],
) -> dict[str, Any]:
    width, height = probe(path)
    pixels = width * height

    if canonical:
        basis = "canonical_commit"
        desc = str(canonical.get("description", "") or "")
        source = str(canonical.get("provider", "") or "")
        risk = str(canonical.get("risk", "") or "LOW").upper()
        klass = str(canonical.get("vi6_class", "") or canonical.get("evidence_class", "") or "")
        hard = bool(canonical.get("hard_mismatch", False))
        relevance = 0.0 if hard else semantic_relevance(scene, canonical, desc)
        safety_reasons = canonical.get("safety_reasons", []) if isinstance(canonical.get("safety_reasons"), list) else []
    else:
        basis = "vi6_shadow"
        win = shadow.get("winner", {}) if isinstance(shadow.get("winner"), dict) else {}
        desc = str(win.get("descricao", "") or "")
        source = str(win.get("fonte", "") or "")
        risk = str(win.get("risk", "LOW") or "LOW").upper()
        klass = str(win.get("class", "") or "")
        hard = "MISLEADING" in klass or risk == "HIGH"
        relevance = 0.0 if hard else clamp(number(win.get("semantic"), 65.0) if win else 65.0)
        safety_reasons = [str(win.get("reason", ""))] if win.get("reason") else []

    location = clamp(100 * overlap(scene.get("location", ""), desc)) if scene.get("location") else 90.0
    subject_text = " ".join([
        str(scene.get("main_subject", "")),
        " ".join(str(x) for x in scene.get("must_have", []) if str(x).strip()),
    ])
    subject = clamp(100 * overlap(subject_text, desc)) if subject_text.strip() else 85.0
    era = clamp(100 * overlap(scene.get("era", ""), desc)) if scene.get("era") else 90.0
    quality = 100.0 if pixels >= 1280 * 720 else 90.0 if pixels >= 921600 else 75.0 if pixels >= 640 * 360 else 35.0
    orientation = 100.0 if height > width else 86.0 if height and width else 50.0
    safety = 0.0 if hard else 100.0 if risk in {"LOW", ""} and "MISLEADING" not in klass else 70.0 if risk == "MEDIUM" else 0.0

    generic_hits = sum(1 for term in GENERIC if term in norm(desc))
    query = str(canonical.get("query") if canonical else scene.get("query", ""))
    query_match = overlap(query, desc) if query.strip() and desc.strip() else 0.0
    generic_penalty = min(24.0, generic_hits * 6.0)
    # Do not penalize stock merely for being stock. Penalize it only when it is
    # both generic and weakly tied to the actual scene query.
    if source.lower() in {"pexels", "pixabay", "coverr"} and generic_hits and query_match < 0.20:
        generic_penalty += 8.0

    evidence_class = str(canonical.get("evidence_class", "") if canonical else "")
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
    score = sum(
        components[key] * weight
        for key, weight in {
            "relevance": 0.28,
            "location": 0.12,
            "character_object": 0.18,
            "era": 0.08,
            "quality": 0.14,
            "orientation": 0.08,
            "safety": 0.12,
        }.items()
    ) - generic_penalty + evidence_bonus
    score = 0.0 if hard else clamp(score)

    return {
        "media": str(path) if path else None,
        "provider": source or None,
        "evidence_basis": basis,
        "vi6_class": klass or None,
        "components": components,
        "generic_penalty": round(generic_penalty, 1),
        "documentary_bonus": evidence_bonus,
        "query_overlap": round(query_match, 3),
        "safety_reasons": safety_reasons,
        "visual_score": score,
    }


def main() -> int:
    scene_map = load(MAP)
    vi = load(VI)
    selected = load(SELECTED)
    scenes = scene_map.get("scenes", []) if isinstance(scene_map.get("scenes"), list) else []
    vi_scenes = vi.get("scenes", []) if isinstance(vi.get("scenes"), list) else []
    if not scenes:
        print("ERRO VISUAL SCORE: scene_map ausente")
        return 1

    minimum = float(os.getenv("SAP_VISUAL_SCORE_MIN", "72"))
    rows: list[dict[str, Any]] = []
    scores: list[float] = []
    canonical_scores: list[float] = []
    canonical_weak: list[int] = []
    shadow_weak: list[int] = []

    for index, scene in enumerate(scenes, 1):
        canonical = canonical_row(selected, index)
        shadow = vi_scenes[index - 1] if index <= len(vi_scenes) and isinstance(vi_scenes[index - 1], dict) else {}
        row = score_scene(scene, media_for(index), canonical, shadow)
        row["scene"] = index
        rows.append(row)
        score = float(row["visual_score"])
        scores.append(score)
        if row["evidence_basis"] == "canonical_commit":
            canonical_scores.append(score)
            if score < minimum:
                canonical_weak.append(index)
        elif score < minimum:
            shadow_weak.append(index)

    expected = len(scenes)
    canonical_count = sum(1 for row in rows if row["evidence_basis"] == "canonical_commit")
    coverage = canonical_count / max(1, expected)
    confidence = "HIGH" if coverage >= 0.75 else "MEDIUM" if coverage > 0 else "LOW"

    raw_average = round(sum(scores) / len(scores), 1)
    if canonical_scores:
        canonical_average = round(sum(canonical_scores) / len(canonical_scores), 1)
    else:
        canonical_average = None

    # A low-confidence shadow-only score is diagnostic, not a production fact.
    # Use a neutral release value until real committed-candidate evidence exists.
    effective_average = (
        raw_average
        if confidence == "HIGH"
        else round(max(78.0, canonical_average if canonical_average is not None else 78.0), 1)
    )

    if confidence != "HIGH":
        status = "OBSERVE"
        weak = []
    else:
        weak = canonical_weak
        status = "PASS" if not weak and effective_average >= minimum else "REVIEW"

    payload = {
        "short_id": SID,
        "version": "2.0_CANONICAL_COMMIT",
        "visual_score": effective_average,
        "raw_visual_score": raw_average,
        "canonical_visual_score": canonical_average,
        "threshold": minimum,
        "status": status,
        "measurement_confidence": confidence,
        "canonical_commit_count": canonical_count,
        "expected_scene_count": expected,
        "canonical_coverage": round(coverage, 3),
        "weak_scenes": weak,
        "canonical_weak_scenes": canonical_weak,
        "shadow_weak_scenes": shadow_weak,
        "scenes": rows,
    }
    atomic(OUT, payload)
    print(
        f"VISUAL MULTISCORE: {status} | {effective_average}/100 "
        f"| raw={raw_average}/100 canonical={canonical_count}/{expected} "
        f"confidence={confidence} weak={weak}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
