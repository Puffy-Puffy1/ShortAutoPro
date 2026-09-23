#!/usr/bin/env python3
"""Bounded pre-render recovery for the canonical ShortAutoPro pipeline.

This module repairs only artifacts that render_preflight can prove are invalid.
It never selects an alternate renderer, never bypasses a quality gate, and
never marks a production successful on command exit code alone.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import render_preflight
from runtime_config import env_int
from subprocess_guard import run_group

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
REPORT_DIR = BASE / "reports" / "production"


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


def _run(short_id: str, script: str, *args: str, timeout: int | None = None) -> dict[str, Any]:
    path = BASE / script
    started = time.monotonic()
    if not path.is_file():
        return {
            "script": script,
            "status": "FAIL",
            "returncode": 127,
            "elapsed_seconds": 0.0,
            "detail": "script_missing",
        }

    env = os.environ.copy()
    env["SHORTAUTOPRO_BASE"] = str(BASE)
    env["SHORT_ID"] = short_id
    limit = timeout or env_int("SAP_RECOVERY_STAGE_TIMEOUT_SECONDS", 600, 60, 1800)
    try:
        proc = run_group(
            [sys.executable, str(path), *args],
            cwd=BASE,
            env=env,
            check=False,
            timeout=limit,
        )
        code = int(proc.returncode)
        detail = ""
    except subprocess.TimeoutExpired:
        code = 124
        detail = f"timeout>{limit}s"
    return {
        "script": script,
        "status": "PASS" if code == 0 else "FAIL",
        "returncode": code,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "detail": detail,
    }


def _append_action(actions: list[dict[str, Any]], result: dict[str, Any]) -> bool:
    actions.append(result)
    try:
        return int(result.get("returncode", 1)) == 0
    except (TypeError, ValueError):
        return False


def _repair_media(short_id: str, actions: list[dict[str, Any]]) -> bool:
    sequence: list[tuple[str, tuple[str, ...]]] = [
        ("media_stage_runtime.py", ()),
        ("media_master_gate.py", ()),
        ("visual_score_engine.py", ()),
        ("motion_director.py", ()),
        ("rhythm_director.py", ()),
        ("professional_edit_director.py", ()),
        ("professional_edit_repair.py", ()),
        ("multi_asset_director.py", ()),
        ("retention_engine.py", ("--repair", "--enforce")),
        ("sound_design_engine.py", ()),
        ("production_supervisor.py", ()),
        ("editorial_gate.py", ()),
    ]
    for script, args in sequence:
        if not _append_action(actions, _run(short_id, script, *args)):
            return False
    return True


def _repair_edit_plan(short_id: str, actions: list[dict[str, Any]]) -> bool:
    sequence: list[tuple[str, tuple[str, ...]]] = [
        ("professional_edit_director.py", ()),
        ("professional_edit_repair.py", ()),
        ("multi_asset_director.py", ()),
        ("retention_engine.py", ("--repair", "--enforce")),
        ("sound_design_engine.py", ()),
        ("production_supervisor.py", ()),
        ("editorial_gate.py", ()),
    ]
    for script, args in sequence:
        if not _append_action(actions, _run(short_id, script, *args)):
            return False
    return True


def _repair_audio(short_id: str, actions: list[dict[str, Any]]) -> bool:
    return _append_action(actions, _run(short_id, "audio.py"))


def _repair_captions(short_id: str, actions: list[dict[str, Any]]) -> bool:
    for script in (
        "legenda_dinamica.py",
        "professional_caption_director.py",
        "caption_layout_guard.py",
    ):
        if not _append_action(actions, _run(short_id, script)):
            return False
    return True


def repair(short_id: str) -> dict[str, Any]:
    sid = str(short_id or "").strip()
    if not sid:
        return {
            "short_id": sid,
            "status": "BLOCKED",
            "reason": "short_id_empty",
            "actions": [],
        }

    render_preflight.BASE = BASE
    before = render_preflight.inspect(sid)
    actions: list[dict[str, Any]] = []

    if before.get("status") == "READY":
        result = {
            "short_id": sid,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "version": "PRE_RENDER_RECOVERY_1.0",
            "status": "READY",
            "reason": "no_repair_needed",
            "before": before,
            "after": before,
            "actions": actions,
        }
        _atomic_json(REPORT_DIR / f"recovery_{sid}.json", result)
        return result

    checks = before.get("checks", {}) if isinstance(before.get("checks"), dict) else {}
    nonrepairable = []
    for key in ("short_id", "ffmpeg", "ffprobe", "directories", "scene_map"):
        if checks.get(key) is False:
            nonrepairable.append(key)
    if any("espaço insuficiente" in str(item).lower() for item in before.get("errors", [])):
        nonrepairable.append("disk_space")

    failed = False
    if not nonrepairable:
        if checks.get("assets") is False:
            failed = not _repair_media(sid, actions)
        elif checks.get("edit_plan") is False:
            failed = not _repair_edit_plan(sid, actions)

        if not failed and checks.get("audio") is False:
            failed = not _repair_audio(sid, actions)

        audio_rebuilt = any(item.get("script") == "audio.py" and item.get("status") == "PASS" for item in actions)
        if not failed and (checks.get("subtitles") is False or audio_rebuilt):
            failed = not _repair_captions(sid, actions)

    after = render_preflight.inspect(sid)
    if nonrepairable:
        status = "BLOCKED"
        reason = "nonrepairable_preflight:" + ",".join(sorted(set(nonrepairable)))
    elif failed:
        status = "BLOCKED"
        reason = "repair_action_failed"
    elif after.get("status") != "READY":
        status = "BLOCKED"
        reason = "preflight_still_failed"
    else:
        status = "RECOVERED"
        reason = "preflight_ready_after_repair"

    result = {
        "short_id": sid,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "version": "PRE_RENDER_RECOVERY_1.0",
        "status": status,
        "reason": reason,
        "before": before,
        "after": after,
        "actions": actions,
    }
    _atomic_json(REPORT_DIR / f"recovery_{sid}.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro bounded pre-render recovery")
    parser.add_argument("--short-id", default=os.getenv("SHORT_ID", ""))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = repair(args.short_id)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"PRE_RENDER_RECOVERY={report['status']} reason={report['reason']}")
        for action in report.get("actions", []):
            print(
                f"RECOVERY_ACTION={action.get('script')} "
                f"status={action.get('status')} rc={action.get('returncode')} "
                f"elapsed={action.get('elapsed_seconds')}s"
            )
    return 0 if report["status"] in {"READY", "RECOVERED"} else 20


if __name__ == "__main__":
    raise SystemExit(main())
