#!/usr/bin/env python3

import argparse
import ast
import re
import shutil
import time
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"
PATH = ROOT / "midia.py"


FINAL_MARK = (
    "# SHORTAUTOPRO VSE42 FINAL GATE"
)

DOWNLOAD_MARK = (
    "# SHORTAUTOPRO VSE42 DOWNLOAD GUARD"
)

PROVIDER_MARK = (
    "# SHORTAUTOPRO VSE42 PROVIDER OBSERVER"
)

BREAK_MARK = (
    "# SHORTAUTOPRO VSE42 FIRST SUCCESS COMMIT"
)


def top_function(tree, name):

    hits = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name == name
        )
    ]

    if len(hits) != 1:
        raise RuntimeError(
            f"{name}: expected 1 definition, "
            f"found {len(hits)}"
        )

    return hits[0]


def preview(src):

    tree = ast.parse(src)

    downloader = top_function(
        tree,
        "baixar_candidato_5_2",
    )

    search = top_function(
        tree,
        "buscar_todos_candidatos",
    )


    pool_hits = list(
        re.finditer(
            r"(?m)^([ \t]*)pool\s*=\s*"
            r"ordenar_failover_5_2\s*\(",
            src,
        )
    )


    failover_hits = [
        i
        for i, line in enumerate(
            src.splitlines(),
            start=1,
        )
        if (
            "FAILOVER: QUALIDADE PRESERVADA"
            in line
        )
    ]


    print(
        "DOWNLOADER_END=",
        downloader.end_lineno,
    )

    print(
        "SEARCH_END=",
        search.end_lineno,
    )

    print(
        "FINAL_GATE_ANCHORS=",
        len(pool_hits),
    )

    print(
        "FAILOVER_PRINT_ANCHORS=",
        len(failover_hits),
    )


    return (
        downloader,
        search,
        pool_hits,
        failover_hits,
    )


def apply_patch():

    src = PATH.read_text(
        encoding="utf-8"
    )

    (
        downloader,
        search,
        pool_hits,
        failover_hits,
    ) = preview(src)


    if not pool_hits:
        raise RuntimeError(
            "ordenar_failover_5_2 anchor missing"
        )

    if not failover_hits:
        raise RuntimeError(
            "FAILOVER anchor missing"
        )


    stamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )

    backup = (
        ROOT
        / "backups"
        / f"midia_v42_patch_{stamp}"
    )

    backup.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        PATH,
        backup / "midia.py",
    )

    (
        ROOT
        / "temp"
        / "VSE42_BACKUP_PATH"
    ).write_text(
        str(backup),
        encoding="utf-8",
    )


    # --------------------------------------------------------
    # 1. FIRST-SUCCESS COMMIT
    # --------------------------------------------------------

    lines = src.splitlines(
        keepends=True
    )


    if BREAK_MARK not in src:

        target = None

        for idx, line in enumerate(lines):

            if (
                "FAILOVER: QUALIDADE PRESERVADA"
                not in line
            ):
                continue

            for j in range(
                idx + 1,
                min(
                    idx + 12,
                    len(lines),
                ),
            ):

                if (
                    lines[j].strip()
                    ==
                    "break"
                ):

                    target = j
                    break

            if target is not None:
                break


        if target is None:

            raise RuntimeError(
                "nested failover break not found"
            )


        nested_indent = (
            lines[target]
            [
                :
                len(lines[target])
                -
                len(
                    lines[target].lstrip()
                )
            ]
        )


        if nested_indent.endswith(
            "    "
        ):

            parent_indent = nested_indent[:-4]

        else:

            parent_indent = nested_indent


        injection = (
            parent_indent
            +
            BREAK_MARK
            +
            "\n"
            +
            parent_indent
            +
            "break\n"
        )


        lines.insert(
            target + 1,
            injection,
        )


        src = "".join(lines)


    # --------------------------------------------------------
    # Reparse after break insertion.
    # --------------------------------------------------------

    tree = ast.parse(src)

    downloader = top_function(
        tree,
        "baixar_candidato_5_2",
    )

    search = top_function(
        tree,
        "buscar_todos_candidatos",
    )


    insertions = []


    if DOWNLOAD_MARK not in src:

        text = (
            "\n"
            + DOWNLOAD_MARK
            + "\n"
            + "try:\n"
            + "    from media_download_guard_v42 "
              "import wrap_downloader as "
              "_vse42_wrap_downloader\n"
            + "    baixar_candidato_5_2 = "
              "_vse42_wrap_downloader("
              "baixar_candidato_5_2)\n"
            + "except Exception as _vse42_exc:\n"
            + "    print("
              "\"VSE42_DOWNLOAD_GUARD_ERROR=\""
              " + type(_vse42_exc).__name__"
              " + \":\" + str(_vse42_exc))\n"
        )

        insertions.append(
            (
                downloader.end_lineno,
                text,
            )
        )


    if PROVIDER_MARK not in src:

        text = (
            "\n"
            + PROVIDER_MARK
            + "\n"
            + "try:\n"
            + "    from provider_observer_v42 "
              "import wrap_search as "
              "_vse42_wrap_search\n"
            + "    buscar_todos_candidatos = "
              "_vse42_wrap_search("
              "buscar_todos_candidatos)\n"
            + "except Exception as _vse42_exc:\n"
            + "    print("
              "\"VSE42_PROVIDER_OBSERVER_ERROR=\""
              " + type(_vse42_exc).__name__"
              " + \":\" + str(_vse42_exc))\n"
        )

        insertions.append(
            (
                search.end_lineno,
                text,
            )
        )


    lines = src.splitlines(
        keepends=True
    )


    for end_line, text in sorted(
        insertions,
        reverse=True,
    ):

        lines.insert(
            end_line,
            text,
        )


    src = "".join(lines)


    if FINAL_MARK not in src:

        match = re.search(
            r"(?m)^([ \t]*)pool\s*=\s*"
            r"ordenar_failover_5_2\s*\(",
            src,
        )

        if not match:

            raise RuntimeError(
                "final gate anchor disappeared"
            )


        indent = match.group(1)


        gate = (
            indent
            + FINAL_MARK
            + "\n"
            + indent
            + "try:\n"
            + indent
            + "    from visual_runtime_v42 "
              "import final_gate_from_context "
              "as _vse42_final_gate\n"
            + indent
            + "    escolhido = "
              "_vse42_final_gate("
              "locals(), globals())\n"
            + indent
            + "except Exception as _vse42_exc:\n"
            + indent
            + "    print("
              "\"VSE42_FINAL_GATE_ERROR=\""
              " + type(_vse42_exc).__name__"
              " + \":\" + str(_vse42_exc))\n"
        )


        src = (
            src[:match.start()]
            +
            gate
            +
            src[match.start():]
        )


    ast.parse(src)

    PATH.write_text(
        src,
        encoding="utf-8",
    )


    print(
        "MIDIA_V42_PATCH=PASS"
    )

    print(
        "BACKUP=",
        backup,
    )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    src = PATH.read_text(
        encoding="utf-8"
    )

    preview(src)

    if args.apply:
        apply_patch()
    else:
        print(
            "DRY_RUN=PASS"
        )


if __name__ == "__main__":
    main()
