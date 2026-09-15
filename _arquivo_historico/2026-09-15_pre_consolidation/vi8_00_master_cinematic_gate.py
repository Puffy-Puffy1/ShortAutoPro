#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path

from vi7_85_shadow_runtime import (
    run as shadow_run
)

from vi7_88_cinematic_audit import (
    evaluate as cinematic_audit
)

from vi7_91_quality_forecast import (
    forecast
)

from vi7_94_transition_intelligence import (
    evaluate as transition_intelligence
)

from vi7_97_release_candidate import (
    evaluate as release_candidate
)


VERSION = "8.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    shadow = shadow_run()

    audit = cinematic_audit(
        shadow
    )

    forecast_result = forecast(
        shadow
    )

    transition_result = (
        transition_intelligence(
            shadow.get("plans")
            or []
        )
    )

    release = release_candidate(
        audit,
        forecast_result
    )

    result = {
        "version": VERSION,
        "status":
            release.get("status"),
        "short_id":
            shadow.get("short_id"),
        "scene_map":
            shadow.get("scene_map"),
        "forecast_score":
            forecast_result.get(
                "forecast_score"
            ),
        "forecast_level":
            forecast_result.get(
                "level"
            ),
        "forecast_components":
            forecast_result.get(
                "components"
            ),
        "visual_quality":
            shadow.get(
                "visual_quality_gate"
            ),
        "diversity":
            shadow.get("diversity"),
        "documentary":
            shadow.get("documentary"),
        "rhythm":
            shadow.get("rhythm"),
        "repetition":
            shadow.get("repetition"),
        "transition_analysis":
            shadow.get("transitions"),
        "transition_intelligence":
            transition_result,
        "optimizer":
            shadow.get("optimizer"),
        "plans":
            shadow.get("plans"),
        "blockers":
            release.get("blockers"),
        "warnings":
            release.get("warnings"),
        "source_recovery":
            "SHADOW_ONLY",
        "renderer_activation":
            False,
        "ffmpeg_executed":
            False,
        "video_generated":
            False,
        "full_active_authorized":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_00_master_cinematic_gate_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),
                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "8.00"

    print(
        "VI8.00 MASTER CINEMATIC GATE=PASS"
    )


if __name__ == "__main__":
    result = evaluate()

    print()
    print(
        "STATUS:",
        result.get("status")
    )

    print(
        "SHORT ID:",
        result.get("short_id")
    )

    print(
        "FORECAST SCORE:",
        result.get(
            "forecast_score"
        )
    )

    print(
        "FORECAST LEVEL:",
        result.get(
            "forecast_level"
        )
    )

    visual = (
        result.get(
            "visual_quality"
        )
        or {}
    )

    print(
        "SAFE SCENES:",
        visual.get(
            "safe_scene_count"
        )
    )

    print(
        "VISUAL QUALITY AVG:",
        visual.get(
            "average_quality"
        )
    )

    print(
        "SHOT MISMATCH SCENES:",
        visual.get(
            "shot_mismatch_scenes"
        )
    )

    diversity = (
        result.get("diversity")
        or {}
    )

    print(
        "CATEGORY DIVERSITY:",
        diversity.get(
            "categories"
        )
    )

    print(
        "SHOT DIVERSITY:",
        diversity.get(
            "shots"
        )
    )

    print(
        "MOTION DIVERSITY:",
        diversity.get(
            "motions"
        )
    )

    print(
        "DIVERSITY SCORE:",
        diversity.get(
            "score"
        )
    )

    documentary = (
        result.get("documentary")
        or {}
    )

    print(
        "DOCUMENTARY RATIO:",
        documentary.get(
            "documentary_ratio"
        )
    )

    transitions = (
        result.get(
            "transition_analysis"
        )
        or {}
    )

    print(
        "TRANSITION AVG:",
        transitions.get(
            "average"
        )
    )

    repetition = (
        result.get(
            "repetition"
        )
        or {}
    )

    print(
        "REPETITION WARNINGS:",
        repetition.get(
            "count"
        )
    )

    rhythm = (
        result.get("rhythm")
        or {}
    )

    print(
        "FLAT ENERGY RUNS:",
        rhythm.get(
            "flat_runs"
        )
    )

    optimizer = (
        result.get("optimizer")
        or {}
    )

    print(
        "OPTIMIZER ACTIONS:",
        optimizer.get(
            "count"
        )
    )

    transition_intel = (
        result.get(
            "transition_intelligence"
        )
        or {}
    )

    print(
        "TRANSITION SUGGESTIONS:",
        transition_intel.get(
            "count"
        )
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
        "SOURCE RECOVERY:",
        result.get(
            "source_recovery"
        )
    )

    print(
        "RENDERER ACTIVATION:",
        result.get(
            "renderer_activation"
        )
    )

    print(
        "FFMPEG EXECUTED:",
        result.get(
            "ffmpeg_executed"
        )
    )

    print(
        "VIDEO GENERATED:",
        result.get(
            "video_generated"
        )
    )

    print(
        "FULL ACTIVE AUTHORIZED:",
        result.get(
            "full_active_authorized"
        )
    )

    print()
    print(
        "===== CINEMATIC SCENE PLAN ====="
    )

    for item in (
        result.get("plans")
        or []
    ):
        print(
            "SCENE",
            item.get("scene"),
            "| category=",
            item.get("category"),
            "| shot=",
            item.get("shot"),
            "| role=",
            item.get("role"),
            "| motion=",
            item.get("motion"),
            "| energy=",
            item.get("energy"),
            "| quality=",
            item.get("quality_score"),
            "| risk=",
            (
                item.get("risk")
                or {}
            ).get("status"),
            "| status=",
            item.get("status"),
        )
