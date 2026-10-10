from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class QueryPlan:
    original: str
    variants: tuple[str, ...]

def _clean(value: str) -> str:
    return " ".join(str(value or "").split()).strip()

def build_query_plan(query: str, must: list[str], soft_must: list[str] | None = None, max_variants: int = 6) -> QueryPlan:
    raw = _clean(query)
    if not raw:
        return QueryPlan("", ())
    variants: list[str] = [raw]
    normalized = _clean(re.sub(r"[^A-Za-z0-9À-ÿ]+", " ", raw))
    if normalized.casefold() not in {v.casefold() for v in variants}:
        variants.append(normalized)
    words = normalized.split()
    if len(words) > 6:
        variants.append(" ".join(words[:6]))
    if len(words) > 4:
        variants.append(" ".join(words[:4]))
    if len(words) > 2:
        variants.append(" ".join(words[:2]))
    anchors = [_clean(x) for x in (soft_must or []) + must if _clean(x)]
    aliases = {
        "security sensor": ("motion sensor","alarm sensor","door sensor"),
        "security sensors": ("motion sensors","alarm sensors","door sensors"),
    }
    for anchor in list(anchors):
        for alias in aliases.get(anchor.casefold(), ()):
            if alias.casefold() not in {v.casefold() for v in variants}:
                variants.append(alias)
    if anchors:
        anchor = " ".join(anchors[:2])
        if anchor and anchor.casefold() not in {v.casefold() for v in variants}:
            variants.append(anchor)
    out=[]; seen=set()
    for value in variants:
        value=_clean(value); key=value.casefold()
        if value and key not in seen:
            seen.add(key); out.append(value)
    return QueryPlan(raw, tuple(out[:max(1, max_variants)]))
