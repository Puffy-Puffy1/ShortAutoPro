#!/usr/bin/env python3
"""Visual continuity analysis for planning and selected production media.

The planning pass enriches the scene-map contract before acquisition. The
selected pass runs after Stage 6 media selection and scores the actual sequence
using the approved scene context, VI6 winner metadata, per-scene visual score,
and Media Master Gate fingerprints. It never invents evidence or rewrites
narration.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
R = BASE / "roteiros"
SCENE_MAP = R / f"scene_map_{SHORT_ID}.json"
REPORT = R / f"visual_continuity_{SHORT_ID}.json"
VI6 = R / f"visual_intelligence_6_{SHORT_ID}.json"
VISUAL_SCORE = R / f"visual_score_{SHORT_ID}.json"
MEDIA_QUALITY = R / f"media_quality_{SHORT_ID}.json"


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.casefold().split())


def toks(value: Any) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", norm(value)) if len(x) >= 3}


def jaccard(first: Any, second: Any) -> float:
    a, b = toks(first), toks(second)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def coverage(required: Any, observed: Any) -> float:
    req, obs = toks(required), toks(observed)
    if not req:
        return 1.0
    return len(req & obs) / len(req)


def safe_num(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return result if math.isfinite(result) else default


def clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


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
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def load(path: Path, *, required: bool = False) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        if required:
            raise
        return {}
    if not isinstance(data, dict):
        if required:
            raise ValueError(f"{path.name} precisa ser objeto JSON")
        return {}
    return data


def field(scene: dict[str, Any], *names: str) -> str:
    for name in names:
        value = scene.get(name)
        if isinstance(value, list):
            value = " ".join(map(str, value))
        if str(value or "").strip():
            return str(value)
    return ""


def scene_number(scene: dict[str, Any], fallback: int) -> int:
    for key in ("scene", "scene_id", "id", "number"):
        try:
            value = int(scene.get(key))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return fallback


def quality_band(score: float) -> str:
    if score < 50:
        return "FAIL"
    if score < 65:
        return "REVIEW"
    if score < 80:
        return "ACCEPTABLE"
    if score < 90:
        return "GOOD"
    return "EXCELLENT"


def narrative_context(scene: dict[str, Any]) -> dict[str, str]:
    return {
        "entity": field(scene, "main_subject", "subject", "character", "object", "must_have"),
        "location": field(scene, "location", "environment", "place"),
        "time": field(scene, "era", "time_period", "period"),
        "event": field(scene, "event", "segment", "text"),
        "aesthetic": field(scene, "visual_style", "style", "visual_mode"),
        "shot": field(scene, "shot_type"),
        "query": field(scene, "query"),
    }


def planning_pair(prev: dict[str, Any], cur: dict[str, Any]) -> tuple[float, dict[str, float], list[str]]:
    pctx, cctx = narrative_context(prev), narrative_context(cur)
    subject = jaccard(pctx["entity"], cctx["entity"])
    location = jaccard(pctx["location"], cctx["location"])
    era = jaccard(pctx["time"], cctx["time"])
    event = jaccard(pctx["event"], cctx["event"])
    query = jaccard(pctx["query"], cctx["query"])
    same_context = max(subject, location, era, event) >= 0.34

    if same_context:
        score = 36 * subject + 22 * location + 12 * era + 20 * event + 10 * min(query, 0.75) / 0.75
    else:
        diversity = 1.0 - min(1.0, query)
        shot_change = norm(pctx["shot"]) != norm(cctx["shot"])
        score = 72 + 18 * diversity + 10 * float(shot_change)

    issues: list[str] = []
    if same_context and subject < 0.20:
        issues.append("subject_anchor_lost")
    if same_context and (pctx["location"] or cctx["location"]) and location < 0.12:
        issues.append("location_anchor_lost")
    if same_context and (pctx["time"] or cctx["time"]) and era < 0.12:
        issues.append("time_anchor_lost")
    if query > 0.82 and norm(pctx["shot"]) == norm(cctx["shot"]):
        issues.append("visual_repetition_risk")

    return clamp(score), {
        "entity_persistence": round(subject * 100, 1),
        "location_persistence": round(location * 100, 1),
        "time_persistence": round(era * 100, 1),
        "event_progression": round(event * 100, 1),
        "query_similarity": round(query * 100, 1),
    }, issues


def _indexed_rows(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = data.get("scenes", []) if isinstance(data.get("scenes"), list) else []
    result: dict[int, dict[str, Any]] = {}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            continue
        number = scene_number(row, index)
        result[number] = row
    return result


def _asset_rows(data: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = data.get("assets", []) if isinstance(data.get("assets"), list) else []
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        match = re.search(r"scene_(\d+)", str(row.get("file", "")), flags=re.I)
        if not match:
            continue
        result[int(match.group(1))] = row
    return result


def hash_similarity(first: str, second: str) -> float:
    if not first or not second or len(first) != len(second):
        return 0.0
    return sum(a == b for a, b in zip(first, second)) / len(first)


def selected_pair(
    prev_scene: dict[str, Any],
    cur_scene: dict[str, Any],
    prev_vi: dict[str, Any],
    cur_vi: dict[str, Any],
    prev_score: dict[str, Any],
    cur_score: dict[str, Any],
    prev_asset: dict[str, Any],
    cur_asset: dict[str, Any],
    editorial_scenes: set[int],
    prev_number: int,
    cur_number: int,
) -> tuple[float, dict[str, float], list[str]]:
    pctx, cctx = narrative_context(prev_scene), narrative_context(cur_scene)
    narrative_entity = jaccard(pctx["entity"], cctx["entity"])
    narrative_location = jaccard(pctx["location"], cctx["location"])
    narrative_time = jaccard(pctx["time"], cctx["time"])
    narrative_event = jaccard(pctx["event"], cctx["event"])
    same_context = max(narrative_entity, narrative_location, narrative_time, narrative_event) >= 0.34

    pwin = prev_vi.get("winner", {}) if isinstance(prev_vi.get("winner"), dict) else {}
    cwin = cur_vi.get("winner", {}) if isinstance(cur_vi.get("winner"), dict) else {}
    pdesc, cdesc = str(pwin.get("descricao", "")), str(cwin.get("descricao", ""))
    selected_similarity = jaccard(pdesc, cdesc)

    cur_required = " ".join(x for x in (cctx["entity"], cctx["location"], cctx["time"], cctx["event"]) if x)
    cur_alignment = coverage(cur_required, cdesc) if cdesc else 0.0
    prev_required = " ".join(x for x in (pctx["entity"], pctx["location"], pctx["time"], pctx["event"]) if x)
    prev_alignment = coverage(prev_required, pdesc) if pdesc else 0.0

    p_visual = safe_num(prev_score.get("visual_score"), 65.0)
    c_visual = safe_num(cur_score.get("visual_score"), 65.0)
    per_scene_quality = (p_visual + c_visual) / 2.0

    exact_duplicate = bool(
        prev_asset.get("sha256")
        and prev_asset.get("sha256") == cur_asset.get("sha256")
    )
    near_similarity = hash_similarity(
        str(prev_asset.get("visual_hash", "")),
        str(cur_asset.get("visual_hash", "")),
    )
    near_duplicate = near_similarity >= 0.985

    shot_change = norm(pctx["shot"]) != norm(cctx["shot"])
    source_change = norm(pwin.get("fonte")) != norm(cwin.get("fonte"))
    selected_progression = (1.0 - min(1.0, selected_similarity)) if not same_context else selected_similarity

    if same_context:
        anchor_quality = 100.0 * ((prev_alignment + cur_alignment) / 2.0)
        progression = 100.0 * selected_progression
        score = 0.46 * anchor_quality + 0.34 * per_scene_quality + 0.12 * progression + 8.0 * float(shot_change)
    else:
        diversity = 100.0 * (1.0 - min(1.0, selected_similarity))
        alignment = 100.0 * ((prev_alignment + cur_alignment) / 2.0)
        score = 0.42 * per_scene_quality + 0.28 * diversity + 0.24 * alignment + 6.0 * float(shot_change or source_change)

    issues: list[str] = []
    if exact_duplicate:
        issues.append("exact_adjacent_duplicate")
        score -= 45
    elif near_duplicate:
        issues.append("near_adjacent_duplicate")
        score -= 28

    if cur_number in editorial_scenes:
        issues.append("current_editorial_reuse")
        score -= 12
    if prev_number in editorial_scenes and cur_number in editorial_scenes:
        issues.append("consecutive_editorial_reuse")
        score -= 16

    if same_context and cur_alignment < 0.22:
        issues.append("selected_asset_lost_narrative_anchor")
        score -= 12
    if same_context and selected_similarity < 0.08:
        issues.append("selected_sequence_disconnect")
        score -= 8
    if not same_context and selected_similarity > 0.82:
        issues.append("selected_sequence_stagnation")
        score -= 10
    if p_visual < 72 or c_visual < 72:
        issues.append("weak_selected_scene")

    return clamp(score), {
        "selected_asset_alignment": round(cur_alignment * 100, 1),
        "previous_asset_alignment": round(prev_alignment * 100, 1),
        "selected_description_similarity": round(selected_similarity * 100, 1),
        "adjacent_visual_hash_similarity": round(near_similarity * 100, 1),
        "per_scene_quality": round(per_scene_quality, 1),
        "narrative_entity_persistence": round(narrative_entity * 100, 1),
        "narrative_location_persistence": round(narrative_location * 100, 1),
        "narrative_time_persistence": round(narrative_time * 100, 1),
        "visual_progression": round(100 * selected_progression, 1),
    }, issues


def choose_repair_scene(
    prev_number: int,
    cur_number: int,
    prev_score: dict[str, Any],
    cur_score: dict[str, Any],
    issues: list[str],
) -> int:
    pscore = safe_num(prev_score.get("visual_score"), 75.0)
    cscore = safe_num(cur_score.get("visual_score"), 75.0)
    if "exact_adjacent_duplicate" in issues or "near_adjacent_duplicate" in issues:
        return cur_number
    if pscore + 5 < cscore:
        return prev_number
    return cur_number


def planning_analysis(data: dict[str, Any]) -> dict[str, Any]:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 2:
        raise ValueError("scene_map sem cenas suficientes")

    pairs: list[dict[str, Any]] = []
    scores: list[float] = []
    issues_all: list[str] = []
    for index in range(1, len(scenes)):
        prev, cur = scenes[index - 1], scenes[index]
        if not isinstance(prev, dict) or not isinstance(cur, dict):
            raise ValueError("scene_map contém cena inválida")
        score, components, issues = planning_pair(prev, cur)
        current_number = scene_number(cur, index + 1)
        pairs.append({
            "from": scene_number(prev, index),
            "to": current_number,
            "score": score,
            "quality": quality_band(score),
            "components": components,
            "issues": issues,
        })
        scores.append(score)
        issues_all.extend(f"scene_{current_number}:{item}" for item in issues)
        cur["visual_continuity_from_previous"] = score
        cur["previous_scene_context"] = narrative_context(prev)
        cur["current_scene_context"] = narrative_context(cur)
        cur["continuity_anchor"] = {
            "entity": field(cur, "main_subject", "must_have"),
            "location": field(cur, "location", "environment"),
            "time": field(cur, "era", "time_period"),
        }

    average = round(sum(scores) / len(scores), 1)
    status = quality_band(average)
    data["visual_continuity"] = {
        "version": "2.0",
        "mode": "PLANNING",
        "score": average,
        "status": status,
    }
    atomic(SCENE_MAP, data)
    return {
        "short_id": SHORT_ID,
        "version": "2.0",
        "mode": "PLANNING",
        "visual_continuity_score": average,
        "status": status,
        "issues": issues_all,
        "repair_scenes": [],
        "pairs": pairs,
    }


def selected_analysis(data: dict[str, Any]) -> dict[str, Any]:
    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or len(scenes) < 2:
        raise ValueError("scene_map sem cenas suficientes")

    vi_rows = _indexed_rows(load(VI6))
    score_rows = _indexed_rows(load(VISUAL_SCORE))
    media = load(MEDIA_QUALITY, required=True)
    asset_rows = _asset_rows(media)
    editorial_scenes = {
        int(x)
        for x in media.get("editorial_reuse_scenes", [])
        if str(x).isdigit()
    }

    expected_numbers = [scene_number(x, index) for index, x in enumerate(scenes, 1) if isinstance(x, dict)]
    missing_assets = [number for number in expected_numbers if number not in asset_rows]
    missing_scores = [number for number in expected_numbers if number not in score_rows]
    missing_vi6 = [number for number in expected_numbers if number not in vi_rows]
    if str(media.get("status", "")).upper() != "PASS":
        raise ValueError("media_quality ainda não está PASS")
    if missing_assets:
        raise ValueError("media_quality sem assets: " + ",".join(map(str, missing_assets)))
    if missing_scores:
        raise ValueError("visual_score sem cenas: " + ",".join(map(str, missing_scores)))
    if missing_vi6:
        raise ValueError("visual_intelligence_6 sem cenas: " + ",".join(map(str, missing_vi6)))

    pairs: list[dict[str, Any]] = []
    scores: list[float] = []
    issues_all: list[str] = []
    repair: set[int] = set()
    for index in range(1, len(scenes)):
        prev, cur = scenes[index - 1], scenes[index]
        if not isinstance(prev, dict) or not isinstance(cur, dict):
            raise ValueError("scene_map contém cena inválida")
        prev_number = scene_number(prev, index)
        cur_number = scene_number(cur, index + 1)
        score, components, issues = selected_pair(
            prev,
            cur,
            vi_rows.get(prev_number, {}),
            vi_rows.get(cur_number, {}),
            score_rows.get(prev_number, {}),
            score_rows.get(cur_number, {}),
            asset_rows.get(prev_number, {}),
            asset_rows.get(cur_number, {}),
            editorial_scenes,
            prev_number,
            cur_number,
        )
        band = quality_band(score)
        pair = {
            "from": prev_number,
            "to": cur_number,
            "score": score,
            "quality": band,
            "components": components,
            "issues": issues,
        }
        pairs.append(pair)
        scores.append(score)
        issues_all.extend(f"scene_{cur_number}:{item}" for item in issues)

        blocking_pair = any(
            item in {
                "exact_adjacent_duplicate",
                "near_adjacent_duplicate",
                "consecutive_editorial_reuse",
                "selected_asset_lost_narrative_anchor",
            }
            for item in issues
        )
        if score < 65 or blocking_pair:
            repair.add(
                choose_repair_scene(
                    prev_number,
                    cur_number,
                    score_rows.get(prev_number, {}),
                    score_rows.get(cur_number, {}),
                    issues,
                )
            )

    average = round(sum(scores) / len(scores), 1)
    weakest = min(scores) if scores else 0.0
    status = quality_band(average)
    if weakest < 35:
        status = "FAIL"
    elif repair and status in {"ACCEPTABLE", "GOOD", "EXCELLENT"}:
        status = "REVIEW"

    previous = load(REPORT)
    planning_score = previous.get("visual_continuity_score") if previous.get("mode") == "PLANNING" else previous.get("planning_score")
    return {
        "short_id": SHORT_ID,
        "version": "2.0",
        "mode": "SELECTED_MEDIA",
        "planning_score": planning_score,
        "visual_continuity_score": average,
        "weakest_pair_score": round(weakest, 1),
        "status": status,
        "quality_scale": {
            "0-49": "FAIL",
            "50-64": "REVIEW",
            "65-79": "ACCEPTABLE",
            "80-89": "GOOD",
            "90-100": "EXCELLENT",
        },
        "issues": issues_all,
        "repair_scenes": sorted(repair),
        "pairs": pairs,
        "inputs": {
            "media_gate_status": media.get("status"),
            "asset_count": len(asset_rows),
            "visual_score_status": load(VISUAL_SCORE).get("status"),
            "vi6_scene_count": len(vi_rows),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected", action="store_true", help="score actual Stage 6 selected media")
    args = parser.parse_args()

    try:
        data = load(SCENE_MAP, required=True)
        payload = selected_analysis(data) if args.selected else planning_analysis(data)
        atomic(REPORT, payload)
    except Exception as exc:
        print(f"ERRO VISUAL CONTINUITY: {type(exc).__name__}: {exc}")
        return 1

    score = payload["visual_continuity_score"]
    status = payload["status"]
    mode = payload["mode"]
    repair = payload.get("repair_scenes", [])
    print(f"VISUAL CONTINUITY SCORE: {score}/100")
    print(f"VISUAL CONTINUITY: {status} | mode={mode}")
    if repair:
        print("VISUAL CONTINUITY REPAIR CANDIDATES: " + ",".join(map(str, repair)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
