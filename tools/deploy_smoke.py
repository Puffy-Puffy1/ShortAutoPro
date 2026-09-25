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
    "media_emergency_fallback.py",
    "media_master_gate.py",
    "visual_qa.py",
    "production_manifest.py",
    "final_quality.py",
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

    if (
        "def allocate_id(*, reuse_existing: bool = False)" not in main_text
        or '"--reuse-short-id"' not in main_text
        or 'os.getenv("SAP_REUSE_SHORT_ID"' in main_text
    ):
        fail("fresh_run_id_isolation_contract")

    recovery_text = (ROOT / "production_recovery.py").read_text(encoding="utf-8")
    if '("retention_engine.py", ("--repair", "--enforce"))' in recovery_text:
        fail("recovery_retention_review_is_fatal")

    resume_text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
    if 'status in {"PASS", "REVIEW"}' not in resume_text:
        fail("resume_retention_review_contract")

    media_stage_text = (ROOT / "media_stage_runtime.py").read_text(encoding="utf-8")
    if 'SAP_MEDIA_SCENE_BUDGET_SECONDS", 18.0' not in media_stage_text:
        fail("stage6_outer_budget_not_aligned")
    if "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_PASS" not in media_stage_text:
        fail("stage6_final_editorial_contract_missing")
    if '"post_scene_plan"' not in resume_text or "RESUME_FROM_STAGE6=YES" not in resume_text:
        fail("resume_stage6_checkpoint_contract")

    if (
        "def media_integrity_ok(" not in resume_text
        or "RELEASE_GATE_1.6_VISUAL_CONTENT_INTEGRITY" not in resume_text
    ):
        fail("resume_completed_visual_revalidation_contract")

    media_fallback_text = (ROOT / "media_emergency_fallback.py").read_text(encoding="utf-8")
    media_gate_text = (ROOT / "media_master_gate.py").read_text(encoding="utf-8")
    render_preflight_text = (ROOT / "render_preflight.py").read_text(encoding="utf-8")
    visual_qa_text = (ROOT / "visual_qa.py").read_text(encoding="utf-8")
    release_text = (ROOT / "release_gate.py").read_text(encoding="utf-8")
    midia_text = (ROOT / "midia.py").read_text(encoding="utf-8")

    if "SAP_MEDIA_EDITORIAL_NEUTRAL=DISABLED" not in media_fallback_text:
        fail("neutral_editorial_disable_contract")
    if "neutral_editorial_scene_" not in media_gate_text:
        fail("media_gate_neutral_placeholder_contract")
    if "neutral editorial placeholder proibido" not in render_preflight_text:
        fail("preflight_neutral_placeholder_contract")
    if "blank_opening_frame" not in visual_qa_text:
        fail("visual_qa_blank_opening_contract")
    if "rendered_visual_content_not_verified" not in release_text:
        fail("release_rendered_content_contract")
    if 'SAP_MEDIA_INROUND_EDITORIAL", "0"' not in midia_text:
        fail("midia_neutral_deferred_contract")

    resilience_text = (ROOT / "media_external_resilience.py").read_text(encoding="utf-8")
    if "SAP_MEDIA_PROVIDER_CONTROLLER_TIMEOUT" not in midia_text:
        fail("provider_controller_timeout_contract_missing")
    if "health_penalty=NO" not in midia_text or "wait(" not in midia_text:
        fail("provider_head_of_line_fix_missing")
    if "SAP_MEDIA_PROVIDER_CIRCUIT_BACKOFF" not in midia_text:
        fail("provider_transient_backoff_contract_missing")
    if 'VERSION = "1.2"' not in resilience_text:
        fail("media_resilience_version_contract")
    if "TRANSIENT_DEDUP_SECONDS" not in resilience_text:
        fail("media_resilience_dedupe_contract")

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
