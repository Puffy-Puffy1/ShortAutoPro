#!/usr/bin/env python3

import json

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

PLAN = (
    BASE
    / "temp/vi1250/"
    "vi1250_selection_plan.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1250_06_portfolio_adversarial_latest.json"
)


def write_json(
    path,
    data
):
    path.write_text(
        json.dumps(
            {
                "gate":
                    data
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def main():
    data = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )


    selected = (
        data.get(
            "selected"
        )
        or {}
    )


    tests = []


    for key, item in (
        selected.items()
    ):

        if (
            item.get(
                "decision"
            )
            != "SELECT_SAFE"
        ):

            continue


        scene = int(
            key
        )


        role = str(
            item.get(
                "role"
            )
            or ""
        ).upper()


        candidate = (
            item.get(
                "candidate"
            )
            or {}
        )


        evaluation = (
            item.get(
                "evaluation"
            )
            or {}
        )


        title = str(
            candidate.get(
                "title"
            )
            or ""
        ).lower()


        passed = (
            evaluation.get(
                "passed"
            )
            is True
        )


        tests.append({
            "name":
                f"SCENE_{scene}_SELECTED_GATE",

            "passed":
                passed,
        })


        if (
            ".pdf"
            in title
            and
            role
            != "DOCUMENT"
        ):

            tests.append({
                "name":
                    f"SCENE_{scene}_NO_PDF_VISUAL_MISMATCH",

                "passed":
                    False,
            })


        if (
            role == "HUMAN"
            and
            (
                "medicine box"
                in title
                or
                "navy medicine"
                in title
            )
        ):

            tests.append({
                "name":
                    f"SCENE_{scene}_NO_MEDICINE_AS_HUMAN",

                "passed":
                    False,
            })


        if (
            scene == 11
            and
            "elisa lam elevator video"
            in title
        ):

            tests.append({
                "name":
                    "SCENE_11_NO_ELEVATOR_AS_ROOFTOP",

                "passed":
                    False,
            })


        mode = evaluation.get(
            "mode"
        )


        if (
            mode
            in {
                "FINAL_CTA_CONTEXT",
                "CONTEXT_NOT_DEPICTING_CLAIM",
            }
            and
            not (
                role == "CONTEXT"
                or
                item.get(
                    "cta"
                )
            )
        ):

            tests.append({
                "name":
                    (
                        f"SCENE_{scene}_"
                        "CONTEXT_FALLBACK_SCOPE"
                    ),

                "passed":
                    False,
            })


        tests.append({
            "name":
                f"SCENE_{scene}_QUERY_NOT_EVIDENCE",

            "passed":
                (
                    (
                        evaluation.get(
                            "truth",
                            {}
                        ).get(
                            "query_used_as_evidence"
                        )
                        is False
                    )
                    if mode
                    == "DIRECT"
                    else True
                ),
        })


    failed = [
        item[
            "name"
        ]

        for item in tests

        if not item[
            "passed"
        ]
    ]


    report = {
        "version":
            "1250.00",

        "status":
            (
                "VI1250_PORTFOLIO_ADVERSARIAL_CERTIFIED"
                if not failed
                else "HOLD"
            ),

        "tests":
            tests,

        "failed":
            failed,

        "remote_media_downloaded":
            False,

        "ffmpeg":
            False,

        "video":
            False,
    }


    write_json(
        OUT,
        report
    )


    print()
    print(
        "=============================================="
    )

    print(
        " VI1250 PORTFOLIO ADVERSARIAL"
    )

    print(
        "=============================================="
    )


    print(
        "STATUS:",
        report[
            "status"
        ]
    )

    print(
        "TESTS:",
        len(
            tests
        )
    )

    print(
        "FAILED:",
        failed
    )


    if failed:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
