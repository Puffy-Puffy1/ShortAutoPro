#!/usr/bin/env python3
"""Fail-closed repository architecture audit for ShortAutoPro Consolidation 3.0."""
from __future__ import annotations

import json
from pathlib import Path

import map_active_graph

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_EXACT = {
    "31",
    "SYNC_TEST.TXT",
    ".resume_vi710_after_semantic_fix.sh.pre_segment_fix",
    "gerar_short.sh",
    "gerar_short_professional.sh",
    "professional_pipeline_runtime.py",
    "resume_short_professional_runtime.py",
    "v6_professional_runtime.py",
    "v6_runtime.py",
    "v6.py",
    "video.py",
    "limpar_storage.sh",
    "tools/apply_consolidation_1_0.py",
    "docs/CONSOLIDATION_1_0.md",
    "docs/CONSOLIDATION_1_0_ACTIVE_GRAPH.json",
    "docs/CONSOLIDATION_1_0_VALIDATION.md",
    "docs/CONSOLIDATION_2_0.md",
    "manifests/visual_selection_engine_v2_certification.json",
    "tests_sim/test_consolidation_2_0.py",
    "tests_sim/test_professional_polish_v2.py",
    "tests_sim/test_termux_render_speed_v2.py",
    "tests_sim/test_v6_runtime.py",
    "tests_sim/test_v6_runtime_codecs.py",
}

REQUIRED = {
    "main.py",
    "runtime_config.py",
    "subprocess_guard.py",
    "production_profiler.py",
    "production_doctor.py",
    "profile_run.sh",
    "resume_short.sh",
    "resume_short_runtime.py",
    "production_ready.sh",
    "media_engine_v2.py",
    "media_provider_v2.py",
    "media_provider_router_v2.py",
    "media_validator_v2.py",
    "media_must_verifier.py",
    "media_visual_verifier.py",
    "media_external_resilience.py",
    "media_quality_report.py",
    "render_plan_v2.py",
    "render_engine_v2.py",
    "professional_edit_director.py",
    "professional_edit_repair.py",
    "professional_caption_director.py",
    "professional_quality_gate.py",
    "visual_director.py",
    "visual_continuity_engine.py",
    "visual_score_engine.py",
    "multi_asset_director.py",
    "retention_engine.py",
    "sound_design_engine.py",
    "speech_director.py",
    "caption_layout_guard.py",
    "audio_finalizer.py",
    "visual_qa.py",
    "release_gate.py",
    "release_artifact_guard.py",
    "storage_manager.py",
    "shortautopro_evolution.py",
    "shortautopro_evolution_core.py",
    "tools/purge_legacy_runtime.py",
}

REQUIRED_IGNORE_RULES = {
    "queue/batch_state.json",
    "queue/.batch_recovery.lock",
    "queue/.batch_recovery.lockdir/",
    "reports/performance/",
    "reports/production/",
    "_arquivo_historico/",
    "*.pre_segment_fix",
    "imagens/short_*/",
    "roteiros/pro_caption_*.json",
    "roteiros/pro_edit_plan_*.json",
    "roteiros/pro_edit_runtime_*.json",
    "roteiros/retention_*.json",
    "roteiros/sound_design_*.json",
    "roteiros/multi_asset_*.json",
    "roteiros/visual_score_*.json",
    "roteiros/visual_continuity_*.json",
    "roteiros/caption_layout_*.json",
    "roteiros/speech_plan_*.json",
    "roteiros/visual_qa_*.json",
    "credits/attribution_client_*.txt",
    "credits/ledger_client_*.json",
    "credits/short_client_*.txt",
    "manifests/client_*.json",
}

MAIN_REQUIRED_TOKENS = {
    "PROFESSIONAL_CANONICAL",
    "media_engine_v2.py",
    "render_plan_v2.py",
    "render_engine_v2.py",
    "multi_asset_director.py",
    "sound_design_engine.py",
    "speech_director.py",
    "professional_caption_director.py",
    "caption_layout_guard.py",
    "audio_finalizer.py",
    "visual_qa.py",
    "professional_quality_gate.py",
    "release_gate.py",
    "storage_manager.py",
}

MAIN_FORBIDDEN_TOKENS = {
    "STANDARD_ROLLBACK",
    "SAP_PRO_EDIT",
    '"video.py"',
    '"v6.py"',
    '"v6_runtime.py"',
    '"gerar_short.sh"',
}

MEDIA_ENGINE_V2_REQUIRED_TOKENS = {
    "from media_provider_v2 import MediaProviderV2",
    "from media_visual_verifier import verify_image_requirements",
    "from media_must_verifier import verified_must",
    "def build_manifest(",
}

MEDIA_PROVIDER_V2_REQUIRED_TOKENS = {
    "from media_provider_router_v2 import MediaProviderRouterV2",
}

MEDIA_ROUTER_V2_REQUIRED_TOKENS = {
    "from media_validator_v2 import validate",
    "from media_external_resilience import",
}

MUST_VERIFIER_REQUIRED_TOKENS = {
    "asset_evidence_text",
    "strict_concept_hits",
    "verified_must",
    "query",
    "search_query",
    "visual_query",
}


def rel_files() -> set[str]:
    return set(map_active_graph.repo_files())


def read_text(path: str) -> str:
    target = ROOT / path
    return target.read_text(encoding="utf-8", errors="ignore") if target.is_file() else ""


def main() -> int:
    files = rel_files()
    issues: list[str] = []

    for path in sorted(FORBIDDEN_EXACT & files):
        issues.append(f"obsolete_file:{path}")
    for path in sorted(files):
        if path.startswith("_arquivo_historico/"):
            issues.append(f"historical_archive_tracked:{path}")
        if path.startswith("imagens/short_"):
            issues.append(f"generated_media_tracked:{path}")
        if path.startswith("roteiros/"):
            issues.append(f"generated_runtime_tracked:{path}")
        if path.startswith("manifests/20") and path.endswith(".json"):
            issues.append(f"generated_manifest_tracked:{path}")
        if (
            path.startswith("credits/attribution_20")
            or path.startswith("credits/ledger_20")
            or path.startswith("credits/short_20")
        ):
            issues.append(f"generated_credit_tracked:{path}")
    for path in sorted(REQUIRED - files):
        issues.append(f"required_file_missing:{path}")

    main_text = read_text("main.py")
    profile_text = read_text("profile_run.sh")
    resume_text = read_text("resume_short_runtime.py")
    gitignore = read_text(".gitignore")
    media_engine_text = read_text("media_engine_v2.py")
    media_provider_text = read_text("media_provider_v2.py")
    media_router_text = read_text("media_provider_router_v2.py")
    verifier_text = read_text("media_must_verifier.py")
    preflight_text = read_text("preflight_check.sh")
    health_text = read_text("health_check.sh")
    readiness_text = read_text("production_ready.sh")
    purge_text = read_text("tools/purge_legacy_runtime.py")

    for token in sorted(MAIN_REQUIRED_TOKENS):
        if token not in main_text:
            issues.append(f"canonical_pipeline_missing:{token}")
    for token in sorted(MAIN_FORBIDDEN_TOKENS):
        if token in main_text:
            issues.append(f"canonical_pipeline_legacy_token:{token}")

    if 'MAIN="$BASE/main.py"' not in profile_text or "PROFESSIONAL_CANONICAL" not in profile_text:
        issues.append("profile_run_not_canonical")
    if "STANDARD_ROLLBACK" in profile_text or "SAP_PRO_EDIT" in profile_text:
        issues.append("profile_run_has_legacy_mode")
    for token in ("media_engine_v2.py", "render_plan_v2.py", "render_engine_v2.py"):
        if token not in resume_text:
            issues.append(f"resume_v2_contract_missing:{token}")
    for token in ("STANDARD_ROLLBACK", "SAP_PRO_EDIT", '"video.py"', '"v6_runtime.py"', "media_stage_runtime.py", "video_professional.py", "v6_professional.py", "retention_engine.py"):
        if token in resume_text:
            issues.append(f"resume_legacy_token:{token}")

    # Canonical media authority: Media Engine V2 owns acquisition and freeze;
    # the provider facade/router own provider access, validation and resilience.
    for token in sorted(MEDIA_ENGINE_V2_REQUIRED_TOKENS):
        if token not in media_engine_text:
            issues.append(f"media_engine_v2_contract_missing:{token}")
    for token in sorted(MEDIA_PROVIDER_V2_REQUIRED_TOKENS):
        if token not in media_provider_text:
            issues.append(f"media_provider_v2_contract_missing:{token}")
    for token in sorted(MEDIA_ROUTER_V2_REQUIRED_TOKENS):
        if token not in media_router_text:
            issues.append(f"media_router_v2_contract_missing:{token}")
    for token in sorted(MUST_VERIFIER_REQUIRED_TOKENS):
        if token not in verifier_text:
            issues.append(f"must_verifier_contract_missing:{token}")

    for token in (
        "gerar_short.sh",
        "gerar_short_professional.sh",
        "professional_pipeline_runtime.py",
        "resume_short_professional_runtime.py",
        "v6_professional_runtime.py",
        "v6_runtime.py",
        "v6.py",
        "video.py",
        "limpar_storage.sh",
        "_arquivo_historico",
    ):
        if token not in purge_text:
            issues.append(f"legacy_purge_contract_missing:{token}")
    if 'p.run("0 - LEGACY RUNTIME PURGE", "tools/purge_legacy_runtime.py")' not in main_text:
        issues.append("canonical_pipeline_missing_legacy_purge")
    if 'python "$BASE/tools/purge_legacy_runtime.py"' not in preflight_text:
        issues.append("preflight_missing_legacy_purge")

    for text_name, text in (
        ("preflight", preflight_text),
        ("health", health_text),
        ("production_ready", readiness_text),
    ):
        for token in (
            "media_engine_v2.py",
            "media_provider_v2.py",
            "media_provider_router_v2.py",
            "media_validator_v2.py",
            "media_must_verifier.py",
            "media_visual_verifier.py",
            "media_external_resilience.py",
            "render_plan_v2.py",
            "render_engine_v2.py",
        ):
            if token not in text:
                issues.append(f"{text_name}_media_runtime_missing:{token}")
        for legacy in (
            "media_stage_runtime.py",
            "midia.py",
            "media_master_gate.py",
            "media_runtime_adapter_v1.py",
            "media_runtime_adapter_v2.py",
            "vg4x_bridge.py",
            "visual_engine_unified.py",
            "video_professional.py",
            "v6_professional.py",
        ):
            if legacy in text:
                issues.append(f"{text_name}_requires_legacy_media_runtime:{legacy}")

    ignore_lines = set(gitignore.splitlines())
    for rule in sorted(REQUIRED_IGNORE_RULES):
        if rule not in ignore_lines:
            issues.append(f"gitignore_rule_missing:{rule}")

    _, _, seeds, active, inactive, classification = map_active_graph.build_analysis()
    production_code = classification["production_code"]
    test_only_code = classification["test_only_code"]
    support_code = classification["support_code"]
    if "main.py" not in seeds:
        issues.append("main_not_active_graph_seed")
    if "main.py" not in active:
        issues.append("main_not_active")
    if "main.py" not in production_code:
        issues.append("main_not_production_reachable")

    # Only files that are unreachable from both production and test/CI roots
    # are treated as orphaned. Test-only code is reported separately so legacy
    # compatibility coverage stays visible without being mistaken for runtime.
    for path in inactive:
        issues.append(f"inactive_code:{path}")

    payload = {
        "version": "CONSOLIDATION_3_0_4_AUDIT",
        "scope": "tracked_git_files",
        "classification": "static_reference_graph",
        "status": "PASS" if not issues else "FAIL",
        "files": len(files),
        "active_code": len(active),
        "production_code_count": len(production_code),
        "production_code": production_code,
        "test_only_code_count": len(test_only_code),
        "test_only_code": test_only_code,
        "support_code_count": len(support_code),
        "support_code": support_code,
        "inactive_code_count": len(inactive),
        "inactive_code": inactive,
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
