#!/usr/bin/env python3
"""Targeted acquisition recovery for explicit-MUST scenes.

This module does not relax validation. It only broadens provider retrieval when
the first acquisition pool contains no asset that can prove every explicit
MUST requirement. It also prevents repeated Coverr calls after persistent empty
responses in the same run and caches identical acquisition calls so layered
query-expansion/retry logic does not hit the same providers twice.
"""
from __future__ import annotations

import copy
import functools
import os
import time
from typing import Any

import media_must_verifier as mustv

VERSION = "1.9"


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


def _rescue_queries(
    busca: str,
    must: list[str],
    assunto: str = "",
    segmento: str = "",
    visual_mode: str = "",
) -> list[str]:
    base = " ".join(must).strip()
    subject = str(assunto or "").strip()
    segment_tokens = [
        x
        for x in str(segmento or "").split()
        if len(x) >= 4
    ][:4]
    segment_anchor = " ".join(segment_tokens).strip()
    mode = str(visual_mode or "").replace("_", " ").strip()

    stock_modes = {
        "human context",
        "environment",
        "object",
        "abstract context",
    }
    stock_first = mode.casefold() in stock_modes

    if stock_first:
        # Stock APIs work best with compact visual nouns. Topic names and long
        # narration often reduce relevance and can exceed provider query limits.
        candidates = [
            base,
            f"{base} {mode}".strip(),
            f"{base} {segment_anchor}".strip(),
            f"{base} close up".strip(),
            f"{base} documentary".strip(),
            f"{base} isolated object".strip(),
            f"{base} archive".strip(),
            f"{base} vintage".strip(),
        ]
    else:
        candidates = [
            base,
            f"{subject} {base}".strip(),
            f"{base} {segment_anchor}".strip(),
            f"{subject} {base} {segment_anchor}".strip(),
            f"{base} {mode}".strip(),
            f"{base} archive photograph".strip(),
            f"{base} historical photograph".strip(),
            f"{base} documentary evidence".strip(),
            f"{base} museum archive".strip(),
            f"{base} newspaper archive".strip(),
            f"{base} official document".strip(),
        ]

    original = str(busca or "").strip()

    # Search individual MUST anchors too, while verification still requires
    # the final candidate to prove the complete original MUST set. This is a
    # retrieval expansion only, never an acceptance relaxation.
    if len(must) > 1:
        for anchor in must:
            candidates.append(f"{anchor} {segment_anchor}".strip())
            candidates.append(f"{anchor} {mode}".strip())

    if original:
        if stock_first:
            candidates.append(f"{base} {original}".strip())
        else:
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
    return out[:8]


def _rescue_budget() -> int:
    """Return a bounded per-scene rescue-query budget.

    Three is the canonical mobile default: enough to change the acquisition
    strategy across retries without turning one difficult scene into an
    unbounded provider loop. The environment override never relaxes MUST
    validation.
    """
    raw = os.getenv("SAP_MUST_RESCUE_MAX_QUERIES", "3")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = 3
    return max(1, min(value, 8))


def _cache_key(
    busca: Any,
    must_have: Any,
    avoid: Any,
    segmento: Any,
    visual_mode: Any,
) -> tuple[Any, ...]:
    def seq(value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple, set)):
            return ()
        return tuple(str(item or "").strip().casefold() for item in value)

    return (
        " ".join(str(busca or "").split()).casefold(),
        seq(must_have),
        seq(avoid),
        " ".join(str(segmento or "").split()).casefold(),
        " ".join(str(visual_mode or "").split()).casefold(),
    )


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

    # Collapse the entire search-wrapper chain for recovery queries.
    # Provider-level wrappers remain active because the base function resolves
    # provider callables from the live module namespace at runtime.
    provider_search = original
    seen_wrappers: set[int] = set()
    unwrapped_layers: list[str] = []

    for _ in range(12):
        marker = id(provider_search)
        if marker in seen_wrappers:
            break
        seen_wrappers.add(marker)

        next_fn = None
        next_label = ""

        for attr, label in (
            ("_sap_query_expansion_original", "QUERY_EXPANSION"),
            ("_sap_vse42_original", "VSE42_RESCUE"),
            ("__wrapped__", "FUNCTOOLS"),
        ):
            candidate = getattr(provider_search, attr, None)
            if callable(candidate) and candidate is not provider_search:
                next_fn = candidate
                next_label = label
                break

        if next_fn is None:
            break

        provider_search = next_fn
        unwrapped_layers.append(next_label)

    if unwrapped_layers:
        print(
            "SAP_MEDIA_RESCUE_NESTING=DISABLED layers="
            + ",".join(unwrapped_layers)
        )

    cache: dict[tuple[Any, ...], list[Any]] = {}
    rescue_cache: dict[tuple[Any, ...], list[Any]] = {}
    stats = {"hits": 0, "misses": 0, "rescue_hits": 0, "rescue_misses": 0}

    def call_original(busca, must_have, avoid, segmento="", visual_mode="") -> list[Any]:
        key = _cache_key(busca, must_have, avoid, segmento, visual_mode)
        if key in cache:
            stats["hits"] += 1
            print(
                "SAP_MEDIA_ACQUISITION_CACHE=HIT "
                f"hits={stats['hits']} misses={stats['misses']} query={str(busca or '')}"
            )
            return copy.deepcopy(cache[key])

        stats["misses"] += 1
        result = list(provider_search(busca, must_have, avoid, segmento, visual_mode) or [])
        cache[key] = copy.deepcopy(result)
        return result

    @functools.wraps(original)
    def wrapped(busca, must_have, avoid, segmento="", visual_mode=""):
        must = _must_list(must_have)
        initial_started = time.monotonic()
        initial = call_original(
            busca,
            must_have,
            avoid,
            segmento,
            visual_mode,
        )
        initial_elapsed = time.monotonic() - initial_started

        if not must or any(_complete(candidate, must) for candidate in initial):
            return initial

        try:
            provider_deadline = float(
                os.getenv("SAP_MEDIA_PROVIDER_RESULT_TIMEOUT", "6") or 6
            )
        except (TypeError, ValueError):
            provider_deadline = 6.0
        provider_deadline = max(2.0, provider_deadline)

        # If the first provider round consumed almost its whole deadline and
        # still returned nothing, repeating near-identical rescue queries is a
        # provider-stall problem, not a query-quality problem. Fail fast to the
        # editorial completion layer instead of spending 2-3 more deadlines.
        if (
            not initial
            and initial_elapsed >= max(2.5, provider_deadline * 0.75)
        ):
            print(
                "SAP_MUST_ACQUISITION_RESCUE=SKIPPED "
                "reason=INITIAL_PROVIDER_STALL "
                f"elapsed={initial_elapsed:.2f}s "
                f"deadline={provider_deadline:.2f}s"
            )
            return initial

        budget = _rescue_budget()
        _mode = str(visual_mode or "").replace("_", " ").strip().casefold()
        if _mode in {"human context", "environment", "object", "abstract context"}:
            try:
                _stock_budget = int(os.getenv("SAP_STOCK_RESCUE_MAX_QUERIES", "4") or 4)
            except (TypeError, ValueError):
                _stock_budget = 4
            budget = min(budget, max(1, min(_stock_budget, 8)))
            print(
                "SAP_STOCK_RESCUE_BUDGET="
                f"{budget} mode={_mode or 'unknown'}"
            )

        print(
            f"SAP_MUST_ACQUISITION_RESCUE=START initial={len(initial)} "
            f"must_total={len(must)} budget={budget}"
        )

        combined = list(initial)
        assunto = str(namespace.get("ASSUNTO", "") or "")
        queries = _rescue_queries(
            str(busca or ""),
            must,
            assunto,
            str(segmento or ""),
            str(visual_mode or ""),
        )[:budget]

        rescue_key = (
            tuple(item.casefold() for item in must),
            tuple(str(item or "").strip().casefold() for item in (avoid or []))
            if isinstance(avoid, (list, tuple, set)) else (str(avoid or "").casefold(),),
            " ".join(str(segmento or "").split()).casefold(),
            " ".join(str(visual_mode or "").split()).casefold(),
            tuple(query.casefold() for query in queries),
        )

        if rescue_key in rescue_cache:
            stats["rescue_hits"] += 1
            print(
                "SAP_MUST_RESCUE_CACHE=HIT "
                f"hits={stats['rescue_hits']} misses={stats['rescue_misses']} "
                f"queries={len(queries)}"
            )
            combined.extend(copy.deepcopy(rescue_cache[rescue_key]))
            combined = _dedupe(combined)
            return combined

        stats["rescue_misses"] += 1
        rescue_only: list[Any] = []

        for query in queries:
            print(f"SAP_MUST_ACQUISITION_QUERY={query}")
            extra = call_original(query, must_have, avoid, segmento, visual_mode)
            rescue_only.extend(extra)
            combined.extend(extra)
            combined = _dedupe(combined)
            if any(_complete(candidate, must) for candidate in combined):
                print(
                    f"SAP_MUST_ACQUISITION_RESCUE=FOUND pool={len(combined)} query={query}"
                )
                break
        else:
            print(
                f"SAP_MUST_ACQUISITION_RESCUE=EXHAUSTED pool={len(combined)} "
                f"queries={len(queries)}"
            )

        rescue_cache[rescue_key] = copy.deepcopy(_dedupe(rescue_only))
        return combined

    wrapped._sap_acquisition_recovery = True
    wrapped._sap_acquisition_cache = cache
    wrapped._sap_rescue_cache = rescue_cache
    wrapped._sap_acquisition_stats = stats
    # Expose a cached single-round provider search for midia.py retries.
    # It bypasses only recursive rescue expansion; validation remains intact.
    wrapped._sap_call_original = call_original
    namespace["buscar_todos_candidatos"] = wrapped
    return True


def install(namespace: dict[str, Any]) -> dict[str, Any]:
    result = {
        "version": VERSION,
        "installed": True,
        "coverr_circuit": _wrap_coverr(namespace),
        "must_pool_rescue": _wrap_pool(namespace),
        "rescue_budget": _rescue_budget(),
        "policy": "RETRIEVE_MORE_NEVER_RELAX_MUST",
    }
    print(
        "SAP_MEDIA_ACQUISITION_RECOVERY=INSTALLED "
        f"version={VERSION} coverr={result['coverr_circuit']} "
        f"must_rescue={result['must_pool_rescue']} budget={result['rescue_budget']}"
    )
    return result


__all__ = [
    "VERSION",
    "install",
    "_rescue_queries",
    "_rescue_budget",
    "_cache_key",
    "_complete",
]
