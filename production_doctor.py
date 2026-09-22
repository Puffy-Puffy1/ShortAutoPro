#!/usr/bin/env python3
"""Unified production diagnosis for the canonical ShortAutoPro pipeline.

Reads existing canonical artifacts only. It does not create an alternate
pipeline and it never weakens a quality gate.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import production_profiler
import release_artifact_guard

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
REPORT_DIR = BASE / "reports" / "production"


def read_json(path: Path, default: Any = None) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        return {} if default is None else default


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
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def latest_short_id() -> str:
    candidates: list[tuple[float, str]] = []

    state_dir = BASE / ".sap_state"
    for path in state_dir.glob("pipeline_*.json") if state_dir.is_dir() else []:
        sid = path.stem.removeprefix("pipeline_")
        try:
            candidates.append((path.stat().st_mtime, sid))
        except OSError:
            pass

    manifests = BASE / "manifests"
    for path in manifests.glob("*_release.json") if manifests.is_dir() else []:
        sid = path.name[:-len("_release.json")]
        try:
            candidates.append((path.stat().st_mtime, sid))
        except OSError:
            pass

    media_reports = BASE / "reports" / "media"
    for path in media_reports.glob("acquisition_missing_*.json") if media_reports.is_dir() else []:
        sid = path.stem.removeprefix("acquisition_missing_")
        try:
            candidates.append((path.stat().st_mtime, sid))
        except OSError:
            pass

    videos = BASE / "videos"
    for path in videos.glob("short_v6_*.mp4") if videos.is_dir() else []:
        sid = path.stem.removeprefix("short_v6_")
        try:
            candidates.append((path.stat().st_mtime, sid))
        except OSError:
            pass

    return max(candidates, default=(0.0, ""))[1]


def media_inventory(sid: str) -> dict[str, Any]:
    root = BASE / "imagens" / f"short_{sid}"
    if not root.is_dir():
        return {"count": 0, "scenes": [], "videos": 0, "photos": 0}
    scenes: list[int] = []
    videos = photos = 0
    for path in sorted(root.glob("scene_*")):
        if not path.is_file():
            continue
        try:
            number = int(path.stem.split("_", 1)[1])
        except Exception:
            continue
        scenes.append(number)
        if path.suffix.lower() == ".mp4":
            videos += 1
        elif path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            photos += 1
    return {
        "count": len(set(scenes)),
        "scenes": sorted(set(scenes)),
        "videos": videos,
        "photos": photos,
    }


def pipeline_failure(state: dict[str, Any]) -> dict[str, Any]:
    stages = state.get("stages", []) if isinstance(state, dict) else []
    if not isinstance(stages, list):
        return {}
    for item in reversed(stages):
        if isinstance(item, dict) and str(item.get("status", "")).lower() == "fail":
            return item
    return {}


def profile_summary(sid: str) -> dict[str, Any]:
    rid = production_profiler.latest_run_id(sid)
    rows = production_profiler.summarize(sid, run_id=rid or None)
    return {
        "run_id": rid,
        "top": rows[:10],
    }


def _missing_scenes(sid: str) -> list[int]:
    path = BASE / "reports" / "media" / f"acquisition_missing_{sid}.json"
    data = read_json(path, {})
    raw = (
        data.get("missing_scenes")
        or data.get("scenes")
        or data.get("missing")
        or []
    ) if isinstance(data, dict) else []
    out: list[int] = []
    if isinstance(raw, list):
        for item in raw:
            value = item.get("scene") if isinstance(item, dict) else item
            try:
                out.append(int(value))
            except (TypeError, ValueError):
                pass
    return sorted(set(out))


def diagnose(sid: str) -> dict[str, Any]:
    state = read_json(BASE / ".sap_state" / f"pipeline_{sid}.json", {})
    release = read_json(BASE / "manifests" / f"{sid}_release.json", {})
    quality = read_json(BASE / "manifests" / f"{sid}_quality.json", {})
    professional = read_json(BASE / "manifests" / f"{sid}_professional.json", {})
    media = media_inventory(sid)
    missing = _missing_scenes(sid)
    render_preflight = read_json(
        REPORT_DIR / f"render_preflight_{sid}.json",
        {},
    )
    profile = profile_summary(sid)
    final_video = BASE / "videos" / f"short_v6_{sid}.mp4"
    final_ok = False
    final_bytes = 0
    try:
        final_bytes = final_video.stat().st_size
        final_ok = final_bytes >= 500_000
    except OSError:
        pass

    issues: list[dict[str, Any]] = []
    if isinstance(render_preflight, dict) and render_preflight:
        preflight_errors = render_preflight.get("errors", [])
        if (
            str(render_preflight.get("status", "")).upper() == "FAILED"
            and isinstance(preflight_errors, list)
        ):
            for detail in preflight_errors[:8]:
                issues.append({
                    "code": "RENDER_PREFLIGHT_FAILED",
                    "severity": "BLOCK",
                    "detail": str(detail),
                })

    if missing:
        issues.append({
            "code": "MEDIA_INCOMPLETE",
            "severity": "BLOCK",
            "detail": f"cenas ausentes: {','.join(map(str, missing))}",
        })

    profile_rows = profile.get("top", [])
    pipeline_rows = [
        row for row in profile_rows
        if row.get("category") == "pipeline_stage"
    ]
    if pipeline_rows:
        slowest = max(
            pipeline_rows,
            key=lambda row: float(row.get("total_seconds", 0) or 0),
        )
        slow_total = float(slowest.get("total_seconds", 0) or 0)
        if slow_total >= 120:
            issues.append({
                "code": "PIPELINE_STAGE_SLOW",
                "severity": "WARN",
                "detail": (
                    f"{slowest.get('name') or 'etapa'} consumiu "
                    f"{round(slow_total, 1)}s no run atual"
                ),
            })

    acquisition = [
        row for row in profile_rows
        if row.get("category") == "media" and row.get("name") == "media_acquisition"
    ]
    if acquisition and float(acquisition[0].get("max_seconds", 0) or 0) >= 60:
        issues.append({
            "code": "MEDIA_ACQUISITION_SLOW",
            "severity": "WARN",
            "detail": f"máximo {acquisition[0].get('max_seconds')}s por aquisição",
        })

    failure = pipeline_failure(state)
    if failure:
        issues.append({
            "code": "PIPELINE_STAGE_FAILED",
            "severity": "BLOCK",
            "detail": str(failure.get("title") or failure.get("stage") or "etapa desconhecida"),
        })

    release_decision = str(release.get("decision", "") or "").upper()
    release_valid = False
    release_reason = "release_not_checked"
    if release_decision in {"PUBLISH", "ACCEPTABLE"}:
        release_valid, release_reason = release_artifact_guard.validate(sid)
        if not release_valid:
            issues.append({
                "code": "RELEASE_ARTIFACT_STALE",
                "severity": "BLOCK",
                "detail": release_reason,
            })
    elif final_ok:
        issues.append({
            "code": "FINAL_VIDEO_NOT_RELEASED",
            "severity": "WARN",
            "detail": release_decision or "release gate ainda não executado",
        })

    semantic_checkpoint = (
        (BASE / "roteiros" / f"scene_map_{sid}.json").is_file()
        and (BASE / "roteiros" / f"post_script_truth_{sid}.json").is_file()
        and (BASE / "roteiros" / f"visual_continuity_{sid}.json").is_file()
    )

    if missing:
        boundary = "media"
        if semantic_checkpoint:
            action = f"python resume_after_semantic_fix.py --short-id {sid}"
        else:
            action = f"python main.py resume --short-id {sid}"
    elif not final_ok:
        boundary = "downstream"
        action = f"python main.py resume --short-id {sid}"
    elif release_valid:
        boundary = "complete"
        action = f"python production_center.py status --short-id {sid}"
    else:
        boundary = "final_gates"
        action = f"python main.py resume --short-id {sid}"

    status = "READY" if not issues and boundary == "complete" else "BLOCKED" if any(
        item["severity"] == "BLOCK" for item in issues
    ) else "IN_PROGRESS"

    result = {
        "short_id": sid,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "boundary": boundary,
        "pipeline_status": state.get("status") if isinstance(state, dict) else None,
        "media": media,
        "missing_scenes": missing,
        "render_preflight": render_preflight,
        "profile": profile,
        "final_video": {
            "path": str(final_video),
            "exists": final_ok,
            "bytes": final_bytes,
        },
        "quality": {
            "approved": quality.get("approved") if isinstance(quality, dict) else None,
            "professional_score": professional.get("score") if isinstance(professional, dict) else None,
            "release_decision": release_decision or None,
            "release_valid": release_valid,
            "release_validation_reason": release_reason,
            "release_score": release.get("shortautopro_score") if isinstance(release, dict) else None,
        },
        "last_failure": failure,
        "runtime": {
            "provider_workers": os.getenv("SAP_MEDIA_PROVIDER_WORKERS", "6"),
            "api_timeout": os.getenv("SAP_MEDIA_API_TIMEOUT", "10"),
            "wikimedia_timeout": os.getenv("SAP_WIKIMEDIA_TIMEOUT", "10"),
            "must_rescue_max_queries": os.getenv("SAP_MUST_RESCUE_MAX_QUERIES", "5"),
            "stock_rescue_max_queries": os.getenv("SAP_STOCK_RESCUE_MAX_QUERIES", "4"),
        },
        "issues": issues,
        "next_action": action,
    }
    atomic_json(REPORT_DIR / f"doctor_{sid}.json", result)
    return result


def print_report(report: dict[str, Any]) -> None:
    print("==============================================")
    print(" SHORTAUTOPRO - PRODUCTION DOCTOR")
    print("==============================================")
    print(f"ID: {report['short_id']}")
    print(f"STATUS: {report['status']}")
    print(f"BOUNDARY: {report['boundary']}")
    print(
        "MEDIA: "
        f"{report['media']['count']} cenas "
        f"({report['media']['videos']} vídeos / {report['media']['photos']} fotos)"
    )
    if report["missing_scenes"]:
        print("MISSING: " + ",".join(map(str, report["missing_scenes"])))
    print(f"PROFILE RUN: {report['profile'].get('run_id') or '-'}")
    for row in report["profile"].get("top", [])[:5]:
        print(
            f"  {row.get('category')}/{row.get('name')}: "
            f"total={row.get('total_seconds')}s max={row.get('max_seconds')}s"
        )
    preflight = report.get("render_preflight", {})
    if isinstance(preflight, dict) and preflight:
        print(
            "RENDER PREFLIGHT: "
            f"{preflight.get('status', 'UNKNOWN')} "
            f"audio={preflight.get('audio_duration', 0)}s "
            f"assets={preflight.get('valid_assets', 0)}/{preflight.get('expected_scenes', '?')}"
        )
    if report["issues"]:
        print("ISSUES:")
        for item in report["issues"]:
            print(f"  [{item['severity']}] {item['code']}: {item['detail']}")
    else:
        print("ISSUES: nenhum bloqueio detectado")
    print("NEXT:")
    print(f"  {report['next_action']}")
    report_path = REPORT_DIR / ("doctor_" + str(report["short_id"]) + ".json")
    print(f"REPORT: {report_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro production doctor")
    parser.add_argument("--short-id", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    sid = args.short_id.strip() or latest_short_id()
    if not sid:
        print("ERRO: nenhuma produção encontrada")
        return 1
    report = diagnose(sid)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_report(report)
    return 0 if report["status"] != "BLOCKED" else 20


if __name__ == "__main__":
    raise SystemExit(main())
