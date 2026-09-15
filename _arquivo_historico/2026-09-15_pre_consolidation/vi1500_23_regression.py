#!/usr/bin/env python3

import tempfile

from pathlib import Path

from vi1500_03_risk_classifier import (
    classify,
)

from vi1500_06_generator_adapter import (
    detect_contract,
)

from vi1500_15_failure_recovery import (
    classify_failure,
)


def main():
    tests = []


    science = classify(
        "O paradoxo de Fermi",
        "SCIENCE_CONCEPT",
    )


    tests.append((
        "SCIENCE_CLASSIFICATION",
        (
            "concept_requires_visual_abstraction"
            in science[
                "reasons"
            ]
        ),
    ))


    event = classify(
        "O desastre do Hindenburg em 1937",
        "HISTORICAL_EVENT",
    )


    tests.append((
        "HISTORICAL_EVENT_RISK",
        event[
            "risk_level"
        ]
        in {
            "MEDIUM",
            "HIGH",
        },
    ))


    transient = classify_failure({
        "stderr_tail":
            "HTTP Error 429 Too many requests",

        "stdout_tail":
            "",
    })


    tests.append((
        "HTTP429_RETRYABLE",
        transient[
            "transient"
        ]
        is True,
    ))


    deterministic = classify_failure({
        "stderr_tail":
            "SyntaxError: invalid syntax",

        "stdout_tail":
            "",
    })


    tests.append((
        "SYNTAX_ERROR_NOT_RETRYABLE",
        deterministic[
            "transient"
        ]
        is False,
    ))


    contract = detect_contract(
        "Regression Topic"
    )


    tests.append((
        "GENERATOR_CONTRACT_SAFE_ENUM",
        contract[
            "contract"
        ]
        in {
            "USER_OVERRIDE",
            "GERAR_SHORT_POSITIONAL",
            "GERAR_SHORT_ENV_TEMA",
            "GERAR_SHORT_ENV_TOPIC",
            "V6_POSITIONAL_TOPIC",
            "UNRESOLVED",
        },
    ))


    failed = []


    print()
    print(
        "=============================================="
    )

    print(
        " VI1500 REGRESSION"
    )

    print(
        "=============================================="
    )


    for name, passed in tests:
        print(
            name,
            "=",
            (
                "PASS"
                if passed
                else "FAIL"
            )
        )


        if not passed:
            failed.append(
                name
            )


    print(
        "FAILED:",
        failed
    )


    if failed:
        raise SystemExit(
            1
        )


    print(
        "VI1500_REGRESSION_CERTIFIED"
    )


if __name__ == "__main__":
    main()
