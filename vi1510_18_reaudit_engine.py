#!/usr/bin/env python3

from pathlib import Path

from vi1510_01_common import (
    BASE,
    RUNS,
    save_json,
)

from vi1510_02_benchmark_bank import (
    build as build_bank,
)

from vi1510_03_run_resolver import (
    resolve,
)

from vi1510_04_asset_inventory import (
    collect as inventory_run,
)

from vi1510_05_source_metadata import (
    collect as metadata_run,
)

from vi1510_06_narrative_scope import (
    collect as narrative_run,
)

from vi1510_07_lineage_builder import (
    build as lineage_run,
)

from vi1510_08_content_leak_guard import (
    run as leak_run,
)

from vi1510_09_stale_asset_guard import (
    run as stale_run,
)

from vi1510_11_provenance_gate import (
    run as provenance_run,
)

from vi1510_12_metadata_relevance import (
    run as relevance_run,
)

from vi1510_13_asset_technical_audit import (
    run as technical_run,
)

from vi1510_14_visual_qa_bridge import (
    run as visual_run,
)

from vi1510_15_media_quality_bridge import (
    run as media_quality_run,
)

from vi1510_16_score_engine import (
    run as score_run,
)

from vi1510_17_release_gate import (
    run as gate_run,
)


def process(
    run_info,
):
    label = run_info[
        "label"
    ]


    output = (
        RUNS
        /
        label
    )


    output.mkdir(
        parents=True,
        exist_ok=True
    )


    if run_info.get(
        "status"
    ) != "RESOLVED":

        result = {
            "label":
                label,

            "status":
                "MISSING",

            "ready":
                False,

            "score":
                0,

            "blockers": [
                "vi1500_run_missing"
            ],
        }


        save_json(
            output
            / "final.json",
            result
        )


        return result


    old_run = Path(
        run_info[
            "old_run_dir"
        ]
    )


    video = run_info.get(
        "final_video"
    )


    print()
    print(
        "=============================================="
    )

    print(
        " VI1510 REAUDIT",
        label
    )

    print(
        "=============================================="
    )

    print(
        "TOPIC:",
        run_info.get(
            "topic"
        )
    )

    print(
        "DOMAIN:",
        run_info.get(
            "domain"
        )
    )

    print(
        "SHORT_ID:",
        run_info.get(
            "short_id"
        )
    )


    inventory = inventory_run(
        run_info,
        output,
    )


    metadata = metadata_run(
        run_info,
        output,
    )


    narrative = narrative_run(
        run_info,
        output,
    )


    lineage = lineage_run(
        inventory,
        metadata,
        output,
    )


    leak = leak_run(
        run_info,
        inventory,
        metadata,
        narrative,
        output,
    )


    stale = stale_run(
        run_info,
        inventory,
        output,
    )


    provenance = provenance_run(
        run_info,
        lineage,
        metadata,
        output,
    )


    relevance = relevance_run(
        run_info,
        metadata,
        output,
    )


    technical = technical_run(
        inventory,
        output,
    )


    if (
        video
        and
        Path(
            video
        ).exists()
    ):

        visual = visual_run(
            video,
            old_run,
            output,
        )


        media_quality = media_quality_run(
            video,
            old_run,
            output,
        )


    else:

        visual = {
            "status":
                "HOLD",

            "average_strength":
                0,

            "blockers": [
                "final_video_missing"
            ],
        }


        media_quality = {
            "status":
                "HOLD",

            "blockers": [
                "final_video_missing"
            ],
        }


        save_json(
            output
            / "visual_qa.json",
            visual
        )


        save_json(
            output
            / "media_quality.json",
            media_quality
        )


    score = score_run(
        provenance,
        relevance,
        leak,
        stale,
        technical,
        visual,
        media_quality,
        output,
    )


    gate = gate_run(
        score,
        output,
    )


    result = {
        "label":
            label,

        "topic":
            run_info.get(
                "topic"
            ),

        "domain":
            run_info.get(
                "domain"
            ),

        "short_id":
            run_info.get(
                "short_id"
            ),

        "final_video":
            video,

        "status":
            gate[
                "status"
            ],

        "ready":
            gate[
                "ready"
            ],

        "score":
            gate[
                "score"
            ],

        "blockers":
            gate[
                "blockers"
            ],

        "assets":
            provenance.get(
                "asset_count"
            ),

        "unique_assets":
            provenance.get(
                "unique_asset_count"
            ),

        "source_records":
            provenance.get(
                "independent_source_records"
            ),

        "provenance_coverage":
            provenance.get(
                "provenance_coverage"
            ),

        "topic_relevant_records":
            relevance.get(
                "relevant_record_count"
            ),

        "content_leak":
            leak.get(
                "status"
            ),

        "control_plane_references":
            leak.get(
                "control_plane_references"
            ),
    }


    save_json(
        output
        / "final.json",
        result
    )


    print(
        "ASSETS=",
        result[
            "assets"
        ]
    )

    print(
        "UNIQUE_ASSETS=",
        result[
            "unique_assets"
        ]
    )

    print(
        "SOURCE_RECORDS=",
        result[
            "source_records"
        ]
    )

    print(
        "PROVENANCE_COVERAGE=",
        result[
            "provenance_coverage"
        ]
    )

    print(
        "TOPIC_RELEVANT_RECORDS=",
        result[
            "topic_relevant_records"
        ]
    )

    print(
        "CONTENT_LEAK=",
        result[
            "content_leak"
        ]
    )

    print(
        "CONTROL_REFERENCES=",
        result[
            "control_plane_references"
        ]
    )

    print(
        "SCORE=",
        result[
            "score"
        ]
    )

    print(
        "RESULT=",
        result[
            "status"
        ]
    )

    print(
        "BLOCKERS=",
        result[
            "blockers"
        ]
    )


    return result


def main():
    build_bank()

    runs = resolve()

    results = [
        process(
            run_info
        )

        for run_info
        in runs
    ]


    save_json(
        BASE
        / "reaudit_results.json",
        {
            "results":
                results
        }
    )


    print()
    print(
        "VI1510 REAUDIT COMPLETED"
    )

    print(
        "TOPICS=",
        len(
            results
        )
    )


if __name__ == "__main__":

    main()
