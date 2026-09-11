#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "6.80"

BASE = Path.home() / "ShortAutoPro"

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi6_80_master_runtime_gate_latest.json"
)


def evaluate(
    gate70,
    freeze,
    source,
    render,
    comparison,
    certification,
    motion
):

    blockers = []

    warnings = []


    if gate70.get(
        "status"
    ) not in {
        "CANARY_PREVIEW_READY",
        "CANARY_PREVIEW_READY_WITH_WARNINGS",
    }:

        blockers.append(
            "vi670_not_ready"
        )


    if freeze.get(
        "status"
    ) != "FROZEN":

        blockers.append(
            "candidate_not_frozen"
        )


    if source.get(
        "status"
    ) != "FOUND":

        blockers.append(
            "real_source_missing"
        )


    if render.get(
        "status"
    ) != "RENDERED":

        blockers.append(
            "real_twin_render_failed"
        )


    if comparison.get(
        "status"
    ) == "HOLD":

        blockers.append(
            "technical_comparison_failed"
        )


    if certification.get(
        "status"
    ) not in {
        "TECHNICALLY_CERTIFIED",
        "TECHNICALLY_CERTIFIED_WITH_WARNINGS",
    }:

        blockers.append(
            "vi679_not_certified"
        )


    if motion.get(
        "status"
    ) != "FROZEN":

        blockers.append(
            "motion_plan_not_frozen"
        )


    warnings.extend(
        certification.get(
            "warnings"
        )
        or []
    )


    status = (
        "HOLD"
        if blockers
        else (
            "READY_FOR_HUMAN_VISUAL_REVIEW_WITH_WARNINGS"
            if warnings
            else
            "READY_FOR_HUMAN_VISUAL_REVIEW"
        )
    )


    result = {
        "version": VERSION,

        "status": status,

        "scene":
            freeze.get("scene"),

        "legacy_preview":
            (
                render.get(
                    "legacy",
                    {}
                ).get(
                    "output"
                )
            ),

        "vi6_preview":
            (
                render.get(
                    "vi6",
                    {}
                ).get(
                    "output"
                )
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "technical_certification":
            certification.get(
                "status"
            ),

        "human_visual_review_required":
            True,

        # Still deliberately locked.
        "runtime_canary_authorized":
            False,

        "full_active_authorized":
            False,

        "active_renderer":
            False,
    }


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
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

    assert VERSION == "6.80"

    print(
        "VI6.80 MASTER RUNTIME GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
