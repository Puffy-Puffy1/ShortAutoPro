#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "225.00"

BASE = Path.home() / "ShortAutoPro"

VI220 = (
    BASE / "logs/producao/"
    "vi220_00_role_constrained_entity_search_latest.json"
)

VI200 = (
    BASE / "logs/producao/"
    "vi200_00_entity_first_search_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi225_00_safe_family_fallback_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/225.00 "
        "(safe visual fallback verification)"
}


PRIMARY_ENTITY = "Hotel Cecil"
SECONDARY_ENTITY = "Los Angeles"
REQUIRED_ROLE = "FACADE"

MIN_ROLE = 75
MIN_FINAL = 72


NEGATIVE = {
    "room rate",
    "rate sign",
    "sign",
    "plaque",
    "elevator",
    "lift",
    "livestream",
    "live stream",
    "stream",
    "review",
    "reaction",
    "podcast",
}


ROLE_TERMS = {
    "facade",
    "façade",
    "exterior",
    "street",
    "street scene",
    "building",
    "front",
    "entrance",
}


def load_gate(path):
    if not path.exists():
        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get("gate", data)


def normalize(text):
    text = str(text or "")

    text = re.sub(
        r"^\s*File\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = text.lower()

    text = text.replace(
        "_",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def negative_terms(text):
    low = normalize(text)

    return sorted({
        term
        for term in NEGATIVE
        if term in low
    })


def primary_score(text):
    low = normalize(text)

    if "hotel cecil" in low:
        return 100

    if "cecil hotel" in low:
        return 100

    return 0


def secondary_score(text):
    low = normalize(text)

    if "los angeles" in low:
        return 100

    return 0


def role_score(text):
    low = normalize(text)

    hits = [
        term
        for term in ROLE_TERMS
        if term in low
    ]

    if (
        "street scene"
        in low
        or "facade"
        in low
        or "façade"
        in low
        or "exterior"
        in low
    ):
        score = 100

    elif (
        "street" in low
        or "building" in low
        or "front" in low
    ):
        score = 80

    else:
        score = 0

    return score, sorted(
        set(hits)
    )


def request_json(params):
    wait = 5

    for attempt in range(1, 4):
        try:
            r = requests.get(
                COMMONS,
                params=params,
                headers=HEADERS,
                timeout=25
            )

            if r.status_code == 429:
                if attempt == 3:
                    raise RuntimeError(
                        "HTTP 429"
                    )

                retry = r.headers.get(
                    "Retry-After"
                )

                try:
                    retry = int(retry)
                except Exception:
                    retry = wait

                time.sleep(
                    max(
                        5,
                        min(retry, 30)
                    )
                )

                wait = min(
                    wait * 2,
                    30
                )

                continue

            r.raise_for_status()

            return r.json()

        except Exception:
            if attempt == 3:
                raise

            time.sleep(wait)

            wait = min(
                wait * 2,
                20
            )

    return {}


def inspect_commons_title(title):
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop":
            "url|size|mime|mediatype|extmetadata",
        "format": "json",
        "formatversion": 2,
    }

    data = request_json(
        params
    )

    pages = (
        data.get("query", {})
        .get("pages", [])
    )

    if not pages:
        return None

    page = pages[0]

    infos = (
        page.get("imageinfo")
        or []
    )

    if not infos:
        return None

    info = infos[0]

    meta = (
        info.get("extmetadata")
        or {}
    )

    def mv(key):
        value = (
            meta.get(key)
            or {}
        )

        if isinstance(value, dict):
            return (
                value.get("value")
                or ""
            )

        return str(value or "")

    description = re.sub(
        r"<[^>]+>",
        " ",
        mv("ImageDescription")
    )

    return {
        "title":
            page.get("title")
            or title,

        "url":
            info.get("url"),

        "mime":
            info.get("mime"),

        "mediatype":
            info.get("mediatype"),

        "width":
            int(
                info.get("width")
                or 0
            ),

        "height":
            int(
                info.get("height")
                or 0
            ),

        "description":
            description,

        "categories":
            mv("Categories"),

        "license":
            mv("LicenseShortName"),

        "usage_terms":
            mv("UsageTerms"),
    }


def technical_score(
    width,
    height
):
    pixels = (
        width * height
    )

    if pixels >= 6_000_000:
        return 100

    if pixels >= 3_000_000:
        return 95

    if pixels >= 2_000_000:
        return 90

    if pixels >= 1_000_000:
        return 80

    if pixels >= 500_000:
        return 65

    return 45


def license_score(
    license_name,
    usage
):
    text = (
        str(license_name or "")
        + " "
        + str(usage or "")
    ).lower()

    if (
        "public domain" in text
        or "cc0" in text
    ):
        return 100

    if (
        "cc by-sa" in text
        or "cc-by-sa" in text
    ):
        return 92

    if (
        "cc by" in text
        or "cc-by" in text
    ):
        return 90

    return 45


def evaluate_candidate(
    source_item
):
    title = str(
        source_item.get("title")
        or ""
    )

    if not title.lower().startswith(
        "file:"
    ):
        return {
            "title":
                title,

            "decision":
                "REJECT",

            "reason":
                "not_commons_file",
        }

    try:
        meta = inspect_commons_title(
            title
        )

    except Exception as exc:
        return {
            "title":
                title,

            "decision":
                "REJECT",

            "reason":
                "metadata_error:"
                + type(exc).__name__
                + ":"
                + str(exc)[:150],
        }

    if not meta:
        return {
            "title":
                title,

            "decision":
                "REJECT",

            "reason":
                "commons_metadata_missing",
        }

    mime = str(
        meta.get("mime")
        or ""
    ).lower()

    family = (
        "VIDEO"
        if mime.startswith("video/")
        else "IMAGE"
    )

    text = " ".join([
        meta.get("title") or "",
        meta.get("description") or "",
        meta.get("categories") or "",
    ])

    primary = primary_score(
        text
    )

    secondary = secondary_score(
        text
    )

    rscore, rhits = role_score(
        text
    )

    neg = negative_terms(
        text
    )

    tech = technical_score(
        meta["width"],
        meta["height"]
    )

    lic = license_score(
        meta["license"],
        meta["usage_terms"]
    )

    # This module intentionally evaluates
    # IMAGE only as fallback after VI220
    # failed to find a valid VIDEO.
    family_ok = (
        family == "IMAGE"
    )

    final = (
        primary * .35
        + rscore * .30
        + secondary * .10
        + tech * .15
        + lic * .10
    )

    if neg:
        final -= 45

    gates = {
        "fallback_family_image":
            family_ok,

        "primary_entity":
            primary == 100,

        "visual_role":
            rscore >= MIN_ROLE,

        "negative_filter":
            not bool(neg),

        "technical":
            tech >= 65,

        "license":
            lic >= 80,

        "final_score":
            final >= MIN_FINAL,
    }

    passed = all(
        gates.values()
    )

    if passed:
        decision = (
            "SAFE_IMAGE_FALLBACK"
        )
        reason = (
            "video_unavailable_image_truth_pass"
        )

    elif not family_ok:
        decision = "REJECT"
        reason = "not_image_fallback"

    elif primary < 100:
        decision = "REJECT"
        reason = (
            "hotel_cecil_not_confirmed"
        )

    elif neg:
        decision = "REJECT"
        reason = (
            "wrong_visual_content:"
            + ",".join(neg)
        )

    elif rscore < MIN_ROLE:
        decision = "REJECT"
        reason = (
            "facade_role_not_confirmed"
        )

    elif lic < 80:
        decision = "REJECT"
        reason = (
            "license_not_safe_enough"
        )

    else:
        decision = "REJECT"
        reason = (
            "fallback_score_below_gate"
        )

    return {
        "title":
            meta["title"],

        "url":
            meta["url"],

        "family":
            family,

        "primary_entity":
            PRIMARY_ENTITY,

        "primary_score":
            primary,

        "secondary_score":
            secondary,

        "required_role":
            REQUIRED_ROLE,

        "role_score":
            rscore,

        "role_hits":
            rhits,

        "negative_terms":
            neg,

        "width":
            meta["width"],

        "height":
            meta["height"],

        "technical_score":
            tech,

        "license":
            meta["license"],

        "license_score":
            lic,

        "final_score":
            round(
                max(0, final),
                2
            ),

        "gates":
            gates,

        "decision":
            decision,

        "reason":
            reason,
    }


def evaluate():
    vi220 = load_gate(
        VI220
    )

    vi200 = load_gate(
        VI200
    )

    if not vi220:
        raise RuntimeError(
            "vi220_missing"
        )

    # Fallback is allowed only because
    # role-constrained VIDEO search failed.
    if (
        vi220.get("decision")
        != "KEEP_CURRENT"
    ):
        raise RuntimeError(
            "video_candidate_already_available"
        )

    source_scene = None

    for item in (
        vi200.get("results")
        or []
    ):
        if int(
            item.get("scene", -1)
        ) == 2:
            source_scene = item
            break

    if not source_scene:
        raise RuntimeError(
            "vi200_scene_2_missing"
        )

    source_candidates = (
        source_scene.get(
            "top_candidates"
        )
        or []
    )

    # Inspect only Commons image candidates
    # already discovered by entity-first search.
    checks = []

    seen = set()

    for item in source_candidates:
        title = str(
            item.get("title")
            or ""
        )

        if title in seen:
            continue

        seen.add(title)

        check = evaluate_candidate(
            item
        )

        checks.append(
            check
        )

        time.sleep(.6)

    checks.sort(
        key=lambda x:
            x.get(
                "final_score",
                0
            ),
        reverse=True
    )

    approved = [
        x
        for x in checks
        if x.get("decision")
        == "SAFE_IMAGE_FALLBACK"
    ]

    best = (
        approved[0]
        if approved
        else None
    )

    report = {
        "version":
            VERSION,

        "status":
            "VI225_SAFE_FAMILY_FALLBACK_CERTIFIED",

        "short_id":
            vi220.get("short_id"),

        "scene":
            2,

        "preferred_family":
            "VIDEO",

        "fallback_family":
            "IMAGE",

        "primary_entity":
            PRIMARY_ENTITY,

        "required_role":
            REQUIRED_ROLE,

        "video_search_result":
            vi220.get("decision"),

        "checked":
            len(checks),

        "approved":
            len(approved),

        "decision":
            (
                "SAFE_IMAGE_FALLBACK_FOUND"
                if best
                else "KEEP_CURRENT"
            ),

        "best":
            best,

        "checks":
            checks,

        "blockers":
            [],

        "warnings":
            (
                ["video_unavailable_using_shadow_image_fallback"]
                if best
                else []
            ),

        "network_executed":
            bool(checks),

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

        "fallback_mode":
            "SHADOW_ONLY",

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
        " VI225 SAFE MEDIA FAMILY FALLBACK"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "SCENE:",
        r["scene"]
    )

    print(
        "PREFERRED FAMILY:",
        r["preferred_family"]
    )

    print(
        "VIDEO RESULT:",
        r["video_search_result"]
    )

    print(
        "FALLBACK FAMILY:",
        r["fallback_family"]
    )

    print(
        "CHECKED:",
        r["checked"]
    )

    print(
        "APPROVED:",
        r["approved"]
    )

    print(
        "DECISION:",
        r["decision"]
    )

    print(
        "BLOCKERS:",
        r["blockers"]
    )

    print(
        "WARNINGS:",
        r["warnings"]
    )

    best = r.get("best")

    if best:
        print()
        print(
            "WINNER:",
            best["title"]
        )

        print(
            "PRIMARY:",
            best["primary_score"]
        )

        print(
            "ROLE:",
            best["role_score"]
        )

        print(
            "SECONDARY:",
            best["secondary_score"]
        )

        print(
            "RESOLUTION:",
            f'{best["width"]}x{best["height"]}'
        )

        print(
            "TECHNICAL:",
            best["technical_score"]
        )

        print(
            "LICENSE:",
            best["license"]
        )

        print(
            "LICENSE SCORE:",
            best["license_score"]
        )

        print(
            "FINAL SCORE:",
            best["final_score"]
        )

        print(
            "GATES:",
            best["gates"]
        )

    print()
    print(
        "===== CANDIDATE CHECKS ====="
    )

    for item in r["checks"]:
        print(
            "-",
            item.get("decision"),
            "|",
            item.get("title"),
            "| primary=",
            item.get("primary_score"),
            "| role=",
            item.get("role_score"),
            "| tech=",
            item.get("technical_score"),
            "| final=",
            item.get("final_score"),
            "| reason=",
            item.get("reason"),
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
        r["production_media_mutated"]
    )

    print(
        "FFMPEG EXECUTED:",
        r["ffmpeg_executed"]
    )

    print(
        "VIDEO GENERATED:",
        r["video_generated"]
    )
