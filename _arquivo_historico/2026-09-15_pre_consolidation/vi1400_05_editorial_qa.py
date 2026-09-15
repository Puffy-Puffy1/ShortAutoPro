#!/usr/bin/env python3

from vi1400_01_common import (
    TMP,
    load_json,
    norm,
    save_json,
)


ILLUSTRATIVE_MODES = {
    "MEDICAL_ILLUSTRATION",
    "MAINTENANCE_WORKER_ILLUSTRATION",
    "WATER_TANK_ILLUSTRATION",
    "STRICT_ACTION_ILLUSTRATION",
    "STRICT_GENERIC_EVIDENCE_CONTEXT",
}


def run():
    artifacts = load_json(
        TMP
        / "artifacts.json"
    )


    plan = load_json(
        artifacts.get(
            "selection_plan"
        )
        or "",
        {}
    )


    selected = (
        plan.get(
            "selected"
        )
        or {}
    )


    warnings = []

    blockers = []

    rows = []

    groups = {}


    for number in range(
        1,
        13
    ):

        item = selected.get(
            str(
                number
            ),
            {}
        )


        if (
            item.get(
                "decision"
            )
            != "SELECT_SAFE"
        ):

            blockers.append(
                f"scene_{number}_not_selected"
            )

            continue


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


        mode = (
            evaluation.get(
                "mode"
            )
            or ""
        )


        source_class = (
            candidate.get(
                "source_class"
            )
            or "UNKNOWN"
        )


        title = (
            candidate.get(
                "title"
            )
            or ""
        )


        group = (
            candidate.get(
                "source_group"
            )
            or title
        )


        groups[
            group
        ] = (
            groups.get(
                group,
                0
            )
            + 1
        )


        label = (
            evaluation.get(
                "overlay_label"
            )
        )


        illustrative = (
            mode
            in ILLUSTRATIVE_MODES

            or

            source_class
            == "GENERIC"
        )


        if (
            illustrative
            and
            not label
        ):

            warnings.append(
                f"scene_{number}_illustrative_label_missing"
            )


        if (
            "MAINTENANCE_WORKER"
            in mode

            and

            "maintenance"
            not in norm(
                title
            )

            and

            "worker"
            not in norm(
                title
            )
        ):

            warnings.append(
                f"scene_{number}_worker_semantics_weak"
            )


        if (
            "WATER_TANK"
            in mode

            and

            "water"
            not in norm(
                title
            )

            and

            "tank"
            not in norm(
                title
            )

            and

            "tower"
            not in norm(
                title
            )
        ):

            warnings.append(
                f"scene_{number}_water_tank_semantics_weak"
            )


        if (
            "MEDICAL"
            in mode

            and

            not any(
                key
                in norm(
                    title
                )

                for key in [
                    "medical",
                    "bipolar",
                    "health",
                    "disorder",
                    "comorbid",
                ]
            )
        ):

            warnings.append(
                f"scene_{number}_medical_semantics_weak"
            )


        rows.append({
            "scene":
                number,

            "title":
                title,

            "source_class":
                source_class,

            "mode":
                mode,

            "overlay_label":
                label,

            "illustrative":
                illustrative,
        })


    repeated = {
        key:
            value

        for key, value
        in groups.items()

        if value > 2
    }


    if repeated:

        warnings.append(
            "source_repeated_more_than_twice"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "rows":
            rows,

        "warnings":
            warnings,

        "blockers":
            blockers,

        "repeated_groups":
            repeated,
    }


    save_json(
        TMP
        / "editorial_qa.json",
        report
    )


    return report


if __name__ == "__main__":

    report = run()


    print(
        "VI1400 EDITORIAL QA=",
        report[
            "status"
        ]
    )

    print(
        "WARNINGS=",
        report[
            "warnings"
        ]
    )

    print(
        "BLOCKERS=",
        report[
            "blockers"
        ]
    )
