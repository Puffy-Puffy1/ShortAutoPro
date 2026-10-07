#!/usr/bin/env python3
"""Canonical deployment smoke contract for ShortAutoPro."""
from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "main.py",
    "pipeline_contracts.py",
    "first_video.py",
    "media_acquisition_v3.py",
    "media_v3/acquisition.py",
    "media_v3/providers.py",
    "media_v3/diagnostics.py",
    "media_v3/health.py",
    "media_validator_v2.py",
    "shortauto_asset_library.py",
    "render_plan_v2.py",
    "render_engine_v2.py",
    "production_recovery.py",
    "render_preflight.py",
    "production_health.py",
    "audio.py",
    "legenda_dinamica.py",
    "professional_caption_director.py",
    "caption_layout_guard.py",
    "visual_qa.py",
    "release_gate.py",
    "automation/termux_bridge.sh",
)

def fail(message: str) -> None:
    print(f"DEPLOY_SMOKE=FAIL {message}")
    raise SystemExit(1)

def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        fail("missing=" + ",".join(missing))

    for name in REQUIRED:
        path = ROOT / name
        if path.suffix != ".py":
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except Exception as exc:
            fail(f"python_syntax:{name}:{type(exc).__name__}")

    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    for token in (
        '"media_acquisition_v3.py"',
        '"render_plan_v2.py"',
        '"render_engine_v2.py"',
        '"production_recovery.py"',
        '"render_preflight.py"',
        '"release_gate.py"',
        "PROFESSIONAL_CANONICAL",
    ):
        if token not in main_text:
            fail(f"main_contract:{token}")
    if '"media_engine_v2.py"' in main_text:
        fail("legacy_media_engine_v2_in_production_path")
    if "media_stage_runtime.py" in main_text:
        fail("legacy_stage6_controller_in_production_path")
    if '"first-video"' not in main_text:
        fail("first_video_cli_contract")
    if "RENDER_ENGINE_LEGACY_DISABLED" not in main_text:
        fail("legacy_renderer_route_not_disabled")

    render_engine_text = (ROOT / "render_engine_v2.py").read_text(encoding="utf-8")
    if "media-manifest-v2" not in render_engine_text:
        fail("render_v2_manifest_contract")

    contracts = (ROOT / "pipeline_contracts.py").read_text(encoding="utf-8")
    for token in ("PipelineContext", "PipelineStageResult", "PipelineArtifact", "PipelineError"):
        if token not in contracts:
            fail("pipeline_contract_missing:" + token)

    bridge = (ROOT / "automation" / "termux_bridge.sh").read_text(encoding="utf-8")
    for token in ('BRANCH="${SAP_BRIDGE_BRANCH:-termux-stable}"', 'git merge --ff-only "origin/$BRANCH"', "ROLLBACK=PASS", "tools/deploy_smoke.py"):
        if token not in bridge:
            fail("bridge_contract:" + token)

    print("DEPLOY_SMOKE=PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
