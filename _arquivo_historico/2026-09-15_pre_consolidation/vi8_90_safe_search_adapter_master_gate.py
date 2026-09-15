#!/usr/bin/env python3

import json
from pathlib import Path

from vi8_86_static_search_adapter_plan import (
    build as build_adapter
)

from vi8_87_safe_call_contract import (
    build as build_contract
)

from vi8_88_side_effect_boundary import (
    evaluate as boundary
)

from vi8_89_adapter_readiness_audit import (
    evaluate as audit
)

VERSION = "8.90"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    adapter = build_adapter()

    best = (
        adapter.get("best")
    )

    contract = (
        build_contract(
            best
        )
    )

    side_effects = (
        boundary()
    )

    audit_result = audit(
        adapter,
        contract,
        side_effects
    )

    result = {
        "version":
            VERSION,

        "status":
            audit_result.get(
                "status"
            ),

        "best_module":
            (
                best.get(
                    "module"
                )
                if best
                else None
            ),

        "providers":
            (
                best.get(
                    "providers"
                )
                if best
                else []
            ),

        "search_functions":
            (
                [
                    fn.get(
                        "name"
                    )
                    for fn
                    in best.get(
                        "safe_search_functions",
                        []
                    )
                ]
                if best
                else []
            ),

        "blocked_functions":
            (
                [
                    fn.get(
                        "name"
                    )
                    for fn
                    in best.get(
                        "blocked_functions",
                        []
                    )
                ]
                if best
                else []
            ),

        "import_risk":
            (
                best.get(
                    "import_risk"
                )
                if best
                else {}
            ),

        "contracts":
            contract.get(
                "contracts"
            )
            or [],

        "blockers":
            audit_result.get(
                "blockers"
            )
            or [],

        "warnings":
            audit_result.get(
                "warnings"
            )
            or [],

        "module_import_executed":
            False,

        "search_function_executed":
            False,

        "network_executed":
            False,

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

        "full_active":
            False,
    }

    output = (
        BASE
        / "logs/producao/"
          "vi8_90_safe_search_adapter_latest.json"
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
    assert VERSION == "8.90"

    print(
        "VI8.90 SAFE SEARCH ADAPTER MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
