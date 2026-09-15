#!/usr/bin/env python3

import importlib.util
import multiprocessing
import os
import queue
from pathlib import Path

from vi8_92_query_argument_builder import (
    build as build_args
)

VERSION = "8.95.1"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def _worker(
    module_path,
    function_name,
    kwargs,
    output_queue
):
    try:
        # Tell parent that the child actually started.
        output_queue.put({
            "_event":
                "WORKER_STARTED"
        })

        os.environ[
            "VI900_SEARCH_PROBE"
        ] = "ON"

        os.environ[
            "VI900_DOWNLOAD_ALLOWED"
        ] = "OFF"

        os.environ[
            "VI900_MEDIA_WRITE_ALLOWED"
        ] = "OFF"

        os.environ[
            "VI900_RENDER_ALLOWED"
        ] = "OFF"

        os.environ[
            "VI900_SOURCE_RECOVERY_ALLOWED"
        ] = "OFF"


        spec = (
            importlib.util
            .spec_from_file_location(
                "_vi900_provider_probe",
                module_path
            )
        )

        if (
            spec is None
            or spec.loader is None
        ):
            raise RuntimeError(
                "module_spec_failed"
            )


        module = (
            importlib.util
            .module_from_spec(
                spec
            )
        )


        spec.loader.exec_module(
            module
        )


        function = getattr(
            module,
            function_name
        )


        output_queue.put({
            "_event":
                "FUNCTION_READY"
        })


        result = function(
            **kwargs
        )


        output_queue.put({
            "ok":
                True,

            "value":
                result,

            "worker_started":
                True,

            "function_called":
                True,
        })


    except Exception as exc:

        output_queue.put({
            "ok":
                False,

            "error":
                (
                    type(exc).__name__
                    + ": "
                    + str(exc)[:500]
                ),

            "worker_started":
                True,
        })


def _safe_context():

    methods = (
        multiprocessing
        .get_all_start_methods()
    )

    # Termux/Android:
    # fork avoids Python trying to reopen <stdin>.
    if "fork" in methods:
        return (
            multiprocessing
            .get_context("fork"),
            "fork"
        )

    # Do NOT silently fall back to spawn
    # while running through python - <<'PY'.
    return None, None


def execute(
    contract,
    query_text,
    timeout=12
):

    module = contract.get(
        "module"
    )

    function = contract.get(
        "function"
    )


    if not module or not function:
        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "contract_incomplete",

            "worker_started":
                False,

            "function_called":
                False,
        }


    module_path = (
        BASE
        / module
    ).resolve()


    try:
        module_path.relative_to(
            BASE.resolve()
        )

    except Exception:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "module_path_escape",

            "worker_started":
                False,

            "function_called":
                False,
        }


    if not module_path.exists():

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "module_missing",

            "worker_started":
                False,

            "function_called":
                False,
        }


    arg_result = build_args(
        contract,
        query_text
    )


    if (
        arg_result.get(
            "status"
        )
        != "ARGS_READY"
    ):

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                arg_result.get(
                    "reason"
                ),

            "worker_started":
                False,

            "function_called":
                False,
        }


    ctx, method = (
        _safe_context()
    )


    if ctx is None:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "safe_process_method_unavailable",

            "start_method":
                None,

            "worker_started":
                False,

            "function_called":
                False,
        }


    output_queue = (
        ctx.Queue()
    )


    process = ctx.Process(
        target=_worker,

        args=(
            str(
                module_path
            ),

            function,

            arg_result[
                "kwargs"
            ],

            output_queue,
        )
    )


    process.start()


    process.join(
        timeout
    )


    if process.is_alive():

        process.terminate()

        process.join(
            2
        )

        return {
            "version":
                VERSION,

            "status":
                "TIMEOUT",

            "reason":
                "provider_timeout",

            "start_method":
                method,

            "worker_started":
                True,

            "function_called":
                None,
        }


    events = []

    final_response = None


    while True:

        try:
            response = (
                output_queue
                .get_nowait()
            )

        except queue.Empty:
            break


        if "_event" in response:

            events.append(
                response[
                    "_event"
                ]
            )

        else:

            final_response = (
                response
            )


    worker_started = (
        "WORKER_STARTED"
        in events
    )

    function_ready = (
        "FUNCTION_READY"
        in events
    )


    if final_response is None:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                (
                    "provider_process_exited_without_result"
                ),

            "exitcode":
                process.exitcode,

            "start_method":
                method,

            "events":
                events,

            "worker_started":
                worker_started,

            "function_called":
                function_ready,
        }


    if not final_response.get(
        "ok"
    ):

        return {
            "version":
                VERSION,

            "status":
                "PROVIDER_ERROR",

            "reason":
                final_response.get(
                    "error"
                ),

            "exitcode":
                process.exitcode,

            "start_method":
                method,

            "events":
                events,

            "worker_started":
                worker_started,

            "function_called":
                function_ready,
        }


    return {
        "version":
            VERSION,

        "status":
            "SEARCH_RETURNED",

        "value":
            final_response.get(
                "value"
            ),

        "timeout_seconds":
            timeout,

        "start_method":
            method,

        "exitcode":
            process.exitcode,

        "events":
            events,

        "worker_started":
            worker_started,

        "function_called":
            True,
    }


def self_test():

    ctx, method = (
        _safe_context()
    )

    if (
        "fork"
        in multiprocessing
        .get_all_start_methods()
    ):
        assert method == "fork"

    assert VERSION == "8.95.1"

    print(
        "VI8.95.1 TERMUX SEARCH PROBE=PASS"
    )

    print(
        "AVAILABLE START METHODS:",
        multiprocessing
        .get_all_start_methods()
    )

    print(
        "SELECTED START METHOD:",
        method
    )


if __name__ == "__main__":
    self_test()
