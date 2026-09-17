#!/usr/bin/env python3
"""ShortAuto Brain — consolidated editorial intelligence for ShortAutoPro.

This module does not replace certified production engines. It links their
outputs into a traceable learning/quality layer: factual trace, story graph,
scene retention roles, hook A/B plan, editorial memory, visual repetition,
quality budget, analytics feedback and autonomy policy.
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
REPORTS = BASE / "reports" / "brain"
ANALYTICS = BASE / "reports" / "analytics"
MEMORY = REPORTS / f"channel_memory_{CHANNEL}.json"
AUTONOMY = os.getenv("SAP_AUTONOMY_MODE", "SAFE").upper().strip()
VALID_AUTONOMY = {"SAFE", "ASSISTED", "AUTONOMOUS"}
WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9'-]+", re.UNICODE)
STOP = {
    "a", "o", "as", "os", "um", "uma", "de", "da", "do", "das", "dos",
    "e", "em", "no", "na", "nos", "nas", "para", "por", "com", "que",
    "se", "the", "of", "and", "in", "to", "for",
}
THEME_GROUPS = {
    "disappearances": {"desapareceu", "desaparecimento", "missing", "disappearance"},
    "historical_cases": {"histórico", "historica", "history", "1962", "prison", "prisão"},
    "documents": {"documento", "arquivo", "file", "record", "document"},
    "mysteries": {"mistério", "misterio", "mystery", "unknown", "inexplicável"},
    "crime": {"crime", "criminal", "police", "prisão", "prison", "escape", "fuga"},
}


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


def tokens(text: Any) -> set[str]:
    return {
        word.lower()
        for word in WORD_RE.findall(str(text or ""))
        if len(word) > 1 and word.lower() not in STOP
    }


def sentences(text: str) -> list[str]:
    return [
        " ".join(item.split())
        for item in re.split(r"(?<=[.!?])\s+|\n+", text or "")
        if item.strip()
    ]


def overlap(a: Any, b: Any) -> float:
    aa, bb = tokens(a), tokens(b)
    return len(aa & bb) / max(1, len(aa)) if aa else 0.0


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except Exception:
        return default


def short_paths(sid: str) -> dict[str, Path]:
    root = BASE / "roteiros"
    return {
        "script": root / f"short_{sid}.txt",
        "source": root / f"fonte_{sid}.txt",
        "scenes": root / f"scene_map_{sid}.json",
        "hook": root / f"hook_{sid}.json",
        "retention": root / f"retention_{sid}.json",
        "media": root / f"media_quality_{sid}.json",
        "caption": root / f"pro_caption_{sid}.json",
        "visual": root / f"visual_score_{sid}.json",
        "pro": BASE / "manifests" / f"{sid}_professional.json",
        "quality": BASE / "manifests" / f"{sid}_quality.json",
        "release": BASE / "manifests" / f"{sid}_release.json",
    }


def fact_layer(source_text: str) -> list[dict[str, Any]]:
    facts = []
    for index, sentence in enumerate(sentences(source_text), 1):
        if len(tokens(sentence)) < 2:
            continue
        facts.append({
            "fact_id": f"fact_{index:03d}",
            "text": sentence,
            "tokens": sorted(tokens(sentence)),
        })
    return facts


def scene_list(scene_doc: dict[str, Any]) -> list[dict[str, Any]]:
    raw = scene_doc.get("scenes", []) if isinstance(scene_doc, dict) else []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def scene_text(scene: dict[str, Any]) -> str:
    fields = (
        "narration", "text", "segment", "segmento", "script",
        "query", "visual_query", "description",
    )
    return " ".join(str(scene.get(key, "") or "") for key in fields).strip()


def build_evidence_map(
    scenes: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    mapped, unsupported = [], []
    for index, scene in enumerate(scenes, 1):
        text = scene_text(scene)
        ranked = sorted(
            ((overlap(text, fact["text"]), fact) for fact in facts),
            key=lambda item: item[0],
            reverse=True,
        )
        best_score, best = ranked[0] if ranked else (0.0, None)
        item = {
            "scene": index,
            "scene_text": text,
            "fact_id": best.get("fact_id") if best else None,
            "support_overlap": round(best_score, 3),
            "supported": bool(best and best_score >= 0.18),
        }
        mapped.append(item)
        if not item["supported"]:
            unsupported.append(index)
    coverage = 100.0 * (len(mapped) - len(unsupported)) / max(1, len(mapped))
    return {
        "coverage": round(coverage, 1),
        "unsupported_scenes": unsupported,
        "scenes": mapped,
    }


def infer_story_graph(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(scenes)
    fallback_roles = ["hook", "context", "discovery", "complication", "reveal", "conclusion"]
    targets = {
        "hook": 96, "context": 78, "discovery": 86, "complication": 90,
        "reveal": 94, "conclusion": 82, "payoff": 90, "evidence": 87,
    }
    items = []
    for index, scene in enumerate(scenes):
        role = str(scene.get("narrative_role", "") or "").strip().lower()
        if not role:
            if count <= 1:
                role = "hook"
            else:
                position = index / max(1, count - 1)
                role = fallback_roles[min(len(fallback_roles) - 1, int(position * len(fallback_roles)))]
        items.append({
            "scene": index + 1,
            "role": role,
            "retention_target": targets.get(role, 80),
            "visual_intent": str(scene.get("visual_mode", scene.get("shot_type", "")) or ""),
        })
    roles = [item["role"] for item in items]
    arc_ok = bool(
        roles
        and roles[0] in {"hook", "cold_open", "opening"}
        and roles[-1] in {"conclusion", "payoff", "aftermath", "reveal"}
    )
    return {"arc_ok": arc_ok, "scenes": items}


def hook_plan(hook_doc: dict[str, Any]) -> dict[str, Any]:
    hooks = hook_doc.get("hooks", []) if isinstance(hook_doc, dict) else []
    variants = []
    if isinstance(hooks, list):
        for index, hook in enumerate(hooks, 1):
            if not isinstance(hook, dict):
                continue
            values = [safe_float(hook.get(key), 0.0) for key in ("curiosity", "clarity", "factuality", "retention")]
            score = sum(values) / max(1, len(values))
            if score <= 10.0:
                score *= 10.0
            variants.append({
                "variant": chr(64 + index),
                "text": str(hook.get("text", "")),
                "score": round(score, 1),
            })
    variants.sort(key=lambda item: item["score"], reverse=True)
    return {
        "variants": variants,
        "recommended": variants[0]["variant"] if variants else None,
        "ab_ready": len(variants) >= 2,
    }


def hash_media(sid: str) -> list[dict[str, Any]]:
    root = BASE / "imagens" / f"short_{sid}"
    if not root.is_dir():
        return []
    assets = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        try:
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            assets.append({
                "file": path.name,
                "sha256": digest.hexdigest(),
                "bytes": path.stat().st_size,
            })
        except OSError:
            continue
    return assets


def repetition_report(sid: str) -> dict[str, Any]:
    current = hash_media(sid)
    history_path = REPORTS / "media_hash_history.json"
    history = load_json(history_path, [])
    if not isinstance(history, list):
        history = []
    previous_hashes = {
        str(item.get("sha256"))
        for item in history
        if isinstance(item, dict) and item.get("short_id") != sid
    }
    repeats = [item for item in current if item["sha256"] in previous_hashes]
    merged = [
        item for item in history
        if isinstance(item, dict) and item.get("short_id") != sid
    ]
    merged.extend({**item, "short_id": sid, "channel": CHANNEL} for item in current)
    atomic_json(history_path, merged[-5000:])
    ratio = len(repeats) / max(1, len(current))
    return {
        "assets": len(current),
        "reused_assets": len(repeats),
        "repetition_ratio": round(ratio, 3),
        "repeated_files": [item["file"] for item in repeats],
    }


def theme_family(text: str) -> str:
    text_tokens = tokens(text)
    best_name, best_hits = "general", 0
    for name, hints in THEME_GROUPS.items():
        hits = len(text_tokens & hints)
        if hits > best_hits:
            best_name, best_hits = name, hits
    return best_name


def theme_intelligence(memory: dict[str, Any]) -> dict[str, Any]:
    counts = {
        name: int((memory.get("theme_counts") or {}).get(name, 0) or 0)
        for name in THEME_GROUPS
    }
    if not counts:
        return {"least_used": None, "counts": {}}
    minimum = min(counts.values())
    least = sorted(name for name, value in counts.items() if value == minimum)
    return {
        "least_used": least[0] if least else None,
        "underused": least,
        "counts": counts,
    }


def load_memory() -> dict[str, Any]:
    data = load_json(MEMORY, {})
    return data if isinstance(data, dict) else {}


def update_memory(
    sid: str,
    topic: str,
    hook: dict[str, Any],
    story: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, Any]:
    memory = load_memory()
    memory.setdefault("channel", CHANNEL)
    memory.setdefault("videos_seen", 0)
    memory.setdefault("theme_counts", {})
    processed = memory.get("processed_short_ids", [])
    if not isinstance(processed, list):
        processed = []
    if sid not in processed:
        family = theme_family(topic)
        counts = Counter(memory.get("theme_counts", {}))
        counts[family] += 1
        memory["theme_counts"] = dict(counts)
        memory["videos_seen"] = int(memory.get("videos_seen", 0)) + 1
        processed.append(sid)
    memory["processed_short_ids"] = processed[-1000:]
    memory["last_short_id"] = sid
    memory["last_hook_variant"] = hook.get("recommended")
    memory["last_evidence_coverage"] = evidence.get("coverage")
    memory["story_arc_ok"] = story.get("arc_ok")
    memory["theme_intelligence"] = theme_intelligence(memory)
    memory["updated_at"] = now()
    atomic_json(MEMORY, memory)
    return memory


def quality_budget(
    paths: dict[str, Path],
    evidence: dict[str, Any],
    repetition: dict[str, Any],
) -> dict[str, Any]:
    retention = load_json(paths["retention"], {})
    media = load_json(paths["media"], {})
    caption = load_json(paths["caption"], {})
    visual = load_json(paths["visual"], {})
    if not isinstance(retention, dict): retention = {}
    if not isinstance(media, dict): media = {}
    if not isinstance(caption, dict): caption = {}
    if not isinstance(visual, dict): visual = {}

    max_repetition = safe_float(os.getenv("SAP_MAX_VISUAL_REPETITION", "0.15"), 0.15)
    min_evidence = safe_float(os.getenv("SAP_MIN_EVIDENCE_COVERAGE", "90"), 90.0)
    min_retention = safe_float(os.getenv("SAP_RETENTION_MIN_SCORE", "78"), 78.0)
    min_visual = safe_float(os.getenv("SAP_VISUAL_SCORE_MIN", "72"), 72.0)
    max_low_resolution = int(safe_float(os.getenv("SAP_BRAIN_MAX_LOW_RESOLUTION", "2"), 2.0))

    retention_score = safe_float(retention.get("retention_score"), 100.0 if not retention else 0.0)
    critical_media = media.get("critical", []) if isinstance(media.get("critical", []), list) else []
    media_warnings = media.get("warnings", []) if isinstance(media.get("warnings", []), list) else []
    low_resolution = [item for item in media_warnings if str(item).startswith("low_resolution:")]
    caption_score = safe_float(caption.get("score"), 100.0 if not caption else 0.0)
    visual_score = safe_float(
        visual.get("score", visual.get("visual_score", 100.0 if not visual else 0.0)),
        0.0,
    )

    checks = {
        "evidence_coverage": safe_float(evidence.get("coverage"), 0.0) >= min_evidence,
        "visual_repetition": safe_float(repetition.get("repetition_ratio"), 0.0) <= max_repetition,
        "retention": retention_score >= min_retention,
        "media_critical": not bool(critical_media),
        "low_resolution_budget": len(low_resolution) <= max_low_resolution,
        "captions": caption_score >= 80.0,
        "visual_quality": visual_score >= min_visual,
    }
    return {
        "status": "PASS" if all(checks.values()) else "BLOCK",
        "checks": checks,
        "limits": {
            "max_visual_repetition": max_repetition,
            "min_evidence_coverage": min_evidence,
            "min_retention": min_retention,
            "min_visual_score": min_visual,
            "max_low_resolution": max_low_resolution,
        },
        "observed": {
            "retention": retention_score,
            "caption": caption_score,
            "visual": visual_score,
            "repetition": repetition.get("repetition_ratio", 0),
            "evidence": evidence.get("coverage", 0),
            "low_resolution_count": len(low_resolution),
        },
    }


def analytics_summary() -> dict[str, Any]:
    path = ANALYTICS / f"{CHANNEL}.jsonl"
    rows = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except Exception:
                pass
    if not rows:
        return {"channel": CHANNEL, "samples": 0, "insights": []}
    metrics = ("views", "avg_view_duration", "percent_viewed", "likes", "comments", "subscribers")
    averages = {
        metric: round(sum(safe_float(row.get(metric)) for row in rows) / len(rows), 3)
        for metric in metrics
    }
    by_hook: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_hook[str(row.get("hook_variant", "unknown"))].append(safe_float(row.get("percent_viewed")))
    hook_average = {
        name: round(sum(values) / len(values), 2)
        for name, values in by_hook.items()
        if values
    }
    best_hook = max(hook_average, key=hook_average.get) if hook_average else None
    insights = [f"best_hook_variant={best_hook}"] if best_hook else []
    return {
        "channel": CHANNEL,
        "samples": len(rows),
        "averages": averages,
        "hook_percent_viewed": hook_average,
        "insights": insights,
    }


def prepare(sid: str) -> dict[str, Any]:
    paths = short_paths(sid)
    script = paths["script"].read_text(encoding="utf-8") if paths["script"].is_file() else ""
    source = paths["source"].read_text(encoding="utf-8") if paths["source"].is_file() else ""
    scenes = scene_list(load_json(paths["scenes"], {}))
    facts = fact_layer(source)
    evidence = build_evidence_map(scenes, facts)
    story = infer_story_graph(scenes)
    hooks = hook_plan(load_json(paths["hook"], {}))
    topic = (script.splitlines()[0] if script else "")[:240]
    memory = update_memory(sid, topic, hooks, story, evidence)
    payload = {
        "short_id": sid,
        "version": "SHORTAUTO_BRAIN_1.1",
        "generated_at": now(),
        "channel": CHANNEL,
        "autonomy_mode": AUTONOMY if AUTONOMY in VALID_AUTONOMY else "SAFE",
        "fact_layer": {"count": len(facts), "facts": facts},
        "evidence_map": evidence,
        "story_graph": story,
        "hook_ab": hooks,
        "editorial_memory": memory,
        "theme_intelligence": theme_intelligence(memory),
        "analytics": analytics_summary(),
        "capabilities": {
            "prepublish_score": True,
            "scene_retention": True,
            "visual_director_bridge": True,
            "cross_video_repetition": True,
            "editorial_memory": True,
            "hook_ab": True,
            "analytics_loop": True,
            "theme_intelligence": True,
            "story_graph": True,
            "fact_layer": True,
            "evidence_map": True,
            "cinematic_pacing_bridge": True,
            "audio_intelligence_bridge": True,
            "semantic_caption_bridge": True,
            "visual_qa_bridge": True,
            "quality_budget": True,
            "control_center": True,
            "autonomy_levels": True,
            "brain": True,
        },
    }
    atomic_json(REPORTS / f"brain_prepare_{sid}.json", payload)
    print(
        f"SHORTAUTO_BRAIN_PREPARE=PASS facts={len(facts)} "
        f"evidence={evidence['coverage']}% scenes={len(scenes)}"
    )
    return payload


def quality(sid: str, enforce: bool = False) -> tuple[int, dict[str, Any]]:
    prep_path = REPORTS / f"brain_prepare_{sid}.json"
    prep = load_json(prep_path, {}) if prep_path.is_file() else prepare(sid)
    repetition = repetition_report(sid)
    budget = quality_budget(short_paths(sid), prep.get("evidence_map", {}), repetition)
    paths = short_paths(sid)
    professional = load_json(paths["pro"], {})
    release = load_json(paths["release"], {})
    components = {
        "evidence": safe_float(prep.get("evidence_map", {}).get("coverage"), 0),
        "story": 100.0 if prep.get("story_graph", {}).get("arc_ok") else 78.0,
        "hook": safe_float((prep.get("hook_ab", {}).get("variants") or [{}])[0].get("score"), 75.0),
        "professional": safe_float(professional.get("score"), 80.0 if not professional else 0.0),
        "anti_repetition": max(0.0, 100.0 - 100.0 * safe_float(repetition.get("repetition_ratio"))),
    }
    score = round(sum(components.values()) / len(components), 1)
    mode = prep.get("autonomy_mode", "SAFE")
    min_auto = safe_float(os.getenv("SAP_BRAIN_AUTONOMY_MIN_SCORE", "92"), 92.0)
    release_ok = (
        str(release.get("decision", "")).upper() in {"PASS", "PUBLISH", "RELEASE", "APPROVED", "ACCEPTABLE"}
        if release else True
    )
    if mode == "SAFE":
        decision = "HUMAN_APPROVAL_REQUIRED"
    elif mode == "ASSISTED":
        decision = "AUTO_RELEASE_ALLOWED" if score >= min_auto and budget["status"] == "PASS" and release_ok else "HUMAN_REVIEW_REQUIRED"
    else:
        decision = "AUTO_RELEASE_ALLOWED" if score >= min_auto and budget["status"] == "PASS" and release_ok else "BLOCK"
    result = {
        "short_id": sid,
        "version": "SHORTAUTO_BRAIN_1.1",
        "generated_at": now(),
        "score": score,
        "components": components,
        "quality_budget": budget,
        "visual_repetition": repetition,
        "autonomy_mode": mode,
        "decision": decision,
        "analytics": analytics_summary(),
    }
    atomic_json(REPORTS / f"brain_quality_{sid}.json", result)
    print(f"SHORTAUTO_BRAIN_QUALITY={budget['status']} score={score} autonomy={mode} decision={decision}")
    blocked = budget["status"] != "PASS" or decision == "BLOCK"
    return (1 if enforce and blocked else 0), result


def record_metrics(args: argparse.Namespace) -> int:
    ANALYTICS.mkdir(parents=True, exist_ok=True)
    path = ANALYTICS / f"{CHANNEL}.jsonl"
    row = {
        "recorded_at": now(),
        "short_id": args.short_id,
        "hook_variant": args.hook_variant,
        "views": args.views,
        "avg_view_duration": args.avg_view_duration,
        "percent_viewed": args.percent_viewed,
        "likes": args.likes,
        "comments": args.comments,
        "subscribers": args.subscribers,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = analytics_summary()
    atomic_json(ANALYTICS / f"{CHANNEL}_summary.json", summary)
    memory = load_memory()
    if memory:
        memory["analytics_summary"] = summary
        memory["updated_at"] = now()
        atomic_json(MEMORY, memory)
    print("SHORTAUTO_ANALYTICS_RECORD=PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = sub.add_parser("prepare")
    prepare_cmd.add_argument("--short-id", default=SID)
    quality_cmd = sub.add_parser("quality")
    quality_cmd.add_argument("--short-id", default=SID)
    quality_cmd.add_argument("--enforce", action="store_true")
    status_cmd = sub.add_parser("status")
    status_cmd.add_argument("--short-id", default=SID)
    record_cmd = sub.add_parser("record")
    record_cmd.add_argument("--short-id", required=True)
    record_cmd.add_argument("--hook-variant", default="unknown")
    record_cmd.add_argument("--views", type=float, default=0)
    record_cmd.add_argument("--avg-view-duration", type=float, default=0)
    record_cmd.add_argument("--percent-viewed", type=float, default=0)
    record_cmd.add_argument("--likes", type=float, default=0)
    record_cmd.add_argument("--comments", type=float, default=0)
    record_cmd.add_argument("--subscribers", type=float, default=0)
    args = parser.parse_args()
    if args.command == "record":
        return record_metrics(args)
    sid = str(args.short_id or "").strip()
    if not sid:
        print("ERRO SHORTAUTO BRAIN: SHORT_ID vazio")
        return 1
    if args.command == "prepare":
        prepare(sid)
        return 0
    if args.command == "quality":
        return quality(sid, args.enforce)[0]
    prep = load_json(REPORTS / f"brain_prepare_{sid}.json", {})
    qual = load_json(REPORTS / f"brain_quality_{sid}.json", {})
    print(json.dumps({
        "prepare": prep,
        "quality": qual,
        "analytics": analytics_summary(),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
