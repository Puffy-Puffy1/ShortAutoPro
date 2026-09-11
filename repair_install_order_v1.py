#!/usr/bin/env python3

from pathlib import Path
import ast
import re


FILES = [
    Path("media_diversity_guard_v1.py"),
    Path("visual_scene_commit_lock_v1.py"),
]


MARKER = "# SHORTAUTOPRO SAFE DEFERRED INSTALL V1"


def repair(path):

    if not path.is_file():
        return {
            "file": str(path),
            "status": "MISSING",
        }

    src = path.read_text(
        encoding="utf-8",
    )

    if MARKER in src:
        return {
            "file": str(path),
            "status": "ALREADY_PATCHED",
        }


    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return {
            "file": str(path),
            "status": "SYNTAX_ERROR",
            "error": str(exc),
        }


    install_defs = [
        n
        for n in tree.body
        if (
            isinstance(n, ast.FunctionDef)
            and n.name == "install"
        )
    ]


    first_install_def = (
        min(
            (n.lineno for n in install_defs),
            default=10**9,
        )
    )


    lines = src.splitlines(
        keepends=True,
    )

    changed = False
    deferred = False


    pattern = re.compile(
        r'^(\s*)install\s*\(\s*globals\s*\(\s*\)\s*\)\s*$'
    )


    new_lines = []


    for lineno, line in enumerate(
        lines,
        start=1,
    ):

        raw = line.rstrip("\r\n")
        match = pattern.match(raw)

        if (
            match
            and
            lineno < first_install_def
        ):

            indent = match.group(1)

            # Só automatizamos chamadas de módulo.
            if indent == "":

                new_lines.append(
                    "# SHORTAUTOPRO: early install deferred\n"
                )

                changed = True
                deferred = True

                continue


        new_lines.append(line)


    new_src = "".join(new_lines)


    if deferred and install_defs:

        new_src += r'''

# SHORTAUTOPRO SAFE DEFERRED INSTALL V1
try:
    _sap_deferred_install = globals().get(
        "install"
    )

    if callable(
        _sap_deferred_install
    ):
        _sap_deferred_install(
            globals()
        )

except Exception as _sap_deferred_install_error:

    print(
        "SAFE_DEFERRED_INSTALL=FAIL_OPEN "
        +
        type(
            _sap_deferred_install_error
        ).__name__
        +
        ":"
        +
        str(
            _sap_deferred_install_error
        )
    )
'''

        changed = True


    elif changed:

        new_src += "\n" + MARKER + "\n"


    if changed:

        path.write_text(
            new_src,
            encoding="utf-8",
        )


    return {
        "file": str(path),
        "status":
            "PATCHED"
            if changed
            else
            "NO_CHANGE",

        "install_defs":
            len(install_defs),

        "deferred":
            deferred,
    }


def main():

    print("=" * 68)
    print("INSTALL ORDER REPAIR")
    print("=" * 68)

    for path in FILES:

        result = repair(path)

        print(
            "RESULT=",
            result,
        )


if __name__ == "__main__":
    main()
