#!/usr/bin/env python3

from vi1510_01_common import (
    BASE,
    load_json,
    norm,
    save_json,
)


def phrase_hits(
    texts,
    phrases,
):
    hits = set()


    for text in texts:

        normalized = norm(
            text
        )


        for phrase in phrases:

            if (
                phrase

                and

                phrase
                in normalized
            ):
                hits.add(
                    phrase
                )


    return sorted(
        hits
    )


def run(
    run,
    inventory,
    metadata,
    narrative,
    run_dir,
):
    bank = load_json(
        BASE
        / "benchmark_bank.json",
        {}
    )


    hard_hashes = set(
        bank.get(
            "hard_hashes",
            []
        )
    )


    generic_hashes = set(
        bank.get(
            "generic_hashes",
            []
        )
    )


    hard_titles = set(
        bank.get(
            "hard_titles",
            []
        )
    )


    phrases = [
        norm(
            item
        )

        for item in bank.get(
            "specific_phrases",
            []
        )
    ]


    blockers = []

    warnings = []


    narrative_hits = phrase_hits(
        narrative.get(
            "texts",
            []
        ),
        phrases,
    )


    if narrative_hits:

        blockers.extend(
            [
                (
                    "benchmark_narrative_leak:"
                    +
                    value
                )

                for value
                in narrative_hits
            ]
        )


    hard_asset_hits = []

    generic_asset_reuse = []


    for asset in inventory.get(
        "source_assets",
        []
    ):

        digest = asset[
            "sha256"
        ]


        if digest in hard_hashes:

            hard_asset_hits.append(
                asset[
                    "path"
                ]
            )


        elif digest in generic_hashes:

            generic_asset_reuse.append(
                asset[
                    "path"
                ]
            )


    if hard_asset_hits:

        blockers.append(
            "benchmark_specific_asset_reused"
        )


    if generic_asset_reuse:

        warnings.append(
            "generic_asset_reused_from_old_benchmark"
        )


    metadata_hard_hits = []


    for record in metadata.get(
        "records",
        []
    ):

        title = norm(
            record.get(
                "title"
            )
        )


        if (
            title
            in hard_titles

            or

            any(
                phrase
                and
                phrase
                in title

                for phrase
                in phrases
            )
        ):

            metadata_hard_hits.append(
                record.get(
                    "title"
                )
            )


    if metadata_hard_hits:

        blockers.append(
            "benchmark_specific_source_metadata_reused"
        )


    # Control-plane references are NOT content leaks.
    # They are reported separately.
    control_references = []


    control_tokens = [
        str(
            item
        )

        for item in bank.get(
            "control_plane_references",
            []
        )
    ]


    control_text = "\n".join(
        [
            str(
                run.get(
                    "old_run_dir"
                )
                or ""
            ),

            str(
                run.get(
                    "old_artifacts"
                )
                or ""
            ),
        ]
    )


    for token in control_tokens:

        if (
            token

            and

            token
            in control_text
        ):
            control_references.append(
                token
            )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),

        "narrative_hits":
            narrative_hits,

        "hard_asset_hits":
            hard_asset_hits,

        "generic_asset_reuse":
            generic_asset_reuse,

        "metadata_hard_hits":
            metadata_hard_hits,

        "control_plane_references":
            control_references,

        "old_short_id_is_content_evidence":
            False,
    }


    save_json(
        run_dir
        / "content_leak_guard.json",
        report
    )


    return report
