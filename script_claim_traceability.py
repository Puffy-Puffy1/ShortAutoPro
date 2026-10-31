#!/usr/bin/env python3
"""Fail-closed bridge between script generation and factual claim validation.

The generator and the intelligence layer use the same claim_lock implementation.
Weakly traceable AI prose is replaced with a contiguous source extract; thresholds
are not lowered and production is blocked if even the extract cannot pass.
"""
from __future__ import annotations

from typing import Any

from script_fallback import build_extractive_script, count_words, is_topic_relevant
from shortauto_intelligence_layer import claim_engine, claim_lock

MIN_SCRIPT_CLAIM_COVERAGE = 90.0
EXTRACTIVE_CTA = "Comente o que acha!"


class ScriptClaimTraceabilityError(RuntimeError):
    """Raised when neither the generated script nor a source extract is traceable."""


def enforce_script_claim_traceability(
    script: str,
    source: str,
    *,
    topic: str = "",
) -> tuple[str, dict[str, Any]]:
    """Keep a supported draft or fail closed to source-only narration."""
    candidate = str(script or "").strip()
    source_text = str(source or "").strip()
    if not candidate:
        raise ScriptClaimTraceabilityError("script_empty")
    if not source_text:
        raise ScriptClaimTraceabilityError("source_empty")

    claims = claim_engine(source_text)
    if not claims:
        raise ScriptClaimTraceabilityError("source_has_no_claims")

    initial = claim_lock(candidate, claims)
    initial_coverage = float(initial.get("coverage", 0.0) or 0.0)
    result: dict[str, Any] = {
        "minimum_coverage": MIN_SCRIPT_CLAIM_COVERAGE,
        "original_coverage": round(initial_coverage, 1),
        "coverage": round(initial_coverage, 1),
        "source_claims": len(claims),
        "unsupported_sentences": len(initial.get("unsupported", [])),
        "fallback_used": False,
    }
    topic_ok = is_topic_relevant(candidate, topic)
    result["topic_relevance_required"] = bool(str(topic or "").strip())
    result["topic_relevant"] = topic_ok
    if initial_coverage >= MIN_SCRIPT_CLAIM_COVERAGE and topic_ok:
        return candidate, result

    result["fallback_reason"] = (
        "topic_mismatch" if not topic_ok else "coverage_below_threshold"
    )
    extract = build_extractive_script(
        source_text, cta=EXTRACTIVE_CTA, topic=topic
    )
    if not extract:
        reason = (
            "source_extract_topic_window_unavailable"
            if topic else "source_extract_window_unavailable"
        )
        raise ScriptClaimTraceabilityError(
            f"coverage={initial_coverage:.1f};{reason}"
        )

    extracted_check = claim_lock(extract, claims)
    extracted_coverage = float(extracted_check.get("coverage", 0.0) or 0.0)
    if extracted_coverage < MIN_SCRIPT_CLAIM_COVERAGE:
        raise ScriptClaimTraceabilityError(
            "source_extract_did_not_pass:"
            f"coverage={extracted_coverage:.1f};"
            f"unsupported={len(extracted_check.get('unsupported', []))}"
        )

    result.update(
        topic_relevant=is_topic_relevant(extract, topic),
        coverage=round(extracted_coverage, 1),
        unsupported_sentences=len(extracted_check.get("unsupported", [])),
        fallback_used=True,
        fallback_words=count_words(extract),
    )
    return extract, result


__all__ = [
    "MIN_SCRIPT_CLAIM_COVERAGE",
    "ScriptClaimTraceabilityError",
    "enforce_script_claim_traceability",
]
