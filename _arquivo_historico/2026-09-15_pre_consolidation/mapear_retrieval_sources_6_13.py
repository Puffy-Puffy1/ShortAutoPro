#!/usr/bin/env python3

import ast
from pathlib import Path


FILES = [

    "midia.py",

    "wikimedia_source.py",

    "source_router.py",

    "wikimedia_query_bridge.py",
]


KEYWORDS = (
    "buscar",
    "search",
    "pixabay",
    "wikimedia",
    "source",
    "media",
)


def signature(
    node
):

    args = []


    for arg in (
        node.args.posonlyargs
        + node.args.args
    ):

        args.append(
            arg.arg
        )


    if node.args.vararg:

        args.append(
            "*"
            + node.args.vararg.arg
        )


    for arg in (
        node.args.kwonlyargs
    ):

        args.append(
            arg.arg
        )


    if node.args.kwarg:

        args.append(
            "**"
            + node.args.kwarg.arg
        )


    return (
        node.name
        + "("
        + ", ".join(
            args
        )
        + ")"
    )


print()
print(
    "======================================"
)
print(
    " VI6.13 SOURCE MAP"
)
print(
    "======================================"
)


count = 0


for filename in FILES:

    path = Path(
        filename
    )


    if not path.exists():

        continue


    try:

        source = path.read_text(
            encoding="utf-8"
        )

        tree = ast.parse(
            source
        )

    except Exception as exc:

        print(
            f"{filename}: "
            f"PARSE ERROR {exc}"
        )

        continue


    found = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef
            )
        ):

            continue


        name = node.name.lower()


        if any(
            keyword in name
            for keyword
            in KEYWORDS
        ):

            found.append(
                (
                    node.lineno,
                    signature(
                        node
                    )
                )
            )


    if found:

        print()
        print(
            f"[{filename}]"
        )


        for line, sig in sorted(
            found
        ):

            count += 1

            print(
                f"  L{line}: {sig}"
            )


print()
print(
    "TOTAL FUNCTIONS:",
    count
)
print()
print(
    "API CALLS=0"
)
print(
    "DOWNLOADS=0"
)
print(
    "VIDEOS=0"
)
print()
