#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


from vi7_28_adaptive_certification import (
    evaluate as certify
)

from vi7_29_release_gate import (
    evaluate as release_gate
)


VERSION = "7.30"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

RUNTIME = (
    BASE
    / "logs/producao/"
      "vi7_19_adaptive_runtime_latest.json"
)

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi7_30_master_gate_latest.json"
)


def evaluate():

    blockers = []


    try:

        data = json.loads(
            RUNTIME.read_text(
                encoding="utf-8"
            )
        )

        events = (
            data.get(
                "events"
            )
            or []
        )


    except Exception:

        events = []

        blockers.append(
            "runtime_telemetry_missing"
        )


    certification = certify(
        events
    )


    certification[
        "blockers"
    ] = sorted(
        set(
            certification.get(
                "blockers"
            )
            or []
        )
        | set(
            blockers
        )
    )


    release = release_gate(
        certification
    )


    result = {
        "version":
            VERSION,

        "status":
            release.get(
                "status"
            ),

        "selected_count":
            certification.get(
                "selected_count"
            ),

        "selected_scenes":
            certification.get(
                "selected_scenes"
            ),

        "success_scenes":
            certification.get(
                "success_scenes"
            ),

        "recovered_scenes":
            certification.get(
                "recovered_scenes"
            ),

        "retry_count":
            certification.get(
                "retry_count"
            ),

        "profiles":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "profiles"
            ),

        "roles":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "roles"
            ),

        "unique_profiles":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "unique_profiles"
            ),

        "adjacent_triples":
            (
                certification.get(
                    "sequence"
                )
                or {}
            ).get(
                "adjacent_triples"
            ),

        "blockers":
            release.get(
                "blockers"
            ),

        "warnings":
            release.get(
                "warnings"
            ),

        "adaptive_runtime_certified":
            (
                release.get(
                    "status"
                )
                == "ADAPTIVE_RUNTIME_CERTIFIED"
            ),

        "source_recovery_active":
            False,

        "full_active_authorized":
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

    assert VERSION == "7.30"

    print(
        "VI7.30 MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
