#!/usr/bin/env python3

import py_compile
from pathlib import Path

from vg4x_common import (
    geo_conflict,
    geo_hits,
)

from vg4x_score import (
    choose_best,
    score_candidate,
)


ROOT = Path.home() / "ShortAutoPro"


def check(name, condition):

    print(
        f"{name}="
        f"{'PASS' if condition else 'FAIL'}"
    )

    if not condition:
        raise RuntimeError(name)


def main():

    modules = [
        "vg4x_common.py",
        "vg4x_score.py",
        "vg4x_acquisition.py",
        "vg4x_commit.py",
        "vg4x_bridge.py",
        "visual_gate_v4x.py",
        "midia.py",
    ]

    for module in modules:

        py_compile.compile(
            str(
                ROOT / module
            ),
            doraise=True,
        )

    print(
        "ALL_COMPILE=PASS"
    )


    check(
        "SP_NY_CONTRADICTION",
        geo_conflict(
            geo_hits(
                "São Paulo Brazil"
            ),
            geo_hits(
                "Empire State Building New York"
            ),
        ),
    )


    scene = {
        "texto":
            "Investigação em apartamento "
            "em São Paulo",

        "must_have":
            [
                "apartamento",
                "São Paulo",
            ],
    }

    wrong = {
        "provider":
            "Pixabay",

        "title":
            "Empire State Building New York",

        "must":
            "2/2",

        "score":
            250,
    }

    correct = {
        "provider":
            "Wikimedia",

        "title":
            "Apartment building Sao Paulo Brazil",

        "must":
            "1/2",

        "score":
            100,
    }


    a = score_candidate(
        wrong,
        scene,
    )

    b = score_candidate(
        correct,
        scene,
    )


    check(
        "WRONG_HARD_MISMATCH",
        a["hard_mismatch"],
    )

    check(
        "CORRECT_NOT_HARD",
        not b["hard_mismatch"],
    )


    chosen, _, _ = choose_best(
        [
            wrong,
            correct,
        ],
        scene,
        reference=wrong,
    )


    check(
        "CORRECT_WINS",
        chosen is correct,
    )


    midia = (
        ROOT
        /
        "midia.py"
    ).read_text(
        encoding="utf-8"
    )

    check(
        "MIDIA_BRIDGE",
        "SHORTAUTOPRO VISUAL GATE V4X BRIDGE"
        in midia,
    )

    check(
        "MIDIA_FINAL_GATE",
        "SHORTAUTOPRO VISUAL GATE V4X FINAL DECISION"
        in midia,
    )


    print(
        "VG4X_CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    main()
