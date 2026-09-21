#!/usr/bin/env python3
"""Visual continuity scorer and conservative repair hints."""
from __future__ import annotations
import json, math, os, re, tempfile, unicodedata
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
REPORT = BASE / "roteiros" / f"visual_continuity_{SHORT_ID}.json"


def norm(v: Any) -> str:
    s = unicodedata.normalize("NFKD", str(v or ""))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().split())


def toks(v: Any) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", norm(v)) if len(x) >= 3}


def jaccard(a: Any, b: Any) -> float:
    aa, bb = toks(a), toks(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def read() -> dict[str, Any]:
    data = json.loads(SCENE_MAP.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        raise ValueError("scene_map inválido")
    return data


def field(scene: dict[str, Any], *names: str) -> str:
    for name in names:
        value = scene.get(name)
        if isinstance(value, list):
            value = " ".join(map(str, value))
        if str(value or "").strip():
            return str(value)
    return ""


def _pair_value(prev: dict[str, Any], cur: dict[str, Any], *names: str) -> tuple[str, str, float | None]:
    left = field(prev, *names)
    right = field(cur, *names)
    if not left or not right:
        return left, right, None
    return left, right, jaccard(left, right)


def _semantic_component(similarity: float | None) -> float | None:
    """Map sparse lexical overlap to a continuity confidence score.

    Scene metadata is intentionally compact and often uses different wording
    for the same visual anchor. Missing metadata is UNKNOWN, not evidence of a
    continuity failure.
    """
    if similarity is None:
        return None
    if similarity >= 0.60:
        return 100.0
    if similarity >= 0.34:
        return 88.0
    if similarity >= 0.18:
        return 72.0
    if similarity > 0:
        return 58.0
    return 25.0


def continuity_pair(prev: dict[str, Any], cur: dict[str, Any]) -> tuple[float, dict[str, Any], list[str]]:
    dimensions = {
        "subject": _pair_value(prev, cur, "continuity_anchor", "main_subject", "entity", "entities", "must_have"),
        "location": _pair_value(prev, cur, "location", "environment", "setting"),
        "era": _pair_value(prev, cur, "era", "time_period", "time_context"),
        "event": _pair_value(prev, cur, "event", "story_event", "narrative_event"),
        "style": _pair_value(prev, cur, "visual_style", "style", "aesthetic"),
        "mood": _pair_value(prev, cur, "emotion", "mood"),
        "query": _pair_value(prev, cur, "query"),
    }
    raw = {name: item[2] for name, item in dimensions.items()}
    semantic = {
        name: _semantic_component(value)
        for name, value in raw.items()
        if name != "query"
    }

    context_candidates = [
        raw.get("subject"),
        raw.get("location"),
        raw.get("era"),
        raw.get("event"),
    ]
    same_context = any(
        value is not None and value >= 0.34
        for value in context_candidates
    )

    issues: list[str] = []
    available: dict[str, float] = {
        name: value
        for name, value in semantic.items()
        if value is not None
    }

    if same_context:
        weights = {
            "subject": 36.0,
            "location": 22.0,
            "era": 12.0,
            "event": 14.0,
            "style": 8.0,
            "mood": 8.0,
        }
        weight_sum = sum(weights[name] for name in available)
        if weight_sum:
            score = sum(available[name] * weights[name] for name in available) / weight_sum
        else:
            score = 70.0

        # Only penalize a semantic break when both sides actually provided
        # evidence for that dimension. Missing metadata remains uncertainty.
        for name, threshold in (
            ("subject", 0.18),
            ("location", 0.12),
            ("era", 0.12),
            ("event", 0.12),
        ):
            value = raw.get(name)
            if value is not None and value < threshold:
                issues.append(f"{name}_anchor_lost")
    else:
        query = raw.get("query")
        diversity = 1.0 - min(1.0, query) if query is not None else 0.5
        score = 72.0 + 16.0 * diversity

        # Healthy context changes benefit from a deliberate shot change.
        previous_shot = norm(prev.get("shot_type"))
        current_shot = norm(cur.get("shot_type"))
        if previous_shot and current_shot and previous_shot != current_shot:
            score += 6.0

    query = raw.get("query")
    previous_shot = norm(prev.get("shot_type"))
    current_shot = norm(cur.get("shot_type"))
    if (
        query is not None
        and query > 0.82
        and previous_shot
        and current_shot
        and previous_shot == current_shot
    ):
        issues.append("visual_repetition_risk")
        score -= 10.0

    score = round(max(0.0, min(100.0, score)), 1)
    components: dict[str, Any] = {}
    for name, item in dimensions.items():
        similarity = item[2]
        components[name] = None if similarity is None else round(similarity * 100, 1)
    components["known_dimensions"] = sum(1 for value in raw.values() if value is not None)
    components["same_context"] = same_context
    return score, components, issues


def quality_tier(score: float) -> str:
    if score < 50:
        return "FAIL"
    if score < 65:
        return "REVIEW"
    if score < 80:
        return "ACCEPTABLE"
    if score < 90:
        return "GOOD"
    return "EXCELLENT"


def main() -> int:
    try:
        data = read(); scenes = data["scenes"]
        if len(scenes) < 2: raise ValueError("cenas insuficientes")
        pairs=[]; scores=[]; all_issues=[]
        for i in range(1,len(scenes)):
            score, components, issues = continuity_pair(scenes[i-1], scenes[i])
            pairs.append({"from":i,"to":i+1,"score":score,"components":components,"issues":issues})
            scores.append(score); all_issues.extend(f"scene_{i+1}:{x}" for x in issues)
            scenes[i]["visual_continuity_from_previous"] = score
        avg = round(sum(scores)/len(scores),1)
        tier = quality_tier(avg)
        low_pairs = [
            item for item in pairs
            if float(item.get("score", 0) or 0) < 65
        ]
        continuity = {
            "version": "1.1",
            "score": avg,
            "status": tier,
            "blocking": tier == "FAIL",
            "low_pairs": [f"{item['from']}->{item['to']}" for item in low_pairs],
        }
        data["visual_continuity"] = continuity
        atomic(SCENE_MAP,data)
        atomic(REPORT,{
            "short_id":SHORT_ID,
            "version":"1.1",
            "visual_continuity_score":avg,
            "status":tier,
            "blocking": tier == "FAIL",
            "issues":all_issues,
            "low_pairs": low_pairs,
            "pairs":pairs,
        })
    except Exception as exc:
        print(f"ERRO VISUAL CONTINUITY: {exc}"); return 1
    print(f"VISUAL CONTINUITY SCORE: {avg}/100")
    print(f"VISUAL CONTINUITY: {tier}")
    return 1 if tier == "FAIL" else 0

if __name__ == "__main__": raise SystemExit(main())
