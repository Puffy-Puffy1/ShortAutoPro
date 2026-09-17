#!/usr/bin/env python3
"""ShortAuto Director AI — pre-media strategy, provenance and visual-intent sidecar.

This module never replaces or rewrites the certified scene/media engines. It reads
an already enriched scene map and produces a traceable plan consumed by QA,
repair and the control center.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", "").strip()
R = BASE / "roteiros"
OUTDIR = BASE / "reports" / "director_ai"
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9'-]+", re.UNICODE)
YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")
STOP = {
    "a","o","as","os","um","uma","de","da","do","das","dos","e","em","no","na",
    "nos","nas","para","por","com","que","se","the","of","and","in","to","for",
    "this","that","was","were","is","are","from","into",
}
ROLE_IMPORTANCE = {
    "hook": 0.98, "cold_open": 0.98, "opening": 0.94, "evidence": 0.93,
    "discovery": 0.90, "reveal": 0.96, "climax": 0.96, "complication": 0.88,
    "turn": 0.89, "turning_point": 0.91, "context": 0.70, "aftermath": 0.76,
    "payoff": 0.91, "conclusion": 0.82,
}
CURIOSITY_MARKERS = (
    "mas ", "porém", "so que", "só que", "entretanto", "até que", "ninguém sabia",
    "but ", "however", "yet ", "until ", "nobody knew", "strange", "mysterious",
)


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def tokens(value: Any) -> set[str]:
    return {
        item.lower() for item in WORD_RE.findall(str(value or ""))
        if len(item) > 1 and item.lower() not in STOP
    }


def overlap(a: Any, b: Any) -> float:
    aa, bb = tokens(a), tokens(b)
    return len(aa & bb) / max(1, len(aa)) if aa else 0.0


def sentences(value: str) -> list[str]:
    return [
        " ".join(item.split())
        for item in re.split(r"(?<=[.!?])\s+|\n+", value or "")
        if item.strip()
    ]


def scenes_for(sid: str) -> list[dict[str, Any]]:
    doc = load_json(R / f"scene_map_{sid}.json", {})
    raw = doc.get("scenes", []) if isinstance(doc, dict) else []
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []


def source_facts(source: str) -> list[dict[str, Any]]:
    out = []
    for index, sentence in enumerate(sentences(source), 1):
        if len(tokens(sentence)) >= 2:
            out.append({"fact_id": f"fact_{index:03d}", "text": sentence})
    return out


def scene_segment(scene: dict[str, Any]) -> str:
    return str(
        scene.get("segment") or scene.get("narration") or scene.get("text") or ""
    ).strip()


def semantic_provenance(
    scenes: list[dict[str, Any]], script: str, source: str
) -> dict[str, Any]:
    facts = source_facts(source)
    supported_tokens = tokens(script) | tokens(source)
    records = []
    unsupported_scenes = []
    for index, scene in enumerate(scenes, 1):
        segment = scene_segment(scene)
        ranked = sorted(
            ((overlap(segment, fact["text"]), fact) for fact in facts),
            key=lambda item: item[0],
            reverse=True,
        )
        score, fact = ranked[0] if ranked else (0.0, None)
        added = sorted(tokens(segment) - supported_tokens)
        delta = len(added) / max(1, len(tokens(segment)))
        supported = bool(segment) and (not added or score >= 0.12)
        record = {
            "scene": index,
            "stage": "scene_map_current",
            "source_text": fact.get("text") if fact else "",
            "generated_text": segment,
            "fact_id": fact.get("fact_id") if fact else None,
            "fact_overlap": round(score, 3),
            "added_claim_tokens": added[:30],
            "removed_claims": [],
            "semantic_delta": round(delta, 3),
            "supported": supported,
        }
        records.append(record)
        if not supported:
            unsupported_scenes.append(index)
    coverage = 100.0 * (len(records) - len(unsupported_scenes)) / max(1, len(records))
    return {
        "coverage": round(coverage, 1),
        "unsupported_scenes": unsupported_scenes,
        "records": records,
    }


def infer_period(script: str, source: str, scenes: list[dict[str, Any]]) -> str:
    explicit = [
        str(scene.get("era") or "").strip()
        for scene in scenes
        if str(scene.get("era") or "").strip()
    ]
    if explicit:
        return Counter(explicit).most_common(1)[0][0]
    years = YEAR_RE.findall(f"{script} {source}")
    return Counter(years).most_common(1)[0][0] if years else ""


def visual_intents(
    scenes: list[dict[str, Any]], script: str, source: str
) -> list[dict[str, Any]]:
    period = infer_period(script, source, scenes)
    intents = []
    for index, scene in enumerate(scenes, 1):
        role = str(scene.get("narrative_role") or "").strip().lower() or "context"
        must = scene.get("must_have", []) if isinstance(scene.get("must_have"), list) else []
        avoid = scene.get("avoid", []) if isinstance(scene.get("avoid"), list) else []
        environment = str(scene.get("environment") or scene.get("setting") or "").strip()
        location = str(scene.get("location") or "").strip()
        emotion = str(scene.get("emotion") or scene.get("mood") or "").strip() or (
            "mystery" if role in {"hook","discovery","reveal","complication"} else "neutral"
        )
        shot = str(scene.get("shot_type") or "medium").strip()
        movement = str(scene.get("movement") or "hold").strip()
        subject = str(scene.get("main_subject") or "").strip() or " ".join(map(str, must[:2])).strip()
        intent = {
            "scene": index,
            "scene_type": role,
            "objective_emotional": emotion,
            "camera": shot,
            "movement": movement,
            "subject": subject,
            "environment": environment,
            "location": location,
            "period": str(scene.get("era") or "").strip() or period,
            "must_have": [str(x).strip() for x in must if str(x).strip()],
            "avoid": [str(x).strip() for x in avoid if str(x).strip()],
            "query": str(scene.get("query") or "").strip(),
            "protected_zone": str(scene.get("protected_zone") or "center"),
        }
        intents.append(intent)
    return intents


def scene_importance(scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    lengths = [len(tokens(scene_segment(scene))) for scene in scenes]
    max_len = max(lengths or [1])
    for index, scene in enumerate(scenes, 1):
        role = str(scene.get("narrative_role") or "context").lower()
        base = ROLE_IMPORTANCE.get(role, 0.68)
        density = len(tokens(scene_segment(scene))) / max_len
        must = scene.get("must_have", []) if isinstance(scene.get("must_have"), list) else []
        evidence_bonus = min(0.08, 0.025 * len(must))
        score = max(0.0, min(1.0, 0.72 * base + 0.20 * density + evidence_bonus))
        out.append({
            "scene": index,
            "importance": round(score, 3),
            "role": role,
            "recommended_treatment": (
                "hero_visual" if score >= 0.88
                else "dedicated_visual" if score >= 0.70
                else "b_roll_or_shared_context"
            ),
        })
    return out


def curiosity_analysis(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    count = 0
    positions = []
    for index, scene in enumerate(scenes, 1):
        value = scene_segment(scene).lower()
        if "?" in value or any(marker in value for marker in CURIOSITY_MARKERS):
            count += 1
            positions.append(index)
    target = 3 if len(scenes) >= 10 else 2
    return {
        "count": count,
        "target": target,
        "status": "PASS" if count >= target else "REVIEW",
        "scenes": positions,
    }


def visual_memory(intents: list[dict[str, Any]]) -> dict[str, Any]:
    memory = []
    duplicate_pairs = []
    signatures: dict[str, int] = {}
    for item in intents:
        signature_parts = [
            str(item.get("subject") or "").casefold(),
            str(item.get("location") or "").casefold(),
            str(item.get("camera") or "").casefold(),
            str(item.get("query") or "").casefold(),
        ]
        signature = "|".join(signature_parts)
        previous = signatures.get(signature)
        if previous is not None and signature.strip("|"):
            duplicate_pairs.append([previous, item["scene"]])
        signatures[signature] = item["scene"]
        memory.append({
            "scene": item["scene"],
            "entity": item.get("subject"),
            "location": item.get("location"),
            "framing": item.get("camera"),
            "period": item.get("period"),
            "query": item.get("query"),
            "signature": signature,
        })
    diversity = 1.0 - len(duplicate_pairs) / max(1, len(intents))
    return {
        "items": memory,
        "duplicate_pairs": duplicate_pairs,
        "diversity_score": round(100.0 * max(0.0, diversity), 1),
    }


def continuity(intents: list[dict[str, Any]]) -> dict[str, Any]:
    if not intents:
        return {"visual_style_continuity": 0.0, "period_continuity": 0.0, "shot_diversity": 0.0}
    periods = [str(x.get("period") or "") for x in intents if str(x.get("period") or "")]
    emotions = [str(x.get("objective_emotional") or "") for x in intents]
    shots = [str(x.get("camera") or "") for x in intents]
    period_score = 100.0 if not periods else 100.0 * Counter(periods).most_common(1)[0][1] / len(periods)
    emotion_transitions = sum(1 for i in range(1, len(emotions)) if emotions[i] != emotions[i-1])
    style_score = max(70.0, 100.0 - max(0, emotion_transitions - len(intents)//2) * 4.0)
    shot_div = 100.0 * len(set(shots)) / max(1, min(6, len(shots)))
    return {
        "visual_style_continuity": round(min(100.0, style_score), 1),
        "period_continuity": round(period_score, 1),
        "shot_diversity": round(min(100.0, shot_div), 1),
    }


def knowledge_graph(
    intents: list[dict[str, Any]], script: str, source: str
) -> dict[str, Any]:
    nodes: dict[str, dict[str, Any]] = {}
    edges = []
    years = sorted(set(YEAR_RE.findall(f"{script} {source}")))
    for year in years:
        nodes[f"year:{year}"] = {"id": f"year:{year}", "type": "year", "label": year}
    for item in intents:
        sid = f"scene:{item['scene']:02d}"
        nodes[sid] = {"id": sid, "type": "scene", "label": f"Scene {item['scene']}"}
        for kind, raw in (
            ("subject", item.get("subject")),
            ("location", item.get("location")),
            ("period", item.get("period")),
        ):
            label = str(raw or "").strip()
            if not label:
                continue
            nid = f"{kind}:{label.casefold()}"
            nodes.setdefault(nid, {"id": nid, "type": kind, "label": label})
            edges.append({"from": sid, "to": nid, "relation": f"has_{kind}"})
        for must in item.get("must_have", []):
            label = str(must).strip()
            if not label:
                continue
            nid = f"entity:{label.casefold()}"
            nodes.setdefault(nid, {"id": nid, "type": "entity", "label": label})
            edges.append({"from": sid, "to": nid, "relation": "requires"})
    return {"nodes": list(nodes.values()), "edges": edges}


def planning_versions(
    scenes: list[dict[str, Any]], intents: list[dict[str, Any]], curiosity: dict[str, Any]
) -> dict[str, Any]:
    first = scenes[0] if scenes else {}
    hook_text = scene_segment(first)
    visual_strength = min(100.0, 65.0 + 7.0 * len((intents[0].get("must_have") if intents else []) or []))
    curiosity_score = min(100.0, 70.0 + 8.0 * curiosity.get("count", 0))
    variants = [
        {"version": "A", "hook_strategy": "direct_mystery", "hook": 88.0, "retention": curiosity_score, "visual_potential": visual_strength},
        {"version": "B", "hook_strategy": "evidence_first", "hook": 92.0 if (intents and intents[0].get("must_have")) else 84.0, "retention": min(100.0, curiosity_score + 3), "visual_potential": min(100.0, visual_strength + 2)},
        {"version": "C", "hook_strategy": "context_then_turn", "hook": 84.0, "retention": max(70.0, curiosity_score - 2), "visual_potential": min(100.0, visual_strength + 5)},
    ]
    for item in variants:
        item["score"] = round((item["hook"] + item["retention"] + item["visual_potential"]) / 3.0, 1)
        item["text_anchor"] = hook_text[:180]
    best = max(variants, key=lambda x: x["score"]) if variants else None
    return {"variants": variants, "recommended": best["version"] if best else None}


def first_frame_plan(
    intents: list[dict[str, Any]], importance: list[dict[str, Any]]
) -> dict[str, Any]:
    imp = {x["scene"]: x["importance"] for x in importance}
    candidates = []
    for item in intents[:3]:
        must = item.get("must_have", [])
        score = 55.0
        score += 22.0 * imp.get(item["scene"], 0.7)
        score += min(12.0, 4.0 * len(must))
        if item.get("camera") in {"close_up","detail","portrait","document"}:
            score += 7.0
        if item["scene"] == 1:
            score += 4.0
        candidates.append({
            "scene": item["scene"],
            "score": round(min(100.0, score), 1),
            "subject": item.get("subject"),
            "camera": item.get("camera"),
            "must_have": must,
        })
    candidates.sort(key=lambda x: x["score"], reverse=True)
    return {
        "candidates": candidates,
        "recommended_scene": candidates[0]["scene"] if candidates else None,
        "first_frame_score": candidates[0]["score"] if candidates else 0.0,
    }


def build(sid: str) -> dict[str, Any]:
    script = text(R / f"short_{sid}.txt")
    source = text(R / f"fonte_{sid}.txt")
    scenes = scenes_for(sid)
    if not scenes:
        raise ValueError(f"scene_map vazio/ausente para {sid}")
    provenance = semantic_provenance(scenes, script, source)
    intents = visual_intents(scenes, script, source)
    importance = scene_importance(scenes)
    curiosity = curiosity_analysis(scenes)
    memory = visual_memory(intents)
    cont = continuity(intents)
    graph = knowledge_graph(intents, script, source)
    versions = planning_versions(scenes, intents, curiosity)
    first_frame = first_frame_plan(intents, importance)
    issues = []
    if provenance["coverage"] < 90:
        issues.append("semantic_provenance_coverage_low")
    if memory["diversity_score"] < 85:
        issues.append("visual_memory_repetition_high")
    if cont["period_continuity"] < 85:
        issues.append("period_continuity_low")
    if curiosity["status"] != "PASS":
        issues.append("curiosity_loops_low")
    scores = [
        provenance["coverage"],
        memory["diversity_score"],
        cont["period_continuity"],
        cont["visual_style_continuity"],
        first_frame["first_frame_score"],
    ]
    director_score = round(sum(scores) / len(scores), 1)
    payload = {
        "short_id": sid,
        "version": "DIRECTOR_AI_1.0",
        "generated_at": now(),
        "status": "PASS" if not any(x in issues for x in ("semantic_provenance_coverage_low","period_continuity_low")) else "REVIEW",
        "director_score": director_score,
        "semantic_provenance": provenance,
        "visual_intent": intents,
        "visual_memory": memory,
        "continuity": cont,
        "scene_importance": importance,
        "curiosity_loops": curiosity,
        "planning_ab": versions,
        "first_frame": first_frame,
        "knowledge_graph": graph,
        "issues": issues,
        "contracts": {
            "does_not_rewrite_narration": True,
            "does_not_replace_visual_selection_v4": True,
            "sidecar_only": True,
        },
    }
    atomic_json(OUTDIR / f"director_{sid}.json", payload)
    print(
        f"SHORTAUTO_DIRECTOR_AI={payload['status']} score={director_score} "
        f"provenance={provenance['coverage']} visual_diversity={memory['diversity_score']}"
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--short-id", default=SID)
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()
    sid = str(args.short_id or "").strip()
    if not sid:
        print("ERRO DIRECTOR AI: SHORT_ID vazio")
        return 1
    try:
        report = build(sid)
    except Exception as exc:
        print(f"ERRO DIRECTOR AI: {type(exc).__name__}: {exc}")
        return 1
    if args.enforce and report["status"] != "PASS":
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
