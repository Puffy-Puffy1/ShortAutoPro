#!/usr/bin/env python3
"""Fail-closed guard against generic/repeated visual search queries.

The guard never rewrites narration. It only repairs visual search metadata when
upstream AI falls back to generic stock prompts or repeats the same query across
many scenes. This keeps Stage 6 scene-specific even during API degradation.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
R = BASE / "roteiros"
MAP = R / f"scene_map_{SID}.json"
REPORT = R / f"visual_query_guard_{SID}.json"

GENERIC_MARKERS = {
    "documentary visual context scene",
    "documentary context archival visual",
    "documentary scene",
    "documentary detail scene",
    "documentary context",
    "archival documentary context",
}

STOP = {
    "a","ao","aos","aquela","aquele","aqueles","as","ate","com","como","da","das","de","dela","dele",
    "deles","do","dos","e","ela","ele","eles","em","entre","era","essa","esse","esta","este","foi","foram",
    "ha","isso","ja","mais","mas","na","nas","no","nos","o","os","ou","para","pela","pelas","pelo","pelos",
    "por","porque","que","se","sem","ser","seu","sua","suas","tambem","tem","teve","um","uma","umas","uns",
    "the","and","with","from","that","this","was","were","into","over","under","about","after","before",
}

TRANSLATE = {
    "igreja":"church","capela":"chapel","casa":"house","rua":"street","estrada":"road","cidade":"city",
    "escola":"school","hospital":"hospital","floresta":"forest","mata":"forest","rio":"river","ponte":"bridge",
    "policia":"police","policial":"police","crime":"crime","assassinato":"murder","morte":"death",
    "desaparecimento":"disappearance","desapareceu":"missing","desaparecida":"missing","desaparecido":"missing",
    "mulher":"woman","homem":"man","crianca":"child","familia":"family","noite":"night","documento":"document",
    "documentos":"documents","carta":"letter","foto":"photograph","fotografia":"photograph","arquivo":"archive",
    "misterio":"mystery","misterioso":"mysterious","testemunha":"witness","testemunhas":"witnesses",
    "investigacao":"investigation","caso":"case","hotel":"hotel","quarto":"room","carro":"car","veiculo":"vehicle",
    "cemiterio":"cemetery","fazenda":"farm","praia":"beach","mar":"sea","montanha":"mountain","caverna":"cave",
}

def clean(v: Any) -> str:
    return " ".join(str(v or "").replace("\n", " ").split())

def norm(v: Any) -> str:
    s = unicodedata.normalize("NFKD", clean(v))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().split())

def words(v: Any) -> list[str]:
    return re.findall(r"[A-Za-zÀ-ÿ0-9'-]+", clean(v))

def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

def load() -> dict[str, Any]:
    data = json.loads(MAP.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        raise ValueError("scene_map invalido")
    return data

def topic_text() -> str:
    for path in (R / f"used_topic_{SID}.txt", R / f"topic_{SID}.txt"):
        try:
            value = clean(path.read_text(encoding="utf-8"))
            if value:
                return value
        except OSError:
            pass
    return ""

def salient(scene: dict[str, Any], topic: str) -> list[str]:
    sources = [
        clean(scene.get("main_subject")),
        clean(scene.get("location")),
        clean(scene.get("environment")),
        clean(scene.get("segment")),
        topic,
    ]
    proper: list[str] = []
    normal: list[str] = []
    seen: set[str] = set()
    for source in sources:
        for raw in words(source):
            n = norm(raw)
            if len(n) < 4 or n in STOP or n.isdigit() or n in seen:
                continue
            seen.add(n)
            out = TRANSLATE.get(n, raw)
            if raw[:1].isupper() and raw.lower() != raw:
                proper.append(out)
            else:
                normal.append(out)
    merged = proper + normal
    return merged[:8]

def is_generic(query: str) -> bool:
    q = norm(query)
    if not q:
        return True
    if q in GENERIC_MARKERS:
        return True
    if "documentary visual context" in q:
        return True
    meaningful = [x for x in re.findall(r"[a-z0-9]+", q) if x not in {"documentary","visual","context","scene","archival","archive"}]
    return len(meaningful) < 2

def build_query(scene: dict[str, Any], topic: str, extra_skip: int = 0) -> str:
    terms = salient(scene, topic)
    if extra_skip and len(terms) > extra_skip:
        terms = terms[extra_skip:] + terms[:extra_skip]
    core = terms[:6]
    while len(core) < 3:
        filler = ["historical", "documentary", "archive"]
        candidate = filler[len(core) % len(filler)]
        if candidate not in core:
            core.append(candidate)
        else:
            core.append("evidence")
    suffix = ["documentary", "archive"]
    output: list[str] = []
    for term in core + suffix:
        key = norm(term)
        if key and key not in {norm(x) for x in output}:
            output.append(term)
    return " ".join(output[:9])

def main() -> int:
    if not SID:
        print("VISUAL_QUERY_GUARD=BLOCK short_id_empty")
        return 1
    try:
        data = load()
    except Exception as exc:
        print(f"VISUAL_QUERY_GUARD=BLOCK {type(exc).__name__}:{exc}")
        return 1
    scenes = data["scenes"]
    expected = max(1, len(scenes))
    topic = topic_text()
    counts = Counter(norm(scene.get("query")) for scene in scenes)
    changed: list[int] = []
    reasons: dict[str, list[int]] = {"generic": [], "repeated": []}
    used: Counter[str] = Counter()

    for idx, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            print(f"VISUAL_QUERY_GUARD=BLOCK invalid_scene:{idx}")
            return 1
        old = clean(scene.get("query"))
        key = norm(old)
        generic = is_generic(old)
        repeated = bool(key) and counts[key] >= 3
        if generic:
            reasons["generic"].append(idx)
        if repeated:
            reasons["repeated"].append(idx)
        if generic or repeated:
            candidate = build_query(scene, topic, extra_skip=(idx - 1) % 3)
            ckey = norm(candidate)
            if used[ckey] >= 2:
                candidate = build_query(scene, topic, extra_skip=idx % 5)
                ckey = norm(candidate)
            scene["query"] = candidate
            alts = scene.get("alt_queries") if isinstance(scene.get("alt_queries"), list) else []
            alt_values = [clean(x) for x in alts if clean(x) and norm(x) != norm(old)]
            derived = [
                build_query(scene, topic, extra_skip=1),
                build_query(scene, topic, extra_skip=2),
            ]
            merged: list[str] = []
            seen_alt: set[str] = set()
            for value in derived + alt_values:
                n = norm(value)
                if value and n and n != norm(candidate) and n not in seen_alt:
                    seen_alt.add(n)
                    merged.append(value)
            scene["alt_queries"] = merged[:3]
            scene["query_guard_repaired"] = True
            scene["query_guard_previous"] = old
            changed.append(idx)
            used[ckey] += 1
        else:
            used[key] += 1

    final_counts = Counter(norm(scene.get("query")) for scene in scenes)
    remaining_generic = [i for i, s in enumerate(scenes, 1) if is_generic(clean(s.get("query")))]
    over_repeated = {q: c for q, c in final_counts.items() if q and c >= 3}
    status = "BLOCK" if remaining_generic or over_repeated else ("REPAIRED" if changed else "PASS")
    data["scenes"] = scenes
    if status != "BLOCK":
        atomic(MAP, data)
    report = {
        "short_id": SID,
        "version": "VISUAL_QUERY_GUARD_1.0",
        "status": status,
        "scene_count": expected,
        "changed_scenes": changed,
        "reasons": reasons,
        "remaining_generic": remaining_generic,
        "over_repeated_queries": over_repeated,
        "queries": [{"scene": i, "query": clean(s.get("query"))} for i, s in enumerate(scenes, 1)],
    }
    atomic(REPORT, report)
    print(
        f"VISUAL_QUERY_GUARD={status} changed={len(changed)}/{expected} "
        f"generic_left={len(remaining_generic)} repeated_left={len(over_repeated)}"
    )
    return 0 if status in {"PASS", "REPAIRED"} else 1

if __name__ == "__main__":
    raise SystemExit(main())
