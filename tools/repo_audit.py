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
    "media_acquisition_v3.py",
    "media_v3/__init__.py",
    "media_v3/acquisition.py",
    "media_v3/providers.py",
    "media_v3/diagnostics.py",
    "media_v3/health.py",
    "media_v3/query.py",
    "pipeline_contracts.py",
    "runtime_config.py",
    "subprocess_guard.py",
    "production_profiler.py",
    "production_doctor.py",
    "profile_run.sh",
    "resume_short.sh",
    "resume_short_runtime.py",
    "midia.py",
    "media_runtime_adapter_v1.py",
    "media_runtime_adapter_v2.py",
    "media_must_verifier.py",
    "vg4x_bridge.py",
    "visual_engine_unified.py",
    "visual_query_expansion_v4.py",
    "visual_query_planner_v4.py",
    "visual_selection_engine_v4.py",
    "video_professional.py",
    "v6_professional.py",
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
    "media_acquisition_v3.py",
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

MEDIA_ADAPTER_V1_REQUIRED_TOKENS = {
    '"SAP_VISUAL_UNIFIED": "1"',
    '"SAP_VSE4": "0"',
    '"SAP_VSE4_RESCUE": "0"',
    '"SAP_VSE_V42": "0"',
    '"SAP_VSE42": "0"',
    '"SAP_VSE42_RUNTIME": "0"',
    '"SAP_VSE42_BRIDGE": "0"',
    '"SAP_VSE42_RESCUE": "0"',
    '"SAP_VSE4_QUERY_EXPANSION": "1"',
    '"SAP_VG4X": "0"',
    '"VISUAL_INTELLIGENCE_MODE": "SHADOW"',
    "from media_must_verifier import verified_must",
    "_sap_contextual_rescue",
    "_sap_declared_must_hits",
    "_sap_verified_must_hits",
    'candidate["must_hits"] = verified',
    "SAP_PROVIDER_SKIP",
    "normalize_candidate",
}

MEDIA_ADAPTER_V2_REQUIRED_TOKENS = {
    "import media_runtime_adapter_v1 as v1",
    "neutral_context_score",
    "SAFE_CONTEXTUAL_RESCUE_NEUTRAL_MUST",
    "_disable_legacy_vse42_authority",
    'namespace["_vse42_enabled"] = disabled',
    'namespace["_vse42_finalize_pool"] = passthrough',
    'namespace["_vse42_note_success"] = no_note',
    'namespace["_vse42_commit_media"] = no_commit',
    '"authority": "VISUAL_UNIFIED"',
    "MEDIA_RUNTIME_ADAPTER_V2=INSTALLED",
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
    adapter_v1_text = read_text("media_runtime_adapter_v1.py")
    adapter_v2_text = read_text("media_runtime_adapter_v2.py")
    verifier_text = read_text("media_must_verifier.py")
    unified_text = read_text("visual_engine_unified.py")
    vg4x_bridge_text = read_text("vg4x_bridge.py")
    preflight_text = read_text("preflight_check.sh")
    health_text = read_text("health_check.sh")
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
    for token in ("media_acquisition_v3.py", "render_plan_v2.py", "render_engine_v2.py"):
        if token not in resume_text:
            issues.append(f"resume_v2_contract_missing:{token}")
    for token in ("STANDARD_ROLLBACK", "SAP_PRO_EDIT", '"video.py"', '"v6_runtime.py"', "media_stage_runtime.py", "video_professional.py", "v6_professional.py", "retention_engine.py"):
        if token in resume_text:
            issues.append(f"resume_legacy_token:{token}")

    # Canonical media runtime: V1 owns normalization/strict MUST verification;
    # V2 is the production reliability layer that preserves Visual Unified as
    # the single winner authority while query expansion only enriches pools.
    for token in sorted(MEDIA_ADAPTER_V1_REQUIRED_TOKENS):
        if token not in adapter_v1_text:
            issues.append(f"media_runtime_v1_contract_missing:{token}")
    for token in sorted(MEDIA_ADAPTER_V2_REQUIRED_TOKENS):
        if token not in adapter_v2_text:
            issues.append(f"media_runtime_v2_contract_missing:{token}")
    for token in sorted(MUST_VERIFIER_REQUIRED_TOKENS):
        if token not in verifier_text:
            issues.append(f"must_verifier_contract_missing:{token}")
    if "from media_must_verifier import verified_must" not in unified_text:
        issues.append("visual_unified_missing_strict_must_verifier")
    if "effective_pre_must_verification" not in unified_text:
        issues.append("visual_unified_missing_must_score_recalibration")
    if "from media_runtime_adapter_v2 import install as install_media_runtime" not in vg4x_bridge_text:
        issues.append("vg4x_bridge_not_routed_to_media_adapter_v2")
    if 'os.getenv("SAP_VG4X_LEGACY", "0") == "1"' not in vg4x_bridge_text:
        issues.append("vg4x_legacy_not_opt_in")

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

    for text_name, text in (("preflight", preflight_text), ("health", health_text)):
        for token in (
            "media_runtime_adapter_v1.py",
            "media_runtime_adapter_v2.py",
            "media_must_verifier.py",
            "vg4x_bridge.py",
            "visual_engine_unified.py",
            "visual_query_expansion_v4.py",
        ):
            if token not in text:
                issues.append(f"{text_name}_media_runtime_missing:{token}")

    ignore_lines = set(gitignore.splitlines())
    for rule in sorted(REQUIRED_IGNORE_RULES):
        if rule not in ignore_lines:
            issues.append(f"gitignore_rule_missing:{rule}")

    _, _, seeds, active, inactive = map_active_graph.build()
    if "main.py" not in seeds:
        issues.append("main_not_active_graph_seed")
    if "main.py" not in active:
        issues.append("main_not_active")

    # Consolidation 3.0.1 rule: tracked operational code may not be orphaned.
    # Tests and workflows are graph seeds, so any remaining .py/.sh entry here
    # is neither production-reachable nor test-reachable and must be removed or
    # deliberately wired into the canonical architecture.
    canonical_v3 = {
        "media_v3/__init__.py",
        "media_v3/acquisition.py",
        "media_v3/providers.py",
        "media_v3/diagnostics.py",
        "media_v3/health.py",
        "media_v3/query.py",
        "tests/test_media_acquisition_v3.py",
        "tests/test_media_acquisition_v3_stress.py",
        "tests/test_media_v3_full_pipeline_stress.py",
        "tests/test_media_v3_render_integration.py",
    }
    for path in inactive:
        if path not in canonical_v3:
            issues.append(f"inactive_code:{path}")

    payload = {
        "version": "CONSOLIDATION_3_0_3_AUDIT",
        "scope": "tracked_git_files",
        "status": "PASS" if not issues else "FAIL",
        "files": len(files),
        "active_code": len(active),
        "inactive_code_count": len(inactive),
        "inactive_code": inactive,
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
