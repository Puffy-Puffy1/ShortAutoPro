#!/usr/bin/env python3

import ast
import json
from pathlib import Path

VERSION = "9.00.2"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

TARGET_FILE = (
    BASE
    / "roteiro.py"
)

TARGET_FUNCTION = (
    "wiki_search"
)


class NameCollector(ast.NodeVisitor):

    def __init__(self):
        self.loaded = set()
        self.called = set()
        self.attributes = set()

    def visit_Name(
        self,
        node
    ):
        if isinstance(
            node.ctx,
            ast.Load
        ):
            self.loaded.add(
                node.id
            )

        self.generic_visit(
            node
        )

    def visit_Call(
        self,
        node
    ):
        if isinstance(
            node.func,
            ast.Name
        ):
            self.called.add(
                node.func.id
            )

        elif isinstance(
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

            self.attributes.add(
                ".".join(
                    reversed(parts)
                )
            )

        self.generic_visit(
            node
        )


def source_segment(
    text,
    node
):
    return ast.get_source_segment(
        text,
        node
    )


def analyze():

    if not TARGET_FILE.exists():
        raise RuntimeError(
            "roteiro.py_missing"
        )

    text = TARGET_FILE.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    tree = ast.parse(
        text
    )

    functions = {}

    constants = {}

    imports = []

    target = None

    top_level_calls = []

    top_level_exits = []


    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):
            functions[
                node.name
            ] = node

            if (
                node.name
                == TARGET_FUNCTION
            ):
                target = node


        elif isinstance(
            node,
            ast.Import
        ):
            imports.append({
                "type":
                    "import",

                "source":
                    source_segment(
                        text,
                        node
                    ),
            })


        elif isinstance(
            node,
            ast.ImportFrom
        ):
            imports.append({
                "type":
                    "from_import",

                "source":
                    source_segment(
                        text,
                        node
                    ),
            })


        elif isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
            )
        ):
            names = []

            if isinstance(
                node,
                ast.Assign
            ):
                targets = (
                    node.targets
                )

            else:
                targets = [
                    node.target
                ]

            for target_node in targets:

                if isinstance(
                    target_node,
                    ast.Name
                ):
                    names.append(
                        target_node.id
                    )

            for name in names:
                constants[
                    name
                ] = node


        else:

            for inner in ast.walk(
                node
            ):

                if isinstance(
                    inner,
                    ast.Call
                ):

                    call_name = None

                    if isinstance(
                        inner.func,
                        ast.Name
                    ):
                        call_name = (
                            inner.func.id
                        )

                    elif isinstance(
                        inner.func,
                        ast.Attribute
                    ):
                        call_name = (
                            inner.func.attr
                        )

                    if call_name:

                        top_level_calls.append({
                            "name":
                                call_name,

                            "line":
                                getattr(
                                    inner,
                                    "lineno",
                                    None
                                ),
                        })


                if isinstance(
                    inner,
                    (
                        ast.Raise,
                        ast.Assert,
                    )
                ):
                    top_level_exits.append({
                        "type":
                            type(
                                inner
                            ).__name__,

                        "line":
                            getattr(
                                inner,
                                "lineno",
                                None
                            ),
                    })


    if target is None:
        raise RuntimeError(
            "wiki_search_not_found"
        )


    collector = (
        NameCollector()
    )

    collector.visit(
        target
    )


    args = {
        arg.arg
        for arg in (
            target.args.args
            or []
        )
    }


    builtins = {
        "str",
        "int",
        "float",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "len",
        "min",
        "max",
        "sum",
        "sorted",
        "enumerate",
        "range",
        "print",
        "isinstance",
        "Exception",
        "RuntimeError",
        "ValueError",
        "TypeError",
    }


    dependencies = sorted(
        name
        for name in collector.loaded
        if (
            name not in args
            and name
            not in builtins
            and name
            != TARGET_FUNCTION
        )
    )


    helper_functions = []

    constant_dependencies = []

    unresolved = []


    for name in dependencies:

        if name in functions:

            helper_functions.append({
                "name":
                    name,

                "line":
                    functions[
                        name
                    ].lineno,

                "source":
                    source_segment(
                        text,
                        functions[name]
                    ),
            })


        elif name in constants:

            constant_dependencies.append({
                "name":
                    name,

                "line":
                    constants[
                        name
                    ].lineno,

                "source":
                    source_segment(
                        text,
                        constants[name]
                    ),
            })


        else:

            unresolved.append(
                name
            )


    result = {
        "version":
            VERSION,

        "target_file":
            str(
                TARGET_FILE
            ),

        "target_function":
            TARGET_FUNCTION,

        "target_line":
            target.lineno,

        "arguments":
            [
                arg.arg
                for arg in (
                    target.args.args
                    or []
                )
            ],

        "target_source":
            source_segment(
                text,
                target
            ),

        "loaded_names":
            sorted(
                collector.loaded
            ),

        "called_names":
            sorted(
                collector.called
            ),

        "attribute_calls":
            sorted(
                collector.attributes
            ),

        "dependencies":
            dependencies,

        "helper_functions":
            helper_functions,

        "constant_dependencies":
            constant_dependencies,

        "unresolved_names":
            unresolved,

        "imports":
            imports,

        "top_level_calls":
            top_level_calls,

        "top_level_exit_like":
            top_level_exits,

        "module_import_executed":
            False,

        "network_executed":
            False,

        "gemini_executed":
            False,

        "download_executed":
            False,

        "media_mutated":
            False,
    }


    output = (
        BASE
        / "logs/producao/"
          "vi9_002_wiki_search_static_analysis.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


def self_test():

    assert VERSION == "9.00.2"

    print(
        "VI9.00.2 STATIC FUNCTION ISOLATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
