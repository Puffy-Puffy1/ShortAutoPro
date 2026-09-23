#!/usr/bin/env python3
"""Production watchdog state for the canonical ShortAutoPro pipeline.

The actual stage process termination remains owned by subprocess_guard/run_group
timeouts. This module records heartbeats and detects stale or orphaned runs
without creating a second production pipeline.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime_config import env_int

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
REPORT_DIR = BASE / "reports" / "production"


def _now() -> datetime:
    return datetime.now().astimezone()


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


def _parse_time(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone()


def _pid_from_lock(short_id: str) -> int | None:
    path = BASE / ".locks" / "runs" / f"{short_id}.lock"
    try:
        value = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return value if value > 0 else None


def _pid_alive(pid: int | None) -> bool | None:
    if pid is None:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


def record_heartbeat(state: dict[str, Any]) -> None:
    """Persist a compact watchdog snapshot. Never mutates production artifacts."""
    try:
        short_id = str(state.get("short_id", "") or "").strip()
        if not short_id:
            return
        payload = {
            "short_id": short_id,
            "generated_at": _now().isoformat(timespec="seconds"),
            "pipeline_status": state.get("status"),
            "current_stage": state.get("current_stage"),
            "last_stage_status": state.get("last_stage_status"),
            "heartbeat_at": state.get("heartbeat_at") or state.get("updated_at"),
            "pid": os.getpid(),
            "status": "ACTIVE" if str(state.get("status", "")).upper() == "RUNNING" else "IDLE",
        }
        _atomic_json(REPORT_DIR / f"watchdog_{short_id}.json", payload)
    except Exception:
        pass


def inspect(short_id: str) -> dict[str, Any]:
    sid = str(short_id or "").strip()
    state_path = BASE / ".sap_state" / f"pipeline_{sid}.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}

    heartbeat = _parse_time(state.get("heartbeat_at") or state.get("updated_at") or state.get("started_at"))
    age = None
    if heartbeat is not None:
        age = max(0.0, (_now() - heartbeat).total_seconds())

    stale_seconds = env_int("SAP_WATCHDOG_STALE_SECONDS", 1500, 120, 7200)
    pipeline_status = str(state.get("status", "") or "").upper()
    pid = _pid_from_lock(sid)
    alive = _pid_alive(pid)

    issues: list[dict[str, Any]] = []
    status = "OK"
    if not state:
        issues.append({"code": "STATE_MISSING", "severity": "WARN"})
        status = "UNKNOWN"
    elif pipeline_status == "RUNNING" and age is not None and age > stale_seconds:
        severity = "BLOCK" if alive is False else "WARN"
        issues.append({
            "code": "STALE_RUN",
            "severity": severity,
            "age_seconds": round(age, 1),
            "threshold_seconds": stale_seconds,
        })
        status = "STALE"
    elif pipeline_status == "RUNNING" and alive is False:
        issues.append({"code": "ORPHANED_RUN", "severity": "BLOCK"})
        status = "ORPHANED"

    report = {
        "short_id": sid,
        "generated_at": _now().isoformat(timespec="seconds"),
        "status": status,
        "pipeline_status": pipeline_status or None,
        "current_stage": state.get("current_stage") if state else None,
        "last_stage_status": state.get("last_stage_status") if state else None,
        "heartbeat_age_seconds": round(age, 1) if age is not None else None,
        "stale_threshold_seconds": stale_seconds,
        "pid": pid,
        "pid_alive": alive,
        "issues": issues,
        "timeout_owner": "subprocess_guard.run_group",
    }
    if sid:
        _atomic_json(REPORT_DIR / f"watchdog_{sid}.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro production watchdog")
    parser.add_argument("--short-id", default=os.getenv("SHORT_ID", ""))
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    report = inspect(args.short_id)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "WATCHDOG "
            f"status={report['status']} "
            f"pipeline={report.get('pipeline_status') or '-'} "
            f"stage={report.get('current_stage') or '-'} "
            f"age={report.get('heartbeat_age_seconds')}"
        )
        for issue in report["issues"]:
            print(f"WATCHDOG_{issue['severity']}={issue['code']}")
    if args.enforce and any(item.get("severity") == "BLOCK" for item in report["issues"]):
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
