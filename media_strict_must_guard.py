#!/usr/bin/env python3
"""Fail-closed explicit-MUST guard for the canonical media runtime.

This module is intentionally narrow.  It does not replace acquisition, scoring,
Visual Unified, VSE4, or provider logic.  It only prevents a scene that declares
explicit MUST requirements from being committed through a partial/zero-MUST
runtime escape hatch.
"""
from __future__ import annotations

import functools
from typing import Any

import media_runtime_adapter_v1 as v1

VERSION = "1.0"


def _must_list(namespace: dict[str, Any]) -> list[str]:
    value = namespace.get("must_have", [])
    if not isinstance(value, (list, tuple, set)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _verified_hits(namespace: dict[str, Any], candidate: Any) -> tuple[int, int]:
    must = _must_list(namespace)
    total = len(must)
    if total <= 0 or not isinstance(candidate, dict):
        return (0 if total else total, total)

    try:
        v1.normalize_candidate(
            candidate,
            query=str(namespace.get("busca", "") or ""),
            must_have=must,
        )
    except Exception:
        pass

    try:
        verified = int(
            candidate.get(
                "_sap_verified_must_hits",
                candidate.get("must_hits", 0),
            )
            or 0
        )
    except (TypeError, ValueError):
        verified = 0

    try:
        verified_total = int(candidate.get("_sap_must_total", total) or total)
    except (TypeError, ValueError):
        verified_total = total

    # The live scene contract is authoritative.  A stale candidate must never
    # reduce the number of requirements that need to be satisfied.
    return verified, max(total, verified_total)


def _strict_ok(namespace: dict[str, Any], candidate: Any) -> bool:
    must = _must_list(namespace)
    if not must:
        return True
    if not isinstance(candidate, dict):
        return False

    try:
        if int(candidate.get("avoid_hits", 0) or 0) > 0:
            return False
    except (TypeError, ValueError):
        return False

    hits, total = _verified_hits(namespace, candidate)
    return total > 0 and hits >= total


def _diag(namespace: dict[str, Any], candidate: Any, label: str) -> None:
    hits, total = _verified_hits(namespace, candidate)
    source = candidate.get("fonte", "?") if isinstance(candidate, dict) else "?"
    media_type = candidate.get("tipo", "?") if isinstance(candidate, dict) else "?"
    print(
        f"SAP_STRICT_MUST_{label}=BLOCKED "
        f"source={source} type={media_type} verified={hits}/{total}"
    )


def _wrap_failover(namespace: dict[str, Any]) -> bool:
    original = namespace.get("ordenar_failover_5_2")
    if not callable(original) or getattr(original, "_sap_strict_must_guard", False):
        return False

    @functools.wraps(original)
    def wrapped(candidates, total_must, route, previous_description=""):
        result = original(candidates, total_must, route, previous_description)
        if not _must_list(namespace):
            return result
        source = result if isinstance(result, list) else list(result or [])
        filtered = [candidate for candidate in source if _strict_ok(namespace, candidate)]
        blocked = len(source) - len(filtered)
        if blocked:
            print(
                f"SAP_STRICT_MUST_POOL=FILTERED blocked={blocked} "
                f"kept={len(filtered)} total={len(source)}"
            )
        return filtered

    wrapped._sap_strict_must_guard = True
    namespace["ordenar_failover_5_2"] = wrapped
    return True


def _wrap_reference_guard(namespace: dict[str, Any]) -> bool:
    original = namespace.get("fallback_preserva_5_2")
    if not callable(original) or getattr(original, "_sap_strict_must_guard", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, reference: Any):
        if _must_list(namespace) and not _strict_ok(namespace, candidate):
            _diag(namespace, candidate, "REFERENCE")
            return False
        return original(candidate, reference)

    wrapped._sap_strict_must_guard = True
    namespace["fallback_preserva_5_2"] = wrapped
    return True


def _wrap_degraded_guard(namespace: dict[str, Any]) -> bool:
    original = namespace.get("fallback_degradado_ok_5_2")
    if not callable(original) or getattr(original, "_sap_strict_must_guard", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, total_must: int):
        if _must_list(namespace) and not _strict_ok(namespace, candidate):
            _diag(namespace, candidate, "DEGRADED")
            return False
        return original(candidate, total_must)

    wrapped._sap_strict_must_guard = True
    namespace["fallback_degradado_ok_5_2"] = wrapped
    return True


def _wrap_download_guard(namespace: dict[str, Any]) -> bool:
    original = namespace.get("baixar_candidato_5_2")
    if not callable(original) or getattr(original, "_sap_strict_must_guard", False):
        return False

    @functools.wraps(original)
    def wrapped(candidate: Any, scene_number: int, label: str):
        if _must_list(namespace) and not _strict_ok(namespace, candidate):
            _diag(namespace, candidate, "DOWNLOAD")
            return False, None
        return original(candidate, scene_number, label)

    wrapped._sap_strict_must_guard = True
    namespace["baixar_candidato_5_2"] = wrapped
    return True


def _wrap_local_guard(namespace: dict[str, Any]) -> bool:
    original = namespace.get("buscar_local")
    if not callable(original) or getattr(original, "_sap_strict_must_guard", False):
        return False

    @functools.wraps(original)
    def wrapped(prefer_video: bool):
        if _must_list(namespace):
            print(
                "SAP_STRICT_MUST_LOCAL_FALLBACK=BLOCKED "
                "reason=EXPLICIT_MUST_REQUIRES_VERIFIED_ASSET"
            )
            return None
        return original(prefer_video)

    wrapped._sap_strict_must_guard = True
    namespace["buscar_local"] = wrapped
    return True


def install(namespace: dict[str, Any]) -> dict[str, Any]:
    result = {
        "version": VERSION,
        "installed": True,
        "failover": _wrap_failover(namespace),
        "reference": _wrap_reference_guard(namespace),
        "degraded": _wrap_degraded_guard(namespace),
        "download": _wrap_download_guard(namespace),
        "local": _wrap_local_guard(namespace),
        "policy": "EXPLICIT_MUST_FAIL_CLOSED",
    }
    print(
        "SAP_STRICT_MUST_GUARD=INSTALLED "
        f"version={VERSION} failover={result['failover']} "
        f"download={result['download']} local={result['local']}"
    )
    return result


__all__ = ["VERSION", "install", "_strict_ok", "_verified_hits"]
