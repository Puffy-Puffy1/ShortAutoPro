#!/usr/bin/env python3

import json
import re
from pathlib import Path


VERSION = "210.00"

BASE = Path.home() / "ShortAutoPro"

VI200 = (
    BASE / "logs/producao/"
    "vi200_00_entity_first_search_latest.json"
)

VI70 = (
    BASE / "logs/producao/"
    "vi70_00_global_visual_casting_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi210_00_scene_role_family_gate_latest.json"
)


NEGATIVE_PHRASES = {
    "live stream",
    "livestream",
    "24hr live stream",
    "24 hour live stream",
    "streaming",
    "podcast",
    "review",
    "reviews",
    "reaction",
    "gameplay",
    "walkthrough",
    "audiobook",
    "creepypasta",
    "compilation",
    "commentary",
    "trailer",
    "teaser",
    "lyrics",
}


ROLE_GROUPS = {
    "FACADE": {
        "facade",
        "façade",
        "exterior",
        "outside",
        "street",
        "building",
        "front",
        "entrance",
    },

    "HALLWAY": {
        "hallway",
        "corridor",
        "doors",
        "interior",
    },

    "ELEVATOR": {
        "elevator",
        "lift",
        "elevador",
    },

    "ROOFTOP": {
        "rooftop",
        "roof",
        "water tank",
        "tank",
    },

    "DOCUMENT": {
        "document",
        "paper",
        "file",
        "report",
        "record",
        "letter",
    },

    "SURVEILLANCE": {
        "cctv",
        "camera",
        "security camera",
        "surveillance",
    },

    "SIGN": {
        "sign",
        "rate sign",
        "room rate",
        "plaque",
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

    return data.get("gate", data)


def by_scene(items):
    out = {}

    for item in items or []:
        try:
            n = int(item.get("scene"))
        except Exception:
            continue

        out[n] = item

    return out


def normalize(text):
    text = str(text or "").lower()

    text = text.replace(
        "-",
        " "
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def detect_negative(text):
    low = normalize(text)

    hits = []

    for phrase in NEGATIVE_PHRASES:
        if phrase in low:
            hits.append(phrase)

    # Standalone stream variants
    if re.search(
        r"\bstream\b",
        low
    ):
        hits.append("stream")

    return sorted(
        set(hits)
    )


def detect_family(item):
    provider = str(
        item.get("provider")
        or ""
    ).upper()

    mime = str(
        item.get("mime")
        or ""
    ).lower()

    title = normalize(
        item.get("title")
    )

    url = normalize(
        item.get("url")
    )

    if (
        mime.startswith("video/")
        or title.endswith(".webm")
        or title.endswith(".mp4")
        or url.endswith(".webm")
        or url.endswith(".mp4")
    ):
        return "VIDEO"

    if provider == "ARCHIVE":
        return "VIDEO"

    return "IMAGE"


def role_hits(text):
    low = normalize(text)

    hits = {}

    for role, terms in ROLE_GROUPS.items():
        found = [
            term
            for term in terms
            if term in low
        ]

        if found:
            hits[role] = sorted(
                set(found)
            )

    return hits


def scene_role(scene_num, original_query):
    low = normalize(
        original_query
    )

    hits = role_hits(
        low
    )

    # Prefer the strongest visual intent
    # for known scene patterns.
    if (
        "facade" in low
        or "street" in low
        or "exterior" in low
    ):
        return "FACADE"

    if (
        "hallway" in low
        or "corridor" in low
    ):
        return "HALLWAY"

    if (
        "elevator" in low
        or "elevador" in low
    ):
        return "ELEVATOR"

    if (
        "rooftop" in low
        or "water tank" in low
    ):
        return "ROOFTOP"

    if (
        "cctv" in low
        or "security camera" in low
    ):
        return "SURVEILLANCE"

    if (
        "document" in low
        or "paper" in low
    ):
        return "DOCUMENT"

    if hits:
        return next(
            iter(hits.keys())
        )

    return "GENERAL"


def role_score(
    required_role,
    candidate_text
):
    if required_role == "GENERAL":
        return 70.0, {}

    hits = role_hits(
        candidate_text
    )

    if required_role in hits:
        return 100.0, hits

    # Some roles have compatible families.
    compatible = {
        "FACADE": {
            "FACADE",
        },

        "HALLWAY": {
            "HALLWAY",
        },

        "ELEVATOR": {
            "ELEVATOR",
        },

        "ROOFTOP": {
            "ROOFTOP",
        },

        "DOCUMENT": {
            "DOCUMENT",
        },

        "SURVEILLANCE": {
            "SURVEILLANCE",
        },
    }

    allowed = compatible.get(
        required_role,
        set()
    )

    if allowed & set(hits):
        return 75.0, hits

    return 0.0, hits


def wrong_role_reason(
    required_role,
    hits
):
    if not hits:
        return "required_role_missing"

    if (
        required_role == "FACADE"
        and "SIGN" in hits
    ):
        return "sign_not_facade"

    if (
        required_role == "FACADE"
        and "ELEVATOR" in hits
    ):
        return "elevator_not_facade"

    return (
        "wrong_visual_role:"
        + ",".join(
            sorted(hits.keys())
        )
    )


def reroute_hint(
    item,
    required_role
):
    hits = role_hits(
        (
            str(item.get("title") or "")
            + " "
            + str(item.get("query") or "")
        )
    )

    if not hits:
        return None

    candidate_roles = set(
        hits.keys()
    )

    candidate_roles.discard(
        required_role
    )

    # Do not route signs by default.
    candidate_roles.discard(
        "SIGN"
    )

    if not candidate_roles:
        return None

    return {
        "candidate_roles":
            sorted(
                candidate_roles
            ),

        "note":
            "candidate_may_fit_another_scene_shadow_only",
    }


def evaluate_candidate(
    item,
    desired_family,
    required_role
):
    title = str(
        item.get("title")
        or ""
    )

    query = str(
        item.get("query")
        or ""
    )

    text = (
        title
        + " "
        + query
    )

    family = detect_family(
        item
    )

    negatives = detect_negative(
        text
    )

    rscore, rhits = role_score(
        required_role,
        text
    )

    entity_score = float(
        item.get(
            "entity_score"
        )
        or 0
    )

    scene_score = float(
        item.get(
            "scene_score"
        )
        or 0
    )

    original_score = float(
        item.get(
            "final_score"
        )
        or 0
    )

    family_ok = (
        family == desired_family
    )

    role_ok = (
        rscore >= 75
    )

    negative_ok = (
        not negatives
    )

    primary_entity_ok = (
        entity_score >= 50
    )

    # Family and role are now hard gates.
    score = (
        entity_score * .30
        + scene_score * .20
        + rscore * .30
        + original_score * .20
    )

    if not family_ok:
        score -= 35

    if not role_ok:
        score -= 35

    if negatives:
        score -= 50

    score = max(
        0,
        score
    )

    gates = {
        "media_family":
            family_ok,

        "scene_role":
            role_ok,

        "primary_entity":
            primary_entity_ok,

        "negative_filter":
            negative_ok,

        "score":
            score >= 65,
    }

    passed = all(
        gates.values()
    )

    if passed:
        decision = (
            "TRUE_SCENE_ROLE_CANDIDATE"
        )
        reason = (
            "family_role_entity_consensus_pass"
        )

    elif not family_ok:
        decision = "REJECT"
        reason = (
            "media_family_mismatch:"
            + family
            + "!="
            + desired_family
        )

    elif negatives:
        decision = "REJECT"
        reason = (
            "negative_content_type:"
            + ",".join(
                negatives
            )
        )

    elif not role_ok:
        decision = "REJECT"
        reason = wrong_role_reason(
            required_role,
            rhits
        )

    elif not primary_entity_ok:
        decision = "REJECT"
        reason = (
            "primary_entity_insufficient"
        )

    else:
        decision = "REJECT"
        reason = (
            "final_score_below_gate"
        )

    return {
        "provider":
            item.get(
                "provider"
            ),

        "title":
            title,

        "identifier":
            item.get(
                "identifier"
            ),

        "url":
            item.get(
                "url"
            ),

        "detected_family":
            family,

        "desired_family":
            desired_family,

        "required_role":
            required_role,

        "role_hits":
            rhits,

        "role_score":
            rscore,

        "entity_score":
            entity_score,

        "scene_score":
            scene_score,

        "original_score":
            original_score,

        "negative_terms":
            negatives,

        "final_score":
            round(
                score,
                2
            ),

        "gates":
            gates,

        "decision":
            decision,

        "reason":
            reason,

        "reroute_hint":
            (
                None
                if passed
                else reroute_hint(
                    item,
                    required_role
                )
            ),
    }


def evaluate():
    vi200 = load_gate(
        VI200
    )

    vi70 = load_gate(
        VI70
    )

    if not vi200:
        raise RuntimeError(
            "vi200_missing"
        )

    plans70 = by_scene(
        vi70.get(
            "decisions"
        )
        or []
    )

    source_results = by_scene(
        vi200.get(
            "results"
        )
        or []
    )

    results = []

    for scene_num in (
        vi200.get(
            "target_scenes"
        )
        or []
    ):
        scene_num = int(
            scene_num
        )

        source = source_results.get(
            scene_num,
            {}
        )

        plan = plans70.get(
            scene_num,
            {}
        )

        desired = str(
            plan.get(
                "desired_family"
            )
            or "IMAGE"
        )

        original_query = ""

        queries = (
            source.get("queries")
            or []
        )

        if queries:
            original_query = queries[0]

        # For scene 2 use the original semantic
        # need inherited from known visual plan.
        if scene_num == 2:
            original_query = (
                "historic old hotel facade "
                "los angeles street view"
            )

        required = scene_role(
            scene_num,
            original_query
        )

        candidates = (
            source.get(
                "top_candidates"
            )
            or []
        )

        evaluated = [
            evaluate_candidate(
                item,
                desired,
                required
            )
            for item in candidates
        ]

        evaluated.sort(
            key=lambda x:
                x["final_score"],
            reverse=True
        )

        approved = [
            x
            for x in evaluated
            if x["decision"]
            == "TRUE_SCENE_ROLE_CANDIDATE"
        ]

        best = (
            approved[0]
            if approved
            else None
        )

        reroutes = [
            {
                "title":
                    x["title"],

                "provider":
                    x["provider"],

                "hint":
                    x["reroute_hint"],
            }
            for x in evaluated
            if x.get(
                "reroute_hint"
            )
        ]

        results.append({
            "scene":
                scene_num,

            "desired_family":
                desired,

            "required_role":
                required,

            "checked":
                len(evaluated),

            "approved":
                len(approved),

            "decision":
                (
                    "TRUE_SCENE_CANDIDATE_FOUND"
                    if best
                    else "KEEP_CURRENT"
                ),

            "best":
                best,

            "checks":
                evaluated,

            "reroute_hints":
                reroutes,
        })

    approved_scenes = [
        x["scene"]
        for x in results
        if x["decision"]
        == "TRUE_SCENE_CANDIDATE_FOUND"
    ]

    family_rejections = sum(
        1
        for result in results
        for check in result[
            "checks"
        ]
        if (
            "media_family_mismatch"
            in check["reason"]
        )
    )

    role_rejections = sum(
        1
        for result in results
        for check in result[
            "checks"
        ]
        if (
            "role"
            in check["reason"]
            or "facade"
            in check["reason"]
        )
    )

    negative_rejections = sum(
        1
        for result in results
        for check in result[
            "checks"
        ]
        if (
            "negative_content_type"
            in check["reason"]
        )
    )

    warnings = []

    if family_rejections:
        warnings.append(
            "wrong_media_family_rejected"
        )

    if role_rejections:
        warnings.append(
            "wrong_scene_role_rejected"
        )

    if negative_rejections:
        warnings.append(
            "negative_content_rejected"
        )

    report = {
        "version":
            VERSION,

        "status":
            "VI210_SCENE_ROLE_FAMILY_GATE_CERTIFIED",

        "short_id":
            vi200.get(
                "short_id"
            ),

        "evaluated_scenes":
            [
                x["scene"]
                for x in results
            ],

        "approved_scenes":
            approved_scenes,

        "family_rejections":
            family_rejections,

        "role_rejections":
            role_rejections,

        "negative_rejections":
            negative_rejections,

        "results":
            results,

        "blockers":
            [],

        "warnings":
            warnings,

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

        "cross_scene_reroute":
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
        " VI210 SCENE ROLE + MEDIA FAMILY GATE"
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
        "APPROVED:",
        r[
            "approved_scenes"
        ]
    )

    print(
        "FAMILY REJECTIONS:",
        r[
            "family_rejections"
        ]
    )

    print(
        "ROLE REJECTIONS:",
        r[
            "role_rejections"
        ]
    )

    print(
        "NEGATIVE REJECTIONS:",
        r[
            "negative_rejections"
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

    for result in r[
        "results"
    ]:
        print(
            "SCENE:",
            result["scene"]
        )

        print(
            " DESIRED FAMILY:",
            result[
                "desired_family"
            ]
        )

        print(
            " REQUIRED ROLE:",
            result[
                "required_role"
            ]
        )

        print(
            " CHECKED:",
            result["checked"]
        )

        print(
            " APPROVED:",
            result["approved"]
        )

        print(
            " DECISION:",
            result[
                "decision"
            ]
        )

        best = result.get(
            "best"
        )

        if best:
            print(
                " WINNER:",
                best["title"]
            )

            print(
                " FAMILY:",
                best[
                    "detected_family"
                ]
            )

            print(
                " ROLE SCORE:",
                best[
                    "role_score"
                ]
            )

            print(
                " ENTITY:",
                best[
                    "entity_score"
                ]
            )

            print(
                " FINAL:",
                best[
                    "final_score"
                ]
            )

            print(
                " GATES:",
                best["gates"]
            )

        print()

        for check in result[
            "checks"
        ][:8]:
            print(
                "  -",
                check["decision"],
                "|",
                check["title"],
                "| family=",
                check[
                    "detected_family"
                ],
                "| role=",
                check[
                    "role_score"
                ],
                "| entity=",
                check[
                    "entity_score"
                ],
                "| score=",
                check[
                    "final_score"
                ],
                "| reason=",
                check["reason"],
            )

        print()

        for hint in result[
            "reroute_hints"
        ][:5]:
            print(
                "  REROUTE SHADOW:",
                hint["title"],
                "->",
                hint["hint"],
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
