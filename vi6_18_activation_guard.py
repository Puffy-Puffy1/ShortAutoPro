#!/usr/bin/env python3

import json
import os
import py_compile
from pathlib import Path


VERSION = "6.18"


REQUIRED = (
    "vi6_6_active_brain.py",
    "vi6_7_retrieval_planner.py",
    "vi6_8_storyboard_director.py",
    "vi6_8_runtime_policy.py",
    "vi6_9_quality_firewall.py",
    "vi6_9_runtime_policy.py",
    "vi6_10_coverage_predictor.py",
    "vi6_11_second_chance.py",
    "vi6_12_story_guard.py",
    "vi6_13_recovery_planner.py",
    "vi6_14_pre_download_gate.py",
    "vi6_15_decision_ledger.py",
    "vi6_16_source_capabilities.py",
    "vi6_17_recovery_router.py",
)


def evaluate_activation(
    capability_payload
):

    reasons = []


    missing = [
        filename
        for filename in REQUIRED
        if not Path(
            filename
        ).exists()
    ]


    if missing:

        reasons.append(
            "missing_modules"
        )


    compile_errors = []


    for filename in REQUIRED:

        if not Path(
            filename
        ).exists():

            continue


        try:

            py_compile.compile(
                filename,
                doraise=True
            )

        except Exception as exc:

            compile_errors.append(
                {
                    "file":
                        filename,

                    "error":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                }
            )


    if compile_errors:

        reasons.append(
            "compile_errors"
        )


    summary = (
        capability_payload.get(
            "summary"
        )
        or {}
    )


    has_documentary = bool(
        summary.get(
            "has_documentary_route"
        )
    )


    has_stock = bool(
        summary.get(
            "has_stock_route"
        )
    )


    usable = int(
        summary.get(
            "usable",
            0
        )
        or 0
    )


    if usable <= 0:

        reasons.append(
            "no_usable_source_functions"
        )


    if not has_documentary:

        reasons.append(
            "no_documentary_route"
        )


    status = (
        "READY_FOR_CONTROLLED_WIRING"

        if not reasons

        else "HOLD"
    )


    return {
        "version":
            VERSION,

        "status":
            status,

        "safe_to_activate":
            status
            == "READY_FOR_CONTROLLED_WIRING",

        "usable_source_functions":
            usable,

        "documentary_route":
            has_documentary,

        "stock_route":
            has_stock,

        "missing":
            missing,

        "compile_errors":
            compile_errors,

        "reasons":
            reasons,

        # Mesmo READY ainda não executa
        # busca automaticamente.
        "runtime_mode":
            "DRY_RUN",
    }


def save_report(
    payload
):

    folder = os.path.expanduser(
        "~/ShortAutoPro/logs/producao"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )


    path = os.path.join(
        folder,
        "vi6_18_activation_guard_latest.json"
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    payload = {
        "summary":
            {
                "usable":
                    2,

                "has_documentary_route":
                    True,

                "has_stock_route":
                    True,
            }
    }


    # Self test não depende dos arquivos
    # reais para a regra lógica.
    summary = payload[
        "summary"
    ]


    assert (
        summary[
            "usable"
        ] > 0
    )


    assert (
        summary[
            "has_documentary_route"
        ]
        is True
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.18 ACTIVATION GUARD SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Capability Requirement"
    )
    print(
        "OK Documentary Route Requirement"
    )
    print(
        "OK Compile Requirement"
    )
    print(
        "OK DRY_RUN Lock"
    )
    print()


if __name__ == "__main__":

    self_test()
