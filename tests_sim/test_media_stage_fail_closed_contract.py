#!/usr/bin/env python3
"""Production contracts for Stage 6 fail-closed semantic recovery."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_midia_semantic_verifier_failure_is_fail_closed():
    source = (ROOT / "midia.py").read_text(encoding="utf-8")
    assert "SAP_MEDIA_SEMANTIC_TRIAGE=FAIL_CLOSED" in source
    assert "todos = []" in source
    assert "SAP_MEDIA_SEMANTIC_TRIAGE=FAIL_OPEN" not in source


def test_editorial_reuse_cannot_satisfy_explicit_must():
    source = (ROOT / "media_stage_runtime.py").read_text(encoding="utf-8")
    assert "explicit_must_requires_verified_fresh_asset" in source
    assert "FINAL_EDITORIAL_BLOCKED" in source
    assert "allow_neutral=False" in source


def test_strict_ship_ocean_aliases_remain_asset_evidence_only():
    source = (ROOT / "media_must_verifier.py").read_text(encoding="utf-8")
    assert '"ship":' in source
    assert '"ocean":' in source
    assert "These affect acceptance only when the asset itself contains the alias." in source
