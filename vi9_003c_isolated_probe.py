#!/usr/bin/env python3

import ast
import importlib.util
import multiprocessing
import os
import queue
from pathlib import Path

BASE = Path.home() / "ShortAutoPro"
ADAPTER = BASE / "vi9_wiki_search_adapter.py"
TARGET = "wiki_search"


def signature():
    text = ADAPTER.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    tree = ast.parse(text)

    for node in tree.body:
        if (
            isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef)
            )
            and node.name == TARGET
        ):
            return [
                a.arg
                for a in node.args.args
                if a.arg not in {"self", "cls"}
            ]

    return []


def make_kwargs(args, query):
    out = {}
    has_query = False

    for arg in args:
        low = arg.lower()

        if low in {
            "query",
            "q",
            "term",
            "search_term",
            "keyword",
            "keywords",
        }:
            out[arg] = query
            has_query = True

        elif low in {
            "limit",
            "max_results",
            "count",
        }:
            out[arg] = 5

        else:
            return None, f"unsupported_argument:{arg}"

    if not has_query:
        return None, "query_argument_not_found"

    return out, None


def worker(kwargs, q):
    try:
        os.environ["VI900_DOWNLOAD_ALLOWED"] = "OFF"
        os.environ["VI900_MEDIA_WRITE_ALLOWED"] = "OFF"
        os.environ["VI900_RENDER_ALLOWED"] = "OFF"
        os.environ["VI900_SOURCE_RECOVERY_ALLOWED"] = "OFF"

        q.put(("EVENT", "WORKER_STARTED"))

        spec = importlib.util.spec_from_file_location(
            "_vi9_wiki",
            str(ADAPTER)
        )

        if spec is None or spec.loader is None:
            raise RuntimeError("adapter_spec_failed")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        q.put(("EVENT", "ADAPTER_IMPORTED"))

        fn = getattr(module, TARGET)

        q.put(("EVENT", "FUNCTION_READY"))

        value = fn(**kwargs)

        q.put(("RESULT", value))

    except BaseException as exc:
        q.put((
            "ERROR",
            type(exc).__name__ + ": " + str(exc)[:600]
        ))


def execute(query, timeout=15):
    args = signature()

    kwargs, error = make_kwargs(
        args,
        query
    )

    if error:
        return {
            "status": "HOLD",
            "reason": error,
            "signature": args,
        }

    if (
        "fork"
        not in multiprocessing.get_all_start_methods()
    ):
        return {
            "status": "HOLD",
            "reason": "fork_unavailable",
            "signature": args,
        }

    ctx = multiprocessing.get_context("fork")
    q = ctx.Queue()

    p = ctx.Process(
        target=worker,
        args=(kwargs, q)
    )

    p.start()
    p.join(timeout)

    if p.is_alive():
        p.terminate()
        p.join(2)

        return {
            "status": "TIMEOUT",
            "reason": "search_timeout",
            "start_method": "fork",
        }

    events = []
    result = None
    error = None

    while True:
        try:
            kind, value = q.get_nowait()
        except queue.Empty:
            break

        if kind == "EVENT":
            events.append(value)

        elif kind == "RESULT":
            result = value

        elif kind == "ERROR":
            error = value

    if error:
        return {
            "status": "PROVIDER_ERROR",
            "reason": error,
            "events": events,
            "exitcode": p.exitcode,
            "start_method": "fork",
        }

    if result is None:
        return {
            "status": "HOLD",
            "reason": "worker_exited_without_result",
            "events": events,
            "exitcode": p.exitcode,
            "start_method": "fork",
        }

    return {
        "status": "SEARCH_RETURNED",
        "value": result,
        "events": events,
        "exitcode": p.exitcode,
        "signature": args,
        "start_method": "fork",
    }


if __name__ == "__main__":
    query = (
        "person hiding corner dark hallway "
        "shadows portrait clear face medium"
    )

    print("SIGNATURE:", signature())
    print("QUERY:", query)

    r = execute(query)

    print("STATUS:", r.get("status"))
    print("REASON:", r.get("reason"))
    print("START METHOD:", r.get("start_method"))
    print("EXIT CODE:", r.get("exitcode"))
    print("EVENTS:", r.get("events"))

    value = r.get("value")

    print(
        "RETURN TYPE:",
        type(value).__name__
    )

    if isinstance(value, list):
        print("RESULT COUNT:", len(value))

        for i, item in enumerate(
            value[:5],
            start=1
        ):
            print(
                f"RESULT {i}:",
                repr(item)[:500]
            )

    else:
        print(
            "RAW RESULT:",
            repr(value)[:1500]
        )
