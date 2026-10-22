#!/usr/bin/env python3
"""ShortAuto Intelligence Layer 1.0.

Consolidated deterministic intelligence sidecar for ShortAutoPro. It does not
replace certified engines; it measures factual/narrative/visual consistency,
channel similarity, explainable quality and automation confidence at four
pipeline checkpoints: pre, scene, media and final.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", "").strip()
CHANNEL = os.getenv("SAP_CHANNEL_PROFILE", "default").strip() or "default"
R = BASE / "roteiros"
REPORTS = BASE / "reports" / "intelligence"
STATE = BASE / ".sap_state"
SCRIPT_HISTORY = STATE / f"script_history_{CHANNEL}.json"
FAILURE_KB = STATE / "failure_knowledge_base.json"
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9'-]+", re.UNICODE)
YEAR_RE = re.compile(r"\b(?:18|19|20)\d{2}\b")
CAP_RE = re.compile(r"\b[A-ZÀ-Ý][A-Za-zÀ-ÿ'-]+(?:\s+[A-ZÀ-Ý][A-Za-zÀ-ÿ'-]+){0,3}\b")
STOP = {
    "a","o","as","os","um","uma","de","da","do","das","dos","e","em","no","na",
    "nos","nas","para","por","com","que","se","the","of","and","in","to","for",
    "this","that","was","were","is","are","from","into","with","his","her",
}
STORY_ROLES = ("hook","setup","curiosity","escalation","reveal","twist","cta")
VISUAL_ROLES = ("establishing","evidence","character","location","document","atmosphere","transition")
MODERN_TERMS = {
    "smartphone","iphone","laptop","modern car","suv","led screen","social media",
    "drone","contemporary","tourist resort",
}
SOURCE_REPUTATION = {
    "wikimedia": "A", "archive": "A", "museum": "A", "government": "A", "gov": "A",
    "library": "A", "newspaper": "B", "press": "B", "reuters": "B", "ap": "B",
    "pexels": "C", "pixabay": "C", "coverr": "C", "unknown": "D",
}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def tokens(value: Any) -> set[str]:
    return {
        word.lower() for word in WORD_RE.findall(str(value or ""))
        if len(word) > 1 and word.lower() not in STOP
    }


def sentences(value: str) -> list[str]:
    return [
        " ".join(item.split()) for item in re.split(r"(?<=[.!?])\s+|\n+", value or "")
        if item.strip()
    ]


def overlap(a: Any, b: Any) -> float:
    aa, bb = tokens(a), tokens(b)
    if not aa:
        return 0.0
    return len(aa & bb) / len(aa)


def cosineish(a: Any, b: Any) -> float:
    aa, bb = tokens(a), tokens(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / math.sqrt(len(aa) * len(bb))


def clamp(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def scene_doc(sid: str) -> dict[str, Any]:
    value = load(R / f"scene_map_{sid}.json", {})
    return value if isinstance(value, dict) else {}


def scenes(sid: str) -> list[dict[str, Any]]:
    raw = scene_doc(sid).get("scenes", [])
    return [x for x in raw if isinstance(x, dict)] if isinstance(raw, list) else []


def segment(scene: dict[str, Any]) -> str:
    return str(
        scene.get("segment") or scene.get("narration") or scene.get("text") or ""
    ).strip()


def script_source(sid: str) -> tuple[str, str]:
    return read(R / f"short_{sid}.txt"), read(R / f"fonte_{sid}.txt")


def claim_engine(source: str) -> list[dict[str, Any]]:
    claims = []
    for index, sent in enumerate(sentences(source), 1):
        ts = tokens(sent)
        if len(ts) < 2:
            continue
        confidence = 1.0 if (YEAR_RE.search(sent) or len(ts) >= 5) else 0.85
        claims.append({
            "claim_id": f"claim_{index:03d}",
            "text": sent,
            "confidence": confidence,
            "evidence_type": "source_sentence",
            "locked": True,
        })
    return claims


def claim_lock(script: str, claims: list[dict[str, Any]]) -> dict[str, Any]:
    rows, unsupported = [], []
    for index, sent in enumerate(sentences(script), 1):
        ranked = sorted(
            ((overlap(sent, claim["text"]), claim) for claim in claims),
            key=lambda item: item[0], reverse=True,
        )
        score, best = ranked[0] if ranked else (0.0, None)
        locked = bool(best and score >= 0.38)
        row = {
            "script_sentence": index,
            "text": sent,
            "claim_id": best.get("claim_id") if best else None,
            "support": round(score, 3),
            "locked": locked,
        }
        rows.append(row)
        if not locked:
            unsupported.append(index)
    coverage = 100.0 * (len(rows) - len(unsupported)) / max(1, len(rows))
    return {"coverage": round(coverage, 1), "unsupported": unsupported, "sentences": rows}


def story_architecture(script: str) -> dict[str, Any]:
    sents = sentences(script)
    n = len(sents)
    if not sents:
        return {"score": 0.0, "beats": [], "status": "BLOCK"}
    beats = []
    for index, sent in enumerate(sents):
        pos = index / max(1, n - 1)
        if index == 0:
            role = "hook"
        elif pos < 0.22:
            role = "setup"
        elif pos < 0.42:
            role = "curiosity"
        elif pos < 0.62:
            role = "escalation"
        elif pos < 0.80:
            role = "reveal"
        elif index == n - 1 and any(x in sent.lower() for x in ("?", "comente", "comment", "subscribe", "inscrev")):
            role = "cta"
        elif index == n - 1:
            role = "twist"
        else:
            role = "twist"
        beats.append({"sentence": index + 1, "role": role, "text": sent})
    present = {x["role"] for x in beats}
    essential = {"hook","setup","curiosity","reveal"}
    score = clamp(70 + 30 * len(present & essential) / len(essential))
    return {"score": score, "beats": beats, "roles_present": sorted(present), "status": "PASS" if score >= 85 else "REVIEW"}


def extract_entities(script: str, source: str, scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    corpus = f"{script}\n{source}"
    names = [x.strip() for x in CAP_RE.findall(corpus) if len(x.split()) <= 4]
    years = sorted(set(YEAR_RE.findall(corpus)))
    locations = []
    for item in scene_rows:
        location = str(item.get("location") or "").strip()
        if location:
            locations.append(location)
    entities = []
    for name, count in Counter(names).most_common(40):
        entities.append({"entity": name, "type": "named_entity", "mentions": count, "aliases": []})
    return {
        "entities": entities,
        "years": years,
        "locations": sorted(set(locations)),
        "entity_count": len(entities),
    }


def entity_consistency(scene_rows: list[dict[str, Any]], registry: dict[str, Any]) -> dict[str, Any]:
    known = {x["entity"].casefold(): x["entity"] for x in registry.get("entities", [])}
    observed = defaultdict(list)
    for index, item in enumerate(scene_rows, 1):
        text = f"{segment(item)} {item.get('main_subject','')} {item.get('query','')}"
        for match in CAP_RE.findall(text):
            observed[match.casefold()].append(index)
    unknown = [
        {"entity": key, "scenes": where}
        for key, where in observed.items()
        if key not in known and len(key) > 2
    ]
    return {"status": "PASS" if not unknown else "REVIEW", "unknown_scene_entities": unknown[:30]}


def temporal_intelligence(script: str, scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sequence = []
    for index, item in enumerate(scene_rows, 1):
        found = YEAR_RE.findall(f"{segment(item)} {item.get('era','')}")
        if found:
            sequence.append({"scene": index, "year": int(found[0])})
    violations = []
    last = None
    for item in sequence:
        if last is not None and item["year"] < last and abs(item["year"] - last) > 1:
            violations.append({"scene": item["scene"], "year": item["year"], "previous_year": last})
        last = item["year"]
    script_years = [int(x) for x in YEAR_RE.findall(script)]
    return {
        "scene_timeline": sequence,
        "script_years": script_years,
        "violations": violations,
        "status": "PASS" if not violations else "REVIEW",
    }


def geographic_consistency(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    # A country and a location inside it are compatible, not contradictory.
    location_parents = {"bass strait": {"australia"}}
    locations = [(i, str(x.get("location") or "").strip()) for i, x in enumerate(scene_rows, 1)]
    locations = [(i, loc) for i, loc in locations if loc]
    mismatches = []
    for index, loc in locations:
        query = str(scene_rows[index-1].get("query") or "").casefold()
        expected = loc.casefold()
        other_locs = {
            other.casefold()
            for _, other in locations
            if other.casefold() != expected
            and other.casefold() not in location_parents.get(expected, set())
            and expected not in location_parents.get(other.casefold(), set())
        }
        wrong = [other for other in other_locs if other and other in query]
        if wrong:
            mismatches.append({"scene": index, "expected": loc, "query_contains_other_location": wrong})
    return {"locations": locations, "mismatches": mismatches, "status": "PASS" if not mismatches else "BLOCK"}


def scene_purpose(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    purposes = []
    duplicate_adjacent = []
    for index, item in enumerate(scene_rows, 1):
        role = str(item.get("narrative_role") or "").strip().lower()
        if not role:
            if index == 1:
                role = "hook"
            elif index == len(scene_rows):
                role = "ending"
            elif item.get("must_have"):
                role = "evidence"
            else:
                role = "context"
        purposes.append({"scene": index, "purpose": role})
        if index > 1 and purposes[-2]["purpose"] == role:
            duplicate_adjacent.append([index - 1, index, role])
    return {"scenes": purposes, "duplicate_adjacent": duplicate_adjacent, "status": "PASS" if len(duplicate_adjacent) <= 2 else "REVIEW"}


def information_density(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows, dead = [], []
    for index, item in enumerate(scene_rows, 1):
        words = len(WORD_RE.findall(segment(item)))
        duration = float(item.get("duration") or item.get("target_duration") or 3.0)
        density = words / max(0.5, duration)
        status = "HIGH" if density > 4.5 else "LOW" if density < 1.2 else "OK"
        rows.append({"scene": index, "words": words, "duration": round(duration,2), "words_per_second": round(density,2), "status": status})
        if duration >= 4.0 and words <= 4:
            dead.append(index)
    return {"scenes": rows, "dead_air_candidates": dead, "status": "PASS" if not dead else "REVIEW"}


def visual_role(item: dict[str, Any], index: int, count: int) -> str:
    shot = str(item.get("shot_type") or "").lower()
    must = " ".join(map(str, item.get("must_have", []) if isinstance(item.get("must_have"), list) else [])).lower()
    subject = str(item.get("main_subject") or "").lower()
    if index == 1:
        return "establishing"
    if "document" in shot or any(x in must for x in ("document","letter","paper","file","newspaper","note")):
        return "document"
    if item.get("location") and shot in {"wide","aerial"}:
        return "location"
    if shot in {"portrait","close_up"} or any(x in subject for x in ("man","woman","person","inmate","victim")):
        return "character"
    if item.get("must_have"):
        return "evidence"
    if index == count:
        return "transition"
    return "atmosphere"


def visual_system(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    shots = []
    repeated_shot_runs = []
    last = None
    run = 0
    for index, item in enumerate(scene_rows, 1):
        role = visual_role(item, index, len(scene_rows))
        shot = str(item.get("shot_type") or "medium").lower()
        shots.append(shot)
        if shot == last:
            run += 1
        else:
            run = 1
            last = shot
        if run >= 3:
            repeated_shot_runs.append({"scene": index, "shot": shot, "run": run})
        if role == "document":
            motion = "slow_zoom_detail"
        elif role == "location":
            motion = "slow_pan"
        elif role == "character":
            motion = "subtle_zoom"
        else:
            motion = "hold_or_parallax"
        rows.append({
            "scene": index, "visual_role": role, "shot": shot,
            "motion_intent": motion,
            "b_roll_plan": "hero_visual" if index == 1 else role,
        })
    diversity = 100.0 * len(set(shots)) / max(1, min(6, len(shots)))
    return {
        "scenes": rows,
        "shot_diversity_score": clamp(diversity),
        "repeated_shot_runs": repeated_shot_runs,
        "status": "PASS" if not repeated_shot_runs else "REVIEW",
    }


def semantic_visual_safety(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    def normalized_phrase(value: Any) -> str:
        return " ".join(WORD_RE.findall(str(value or "").casefold()))

    violations = []
    for index, item in enumerate(scene_rows, 1):
        spoken = f" {normalized_phrase(segment(item))} "
        query = f" {normalized_phrase(item.get('query', ''))} "
        must_values = item.get("must_have", []) if isinstance(item.get("must_have"), list) else []
        must = f" {normalized_phrase(' '.join(map(str, must_values)))} "
        avoid = item.get("avoid", []) if isinstance(item.get("avoid"), list) else []
        introduced = []
        for term in avoid:
            phrase = normalized_phrase(term)
            if (
                phrase
                and f" {phrase} " in query
                and f" {phrase} " not in spoken
                and f" {phrase} " not in must
            ):
                introduced.append(phrase)
        introduced = sorted(set(introduced))
        if introduced:
            violations.append({"scene": index, "introduced_avoid_terms": introduced})
    return {"violations": violations, "status": "PASS" if not violations else "BLOCK"}


def historical_authenticity(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    problems = []
    scored = []
    for index, item in enumerate(scene_rows, 1):
        era = str(item.get("era") or "").strip()
        query = str(item.get("query") or "").casefold()
        found_modern = sorted(term for term in MODERN_TERMS if term in query)
        score = 100.0 if not found_modern else max(0.0, 100 - 25 * len(found_modern))
        if era and found_modern:
            problems.append({"scene": index, "era": era, "modern_terms": found_modern})
        scored.append({"scene": index, "score": score, "era": era})
    average = sum(x["score"] for x in scored) / max(1, len(scored))
    return {"score": round(average,1), "problems": problems, "scenes": scored, "status": "PASS" if not problems else "REVIEW"}


def source_grade(value: Any) -> str:
    text = str(value or "unknown").casefold()
    for key, grade in SOURCE_REPUTATION.items():
        if key in text:
            return grade
    return "D"


def media_intelligence(sid: str) -> dict[str, Any]:
    media = load(R / f"media_quality_{sid}.json", {})
    scene_rows = scenes(sid)
    by_scene = {int(x.get("scene",0) or 0): x for x in scene_rows}
    rows = []
    grades = Counter()
    for asset in media.get("assets", []) if isinstance(media, dict) else []:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("file") or "")
        match = re.search(r"scene_(\d+)", name)
        number = int(match.group(1)) if match else 0
        scene = by_scene.get(number, {})
        source = scene.get("source") or scene.get("provider") or "unknown"
        grade = source_grade(source)
        grades[grade] += 1
        rows.append({
            "scene": number,
            "file": name,
            "source": source,
            "source_reputation": grade,
            "quality_pixels": int(asset.get("width") or 0) * int(asset.get("height") or 0),
            "visual_hash": asset.get("visual_hash"),
            "sha256": asset.get("sha256"),
        })
    important_low = [
        x["scene"] for x in rows if x["source_reputation"] in {"C","D"} and
        str(by_scene.get(x["scene"],{}).get("narrative_role","")).lower() in {"evidence","reveal","hook"}
    ]
    return {
        "assets": rows,
        "source_grade_counts": dict(grades),
        "important_low_reputation_scenes": important_low,
        "status": "PASS" if not important_low else "REVIEW",
    }


def smart_cache_and_aging(sid: str) -> dict[str, Any]:
    lib = load(STATE / "asset_library.json", {"assets":[]})
    assets = lib.get("assets", []) if isinstance(lib, dict) else []
    rows = []
    for item in assets if isinstance(assets, list) else []:
        if not isinstance(item, dict):
            continue
        used = int(item.get("used_count",0) or 0)
        quality = float(item.get("quality",0) or 0)
        aging = max(0.35, 1.0 - max(0, used - 1) * 0.12)
        rows.append({
            "asset_id": item.get("asset_id"),
            "used_count": used,
            "quality": quality,
            "aging_multiplier": round(aging,3),
            "reuse_priority": round(quality * aging,1),
        })
    rows.sort(key=lambda x: x["reuse_priority"], reverse=True)
    return {"cached_assets": len(rows), "top_reusable": rows[:20]}


def script_history_update(sid: str, script: str, topic: str) -> dict[str, Any]:
    history = load(SCRIPT_HISTORY, [])
    if not isinstance(history, list):
        history = []
    prior = [x for x in history if isinstance(x, dict) and x.get("short_id") != sid]
    similarities = []
    for item in prior[-100:]:
        sim = cosineish(script, item.get("script",""))
        similarities.append({"short_id": item.get("short_id"), "similarity": round(sim,3), "topic": item.get("topic","")})
    max_sim = max([x["similarity"] for x in similarities], default=0.0)
    same_topic = sum(1 for x in prior[-100:] if str(x.get("topic","")).casefold() == topic.casefold() and topic)
    entry = {
        "short_id": sid, "topic": topic, "script": script,
        "sha256": hashlib.sha256(script.encode("utf-8")).hexdigest(),
        "at": now(),
    }
    prior.append(entry)
    atomic(SCRIPT_HISTORY, prior[-100:])
    return {
        "max_similarity_last_100": round(max_sim,3),
        "most_similar": sorted(similarities, key=lambda x: x["similarity"], reverse=True)[:5],
        "topic_count_last_100": same_topic + 1,
        "similarity_status": "REVIEW" if max_sim >= 0.72 else "PASS",
        "topic_saturation": "REVIEW" if same_topic + 1 >= 6 else "PASS",
    }


def angle_generator(topic: str) -> list[str]:
    bases = ["mystery","timeline","three_clues","investigation_error","strange_document","historical_theory"]
    return [f"{topic}::{angle}" for angle in bases] if topic else bases


def hook_laboratory(script: str, topic: str) -> dict[str, Any]:
    first = sentences(script)[0] if sentences(script) else topic
    anchors = [
        ("question", f"What really happened in {topic}?" if topic else first),
        ("mystery", f"There is one detail in {topic} that still makes no sense." if topic else first),
        ("evidence", f"One piece of evidence changed everything in {topic}." if topic else first),
        ("conflict", f"The official story of {topic} leaves a major problem." if topic else first),
        ("rare_fact", f"Most people miss this detail about {topic}." if topic else first),
    ]
    variants = []
    for kind, text in anchors:
        length = len(WORD_RE.findall(text))
        novelty = 92 if kind in {"evidence","rare_fact"} else 86
        clarity = max(70, 100 - max(0, length - 14) * 3)
        curiosity = 96 if kind in {"question","mystery","conflict"} else 90
        score = round((novelty + clarity + curiosity) / 3, 1)
        variants.append({"type": kind, "text": text, "score": score})
    variants.sort(key=lambda x: x["score"], reverse=True)
    return {"variants": variants, "recommended": variants[0] if variants else None}


def ending_laboratory(script: str) -> dict[str, Any]:
    sents = sentences(script)
    first = sents[0] if sents else ""
    last = sents[-1] if sents else ""
    types = [
        {"type":"open_question","score":92 if "?" in last else 84},
        {"type":"reveal","score":90},
        {"type":"callback","score":94 if cosineish(first,last) >= 0.20 else 82},
        {"type":"cta","score":82},
        {"type":"next_video_hook","score":86},
    ]
    types.sort(key=lambda x:x["score"], reverse=True)
    return {
        "current_ending": last,
        "options": types,
        "recommended": types[0] if types else None,
        "loop_ending_ready": cosineish(first, last) >= 0.20,
    }


def content_expansion(topic: str, registry: dict[str, Any]) -> dict[str, Any]:
    nodes = [x["entity"] for x in registry.get("entities", [])[:10]]
    return {
        "series": {"enabled": True, "continuity_entities": nodes[:6]},
        "long_form": [
            {"format":"short","target_seconds":45},
            {"format":"video","target_minutes":8},
            {"format":"video","target_minutes":20},
            {"format":"community_post","target_words":180},
        ],
        "content_graph_seeds": [f"{topic} -> {x}" for x in nodes[:8]] if topic else nodes[:8],
    }


def special_scene_planning(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    plans = []
    for index, item in enumerate(scene_rows, 1):
        seg = segment(item)
        years = YEAR_RE.findall(seg)
        must = " ".join(map(str, item.get("must_have", []) if isinstance(item.get("must_have"), list) else [])).lower()
        location = str(item.get("location") or "")
        role = visual_role(item,index,len(scene_rows))
        suggestion = None
        if years and len(years) >= 2:
            suggestion = "timeline_scene"
        elif location and any(x in seg.lower() for x in ("from ","to ","travel","moved","route","rota","até ")):
            suggestion = "map_scene"
        elif role == "document":
            suggestion = "document_focus_scene"
        elif years and not item.get("must_have"):
            suggestion = "smart_typography_scene"
        if suggestion:
            plans.append({"scene":index,"suggestion":suggestion})
    return {
        "plans": plans,
        "fallback_hierarchy": ["real_footage","historical_photo","document","contextual_broll","map","typography"],
        "safe_crop_policy": {"protect_faces":True,"protect_text":True,"target_aspect":"9:16"},
    }


def editing_grammar(scene_rows: list[dict[str, Any]]) -> dict[str, Any]:
    rules = []
    previous_location = None
    previous_year = None
    for index, item in enumerate(scene_rows,1):
        location = str(item.get("location") or "")
        years = YEAR_RE.findall(f"{segment(item)} {item.get('era','')}")
        year = years[0] if years else None
        transition = "cut"
        shot = str(item.get("shot_type") or "medium")
        if location and previous_location and location != previous_location:
            transition = "location_change_establishing"
            shot = "wide"
        elif year and previous_year and year != previous_year:
            transition = "temporal_transition"
        elif visual_role(item,index,len(scene_rows)) == "evidence":
            shot = "close_up"
        rules.append({"scene":index,"transition_intent":transition,"shot_intent":shot})
        previous_location = location or previous_location
        previous_year = year or previous_year
    return {"scenes":rules}


def render_budget(scene_rows: list[dict[str, Any]], purpose: dict[str, Any]) -> dict[str, Any]:
    role_by_scene = {x["scene"]:x["purpose"] for x in purpose.get("scenes",[])}
    rows=[]
    total=0
    for index,_ in enumerate(scene_rows,1):
        role=role_by_scene.get(index,"context")
        units=3 if role in {"hook","evidence","reveal","ending"} else 2 if role in {"suspense","transition"} else 1
        rows.append({"scene":index,"budget_units":units})
        total += units
    return {"scenes":rows,"total_units":total}


def module_versions() -> dict[str, str]:
    return {
        "intelligence_layer":"1.0",
        "shortauto_brain":"1.1",
        "director_ai":"1.0",
        "visual_selection_engine":"4-certified",
        "semantic_integrity":"5.3+",
        "asset_library":"1.0",
        "repair_engine":"1.0",
        "pipeline":"CONSOLIDATION_3_0",
    }


def explainable_qa(payload: dict[str, Any]) -> dict[str, Any]:
    deductions=[]
    def deduct(points:int, reason:str):
        deductions.append({"points":-abs(points),"reason":reason})
    pre=payload.get("pre",{})
    scene=payload.get("scene",{})
    media=payload.get("media",{})
    if pre.get("claim_lock",{}).get("coverage",100)<90:
        deduct(12,"claim coverage below 90%")
    sim=pre.get("channel_memory",{}).get("max_similarity_last_100",0)
    if sim>=0.72:
        deduct(8,f"script similarity to prior video is {sim:.2f}")
    if pre.get("channel_memory",{}).get("topic_saturation")=="REVIEW":
        deduct(5,"topic saturation inside channel")
    if scene.get("temporal",{}).get("violations"):
        deduct(8,"timeline ordering conflict")
    if scene.get("geographic",{}).get("mismatches"):
        deduct(10,"geographic mismatch between scene contract and query")
    if scene.get("visual",{}).get("repeated_shot_runs"):
        deduct(5,"three or more consecutive identical shot types")
    if scene.get("semantic_visual_safety",{}).get("status")=="BLOCK":
        deduct(15,"visual query introduces avoided/unsupported concept")
    if scene.get("historical_authenticity",{}).get("score",100)<90:
        deduct(6,"historical authenticity risk")
    if media.get("important_low_reputation_scenes"):
        deduct(6,"important factual scenes use low-reputation media source")
    score=clamp(100+sum(x["points"] for x in deductions))
    return {"score":score,"deductions":deductions,"status":"PASS" if score>=90 else "REVIEW" if score>=80 else "BLOCK"}


def confidence_policy(qa: dict[str, Any], critical: list[str]) -> dict[str, Any]:
    score=float(qa.get("score",0))
    if critical or score<80:
        decision="BLOCK"
    elif score<90:
        decision="REPAIR"
    else:
        decision="CONTINUE"
    return {"confidence":score,"decision":decision,"critical":critical}


def failure_knowledge_update(sid: str, issues: list[str]) -> dict[str, Any]:
    kb=load(FAILURE_KB,[])
    if not isinstance(kb,list):
        kb=[]
    known={str(x.get("signature")):x for x in kb if isinstance(x,dict)}
    matches=[]
    for issue in sorted(set(issues)):
        sig=hashlib.sha256(issue.encode("utf-8")).hexdigest()[:16]
        if sig in known:
            known[sig]["occurrences"]=int(known[sig].get("occurrences",1))+1
            known[sig]["last_short_id"]=sid
            known[sig]["last_seen_at"]=now()
            matches.append(sig)
        else:
            known[sig]={
                "signature":sig,"error":issue,"cause":"unresolved_or_reported",
                "correction":"use matching repair action then revalidate",
                "test":"regression coverage required before certification",
                "version":"INTELLIGENCE_1.0","occurrences":1,
                "last_short_id":sid,"last_seen_at":now(),
            }
    atomic(FAILURE_KB,list(known.values())[-2000:])
    return {"known_failures":len(known),"matched_signatures":matches}


def pre_phase(sid: str) -> dict[str, Any]:
    script,source=script_source(sid)
    if not script:
        raise ValueError("roteiro ausente")
    claims=claim_engine(source)
    locked=claim_lock(script,claims)
    story=story_architecture(script)
    topic=(read(R / f"topic_{sid}.txt") or script.splitlines()[0])[:180]
    history=script_history_update(sid,script,topic)
    registry=extract_entities(script,source,[])
    hooks=hook_laboratory(script,topic)
    endings=ending_laboratory(script)
    expansion=content_expansion(topic,registry)
    payload={
        "short_id":sid,"phase":"pre","version":"INTELLIGENCE_1.0","generated_at":now(),
        "story_architecture":story,"claims":claims,"claim_lock":locked,
        "entity_registry":registry,"channel_memory":history,
        "angles":angle_generator(topic),"hook_laboratory":hooks,"ending_laboratory":endings,
        "expansion":expansion,"module_versions":module_versions(),
        "status":"PASS" if locked["coverage"]>=80 else "REVIEW",
    }
    atomic(REPORTS / f"pre_{sid}.json",payload)
    unsupported = [
        {"sentence": row["script_sentence"], "support": row["support"], "text": row["text"][:120]}
        for row in locked["sentences"] if not row["locked"]
    ]
    if unsupported:
        print("INTELLIGENCE_CLAIM_LOCK_UNSUPPORTED=" + json.dumps(unsupported, ensure_ascii=False))
    print(f"INTELLIGENCE_PRE={payload['status']} claims={len(claims)} coverage={locked['coverage']} story={story['score']}")
    return payload


def scene_phase(sid: str) -> dict[str, Any]:
    script,source=script_source(sid)
    rows=scenes(sid)
    if not rows:
        raise ValueError("scene_map ausente")
    registry=extract_entities(script,source,rows)
    purpose=scene_purpose(rows)
    payload={
        "short_id":sid,"phase":"scene","version":"INTELLIGENCE_1.0","generated_at":now(),
        "entity_registry":registry,
        "entity_consistency":entity_consistency(rows,registry),
        "temporal":temporal_intelligence(script,rows),
        "geographic":geographic_consistency(rows),
        "scene_purpose":purpose,
        "information_density":information_density(rows),
        "visual":visual_system(rows),
        "semantic_visual_safety":semantic_visual_safety(rows),
        "historical_authenticity":historical_authenticity(rows),
        "special_scene_planning":special_scene_planning(rows),
        "editing_grammar":editing_grammar(rows),
        "render_budget":render_budget(rows,purpose),
        "status":"PASS",
    }
    critical=[]
    if payload["geographic"]["status"]=="BLOCK":
        critical.append("geographic_mismatch")
    if payload["semantic_visual_safety"]["status"]=="BLOCK":
        critical.append("semantic_visual_safety_block")
    if critical:
        payload["status"]="BLOCK"
    elif any(payload[x]["status"]=="REVIEW" for x in ("entity_consistency","temporal","scene_purpose","information_density","visual","historical_authenticity")):
        payload["status"]="REVIEW"
    payload["critical"]=critical
    atomic(REPORTS / f"scene_{sid}.json",payload)
    print(f"INTELLIGENCE_SCENE={payload['status']} critical={len(critical)} shot_diversity={payload['visual']['shot_diversity_score']}")
    return payload


def media_phase(sid: str) -> dict[str, Any]:
    media=media_intelligence(sid)
    cache=smart_cache_and_aging(sid)
    payload={
        "short_id":sid,"phase":"media","version":"INTELLIGENCE_1.0","generated_at":now(),
        **media,"smart_cache":cache,
    }
    atomic(REPORTS / f"media_{sid}.json",payload)
    print(f"INTELLIGENCE_MEDIA={payload['status']} assets={len(payload['assets'])} cache={cache['cached_assets']}")
    return payload


def final_phase(sid: str) -> dict[str, Any]:
    pre=load(REPORTS / f"pre_{sid}.json",{})
    scene=load(REPORTS / f"scene_{sid}.json",{})
    media=load(REPORTS / f"media_{sid}.json",{})
    combined={"pre":pre,"scene":scene,"media":media}
    qa=explainable_qa(combined)
    critical=[]
    critical.extend(scene.get("critical",[]) if isinstance(scene,dict) else [])
    if float(pre.get("claim_lock",{}).get("coverage",100) or 0)<70:
        critical.append("claim_lock_coverage_critical")
    confidence=confidence_policy(qa,critical)
    issues=[x["reason"] for x in qa.get("deductions",[])] + critical
    failure_kb=failure_knowledge_update(sid,issues)
    manifest={
        "short_id":sid,"phase":"final","version":"INTELLIGENCE_1.0","generated_at":now(),
        "module_versions":module_versions(),
        "explainable_qa":qa,
        "confidence_automation":confidence,
        "failure_knowledge_base":failure_kb,
        "checkpoint_policy":{"universal":True,"deterministic_resume_required":True},
        "canary_policy":{"enabled":True,"important_updates_first_short_only":True},
        "quality_regression_policy":{"golden_projects_target":5,"block_score_drop_over":8},
        "provider_router_policy":["provider_primary","provider_secondary","local_or_cache"],
        "offline_capabilities":["tts","whisper","captions","media_probe","hash_qa","release_scoring"],
        "cost_performance_policy":{"prefer_free":True,"prefer_cache":True,"prefer_local_when_equivalent":True},
        "autonomous_queue":{"supported_by_existing_batch":True,"per_item_qa":True,"per_item_repair":True},
        "status":confidence["decision"],
    }
    atomic(REPORTS / f"final_{sid}.json",manifest)
    print(f"INTELLIGENCE_FINAL={manifest['status']} qa={qa['score']} deductions={len(qa['deductions'])}")
    return manifest


def run_phase(phase:str,sid:str)->dict[str,Any]:
    if phase=="pre": return pre_phase(sid)
    if phase=="scene": return scene_phase(sid)
    if phase=="media": return media_phase(sid)
    if phase=="final": return final_phase(sid)
    raise ValueError(f"fase inválida: {phase}")


def main()->int:
    parser=argparse.ArgumentParser()
    parser.add_argument("phase",choices=["pre","scene","media","final","status"])
    parser.add_argument("--short-id",default=SID)
    parser.add_argument("--enforce",action="store_true")
    args=parser.parse_args()
    sid=str(args.short_id or "").strip()
    if not sid:
        print("ERRO INTELLIGENCE LAYER: SHORT_ID vazio")
        return 1
    if args.phase=="status":
        result={phase:load(REPORTS / f"{phase}_{sid}.json",{}) for phase in ("pre","scene","media","final")}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    try:
        result=run_phase(args.phase,sid)
    except Exception as exc:
        print(f"ERRO INTELLIGENCE LAYER: {type(exc).__name__}: {exc}")
        return 1
    if args.enforce:
        status=str(result.get("status","PASS")).upper()
        if status=="BLOCK":
            return 1
        if status in {"REVIEW","REPAIR"}:
            return 20
    return 0


if __name__=="__main__":
    raise SystemExit(main())
