#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_77_search_architecture_mapper import (
    evaluate as map_architecture
)

from vi8_78_safe_integration_candidate import (
    evaluate as find_candidates
)

from vi8_75_source_recovery_lock_audit import (
    evaluate as recovery_lock
)

from vi8_79_search_architecture_safety_gate import (
    evaluate as safety_gate
)


VERSION = "8.80"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    architecture = (
        map_architecture()
    )

    candidates = (
        find_candidates(
            architecture
        )
    )

    recovery = (
        recovery_lock()
    )

    safety = (
        safety_gate(
            architecture,
            candidates,
            recovery
        )
    )

    if safety.get(
        "blockers"
    ):
        status = "HOLD"

    elif candidates.get(
        "count",
        0
    ):
        status = (
            "SEARCH_ARCHITECTURE_MAPPED"
        )

    else:
        status = (
            "SEARCH_ARCHITECTURE_PARTIAL"
        )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "architecture":
            architecture,

        "integration_candidates":
            candidates,

        "source_recovery":
            recovery,

        "safety":
            safety,

        "network_executed":
            False,

        "provider_called":
            False,

        "download_executed":
            False,

        "media_mutated":
            False,

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "full_active":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_80_search_architecture_latest.json"
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
    assert VERSION == "8.80"

    print(
        "VI8.80 SEARCH ARCHITECTURE MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
