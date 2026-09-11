#!/usr/bin/env python3

import json
import os

from datetime import datetime
from pathlib import Path

from vi8_91_safe_contract_selector import (
    select as select_contract
)

from vi8_96_probe_query_selector import (
    select as select_query
)

from vi8_97_observational_probe_gate import (
    evaluate as probe_gate
)

from vi8_95_search_probe import (
    execute as execute_probe
)

from vi8_93_search_result_sanitizer import (
    sanitize
)

from vi8_94_search_result_safety import (
    evaluate as result_safety
)

from vi8_98_probe_result_audit import (
    evaluate as probe_audit
)

from vi8_99_vi9_release_candidate import (
    evaluate as release_candidate
)


VERSION = "9.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    contract_selection = (
        select_contract()
    )

    query_selection = (
        select_query()
    )

    safety = probe_gate(
        contract_selection,
        query_selection
    )


    probe_executed = False

    raw_probe = {
        "status":
            "NETWORK_LOCKED"
    }


    if (
        safety.get(
            "status"
        )
        == "CONTROLLED_PROBE_ALLOWED"
    ):

        probe_executed = True

        raw_probe = execute_probe(
            contract_selection[
                "contract"
            ],
            query_selection[
                "query"
            ],
            timeout=12
        )


    elif (
        safety.get(
            "status"
        )
        == "NO_SEARCH_REQUIRED"
    ):

        raw_probe = {
            "status":
                "NO_SEARCH_REQUIRED"
        }


    sanitized = sanitize(
        raw_probe.get(
            "value"
        )
    )


    safe_results = (
        result_safety(
            sanitized.get(
                "results"
            )
            or []
        )
    )


    audit = probe_audit(
        raw_probe.get(
            "status"
        ),
        safety
    )


    release = release_candidate(
        audit,
        safe_results.get(
            "safe_count",
            0
        ),
        probe_executed
    )


    result = {
        "version":
            VERSION,

        "status":
            release.get(
                "status"
            ),

        "contract":
            contract_selection,

        "query":
            query_selection,

        "safety":
            safety,

        "probe_executed":
            probe_executed,

        "probe_status":
            raw_probe.get(
                "status"
            ),

        "probe_reason":
            raw_probe.get(
                "reason"
            ),

        "safe_result_count":
            safe_results.get(
                "safe_count"
            ),

        "rejected_result_count":
            safe_results.get(
                "rejected_count"
            ),

        "safe_results":
            safe_results.get(
                "safe"
            )
            or [],

        "blockers":
            release.get(
                "blockers"
            ),

        "warnings":
            release.get(
                "warnings"
            ),

        "network_executed":
            probe_executed,

        "download_executed":
            False,

        "media_mutated":
            False,

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
        / "logs/producao/"
          "vi9_00_master_search_observation_latest.json"
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

    assert VERSION == "9.00"

    print(
        "VI9.00 MASTER SEARCH OBSERVATION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
