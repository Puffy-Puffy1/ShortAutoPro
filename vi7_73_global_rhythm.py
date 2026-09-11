#!/usr/bin/env python3

VERSION = "7.73"

def evaluate(plans):
    energies = [
        x.get(
            "energy",
            1
        )
        for x in plans
    ]

    flat_runs = []

    for i in range(
        len(energies) - 2
    ):
        if (
            energies[i]
            == energies[i+1]
            == energies[i+2]
        ):
            flat_runs.append([
                i + 1,
                i + 2,
                i + 3,
            ])

    return {
        "version": VERSION,
        "energies": energies,
        "flat_runs": flat_runs,
        "status": (
            "PASS_WITH_WARNINGS"
            if flat_runs
            else "PASS"
        ),
    }

def self_test():
    result = evaluate([
        {"energy": 1},
        {"energy": 1},
        {"energy": 1},
    ])

    assert len(
        result["flat_runs"]
    ) == 1

    print(
        "VI7.73 GLOBAL RHYTHM=PASS"
    )

if __name__ == "__main__":
    self_test()
