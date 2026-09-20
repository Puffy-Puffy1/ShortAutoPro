#!/usr/bin/env python3
"""Production-safe script generation recovery.

Runs the canonical roteiro.py. If Gemini repeatedly returns an otherwise
successful HTTP response without usable candidates for the selected topic,
roteiro.py returns code 24. Only that code triggers topic reselection.
Infrastructure/API failures remain hard failures.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from subprocess_guard import run_group
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
ROTEIROS = BASE / "roteiros"
TOPIC_FILE = ROTEIROS / f"topic_{SID}.txt"
REJECTED_FILE = ROTEIROS / f"topic_rejected_{SID}.json"
MAX_TOPIC_RECOVERIES = max(1, min(int(os.getenv("SAP_SCRIPT_TOPIC_RECOVERIES", "3") or 3), 5))
TOPIC_INCOMPATIBLE = 24


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


def read_topic() -> str:
    try:
        return TOPIC_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return ""


def read_rejected() -> dict[str, Any]:
    try:
        value = json.loads(REJECTED_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def reject_topic(topic: str, reason: str) -> None:
    data = read_rejected()
    items = data.get("topics", []) if isinstance(data.get("topics"), list) else []
    normalized = topic.casefold().strip()
    if topic and not any(str(x.get("topic", "")).casefold().strip() == normalized for x in items if isinstance(x, dict)):
        items.append({
            "topic": topic,
            "reason": reason,
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        })
    atomic_json(REJECTED_FILE, {
        "short_id": SID,
        "topics": items,
    })


def run_python(filename: str) -> int:
    try:
        timeout = int(os.getenv("SAP_SCRIPT_SUBPROCESS_TIMEOUT", "420") or 420)
    except (TypeError, ValueError):
        timeout = 420
    timeout = max(120, min(timeout, 900))
    try:
        return run_group(
            [sys.executable, str(BASE / filename)],
            cwd=BASE,
            env=os.environ.copy(),
            check=False,
            timeout=timeout,
        ).returncode
    except subprocess.TimeoutExpired:
        print(
            "SCRIPT_RUNTIME=SUBPROCESS_TIMEOUT "
            f"file={filename} limit={timeout}s"
        )
        return 124


def main() -> int:
    if not SID:
        print("ERRO SCRIPT RUNTIME: SHORT_ID vazio")
        return 1

    for cycle in range(MAX_TOPIC_RECOVERIES + 1):
        topic = read_topic()
        if not topic:
            print("SCRIPT_RUNTIME=NO_TOPIC; selecionando tema")
            if run_python("topic_engine_runtime.py") != 0:
                return 1
            topic = read_topic()

        print(
            f"SCRIPT_RUNTIME_TOPIC={topic or '?'} "
            f"cycle={cycle}/{MAX_TOPIC_RECOVERIES}"
        )

        code = run_python("roteiro.py")
        if code == 0:
            print("SCRIPT_RUNTIME=PASS")
            return 0

        if code != TOPIC_INCOMPATIBLE:
            print(f"SCRIPT_RUNTIME=HARD_FAIL code={code}")
            return code or 1

        if cycle >= MAX_TOPIC_RECOVERIES:
            print("SCRIPT_RUNTIME=TOPIC_RECOVERY_EXHAUSTED")
            return 1

        reject_topic(topic, "gemini_no_usable_candidate")
        print(
            "SCRIPT_RUNTIME=RESELECT_TOPIC "
            f"rejected={topic}"
        )

        try:
            TOPIC_FILE.unlink(missing_ok=True)
        except OSError:
            pass

        if run_python("topic_engine_runtime.py") != 0:
            print("SCRIPT_RUNTIME=TOPIC_RESELECT_FAILED")
            return 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
