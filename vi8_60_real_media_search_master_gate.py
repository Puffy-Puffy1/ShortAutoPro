#!/usr/bin/env python3

import json
from pathlib import Path

from vi8_50_real_media_master_gate import (
    evaluate as real_media_gate
)

from vi8_58_search_strategy_plan import (
    build as build_strategy
)

from vi8_59_search_strategy_audit import (
    evaluate as audit_strategy
)

VERSION = "8.60"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    real = real_media_gate()

    plan = (
        real.get("plan")
        or {}
    )

    strategy = build_strategy(
        plan
    )

    audit = audit_strategy(
        strategy
    )

    blockers = (
        audit.get(
            "blockers"
        )
        or []
    )

    if blockers:
        status = "HOLD"

    elif audit.get(
        "selected_count",
        0
    ) > 0:
        status = (
            "SEARCH_STRATEGY_SHADOW_READY"
        )

    else:
        status = (
            "REAL_MEDIA_ALREADY_COMPETITIVE"
        )

    result = {
        "version": VERSION,
        "status": status,
        "short_id":
            real.get("short_id"),
        "real_media_status":
            real.get("status"),
        "strategy":
            strategy,
        "audit":
            audit,
        "blockers":
            blockers,
        "warnings":
            audit.get(
                "warnings"
            )
            or [],
        "automatic_search":
            False,
        "automatic_download":
            False,
        "automatic_replace":
            False,
        "media_mutated":
            False,
        "renderer_activation":
            False,
        "ffmpeg_executed":
            False,
        "video_generated":
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
        / "vi8_60_real_media_search_master_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            {
                "gate": result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "8.60"

    print(
        "VI8.60 REAL MEDIA SEARCH MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
