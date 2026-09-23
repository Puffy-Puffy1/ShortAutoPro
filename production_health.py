#!/usr/bin/env python3
"""Machine-readable production health snapshot for ShortAutoPro.

This is an observability layer for the canonical pipeline. It does not replace
preflight, render validation, release gates, or the canonical renderer.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
REPORT_DIR = BASE / "reports" / "production"
CORE_FILES = (
    "main.py",
    "media_stage_runtime.py",
    "render_preflight.py",
    "production_recovery.py",
    "production_watchdog.py",
    "video_professional.py",
    "v6_professional.py",
    "release_gate.py",
    "resume_short_runtime.py",
)


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
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


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def snapshot(short_id: str, phase: str = "runtime") -> dict[str, Any]:
    sid = str(short_id or "").strip()
    missing_files = [name for name in CORE_FILES if not (BASE / name).is_file()]
    commands = {
        name: shutil.which(name) is not None
        for name in ("python", "ffmpeg", "ffprobe", "piper", "bash")
    }

    free_mb = None
    try:
        free_mb = shutil.disk_usage(BASE).free // (1024 * 1024)
    except OSError:
        pass

    state = _read_json(BASE / ".sap_state" / f"pipeline_{sid}.json") if sid else {}
    render_preflight = _read_json(
        BASE / "reports" / "production" / f"render_preflight_{sid}.json"
    ) if sid else {}
    release = _read_json(BASE / "manifests" / f"{sid}_release.json") if sid else {}

    issues: list[dict[str, Any]] = []
    if missing_files:
        issues.append({
            "code": "CORE_FILES_MISSING",
            "severity": "BLOCK",
            "detail": missing_files,
        })
    missing_commands = [name for name, ok in commands.items() if not ok]
    if missing_commands:
        issues.append({
            "code": "COMMANDS_MISSING",
            "severity": "BLOCK",
            "detail": missing_commands,
        })
    if free_mb is not None and free_mb < 700:
        issues.append({
            "code": "LOW_STORAGE",
            "severity": "BLOCK",
            "detail": {"free_mb": free_mb, "required_mb": 700},
        })

    if render_preflight and str(render_preflight.get("status", "")).upper() == "FAILED":
        issues.append({
            "code": "RENDER_PREFLIGHT_FAILED",
            "severity": "BLOCK",
            "detail": render_preflight.get("errors", []),
        })

    status = "HEALTHY"
    if any(item["severity"] == "BLOCK" for item in issues):
        status = "BLOCKED"
    elif issues:
        status = "DEGRADED"

    payload = {
        "short_id": sid or None,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "version": "PRODUCTION_HEALTH_1.0",
        "phase": str(phase or "runtime"),
        "status": status,
        "commands": commands,
        "core_files": {
            "required": list(CORE_FILES),
            "missing": missing_files,
        },
        "storage": {"free_mb": free_mb, "minimum_mb": 700},
        "pipeline": {
            "status": state.get("status") if state else None,
            "current_stage": state.get("current_stage") if state else None,
            "last_stage_status": state.get("last_stage_status") if state else None,
            "heartbeat_at": state.get("heartbeat_at") if state else None,
        },
        "render_preflight": {
            "status": render_preflight.get("status") if render_preflight else None,
            "valid_assets": render_preflight.get("valid_assets") if render_preflight else None,
            "expected_scenes": render_preflight.get("expected_scenes") if render_preflight else None,
        },
        "release": {
            "decision": release.get("decision") if release else None,
            "score": release.get("shortautopro_score") if release else None,
        },
        "issues": issues,
    }
    name = f"production_health_{sid or 'global'}.json"
    _atomic_json(REPORT_DIR / name, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro production health")
    parser.add_argument("--short-id", default=os.getenv("SHORT_ID", ""))
    parser.add_argument("--phase", default="runtime")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    report = snapshot(args.short_id, args.phase)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"PRODUCTION_HEALTH={report['status']} phase={report['phase']}")
        print(
            "COMMANDS="
            + ",".join(f"{name}:{'OK' if ok else 'MISSING'}" for name, ok in report["commands"].items())
        )
        if report["issues"]:
            for item in report["issues"]:
                print(f"HEALTH_{item['severity']}={item['code']}")
    if args.enforce and report["status"] == "BLOCKED":
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
