#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path

from vi8_00_master_cinematic_gate import (
    evaluate as cinematic_gate
)

from vi8_20_media_selection_shadow_gate import (
    evaluate as media_gate
)

from vi8_25_cinematic_media_merger import (
    merge
)

from vi8_26_change_plan_builder import (
    build as build_change_plan
)

from vi8_24_global_regression_guard import (
    evaluate as regression_guard
)

from vi8_27_activation_safety_contract import (
    evaluate as safety_contract
)

from vi8_28_integration_readiness import (
    evaluate as readiness_gate
)

from vi8_29_master_certification import (
    evaluate as certification_gate
)


VERSION = "8.30"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    cinematic = cinematic_gate()

    media = media_gate()

    media_plan = (
        media.get("plan")
        or {}
    )

    cinematic_plans = (
        cinematic.get("plans")
        or []
    )

    merged = merge(
        media_plan,
        cinematic_plans
    )

    change_plan = (
        build_change_plan(
            merged
        )
    )

    regression = (
        regression_guard(
            cinematic,
            media_plan,
            change_plan.get(
                "budget"
            )
            or {}
        )
    )

    safety = (
        safety_contract()
    )

    readiness = (
        readiness_gate(
            cinematic,
            media.get(
                "audit"
            )
            or {},
            regression,
            change_plan
        )
    )

    certification = (
        certification_gate(
            readiness,
            safety,
            cinematic.get(
                "forecast_score"
            )
        )
    )

    result = {
        "version":
            VERSION,

        "status":
            certification.get(
                "status"
            ),

        "short_id":
            cinematic.get(
                "short_id"
            ),

        "cinematic_score":
            cinematic.get(
                "forecast_score"
            ),

        "cinematic_level":
            cinematic.get(
                "forecast_level"
            ),

        "cinematic_status":
            cinematic.get(
                "status"
            ),

        "media_status":
            media.get(
                "status"
            ),

        "merged":
            merged,

        "change_plan":
            change_plan,

        "regression_guard":
            regression,

        "readiness":
            readiness,

        "safety":
            safety,

        "blockers":
            certification.get(
                "blockers"
            ),

        "warnings":
            certification.get(
                "warnings"
            ),

        "shadow_certified":
            certification.get(
                "shadow_certified"
            ),

        "automatic_download":
            False,

        "automatic_media_replace":
            False,

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "full_active_authorized":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_30_master_media_cinematic_gate_latest.json"
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
    assert VERSION == "8.30"

    print(
        "VI8.30 MASTER MEDIA CINEMATIC GATE=PASS"
    )


if __name__ == "__main__":
    result = evaluate()

    print()
    print(
        "======================================"
    )
    print(
        " VI8.30 MASTER MEDIA CINEMATIC GATE"
    )
    print(
        "======================================"
    )

    print(
        "STATUS:",
        result.get("status")
    )

    print(
        "SHORT ID:",
        result.get("short_id")
    )

    print(
        "CINEMATIC SCORE:",
        result.get(
            "cinematic_score"
        )
    )

    print(
        "CINEMATIC LEVEL:",
        result.get(
            "cinematic_level"
        )
    )

    print(
        "CINEMATIC STATUS:",
        result.get(
            "cinematic_status"
        )
    )

    print(
        "MEDIA STATUS:",
        result.get(
            "media_status"
        )
    )

    change_plan = (
        result.get(
            "change_plan"
        )
        or {}
    )

    print(
        "PLANNED CHANGES:",
        change_plan.get(
            "planned_change_count"
        )
    )

    print(
        "PLANNED SCENES:",
        (
            change_plan.get(
                "budget"
            )
            or {}
        ).get(
            "selected_scenes"
        )
    )

    regression = (
        result.get(
            "regression_guard"
        )
        or {}
    )

    print(
        "REGRESSION GUARD:",
        regression.get(
            "status"
        )
    )

    print(
        "BLOCKERS:",
        result.get(
            "blockers"
        )
    )

    print(
        "WARNINGS:",
        result.get(
            "warnings"
        )
    )

    print(
        "SHADOW CERTIFIED:",
        result.get(
            "shadow_certified"
        )
    )

    print()
    print(
        "===== PRIORITIZED MEDIA CHANGES ====="
    )

    merged = (
        result.get(
            "merged"
        )
        or {}
    )

    items = sorted(
        merged.get(
            "items"
        )
        or [],
        key=lambda item:
            item.get(
                "priority_score",
                0
            ),
        reverse=True
    )

    for item in items:
        print(
            "SCENE",
            item.get(
                "scene"
            ),
            "| category=",
            item.get(
                "category"
            ),
            "| current=",
            item.get(
                "current_score"
            ),
            "| winner=",
            item.get(
                "winner_score"
            ),
            "| delta=",
            item.get(
                "delta"
            ),
            "| shot=",
            item.get(
                "winner_shot"
            ),
            "| priority=",
            item.get(
                "priority_score"
            ),
            "| confidence=",
            item.get(
                "confidence"
            ),
            item.get(
                "confidence_level"
            ),
            "| recommendation=",
            item.get(
                "recommendation"
            ),
        )

    print()
    print(
        "AUTOMATIC DOWNLOAD:",
        result.get(
            "automatic_download"
        )
    )

    print(
        "AUTOMATIC MEDIA REPLACE:",
        result.get(
            "automatic_media_replace"
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
        "SOURCE RECOVERY:",
        result.get(
            "source_recovery"
        )
    )

    print(
        "FULL ACTIVE AUTHORIZED:",
        result.get(
            "full_active_authorized"
        )
    )
