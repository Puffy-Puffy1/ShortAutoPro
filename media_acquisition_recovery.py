#!/usr/bin/env python3
"""Targeted acquisition recovery for explicit-MUST scenes.

This module does not relax validation. It only broadens provider retrieval when
the first acquisition pool contains no asset that can prove every explicit
MUST requirement. It also prevents repeated Coverr calls after persistent empty
responses in the same run.
"""
from __future__ import annotations

import functools
from typing import Any, Callable

import media_must_verifier as mustv

VERSION = "1.0"


def _must_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, (list, tuple, set)):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        key = text.casefold()
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return out


def _complete(candidate: Any, must: list[str]) -> bool:
    if not must or not isinstance(candidate, dict):
        return False
    result = mustv.verified_must(candidate, {"must_have": must})
    return bool(result.get("total")) and int(result.get("hits", 0) or 0) >= int(result.get("total", 0) or 0)


def _dedupe(candidates: list[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            out.append(candidate)
            continue
        key = str(
            candidate.get("url")
            or candidate.get("download_url")
            or candidate.get("src")
            or candidate.get("id")
            or candidate.get("filename")
            or repr(sorted(candidate.items(), key=lambda kv: str(kv[0])))
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def _rescue_queries(busca: str, must: list[str], assunto: str = "") -> list[str]:
    base = " ".join(must).strip()
    subject = str(assunto or "").strip()
    candidates = [
        base,
        f"{subject} {base}".strip(),
        f"{base} archive photograph".strip(),
        f"{base} historical photograph".strip(),
        f"{base} documentary evidence".strip(),
    ]
    original = str(busca or "").strip()
    if original:
        candidates.append(f"{base} {original}".strip())

    out: list[str] = []
    seen: set[str] = set()
    for query in candidates:
        query = " ".join(query.split())
        key = query.casefold()
        if not query or key in seen or key == original.casefold():
            continue
        seen.add(key)
        out.append(query)
    return out[:5]


def _wrap_coverr(namespace: dict[str, Any]) -> bool:
    original = namespace.get("coverr_video")
    if not callable(original) or getattr(original, "_sap_acquisition_recovery", False):
        return False

    state = {"empty": 0, "open": False}

    @functools.wraps(original)
    def wrapped(*args, **kwargs):
        if state["open"]:
            print("SAP_COVERR_CIRCUIT=OPEN reason=PERSISTENT_EMPTY_RETURN")
            return []
        result = original(*args, **kwargs)
        items = list(result or [])
        if items:
            state["empty"] = 0
            return items
        state["empty"] += 1
        if state["empty"] >= 2:
            state["open"] = True
            print("SAP_COVERR_CIRCUIT=TRIPPED empty_returns=2")
        return items

    wrapped._sap_acquisition_recovery = True
    namespace["coverr_video"] = wrapped
    return True


def _wrap_pool(namespace: dict[str, Any]) -> bool:
    original = namespace.get("buscar_todos_candidatos")
    if not callable(original) or getattr(original, "_sap_acquisition_recovery", False):
        return False

    @functools.wraps(original)
    def wrapped(busca, must_have, avoid, segmento="", visual_mode=""):
        must = _must_list(must_have)
        initial = list(original(busca, must_have, avoid, segmento, visual_mode) or [])
        if not must or any(_complete(candidate, must) for candidate in initial):
            return initial

        print(
            f"SAP_MUST_ACQUISITION_RESCUE=START initial={len(initial)} "
            f"must_total={len(must)}"
        )

        combined = list(initial)
        assunto = str(namespace.get("ASSUNTO", "") or "")
        for query in _rescue_queries(str(busca or ""), must, assunto):
            print(f"SAP_MUST_ACQUISITION_QUERY={query}")
            extra = list(original(query, must_have, avoid, segmento, visual_mode) or [])
            combined.extend(extra)
            combined = _dedupe(combined)
            if any(_complete(candidate, must) for candidate in combined):
                print(
                    f"SAP_MUST_ACQUISITION_RESCUE=FOUND pool={len(combined)} query={query}"
                )
                break
        else:
            print(f"SAP_MUST_ACQUISITION_RESCUE=EXHAUSTED pool={len(combined)}")

        return combined

    wrapped._sap_acquisition_recovery = True
    namespace["buscar_todos_candidatos"] = wrapped
    return True


def install(namespace: dict[str, Any]) -> dict[str, Any]:
    result = {
        "version": VERSION,
        "installed": True,
        "coverr_circuit": _wrap_coverr(namespace),
        "must_pool_rescue": _wrap_pool(namespace),
        "policy": "RETRIEVE_MORE_NEVER_RELAX_MUST",
    }
    print(
        "SAP_MEDIA_ACQUISITION_RECOVERY=INSTALLED "
        f"version={VERSION} coverr={result['coverr_circuit']} "
        f"must_rescue={result['must_pool_rescue']}"
    )
    return result


__all__ = ["VERSION", "install", "_rescue_queries", "_complete"]
