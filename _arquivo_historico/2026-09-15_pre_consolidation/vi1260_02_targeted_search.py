#!/usr/bin/env python3

import hashlib
import json
import time

from pathlib import Path


from vi1000_1_semantic_core import norm

from vi1200_02_commons_provider import (
    search as commons_search,
)

from vi1200_03_archive_provider import (
    search as archive_search,
)

from vi1260_01_semantic_roles import (
    scene_requirements,
)


BASE = Path.home() / "ShortAutoPro"

CACHE = (
    BASE
    / "temp/vi1260/cache"
)


def unique(
    values,
    limit=8,
):
    output = []
    seen = set()

    for value in values:
        value = " ".join(
            str(value or "").split()
        )

        if not value:
            continue

        key = norm(value)

        if key in seen:
            continue

        seen.add(key)
        output.append(value)

        if len(output) >= limit:
            break

    return output


def build_queries(
    scene,
    entities,
    limit=8,
):
    requirements = scene_requirements(
        scene,
        entities
    )

    req = set(
        requirements[
            "requirements"
        ]
    )

    person = (
        entities.get("primary_person")
        or {}
    ).get("name") or ""

    location = (
        entities.get("primary_location")
        or {}
    ).get("name") or ""

    queries = []


    if "SPECIFIC_PERSON" in req:
        queries.extend([
            f"{person} photograph",
            f"{person} archival photograph",
            f"{person} archival image",
            f"{person} Hotel Cecil",
            f"{person} elevator",
            f"{person} surveillance video",
        ])


    if "PRIMARY_LOCATION_MENTIONED" in req:
        queries.extend([
            f"{location} Los Angeles",
            f"{location} exterior",
            f"{location} building",
            f"{location} facade",
        ])


    if "HIDE_BEHAVIOR" in req:
        queries.extend([
            "hotel corridor doorway",
            "hotel hallway doorway",
            "elevator hallway corner",
            "hotel corridor door",
            "empty hotel hallway door",
            "person hiding doorway",
        ])


    if "EVIDENCE_DISCUSSION" in req:
        queries.extend([
            f"{person} elevator video",
            f"{location} elevator",
            f"{location} surveillance",
            "CCTV monitor",
            "security camera monitor",
            "elevator surveillance camera",
        ])


    if "BIPOLAR" in req:
        queries.extend([
            "bipolar disorder diagram",
            "bipolar disorder illustration",
            "bipolar mood disorder",
            "mental health mood disorder diagram",
            "psychiatry bipolar disorder",
            "bipolar affective disorder diagram",
        ])


    if "MAINTENANCE_WORKER" in req:
        queries.extend([
            "maintenance worker building",
            "hotel maintenance worker",
            "maintenance technician building",
            "building maintenance employee",
            "maintenance staff hotel",
            "worker checking water tank",
            "maintenance worker rooftop",
        ])


    if "WATER_TANK" in req:
        queries.extend([
            "rooftop water tank",
            "building rooftop water tank",
            "hotel rooftop water tank",
            "water tower rooftop",
            "urban rooftop water tanks",
            "roof water tank building",
        ])


    if not queries:
        queries.extend([
            f"{person} {location}",
            f"{location} Los Angeles",
            "documentary context",
        ])


    return unique(
        queries,
        limit=limit
    )


def cache_key(
    provider,
    query,
):
    raw = (
        provider
        + "\n"
        + query
    ).encode(
        "utf-8"
    )

    return hashlib.sha256(
        raw
    ).hexdigest()


def cached_call(
    provider,
    query,
):
    CACHE.mkdir(
        parents=True,
        exist_ok=True
    )

    path = (
        CACHE
        /
        (
            provider
            + "_"
            + cache_key(
                provider,
                query
            )
            + ".json"
        )
    )


    if path.exists():

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            if data.get("ok"):
                data["_from_cache"] = True
                return data

        except Exception:
            pass


    if provider == "commons":
        data = commons_search(
            query,
            limit=5
        )

    else:
        data = archive_search(
            query,
            limit=4
        )


    data["_from_cache"] = False


    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    time.sleep(
        0.10
    )

    return data


def dedupe_raw(
    values,
):
    result = []
    seen = set()


    for raw in values:

        key = (
            raw.get("provider"),
            raw.get("pageid")
            or
            raw.get("identifier")
            or
            raw.get("title"),
        )


        if key in seen:
            continue


        seen.add(key)
        result.append(raw)


    return result


def search_scene(
    scene,
    entities,
    *,
    limit=8,
):
    queries = build_queries(
        scene,
        entities,
        limit=limit
    )

    raw = []
    calls = []


    req = set(
        scene_requirements(
            scene,
            entities
        )[
            "requirements"
        ]
    )


    archive_allowed = bool(
        req
        &
        {
            "SPECIFIC_PERSON",
            "EVIDENCE_DISCUSSION",
        }
    )


    for index, query in enumerate(
        queries
    ):

        commons = cached_call(
            "commons",
            query
        )


        calls.append({
            "provider":
                "COMMONS",

            "query":
                query,

            "ok":
                commons.get(
                    "ok",
                    False
                ),

            "count":
                commons.get(
                    "count",
                    0
                ),

            "cache":
                commons.get(
                    "_from_cache",
                    False
                ),
        })


        if commons.get("ok"):
            raw.extend(
                commons.get(
                    "results",
                    []
                )
            )


        if (
            archive_allowed
            and
            index < 4
        ):

            archive = cached_call(
                "archive",
                query
            )


            calls.append({
                "provider":
                    "ARCHIVE",

                "query":
                    query,

                "ok":
                    archive.get(
                        "ok",
                        False
                    ),

                "count":
                    archive.get(
                        "count",
                        0
                    ),

                "cache":
                    archive.get(
                        "_from_cache",
                        False
                    ),
            })


            if archive.get("ok"):
                raw.extend(
                    archive.get(
                        "results",
                        []
                    )
                )


    return {
        "scene":
            scene["scene"],

        "queries":
            queries,

        "calls":
            calls,

        "results":
            dedupe_raw(raw),
    }


if __name__ == "__main__":
    print(
        "VI1260 TARGETED SEARCH=PASS"
    )
