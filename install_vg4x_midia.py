#!/usr/bin/env python3

import ast
import shutil
import sys
import time
from pathlib import Path


PATH = Path(
    "midia.py"
)

HOOK_MARKER = (
    "# SHORTAUTOPRO VISUAL GATE V4X BRIDGE"
)

FINAL_MARKER = (
    "# SHORTAUTOPRO VISUAL GATE V4X FINAL DECISION"
)


def find_final_assignment(
    source,
    tree,
):

    matches = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Assign,
        ):
            continue

        names = [
            target.id
            for target in node.targets
            if isinstance(
                target,
                ast.Name,
            )
        ]

        if "pool" not in names:
            continue

        segment = ast.get_source_segment(
            source,
            node,
        ) or ""

        if (
            "escolhido"
            in segment
            and
            "pool"
            in segment
            and
            "chave"
            in segment
        ):
            matches.append(node)

    return matches


def patch(
    dry_run=False,
):

    source = PATH.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    lines = source.splitlines(
        keepends=True
    )

    final_matches = find_final_assignment(
        source,
        tree,
    )

    if (
        FINAL_MARKER not in source
        and len(final_matches) != 1
    ):

        print(
            "VG4X_PATCH=REFUSED"
        )

        print(
            "FINAL_ASSIGNMENT_MATCHES=",
            len(final_matches),
        )

        return 2


    top_defs = [
        node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        )
    ]

    if not top_defs:

        print(
            "VG4X_PATCH=REFUSED_NO_DEFS"
        )

        return 3


    last_def = max(
        top_defs,
        key=lambda node:
            node.end_lineno
    )

    print(
        "LAST_TOP_LEVEL_DEF_END=",
        last_def.end_lineno,
    )

    if final_matches:

        print(
            "FINAL_GATE_INSERT_LINE=",
            final_matches[0].lineno,
        )


    if dry_run:

        print(
            "VG4X_DRY_RUN=PASS"
        )

        return 0


    backup = Path(
        "backups"
    ) / (
        "midia_pre_vg4x_"
        +
        time.strftime(
            "%Y%m%d_%H%M%S"
        )
        +
        ".py"
    )

    backup.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        PATH,
        backup,
    )

    Path(
        "temp/VG4X_MIDIA_BACKUP_PATH"
    ).write_text(
        str(backup),
        encoding="utf-8",
    )


    insertions = []


    if HOOK_MARKER not in source:

        hook = f'''
{HOOK_MARKER}
try:
    from vg4x_bridge import install as _vg4x_install_bridge
    _VG4X_BRIDGE_RESULT = _vg4x_install_bridge(globals())
except Exception as _vg4x_bridge_error:
    print(
        "VG4X_BRIDGE=FAIL_OPEN "
        + type(_vg4x_bridge_error).__name__
        + ":"
        + str(_vg4x_bridge_error)
    )

'''

        insertions.append(
            (
                last_def.end_lineno + 1,
                hook,
            )
        )


    if FINAL_MARKER not in source:

        node = final_matches[0]

        original_line = lines[
            node.lineno - 1
        ]

        indent = (
            original_line[
                :len(original_line)
                -
                len(
                    original_line.lstrip()
                )
            ]
        )

        gate_lines = [
            "",
            FINAL_MARKER,
            "try:",
            "    from visual_gate_v4x import choose_from_locals as _vg4x_choose_from_locals",
            "    escolhido, pool, _vg4x_meta = _vg4x_choose_from_locals(",
            "        locals(),",
            "        pool,",
            "        escolhido,",
            "    )",
            "except Exception as _vg4x_gate_error:",
            "    print(",
            '        "VG4X_FINAL_GATE=FAIL_OPEN "',
            "        + type(_vg4x_gate_error).__name__",
            '        + ":"',
            "        + str(_vg4x_gate_error)",
            "    )",
            "",
        ]

        gate = "".join(
            indent
            +
            line
            +
            "\n"

            for line in gate_lines
        )

        insertions.append(
            (
                node.lineno,
                gate,
            )
        )


    # Aplica do fim para o início.
    for line_number, text in sorted(
        insertions,
        reverse=True,
    ):

        index = max(
            0,
            line_number - 1,
        )

        lines.insert(
            index,
            text,
        )


    new_source = "".join(
        lines
    )


    # Certifica sintaxe ANTES de gravar.
    compile(
        new_source,
        str(PATH),
        "exec",
    )


    PATH.write_text(
        new_source,
        encoding="utf-8",
    )


    print(
        "VG4X_PATCH=PASS"
    )

    print(
        "BACKUP=",
        backup,
    )

    return 0


if __name__ == "__main__":

    dry = (
        "--dry-run"
        in sys.argv
    )

    raise SystemExit(
        patch(
            dry_run=dry
        )
    )
