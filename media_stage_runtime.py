#!/usr/bin/env python3
"""Canonical Stage 6 multi-round recovery controller.

Runs midia.py incrementally. The selector itself remains authoritative and
fail-closed. Successful scenes are preserved by midia.py's existing incremental
checkpoint; only missing scenes are retried. Search budgets increase gradually
without relaxing MUST verification.
"""
from __future__ import annotations

import json
import os
import subprocess
from subprocess_guard import run_group
from runtime_config import env_int
from runtime_config import env_float
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
REPORT = BASE / "reports" / "media" / f"acquisition_missing_{SID}.json"
MIDIA = BASE / "midia.py"


def read_report() -> dict[str, Any]:
    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def missing_numbers(report: dict[str, Any]) -> list[int]:
    out = []
    for item in report.get("missing_scenes", []) if isinstance(report.get("missing_scenes"), list) else []:
        if not isinstance(item, dict):
            continue
        try:
            out.append(int(item.get("scene")))
        except Exception:
            pass
    for item in report.get("pending_scenes", []) if isinstance(report.get("pending_scenes"), list) else []:
        try:
            out.append(int(item))
        except Exception:
            pass
    return sorted(set(out))


def total_from(report: dict[str, Any]) -> int:
    try:
        return int(report.get("total", 0) or 0)
    except Exception:
        return 0


def expected_from(report: dict[str, Any]) -> int:
    try:
        return int(report.get("expected", 0) or 0)
    except Exception:
        return 0


def round_env(round_index: int) -> dict[str, str]:
    env = os.environ.copy()
    env["SHORT_ID"] = SID
    env["SAP_MEDIA_INCREMENTAL"] = "1"

    # Increasing retrieval effort only. MUST acceptance rules are untouched.
    rescue_budget = (2, 4, 6, 8, 8)[min(round_index, 4)]
    # Keep recovery bounded on mobile. The provider layer already runs
    # concurrently, so escalating to 30-45s makes hard scenes dominate the
    # entire Short production without improving acceptance rules.
    provider_timeout = (12, 14, 16, 18, 20)[min(round_index, 4)]
    wiki_deadline = (12, 16, 20, 24, 28)[min(round_index, 4)]

    env["SAP_STOCK_RESCUE_MAX_QUERIES"] = str(rescue_budget)
    env["SAP_MUST_RESCUE_MAX_QUERIES"] = str(rescue_budget)
    env["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"] = str(provider_timeout)
    env["SAP_WIKIMEDIA_SEARCH_DEADLINE"] = str(wiki_deadline)
    env["SAP_MEDIA_RECOVERY_ROUND"] = str(round_index + 1)
    return env


def scene_count_hint() -> int:
    scene_map = BASE / "roteiros" / f"scene_map_{SID}.json"
    try:
        data = json.loads(scene_map.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            for key in ("scenes", "cenas", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return len(value)
    except Exception:
        pass
    return env_int("SHORT_QTD_CENAS", 12, 6, 20)


def current_completed_hint() -> int:
    media_dir = BASE / "imagens" / f"short_{SID}"
    expected = scene_count_hint()
    seen: set[int] = set()
    try:
        for path in media_dir.iterdir():
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}:
                continue
            if not path.stem.startswith("scene_"):
                continue
            try:
                number = int(path.stem.split("_", 1)[1])
                if 1 <= number <= expected and path.is_file() and path.stat().st_size > 1000:
                    seen.add(number)
            except (OSError, ValueError):
                continue
    except OSError:
        return 0
    return len(seen)


def report_signature() -> tuple[int, int, int] | None:
    try:
        stat = REPORT.stat()
        return stat.st_ino, stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


def round_timeout_seconds() -> tuple[int, int]:
    expected = scene_count_hint()
    report = read_report()
    pending = missing_numbers(report)
    if pending:
        remaining = len(pending)
    else:
        remaining = max(1, expected - current_completed_hint())
    base = env_int("SAP_MEDIA_ROUND_TIMEOUT", 240, 60, 900)
    scene_budget = env_float("SAP_MEDIA_SCENE_BUDGET_SECONDS", 75.0, 30.0, 180.0)
    grace = env_int("SAP_MEDIA_ROUND_GRACE_SECONDS", 45, 15, 180)
    dynamic = int(remaining * scene_budget + grace)
    return max(base, min(dynamic, 900)), remaining


def main() -> int:
    if not SID:
        print("ERRO MEDIA STAGE: SHORT_ID vazio")
        return 1
    if not MIDIA.is_file():
        print(f"ERRO MEDIA STAGE: ausente {MIDIA}")
        return 1

    max_rounds = env_int("SAP_MEDIA_STAGE_ROUNDS", 4, 1, 5)

    previous_missing: set[int] | None = None
    previous_total = -1
    no_progress_rounds = 0

    for round_index in range(max_rounds):
        print()
        print("================================")
        print(f"MEDIA STAGE RECOVERY {round_index + 1}/{max_rounds}")
        print("================================")
        print(
            "Policy: incremental cache + retrieve more; "
            "MUST verification remains strict"
        )

        started = time.monotonic()
        round_timeout, remaining_hint = round_timeout_seconds()
        print(
            "MEDIA_STAGE_RUNTIME=BUDGET "
            f"round={round_index + 1} remaining={remaining_hint} "
            f"timeout={round_timeout}s "
            f"scene_budget={env_float('SAP_MEDIA_SCENE_BUDGET_SECONDS', 75.0, 30.0, 180.0):.0f}s"
        )

        previous_report = report_signature()
        try:
            proc = run_group(
                [sys.executable, str(MIDIA)],
                cwd=str(BASE),
                env=round_env(round_index),
                check=False,
                timeout=round_timeout,
            )
            returncode = proc.returncode
        except subprocess.TimeoutExpired:
            returncode = 124
            print(
                "MEDIA_STAGE_RUNTIME=ROUND_TIMEOUT "
                f"round={round_index + 1} limit={round_timeout}s"
            )

        elapsed = time.monotonic() - started

        if returncode == 0:
            print(
                f"MEDIA_STAGE_RUNTIME=PASS round={round_index + 1} "
                f"elapsed={elapsed:.1f}s"
            )
            return 0

        if report_signature() == previous_report:
            print(f"MEDIA_STAGE_RUNTIME=HARD_FAIL code={returncode} reason=STALE_MISSING_REPORT")
            return returncode or 1
        report = read_report()
        missing = set(missing_numbers(report))
        total = total_from(report)
        expected = expected_from(report)

        print(
            "MEDIA_STAGE_RUNTIME=PARTIAL "
            f"round={round_index + 1} total={total}/{expected or '?'} "
            f"missing={','.join(map(str, sorted(missing))) or '?'} "
            f"elapsed={elapsed:.1f}s"
        )

        # If midia failed for a reason unrelated to an incomplete-media report,
        # preserve that real failure instead of masking it with retries.
        if not report or not missing:
            print(
                f"MEDIA_STAGE_RUNTIME=HARD_FAIL code={returncode} "
                "reason=NO_VALID_MISSING_REPORT"
            )
            return returncode or 1

        if previous_missing is not None:
            made_progress = total > previous_total or missing < previous_missing
            if made_progress:
                no_progress_rounds = 0
            else:
                no_progress_rounds += 1
                action = (
                    "STOP_BOUNDED_RECOVERY"
                    if no_progress_rounds >= 2
                    else "ESCALATE_NEXT_ROUND"
                )
                print(
                    "MEDIA_STAGE_RUNTIME=NO_PROGRESS "
                    f"round={round_index + 1} "
                    f"streak={no_progress_rounds} "
                    f"missing={','.join(map(str, sorted(missing)))} "
                    f"action={action}"
                )
                if no_progress_rounds >= 2:
                    print(
                        "MEDIA_STAGE_RUNTIME=EARLY_STOP "
                        "reason=TWO_CONSECUTIVE_NO_PROGRESS_ROUNDS"
                    )
                    break

        previous_missing = missing
        previous_total = total

        if round_index + 1 < max_rounds:
            next_budget = (2, 4, 6, 8, 8)[min(round_index + 1, 4)]
            print(
                "MEDIA_STAGE_RUNTIME=RETRY_MISSING_ONLY "
                f"next_round={round_index + 2} "
                f"next_budget={next_budget} "
                f"missing={','.join(map(str, sorted(missing)))}"
            )

    final = read_report()
    print(
        "MEDIA_STAGE_RUNTIME=EXHAUSTED "
        f"missing={','.join(map(str, missing_numbers(final))) or '?'}"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
