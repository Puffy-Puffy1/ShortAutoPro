#!/usr/bin/env python3

import json
import re
from pathlib import Path
from collections import Counter

VERSION = "70.00"

BASE = Path.home() / "ShortAutoPro"

VI60 = (
    BASE / "logs/producao/"
    "vi60_00_deep_video_verifier_latest.json"
)

VI30 = (
    BASE / "logs/producao/"
    "vi30_00_cross_media_director_latest.json"
)

VI20 = (
    BASE / "logs/producao/"
    "vi20_00_real_media_ab_latest.json"
)

OUT = (
    BASE / "logs/producao/"
    "vi70_00_global_visual_casting_latest.json"
)

MIN_TOPIC_MATCH = 22.0
MIN_SCENE_MATCH = 22.0
MIN_CONTEXT_SCORE = 45.0
MIN_FINAL_SCORE = 68.0

STOP = {
    "the", "and", "for", "with", "from",
    "this", "that", "into", "about",
    "documentary", "video", "image",
    "photo", "photograph", "cinematic",
    "medium", "wide", "close", "shot",
    "clear", "scene", "visual",
    "person", "people",
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


def tokens(text):
    return {
        x.lower()
        for x in re.findall(
            r"[A-Za-zÀ-ÿ0-9'-]+",
            str(text or "")
        )
        if (
            len(x) >= 3
            and x.lower() not in STOP
        )
    }


def overlap_score(reference, candidate):
    r = tokens(reference)
    c = tokens(candidate)

    if not r:
        return 0.0

    shared = r & c

    if not shared:
        return 0.0

    coverage = (
        len(shared)
        / len(r)
    )

    score = coverage * 100

    if len(shared) == 1:
        score *= .55

    return round(
        min(100, score),
        2
    )


def latest_scene_map(short_id):
    path = (
        BASE
        / "roteiros"
        / f"scene_map_{short_id}.json"
    )

    if not path.exists():
        raise RuntimeError(
            "scene_map_missing"
        )

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )


def topic_text(short_id):
    candidates = [
        BASE / "roteiros"
        / f"topic_verified_{short_id}.json",

        BASE / "roteiros"
        / f"narrative_{short_id}.json",

        BASE / "roteiros"
        / f"post_script_truth_{short_id}.json",
    ]

    pieces = []

    for path in candidates:
        if not path.exists():
            continue

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception:
            continue

        def walk(value):
            if isinstance(value, str):
                pieces.append(value)

            elif isinstance(value, dict):
                for v in value.values():
                    walk(v)

            elif isinstance(value, list):
                for v in value:
                    walk(v)

        walk(data)

    return " ".join(
        pieces
    )[:20000]


def scene_context(scene):
    parts = []

    for key in (
        "segment",
        "query",
        "must_have",
        "avoid",
    ):
        value = scene.get(key)

        if isinstance(value, list):
            parts.extend(
                str(x)
                for x in value
            )

        elif value:
            parts.append(
                str(value)
            )

    return " ".join(parts)


def candidate_text(check):
    parts = [
        check.get("title") or "",
        check.get("identifier") or "",
        check.get("reason") or "",
    ]

    return " ".join(parts)


def context_gate(
    check,
    scene_text,
    topic
):
    text = candidate_text(
        check
    )

    topic_match = overlap_score(
        topic,
        text
    )

    scene_match = overlap_score(
        scene_text,
        text
    )

    context_score = (
        topic_match * .45
        + scene_match * .55
    )

    topic_ok = (
        topic_match
        >= MIN_TOPIC_MATCH
    )

    scene_ok = (
        scene_match
        >= MIN_SCENE_MATCH
    )

    context_ok = (
        context_score
        >= MIN_CONTEXT_SCORE
    )

    passed = (
        topic_ok
        and scene_ok
        and context_ok
    )

    return {
        "topic_match":
            round(
                topic_match,
                2
            ),

        "scene_match":
            round(
                scene_match,
                2
            ),

        "context_score":
            round(
                context_score,
                2
            ),

        "topic_gate":
            topic_ok,

        "scene_gate":
            scene_ok,

        "context_gate":
            context_ok,

        "passed":
            passed,
    }


def verify_video_candidates(
    vi60_result,
    scene_text,
    topic
):
    checks = (
        vi60_result.get(
            "checks"
        )
        or []
    )

    evaluated = []

    winner = None

    for check in checks:
        if (
            check.get(
                "decision"
            )
            != "TRUE_VIDEO_CANDIDATE"
        ):
            evaluated.append({
                "title":
                    check.get(
                        "title"
                    ),

                "identifier":
                    check.get(
                        "identifier"
                    ),

                "original_decision":
                    check.get(
                        "decision"
                    ),

                "final_decision":
                    "REJECT_PREVIOUS_GATE",

                "reason":
                    check.get(
                        "reason"
                    ),
            })

            continue

        context = context_gate(
            check,
            scene_text,
            topic
        )

        base_score = float(
            check.get(
                "final_score"
            )
            or 0
        )

        final_score = (
            base_score * .55
            + context[
                "context_score"
            ] * .45
        )

        if not context[
            "passed"
        ]:
            decision = (
                "REJECT_CONTEXT_MISMATCH"
            )

        elif (
            final_score
            < MIN_FINAL_SCORE
        ):
            decision = (
                "REJECT_FINAL_SCORE"
            )

        else:
            decision = (
                "TRUE_CONTEXTUAL_VIDEO_CANDIDATE"
            )

        item = {
            "title":
                check.get(
                    "title"
                ),

            "identifier":
                check.get(
                    "identifier"
                ),

            "base_score":
                base_score,

            "context":
                context,

            "final_score":
                round(
                    final_score,
                    2
                ),

            "decision":
                decision,

            "best_file":
                check.get(
                    "best_file"
                ),

            "license":
                check.get(
                    "license"
                ),
        }

        evaluated.append(
            item
        )

        if (
            decision
            == "TRUE_CONTEXTUAL_VIDEO_CANDIDATE"
        ):
            if (
                winner is None
                or item[
                    "final_score"
                ]
                > winner[
                    "final_score"
                ]
            ):
                winner = item

    return {
        "winner":
            winner,

        "evaluated":
            evaluated,
    }


def evaluate():
    vi60 = load_gate(
        VI60
    )

    vi30 = load_gate(
        VI30
    )

    vi20 = load_gate(
        VI20
    )

    if not vi30:
        raise RuntimeError(
            "vi30_missing"
        )

    short_id = str(
        vi30.get(
            "short_id"
        )
        or ""
    )

    scene_map = latest_scene_map(
        short_id
    )

    scenes = by_scene(
        scene_map.get(
            "scenes"
        )
        or []
    )

    plans30 = by_scene(
        vi30.get(
            "decisions"
        )
        or []
    )

    vi60_results = by_scene(
        vi60.get(
            "results"
        )
        or []
    )

    vi20_results = by_scene(
        vi20.get(
            "results"
        )
        or []
    )

    topic = topic_text(
        short_id
    )

    decisions = []

    for scene_num in range(
        1,
        13
    ):
        scene = scenes.get(
            scene_num,
            {}
        )

        plan = plans30.get(
            scene_num,
            {}
        )

        stext = scene_context(
            scene
        )

        current_family = (
            plan.get(
                "current_family"
            )
            or "UNKNOWN"
        )

        desired_family = (
            plan.get(
                "desired_family"
            )
            or current_family
        )

        action = (
            "KEEP_CURRENT"
        )

        selected_candidate = None

        reasons = []

        video_verification = None

        if scene_num in vi60_results:
            video_verification = (
                verify_video_candidates(
                    vi60_results[
                        scene_num
                    ],
                    stext,
                    topic
                )
            )

            winner = (
                video_verification[
                    "winner"
                ]
            )

            if winner:
                action = (
                    "CONTEXT_VERIFIED_VIDEO_CANDIDATE"
                )

                selected_candidate = (
                    winner
                )

                reasons.append(
                    "video_context_truth_pass"
                )

            else:
                reasons.append(
                    "video_candidates_context_rejected"
                )

        # Image candidate from VI20 is retained only
        # as a shadow option if its family matches
        # the desired family.
        image_shadow = None

        if scene_num in vi20_results:
            item = vi20_results[
                scene_num
            ]

            if (
                item.get(
                    "decision"
                )
                == "READY_FOR_MANUAL_REPLACEMENT"
            ):
                image_shadow = {
                    "candidate_score":
                        item.get(
                            "candidate_score"
                        ),

                    "gain":
                        item.get(
                            "final_gain"
                        ),

                    "decision":
                        "SHADOW_ONLY",
                }

                if (
                    desired_family
                    in {
                        "IMAGE",
                        "ARCHIVAL_IMAGE"
                    }
                ):
                    reasons.append(
                        "image_shadow_candidate_available"
                    )

        decisions.append({
            "scene":
                scene_num,

            "category":
                plan.get(
                    "category"
                ),

            "current_family":
                current_family,

            "desired_family":
                desired_family,

            "action":
                action,

            "selected_candidate":
                selected_candidate,

            "video_verification":
                video_verification,

            "image_shadow":
                image_shadow,

            "identity":
                plan.get(
                    "identity"
                ),

            "reasons":
                reasons,
        })

    contextual_video = [
        x["scene"]
        for x in decisions
        if x[
            "action"
        ]
        == "CONTEXT_VERIFIED_VIDEO_CANDIDATE"
    ]

    rejected_context = []

    for item in decisions:
        verification = (
            item.get(
                "video_verification"
            )
            or {}
        )

        for candidate in (
            verification.get(
                "evaluated"
            )
            or []
        ):
            if (
                candidate.get(
                    "decision"
                )
                == "REJECT_CONTEXT_MISMATCH"
            ):
                rejected_context.append({
                    "scene":
                        item[
                            "scene"
                        ],

                    "title":
                        candidate.get(
                            "title"
                        ),

                    "identifier":
                        candidate.get(
                            "identifier"
                        ),
                })

    action_counts = Counter(
        x["action"]
        for x in decisions
    )

    family_counts = Counter(
        x["desired_family"]
        for x in decisions
    )

    blockers = []

    warnings = []

    if len(decisions) != 12:
        blockers.append(
            "scene_count_not_12"
        )

    if rejected_context:
        warnings.append(
            "context_false_positives_rejected"
        )

    status = (
        "HOLD"
        if blockers
        else
        "VI70_GLOBAL_VISUAL_CASTING_CERTIFIED"
    )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "short_id":
            short_id,

        "scene_count":
            len(decisions),

        "desired_family_counts":
            dict(
                family_counts
            ),

        "action_counts":
            dict(
                action_counts
            ),

        "context_verified_video_scenes":
            contextual_video,

        "context_rejections":
            rejected_context,

        "decisions":
            decisions,

        "blockers":
            blockers,

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
        " VI70 GLOBAL VISUAL CASTING + CONTEXT TRUTH"
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
        "SCENES:",
        r["scene_count"]
    )

    print(
        "DESIRED FAMILIES:",
        r[
            "desired_family_counts"
        ]
    )

    print(
        "ACTIONS:",
        r[
            "action_counts"
        ]
    )

    print(
        "CONTEXT VERIFIED VIDEOS:",
        r[
            "context_verified_video_scenes"
        ]
    )

    print(
        "CONTEXT REJECTIONS:",
        len(
            r[
                "context_rejections"
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
    print(
        "===== GLOBAL CASTING PLAN ====="
    )

    for x in r[
        "decisions"
    ]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x["category"],
            "| current=",
            x["current_family"],
            "| desired=",
            x["desired_family"],
            "| action=",
            x["action"],
            "| identity=",
            x["identity"],
        )

        candidate = x.get(
            "selected_candidate"
        )

        if candidate:
            print(
                "   CANDIDATE:",
                candidate.get(
                    "title"
                )
            )

            print(
                "   BASE:",
                candidate.get(
                    "base_score"
                ),
                "| TOPIC:",
                candidate[
                    "context"
                ][
                    "topic_match"
                ],
                "| SCENE:",
                candidate[
                    "context"
                ][
                    "scene_match"
                ],
                "| CONTEXT:",
                candidate[
                    "context"
                ][
                    "context_score"
                ],
                "| FINAL:",
                candidate.get(
                    "final_score"
                ),
            )

    print()
    print(
        "===== CONTEXT REJECTIONS ====="
    )

    for x in r[
        "context_rejections"
    ]:
        print(
            "SCENE",
            x["scene"],
            "|",
            x["title"]
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
