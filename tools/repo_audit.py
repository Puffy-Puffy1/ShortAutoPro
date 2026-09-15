#!/usr/bin/env python3
"""Fail-closed repository architecture audit for ShortAutoPro Consolidation 3.0."""
from __future__ import annotations

import json
from pathlib import Path

import map_active_graph

ROOT = Path(__file__).resolve().parents[1]

# These files represent duplicate/retired Short production paths and are not
# allowed back into the operational tree after Consolidation 3.0.
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


def rel_files() -> set[str]:
    return set(map_active_graph.repo_files())


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

    main_text = (ROOT / "main.py").read_text(encoding="utf-8", errors="ignore") if (ROOT / "main.py").is_file() else ""
    profile_text = (ROOT / "profile_run.sh").read_text(encoding="utf-8", errors="ignore") if (ROOT / "profile_run.sh").is_file() else ""
    resume_text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8", errors="ignore") if (ROOT / "resume_short_runtime.py").is_file() else ""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore") if (ROOT / ".gitignore").is_file() else ""

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
