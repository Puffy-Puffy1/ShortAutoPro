#!/usr/bin/env python3

import ast
import json
import os
from pathlib import Path


VERSION = "6.16"


FILES = (
    "midia.py",
    "wikimedia_source.py",
    "source_router.py",
    "wikimedia_query_bridge.py",
)


SOURCE_WORDS = {
    "WIKIMEDIA": (
        "wikimedia",
        "commons",
        "wiki",
    ),

    "PIXABAY": (
        "pixabay",
    ),

    "GENERIC": (
        "media",
        "midia",
        "buscar",
        "search",
        "source",
    ),
}


QUERY_ARGS = {
    "q",
    "query",
    "consulta",
    "termo",
    "busca",
    "search",
    "search_query",
    "visual_query",
}


OPTIONAL_CONTEXT_ARGS = {
    "cena",
    "scene",
    "topic",
    "topico",
    "tópico",
    "modo",
    "mode",
    "limit",
    "limite",
    "must_have",
    "rota_fonte",
    "short_id",
    "descricao",
    "description",
}


def _source_class(name):

    low = name.lower()

    for source, words in SOURCE_WORDS.items():

        if any(
            word in low
            for word in words
        ):
            return source

    return "OTHER"


def _function_signature(node):

    positional = (
        list(node.args.posonlyargs)
        + list(node.args.args)
    )

    defaults_count = len(
        node.args.defaults
    )

    required_count = (
        len(positional)
        - defaults_count
    )


    args = [
        arg.arg
        for arg in positional
    ]


    required = [
        arg.arg
        for arg in positional[
            :required_count
        ]
    ]


    optional = [
        arg.arg
        for arg in positional[
            required_count:
        ]
    ]


    optional.extend(
        arg.arg
        for arg, default
        in zip(
            node.args.kwonlyargs,
            node.args.kw_defaults
        )
        if default is not None
    )


    kw_required = [
        arg.arg
        for arg, default
        in zip(
            node.args.kwonlyargs,
            node.args.kw_defaults
        )
        if default is None
    ]


    required.extend(
        kw_required
    )


    return {
        "args":
            args,

        "required":
            required,

        "optional":
            optional,

        "vararg":
            (
                node.args.vararg.arg
                if node.args.vararg
                else None
            ),

        "kwarg":
            (
                node.args.kwarg.arg
                if node.args.kwarg
                else None
            ),
    }


def _query_compatible(info):

    args = {
        x.lower()
        for x in (
            info["args"]
            + info["required"]
            + info["optional"]
        )
    }


    return bool(
        args
        & QUERY_ARGS
    )


def _required_supported(info):

    supported = (
        QUERY_ARGS
        | OPTIONAL_CONTEXT_ARGS
        | {
            "self",
            "cls",
        }
    )


    unsupported = [
        arg
        for arg in info["required"]
        if arg.lower()
        not in supported
    ]


    return (
        len(unsupported) == 0,
        unsupported
    )


def discover():

    functions = []


    for filename in FILES:

        path = Path(filename)

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

            functions.append(
                {
                    "file":
                        filename,

                    "parse_error":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                }
            )

            continue


        for node in ast.walk(tree):

            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            ):
                continue


            source_class = (
                _source_class(
                    node.name
                )
            )


            if source_class == "OTHER":
                continue


            sig = _function_signature(
                node
            )


            query_ok = (
                _query_compatible(
                    sig
                )
            )


            (
                required_ok,
                unsupported
            ) = _required_supported(
                sig
            )


            functions.append(
                {
                    "file":
                        filename,

                    "line":
                        node.lineno,

                    "name":
                        node.name,

                    "source":
                        source_class,

                    "args":
                        sig["args"],

                    "required":
                        sig["required"],

                    "optional":
                        sig["optional"],

                    "vararg":
                        sig["vararg"],

                    "kwarg":
                        sig["kwarg"],

                    "query_compatible":
                        query_ok,

                    "required_supported":
                        required_ok,

                    "unsupported_required":
                        unsupported,

                    "candidate_for_recovery":
                        bool(
                            query_ok
                            and required_ok
                        ),
                }
            )


    return functions


def summarize(functions):

    usable = [
        x
        for x in functions
        if x.get(
            "candidate_for_recovery"
        )
    ]


    wikimedia = [
        x
        for x in usable
        if x.get(
            "source"
        ) == "WIKIMEDIA"
    ]


    pixabay = [
        x
        for x in usable
        if x.get(
            "source"
        ) == "PIXABAY"
    ]


    generic = [
        x
        for x in usable
        if x.get(
            "source"
        ) == "GENERIC"
    ]


    return {
        "version":
            VERSION,

        "functions_seen":
            len(functions),

        "usable":
            len(usable),

        "wikimedia":
            len(wikimedia),

        "pixabay":
            len(pixabay),

        "generic":
            len(generic),

        "has_documentary_route":
            bool(
                wikimedia
                or generic
            ),

        "has_stock_route":
            bool(
                pixabay
                or generic
            ),
    }


def save_report(
    path=None
):

    functions = discover()

    summary = summarize(
        functions
    )


    if path is None:

        folder = os.path.expanduser(
            "~/ShortAutoPro/logs/producao"
        )

        os.makedirs(
            folder,
            exist_ok=True
        )

        path = os.path.join(
            folder,
            "vi6_16_capabilities_latest.json"
        )


    payload = {
        "summary":
            summary,

        "functions":
            functions,
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )


    return (
        path,
        payload
    )


def self_test():

    code = '''
def buscar_wikimedia_fotos(query, limit=10):
    pass

def buscar_pixabay_videos(termo, pagina=1):
    pass

def helper(foo, bar):
    pass
'''


    tree = ast.parse(code)

    nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(
            node,
            ast.FunctionDef
        )
    ]


    wiki = nodes[0]

    sig = _function_signature(
        wiki
    )


    assert (
        "query"
        in sig["required"]
    )


    assert (
        _query_compatible(
            sig
        )
    )


    ok, unsupported = (
        _required_supported(
            sig
        )
    )


    assert ok is True
    assert unsupported == []


    assert (
        _source_class(
            "buscar_wikimedia_fotos"
        )
        == "WIKIMEDIA"
    )


    assert (
        _source_class(
            "buscar_pixabay_videos"
        )
        == "PIXABAY"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.16 CAPABILITY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK AST Discovery"
    )
    print(
        "OK Query Argument Detection"
    )
    print(
        "OK Required Argument Safety"
    )
    print(
        "OK Wikimedia Classification"
    )
    print(
        "OK Pixabay Classification"
    )
    print()


if __name__ == "__main__":

    self_test()

    path, payload = save_report()

    print(
        "REPORT:",
        path
    )

    print(
        "SUMMARY:",
        payload[
            "summary"
        ]
    )
