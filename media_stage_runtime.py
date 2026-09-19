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
    provider_timeout = (22, 30, 38, 42, 45)[min(round_index, 4)]
    wiki_deadline = (18, 26, 34, 40, 45)[min(round_index, 4)]

    env["SAP_STOCK_RESCUE_MAX_QUERIES"] = str(rescue_budget)
    env["SAP_MUST_RESCUE_MAX_QUERIES"] = str(rescue_budget)
    env["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"] = str(provider_timeout)
    env["SAP_WIKIMEDIA_SEARCH_DEADLINE"] = str(wiki_deadline)
    env["SAP_MEDIA_RECOVERY_ROUND"] = str(round_index + 1)
    return env


def main() -> int:
    if not SID:
        print("ERRO MEDIA STAGE: SHORT_ID vazio")
        return 1
    if not MIDIA.is_file():
        print(f"ERRO MEDIA STAGE: ausente {MIDIA}")
        return 1

    try:
        max_rounds = int(os.getenv("SAP_MEDIA_STAGE_ROUNDS", "3") or 3)
    except ValueError:
        max_rounds = 3
    max_rounds = max(1, min(max_rounds, 5))

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
        proc = subprocess.run(
            [sys.executable, str(MIDIA)],
            cwd=str(BASE),
            env=round_env(round_index),
            check=False,
        )
        elapsed = time.monotonic() - started

        if proc.returncode == 0:
            print(
                f"MEDIA_STAGE_RUNTIME=PASS round={round_index + 1} "
                f"elapsed={elapsed:.1f}s"
            )
            return 0

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
                f"MEDIA_STAGE_RUNTIME=HARD_FAIL code={proc.returncode} "
                "reason=NO_VALID_MISSING_REPORT"
            )
            return proc.returncode or 1

        if previous_missing is not None:
            made_progress = total > previous_total or missing < previous_missing
            if made_progress:
                no_progress_rounds = 0
            else:
                no_progress_rounds += 1
                print(
                    "MEDIA_STAGE_RUNTIME=NO_PROGRESS "
                    f"round={round_index + 1} "
                    f"streak={no_progress_rounds} "
                    f"missing={','.join(map(str, sorted(missing)))} "
                    "action=ESCALATE_NEXT_ROUND"
                )

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
