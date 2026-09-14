#!/usr/bin/env python3
"""ShortAutoPro Evolution Core.

Camada central, stdlib-only, para observabilidade, qualidade, inventário,
recuperação, perfis, validação E2E e fundações de long-form/serviço.

O módulo foi desenhado para ser seguro em Termux e Windows e não substitui
os motores de produção existentes: ele mede e coordena o pipeline oficial.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "1.0.0"
BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
STATE_DIR = BASE / ".sap_state"
REPORT_DIR = BASE / "reports" / "evolution"
METRICS_DIR = BASE / "metrics"
PROFILES_FILE = BASE / "config" / "channel_profiles.json"

GENERATED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "logs", "temp", "tmp", "cache",
    "videos", "audios", "downloads", "backups", ".sap_state", "metrics",
}

STOPWORDS = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "um",
    "uma", "para", "por", "com", "sem", "the", "of", "and", "in", "on", "to",
    "cinematic", "dramatic", "dark", "vintage", "historic", "image", "video",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def short_id() -> str:
    value = os.getenv("SHORT_ID", "").strip()
    return value or datetime.now().strftime("%Y-%m-%d")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, float(value)))


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {} if default is None else default


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def words(text: Any) -> list[str]:
    return re.findall(r"\b[\wÀ-ÿ'-]+\b", str(text or ""), flags=re.UNICODE)


def tokens(text: Any) -> set[str]:
    return {
        item for item in re.findall(r"[a-z0-9à-ÿ]+", str(text or "").lower())
        if len(item) >= 3 and item not in STOPWORDS
    }


def similarity(a: Any, b: Any) -> float:
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def load_profiles() -> dict[str, Any]:
    data = read_json(PROFILES_FILE, {})
    return data if isinstance(data, dict) else {}


def resolve_profile(name: str | None = None) -> tuple[str, dict[str, Any]]:
    profiles = load_profiles()
    requested = (name or os.getenv("SAP_CHANNEL_PROFILE", "default")).strip() or "default"
    base = profiles.get("default", {}) if isinstance(profiles.get("default"), dict) else {}
    selected = profiles.get(requested, {}) if isinstance(profiles.get(requested), dict) else {}
    merged = dict(base)
    for key, value in selected.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return requested, merged


# ---------------------------------------------------------------------------
# Checkpoint / recovery / telemetry
# ---------------------------------------------------------------------------


def state_path(sid: str | None = None) -> Path:
    return STATE_DIR / f"{sid or short_id()}.json"


def load_state(sid: str | None = None) -> dict[str, Any]:
    path = state_path(sid)
    data = read_json(path, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("short_id", sid or short_id())
    data.setdefault("created_at", now_iso())
    data.setdefault("stages", {})
    return data


def checkpoint(stage: str, status: str, title: str = "", sid: str | None = None) -> dict[str, Any]:
    sid = sid or short_id()
    state = load_state(sid)
    stages = state.setdefault("stages", {})
    entry = stages.get(stage, {}) if isinstance(stages.get(stage), dict) else {}
    ts = time.time()
    status = status.lower().strip()
    if status in {"start", "started", "running"}:
        entry["started_at"] = now_iso()
        entry["started_epoch"] = ts
        normalized = "RUNNING"
    elif status in {"pass", "passed", "ok", "success"}:
        normalized = "PASS"
        entry["finished_at"] = now_iso()
        started = safe_float(entry.get("started_epoch"), ts)
        entry["elapsed_seconds"] = round(max(0.0, ts - started), 3)
    elif status in {"fail", "failed", "error", "block"}:
        normalized = "FAIL"
        entry["finished_at"] = now_iso()
        started = safe_float(entry.get("started_epoch"), ts)
        entry["elapsed_seconds"] = round(max(0.0, ts - started), 3)
    else:
        raise ValueError(f"status inválido: {status}")
    entry["status"] = normalized
    if title:
        entry["title"] = title
    stages[stage] = entry
    state["updated_at"] = now_iso()
    atomic_json(state_path(sid), state)
    return entry


def finish_production(status: str = "SUCCESS", sid: str | None = None) -> dict[str, Any]:
    sid = sid or short_id()
    state = load_state(sid)
    state["production_status"] = status.upper()
    state["finished_at"] = now_iso()
    state["updated_at"] = now_iso()
    started_epochs = [
        safe_float(item.get("started_epoch"), 0)
        for item in state.get("stages", {}).values()
        if isinstance(item, dict) and item.get("started_epoch")
    ]
    if started_epochs:
        state["elapsed_seconds"] = round(max(0.0, time.time() - min(started_epochs)), 3)
    atomic_json(state_path(sid), state)
    event = {
        "short_id": sid,
        "timestamp": now_iso(),
        "status": state["production_status"],
        "elapsed_seconds": state.get("elapsed_seconds", 0),
        "stages_pass": sum(1 for x in state.get("stages", {}).values() if isinstance(x, dict) and x.get("status") == "PASS"),
        "stages_fail": sum(1 for x in state.get("stages", {}).values() if isinstance(x, dict) and x.get("status") == "FAIL"),
    }
    quality = read_json(BASE / "manifests" / f"{sid}_evolution.json", {})
    if isinstance(quality, dict):
        event["quality_score"] = quality.get("total_score")
        event["quality_status"] = quality.get("status")
    append_jsonl(METRICS_DIR / "production.jsonl", event)
    return event


def resume_plan(sid: str | None = None) -> dict[str, Any]:
    state = load_state(sid)
    stages = state.get("stages", {}) if isinstance(state.get("stages"), dict) else {}
    failed = [name for name, item in stages.items() if isinstance(item, dict) and item.get("status") == "FAIL"]
    running = [name for name, item in stages.items() if isinstance(item, dict) and item.get("status") == "RUNNING"]
    passed = [name for name, item in stages.items() if isinstance(item, dict) and item.get("status") == "PASS"]
    candidate = failed[0] if failed else (running[0] if running else None)
    return {
        "short_id": state.get("short_id"),
        "production_status": state.get("production_status", "INCOMPLETE"),
        "passed_count": len(passed),
        "failed": failed,
        "running": running,
        "resume_candidate": candidate,
        "note": "Checkpoint seguro; pular etapas automaticamente exige idempotência comprovada do estágio.",
    }


# ---------------------------------------------------------------------------
# Inventory / consolidation map
# ---------------------------------------------------------------------------


def iter_source_files() -> Iterable[Path]:
    for path in BASE.rglob("*"):
        try:
            rel = path.relative_to(BASE)
        except ValueError:
            continue
        if any(part in GENERATED_DIRS for part in rel.parts):
            continue
        if path.is_file() and path.suffix.lower() in {".py", ".sh", ".yml", ".yaml", ".json", ".md"}:
            yield path


def pipeline_references() -> set[str]:
    refs: set[str] = set()
    path = BASE / "gerar_short.sh"
    if not path.is_file():
        return refs
    text = path.read_text(encoding="utf-8", errors="ignore")
    refs.update(re.findall(r'"([A-Za-z0-9_.-]+\.(?:py|sh))"', text))
    refs.add("gerar_short.sh")
    refs.add("control_center.sh")
    return refs


def local_imports(path: Path) -> set[str]:
    if path.suffix.lower() != ".py":
        return set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return set()
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.add(node.module.split(".")[0])
    return result


def build_inventory() -> dict[str, Any]:
    files = list(iter_source_files())
    pipeline = pipeline_references()
    stem_to_paths: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        if path.suffix.lower() == ".py":
            stem_to_paths[path.stem].append(path)

    dependency_names: set[str] = set()
    for filename in pipeline:
        path = BASE / filename
        if path.is_file():
            dependency_names.update(local_imports(path))
    changed = True
    while changed:
        changed = False
        for name in list(dependency_names):
            for dep_path in stem_to_paths.get(name, []):
                before = len(dependency_names)
                dependency_names.update(local_imports(dep_path))
                changed |= len(dependency_names) != before

    rows = []
    counts = Counter()
    for path in sorted(files):
        rel = path.relative_to(BASE).as_posix()
        name = path.name
        lower = rel.lower()
        reasons = []
        if rel.startswith("tests_sim/") or name.startswith("test_"):
            category = "TESTE"
            reasons.append("arquivo de regressão/teste")
        elif rel.startswith(".github/") or rel.startswith("automation/"):
            category = "INFRAESTRUTURA"
            reasons.append("automação/deploy")
        elif name in pipeline:
            category = "PRODUCAO"
            reasons.append("referenciado pelo pipeline oficial")
        elif path.stem in dependency_names:
            category = "DEPENDENCIA"
            reasons.append("importado por módulo do pipeline")
        elif any(term in lower for term in ("legacy", "deprecated", "old_", "backup", "archive")):
            category = "LEGADO_PROVAVEL"
            reasons.append("nome indica versão antiga; não remover sem auditoria")
        elif path.suffix.lower() in {".md", ".json"}:
            category = "CONFIG_OU_DOC"
            reasons.append("configuração/documentação")
        else:
            category = "NAO_IDENTIFICADO"
            reasons.append("sem vínculo estático confirmado")
        counts[category] += 1
        rows.append({"path": rel, "category": category, "reason": "; ".join(reasons)})

    report = {
        "version": VERSION,
        "generated_at": now_iso(),
        "pipeline_references": sorted(pipeline),
        "counts": dict(counts),
        "files": rows,
        "safety": "Relatório somente leitura; nenhuma exclusão é feita automaticamente.",
    }
    atomic_json(REPORT_DIR / "inventory.json", report)
    return report


# ---------------------------------------------------------------------------
# Visual / caption / technical audits
# ---------------------------------------------------------------------------


def visual_audit(sid: str | None = None) -> dict[str, Any]:
    sid = sid or short_id()
    scene_map_path = BASE / "roteiros" / f"scene_map_{sid}.json"
    supervisor_path = BASE / "roteiros" / f"supervisor_{sid}.json"
    media_quality_path = BASE / "roteiros" / f"media_quality_{sid}.json"
    media_dir = BASE / "imagens" / f"short_{sid}"
    scene_map = read_json(scene_map_path, {})
    scenes = scene_map.get("scenes", []) if isinstance(scene_map, dict) else []
    if not isinstance(scenes, list):
        scenes = []
    expected = int(os.getenv("SHORT_QTD_CENAS", "12") or 12)
    expected = max(6, min(expected, 20))

    structure = 0.0
    if len(scenes) == expected:
        structure += 12.0
    numbered = []
    for scene in scenes:
        if isinstance(scene, dict):
            try:
                numbered.append(int(scene.get("scene")))
            except (TypeError, ValueError):
                pass
    if numbered == list(range(1, expected + 1)):
        structure += 8.0

    query_hits = sum(1 for s in scenes if isinstance(s, dict) and str(s.get("query", "")).strip())
    must_hits = sum(1 for s in scenes if isinstance(s, dict) and isinstance(s.get("must_have"), list) and s.get("must_have"))
    relevance = 0.0 if not scenes else 30.0 * ((query_hits + must_hits) / (2 * len(scenes)))

    repeats = 0
    adjacent_scores = []
    for left, right in zip(scenes, scenes[1:]):
        if not isinstance(left, dict) or not isinstance(right, dict):
            continue
        score = similarity(left.get("query"), right.get("query"))
        adjacent_scores.append(score)
        if score >= 0.55:
            repeats += 1
    diversity = 20.0
    if scenes:
        diversity -= min(20.0, repeats * 4.0)
        unique_modes = {str(s.get("visual_mode", "")).strip() for s in scenes if isinstance(s, dict) and s.get("visual_mode")}
        if len(unique_modes) < 3:
            diversity -= 4.0
    diversity = max(0.0, diversity)

    physical = []
    if media_dir.is_dir():
        physical = [p for p in media_dir.glob("scene_*") if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".mp4"}]
    coverage = 15.0 * min(1.0, len(physical) / expected) if expected else 0.0

    supervisor = read_json(supervisor_path, {})
    supervisor_status = str(supervisor.get("status", "")).upper() if isinstance(supervisor, dict) else ""
    supervisor_score = {"EXCELLENT": 15.0, "PASS": 13.0, "WARNING": 9.0, "BLOCK": 0.0}.get(supervisor_status, 6.0)

    external = read_json(media_quality_path, {})
    external_score = None
    if isinstance(external, dict):
        for key in ("score", "total_score", "visual_score", "quality_score"):
            value = external.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                external_score = clamp(float(value))
                break

    raw = structure + relevance + diversity + coverage + supervisor_score
    if external_score is not None:
        score = round(raw * 0.80 + external_score * 0.20, 1)
    else:
        score = round(raw, 1)

    threshold = safe_float(os.getenv("SAP_VISUAL_MIN_SCORE", "78"), 78.0)
    result = {
        "short_id": sid,
        "score": clamp(score),
        "threshold": threshold,
        "status": "PASS" if score >= threshold else "RETRY_RECOMMENDED",
        "components": {
            "structure": round(structure, 1),
            "semantic_relevance": round(relevance, 1),
            "diversity_continuity": round(diversity, 1),
            "physical_coverage": round(coverage, 1),
            "supervisor": round(supervisor_score, 1),
        },
        "details": {
            "expected_scenes": expected,
            "scene_map_count": len(scenes),
            "physical_media_count": len(physical),
            "repeated_adjacent_queries": repeats,
            "mean_adjacent_similarity": round(sum(adjacent_scores) / len(adjacent_scores), 3) if adjacent_scores else 0.0,
            "supervisor_status": supervisor_status or "UNKNOWN",
            "external_media_score": external_score,
        },
    }
    atomic_json(REPORT_DIR / f"visual_{sid}.json", result)
    return result


def find_caption_file(sid: str) -> Path | None:
    candidates = []
    for root_name in ("temp", "tmp", "roteiros"):
        root = BASE / root_name
        if not root.exists():
            continue
        candidates.extend(root.rglob(f"*{sid}*.ass"))
        candidates.extend(root.rglob(f"*{sid}*.srt"))
    if not candidates:
        return None
    return max((p for p in candidates if p.is_file()), key=lambda p: p.stat().st_mtime, default=None)


def caption_audit(sid: str | None = None, profile_name: str | None = None) -> dict[str, Any]:
    sid = sid or short_id()
    profile_name, profile = resolve_profile(profile_name)
    policy = profile.get("captions", {}) if isinstance(profile.get("captions"), dict) else {}
    max_words = int(policy.get("max_words_per_event", 7) or 7)
    max_lines = int(policy.get("max_lines", 2) or 2)
    path = find_caption_file(sid)
    events: list[str] = []
    if path and path.suffix.lower() == ".ass":
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                if len(parts) == 10:
                    events.append(re.sub(r"\{[^}]*\}", "", parts[9]))
    elif path and path.suffix.lower() == ".srt":
        raw = path.read_text(encoding="utf-8", errors="ignore")
        blocks = re.split(r"\n\s*\n", raw)
        for block in blocks:
            lines = [x.strip() for x in block.splitlines() if x.strip()]
            text_lines = [x for x in lines if "-->" not in x and not x.isdigit()]
            if text_lines:
                events.append("\\N".join(text_lines))

    violations_words = sum(1 for text in events if len(words(text.replace("\\N", " "))) > max_words)
    violations_lines = sum(1 for text in events if len(text.split("\\N")) > max_lines)
    total = len(events)
    if not path:
        score = 55.0
        status = "NOT_MEASURABLE"
    elif total == 0:
        score = 40.0
        status = "REVIEW"
    else:
        penalty = (violations_words * 2.5) + (violations_lines * 5.0)
        score = clamp(100.0 - penalty)
        status = "PASS" if score >= 80 else "REVIEW"
    result = {
        "short_id": sid,
        "profile": profile_name,
        "score": round(score, 1),
        "status": status,
        "caption_file": str(path) if path else None,
        "events": total,
        "violations": {"too_many_words": violations_words, "too_many_lines": violations_lines},
        "policy": {
            "max_words_per_event": max_words,
            "max_lines": max_lines,
            "safe_bottom_ratio": policy.get("safe_bottom_ratio", 0.16),
            "highlight_keywords": bool(policy.get("highlight_keywords", True)),
        },
    }
    atomic_json(REPORT_DIR / f"captions_{sid}.json", result)
    return result


def ffprobe_video(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"errors": ["video_missing"], "score": 0.0}
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
            capture_output=True, text=True, check=True, timeout=45,
        )
        data = json.loads(proc.stdout)
    except Exception as exc:
        return {"errors": [f"ffprobe_failed:{exc}"], "score": 0.0}
    streams = data.get("streams", []) if isinstance(data, dict) else []
    fmt = data.get("format", {}) if isinstance(data, dict) else {}
    videos = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"]
    audios = [s for s in streams if isinstance(s, dict) and s.get("codec_type") == "audio"]
    errors = []
    score = 100.0
    width = height = 0
    if not videos:
        errors.append("video_stream_missing")
        score -= 60
    else:
        width = int(videos[0].get("width") or 0)
        height = int(videos[0].get("height") or 0)
        if (width, height) != (1080, 1920):
            errors.append(f"resolution={width}x{height}")
            score -= 25
    if not audios:
        errors.append("audio_stream_missing")
        score -= 35
    duration = safe_float(fmt.get("duration"), 0.0)
    if not 15 <= duration <= 180:
        errors.append(f"duration={duration:.2f}")
        score -= 25
    return {
        "score": clamp(score), "errors": errors, "duration": round(duration, 3),
        "width": width, "height": height, "audio_streams": len(audios), "video_streams": len(videos),
    }


def latest_video(sid: str | None = None) -> Path | None:
    if sid:
        candidate = BASE / "videos" / f"short_v6_{sid}.mp4"
        if candidate.is_file():
            return candidate
    videos_dir = BASE / "videos"
    if not videos_dir.is_dir():
        return None
    return max(videos_dir.glob("short_v6_*.mp4"), key=lambda p: p.stat().st_mtime, default=None)


def black_frame_check(path: Path) -> dict[str, Any]:
    if not shutil.which("ffmpeg"):
        return {"available": False, "black_events": None}
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostdin", "-i", str(path), "-vf", "blackdetect=d=0.5:pix_th=0.10", "-an", "-f", "null", "-"],
            capture_output=True, text=True, timeout=90,
        )
        combined = (proc.stderr or "") + "\n" + (proc.stdout or "")
        events = len(re.findall(r"black_start:", combined))
        return {"available": True, "black_events": events, "returncode": proc.returncode}
    except Exception as exc:
        return {"available": True, "black_events": None, "error": str(exc)}


def e2e_validate(sid: str | None = None, check_black: bool = False) -> dict[str, Any]:
    video = latest_video(sid)
    if video is None:
        return {"status": "BLOCK", "score": 0.0, "errors": ["video_not_found"]}
    tech = ffprobe_video(video)
    score = safe_float(tech.get("score"), 0.0)
    result: dict[str, Any] = {"video": str(video), "technical": tech, "score": score, "status": "PASS" if score >= 90 else "BLOCK"}
    if check_black:
        black = black_frame_check(video)
        result["black_frames"] = black
        if isinstance(black.get("black_events"), int) and black["black_events"] > 0:
            result["score"] = max(0.0, result["score"] - min(20.0, black["black_events"] * 5.0))
            result["status"] = "REVIEW"
    sid_final = sid or re.sub(r"^short_v6_|\.mp4$", "", video.name)
    result["short_id"] = sid_final
    atomic_json(REPORT_DIR / f"e2e_{sid_final}.json", result)
    return result


# ---------------------------------------------------------------------------
# Central quality score
# ---------------------------------------------------------------------------


def quality_score(sid: str | None = None) -> dict[str, Any]:
    sid = sid or short_id()
    visual = visual_audit(sid)
    captions = caption_audit(sid)
    video = latest_video(sid)
    technical = ffprobe_video(video) if video else {"score": 0.0, "errors": ["video_missing"]}
    final = read_json(BASE / "manifests" / f"{sid}_quality.json", {})
    editorial_raw = safe_float(final.get("total_score"), 0.0) if isinstance(final, dict) else 0.0
    editorial_score = clamp(editorial_raw)

    profile_name, profile = resolve_profile(None)
    audio_policy = profile.get("audio", {}) if isinstance(profile.get("audio"), dict) else {}
    audio_score = 100.0 if technical.get("audio_streams", 0) else 0.0

    components = {
        "visual": round(safe_float(visual.get("score")), 1),
        "captions": round(safe_float(captions.get("score")), 1),
        "audio": round(audio_score, 1),
        "technical": round(safe_float(technical.get("score")), 1),
        "editorial": round(editorial_score, 1),
    }
    weights = {"visual": 0.35, "captions": 0.15, "audio": 0.15, "technical": 0.20, "editorial": 0.15}
    total = round(sum(components[key] * weights[key] for key in weights), 1)
    threshold = safe_float(os.getenv("SAP_EVOLUTION_MIN_SCORE", "80"), 80.0)
    critical = []
    if technical.get("errors"):
        hard = {"video_missing", "video_stream_missing", "audio_stream_missing"}
        for error in technical.get("errors", []):
            if str(error).split(":", 1)[0].split("=", 1)[0] in hard:
                critical.append(str(error))
    if isinstance(final, dict) and final and not final.get("approved", False):
        critical.append("legacy_final_quality_not_approved")
    status = "PASS" if total >= threshold and not critical else ("RETRY" if not critical else "BLOCK")
    remediation = []
    if components["visual"] < 78:
        remediation.append("rebuscar mídia das cenas fracas/repetidas")
    if components["captions"] < 80:
        remediation.append("reduzir palavras/linhas por evento de legenda")
    if components["audio"] < 90:
        remediation.append("regerar ou remasterizar áudio")
    if components["technical"] < 90:
        remediation.append("corrigir render técnico antes de publicar")
    if components["editorial"] < 75:
        remediation.append("revisar roteiro/hook/publish pack")

    result = {
        "short_id": sid,
        "generated_at": now_iso(),
        "profile": profile_name,
        "total_score": total,
        "threshold": threshold,
        "status": status,
        "components": components,
        "weights": weights,
        "critical": critical,
        "remediation": remediation,
        "audio_policy": {
            "target_lufs": audio_policy.get("target_lufs", -14),
            "true_peak_db": audio_policy.get("true_peak_db", -1.5),
            "music_ducking_db": audio_policy.get("music_ducking_db", -12),
        },
    }
    atomic_json(BASE / "manifests" / f"{sid}_evolution.json", result)
    return result


# ---------------------------------------------------------------------------
# Metrics / dashboards
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            rows.append(item)
    return rows


def metrics_summary() -> dict[str, Any]:
    rows = read_jsonl(METRICS_DIR / "production.jsonl")
    success = [x for x in rows if x.get("status") == "SUCCESS"]
    quality = [safe_float(x.get("quality_score"), -1) for x in rows]
    quality = [x for x in quality if x >= 0]
    elapsed = [safe_float(x.get("elapsed_seconds"), 0) for x in rows if safe_float(x.get("elapsed_seconds"), 0) > 0]
    return {
        "productions": len(rows),
        "success": len(success),
        "success_rate": round((len(success) / len(rows) * 100), 1) if rows else 0.0,
        "average_quality": round(sum(quality) / len(quality), 1) if quality else None,
        "average_elapsed_seconds": round(sum(elapsed) / len(elapsed), 1) if elapsed else None,
        "last": rows[-1] if rows else None,
    }


def dashboard() -> dict[str, Any]:
    states = sorted(STATE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True) if STATE_DIR.exists() else []
    last_state = read_json(states[0], {}) if states else {}
    last_quality = None
    if isinstance(last_state, dict) and last_state.get("short_id"):
        last_quality = read_json(BASE / "manifests" / f"{last_state['short_id']}_evolution.json", {})
    return {
        "version": VERSION,
        "profile": resolve_profile(None)[0],
        "metrics": metrics_summary(),
        "last_state": last_state,
        "last_quality": last_quality,
        "free_stack": True,
    }


# ---------------------------------------------------------------------------
# Long-form + client-service foundations
# ---------------------------------------------------------------------------


def longform_plan(topic: str, minutes: int, chapters: int | None = None) -> dict[str, Any]:
    minutes = max(5, min(int(minutes), 180))
    chapters = chapters or max(3, min(18, round(minutes / 3)))
    seconds = minutes * 60
    per_chapter = seconds / chapters
    plan = {
        "topic": topic.strip(),
        "target_minutes": minutes,
        "chapters": [],
        "continuity": {"global_topic_lock": True, "entity_memory": True, "resume_by_chapter": True},
        "status": "PLANNED",
        "generated_at": now_iso(),
    }
    for index in range(1, chapters + 1):
        start = round((index - 1) * per_chapter)
        end = round(index * per_chapter)
        plan["chapters"].append({
            "chapter": index,
            "start_second": start,
            "target_end_second": end,
            "objective": "context" if index == 1 else ("conclusion" if index == chapters else "development"),
            "status": "PENDING",
        })
    slug = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")[:50] or "longform"
    atomic_json(REPORT_DIR / f"longform_{slug}.json", plan)
    return plan


def client_job(client: str, topic: str, quantity: int, language: str, profile: str) -> dict[str, Any]:
    quantity = max(1, min(int(quantity), 100))
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload = {
        "job_id": job_id,
        "client": client.strip(),
        "topic": topic.strip(),
        "quantity": quantity,
        "language": language.strip(),
        "profile": profile.strip() or "default",
        "deliverables": ["video", "title", "description", "hashtags", "credits", "quality_report"],
        "status": "QUEUED",
        "created_at": now_iso(),
    }
    atomic_json(REPORT_DIR / "client_jobs" / f"{job_id}.json", payload)
    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def dump_result(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_profiles(_: argparse.Namespace) -> int:
    data = load_profiles()
    print("Perfis disponíveis:")
    for name in sorted(data):
        print(f"- {name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ShortAutoPro Evolution Core")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("checkpoint")
    p.add_argument("--stage", required=True)
    p.add_argument("--status", required=True)
    p.add_argument("--title", default="")
    p.add_argument("--short-id", default=None)

    p = sub.add_parser("finish")
    p.add_argument("--status", default="SUCCESS")
    p.add_argument("--short-id", default=None)

    p = sub.add_parser("resume-plan")
    p.add_argument("--short-id", default=None)

    sub.add_parser("inventory")

    p = sub.add_parser("visual-audit")
    p.add_argument("--short-id", default=None)

    p = sub.add_parser("caption-audit")
    p.add_argument("--short-id", default=None)
    p.add_argument("--profile", default=None)

    p = sub.add_parser("quality-score")
    p.add_argument("--short-id", default=None)
    p.add_argument("--enforce", action="store_true")

    p = sub.add_parser("e2e")
    p.add_argument("--short-id", default=None)
    p.add_argument("--black-frames", action="store_true")
    p.add_argument("--enforce", action="store_true")

    sub.add_parser("metrics")
    sub.add_parser("dashboard")
    sub.add_parser("profiles")

    p = sub.add_parser("longform-plan")
    p.add_argument("--topic", required=True)
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--chapters", type=int, default=None)

    p = sub.add_parser("client-job")
    p.add_argument("--client", required=True)
    p.add_argument("--topic", required=True)
    p.add_argument("--quantity", type=int, default=1)
    p.add_argument("--language", default="pt-BR")
    p.add_argument("--profile", default="default")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "checkpoint":
            dump_result(checkpoint(args.stage, args.status, args.title, args.short_id))
        elif args.command == "finish":
            dump_result(finish_production(args.status, args.short_id))
        elif args.command == "resume-plan":
            dump_result(resume_plan(args.short_id))
        elif args.command == "inventory":
            report = build_inventory()
            dump_result({"counts": report["counts"], "report": str(REPORT_DIR / "inventory.json")})
        elif args.command == "visual-audit":
            dump_result(visual_audit(args.short_id))
        elif args.command == "caption-audit":
            dump_result(caption_audit(args.short_id, args.profile))
        elif args.command == "quality-score":
            result = quality_score(args.short_id)
            dump_result(result)
            if args.enforce and result["status"] != "PASS":
                return 1
        elif args.command == "e2e":
            result = e2e_validate(args.short_id, args.black_frames)
            dump_result(result)
            if args.enforce and result["status"] != "PASS":
                return 1
        elif args.command == "metrics":
            dump_result(metrics_summary())
        elif args.command == "dashboard":
            dump_result(dashboard())
        elif args.command == "profiles":
            return cmd_profiles(args)
        elif args.command == "longform-plan":
            dump_result(longform_plan(args.topic, args.minutes, args.chapters))
        elif args.command == "client-job":
            dump_result(client_job(args.client, args.topic, args.quantity, args.language, args.profile))
        else:
            raise ValueError(f"comando não implementado: {args.command}")
    except Exception as exc:
        print(f"EVOLUTION_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
