#!/usr/bin/env python3

import json
import re
import time
from pathlib import Path

import requests


VERSION = "320.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI300 = (
    LOG /
    "vi300_00_targeted_global_search_latest.json"
)

OUT = (
    LOG /
    "vi320_00_deep_context_truth_latest.json"
)

COMMONS = "https://commons.wikimedia.org/w/api.php"
ARCHIVE_META = "https://archive.org/metadata/"

HEADERS = {
    "User-Agent":
        "ShortAutoPro/320.00 "
        "(deep context truth metadata verification)"
}

VIDEO_EXT = {
    ".mp4",
    ".webm",
    ".ogv",
    ".mpeg",
    ".mpg",
    ".mov",
    ".m4v",
}

NEGATIVE_CONTENT = {
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

DOCUMENT_TERMS = {
    "official document",
    "document",
    "police report",
    "report",
    "official record",
    "record",
    "death certificate",
    "certificate",
    "autopsy",
    "coroner",
    "case report",
    "court record",
    "newspaper",
    "scanned document",
}

ARCHIVAL_TERMS = {
    "archive",
    "archival",
    "historical",
    "historic",
    "record",
    "document",
    "report",
    "newspaper",
    "scan",
    "scanned",
}

ELEVATOR_TERMS = {
    "elevator",
    "elevator video",
    "elevator footage",
    "lift",
    "elevador",
}


def load_gate(path):
    if not path.exists():
        raise RuntimeError(
            f"missing:{path.name}"
        )

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
    text = str(value or "")

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"^\s*File\s*:\s*",
        "",
        text,
        flags=re.I
    )

    text = text.replace(
        "_",
        " "
    )

    text = text.replace(
        "-",
        " "
    )

    text = text.lower()

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def flatten(value):
    if value is None:
        return ""

    if isinstance(
        value,
        list
    ):
        return " ".join(
            flatten(x)
            for x in value
        )

    if isinstance(
        value,
        dict
    ):
        return " ".join(
            flatten(x)
            for x in value.values()
        )

    return str(value)


def request_json(
    url,
    params=None
):
    wait = 5

    for attempt in range(1, 4):
        try:
            r = requests.get(
                url,
                params=params,
                headers=HEADERS,
                timeout=30
            )

            if r.status_code == 429:
                if attempt == 3:
                    return {
                        "_status":
                            "RATE_LIMITED"
                    }

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
                    max(
                        5,
                        min(
                            retry,
                            30
                        )
                    )
                )

                wait = min(
                    wait * 2,
                    30
                )

                continue

            r.raise_for_status()

            data = r.json()

            data["_status"] = "OK"

            return data

        except Exception as exc:
            if attempt == 3:
                return {
                    "_status":
                        "ERROR",

                    "_error":
                        type(exc).__name__
                        + ":"
                        + str(exc)[:180],
                }

            time.sleep(wait)

            wait = min(
                wait * 2,
                20
            )

    return {
        "_status":
            "ERROR"
    }


def license_score(text):
    low = normalize(text)

    if (
        "public domain"
        in low
        or "publicdomain"
        in low
        or "cc0"
        in low
        or "zero/1.0"
        in low
    ):
        return 100

    if (
        "cc by-sa"
        in low
        or "/by-sa/"
        in low
    ):
        return 92

    if (
        "cc by"
        in low
        or "/by/"
        in low
    ):
        return 90

    if "creativecommons" in low:
        return 82

    return 45


def negative_terms(text):
    low = normalize(text)

    return sorted({
        x
        for x in NEGATIVE_CONTENT
        if x in low
    })


def phrase_hits(
    text,
    terms
):
    low = normalize(text)

    return sorted({
        x
        for x in terms
        if x in low
    })


def has_wrong_geo(text):
    low = normalize(text)

    return sorted({
        x
        for x in WRONG_GEO
        if x in low
    })


def commons_metadata(title):
    params = {
        "action":
            "query",

        "titles":
            title,

        "prop":
            "imageinfo",

        "iiprop":
            "url|size|mime|mediatype|extmetadata",

        "format":
            "json",

        "formatversion":
            2,
    }

    data = request_json(
        COMMONS,
        params
    )

    if data.get(
        "_status"
    ) != "OK":
        return {
            "ok":
                False,

            "error":
                data.get(
                    "_status"
                ),
        }

    pages = (
        data.get(
            "query",
            {}
        ).get(
            "pages",
            []
        )
    )

    if not pages:
        return {
            "ok":
                False,

            "error":
                "page_missing",
        }

    page = pages[0]

    info_list = (
        page.get(
            "imageinfo"
        )
        or []
    )

    if not info_list:
        return {
            "ok":
                False,

            "error":
                "imageinfo_missing",
        }

    info = info_list[0]

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
            return flatten(
                value.get(
                    "value"
                )
            )

        return flatten(
            value
        )

    title_real = str(
        page.get(
            "title"
        )
        or title
    )

    description = mv(
        "ImageDescription"
    )

    categories = mv(
        "Categories"
    )

    credit = mv(
        "Credit"
    )

    artist = mv(
        "Artist"
    )

    object_name = mv(
        "ObjectName"
    )

    # IMPORTANT:
    # search query is deliberately absent.
    evidence = " ".join([
        title_real,
        description,
        categories,
        credit,
        artist,
        object_name,
    ])

    mime = normalize(
        info.get("mime")
    )

    mediatype = normalize(
        info.get(
            "mediatype"
        )
    )

    family = (
        "VIDEO"
        if (
            mime.startswith(
                "video/"
            )
            or mediatype
            == "video"
        )
        else "IMAGE"
    )

    try:
        width = int(
            info.get(
                "width"
            )
            or 0
        )
    except Exception:
        width = 0

    try:
        height = int(
            info.get(
                "height"
            )
            or 0
        )
    except Exception:
        height = 0

    try:
        byte_size = int(
            info.get(
                "size"
            )
            or 0
        )
    except Exception:
        byte_size = 0

    license_name = mv(
        "LicenseShortName"
    )

    usage_terms = mv(
        "UsageTerms"
    )

    return {
        "ok":
            True,

        "provider":
            "WIKIMEDIA_COMMONS",

        "title":
            title_real,

        "evidence":
            evidence,

        "family":
            family,

        "mime":
            mime,

        "width":
            width,

        "height":
            height,

        "bytes":
            byte_size,

        "url":
            info.get("url"),

        "license":
            license_name,

        "license_text":
            (
                license_name
                + " "
                + usage_terms
            ),
    }


def archive_video_files(data):
    out = []

    for item in (
        data.get(
            "files"
        )
        or []
    ):
        name = str(
            item.get("name")
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
            ext in VIDEO_EXT
            or "mpeg4" in fmt
            or "webm" in fmt
            or "h.264" in fmt
        ):
            continue

        try:
            size = int(
                float(
                    item.get(
                        "size"
                    )
                    or 0
                )
            )
        except Exception:
            size = 0

        try:
            width = int(
                float(
                    item.get(
                        "width"
                    )
                    or 0
                )
            )
        except Exception:
            width = 0

        try:
            height = int(
                float(
                    item.get(
                        "height"
                    )
                    or 0
                )
            )
        except Exception:
            height = 0

        try:
            length = float(
                item.get(
                    "length"
                )
                or 0
            )
        except Exception:
            length = 0

        out.append({
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
        })

    out.sort(
        key=lambda x: (
            x["width"]
            * x["height"],
            x["size"],
        ),
        reverse=True
    )

    return out


def archive_metadata(identifier):
    data = request_json(
        ARCHIVE_META
        + str(identifier)
    )

    if data.get(
        "_status"
    ) != "OK":
        return {
            "ok":
                False,

            "error":
                data.get(
                    "_status"
                ),
        }

    meta = (
        data.get(
            "metadata"
        )
        or {}
    )

    evidence = " ".join([
        flatten(
            meta.get("title")
        ),
        flatten(
            meta.get(
                "description"
            )
        ),
        flatten(
            meta.get(
                "subject"
            )
        ),
        flatten(
            meta.get(
                "collection"
            )
        ),
        flatten(
            meta.get(
                "creator"
            )
        ),
    ])

    files = archive_video_files(
        data
    )

    license_text = flatten(
        meta.get(
            "licenseurl"
        )
    )

    return {
        "ok":
            True,

        "provider":
            "INTERNET_ARCHIVE",

        "title":
            flatten(
                meta.get(
                    "title"
                )
            )
            or str(identifier),

        "identifier":
            str(identifier),

        "evidence":
            evidence,

        "family":
            (
                "VIDEO"
                if files
                else "UNKNOWN"
            ),

        "video_files":
            files,

        "best_file":
            (
                files[0]
                if files
                else None
            ),

        "license":
            license_text,

        "license_text":
            license_text,
    }


def contextual_entity_truth(
    evidence,
    anchors
):
    low = normalize(
        evidence
    )

    primary = normalize(
        anchors.get(
            "primary"
        )
    )

    known = [
        normalize(x)
        for x in (
            anchors.get(
                "known_entities"
            )
            or []
        )
    ]

    hotel_hit = (
        "hotel cecil" in low
        or "cecil hotel" in low
    )

    los_angeles_hit = (
        "los angeles" in low
        or "hotel cecil la" in low
    )

    elisa_known = (
        "elisa lam"
        in known
    )

    elisa_hit = (
        elisa_known
        and "elisa lam"
        in low
    )

    wrong_geo = has_wrong_geo(
        evidence
    )

    # Same-name hotels elsewhere must never pass.
    location_truth = (
        hotel_hit
        and los_angeles_hit
        and not wrong_geo
    )

    # Direct case identity is stronger than
    # generic same-name hotel metadata.
    direct_case_truth = (
        elisa_hit
        and not wrong_geo
    )

    entity_truth = (
        location_truth
        or direct_case_truth
    )

    return {
        "primary_expected":
            primary,

        "hotel_cecil_hit":
            hotel_hit,

        "los_angeles_hit":
            los_angeles_hit,

        "elisa_lam_hit":
            elisa_hit,

        "wrong_geo":
            wrong_geo,

        "location_truth":
            location_truth,

        "direct_case_truth":
            direct_case_truth,

        "entity_truth":
            entity_truth,
    }


def evaluate_candidate(
    scene,
    scene_result,
    candidate,
    anchors
):
    provider = str(
        candidate.get(
            "provider"
        )
        or ""
    )

    if provider == "WIKIMEDIA_COMMONS":
        meta = commons_metadata(
            candidate.get(
                "title"
            )
        )

    elif provider == "INTERNET_ARCHIVE":
        meta = archive_metadata(
            candidate.get(
                "identifier"
            )
        )

    else:
        return {
            "scene":
                scene,

            "title":
                candidate.get(
                    "title"
                ),

            "provider":
                provider,

            "decision":
                "REJECT_DEEP_TRUTH",

            "reason":
                "unsupported_provider",
        }

    if not meta.get(
        "ok"
    ):
        return {
            "scene":
                scene,

            "title":
                candidate.get(
                    "title"
                ),

            "provider":
                provider,

            "decision":
                "REJECT_DEEP_TRUTH",

            "reason":
                "metadata_unavailable",

            "metadata_error":
                meta.get(
                    "error"
                ),
        }

    evidence = meta[
        "evidence"
    ]

    truth = contextual_entity_truth(
        evidence,
        anchors
    )

    negatives = negative_terms(
        evidence
    )

    role = str(
        scene_result.get(
            "role"
        )
        or ""
    ).upper()

    desired = str(
        scene_result.get(
            "desired_family"
        )
        or ""
    ).upper()

    if role == "ELEVATOR":
        role_hits = phrase_hits(
            evidence,
            ELEVATOR_TERMS
        )

        role_truth = bool(
            role_hits
        )

        archival_truth = True

    elif role == "DOCUMENT":
        role_hits = phrase_hits(
            evidence,
            DOCUMENT_TERMS
        )

        role_truth = bool(
            role_hits
        )

        archival_hits = phrase_hits(
            evidence,
            ARCHIVAL_TERMS
        )

        archival_truth = bool(
            archival_hits
        )

    else:
        role_hits = []

        role_truth = False

        archival_hits = []

        archival_truth = True

    family = meta.get(
        "family"
    )

    if desired == "VIDEO":
        family_truth = (
            family == "VIDEO"
        )

    elif desired == "ARCHIVAL_IMAGE":
        family_truth = (
            family == "IMAGE"
        )

    else:
        family_truth = (
            family == desired
        )

    if family == "VIDEO":
        if provider == "INTERNET_ARCHIVE":
            technical_truth = (
                meta.get(
                    "best_file"
                )
                is not None
            )
        else:
            technical_truth = (
                int(
                    meta.get(
                        "width"
                    )
                    or 0
                ) > 0
                and int(
                    meta.get(
                        "height"
                    )
                    or 0
                ) > 0
            )

    elif family == "IMAGE":
        technical_truth = (
            int(
                meta.get(
                    "width"
                )
                or 0
            )
            * int(
                meta.get(
                    "height"
                )
                or 0
            )
            >= 200_000
        )

    else:
        technical_truth = False

    lic_score = license_score(
        meta.get(
            "license_text"
        )
    )

    gates = {
        "context_entity":
            truth[
                "entity_truth"
            ],

        "wrong_geo_absent":
            not bool(
                truth[
                    "wrong_geo"
                ]
            ),

        "scene_role":
            role_truth,

        "family":
            family_truth,

        "archival_truth":
            archival_truth,

        "negative_content_absent":
            not bool(
                negatives
            ),

        "license":
            lic_score >= 80,

        "technical_metadata":
            technical_truth,
    }

    passed = all(
        gates.values()
    )

    score = 0

    score += (
        35
        if truth[
            "entity_truth"
        ]
        else 0
    )

    score += (
        25
        if role_truth
        else 0
    )

    score += (
        10
        if family_truth
        else 0
    )

    score += (
        10
        if archival_truth
        else 0
    )

    score += (
        10
        if lic_score >= 80
        else 0
    )

    score += (
        10
        if technical_truth
        else 0
    )

    if truth[
        "direct_case_truth"
    ]:
        score += 5

    if truth[
        "wrong_geo"
    ]:
        score -= 100

    if negatives:
        score -= 60

    return {
        "scene":
            scene,

        "title":
            meta.get(
                "title"
            ),

        "provider":
            provider,

        "family":
            family,

        "role":
            role,

        "desired_family":
            desired,

        "context_truth":
            truth,

        "role_hits":
            role_hits,

        "archival_hits":
            (
                archival_hits
                if role
                == "DOCUMENT"
                else []
            ),

        "negative_terms":
            negatives,

        "license":
            meta.get(
                "license"
            ),

        "license_score":
            lic_score,

        "mime":
            meta.get(
                "mime"
            ),

        "width":
            meta.get(
                "width"
            ),

        "height":
            meta.get(
                "height"
            ),

        "bytes":
            meta.get(
                "bytes"
            ),

        "best_file":
            meta.get(
                "best_file"
            ),

        "gates":
            gates,

        "deep_score":
            max(
                0,
                score
            ),

        "decision":
            (
                "DEEP_TRUE_CANDIDATE"
                if passed
                else
                "REJECT_DEEP_TRUTH"
            ),

        "evidence_excludes_search_query":
            True,
    }


def evaluate():
    vi300 = load_gate(
        VI300
    )

    anchors = (
        vi300.get(
            "anchors"
        )
        or {}
    )

    results300 = (
        vi300.get(
            "results"
        )
        or []
    )

    deep_results = []

    invalidated_scenes = []

    ready_scenes = []

    false_positive_titles = []

    scene_decisions = []

    for scene_result in results300:
        scene = int(
            scene_result.get(
                "scene"
            )
        )

        candidates = (
            scene_result.get(
                "top_candidates"
            )
            or []
        )

        approved300 = [
            x
            for x in candidates
            if x.get(
                "decision"
            )
            == "TRUE_TARGETED_CANDIDATE"
        ]

        # Only VI300 winners/approved candidates
        # receive costly deep metadata verification.
        checks = []

        for candidate in approved300:
            check = evaluate_candidate(
                scene,
                scene_result,
                candidate,
                anchors
            )

            checks.append(
                check
            )

            deep_results.append(
                check
            )

            if (
                check[
                    "decision"
                ]
                == "REJECT_DEEP_TRUTH"
            ):
                false_positive_titles.append(
                    check.get(
                        "title"
                    )
                )

            time.sleep(.4)

        passed = [
            x
            for x in checks
            if x[
                "decision"
            ]
            == "DEEP_TRUE_CANDIDATE"
        ]

        passed.sort(
            key=lambda x:
                x.get(
                    "deep_score",
                    0
                ),
            reverse=True
        )

        best = (
            passed[0]
            if passed
            else None
        )

        was_approved = (
            scene_result.get(
                "decision"
            )
            == "TRUE_TARGETED_CANDIDATE_FOUND"
        )

        if best:
            decision = (
                "READY_FOR_CONTROLLED_AB"
            )

            ready_scenes.append(
                scene
            )

        else:
            decision = (
                "KEEP_CURRENT"
            )

            if was_approved:
                invalidated_scenes.append(
                    scene
                )

        scene_decisions.append({
            "scene":
                scene,

            "vi300_decision":
                scene_result.get(
                    "decision"
                ),

            "deep_checked":
                len(checks),

            "deep_approved":
                len(passed),

            "best":
                best,

            "decision":
                decision,
        })

    # Preserve identity quarantine from VI300.
    identity_quarantined = (
        vi300.get(
            "identity_quarantined_scenes"
        )
        or []
    )

    corrections = {
        "same_name_hotel_alias":
            "REQUIRES_LOS_ANGELES_OR_DIRECT_ELISA_LAM_CASE_EVIDENCE",

        "alexandria_egypt_collision":
            "HARD_REJECT",

        "document_role_generic_file_token":
            "REMOVED",

        "document_role":
            "REQUIRES_STRONG_DOCUMENT_OR_RECORD_EVIDENCE",

        "archival_image":
            "REQUIRES_ARCHIVAL_OR_DOCUMENT_EVIDENCE",

        "candidate_search_query_as_evidence":
            "FORBIDDEN",

        "face_without_explicit_identity":
            "IDENTITY_QUARANTINE_PRESERVED",

        "automatic_replace":
            False,
    }

    warnings = []

    if invalidated_scenes:
        warnings.append(
            "vi300_false_positive_approvals_invalidated"
        )

    if identity_quarantined:
        warnings.append(
            "identity_quarantine_active"
        )

    blockers = []

    report = {
        "version":
            VERSION,

        "status":
            "VI320_DEEP_CONTEXT_TRUTH_CERTIFIED",

        "short_id":
            vi300.get(
                "short_id"
            ),

        "anchors":
            anchors,

        "corrections":
            corrections,

        "vi300_approved_scenes":
            vi300.get(
                "approved_scenes"
            )
            or [],

        "deep_ready_scenes":
            ready_scenes,

        "invalidated_vi300_scenes":
            invalidated_scenes,

        "identity_quarantined_scenes":
            identity_quarantined,

        "false_positive_titles":
            [
                x
                for x in false_positive_titles
                if x
            ],

        "scene_decisions":
            scene_decisions,

        "deep_results":
            deep_results,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            bool(deep_results),

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
        " VI320 DEEP CONTEXT TRUTH HARDENING"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "VI300 APPROVED:",
        r[
            "vi300_approved_scenes"
        ]
    )

    print(
        "DEEP READY:",
        r[
            "deep_ready_scenes"
        ]
    )

    print(
        "INVALIDATED:",
        r[
            "invalidated_vi300_scenes"
        ]
    )

    print(
        "IDENTITY QUARANTINED:",
        r[
            "identity_quarantined_scenes"
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
    print(
        "===== DEEP CANDIDATE TRUTH ====="
    )

    for x in r[
        "deep_results"
    ]:
        print()
        print(
            "SCENE:",
            x["scene"]
        )

        print(
            "TITLE:",
            x["title"]
        )

        print(
            "PROVIDER:",
            x["provider"]
        )

        print(
            "FAMILY:",
            x.get(
                "family"
            )
        )

        print(
            "ROLE:",
            x.get(
                "role"
            )
        )

        truth = (
            x.get(
                "context_truth"
            )
            or {}
        )

        print(
            "HOTEL CECIL:",
            truth.get(
                "hotel_cecil_hit"
            )
        )

        print(
            "LOS ANGELES:",
            truth.get(
                "los_angeles_hit"
            )
        )

        print(
            "ELISA LAM:",
            truth.get(
                "elisa_lam_hit"
            )
        )

        print(
            "WRONG GEO:",
            truth.get(
                "wrong_geo"
            )
        )

        print(
            "DIRECT CASE:",
            truth.get(
                "direct_case_truth"
            )
        )

        print(
            "ROLE HITS:",
            x.get(
                "role_hits"
            )
        )

        if x.get(
            "archival_hits"
        ):
            print(
                "ARCHIVAL HITS:",
                x[
                    "archival_hits"
                ]
            )

        print(
            "LICENSE:",
            x.get(
                "license"
            )
        )

        print(
            "SCORE:",
            x.get(
                "deep_score"
            )
        )

        print(
            "GATES:",
            x.get(
                "gates"
            )
        )

        print(
            "DECISION:",
            x[
                "decision"
            ]
        )

        if x.get(
            "best_file"
        ):
            print(
                "BEST FILE:",
                x[
                    "best_file"
                ]
            )

    print()
    print(
        "===== CONSOLIDATED SCENE DECISIONS ====="
    )

    for x in r[
        "scene_decisions"
    ]:
        print(
            "SCENE",
            x["scene"],
            "| VI300=",
            x[
                "vi300_decision"
            ],
            "| checked=",
            x[
                "deep_checked"
            ],
            "| approved=",
            x[
                "deep_approved"
            ],
            "| FINAL=",
            x["decision"],
        )

        if x.get(
            "best"
        ):
            print(
                "   WINNER:",
                x[
                    "best"
                ][
                    "title"
                ]
            )

    print()
    print(
        "NETWORK EXECUTED:",
        r[
            "network_executed"
        ]
    )

    print(
        "DOWNLOAD EXECUTED:",
        r[
            "download_executed"
        ]
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
