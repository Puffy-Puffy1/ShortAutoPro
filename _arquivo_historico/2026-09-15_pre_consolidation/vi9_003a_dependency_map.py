#!/usr/bin/env python3

import ast
import json
from pathlib import Path

VERSION = "9.00.3A"

BASE = Path.home() / "ShortAutoPro"
SOURCE = BASE / "roteiro.py"
REPORT = BASE / "logs/producao/vi9_003a_dependency_map.json"

TARGET = "wiki_search"

BLOCKED = {
    "GEMINI_API_KEY",
    "GEMINI_KEY",
    "genai",
    "gemini",
    "model",
}


class Names(ast.NodeVisitor):

    def __init__(self):
        self.loaded = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.loaded.add(node.id)

        self.generic_visit(node)


def assigned_names(node):

    if isinstance(node, ast.Assign):
        targets = node.targets

    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]

    else:
        return []

    return [
        target.id
        for target in targets
        if isinstance(target, ast.Name)
    ]


def analyze():

    text = SOURCE.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    tree = ast.parse(text)

    functions = {}
    assignments = {}
    imports = {}

    for node in tree.body:

        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            functions[node.name] = node

        elif isinstance(
            node,
            (ast.Assign, ast.AnnAssign)
        ):
            for name in assigned_names(node):
                assignments[name] = node

        elif isinstance(node, ast.Import):

            for alias in node.names:
                local = (
                    alias.asname
                    or alias.name.split(".")[0]
                )

                imports[local] = {
                    "module": alias.name,
                    "source":
                        ast.get_source_segment(
                            text,
                            node
                        ),
                }

        elif isinstance(node, ast.ImportFrom):

            for alias in node.names:
                local = (
                    alias.asname
                    or alias.name
                )

                imports[local] = {
                    "module":
                        node.module or "",
                    "source":
                        ast.get_source_segment(
                            text,
                            node
                        ),
                }


    if TARGET not in functions:
        raise RuntimeError(
            "wiki_search_not_found"
        )


    required_functions = {TARGET}
    required_assignments = set()
    required_imports = set()
    blocked = set()
    unresolved = set()

    processed = set()


    builtin_names = set(
        dir(__builtins__)
    )


    while True:

        pending = (
            required_functions
            - processed
        )

        if not pending:
            break

        name = sorted(pending)[0]

        processed.add(name)

        node = functions[name]

        collector = Names()
        collector.visit(node)

        args = {
            arg.arg
            for arg in node.args.args
        }

        for dep in collector.loaded:

            if dep in args:
                continue

            if dep in builtin_names:
                continue

            if dep in BLOCKED:
                blocked.add(dep)
                continue

            if dep in functions:
                required_functions.add(dep)
                continue

            if dep in assignments:
                required_assignments.add(dep)
                continue

            if dep in imports:
                required_imports.add(dep)
                continue

            unresolved.add(dep)


    function_data = []

    for name in sorted(
        required_functions,
        key=lambda n:
            functions[n].lineno
    ):
        node = functions[name]

        function_data.append({
            "name": name,
            "line": node.lineno,
            "source":
                ast.get_source_segment(
                    text,
                    node
                ),
        })


    assignment_data = []

    for name in sorted(
        required_assignments
    ):
        node = assignments[name]

        assignment_data.append({
            "name": name,
            "source":
                ast.get_source_segment(
                    text,
                    node
                ),
        })


    import_data = []

    seen = set()

    for name in sorted(
        required_imports
    ):
        item = imports[name]

        source = item["source"]

        if source in seen:
            continue

        seen.add(source)

        import_data.append({
            "symbol": name,
            "module":
                item["module"],
            "source":
                source,
        })


    result = {
        "version":
            VERSION,

        "target":
            TARGET,

        "functions":
            function_data,

        "assignments":
            assignment_data,

        "imports":
            import_data,

        "blocked":
            sorted(blocked),

        "unresolved":
            sorted(unresolved),

        "network_executed":
            False,

        "roteiro_imported":
            False,

        "gemini_executed":
            False,
    }


    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    REPORT.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


if __name__ == "__main__":

    r = analyze()

    print(
        "VI9.00.3A DEPENDENCY MAP=PASS"
    )

    print(
        "FUNCTIONS:",
        [
            x["name"]
            for x in r["functions"]
        ]
    )

    print(
        "ASSIGNMENTS:",
        [
            x["name"]
            for x in r["assignments"]
        ]
    )

    print(
        "IMPORTS:",
        [
            (
                x["symbol"],
                x["module"]
            )
            for x in r["imports"]
        ]
    )

    print(
        "BLOCKED:",
        r["blocked"]
    )

    print(
        "UNRESOLVED:",
        r["unresolved"]
    )

    print(
        "NETWORK EXECUTED:",
        r["network_executed"]
    )

    print(
        "ROTEIRO IMPORTED:",
        r["roteiro_imported"]
    )

    print(
        "GEMINI EXECUTED:",
        r["gemini_executed"]
    )
