#!/usr/bin/env python3

VERSION = "7.88"

def evaluate(result):
    blockers = []
    warnings = []

    gate = (
        result.get(
            "visual_quality_gate"
        )
        or {}
    )

    if gate.get("status") == "HOLD":
        blockers.extend(
            gate.get("blockers")
            or []
        )

    repetition = (
        result.get("repetition")
        or {}
    )

    if repetition.get(
        "count",
        0
    ):
        warnings.append(
            "visual_repetition_detected"
        )

    optimizer = (
        result.get("optimizer")
        or {}
    )

    if optimizer.get(
        "count",
        0
    ):
        warnings.append(
            "sequence_improvements_available"
        )

    rhythm = (
        result.get("rhythm")
        or {}
    )

    if rhythm.get(
        "flat_runs"
    ):
        warnings.append(
            "flat_energy_runs_detected"
        )

    return {
        "version": VERSION,
        "status": (
            "HOLD"
            if blockers
            else (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            )
        ),
        "blockers":
            sorted(
                set(blockers)
            ),
        "warnings":
            sorted(
                set(warnings)
            ),
    }

def self_test():
    result = evaluate({
        "visual_quality_gate": {
            "status": "PASS",
            "blockers": [],
        },
        "repetition": {
            "count": 0
        },
        "optimizer": {
            "count": 0
        },
        "rhythm": {
            "flat_runs": []
        },
    })

    assert result["status"] == "PASS"

    print(
        "VI7.88 CINEMATIC AUDIT=PASS"
    )

if __name__ == "__main__":
    self_test()
