#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import copy
import hashlib
import json
import re
import time
from pathlib import Path

import requests


VERSION = "400.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI260 = (
    LOG /
    "vi260_00_global_provenance_director_latest.json"
)

VI300 = (
    LOG /
    "vi300_00_targeted_global_search_latest.json"
)

VI320 = (
    LOG /
    "vi320_00_deep_context_truth_latest.json"
)

VI330 = (
    LOG /
    "vi330_00_controlled_real_ab_latest.json"
)

OUT = (
    LOG /
    "vi400_00_speed_quality_accelerator_latest.json"
)

CACHE = (
    BASE /
    "temp/vi400_cache/metadata_cache.json"
)

SHADOW = (
    BASE /
    "temp/vi400_shadow/"
    "motion_plan_2026-09-01_1433_vi400_shadow.json"
)

COMMONS = (
    "https://commons.wikimedia.org/w/api.php"
)

ARCHIVE_SEARCH = (
    "https://archive.org/advancedsearch.php"
)

ARCHIVE_META = (
    "https://archive.org/metadata/"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/400.00 "
        "(speed-quality metadata research)"
}

MAX_RESULTS = 12

# 24h de cache.
CACHE_TTL = 86400


NEGATIVE = {
    "live stream",
    "livestream",
    "podcast",
    "review",
    "reaction",
    "gameplay",
    "walkthrough",
    "creepypasta",
    "compilation",
    "commentary",
    "trailer",
    "teaser",
    "lyrics",
}


WRONG_GEO = {
    "alexandria",
    "egypt",
    "ägypten",
    "egypten",
    "alexandrie",
}


ROLE_TERMS = {
    "ELEVATOR": {
        "elevator",
        "elevator video",
        "elevator footage",
        "lift",
    },

    "HALLWAY": {
        "hallway",
        "corridor",
        "hotel hallway",
        "hotel corridor",
    },

    "ROOFTOP": {
        "rooftop",
        "roof",
        "water tank",
        "water tower",
    },

    "SURVEILLANCE": {
        "cctv",
        "security camera",
        "surveillance",
        "closed circuit",
    },

    "DOCUMENT": {
        "official document",
        "police report",
        "report",
        "official record",
        "death certificate",
        "certificate",
        "autopsy",
        "coroner",
        "court record",
        "newspaper",
        "scanned document",
    },

    "MEDICINE": {
        "medicine",
        "medication",
        "prescription",
        "pill bottle",
        "medicine bottle",
        "prescription bottle",
    },
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


def normalize(value):
    text = re.sub(
        r"<[^>]+>",
        " ",
        str(value or "")
    )

    # Namespace do Commons NÃO é significado visual.
    text = re.sub(
        r"^\s*File\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = (
        text
        .replace("_", " ")
        .replace("-", " ")
        .lower()
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def clamp(value):
    return round(
        max(
            0,
            min(
                100,
                float(value)
            )
        ),
        2
    )


def load_cache():
    if not CACHE.exists():
        return {
            "entries": {}
        }

    try:
        return json.loads(
            CACHE.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {
            "entries": {}
        }


def save_cache(cache):
    CACHE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    CACHE.write_text(
        json.dumps(
            cache,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def cached_json(
    url,
    params,
    key,
    cache
):
    now = time.time()

    entry = (
        cache
        .get("entries", {})
        .get(key)
    )

    if entry:
        age = (
            now
            - float(
                entry.get(
                    "time",
                    0
                )
            )
        )

        if age < CACHE_TTL:
            return (
                entry.get(
                    "data",
                    {}
                ),
                "CACHE"
            )

    wait = 4

    for attempt in range(3):
        try:
            r = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=25
            )

            if r.status_code == 429:
                retry = (
                    r.headers.get(
                        "Retry-After"
                    )
                    or wait
                )

                try:
                    retry = int(
                        retry
                    )
                except Exception:
                    retry = wait

                time.sleep(
                    min(
                        30,
                        max(
                            5,
                            retry
                        )
                    )
                )

                wait = min(
                    wait * 2,
                    20
                )

                continue

            r.raise_for_status()

            data = r.json()

            cache.setdefault(
                "entries",
                {}
            )[key] = {
                "time":
                    now,

                "data":
                    data,
            }

            return (
                data,
                "NETWORK"
            )

        except Exception as exc:
            if attempt == 2:
                return (
                    {
                        "_error":
                            type(exc).__name__
                            + ":"
                            + str(exc)[:160]
                    },
                    "ERROR"
                )

            time.sleep(wait)

            wait = min(
                wait * 2,
                20
            )

    return (
        {
            "_error":
                "unknown"
        },
        "ERROR"
    )


def license_score(text):
    low = normalize(text)

    if any(
        x in low
        for x in (
            "public domain",
            "publicdomain",
            "cc0",
            "zero/1.0",
        )
    ):
        return 100

    if (
        "cc by-sa" in low
        or "/by-sa/" in low
    ):
        return 92

    if (
        "cc by" in low
        or "/by/" in low
    ):
        return 90

    if "creativecommons" in low:
        return 82

    return 45


def role_hits(
    role,
    text
):
    low = normalize(text)

    return sorted({
        term
        for term in ROLE_TERMS.get(
            role,
            set()
        )
        if term in low
    })


def negative_terms(text):
    low = normalize(text)

    return sorted({
        term
        for term in NEGATIVE
        if term in low
    })


def wrong_geo(text):
    low = normalize(text)

    return sorted({
        term
        for term in WRONG_GEO
        if term in low
    })


def entity_truth(
    anchor,
    text
):
    if not anchor:
        return True, []

    low = normalize(text)

    hits = []

    if normalize(anchor) == "hotel cecil":
        if (
            "hotel cecil" in low
            or "cecil hotel" in low
        ):
            hits.append(
                "Hotel Cecil"
            )

        if (
            "los angeles" in low
            or "hotel cecil la" in low
        ):
            hits.append(
                "Los Angeles"
            )

        if "elisa lam" in low:
            hits.append(
                "Elisa Lam"
            )

        # Hotel Cecil sozinho NÃO basta.
        valid = (
            (
                "Hotel Cecil" in hits
                and
                "Los Angeles" in hits
            )
            or
            "Elisa Lam" in hits
        )

    else:
        valid = (
            normalize(anchor)
            in low
        )

        if valid:
            hits.append(
                anchor
            )

    return valid, hits


def technical_score(
    width,
    height
):
    pixels = (
        int(width or 0)
        * int(height or 0)
    )

    if pixels >= 2_000_000:
        return 100

    if pixels >= 1_000_000:
        return 90

    if pixels >= 500_000:
        return 75

    if pixels >= 200_000:
        return 60

    return 40


def commons_search(
    query,
    family,
    cache
):
    params = {
        "action":
            "query",

        "generator":
            "search",

        "gsrsearch":
            query,

        "gsrnamespace":
            6,

        "gsrlimit":
            MAX_RESULTS,

        "prop":
            "imageinfo",

        "iiprop":
            "url|size|mime|mediatype|extmetadata",

        "format":
            "json",

        "formatversion":
            2,
    }

    key = (
        "commons|"
        + family
        + "|"
        + query.lower()
    )

    data, source = cached_json(
        COMMONS,
        params,
        key,
        cache
    )

    pages = (
        data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        )
        if isinstance(
            data,
            dict
        )
        else []
    )

    results = []

    for page in pages:
        infos = (
            page.get(
                "imageinfo"
            )
            or []
        )

        if not infos:
            continue

        info = infos[0]

        mime = normalize(
            info.get("mime")
        )

        mediatype = normalize(
            info.get(
                "mediatype"
            )
        )

        actual_family = (
            "VIDEO"
            if (
                mime.startswith(
                    "video/"
                )
                or
                mediatype == "video"
            )
            else
            "IMAGE"
        )

        wanted = (
            "IMAGE"
            if family
            == "ARCHIVAL_IMAGE"
            else family
        )

        if (
            actual_family
            != wanted
        ):
            continue

        meta = (
            info.get(
                "extmetadata"
            )
            or {}
        )

        def mv(key):
            value = (
                meta.get(key)
                or {}
            )

            if isinstance(
                value,
                dict
            ):
                return str(
                    value.get(
                        "value"
                    )
                    or ""
                )

            return str(
                value or ""
            )

        title = str(
            page.get(
                "title"
            )
            or ""
        )

        description = re.sub(
            r"<[^>]+>",
            " ",
            mv(
                "ImageDescription"
            )
        )

        # Query NÃO entra na evidência.
        evidence = " ".join([
            title,
            description,
            mv("Categories"),
            mv("ObjectName"),
        ])

        results.append({
            "provider":
                "WIKIMEDIA_COMMONS",

            "key":
                info.get("url")
                or title,

            "title":
                title,

            "url":
                info.get("url"),

            "family":
                actual_family,

            "evidence":
                evidence,

            "width":
                int(
                    info.get(
                        "width"
                    )
                    or 0
                ),

            "height":
                int(
                    info.get(
                        "height"
                    )
                    or 0
                ),

            "license":
                mv(
                    "LicenseShortName"
                ),

            "license_text":
                (
                    mv(
                        "LicenseShortName"
                    )
                    + " "
                    + mv(
                        "UsageTerms"
                    )
                ),
        })

    return results, source


def archive_video_search(
    query,
    cache
):
    params = {
        "q":
            f"({query}) AND mediatype:movies",

        "fl[]":
            "identifier,title,description,"
            "licenseurl,creator,date",

        "rows":
            MAX_RESULTS,

        "page":
            1,

        "output":
            "json",
    }

    key = (
        "archive-search|"
        + query.lower()
    )

    data, source = cached_json(
        ARCHIVE_SEARCH,
        params,
        key,
        cache
    )

    docs = (
        data.get(
            "response",
            {}
        ).get(
            "docs",
            []
        )
        if isinstance(
            data,
            dict
        )
        else []
    )

    results = []

    for item in docs:
        description = (
            item.get(
                "description"
            )
            or ""
        )

        if isinstance(
            description,
            list
        ):
            description = " ".join(
                str(x)
                for x in description
            )

        identifier = str(
            item.get(
                "identifier"
            )
            or ""
        )

        title = str(
            item.get(
                "title"
            )
            or ""
        )

        results.append({
            "provider":
                "INTERNET_ARCHIVE",

            "identifier":
                identifier,

            "key":
                "ia:"
                + identifier,

            "title":
                title,

            "family":
                "VIDEO",

            "evidence":
                (
                    title
                    + " "
                    + str(
                        description
                    )
                ),

            "license":
                str(
                    item.get(
                        "licenseurl"
                    )
                    or ""
                ),

            "license_text":
                str(
                    item.get(
                        "licenseurl"
                    )
                    or ""
                ),
        })

    return results, source


def archive_deep(
    candidate,
    cache
):
    identifier = (
        candidate.get(
            "identifier"
        )
    )

    key = (
        "archive-meta|"
        + str(identifier)
    )

    data, source = cached_json(
        ARCHIVE_META
        + str(identifier),
        None,
        key,
        cache
    )

    if (
        not isinstance(
            data,
            dict
        )
        or data.get(
            "_error"
        )
    ):
        return None, source

    metadata = (
        data.get(
            "metadata"
        )
        or {}
    )

    evidence = " ".join(
        str(
            metadata.get(key)
            or ""
        )
        for key in (
            "title",
            "description",
            "subject",
            "collection",
            "creator",
        )
    )

    files = []

    for item in (
        data.get(
            "files"
        )
        or []
    ):
        name = str(
            item.get(
                "name"
            )
            or ""
        )

        fmt = normalize(
            item.get(
                "format"
            )
        )

        ext = (
            Path(name)
            .suffix.lower()
        )

        if not (
            ext in {
                ".mp4",
                ".webm",
                ".ogv",
                ".mpeg",
                ".mpg",
                ".mov",
                ".m4v",
            }
            or
            "mpeg4" in fmt
            or
            "webm" in fmt
            or
            "h.264" in fmt
        ):
            continue

        def number(key):
            try:
                return float(
                    item.get(
                        key
                    )
                    or 0
                )
            except Exception:
                return 0

        files.append({
            "name":
                name,

            "size":
                int(
                    number("size")
                ),

            "width":
                int(
                    number("width")
                ),

            "height":
                int(
                    number("height")
                ),

            "length":
                number("length"),
        })

    files.sort(
        key=lambda x: (
            x["width"]
            * x["height"],
            x["size"],
        ),
        reverse=True
    )

    if not files:
        return None, source

    result = dict(
        candidate
    )

    result["evidence"] = (
        evidence
    )

    result["best_file"] = (
        files[0]
    )

    result["width"] = (
        files[0]["width"]
    )

    result["height"] = (
        files[0]["height"]
    )

    result["license_text"] = str(
        metadata.get(
            "licenseurl"
        )
        or candidate.get(
            "license_text"
        )
        or ""
    )

    result["license"] = (
        result[
            "license_text"
        ]
    )

    return result, source


def evaluate_candidate(
    candidate,
    policy
):
    evidence = (
        candidate.get(
            "evidence"
        )
        or ""
    )

    geo = wrong_geo(
        evidence
    )

    entity_ok, entity_hits = (
        entity_truth(
            policy.get(
                "anchor"
            ),
            evidence
        )
    )

    hits = role_hits(
        policy[
            "role"
        ],
        evidence
    )

    neg = negative_terms(
        evidence
    )

    lic = license_score(
        candidate.get(
            "license_text"
        )
    )

    tech = technical_score(
        candidate.get(
            "width"
        ),
        candidate.get(
            "height"
        )
    )

    entity_required = (
        policy.get(
            "entity_required",
            False
        )
    )

    if entity_required:
        entity_gate = (
            entity_ok
        )
    else:
        entity_gate = True

    wanted_family = (
        "IMAGE"
        if policy["family"]
        == "ARCHIVAL_IMAGE"
        else policy["family"]
    )

    gates = {
        "family":
            candidate.get(
                "family"
            )
            == wanted_family,

        "entity":
            entity_gate,

        "wrong_geo_absent":
            not bool(
                geo
            ),

        "role":
            bool(
                hits
            ),

        "negative_absent":
            not bool(
                neg
            ),

        "license":
            lic >= 80,

        "technical_metadata":
            tech >= 40,
    }

    score = 0

    if entity_gate:
        score += 35

    if hits:
        score += 30

    if lic >= 80:
        score += 15

    if tech >= 60:
        score += 10
    else:
        score += 5

    if (
        not geo
        and not neg
    ):
        score += 10

    score = clamp(
        score
    )

    return {
        **candidate,

        "entity_hits":
            entity_hits,

        "wrong_geo":
            geo,

        "role_hits":
            hits,

        "negative_terms":
            neg,

        "license_score":
            lic,

        "technical_score":
            tech,

        "gates":
            gates,

        "final_score":
            score,

        "decision":
            (
                "TRUE_CANDIDATE"
                if all(
                    gates.values()
                )
                else "REJECT"
            ),
    }


def render_geometry(
    width,
    height
):
    if not width or not height:
        return {
            "cover_scale":
                None,

            "retained_fraction":
                None,
        }

    # Escala necessária para preencher 1080x1920.
    scale = max(
        1080 / width,
        1920 / height
    )

    scaled_width = (
        width * scale
    )

    scaled_height = (
        height * scale
    )

    retained = min(
        1.0,
        (
            1080 * 1920
        )
        /
        (
            scaled_width
            * scaled_height
        )
    )

    return {
        "cover_scale":
            round(
                scale,
                2
            ),

        "retained_fraction":
            round(
                retained,
                3
            ),
    }


def build_policies():
    # FACE 5/6/10 não entram aqui.
    # Permanecem em quarentena de identidade.
    return {
        3: {
            "role":
                "HALLWAY",

            "family":
                "VIDEO",

            "anchor":
                "Hotel Cecil",

            "entity_required":
                True,

            "queries": [
                "Hotel Cecil hallway",
                "Hotel Cecil corridor",
            ],
        },

        8: {
            "role":
                "HALLWAY",

            "family":
                "VIDEO",

            "anchor":
                "Hotel Cecil",

            "entity_required":
                True,

            "queries": [
                "Hotel Cecil hallway",
                "Hotel Cecil corridor",
            ],
        },

        11: {
            "role":
                "ROOFTOP",

            "family":
                "VIDEO",

            "anchor":
                "Hotel Cecil",

            "entity_required":
                True,

            "queries": [
                "Hotel Cecil rooftop water tank",
                "Hotel Cecil roof water tower",
            ],
        },

        4: {
            "role":
                "SURVEILLANCE",

            "family":
                "ARCHIVAL_IMAGE",

            "anchor":
                "Hotel Cecil",

            "entity_required":
                True,

            "queries": [
                "Hotel Cecil CCTV security camera",
                "Elisa Lam surveillance camera",
            ],
        },

        9: {
            "role":
                "MEDICINE",

            "family":
                "IMAGE",

            # Cena simbólica.
            # Não inventar que frascos pertencem ao caso.
            "anchor":
                None,

            "entity_required":
                False,

            "queries": [
                "prescription medicine bottles",
                "prescription medication bottles",
            ],
        },

        12: {
            "role":
                "DOCUMENT",

            "family":
                "ARCHIVAL_IMAGE",

            "anchor":
                "Hotel Cecil",

            "entity_required":
                True,

            "queries": [
                "Hotel Cecil official record document",
                "Elisa Lam official report document",
            ],
        },
    }


def find_motion_plan(
    short_id
):
    possibilities = [
        (
            BASE /
            "roteiros" /
            f"motion_plan_{short_id}.json"
        ),

        (
            BASE /
            f"motion_plan_{short_id}.json"
        ),
    ]

    for path in possibilities:
        if path.exists():
            return path

    return None


def build_shadow_plan(
    short_id,
    scene1_strategy,
    current_geometry,
    candidate_geometry,
    candidate
):
    motion = find_motion_plan(
        short_id
    )

    if not motion:
        return {
            "written":
                False,

            "source":
                None,

            "path":
                None,
        }

    original = json.loads(
        motion.read_text(
            encoding="utf-8"
        )
    )

    meta = {
        "scene_1": {
            "strategy":
                scene1_strategy,

            # Fundamental:
            # mídia atual NÃO é trocada.
            "keep_base_media":
                True,

            "candidate_path":
                candidate.get(
                    "sandbox_path"
                ),

            "candidate_truth_score":
                min(
                    100,
                    int(
                        candidate.get(
                            "normalized_truth_score"
                        )
                        or 0
                    )
                ),

            "candidate_low_res":
                bool(
                    candidate.get(
                        "archival_low_resolution"
                    )
                ),

            "candidate_geometry":
                candidate_geometry,

            "current_geometry":
                current_geometry,

            "renderer_activation":
                False,

            "note":
                (
                    "authentic archival candidate; "
                    "insert metadata only"
                ),
        },

        "global": {
            "production_media_preserved":
                True,

            "renderer_activation":
                False,

            "ffmpeg":
                False,

            "video_generation":
                False,
        },
    }

    # Preserva 100% da estrutura original.
    if isinstance(
        original,
        dict
    ):
        shadow = copy.deepcopy(
            original
        )

        shadow[
            "vi400_shadow"
        ] = meta

    else:
        shadow = {
            "source_plan":
                original,

            "vi400_shadow":
                meta,
        }

    SHADOW.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    SHADOW.write_text(
        json.dumps(
            shadow,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return {
        "written":
            True,

        "source":
            str(
                motion
            ),

        "source_sha256":
            sha256(
                motion
            ),

        "path":
            str(
                SHADOW
            ),
    }


def evaluate():
    vi260 = load_gate(
        VI260
    )

    vi300 = load_gate(
        VI300
    )

    vi320 = load_gate(
        VI320
    )

    vi330 = load_gate(
        VI330
    )

    if not all(
        (
            vi260,
            vi300,
            vi320,
            vi330,
        )
    ):
        raise RuntimeError(
            "required_vi_state_missing"
        )

    short_id = str(
        vi260.get(
            "short_id"
        )
        or _sap_resolve_short_id()
    )

    current = (
        vi330.get(
            "current"
        )
        or {}
    )

    candidate = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    current_geometry = (
        render_geometry(
            int(
                current.get(
                    "width"
                )
                or 0
            ),
            int(
                current.get(
                    "height"
                )
                or 0
            )
        )
    )

    candidate_geometry = (
        render_geometry(
            int(
                candidate.get(
                    "width"
                )
                or 0
            ),
            int(
                candidate.get(
                    "height"
                )
                or 0
            )
        )
    )

    low_res = bool(
        candidate.get(
            "archival_low_resolution"
        )
    )

    truth_score = min(
        100,
        int(
            candidate.get(
                "normalized_truth_score"
            )
            or 0
        )
    )

    truth = (
        truth_score >= 95
    )

    cover_scale = (
        candidate_geometry.get(
            "cover_scale"
        )
        or 99
    )

    retained = (
        candidate_geometry.get(
            "retained_fraction"
        )
        or 0
    )

    fullscreen_risk = (
        cover_scale > 3.0
        or retained < 0.60
    )

    # Grande correção:
    # verdade alta não significa fullscreen automático.
    if (
        truth
        and (
            low_res
            or fullscreen_risk
        )
    ):
        scene1_strategy = (
            "HYBRID_ARCHIVAL_INSERT_ONLY"
        )

    elif truth:
        scene1_strategy = (
            "SHADOW_FULL_REPLACEMENT_CANDIDATE"
        )

    else:
        scene1_strategy = (
            "KEEP_CURRENT"
        )

    shadow = build_shadow_plan(
        short_id,
        scene1_strategy,
        current_geometry,
        candidate_geometry,
        candidate
    )


    policies = (
        build_policies()
    )

    # Agrupa cenas com exatamente a mesma necessidade.
    # 3 e 8, por exemplo, deixam de repetir
    # a mesma busca de hallway.
    groups = {}

    for scene, policy in (
        policies.items()
    ):
        signature = (
            policy["role"],
            policy["family"],
            policy.get("anchor"),
            tuple(
                policy["queries"]
            ),
        )

        groups.setdefault(
            signature,
            {
                "policy":
                    policy,

                "scenes":
                    [],
            }
        )[
            "scenes"
        ].append(
            scene
        )

    cache = load_cache()

    cache_stats = {
        "CACHE": 0,
        "NETWORK": 0,
        "ERROR": 0,
    }

    candidates_by_group = {}

    network_groups = []

    for signature, group in (
        groups.items()
    ):
        policy = group[
            "policy"
        ]

        raw = []

        for query in (
            policy["queries"]
        ):
            if (
                policy["family"]
                == "VIDEO"
            ):
                archive, source = (
                    archive_video_search(
                        query,
                        cache
                    )
                )

                raw.extend(
                    archive
                )

                cache_stats[
                    source
                ] = (
                    cache_stats.get(
                        source,
                        0
                    )
                    + 1
                )

                commons, source = (
                    commons_search(
                        query,
                        "VIDEO",
                        cache
                    )
                )

                raw.extend(
                    commons
                )

                cache_stats[
                    source
                ] = (
                    cache_stats.get(
                        source,
                        0
                    )
                    + 1
                )

            else:
                commons, source = (
                    commons_search(
                        query,
                        policy[
                            "family"
                        ],
                        cache
                    )
                )

                raw.extend(
                    commons
                )

                cache_stats[
                    source
                ] = (
                    cache_stats.get(
                        source,
                        0
                    )
                    + 1
                )

        # Deduplicação global do grupo.
        dedup = {}

        for item in raw:
            key = (
                item.get("key")
                or item.get(
                    "title"
                )
            )

            dedup[key] = item

        raw = list(
            dedup.values()
        )

        # Archive só recebe consulta profunda
        # depois de passar um prefilter barato.
        if (
            policy["family"]
            == "VIDEO"
        ):
            deep_ready = []

            for item in raw:
                if (
                    item["provider"]
                    == "INTERNET_ARCHIVE"
                ):
                    if policy.get(
                        "entity_required"
                    ):
                        entity_ok, _ = (
                            entity_truth(
                                policy.get(
                                    "anchor"
                                ),
                                item.get(
                                    "evidence"
                                )
                            )
                        )

                        role_ok = bool(
                            role_hits(
                                policy[
                                    "role"
                                ],
                                item.get(
                                    "evidence"
                                )
                            )
                        )

                        if (
                            not entity_ok
                            or not role_ok
                            or wrong_geo(
                                item.get(
                                    "evidence"
                                )
                            )
                            or negative_terms(
                                item.get(
                                    "evidence"
                                )
                            )
                        ):
                            continue

                    deep, source = (
                        archive_deep(
                            item,
                            cache
                        )
                    )

                    cache_stats[
                        source
                    ] = (
                        cache_stats.get(
                            source,
                            0
                        )
                        + 1
                    )

                    if deep:
                        deep_ready.append(
                            deep
                        )

                else:
                    deep_ready.append(
                        item
                    )

            raw = deep_ready

        evaluated = [
            evaluate_candidate(
                item,
                policy
            )
            for item in raw
        ]

        evaluated.sort(
            key=lambda x: (
                x["decision"]
                == "TRUE_CANDIDATE",

                x[
                    "final_score"
                ],
            ),
            reverse=True
        )

        candidates_by_group[
            signature
        ] = evaluated

        network_groups.append({
            "scenes":
                group["scenes"],

            "role":
                policy["role"],

            "family":
                policy["family"],

            "queries":
                policy["queries"],

            "candidate_count":
                len(
                    evaluated
                ),

            "approved_count":
                sum(
                    x["decision"]
                    == "TRUE_CANDIDATE"
                    for x in evaluated
                ),
        })

    save_cache(
        cache
    )

    # Um vencedor não pode ser distribuído
    # automaticamente para várias cenas.
    used_candidates = set()

    scene_results = {}

    for scene in sorted(
        policies
    ):
        policy = policies[
            scene
        ]

        signature = (
            policy["role"],
            policy["family"],
            policy.get("anchor"),
            tuple(
                policy["queries"]
            ),
        )

        approved = [
            x
            for x in (
                candidates_by_group.get(
                    signature,
                    []
                )
            )
            if x[
                "decision"
            ]
            == "TRUE_CANDIDATE"
        ]

        winner = None

        for item in approved:
            key = (
                item.get("key")
                or item.get(
                    "title"
                )
            )

            if key in used_candidates:
                continue

            winner = item

            used_candidates.add(
                key
            )

            break

        scene_results[
            scene
        ] = {
            "scene":
                scene,

            "role":
                policy["role"],

            "family":
                policy["family"],

            "queries":
                policy["queries"],

            "approved_count":
                len(
                    approved
                ),

            "winner":
                winner,

            "decision":
                (
                    "READY_FOR_DEEP_AB_METADATA"
                    if winner
                    else "KEEP_CURRENT"
                ),
        }

    global_plan = []

    for scene in range(
        1,
        13
    ):
        if scene == 1:
            action = (
                scene1_strategy
            )

        elif scene == 2:
            action = (
                "KEEP_CURRENT_VERIFIED"
            )

        elif scene == 7:
            action = (
                "KEEP_CURRENT_SEARCH_EXHAUSTED"
            )

        elif scene in {
            5,
            6,
            10,
        }:
            action = (
                "IDENTITY_QUARANTINE"
            )

        else:
            action = (
                scene_results
                .get(
                    scene,
                    {}
                )
                .get(
                    "decision",
                    "KEEP_CURRENT"
                )
            )

        winner = (
            scene_results
            .get(
                scene,
                {}
            )
            .get(
                "winner"
            )
        )

        global_plan.append({
            "scene":
                scene,

            "action":
                action,

            "winner":
                (
                    winner.get(
                        "title"
                    )
                    if winner
                    else None
                ),
        })

    ready = [
        x["scene"]
        for x in global_plan
        if x["action"]
        == "READY_FOR_DEEP_AB_METADATA"
    ]

    warnings = []

    if low_res:
        warnings.append(
            "scene1_archival_video_insert_only"
        )

    if cache_stats.get(
        "ERROR",
        0
    ):
        warnings.append(
            "provider_errors_present"
        )

    report = {
        "version":
            VERSION,

        "status":
            "VI400_SPEED_QUALITY_ACCELERATOR_CERTIFIED",

        "short_id":
            short_id,

        "scene1": {
            "strategy":
                scene1_strategy,

            "truth_score":
                truth_score,

            "current_geometry":
                current_geometry,

            "candidate_geometry":
                candidate_geometry,

            "candidate_low_res":
                low_res,

            "fullscreen_risk":
                fullscreen_risk,

            "full_replacement_allowed":
                (
                    truth
                    and
                    not low_res
                    and
                    not fullscreen_risk
                ),

            "shadow_plan_written":
                shadow["written"],

            "shadow_plan_source":
                shadow["source"],

            "shadow_plan_path":
                shadow["path"],
        },

        "speed": {
            "scene_search_count":
                len(
                    policies
                ),

            "group_count":
                len(
                    groups
                ),

            "saved_duplicate_scene_searches":
                (
                    len(
                        policies
                    )
                    - len(
                        groups
                    )
                ),

            "cache_stats":
                cache_stats,

            "cache_ttl_seconds":
                CACHE_TTL,
        },

        "network_groups":
            network_groups,

        "scene_search_results": [
            scene_results[key]
            for key in sorted(
                scene_results
            )
        ],

        "ready_for_next_deep_ab":
            ready,

        "global_plan":
            global_plan,

        "identity_quarantine": [
            5,
            6,
            10,
        ],

        "verified_keep": [
            2
        ],

        "search_exhausted_keep": [
            7
        ],

        "blockers":
            [],

        "warnings":
            warnings,

        "network_executed":
            cache_stats.get(
                "NETWORK",
                0
            ) > 0,

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
            {
                "gate":
                    report
            },
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
        " VI400 SPEED + QUALITY ACCELERATOR"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SCENE 1 STRATEGY:",
        r["scene1"]["strategy"]
    )

    print(
        "SCENE 1 TRUTH:",
        r["scene1"]["truth_score"]
    )

    print(
        "CURRENT GEOMETRY:",
        r["scene1"][
            "current_geometry"
        ]
    )

    print(
        "CANDIDATE GEOMETRY:",
        r["scene1"][
            "candidate_geometry"
        ]
    )

    print(
        "FULLSCREEN RISK:",
        r["scene1"][
            "fullscreen_risk"
        ]
    )

    print(
        "FULL REPLACEMENT:",
        r["scene1"][
            "full_replacement_allowed"
        ]
    )

    print(
        "SHADOW PLAN:",
        r["scene1"][
            "shadow_plan_path"
        ]
    )

    print()
    print(
        "SEARCH SCENES:",
        r["speed"][
            "scene_search_count"
        ]
    )

    print(
        "SEARCH GROUPS:",
        r["speed"][
            "group_count"
        ]
    )

    print(
        "DUPLICATE SEARCHES SAVED:",
        r["speed"][
            "saved_duplicate_scene_searches"
        ]
    )

    print(
        "CACHE STATS:",
        r["speed"][
            "cache_stats"
        ]
    )

    print(
        "READY NEXT A/B:",
        r[
            "ready_for_next_deep_ab"
        ]
    )

    print()
    print(
        "===== GLOBAL PLAN ====="
    )

    for item in r[
        "global_plan"
    ]:
        print(
            "SCENE",
            item["scene"],
            "|",
            item["action"],
            "| winner=",
            item["winner"],
        )

    print()
    print(
        "===== GROUPED SEARCH ====="
    )

    for group in r[
        "network_groups"
    ]:
        print(
            "SCENES",
            group["scenes"],
            "| role=",
            group["role"],
            "| family=",
            group["family"],
            "| candidates=",
            group["candidate_count"],
            "| approved=",
            group["approved_count"],
        )

        print(
            "   QUERIES:",
            group["queries"]
        )

    print()
    print(
        "WARNINGS:",
        r["warnings"]
    )

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
        "PRODUCTION PLAN MUTATED:",
        r[
            "production_plan_mutated"
        ]
    )

    print(
        "AUTOMATIC REPLACE:",
        r[
            "automatic_replace"
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
