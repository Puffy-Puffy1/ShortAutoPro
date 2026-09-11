#!/usr/bin/env python3

import re

from pathlib import Path

from vi1500_01_common import (
    save_json,
)


BENCHMARK_PATTERNS = {
    "ELISA_LAM":
        r"\belisa\s+lam\b",

    "HOTEL_CECIL":
        r"\bhotel\s+cecil\b",

    "ELISA_AUTOPSY":
        r"autopsy\s+report\s+of\s+elisa\s+lam",

    "OLD_SHORT_ID":
        r"2026[-_]09[-_]01[_-]1433",
}


def run(
    topic,
    artifacts,
    run_dir,
):
    texts = []


    for path_text in (
        artifacts.get(
            "new_metadata",
            []
        )
    ):
        path = Path(
            path_text
        )

        if not path.exists():
            continue


        try:
            texts.append(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            )

        except Exception:
            pass


    for name in [
        "generator_stdout.txt",
        "generator_stderr.txt",
    ]:
        path = (
            run_dir
            / name
        )

        if path.exists():
            texts.append(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )
            )


    combined = "\n".join(
        texts
    )


    hits = []


    for name, pattern in (
        BENCHMARK_PATTERNS.items()
    ):

        if re.search(
            pattern,
            combined,
            re.I,
        ):
            hits.append(
                name
            )


    # Do not flag an intentionally user-selected
    # benchmark as leakage.
    if re.search(
        r"\belisa\s+lam\b",
        topic,
        re.I,
    ):
        hits = []


    report = {
        "status":
            (
                "PASS"
                if not hits
                else "HOLD"
            ),

        "hits":
            hits,

        "blockers": [
            "semantic_benchmark_leak:"
            + hit

            for hit
            in hits
        ],
    }


    save_json(
        run_dir
        / "semantic_leak_guard.json",
        report
    )


    return report
