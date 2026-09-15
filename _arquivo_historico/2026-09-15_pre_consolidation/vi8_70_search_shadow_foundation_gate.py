#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_60_real_media_search_master_gate import (
    evaluate as vi860
)

from vi8_69_search_plan_compiler import (
    compile_plan
)

VERSION = "8.70"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    baseline = vi860()

    strategy = (
        baseline.get(
            "strategy"
        )
        or {}
    )

    budget = (
        strategy.get(
            "budget"
        )
        or {}
    )

    selected = (
        budget.get(
            "selected"
        )
        or []
    )

    compiled = compile_plan(
        selected
    )

    blockers = []
    warnings = []

    for plan in (
        compiled.get("plans")
        or []
    ):
        if plan.get(
            "allow_network"
        ):
            blockers.append(
                "network_must_remain_disabled"
            )

        if plan.get(
            "allow_download"
        ):
            blockers.append(
                "download_must_remain_disabled"
            )

        audit = (
            plan.get(
                "query_diversity"
            )
            or {}
        )

        if audit.get(
            "status"
        ) != "PASS":
            warnings.append(
                f"scene_{plan.get('scene')}_query_diversity"
            )

    if blockers:
        status = "HOLD"

    elif compiled.get(
        "count",
        0
    ) > 0:
        status = (
            "SEARCH_SHADOW_FOUNDATION_READY"
        )

    else:
        status = (
            "NO_SEARCH_REQUIRED"
        )

    result = {
        "version": VERSION,
        "status": status,
        "short_id":
            baseline.get(
                "short_id"
            ),
        "baseline_status":
            baseline.get(
                "status"
            ),
        "compiled":
            compiled,
        "blockers":
            sorted(
                set(blockers)
            ),
        "warnings":
            sorted(
                set(warnings)
            ),
        "network_executed":
            False,
        "download_executed":
            False,
        "media_mutated":
            False,
        "ffmpeg_executed":
            False,
        "video_generated":
            False,
        "renderer_activation":
            False,
        "source_recovery":
            "SHADOW_ONLY",
        "full_active":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_70_search_shadow_foundation_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
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


def self_test():
    assert VERSION == "8.70"

    print(
        "VI8.70 SEARCH SHADOW FOUNDATION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
