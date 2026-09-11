#!/usr/bin/env python3

import json
import re
from pathlib import Path
from collections import Counter


VERSION = "120.00"

BASE = Path.home() / "ShortAutoPro"

VI100 = (
    BASE / "logs/producao/"
    "vi100_00_real_candidate_fusion_latest.json"
)

VI70 = (
    BASE / "logs/producao/"
    "vi70_00_global_visual_casting_latest.json"
)

VI10 = (
    BASE / "logs/producao/"
    "vi10_00_visual_director_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi120_00_query_intelligence_latest.json"
)


STYLE_WORDS = {
    "dark", "mysterious", "cinematic",
    "dramatic", "moody", "creepy",
    "scary", "suspense", "shadow",
    "shadows", "clear", "beautiful",
    "vintage", "atmospheric",
    "foreground", "background",
    "portrait", "wide", "medium",
    "close", "closeup", "shot",
}


GENERIC_WORDS = {
    "person", "people", "someone",
    "thing", "object", "place",
    "scene", "image", "photo",
    "video", "footage",
}


LOCATION_ANCHORS = {
    "hotel", "hallway", "corridor",
    "street", "building", "facade",
    "rooftop", "elevator", "room",
    "door", "doors", "tank",
    "water", "architecture",
}


DOCUMENT_ANCHORS = {
    "document", "paper", "file",
    "letter", "report", "record",
    "certificate", "newspaper",
    "affidavit", "archive",
}


EVIDENCE_ANCHORS = {
    "camera", "cctv", "security",
    "surveillance", "evidence",
    "recording", "monitor",
}


STOP = {
    "the", "and", "for", "with",
    "from", "into", "this", "that",
    "over", "under", "onto",
    "near", "behind", "beside",
    "of", "in", "on", "at",
    "a", "an",
}


def load_gate(path):
    if not path.exists():
        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get(
        "gate",
        data
    )


def by_scene(items):
    out = {}

    for item in items or []:
        try:
            n = int(
                item.get("scene")
            )
        except Exception:
            continue

        out[n] = item

    return out


def words(text):
    return re.findall(
        r"[A-Za-zÀ-ÿ0-9'-]+",
        str(text or "")
    )


def clean_tokens(text):
    output = []
    seen = set()

    for word in words(text):
        low = word.lower()

        if low in STOP:
            continue

        if low in STYLE_WORDS:
            continue

        if low in GENERIC_WORDS:
            continue

        if len(low) < 3:
            continue

        if low in seen:
            continue

        seen.add(low)
        output.append(word)

    return output


def proper_entities(text):
    values = re.findall(
        r"\b(?:[A-Z][a-zÀ-ÿ]+"
        r"(?:\s+[A-Z][a-zÀ-ÿ]+)+)\b",
        str(text or "")
    )

    result = []

    seen = set()

    for value in values:
        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result[:4]


def years(text):
    return re.findall(
        r"\b(?:18|19|20)\d{2}\b",
        str(text or "")
    )[:3]


def anchors(tokens, category):
    lower = {
        x.lower()
        for x in tokens
    }

    category = str(
        category or ""
    ).upper()

    if category == "LOCATION":
        preferred = (
            lower
            & LOCATION_ANCHORS
        )

    elif category in {
        "DOCUMENT",
        "EVIDENCE"
    }:
        preferred = (
            lower
            & (
                DOCUMENT_ANCHORS
                | EVIDENCE_ANCHORS
            )
        )

    else:
        preferred = set()

    return sorted(
        preferred
    )


def compress(tokens, max_words):
    return " ".join(
        tokens[:max_words]
    )


def unique(values):
    out = []
    seen = set()

    for value in values:
        value = " ".join(
            str(value).split()
        ).strip()

        if not value:
            continue

        key = value.lower()

        if key in seen:
            continue

        seen.add(key)
        out.append(value)

    return out


def provider_variants(
    original,
    scene_text,
    category,
    desired_family
):
    combined = (
        str(original or "")
        + " "
        + str(scene_text or "")
    )

    tokens = clean_tokens(
        combined
    )

    scene_tokens = clean_tokens(
        original
    )

    entity_values = proper_entities(
        combined
    )

    year_values = years(
        combined
    )

    anchor_values = anchors(
        tokens,
        category
    )

    factual_core = unique(
        anchor_values
        + scene_tokens
    )

    if not factual_core:
        factual_core = tokens[:6]

    base4 = compress(
        factual_core,
        4
    )

    base5 = compress(
        factual_core,
        5
    )

    base6 = compress(
        factual_core,
        6
    )

    commons = [
        base6,
        base5,
        base4,
    ]

    archive = [
        base6,
        base5,
        base4,
    ]

    # Entity-first searches are much stronger
    # for factual/historical media.
    for entity in entity_values:
        commons.insert(
            0,
            entity + " " + base4
        )

        archive.insert(
            0,
            entity + " " + base4
        )

    if year_values:
        year = year_values[0]

        commons.insert(
            0,
            base4 + " " + year
        )

        archive.insert(
            0,
            base4 + " " + year
        )

    category = str(
        category or ""
    ).upper()

    if desired_family == "ARCHIVAL_IMAGE":
        commons.extend([
            base4 + " archive",
            base4 + " historical",
        ])

    elif desired_family == "VIDEO":
        archive.extend([
            base4 + " film",
            base4 + " footage",
        ])

    if category == "LOCATION":
        commons.append(
            base4 + " exterior"
        )

        archive.append(
            base4 + " location"
        )

    if category == "EVIDENCE":
        commons.append(
            base4 + " surveillance"
        )

    return {
        "commons":
            unique(
                commons
            )[:6],

        "archive":
            unique(
                archive
            )[:6],

        "entities":
            entity_values,

        "years":
            year_values,

        "anchors":
            anchor_values,

        "clean_tokens":
            tokens[:20],
    }


def query_quality(
    query,
    category,
    desired_family
):
    tokens = [
        x.lower()
        for x in words(query)
    ]

    score = 50.0

    if 2 <= len(tokens) <= 6:
        score += 20

    elif len(tokens) > 8:
        score -= 15

    if any(
        x in STYLE_WORDS
        for x in tokens
    ):
        score -= 20

    if any(
        x in GENERIC_WORDS
        for x in tokens
    ):
        score -= 10

    category = str(
        category or ""
    ).upper()

    token_set = set(
        tokens
    )

    if (
        category == "LOCATION"
        and token_set
        & LOCATION_ANCHORS
    ):
        score += 15

    if (
        category in {
            "DOCUMENT",
            "EVIDENCE"
        }
        and token_set
        & (
            DOCUMENT_ANCHORS
            | EVIDENCE_ANCHORS
        )
    ):
        score += 15

    if (
        desired_family
        == "ARCHIVAL_IMAGE"
        and any(
            x in {
                "archive",
                "historical",
            }
            for x in tokens
        )
    ):
        score += 5

    if (
        desired_family
        == "VIDEO"
        and any(
            x in {
                "film",
                "footage",
                "location",
            }
            for x in tokens
        )
    ):
        score += 5

    return round(
        max(
            0,
            min(
                100,
                score
            )
        ),
        2
    )


def evaluate():
    vi100 = load_gate(
        VI100
    )

    vi70 = load_gate(
        VI70
    )

    vi10 = load_gate(
        VI10
    )

    if not vi100:
        raise RuntimeError(
            "vi100_missing"
        )

    short_id = str(
        vi100.get(
            "short_id"
        )
        or ""
    )

    scene_path = (
        BASE / "roteiros"
        / f"scene_map_{short_id}.json"
    )

    scene_data = json.loads(
        scene_path.read_text(
            encoding="utf-8"
        )
    )

    scenes = by_scene(
        scene_data.get(
            "scenes"
        )
        or []
    )

    plans70 = by_scene(
        vi70.get(
            "decisions"
        )
        or []
    )

    plans10 = by_scene(
        vi10.get(
            "plans"
        )
        or []
    )

    previous = by_scene(
        vi100.get(
            "results"
        )
        or []
    )

    results = []

    for scene_num in (
        vi100.get(
            "evaluated_scenes"
        )
        or []
    ):
        scene_num = int(
            scene_num
        )

        scene = scenes.get(
            scene_num,
            {}
        )

        p70 = plans70.get(
            scene_num,
            {}
        )

        p10 = plans10.get(
            scene_num,
            {}
        )

        previous_result = previous.get(
            scene_num,
            {}
        )

        original = (
            scene.get("query")
            or scene.get("segment")
            or ""
        )

        stext = (
            scene.get("segment")
            or ""
        )

        category = (
            p70.get("category")
            or p10.get("category")
            or "GENERAL"
        )

        desired = (
            p70.get(
                "desired_family"
            )
            or p70.get(
                "current_family"
            )
            or "IMAGE"
        )

        generated = provider_variants(
            original,
            stext,
            category,
            desired
        )

        commons_scored = [
            {
                "query": q,
                "quality":
                    query_quality(
                        q,
                        category,
                        desired
                    )
            }
            for q in generated[
                "commons"
            ]
        ]

        archive_scored = [
            {
                "query": q,
                "quality":
                    query_quality(
                        q,
                        category,
                        desired
                    )
            }
            for q in generated[
                "archive"
            ]
        ]

        commons_scored.sort(
            key=lambda x:
                x["quality"],
            reverse=True
        )

        archive_scored.sort(
            key=lambda x:
                x["quality"],
            reverse=True
        )

        results.append({
            "scene":
                scene_num,

            "category":
                category,

            "desired_family":
                desired,

            "original_query":
                original,

            "previous_candidates":
                previous_result.get(
                    "candidate_count",
                    0
                ),

            "previous_qualified":
                previous_result.get(
                    "qualified_count",
                    0
                ),

            "entities":
                generated[
                    "entities"
                ],

            "years":
                generated[
                    "years"
                ],

            "anchors":
                generated[
                    "anchors"
                ],

            "commons_queries":
                commons_scored,

            "archive_queries":
                archive_scored,

            "best_commons_query":
                (
                    commons_scored[0]
                    if commons_scored
                    else None
                ),

            "best_archive_query":
                (
                    archive_scored[0]
                    if archive_scored
                    else None
                ),
        })

    high_quality = [
        x["scene"]
        for x in results
        if (
            (
                x[
                    "best_commons_query"
                ]
                or {}
            ).get(
                "quality",
                0
            ) >= 70
            or (
                (
                    x[
                        "best_archive_query"
                    ]
                    or {}
                ).get(
                    "quality",
                    0
                ) >= 70
            )
        )
    ]

    blockers = []

    warnings = []

    for x in results:
        if (
            not x[
                "commons_queries"
            ]
            and not x[
                "archive_queries"
            ]
        ):
            warnings.append(
                "scene_query_generation_empty"
            )
            break

    status = (
        "HOLD"
        if blockers
        else
        "VI120_QUERY_INTELLIGENCE_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "evaluated_scenes":
            [
                x["scene"]
                for x in results
            ],

        "high_quality_query_scenes":
            high_quality,

        "results":
            results,

        "blockers":
            blockers,

        "warnings":
            sorted(
                set(warnings)
            ),

        "network_executed":
            False,

        "download_executed":
            False,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "automatic_replace":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            {"gate": report},
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return report


if __name__ == "__main__":
    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI120 QUERY INTELLIGENCE"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "EVALUATED:",
        r[
            "evaluated_scenes"
        ]
    )

    print(
        "HIGH QUALITY QUERY SCENES:",
        r[
            "high_quality_query_scenes"
        ]
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

    for x in r["results"]:
        print(
            "SCENE:",
            x["scene"]
        )

        print(
            " CATEGORY:",
            x["category"]
        )

        print(
            " DESIRED:",
            x[
                "desired_family"
            ]
        )

        print(
            " ORIGINAL:",
            x[
                "original_query"
            ]
        )

        print(
            " ENTITIES:",
            x["entities"]
        )

        print(
            " ANCHORS:",
            x["anchors"]
        )

        print(
            " PREVIOUS:",
            x[
                "previous_candidates"
            ],
            "candidates /",
            x[
                "previous_qualified"
            ],
            "qualified"
        )

        print(
            " COMMONS:"
        )

        for q in (
            x[
                "commons_queries"
            ][:3]
        ):
            print(
                "   ",
                q["quality"],
                "|",
                q["query"]
            )

        print(
            " ARCHIVE:"
        )

        for q in (
            x[
                "archive_queries"
            ][:3]
        ):
            print(
                "   ",
                q["quality"],
                "|",
                q["query"]
            )

        print()

    print(
        "NETWORK EXECUTED:",
        r["network_executed"]
    )

    print(
        "DOWNLOAD EXECUTED:",
        r["download_executed"]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
        ]
    )

    print(
        "FFMPEG EXECUTED:",
        r[
            "ffmpeg_executed"
        ]
    )

    print(
        "VIDEO GENERATED:",
        r[
            "video_generated"
        ]
    )
