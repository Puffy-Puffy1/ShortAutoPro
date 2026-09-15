#!/usr/bin/env python3
"""Fail-closed repository architecture audit for ShortAutoPro Consolidation 2.0."""

from __future__ import annotations

import json
from pathlib import Path

import map_active_graph

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_EXACT = {
    "31",
    "SYNC_TEST.TXT",
    ".resume_vi710_after_semantic_fix.sh.pre_segment_fix",
    "gerar_short_professional.sh",
    "professional_pipeline_runtime.py",
    "resume_short_professional_runtime.py",
    "v6_professional_runtime.py",
    "tools/apply_consolidation_1_0.py",
}

REQUIRED = {
    "gerar_short.sh",
    "profile_run.sh",
    "resume_short.sh",
    "resume_short_runtime.py",
    "v6_runtime.py",
    "v6.py",
    "v6_professional.py",
    "video.py",
    "video_professional.py",
    "professional_edit_director.py",
    "professional_edit_repair.py",
    "professional_caption_director.py",
    "professional_quality_gate.py",
    "shortautopro_evolution.py",
    "shortautopro_evolution_core.py",
    "visual_quality_policy_v1.py",
    "docs/CONSOLIDATION_2_0.md",
}

REQUIRED_IGNORE_RULES = {
    "_arquivo_historico/",
    "*.pre_segment_fix",
}


def rel_files() -> set[str]:
    return {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(ROOT).parts
    }


def main() -> int:
    files = rel_files()
    issues: list[str] = []

    for path in sorted(FORBIDDEN_EXACT & files):
        issues.append(f"obsolete_file:{path}")
    for path in sorted(files):
        if path.startswith("_arquivo_historico/"):
            issues.append(f"historical_archive_in_worktree:{path}")

    for path in sorted(REQUIRED - files):
        issues.append(f"required_file_missing:{path}")

    canonical = (ROOT / "gerar_short.sh").read_text(encoding="utf-8", errors="ignore") if (ROOT / "gerar_short.sh").is_file() else ""
    profile_run = (ROOT / "profile_run.sh").read_text(encoding="utf-8", errors="ignore") if (ROOT / "profile_run.sh").is_file() else ""
    resume_shell = (ROOT / "resume_short.sh").read_text(encoding="utf-8", errors="ignore") if (ROOT / "resume_short.sh").is_file() else ""
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8", errors="ignore") if (ROOT / ".gitignore").is_file() else ""

    required_pipeline_tokens = [
        'SAP_PRO_EDIT="${SAP_PRO_EDIT:-1}"',
        "professional_edit_director.py",
        "professional_edit_repair.py",
        "professional_caption_director.py",
        "video_professional.py",
        '"video.py"',
        "v6_runtime.py",
        "professional_quality_gate.py",
    ]
    for token in required_pipeline_tokens:
        if token not in canonical:
            issues.append(f"canonical_pipeline_missing:{token}")

    for rule in sorted(REQUIRED_IGNORE_RULES):
        if rule not in gitignore.splitlines():
            issues.append(f"gitignore_rule_missing:{rule}")

    if "STATUS: QUALITY PASS" in canonical:
        issues.append("hardcoded_final_quality_status")
    if "gerar_short_professional.sh" in profile_run:
        issues.append("profile_run_still_uses_duplicate_generator")
    if "resume_short_professional_runtime.py" in resume_shell:
        issues.append("resume_shell_still_uses_duplicate_runtime")

    _, _, _, active, inactive = map_active_graph.build()
    for path in inactive:
        issues.append(f"inactive_code:{path}")

    payload = {
        "version": "CONSOLIDATION_2_0_AUDIT",
        "status": "PASS" if not issues else "FAIL",
        "files": len(files),
        "active_code": len(active),
        "inactive_code": inactive,
        "issues": issues,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
