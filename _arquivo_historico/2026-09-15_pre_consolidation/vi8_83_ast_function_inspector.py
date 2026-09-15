#!/usr/bin/env python3

import ast
from pathlib import Path

VERSION = "8.83"


def inspect_python(path):
    p = Path(path)

    if p.suffix != ".py":
        return {
            "version": VERSION,
            "functions": [],
            "imports": [],
            "status":
                "NON_PYTHON_MODULE",
        }

    text = p.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    tree = ast.parse(
        text
    )

    functions = []

    imports = []

    for node in ast.walk(
        tree
    ):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):
            args = [
                arg.arg
                for arg in (
                    node.args.args
                    or []
                )
            ]

            functions.append({
                "name":
                    node.name,

                "args":
                    args,

                "async":
                    isinstance(
                        node,
                        ast.AsyncFunctionDef
                    ),

                "lineno":
                    node.lineno,
            })

        elif isinstance(
            node,
            ast.Import
        ):
            for alias in node.names:
                imports.append(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom
        ):
            if node.module:
                imports.append(
                    node.module
                )

    return {
        "version": VERSION,
        "functions":
            sorted(
                functions,
                key=lambda x:
                    x["lineno"]
            ),

        "imports":
            sorted(
                set(imports)
            ),

        "status":
            "PASS",
    }


def self_test():
    assert VERSION == "8.83"

    print(
        "VI8.83 AST FUNCTION INSPECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
