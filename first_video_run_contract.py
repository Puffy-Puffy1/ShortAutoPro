#!/usr/bin/env python3
"""Separate video-generation proof from the independent release-approval gate.

This helper never changes a release decision. It only lets FIRST_VIDEO prove
that a valid output was generated when the sole final blocker is human approval.
FFprobe runs as a separate required workflow step after this check.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

HUMAN_APPROVAL_BLOCK = "shortauto_brain_approval_required"
HUMAN_APPROVAL_DECISIONS = {"HUMAN_APPROVAL_REQUIRED", "HUMAN_REVIEW_REQUIRED"}
RELEASE_ALLOWED_DECISIONS = {"PUBLISH", "ACCEPTABLE"}


def evaluate_run_result(
    base: str | Path,
    short_id: str,
    exit_code: int,
) -> tuple[bool, str]:
    """Return whether the run proved generation without overriding release gates."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(short_id or "")):
        return False, "invalid_short_id"

    root = Path(base).resolve()
    video_path = root / "videos" / f"short_v6_{short_id}.mp4"
    if not video_path.is_file():
        return False, "current_run_mp4_missing"
    try:
        if video_path.stat().st_size <= 0:
            return False, "current_run_mp4_empty"
    except OSError:
        return False, "current_run_mp4_unreadable"

    report_path = root / "manifests" / f"{short_id}_release.json"
    try:
        report: Any = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False, "current_run_release_report_missing_or_invalid"
    if not isinstance(report, dict) or report.get("short_id") != short_id:
        return False, "release_report_identity_mismatch"

    decision = str(report.get("decision") or "").upper()
    critical = report.get("critical")
    brain = report.get("shortauto_brain")
    brain = brain if isinstance(brain, dict) else {}
    brain_decision = str(
        brain.get("decision")
        or (brain.get("quality") or {}).get("decision")
        if isinstance(brain.get("quality"), dict)
        else brain.get("decision") or ""
    ).upper()

    if exit_code == 0:
        if decision not in RELEASE_ALLOWED_DECISIONS or critical:
            return False, "pipeline_exit_success_conflicts_with_release_report"
        return True, "generation_and_release_gate_pass"

    if exit_code != 1:
        return False, f"unexpected_pipeline_exit_code_{exit_code}"

    expected_approval_only = (
        decision == "BLOCK"
        and critical == [HUMAN_APPROVAL_BLOCK]
        and report.get("brain_enforced") is True
        and brain_decision in HUMAN_APPROVAL_DECISIONS
    )
    if expected_approval_only:
        return True, "generation_pass_release_held_for_human_approval"

    return False, "pipeline_failed_or_release_gate_has_additional_blockers"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--short-id", required=True)
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument(
        "--base",
        default=os.getenv("SHORTAUTOPRO_BASE", os.getcwd()),
    )
    args = parser.parse_args()

    accepted, reason = evaluate_run_result(args.base, args.short_id, args.exit_code)
    if accepted and reason == "generation_pass_release_held_for_human_approval":
        print(
            "FIRST_VIDEO_GENERATION=PASS "
            "RELEASE_DECISION=BLOCK "
            "reason=HUMAN_APPROVAL_REQUIRED"
        )
        print("Release approval remains required; no publish gate was bypassed.")
        return 0
    if accepted:
        print("FIRST_VIDEO_GENERATION=PASS RELEASE_DECISION=PASS")
        return 0

    print(f"FIRST_VIDEO_GENERATION=FAIL reason={reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
