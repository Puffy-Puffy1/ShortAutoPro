#!/usr/bin/env python3

from pathlib import Path

from vi1510_01_common import (
    BASE,
    ROOT,
    load_json,
    norm,
    policy,
    save_json,
    sha256_file,
)


def build():
    config = policy()

    classes = set(
        config.get(
            "benchmark_specific_classes",
            []
        )
    )

    phrases = [
        norm(
            item
        )

        for item in config.get(
            "benchmark_specific_phrases",
            []
        )
    ]


    selection = load_json(
        ROOT
        / "temp"
        / "vi1260_1"
        / "selection_plan.json",
        {}
    )


    manifest = load_json(
        ROOT
        / "temp"
        / "vi1270_downloads"
        / "download_manifest.json",
        {}
    )


    selected = (
        selection.get(
            "selected"
        )
        or {}
    )


    assets = (
        manifest.get(
            "source_assets"
        )
        or {}
    )


    hard_groups = set()

    generic_groups = set()

    hard_titles = set()

    generic_titles = set()


    for item in selected.values():

        candidate = (
            item.get(
                "candidate"
            )
            or {}
        )


        title = str(
            candidate.get(
                "title"
            )
            or ""
        )


        group = str(
            candidate.get(
                "source_group"
            )
            or ""
        )


        source_class = str(
            candidate.get(
                "source_class"
            )
            or ""
        )


        specific_phrase = any(
            phrase
            and
            phrase
            in norm(
                title
            )

            for phrase
            in phrases
        )


        if (
            source_class
            in classes

            or

            specific_phrase
        ):

            if group:
                hard_groups.add(
                    group
                )

            if title:
                hard_titles.add(
                    norm(
                        title
                    )
                )

        else:

            if group:
                generic_groups.add(
                    group
                )

            if title:
                generic_titles.add(
                    norm(
                        title
                    )
                )


    hard_hashes = set()

    generic_hashes = set()


    for group, asset in assets.items():

        path = Path(
            str(
                asset.get(
                    "path"
                )
                or ""
            )
        )


        if not path.exists():
            continue


        try:
            digest = sha256_file(
                path
            )

        except Exception:
            continue


        title = norm(
            asset.get(
                "title"
            )
        )


        if (
            group
            in hard_groups

            or

            title
            in hard_titles
        ):
            hard_hashes.add(
                digest
            )

        else:
            generic_hashes.add(
                digest
            )


    bank = {
        "hard_groups":
            sorted(
                hard_groups
            ),

        "generic_groups":
            sorted(
                generic_groups
            ),

        "hard_titles":
            sorted(
                hard_titles
            ),

        "generic_titles":
            sorted(
                generic_titles
            ),

        "hard_hashes":
            sorted(
                hard_hashes
            ),

        "generic_hashes":
            sorted(
                generic_hashes
            ),

        "specific_phrases":
            phrases,

        "control_plane_references":
            config.get(
                "control_plane_references",
                []
            ),
    }


    save_json(
        BASE
        / "benchmark_bank.json",
        bank
    )


    return bank


if __name__ == "__main__":

    bank = build()

    print(
        "VI1510 BENCHMARK BANK=PASS"
    )

    print(
        "HARD HASHES=",
        len(
            bank[
                "hard_hashes"
            ]
        )
    )

    print(
        "GENERIC HASHES=",
        len(
            bank[
                "generic_hashes"
            ]
        )
    )
