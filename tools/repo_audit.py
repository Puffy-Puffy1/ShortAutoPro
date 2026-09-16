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
}

REQUIRED = {
    "main.py",
    "profile_run.sh",
    "resume_short.sh",
    "resume_short_runtime.py",
    "midia.py",
    "media_runtime_adapter_v1.py",
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
    "storage_manager.py",
    "shortautopro_evolution.py",
    "shortautopro_evolution_core.py",
}

REQUIRED_IGNORE_RULES = {
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
    "professional_edit_director.py",
    "professional_edit_repair.py",
    "multi_asset_director.py",
    "retention_engine.py",
    "sound_design_engine.py",
    "speech_director.py",
    "professional_caption_director.py",
    "caption_layout_guard.py",
    "video_professional.py",
    "v6_professional.py",
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

MEDIA_ADAPTER_REQUIRED_TOKENS = {
    '"SAP_VISUAL_UNIFIED": "1"',
    '"SAP_VSE42_BRIDGE": "0"',
    '"SAP_VSE4_QUERY_EXPANSION": "1"',
    '"SAP_VSE42_RESCUE": "0"',
    '"SAP_VG4X": "0"',
    '"VISUAL_INTELLIGENCE_MODE": "SHADOW"',
    "_sap_contextual_rescue",
    "SAP_PROVIDER_SKIP",
    "normalize_candidate",
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
    for path in sorted(REQUIRED - files):
        issues.append(f"required_file_missing:{path}")

    main_text = read_text("main.py")
    profile_text = read_text("profile_run.sh")
    resume_text = read_text("resume_short_runtime.py")
    gitignore = read_text(".gitignore")
    adapter_text = read_text("media_runtime_adapter_v1.py")
    verifier_text = read_text("media_must_verifier.py")
    unified_text = read_text("visual_engine_unified.py")
    vg4x_bridge_text = read_text("vg4x_bridge.py")
    preflight_text = read_text("preflight_check.sh")
    health_text = read_text("health_check.sh")

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
    if "v6_professional.py" not in resume_text or "video_professional.py" not in resume_text:
        issues.append("resume_not_professional_canonical")
    for token in ("STANDARD_ROLLBACK", "SAP_PRO_EDIT", '"video.py"', '"v6_runtime.py"'):
        if token in resume_text:
            issues.append(f"resume_legacy_token:{token}")

    # Canonical media runtime: query expansion enriches the pool, while Visual
    # Unified is the sole production reranker. VI6 is telemetry-only SHADOW.
    for token in sorted(MEDIA_ADAPTER_REQUIRED_TOKENS):
        if token not in adapter_text:
            issues.append(f"media_runtime_contract_missing:{token}")
    for token in sorted(MUST_VERIFIER_REQUIRED_TOKENS):
        if token not in verifier_text:
            issues.append(f"must_verifier_contract_missing:{token}")
    if "from media_must_verifier import verified_must" not in unified_text:
        issues.append("visual_unified_missing_strict_must_verifier")
    if "effective_pre_must_verification" not in unified_text:
        issues.append("visual_unified_missing_must_score_recalibration")
    if "from media_runtime_adapter_v1 import install as install_media_runtime" not in vg4x_bridge_text:
        issues.append("vg4x_bridge_not_routed_to_media_adapter")
    if 'os.getenv("SAP_VG4X_LEGACY", "0") == "1"' not in vg4x_bridge_text:
        issues.append("vg4x_legacy_not_opt_in")

    for text_name, text in (("preflight", preflight_text), ("health", health_text)):
        for token in (
            "media_runtime_adapter_v1.py",
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

    payload = {
        "version": "CONSOLIDATION_3_0_AUDIT",
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
