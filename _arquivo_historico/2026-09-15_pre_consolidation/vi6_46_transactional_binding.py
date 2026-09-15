#!/usr/bin/env python3

import argparse
import ast
import hashlib
import json
import os

from datetime import datetime
from pathlib import Path


VERSION = "6.46-module"


BASE = Path.home() / "ShortAutoPro"


VIDEO = BASE / "video.py"


R43 = (
    BASE
    / "logs"
    / "producao"
    / "vi6_43_binding_plan_latest.json"
)


MANIFEST = (
    BASE
    / "logs"
    / "producao"
    / "vi6_46_binding_manifest_latest.json"
)


MARKER = (
    "# VI6.46 MODULE-LEVEL "
    "TRANSACTIONAL BINDING"
)


def _sha(
    path
):

    return hashlib.sha256(
        Path(
            path
        ).read_bytes()
    ).hexdigest()


def _call_name(
    node
):

    if isinstance(
        node.func,
        ast.Name
    ):

        return node.func.id


    if isinstance(
        node.func,
        ast.Attribute
    ):

        parts = []

        current = node.func


        while isinstance(
            current,
            ast.Attribute
        ):

            parts.append(
                current.attr
            )

            current = (
                current.value
            )


        if isinstance(
            current,
            ast.Name
        ):

            parts.append(
                current.id
            )


        return ".".join(
            reversed(
                parts
            )
        )


    return ""


def _load_plan():

    with R43.open(
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(
            f
        )["plan"]


def _target():

    plan = _load_plan()


    line = int(
        plan[
            "renderer_execution_line"
        ]
    )


    source = VIDEO.read_text(
        encoding="utf-8"
    )


    tree = ast.parse(
        source
    )


    parent = {}


    for node in ast.walk(
        tree
    ):

        for child in ast.iter_child_nodes(
            node
        ):

            parent[
                child
            ] = node


    matches = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call
        ):

            continue


        if node.lineno != line:

            continue


        if (
            _call_name(
                node
            )
            != "subprocess.run"
        ):

            continue


        if not node.args:

            continue


        first = node.args[0]


        if not (
            isinstance(
                first,
                ast.Name
            )
            and first.id
            == "comando"
        ):

            continue


        matches.append(
            node
        )


    if len(
        matches
    ) != 1:

        raise RuntimeError(
            "expected_one_target_run:"
            + str(
                len(
                    matches
                )
            )
        )


    call = matches[0]


    current = call


    target_try = None


    while current in parent:

        current = parent[
            current
        ]


        if isinstance(
            current,
            ast.Try
        ):

            target_try = current

            break


    if target_try is None:

        raise RuntimeError(
            "renderer_try_not_found"
        )


    return {
        "plan":
            plan,

        "source":
            source,

        "call_line":
            call.lineno,

        "try_line":
            target_try.lineno,
    }


def precheck():

    source = VIDEO.read_text(
        encoding="utf-8"
    )


    if MARKER in source:

        return {

            "status":
                "ALREADY_BOUND",

            "video_sha256":
                _sha(
                    VIDEO
                ),
        }


    target = _target()


    plan = target[
        "plan"
    ]


    blockers = []


    if plan.get(
        "status"
    ) != "READY_FOR_ADAPTER_PREVIEW":

        blockers.append(
            "plan_not_ready"
        )


    if plan.get(
        "strategy"
    ) != "MODULE_LEVEL_SCENE_FILTER_BINDING":

        blockers.append(
            "wrong_strategy"
        )


    if plan.get(
        "video_sha256"
    ) != _sha(
        VIDEO
    ):

        blockers.append(
            "video_hash_changed"
        )


    return {

        "status":
            (
                "READY"
                if not blockers
                else "HOLD"
            ),

        "blockers":
            blockers,

        "renderer_execution_line":
            target[
                "call_line"
            ],

        "insertion_line":
            target[
                "try_line"
            ],

        "video_sha256":
            _sha(
                VIDEO
            ),
    }


def _bridge_block(
    indent
):

    i = indent


    return [

        i + MARKER,

        i + "try:",

        i + (
            "    from vi6_47_renderer_switch "
            "import adapt_scene_command "
            "as _vi647_adapt_scene_command"
        ),

        "",

        i + (
            "    comando = "
            "_vi647_adapt_scene_command("
        ),

        i + "        comando,",

        i + "        {",

        i + (
            "            \"source\": "
            "\"video.py\","
        ),

        i + (
            "            \"stage\": "
            "\"SCENE_RENDER_PRIMARY\","
        ),

        i + "        },",

        i + "    )",

        "",

        i + (
            "except Exception "
            "as _vi647_bridge_exc:"
        ),

        i + "    try:",

        i + (
            "        from "
            "vi6_48_emergency_rollback "
            "import trip as _vi648_trip"
        ),

        "",

        i + "        _vi648_trip(",

        i + (
            "            \"scene_command_bridge:\""
        ),

        i + (
            "            + type("
            "_vi647_bridge_exc"
            ").__name__"
        ),

        i + "        )",

        "",

        i + "    except Exception:",

        i + "        pass",

        "",
    ]


def bind(
    backup_path
):

    check = precheck()


    if check[
        "status"
    ] == "ALREADY_BOUND":

        return check


    if check[
        "status"
    ] != "READY":

        return check


    target = _target()


    original = VIDEO.read_bytes()


    source = original.decode(
        "utf-8"
    )


    lines = source.splitlines(
        keepends=True
    )


    insertion_line = int(
        target[
            "try_line"
        ]
    )


    original_line = (
        lines[
            insertion_line - 1
        ]
    )


    indent = (
        original_line[
            :len(
                original_line
            )
            - len(
                original_line.lstrip()
            )
        ]
    )


    block = _bridge_block(
        indent
    )


    block_text = (
        "\n".join(
            block
        )
        + "\n"
    )


    patched_lines = (
        lines[
            :insertion_line - 1
        ]
        + [
            block_text
        ]
        + lines[
            insertion_line - 1:
        ]
    )


    patched = "".join(
        patched_lines
    )


    # Sintaxe antes de tocar no original.
    ast.parse(
        patched
    )


    Path(
        backup_path
    ).write_bytes(
        original
    )


    temp = VIDEO.with_name(
        ".video.py.vi646.tmp"
    )


    temp.write_text(
        patched,
        encoding="utf-8"
    )


    os.replace(
        temp,
        VIDEO
    )


    # Validação após escrita.
    final_source = VIDEO.read_text(
        encoding="utf-8"
    )


    if final_source.count(
        MARKER
    ) != 1:

        VIDEO.write_bytes(
            original
        )

        raise RuntimeError(
            "binding_marker_invalid"
        )


    ast.parse(
        final_source
    )


    result = {

        "version":
            VERSION,

        "status":
            "BOUND_LEGACY_DEFAULT",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "renderer_execution_line_before":
            target[
                "call_line"
            ],

        "binding_insertion_line_before":
            target[
                "try_line"
            ],

        "strategy":
            "PRE_RUN_COMMAND_ADAPTER",

        "default_mode":
            "LEGACY",

        "shadow_available":
            True,

        "active_available":
            False,

        "video_sha256_before":
            hashlib.sha256(
                original
            ).hexdigest(),

        "video_sha256_after":
            _sha(
                VIDEO
            ),

        "backup":
            str(
                backup_path
            ),

        "ffmpeg_executed":
            False,

        "video_generated":
            False,
    }


    MANIFEST.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    with MANIFEST.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "binding":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return result


def verify():

    source = VIDEO.read_text(
        encoding="utf-8"
    )


    ast.parse(
        source
    )


    return {

        "status":
            (
                "BOUND_VALID"
                if source.count(
                    MARKER
                ) == 1
                else "INVALID"
            ),

        "marker_count":
            source.count(
                MARKER
            ),

        "has_adapter":
            (
                "adapt_scene_command"
                in source
            ),

        "has_subprocess_run":
            (
                "subprocess.run"
                in source
            ),

        "video_sha256":
            _sha(
                VIDEO
            ),
    }


def self_test():

    result = precheck()


    assert result[
        "status"
    ] in {
        "READY",
        "ALREADY_BOUND",
    }, result


    print()
    print(
        "======================================"
    )
    print(
        " VI6.46 MODULE PRECHECK: PASS"
    )
    print(
        "======================================"
    )


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--check",
        action="store_true"
    )


    parser.add_argument(
        "--bind"
    )


    parser.add_argument(
        "--verify",
        action="store_true"
    )


    args = parser.parse_args()


    if args.check:

        print(
            json.dumps(
                precheck(),
                ensure_ascii=False,
                indent=2
            )
        )

        return


    if args.bind:

        print(
            json.dumps(
                bind(
                    args.bind
                ),
                ensure_ascii=False,
                indent=2
            )
        )

        return


    if args.verify:

        print(
            json.dumps(
                verify(),
                ensure_ascii=False,
                indent=2
            )
        )

        return


    self_test()


if __name__ == "__main__":
    main()
