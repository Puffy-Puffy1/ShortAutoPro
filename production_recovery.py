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
from recovery_controller import RecoveryAction, RecoveryController
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


def _visual_quality_state(short_id: str) -> dict[str, Any]:
    path = BASE / "roteiros" / f"visual_score_{short_id}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "available": False,
            "needs_repair": False,
            "weak_count": 0,
            "scene_count": 0,
            "visual_score": None,
        }
    if not isinstance(data, dict):
        return {
            "available": False,
            "needs_repair": False,
            "weak_count": 0,
            "scene_count": 0,
            "visual_score": None,
        }
    weak = data.get("weak_scenes", []) if isinstance(data.get("weak_scenes"), list) else []
    scenes = data.get("scenes", []) if isinstance(data.get("scenes"), list) else []
    scene_count = len(scenes) or max(len(weak), 1)
    trigger_default = max(4, int((scene_count * 3 + 3) // 4))
    trigger = env_int("SAP_PRE_RENDER_WEAK_SCENES_TRIGGER", trigger_default, 2, 20)
    try:
        score = float(data.get("visual_score", 100.0) or 100.0)
    except (TypeError, ValueError):
        score = 100.0
    minimum_score = env_int("SAP_PRE_RENDER_VISUAL_SCORE_MIN", 62, 40, 90)
    version = str(data.get("version", "") or "")
    has_canonical_contract = (
        "CANONICAL" in version.upper()
        or "measurement_confidence" in data
        or "canonical_coverage" in data
    )
    confidence = str(
        data.get("measurement_confidence", "LOW" if not has_canonical_contract else "HIGH")
        or ("LOW" if not has_canonical_contract else "HIGH")
    ).upper()
    canonical_coverage = float(
        data.get("canonical_coverage", 0.0 if not has_canonical_contract else 1.0)
        or 0.0
    )
    # Shadow-only or legacy visual metadata cannot prove that committed media is weak.
    # Fail closed only when canonical commit evidence is sufficiently complete.
    authoritative = confidence == "HIGH" and canonical_coverage >= 0.75
    needs = authoritative and (len(weak) >= trigger or score < minimum_score)
    return {
        "available": True,
        "needs_repair": needs,
        "authoritative": authoritative,
        "measurement_confidence": confidence,
        "canonical_coverage": canonical_coverage,
        "weak_count": len(weak),
        "weak_scenes": weak,
        "scene_count": scene_count,
        "trigger": trigger,
        "visual_score": score,
        "minimum_score": minimum_score,
    }


def _repair_media(short_id: str, actions: list[dict[str, Any]]) -> bool:
    # Recovery never re-enters retired Stage 6. Media Acquisition V3 owns
    # acquisition and manifest validation; the frozen manifest is authoritative.
    return _append_action(actions, _run(short_id, "media_acquisition_v3.py", "--short-id", short_id))


def _repair_edit_plan(short_id: str, actions: list[dict[str, Any]]) -> bool:
    return _append_action(actions, _run(short_id, "render_plan_v2.py", "--short-id", short_id))


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


def _repair_once(short_id: str) -> dict[str, Any]:
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
    visual_before = _visual_quality_state(sid)
    actions: list[dict[str, Any]] = []

    if before.get("status") == "READY" and not visual_before.get("needs_repair"):
        result = {
            "short_id": sid,
            "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "version": "PRE_RENDER_RECOVERY_1.2_CANONICAL_VISUAL",
            "status": "READY",
            "reason": "no_repair_needed",
            "before": before,
            "after": before,
            "visual_before": visual_before,
            "visual_after": visual_before,
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
        if visual_before.get("needs_repair"):
            failed = not _repair_media(sid, actions)
        elif checks.get("assets") is False:
            failed = not _repair_media(sid, actions)
        elif checks.get("edit_plan") is False:
            failed = not _repair_edit_plan(sid, actions)

        if not failed and checks.get("audio") is False:
            failed = not _repair_audio(sid, actions)

        audio_rebuilt = any(item.get("script") == "audio.py" and item.get("status") == "PASS" for item in actions)
        if not failed and (checks.get("subtitles") is False or audio_rebuilt):
            failed = not _repair_captions(sid, actions)

    after = render_preflight.inspect(sid)
    visual_after = _visual_quality_state(sid)
    if nonrepairable:
        status = "BLOCKED"
        reason = "nonrepairable_preflight:" + ",".join(sorted(set(nonrepairable)))
    elif failed:
        status = "BLOCKED"
        reason = "repair_action_failed"
    elif after.get("status") != "READY":
        status = "BLOCKED"
        reason = "preflight_still_failed"
    elif visual_after.get("needs_repair"):
        status = "BLOCKED"
        reason = (
            "visual_quality_still_low:"
            f"weak={visual_after.get('weak_count')}/{visual_after.get('scene_count')}:"
            f"score={visual_after.get('visual_score')}"
        )
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
        "visual_before": visual_before,
        "visual_after": visual_after,
        "actions": actions,
    }
    _atomic_json(REPORT_DIR / f"recovery_{sid}.json", result)
    return result



def repair(short_id: str) -> dict[str, Any]:
    """Compatibility entry point; all recovery now flows through the canonical controller."""
    result = RecoveryController(max_actions=1).run([
        RecoveryAction(
            name="pre_render_repair_pass",
            run=lambda: _repair_once(short_id),
        )
    ])
    return result.to_dict()

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
