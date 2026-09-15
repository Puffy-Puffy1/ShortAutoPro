#!/usr/bin/env python3

import json
import re
from collections import Counter
from pathlib import Path

from vi7_31_visual_ontology import classify

try:
    from vi9_wiki_search_adapter import wiki_search
    WIKI_AVAILABLE = True
except Exception:
    wiki_search = None
    WIKI_AVAILABLE = False


VERSION = "9.20"

BASE = Path.home() / "ShortAutoPro"

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi9_20_provider_router_master_latest.json"
)


# =====================================================
# LANGUAGE / SEMANTIC DATA
# =====================================================

VISUAL_TERMS = {
    "portrait", "clear", "face", "medium",
    "shot", "close", "wide", "detail",
    "documentary", "photograph", "photo",
    "image", "dark", "shadow", "shadows",
    "cinematic", "dramatic", "moody",
    "lighting", "hallway", "corner",
    "background", "foreground",
}

GENERIC_ATMOSPHERIC = {
    "person", "people", "someone",
    "hiding", "walking", "running",
    "standing", "sitting",
    "hallway", "corridor", "room",
    "dark", "shadow", "shadows",
    "corner", "silhouette",
    "mysterious", "scary", "creepy",
    "dramatic", "atmosphere",
}

WIKI_STOPWORDS = {
    "the", "a", "an", "of", "in", "on",
    "at", "to", "for", "from", "with",
    "and", "or",
    "de", "da", "do", "das", "dos",
    "um", "uma", "em", "para", "com",
    "que",
    "person", "people",
    "portrait", "photo", "image",
    "shot", "medium", "wide",
    "close", "detail",
    "documentary", "photograph",
    "clear", "cinematic",
}

ENTITY_HINTS = {
    "murder", "case", "crime",
    "school", "house", "hotel",
    "city", "town", "street",
    "police", "court",
    "document", "letter",
    "note", "newspaper",
    "evidence", "archive",
    "victim", "suspect",
}


# =====================================================
# HELPERS
# =====================================================

def words(text):
    return re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )


def token_set(text, stop=None):
    stop = stop or set()

    return {
        w.lower()
        for w in words(text)
        if (
            len(w) >= 3
            and w.lower() not in stop
        )
    }


def scene_text(scene):
    values = [
        scene.get("segment") or "",
        scene.get("query") or "",
    ]

    for key in (
        "must_have",
        "avoid",
    ):
        value = scene.get(key)

        if isinstance(value, list):
            values.extend(
                str(x)
                for x in value
            )

        elif value:
            values.append(
                str(value)
            )

    return " ".join(values)


def normalized_query(text):
    seen = set()
    output = []

    for token in words(text):
        low = token.lower()

        if low in VISUAL_TERMS:
            continue

        if low in seen:
            continue

        seen.add(low)
        output.append(token)

    return " ".join(output).strip()


def proper_name_signal(text):
    # Conservative signal only.
    tokens = re.findall(
        r"\b[A-Z][a-zÀ-ÿ]{2,}\b",
        str(text or "")
    )

    generic = {
        "The", "This", "That",
        "Scene", "Image",
    }

    tokens = [
        x
        for x in tokens
        if x not in generic
    ]

    return len(tokens) >= 2


def numeric_entity_signal(text):
    return bool(
        re.search(
            r"\b(?:18|19|20)\d{2}\b",
            str(text or "")
        )
    )


def generic_ratio(text):
    tokens = token_set(text)

    if not tokens:
        return 1.0

    generic = (
        tokens
        & GENERIC_ATMOSPHERIC
    )

    return (
        len(generic)
        / len(tokens)
    )


# =====================================================
# PROVIDER ROUTER
# =====================================================

def route_scene(scene):

    category = classify(scene)

    text = scene_text(scene)

    query = str(
        scene.get("query")
        or ""
    )

    generic = generic_ratio(
        query
    )

    has_name = proper_name_signal(
        text
    )

    has_year = numeric_entity_signal(
        text
    )

    tokens = token_set(
        text
    )

    entity_hint_count = len(
        tokens
        & ENTITY_HINTS
    )

    reasons = []

    # Face without confirmed named subject:
    # don't ask Wikipedia to guess identity.
    if (
        category == "FACE"
        and not has_name
    ):
        provider = (
            "VISUAL_SEARCH_SHADOW"
        )

        confidence = 0.95

        reasons.append(
            "face_without_confirmed_entity"
        )


    elif generic >= 0.45:
        provider = (
            "VISUAL_SEARCH_SHADOW"
        )

        confidence = 0.92

        reasons.append(
            "generic_atmospheric_scene"
        )


    elif category in {
        "DOCUMENT",
        "EVIDENCE",
    }:
        provider = (
            "DOCUMENTARY_ARCHIVE_SHADOW"
        )

        confidence = 0.86

        reasons.append(
            "documentary_material"
        )


    elif (
        has_name
        or has_year
        or entity_hint_count >= 2
    ):
        provider = "WIKIPEDIA"

        confidence = 0.82

        reasons.append(
            "entity_or_fact_signal"
        )


    elif category == "LOCATION":
        provider = (
            "VISUAL_SEARCH_SHADOW"
        )

        confidence = 0.75

        reasons.append(
            "location_without_strong_entity"
        )


    else:
        provider = (
            "VISUAL_SEARCH_SHADOW"
        )

        confidence = 0.72

        reasons.append(
            "visual_provider_more_suitable"
        )


    return {
        "scene":
            scene.get("scene"),

        "category":
            category,

        "provider":
            provider,

        "confidence":
            round(
                confidence,
                3
            ),

        "reasons":
            reasons,

        "generic_ratio":
            round(
                generic,
                3
            ),

        "proper_name_signal":
            has_name,

        "year_signal":
            has_year,

        "entity_hint_count":
            entity_hint_count,

        "original_query":
            query,
    }


# =====================================================
# WIKIPEDIA QUERY PLANNER
# =====================================================

def wiki_variants(scene):

    raw = str(
        scene.get("query")
        or ""
    )

    cleaned = normalized_query(
        raw
    )

    scene_tokens = [
        x
        for x in words(cleaned)
        if (
            len(x) >= 3
            and x.lower()
            not in WIKI_STOPWORDS
        )
    ]


    candidates = [
        cleaned,
        " ".join(
            scene_tokens[:6]
        ),
        " ".join(
            scene_tokens[:4]
        ),
        " ".join(
            scene_tokens[:3]
        ),
    ]


    segment = normalized_query(
        scene.get("segment")
        or ""
    )

    segment_tokens = [
        x
        for x in words(segment)
        if (
            len(x) >= 3
            and x.lower()
            not in WIKI_STOPWORDS
        )
    ]

    if segment_tokens:
        candidates.append(
            " ".join(
                segment_tokens[:5]
            )
        )


    output = []
    seen = set()


    for candidate in candidates:

        candidate = (
            candidate.strip()
        )

        key = candidate.lower()

        if (
            candidate
            and key not in seen
        ):
            seen.add(key)

            output.append(
                candidate
            )


    return output[:4]


# =====================================================
# SEMANTIC RELEVANCE
# =====================================================

def result_text(item):

    return " ".join(
        str(
            item.get(key)
            or ""
        )
        for key in (
            "title",
            "snippet",
            "description",
        )
    )


def semantic_score(
    query,
    item
):

    q = token_set(
        query,
        WIKI_STOPWORDS
    )

    r = token_set(
        result_text(item),
        WIKI_STOPWORDS
    )

    title = token_set(
        item.get(
            "title"
        )
        or "",
        WIKI_STOPWORDS
    )


    if not q:
        return {
            "score": 0.0,
            "shared": [],
            "title_shared": [],
        }


    shared = (
        q & r
    )

    title_shared = (
        q & title
    )


    coverage = (
        len(shared)
        / len(q)
    )


    title_bonus = min(
        0.35,
        len(title_shared)
        * 0.175
    )


    # One accidental common word should not
    # certify a result.
    if (
        len(shared) <= 1
        and not title_shared
    ):
        score = (
            coverage * 0.35
        )

    else:
        score = (
            coverage
            + title_bonus
        )


    score = min(
        1.0,
        score
    )


    return {
        "score":
            round(
                score,
                3
            ),

        "shared":
            sorted(shared),

        "title_shared":
            sorted(
                title_shared
            ),
    }


# =====================================================
# WIKI PROBE
# =====================================================

def probe_wikipedia(
    scene,
    threshold=0.42
):

    if not WIKI_AVAILABLE:

        return {
            "status":
                "PROVIDER_UNAVAILABLE",

            "accepted":
                [],

            "attempts":
                [],
        }


    attempts = []

    accepted_global = []


    for query in wiki_variants(
        scene
    ):

        try:

            results = wiki_search(
                query,
                limit=5
            )

        except Exception as exc:

            attempts.append({
                "query":
                    query,

                "status":
                    "ERROR",

                "error":
                    type(exc).__name__
                    + ": "
                    + str(exc)[:250],
            })

            continue


        evaluated = []


        for item in (
            results or []
        ):

            score = semantic_score(
                query,
                item
            )

            result = {
                "title":
                    item.get(
                        "title"
                    ),

                "score":
                    score[
                        "score"
                    ],

                "shared":
                    score[
                        "shared"
                    ],

                "title_shared":
                    score[
                        "title_shared"
                    ],

                "accepted":
                    score[
                        "score"
                    ]
                    >= threshold,
            }

            evaluated.append(
                result
            )


            if result[
                "accepted"
            ]:

                accepted_global.append({
                    "query":
                        query,

                    **result,
                })


        attempts.append({
            "query":
                query,

            "status":
                "RETURNED",

            "raw_count":
                len(
                    results or []
                ),

            "accepted_count":
                sum(
                    1
                    for x in evaluated
                    if x["accepted"]
                ),

            "results":
                evaluated[:5],
        })


        if accepted_global:
            break


    accepted_global.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    if accepted_global:

        status = (
            "SEMANTIC_ROUTE_FOUND"
        )

    else:

        status = (
            "WIKIPEDIA_ROUTE_REJECTED"
        )


    return {
        "status":
            status,

        "accepted":
            accepted_global[:5],

        "attempts":
            attempts,
    }


# =====================================================
# FINAL ROUTE DECISION
# =====================================================

def final_decision(
    scene,
    route,
    wiki_probe=None
):

    provider = route[
        "provider"
    ]

    decision = {
        "scene":
            route["scene"],

        "category":
            route["category"],

        "initial_provider":
            provider,

        "final_provider":
            provider,

        "action":
            "SHADOW_ONLY",

        "confidence":
            route[
                "confidence"
            ],

        "reasons":
            list(
                route[
                    "reasons"
                ]
            ),

        "wiki_status":
            None,

        "accepted_wiki_results":
            0,

        "download_allowed":
            False,

        "replace_allowed":
            False,
    }


    if provider == "WIKIPEDIA":

        wiki_probe = (
            wiki_probe
            or {
                "status":
                    "NOT_PROBED",

                "accepted":
                    [],
            }
        )


        decision[
            "wiki_status"
        ] = wiki_probe[
            "status"
        ]


        decision[
            "accepted_wiki_results"
        ] = len(
            wiki_probe.get(
                "accepted"
            )
            or []
        )


        if (
            wiki_probe[
                "status"
            ]
            != "SEMANTIC_ROUTE_FOUND"
        ):

            decision[
                "final_provider"
            ] = (
                "VISUAL_SEARCH_SHADOW"
            )

            decision[
                "reasons"
            ].append(
                "wikipedia_semantic_rejection"
            )


    return decision


# =====================================================
# SCENE MAP
# =====================================================

def latest_scene_map():

    files = [
        p
        for p in (
            BASE / "roteiros"
        ).glob(
            "scene_map_*.json"
        )
        if "_pre_" not in p.name
    ]


    files.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )


    return (
        files[0]
        if files
        else None
    )


# =====================================================
# MASTER
# =====================================================

def evaluate():

    scene_map_path = (
        latest_scene_map()
    )


    if not scene_map_path:

        raise RuntimeError(
            "scene_map_missing"
        )


    data = json.loads(
        scene_map_path.read_text(
            encoding="utf-8"
        )
    )


    scenes = (
        data.get("scenes")
        or []
    )


    if len(scenes) != 12:

        raise RuntimeError(
            "scene_count_not_12"
        )


    routes = [
        route_scene(scene)
        for scene in scenes
    ]


    # Limit real Wikipedia network probes.
    wiki_candidates = [
        (
            scene,
            route
        )
        for scene, route
        in zip(
            scenes,
            routes
        )
        if route[
            "provider"
        ] == "WIKIPEDIA"
    ]


    wiki_candidates.sort(
        key=lambda pair:
            pair[1][
                "confidence"
            ],
        reverse=True
    )


    wiki_candidates = (
        wiki_candidates[:3]
    )


    wiki_by_scene = {}


    for scene, route in (
        wiki_candidates
    ):

        wiki_by_scene[
            route["scene"]
        ] = probe_wikipedia(
            scene
        )


    decisions = []


    for scene, route in zip(
        scenes,
        routes
    ):

        decisions.append(
            final_decision(
                scene,
                route,
                wiki_by_scene.get(
                    route["scene"]
                )
            )
        )


    provider_counts = Counter(
        x["final_provider"]
        for x in decisions
    )


    wiki_rejected = [
        x["scene"]
        for x in decisions
        if (
            x.get(
                "wiki_status"
            )
            == "WIKIPEDIA_ROUTE_REJECTED"
        )
    ]


    face_visual = [
        x["scene"]
        for x in decisions
        if (
            x["category"]
            == "FACE"
            and x[
                "final_provider"
            ]
            == "VISUAL_SEARCH_SHADOW"
        )
    ]


    blockers = []

    warnings = []


    # No scene should authorize mutation.
    for decision in decisions:

        if (
            decision[
                "download_allowed"
            ]
            or decision[
                "replace_allowed"
            ]
        ):

            blockers.append(
                f"scene_{decision['scene']}_unsafe_activation"
            )


    if wiki_rejected:

        warnings.append(
            "wikipedia_semantic_routes_rejected"
        )


    if (
        provider_counts[
            "VISUAL_SEARCH_SHADOW"
        ]
        >= 8
    ):

        warnings.append(
            "visual_provider_needed_for_majority_of_scenes"
        )


    if blockers:

        status = "HOLD"

    else:

        status = (
            "PROVIDER_ROUTER_SHADOW_CERTIFIED"
        )


    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            data.get(
                "short_id"
            ),

        "scene_map":
            str(
                scene_map_path
            ),

        "wiki_available":
            WIKI_AVAILABLE,

        "network_probe_limit":
            3,

        "routes":
            routes,

        "wiki_probes":
            wiki_by_scene,

        "decisions":
            decisions,

        "provider_counts":
            dict(
                provider_counts
            ),

        "wiki_rejected_scenes":
            wiki_rejected,

        "face_visual_scenes":
            face_visual,

        "blockers":
            sorted(
                set(blockers)
            ),

        "warnings":
            sorted(
                set(warnings)
            ),

        "automatic_download":
            False,

        "automatic_replace":
            False,

        "media_mutated":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "full_active":
            False,
    }


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


if __name__ == "__main__":

    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI9.20 PROVIDER ROUTER MASTER"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SHORT ID:",
        r["short_id"]
    )

    print(
        "WIKI AVAILABLE:",
        r["wiki_available"]
    )

    print(
        "PROVIDER COUNTS:",
        r["provider_counts"]
    )

    print(
        "WIKI REJECTED SCENES:",
        r["wiki_rejected_scenes"]
    )

    print(
        "FACE VISUAL SCENES:",
        r["face_visual_scenes"]
    )

    print(
        "BLOCKERS:",
        r["blockers"]
    )

    print(
        "WARNINGS:",
        r["warnings"]
    )


    print()
    print(
        "===== PROVIDER PLAN BY SCENE ====="
    )


    for item in r[
        "decisions"
    ]:

        print(
            "SCENE",
            item["scene"],
            "| category=",
            item["category"],
            "| initial=",
            item["initial_provider"],
            "| final=",
            item["final_provider"],
            "| confidence=",
            item["confidence"],
            "| wiki=",
            item["wiki_status"],
            "| accepted=",
            item["accepted_wiki_results"],
            "| reasons=",
            item["reasons"],
        )


    print()
    print(
        "===== WIKIPEDIA PROBES ====="
    )


    for scene, probe in (
        r["wiki_probes"].items()
    ):

        print()
        print(
            "SCENE:",
            scene
        )

        print(
            "STATUS:",
            probe["status"]
        )

        print(
            "ACCEPTED:",
            len(
                probe.get(
                    "accepted"
                )
                or []
            )
        )

        for attempt in (
            probe.get(
                "attempts"
            )
            or []
        ):

            print(
                "  QUERY:",
                attempt.get(
                    "query"
                ),
                "| raw=",
                attempt.get(
                    "raw_count"
                ),
                "| accepted=",
                attempt.get(
                    "accepted_count"
                ),
                "| status=",
                attempt.get(
                    "status"
                ),
            )


    print()
    print(
        "AUTOMATIC DOWNLOAD:",
        r["automatic_download"]
    )

    print(
        "AUTOMATIC REPLACE:",
        r["automatic_replace"]
    )

    print(
        "MEDIA MUTATED:",
        r["media_mutated"]
    )

    print(
        "FFMPEG EXECUTED:",
        r["ffmpeg_executed"]
    )

    print(
        "VIDEO GENERATED:",
        r["video_generated"]
    )

    print(
        "SOURCE RECOVERY:",
        r["source_recovery"]
    )

    print(
        "FULL ACTIVE:",
        r["full_active"]
    )
