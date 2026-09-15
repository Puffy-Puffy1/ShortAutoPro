#!/usr/bin/env python3

import ast
import json

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)


FILES = [
    "vi1510_1_24_partitioned_resolver.py",
    "vi1510_1_25_scene_usage.py",
    "vi1510_1_26_evidence_text.py",
    "vi1510_1_27_source_metadata_v2.py",
    "vi1510_1_28_relevance_v2.py",
    "vi1510_1_29_lineage_v2.py",
    "vi1510_1_33_runtime_inventory_v3_regression.py",
    "vi1510_1_23_runtime_inventory_v3.py",
    "vi1510_1_33_source_usage_join_regression.py",
    "vi1510_1_29_source_usage_join.py",
    "vi1510_1_30_evidence_gate_v2.py",
    "vi1510_1_31_cross_topic_v3.py",
    "vi1510_1_32_regression_v2.py",
]


SAFE_LOCAL_URL_MODULES = {
    "urllib.parse",
}


DIRECT_NETWORK_MODULES = {
    "urllib.request",
    "urllib.error",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
}


DANGEROUS_ROOTS = {
    "subprocess",
}


DANGEROUS_OS_METHODS = {
    "system",
    "popen",
    "spawnl",
    "spawnlp",
    "spawnv",
    "spawnvp",
}


HARD_CODED_CASE_MARKERS = {
    "elisa lam",
    "hotel cecil",
    "roanoke",
    "hindenburg",
    "fermi paradox",
}


def import_names(
    node,
):
    if isinstance(
        node,
        ast.Import
    ):

        return [
            item.name

            for item
            in node.names
        ]


    if isinstance(
        node,
        ast.ImportFrom
    ):

        return (
            [
                node.module
            ]

            if node.module

            else []
        )


    return []


def inspect_file(
    path,
):
    text = path.read_text(
        encoding="utf-8"
    )


    tree = ast.parse(
        text
    )


    network = []

    safe_local_url = []

    dangerous = []


    for node in ast.walk(
        tree
    ):

        for name in import_names(
            node
        ):

            if name in SAFE_LOCAL_URL_MODULES:

                safe_local_url.append(
                    name
                )


            if (
                name in DIRECT_NETWORK_MODULES

                or

                name.startswith(
                    "urllib.request"
                )

                or

                name.startswith(
                    "requests."
                )

                or

                name.startswith(
                    "httpx."
                )

                or

                name.startswith(
                    "aiohttp."
                )

                or

                name.startswith(
                    "socket."
                )
            ):

                network.append(
                    name
                )


        if isinstance(
            node,
            ast.Call
        ):

            func = node.func


            if (
                isinstance(
                    func,
                    ast.Attribute
                )

                and

                isinstance(
                    func.value,
                    ast.Name
                )
            ):

                root = (
                    func.value.id
                )


                method = (
                    func.attr
                )


                if root in DANGEROUS_ROOTS:

                    dangerous.append(
                        root
                        + "."
                        + method
                    )


                if (
                    root == "os"

                    and

                    method
                    in DANGEROUS_OS_METHODS
                ):

                    dangerous.append(
                        "os."
                        + method
                    )


    # V2.2:
    # hardcode analysis must inspect production AST/text,
    # not standalone __main__ self-tests.
    production_lines = []

    for line in text.splitlines():

        if line.startswith(
            'if __name__ == "__main__":'
        ):

            break

        production_lines.append(
            line
        )


    normalized = (
        "\n".join(
            production_lines
        ).lower()
    )


    hardcoded_hits = [
        marker

        for marker in (
            HARD_CODED_CASE_MARKERS
        )

        if marker
        in normalized
    ]


    # Regression files are allowed to contain explicit
    # fixture/topic strings. Production modules are not.
    is_regression = (
        "regression"
        in path.name.lower()
    )


    hardcoded = (
        bool(
            hardcoded_hits
        )

        and

        not is_regression
    )


    return {
        "file":
            path.name,

        "network":
            sorted(
                set(
                    network
                )
            ),

        "safe_local_url":
            sorted(
                set(
                    safe_local_url
                )
            ),

        "dangerous":
            sorted(
                set(
                    dangerous
                )
            ),

        "hardcoded":
            hardcoded,

        "hardcoded_hits":
            (
                sorted(
                    hardcoded_hits
                )

                if hardcoded

                else []
            ),
    }


def main():
    results = []

    blockers = []


    for name in FILES:

        path = (
            BASE
            / name
        )


        if not path.exists():

            blockers.append(
                "missing:"
                + name
            )

            continue


        try:

            result = inspect_file(
                path
            )


        except Exception as exc:

            blockers.append(
                (
                    "parse_error:"
                    + name
                    + ":"
                    + type(
                        exc
                    ).__name__
                    + ":"
                    + str(
                        exc
                    )
                )
            )

            continue


        results.append(
            result
        )


        if result[
            "network"
        ]:

            blockers.append(
                "direct_network:"
                + name
            )


        if result[
            "dangerous"
        ]:

            blockers.append(
                "dangerous_execution:"
                + name
            )


        if result[
            "hardcoded"
        ]:

            blockers.append(
                "hardcoded_topic:"
                + name
            )


    status = (
        "VI1510_1_V2_ARCHITECTURE_CERTIFIED"

        if not blockers

        else
        "VI1510_1_V2_ARCHITECTURE_HOLD"
    )


    report = {
        "version":
            "1510.1-v2.1",

        "status":
            status,

        "files":
            results,

        "blockers":
            blockers,

        "network_executed":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "production_mutated":
            False,
    }


    output = (
        BASE
        / "logs/producao/"
        "vi1510_1_v2_architecture_latest.json"
    )


    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    output.write_text(
        json.dumps(
            {
                "gate":
                    report
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    print()
    print(
        "=============================================="
    )

    print(
        " VI1510.1 V2 ARCHITECTURE"
    )

    print(
        "=============================================="
    )


    print(
        "STATUS:",
        status
    )


    for item in results:

        print(
            item[
                "file"
            ],
            "| network=",
            item[
                "network"
            ],
            "| local_url=",
            item[
                "safe_local_url"
            ],
            "| dangerous=",
            item[
                "dangerous"
            ],
            "| hardcoded=",
            item[
                "hardcoded"
            ],
        )


    print(
        "BLOCKERS:",
        blockers
    )


    if blockers:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
