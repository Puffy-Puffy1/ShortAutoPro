#!/usr/bin/env python3

import inspect
import os

from visual_query_planner_v4 import expansion_queries

try:
    from visual_selection_engine_v4 import candidate_key, flatten_candidates
except Exception:
    candidate_key = None
    flatten_candidates = None


def _dedupe(items):
    result = []
    seen = set()
    for candidate in items:
        try:
            key = candidate_key(candidate) if candidate_key else repr(candidate)
        except Exception:
            key = repr(candidate)
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _env_int(name, default, minimum, maximum):
    try:
        value = int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(value, maximum))


def wrap_search_function(fn):
    if getattr(fn, "_vse42_query_expanded", False):
        return fn

    signature = inspect.signature(fn)
    params = list(signature.parameters)
    query_name = None

    for name in params:
        lname = name.casefold()
        if any(token in lname for token in ("busca", "query", "search", "termo", "pesquisa")):
            query_name = name
            break

    def wrapped(*args, **kwargs):
        primary = fn(*args, **kwargs)

        if os.getenv("SAP_VSE4_QUERY_EXPANSION", "1") != "1":
            return primary
        if query_name is None or not isinstance(primary, (list, tuple)):
            return primary

        try:
            bound = signature.bind_partial(*args, **kwargs)
            query = bound.arguments.get(query_name)
            must_have = bound.arguments.get("must_have", [])
        except Exception:
            return primary

        if not isinstance(query, str):
            return primary

        # Expansion is a rescue tier, not a permanent multiplier. The old
        # behavior executed up to three complete provider acquisitions even
        # after a successful primary query, multiplying latency and starving
        # the Stage 6 per-scene budget.
        if os.getenv("SAP_VSE4_QUERY_ONLY_ON_EMPTY", "1") == "1" and primary:
            return primary

        max_extra = _env_int("SAP_VSE4_QUERY_EXTRA", 1, 0, 2)
        if max_extra <= 0:
            return primary

        original = " ".join(query.split())
        plans = []

        # MUST-first rescue broadens only the search query. The original
        # must_have argument is passed unchanged to fn(), so acceptance remains
        # fail-closed and is never relaxed by this expansion layer.
        if isinstance(must_have, (list, tuple)):
            must_terms = [str(item).strip() for item in must_have if str(item).strip()]
            must_query = " ".join(must_terms)
            if must_query and must_query.casefold() != original.casefold():
                plans.append(must_query)

        existing = {item.casefold() for item in plans}
        if len(plans) < max_extra:
            for plan in expansion_queries(original, max_extra=max_extra):
                if plan.casefold() == original.casefold():
                    continue
                if plan.casefold() in existing:
                    continue
                plans.append(plan)
                existing.add(plan.casefold())
                if len(plans) >= max_extra:
                    break

        if not plans:
            return primary

        merged = list(primary)
        for alt in plans:
            try:
                alt_bound = signature.bind_partial(*args, **kwargs)
                alt_bound.arguments[query_name] = alt
                extra = fn(*alt_bound.args, **alt_bound.kwargs)
                if isinstance(extra, (list, tuple)):
                    merged.extend(extra)
                print("VSE42_QUERY_EXPANSION=" + alt)
            except Exception as exc:
                print(
                    "VSE42_QUERY_EXPANSION_FAIL_OPEN="
                    f"{type(exc).__name__}:{exc}"
                )

        merged = _dedupe(merged)
        print(
            "VSE42_EXPANDED_POOL="
            f"{len(merged)} rescue_queries={len(plans)} primary={len(primary)}"
        )
        return tuple(merged) if isinstance(primary, tuple) else merged

    wrapped._vse42_query_expanded = True
    wrapped._sap_query_expansion_original = fn
    wrapped.__wrapped__ = fn
    wrapped.__name__ = getattr(fn, "__name__", "wrapped_search")
    return wrapped
