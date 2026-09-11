#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "60.00"

BASE = Path.home() / "ShortAutoPro"

VI50 = (
    BASE / "logs/producao/"
    "vi50_00_multi_provider_video_latest.json"
)

VI30 = (
    BASE / "logs/producao/"
    "vi30_00_cross_media_director_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi60_00_deep_video_verifier_latest.json"
)

HEADERS = {
    "User-Agent":
        "ShortAutoPro/60.00 "
        "(deep metadata verification)"
}

MAX_SCENES = 3
MAX_CANDIDATES_PER_SCENE = 10

MIN_VISUAL_INTENT = 60
MIN_FINAL_SCORE = 68
MIN_FILE_SCORE = 60


NEGATIVE_TERMS = {
    "review",
    "reviews",
    "reaction",
    "reactions",
    "podcast",
    "gameplay",
    "walkthrough",
    "audiobook",
    "creepypasta",
    "compilation",
    "commentary",
    "stream",
    "livestream",
    "trailer",
    "teaser",
    "music video",
    "lyrics",
    "interview",
    "episode",
}


VISUAL_LOCATION_TERMS = {
    "street",
    "building",
    "hotel",
    "house",
    "room",
    "hallway",
    "corridor",
    "city",
    "town",
    "architecture",
    "interior",
    "exterior",
    "elevator",
    "door",
    "road",
    "landscape",
    "location",
}


VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".ogv",
    ".mpeg",
    ".mpg",
    ".mov",
    ".m4v",
}


BAD_FILE_HINTS = {
    "thumb",
    "thumbnail",
    "spectrogram",
    "waveform",
    "metadata",
    "torrent",
    "sqlite",
    "xml",
    "json",
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
    result = {}

    for item in items or []:
        try:
            scene = int(
                item.get("scene")
            )
        except Exception:
            continue

        result[scene] = item

    return result


def text_tokens(text):
    return set(
        re.findall(
            r"[a-z0-9'-]+",
            str(text or "").lower()
        )
    )


def contains_negative(text):
    low = str(
        text or ""
    ).lower()

    found = []

    for term in NEGATIVE_TERMS:
        if term in low:
            found.append(term)

    return sorted(
        set(found)
    )


def archive_metadata(identifier):
    url = (
        "https://archive.org/metadata/"
        + str(identifier)
    )

    r = requests.get(
        url,
        headers=HEADERS,
        timeout=25
    )

    r.raise_for_status()

    return r.json()


def file_extension(name):
    return Path(
        str(name or "")
    ).suffix.lower()


def file_is_video(item):
    name = str(
        item.get("name")
        or ""
    )

    ext = file_extension(
        name
    )

    fmt = str(
        item.get("format")
        or ""
    ).lower()

    return (
        ext in VIDEO_EXTENSIONS
        or "mpeg4" in fmt
        or "h.264" in fmt
        or "webm" in fmt
        or "ogg video" in fmt
    )


def bad_file(item):
    name = str(
        item.get("name")
        or ""
    ).lower()

    return any(
        hint in name
        for hint in BAD_FILE_HINTS
    )


def parse_int(value):
    try:
        return int(
            float(value)
        )
    except Exception:
        return 0


def parse_float(value):
    try:
        return float(value)
    except Exception:
        return 0.0


def video_file_score(item):
    name = str(
        item.get("name")
        or ""
    )

    size = parse_int(
        item.get("size")
    )

    width = parse_int(
        item.get("width")
    )

    height = parse_int(
        item.get("height")
    )

    length = parse_float(
        item.get("length")
    )

    score = 40.0

    if size >= 50_000_000:
        score += 20

    elif size >= 10_000_000:
        score += 15

    elif size >= 2_000_000:
        score += 8

    if width >= 1920:
        score += 20

    elif width >= 1280:
        score += 15

    elif width >= 720:
        score += 8

    if height >= 720:
        score += 10

    elif height >= 480:
        score += 5

    if length >= 5:
        score += 10

    if bad_file(
        item
    ):
        score -= 40

    return {
        "name":
            name,

        "size":
            size,

        "width":
            width,

        "height":
            height,

        "length":
            length,

        "format":
            item.get(
                "format"
            ),

        "score":
            round(
                max(
                    0,
                    min(
                        100,
                        score
                    )
                ),
                2
            ),
    }


def visual_intent_score(
    candidate,
    metadata,
    category
):
    meta = (
        metadata.get(
            "metadata"
        )
        or {}
    )

    title = str(
        meta.get(
            "title"
        )
        or candidate.get(
            "title"
        )
        or ""
    )

    description = str(
        meta.get(
            "description"
        )
        or candidate.get(
            "description"
        )
        or ""
    )

    subject = meta.get(
        "subject"
    )

    if isinstance(
        subject,
        list
    ):
        subject = " ".join(
            str(x)
            for x in subject
        )

    text = (
        title
        + " "
        + description
        + " "
        + str(
            subject or ""
        )
    )

    negatives = contains_negative(
        text
    )

    score = 65.0

    if negatives:
        score -= min(
            60,
            len(negatives) * 25
        )

    tokens = text_tokens(
        text
    )

    if category == "LOCATION":
        matches = (
            tokens
            & VISUAL_LOCATION_TERMS
        )

        score += min(
            25,
            len(matches) * 5
        )

    creator = str(
        meta.get(
            "creator"
        )
        or ""
    ).lower()

    if any(
        x in creator
        for x in (
            "archive",
            "library",
            "government",
            "museum",
        )
    ):
        score += 8

    return {
        "score":
            round(
                max(
                    0,
                    min(
                        100,
                        score
                    )
                ),
                2
            ),

        "negative_terms":
            negatives,
    }


def license_gate(
    candidate,
    metadata
):
    meta = (
        metadata.get(
            "metadata"
        )
        or {}
    )

    license_text = str(
        meta.get(
            "licenseurl"
        )
        or candidate.get(
            "license"
        )
        or ""
    ).lower()

    if (
        "publicdomain" in license_text
        or "public domain" in license_text
        or "zero/1.0" in license_text
        or "cc0" in license_text
    ):
        return {
            "status": "PASS",
            "score": 100,
            "license":
                license_text,
        }

    if (
        "creativecommons" in license_text
        and (
            "/by/" in license_text
            or "/by-sa/" in license_text
        )
    ):
        return {
            "status": "PASS",
            "score": 90,
            "license":
                license_text,
        }

    return {
        "status": "CAUTION",
        "score": 45,
        "license":
            license_text,
    }


def inspect_candidate(
    candidate,
    category
):
    identifier = str(
        candidate.get(
            "identifier"
        )
        or ""
    )

    if not identifier:
        return {
            "status":
                "REJECT",

            "reason":
                "identifier_missing",
        }

    try:
        metadata = archive_metadata(
            identifier
        )

    except Exception as exc:
        return {
            "status":
                "REJECT",

            "reason":
                "metadata_error",

            "error":
                type(exc).__name__
                + ": "
                + str(exc)[:220],
        }

    intent = visual_intent_score(
        candidate,
        metadata,
        category
    )

    license_result = license_gate(
        candidate,
        metadata
    )

    files = (
        metadata.get(
            "files"
        )
        or []
    )

    video_files = []

    for item in files:
        if not file_is_video(
            item
        ):
            continue

        scored = video_file_score(
            item
        )

        video_files.append(
            scored
        )

    video_files.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )

    usable_files = [
        x
        for x in video_files
        if x["score"]
        >= MIN_FILE_SCORE
    ]

    best_file = (
        usable_files[0]
        if usable_files
        else None
    )

    text_score = float(
        candidate.get(
            "semantic"
        )
        or 0
    )

    provider_score = float(
        candidate.get(
            "provider_trust"
        )
        or 0
    )

    file_score = (
        best_file[
            "score"
        ]
        if best_file
        else 0
    )

    final_score = (
        text_score * .25
        + intent["score"] * .30
        + file_score * .25
        + license_result[
            "score"
        ] * .10
        + provider_score * .10
    )

    gates = {
        "visual_intent":
            intent["score"]
            >= MIN_VISUAL_INTENT,

        "real_video_file":
            best_file
            is not None,

        "file_quality":
            file_score
            >= MIN_FILE_SCORE,

        "license":
            license_result[
                "status"
            ] == "PASS",

        "negative_filter":
            not bool(
                intent[
                    "negative_terms"
                ]
            ),

        "final_score":
            final_score
            >= MIN_FINAL_SCORE,
    }

    passed = all(
        gates.values()
    )

    if passed:
        decision = (
            "TRUE_VIDEO_CANDIDATE"
        )

        reason = (
            "deep_consensus_pass"
        )

    elif intent[
        "negative_terms"
    ]:
        decision = "REJECT"

        reason = (
            "negative_content_type:"
            + ",".join(
                intent[
                    "negative_terms"
                ]
            )
        )

    elif not best_file:
        decision = "REJECT"

        reason = (
            "no_usable_video_file"
        )

    else:
        decision = "REJECT"

        failed = [
            k
            for k, ok
            in gates.items()
            if not ok
        ]

        reason = (
            "failed:"
            + ",".join(
                failed
            )
        )

    return {
        "identifier":
            identifier,

        "title":
            candidate.get(
                "title"
            ),

        "status":
            "PASS",

        "decision":
            decision,

        "reason":
            reason,

        "text_semantic":
            text_score,

        "visual_intent":
            intent,

        "license":
            license_result,

        "video_file_count":
            len(
                video_files
            ),

        "usable_file_count":
            len(
                usable_files
            ),

        "best_file":
            best_file,

        "final_score":
            round(
                final_score,
                2
            ),

        "gates":
            gates,
    }


def verify_scene(
    discovery,
    category
):
    candidates = (
        discovery.get(
            "top_candidates"
        )
        or []
    )

    candidates = candidates[
        :MAX_CANDIDATES_PER_SCENE
    ]

    checks = []

    winner = None

    for candidate in candidates:
        if (
            candidate.get(
                "provider"
            )
            != "INTERNET_ARCHIVE"
        ):
            continue

        result = inspect_candidate(
            candidate,
            category
        )

        checks.append(
            result
        )

        if (
            result.get(
                "decision"
            )
            == "TRUE_VIDEO_CANDIDATE"
        ):
            winner = result
            break

        time.sleep(.4)

    if winner:
        decision = (
            "TRUE_VIDEO_CANDIDATE_FOUND"
        )

    else:
        decision = (
            "KEEP_CURRENT_VIDEO"
        )

    return {
        "scene":
            discovery.get(
                "scene"
            ),

        "decision":
            decision,

        "winner":
            winner,

        "checked_count":
            len(
                checks
            ),

        "checks":
            checks,
    }


def evaluate():
    vi50 = load_gate(
        VI50
    )

    vi30 = load_gate(
        VI30
    )

    if not vi50:
        raise RuntimeError(
            "vi50_missing"
        )

    decisions30 = by_scene(
        vi30.get(
            "decisions"
        )
        or []
    )

    discoveries = [
        x
        for x in (
            vi50.get(
                "discoveries"
            )
            or []
        )
        if x.get(
            "decision"
        )
        == "BETTER_VIDEO_CANDIDATE_FOUND"
    ]

    discoveries = discoveries[
        :MAX_SCENES
    ]

    verified = []

    for discovery in discoveries:
        scene = int(
            discovery[
                "scene"
            ]
        )

        category = str(
            decisions30.get(
                scene,
                {}
            ).get(
                "category"
            )
            or ""
        ).upper()

        verified.append(
            verify_scene(
                discovery,
                category
            )
        )

    winners = [
        x["scene"]
        for x in verified
        if x[
            "decision"
        ]
        == "TRUE_VIDEO_CANDIDATE_FOUND"
    ]

    rejected_false_positive = []

    for scene_result in verified:
        for check in (
            scene_result.get(
                "checks"
            )
            or []
        ):
            if (
                "negative_content_type"
                in str(
                    check.get(
                        "reason"
                    )
                )
            ):
                rejected_false_positive.append(
                    check.get(
                        "identifier"
                    )
                )

    blockers = []

    warnings = []

    if rejected_false_positive:
        warnings.append(
            "false_positive_candidates_rejected"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI60_DEEP_VIDEO_VERIFICATION_CERTIFIED"
    )

    report = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            vi50.get(
                "short_id"
            ),

        "verified_scenes":
            [
                x["scene"]
                for x in verified
            ],

        "true_video_candidate_scenes":
            winners,

        "false_positive_rejections":
            rejected_false_positive,

        "results":
            verified,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            bool(
                discoveries
            ),

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
        " VI60 DEEP VIDEO VERIFICATION"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "VERIFIED SCENES:",
        r[
            "verified_scenes"
        ]
    )

    print(
        "TRUE VIDEO CANDIDATES:",
        r[
            "true_video_candidate_scenes"
        ]
    )

    print(
        "FALSE POSITIVES REJECTED:",
        len(
            r[
                "false_positive_rejections"
            ]
        )
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

    for result in r["results"]:
        print(
            "SCENE:",
            result["scene"]
        )

        print(
            " DECISION:",
            result["decision"]
        )

        print(
            " CHECKED:",
            result["checked_count"]
        )

        winner = result.get(
            "winner"
        )

        if winner:
            print(
                " WINNER:",
                winner["title"]
            )

            print(
                " IDENTIFIER:",
                winner["identifier"]
            )

            print(
                " FINAL SCORE:",
                winner["final_score"]
            )

            print(
                " VISUAL INTENT:",
                winner[
                    "visual_intent"
                ][
                    "score"
                ]
            )

            print(
                " BEST FILE:",
                winner[
                    "best_file"
                ]
            )

            print(
                " GATES:",
                winner["gates"]
            )

        print()

        for check in result[
            "checks"
        ][:5]:
            print(
                "  -",
                check.get(
                    "decision"
                ),
                "|",
                check.get(
                    "title"
                ),
                "| score=",
                check.get(
                    "final_score"
                ),
                "| intent=",
                (
                    check.get(
                        "visual_intent"
                    )
                    or {}
                ).get(
                    "score"
                ),
                "| reason=",
                check.get(
                    "reason"
                ),
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
