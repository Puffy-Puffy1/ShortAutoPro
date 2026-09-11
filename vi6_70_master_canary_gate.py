#!/usr/bin/env python3

import argparse
import json

from datetime import datetime
from pathlib import Path


from vi6_61_motion_diversity_planner import (
    plan as motion_plan
)

from vi6_62_media_streak_intelligence import (
    audit as streak_audit
)

from vi6_64_source_recovery_guard import (
    inspect as source_guard
)

from vi6_65_canary_candidate_selector import (
    select as select_candidate
)

from vi6_66_canary_filter_preview import (
    preview as filter_preview
)

from vi6_67_scene_rollback_contract import (
    build as rollback_contract
)

from vi6_68_performance_intelligence import (
    analyze as performance_analyze
)

from vi6_69_storage_telemetry_guard import (
    audit as storage_audit
)


VERSION = "6.70"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


SESSION = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_shadow_session_latest.json"
)


MASTER60 = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_master_gate_latest.json"
)


OUTPUT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_70_master_canary_gate_latest.json"
)


PLAN_OUTPUT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_70_canary_plan_latest.json"
)


def _load(path, key):

    try:

        return json.loads(
            Path(path).read_text(
                encoding="utf-8"
            )
        ).get(key)

    except Exception:

        return None


def evaluate():

    session = _load(
        SESSION,
        "session"
    )


    master60 = _load(
        MASTER60,
        "gate"
    )


    blockers = []
    warnings = []


    if session is None:

        blockers.append(
            "vi660_session_missing"
        )

        events = []


    else:

        events = (
            session.get("events")
            or []
        )


        if session.get(
            "unique_scenes"
        ) != 12:

            blockers.append(
                "requires_12_scenes"
            )


        if session.get(
            "identity_holds",
            0
        ) != 0:

            blockers.append(
                "identity_hold"
            )


        if session.get(
            "native_video_holds",
            0
        ) != 0:

            blockers.append(
                "native_video_hold"
            )


    if master60 is None:

        blockers.append(
            "vi660_master_missing"
        )


    elif master60.get(
        "status"
    ) not in {
        "CERTIFIED",
        "CERTIFIED_WITH_WARNINGS",
    }:

        blockers.append(
            "vi660_not_certified"
        )


    motion = motion_plan(
        events
    )


    streak = streak_audit(
        events
    )


    source = source_guard()


    candidate = select_candidate(
        events
    )


    winner = candidate.get(
        "winner"
    )


    preview = filter_preview(
        winner
    )


    rollback = rollback_contract(
        winner.get("scene")
        if winner
        else None
    )


    performance = performance_analyze(
        events
    )


    storage = storage_audit()


    if (
        candidate.get("status")
        != "SELECTED"
    ):

        blockers.append(
            "canary_candidate_missing"
        )


    if (
        preview.get("status")
        != "PREVIEW_READY"
    ):

        blockers.append(
            "canary_filter_preview_hold"
        )


    if (
        source.get("status")
        == "HOLD"
    ):

        blockers.append(
            "source_guard_hold"
        )


    elif (
        source.get("status")
        == "PASS_WITH_WARNINGS"
    ):

        warnings.append(
            "source_recovery_still_shadow_only"
        )


    if (
        streak.get("status")
        == "PASS_WITH_WARNINGS"
    ):

        warnings.append(
            "long_media_streak_requires_motion_diversity"
        )


    warnings.extend(
        performance.get(
            "warnings"
        )
        or []
    )


    warnings.extend(
        storage.get(
            "warnings"
        )
        or []
    )


    blockers = sorted(
        set(blockers)
    )


    warnings = sorted(
        set(warnings)
    )


    status = (
        "HOLD"
        if blockers
        else (
            "CANARY_PREVIEW_READY_WITH_WARNINGS"
            if warnings
            else "CANARY_PREVIEW_READY"
        )
    )


    plan = {
        "version": VERSION,
        "status": status,

        "candidate": winner,

        "filter_preview": preview,

        "rollback_contract": rollback,

        "motion_diversity": motion,

        "media_streak": streak,

        "performance": performance,

        "storage": storage,

        "source_guard": source,

        "blockers": blockers,

        "warnings": warnings,

        # This release only prepares the canary.
        "canary_filter_applied": False,

        "canary_render_executed": False,

        "active_canary_authorized": False,

        "active_renderer": False,
    }


    return plan


def save(result):

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    payload = {
        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "gate": result,
    }


    OUTPUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    PLAN_OUTPUT.write_text(
        json.dumps(
            {
                "generated_at":
                    payload[
                        "generated_at"
                    ],

                "plan": {
                    "status":
                        result[
                            "status"
                        ],

                    "candidate":
                        result[
                            "candidate"
                        ],

                    "filter_preview":
                        result[
                            "filter_preview"
                        ],

                    "rollback_contract":
                        result[
                            "rollback_contract"
                        ],

                    "active_canary_authorized":
                        False,
                }
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    assert VERSION == "6.70"

    print(
        "VI6.70 MASTER CANARY GATE SELF TEST=PASS"
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--real",
        action="store_true"
    )

    args = parser.parse_args()


    self_test()


    if not args.real:
        return


    result = evaluate()

    save(result)


    print()
    print(
        "======================================================"
    )
    print(
        " VI6.70 MEGA CANARY MASTER GATE"
    )
    print(
        "======================================================"
    )


    print(
        "STATUS:",
        result.get("status")
    )


    candidate = (
        result.get("candidate")
        or {}
    )


    print(
        "CANARY CANDIDATE SCENE:",
        candidate.get("scene")
    )


    print(
        "CANDIDATE SCORE:",
        candidate.get("score")
    )


    print(
        "CANDIDATE DURATION:",
        candidate.get(
            "duration_seconds"
        )
    )


    print(
        "CANDIDATE ROLE:",
        candidate.get("role")
    )


    preview = (
        result.get("filter_preview")
        or {}
    )


    print(
        "FILTER PREVIEW:",
        preview.get("status")
    )


    print(
        "FILTER DIFFERENT FROM LEGACY:",
        preview.get(
            "different_from_legacy"
        )
    )


    motion = (
        result.get(
            "motion_diversity"
        )
        or {}
    )


    print(
        "MOTION TRIPLE REPEATS:",
        motion.get(
            "triple_repeats"
        )
    )


    performance = (
        result.get("performance")
        or {}
    )


    print(
        "AVERAGE SCENE INTERVAL:",
        performance.get(
            "average_interval_seconds"
        )
    )


    print(
        "SLOWEST:",
        performance.get("slowest")
    )


    print(
        "BLOCKERS:",
        result.get("blockers")
    )


    print(
        "WARNINGS:",
        result.get("warnings")
    )


    print(
        "CANARY FILTER APPLIED:",
        result.get(
            "canary_filter_applied"
        )
    )


    print(
        "CANARY RENDER EXECUTED:",
        result.get(
            "canary_render_executed"
        )
    )


    print(
        "ACTIVE CANARY AUTHORIZED:",
        result.get(
            "active_canary_authorized"
        )
    )


    print(
        "ACTIVE RENDERER:",
        result.get(
            "active_renderer"
        )
    )


if __name__ == "__main__":
    main()
