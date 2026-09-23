#!/usr/bin/env python3
"""Lightweight deploy contract used by GitHub CI and the Termux bridge."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "main.py",
    "render_preflight.py",
    "production_recovery.py",
    "production_watchdog.py",
    "production_health.py",
    "visual_query_guard.py",
    "visual_media_refresh.py",
    "resume_short_runtime.py",
    "media_stage_runtime.py",
    "video_professional.py",
    "v6_professional.py",
    "release_gate.py",
    "automation/termux_bridge.sh",
)

LEGACY = (
    "gerar_short.sh",
    "gerar_short_professional.sh",
    "professional_pipeline_runtime.py",
    "resume_short_professional_runtime.py",
    "v6_professional_runtime.py",
    "v6_runtime.py",
    "v6.py",
    "video.py",
    "limpar_storage.sh",
)


def fail(message: str) -> None:
    print(f"DEPLOY_SMOKE=FAIL {message}")
    raise SystemExit(1)


def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing=" + ",".join(missing))

    present_legacy = [name for name in LEGACY if (ROOT / name).exists()]
    if present_legacy:
        fail("legacy=" + ",".join(present_legacy))

    for name in REQUIRED:
        path = ROOT / name
        if path.suffix != ".py":
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            fail(f"python_syntax:{name}:{type(exc).__name__}")

    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    contracts = (
        '"render_preflight.py"',
        '"production_recovery.py"',
        '"visual_query_guard.py"',
        "PROFESSIONAL_CANONICAL",
        '"video_professional.py"',
        '"v6_professional.py"',
        '"release_gate.py"',
    )
    for token in contracts:
        if token not in main_text:
            fail(f"main_contract:{token}")

    if "RETENTION_REVIEW=CONTINUE" not in main_text:
        fail("main_retention_review_contract")

    recovery_text = (ROOT / "production_recovery.py").read_text(encoding="utf-8")
    if '("retention_engine.py", ("--repair", "--enforce"))' in recovery_text:
        fail("recovery_retention_review_is_fatal")

    resume_text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
    if 'status in {"PASS", "REVIEW"}' not in resume_text:
        fail("resume_retention_review_contract")

    bridge = (ROOT / "automation" / "termux_bridge.sh").read_text(encoding="utf-8")
    if 'BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"' not in bridge:
        fail("bridge_branch_contract")
    if 'git merge --ff-only "origin/$BRANCH"' not in bridge:
        fail("bridge_fast_forward_contract")
    if "ROLLBACK=PASS" not in bridge:
        fail("bridge_rollback_contract")
    if "tools/deploy_smoke.py" not in bridge:
        fail("bridge_deploy_smoke_contract")

    print("DEPLOY_SMOKE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
