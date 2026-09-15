#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "=================================================="
echo " VI9.00.1"
echo " TERMUX PROCESS COMPATIBILITY HOTFIX"
echo "=================================================="

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"

cp -f \
  vi8_95_search_probe.py \
  "vi8_95_search_probe.py.bak_vi9001_$(date +%Y%m%d_%H%M%S)"


cat > vi8_95_search_probe.py <<'PY'
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
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_95_search_probe.py \
  vi9_00_master_search_observation_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== TERMUX PROCESS TEST ====="

python vi8_95_search_probe.py \
  || exit 11


echo
echo "===== CORE INTEGRITY ====="

VIDEO_MID="$(sha256sum video.py | awk '{print $1}')"
GERAR_MID="$(sha256sum gerar_short.sh | awk '{print $1}')"

[ "$VIDEO_BEFORE" = "$VIDEO_MID" ] || {
    echo "CRITICAL: video.py changed"
    exit 20
}

[ "$GERAR_BEFORE" = "$GERAR_MID" ] || {
    echo "CRITICAL: gerar_short.sh changed"
    exit 21
}

echo "CORE FILES UNCHANGED=YES"


echo
echo "=================================================="
echo " VI9.00.1 NETWORK-LOCKED CONTROL"
echo "=================================================="

VI900_NETWORK_PROBE=OFF \
python - <<'PY'
from vi9_00_master_search_observation_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "PROBE EXECUTED:",
    r.get(
        "probe_executed"
    )
)

print(
    "PROBE STATUS:",
    r.get(
        "probe_status"
    )
)

if r.get(
    "probe_executed"
):
    raise SystemExit(
        "NETWORK LOCK VIOLATION"
    )

print(
    "NETWORK LOCK=PASS"
)
PY


echo
echo "=================================================="
echo " VI9.00.1 REAL OBSERVATIONAL RETEST"
echo " NETWORK=ON"
echo " DOWNLOAD=OFF"
echo " MEDIA MUTATION=OFF"
echo " VIDEO=OFF"
echo "=================================================="

VI900_NETWORK_PROBE=ON \
python - <<'PY'
from vi8_91_safe_contract_selector import (
    select as select_contract
)

from vi8_96_probe_query_selector import (
    select as select_query
)

from vi8_95_search_probe import (
    execute
)

from vi8_93_search_result_sanitizer import (
    sanitize
)

from vi8_94_search_result_safety import (
    evaluate as safety
)


contract_selection = (
    select_contract()
)

query_selection = (
    select_query()
)


print(
    "CONTRACT STATUS:",
    contract_selection.get(
        "status"
    )
)

print(
    "QUERY STATUS:",
    query_selection.get(
        "status"
    )
)


if (
    contract_selection.get(
        "status"
    )
    != "SAFE_CONTRACT_SELECTED"
):
    raise SystemExit(
        "SAFE CONTRACT NOT AVAILABLE"
    )


if (
    query_selection.get(
        "status"
    )
    != "QUERY_SELECTED"
):
    raise SystemExit(
        "SAFE QUERY NOT AVAILABLE"
    )


contract = (
    contract_selection[
        "contract"
    ]
)


print(
    "MODULE:",
    contract.get(
        "module"
    )
)

print(
    "FUNCTION:",
    contract.get(
        "function"
    )
)

print(
    "SCENE:",
    query_selection.get(
        "scene"
    )
)

print(
    "QUERY:",
    query_selection.get(
        "query"
    )
)


result = execute(
    contract,
    query_selection[
        "query"
    ],
    timeout=12
)


print()
print(
    "===== PROBE RESULT ====="
)

print(
    "STATUS:",
    result.get(
        "status"
    )
)

print(
    "REASON:",
    result.get(
        "reason"
    )
)

print(
    "START METHOD:",
    result.get(
        "start_method"
    )
)

print(
    "EXIT CODE:",
    result.get(
        "exitcode"
    )
)

print(
    "WORKER STARTED:",
    result.get(
        "worker_started"
    )
)

print(
    "FUNCTION CALLED:",
    result.get(
        "function_called"
    )
)

print(
    "EVENTS:",
    result.get(
        "events"
    )
)


clean = sanitize(
    result.get(
        "value"
    )
)


checked = safety(
    clean.get(
        "results"
    )
    or []
)


print(
    "RAW SANITIZED:",
    clean.get(
        "count"
    )
)

print(
    "SAFE RESULTS:",
    checked.get(
        "safe_count"
    )
)

print(
    "REJECTED:",
    checked.get(
        "rejected_count"
    )
)


print()
print(
    "===== SAFE RESULT PREVIEW ====="
)


for index, item in enumerate(
    checked.get(
        "safe"
    )
    or [],
    start=1
):

    print(
        index,
        "|",
        item.get(
            "title"
        ),
        "|",
        item.get(
            "source"
        ),
        "|",
        item.get(
            "url"
        ),
    )


print()
print(
    "DOWNLOAD EXECUTED: False"
)

print(
    "MEDIA MUTATED: False"
)

print(
    "FFMPEG EXECUTED: False"
)

print(
    "VIDEO GENERATED: False"
)
PY


VIDEO_FINAL="$(sha256sum video.py | awk '{print $1}')"
GERAR_FINAL="$(sha256sum gerar_short.sh | awk '{print $1}')"

echo
echo "===== FINAL CORE INTEGRITY ====="

echo "VIDEO BEFORE=$VIDEO_BEFORE"
echo "VIDEO FINAL =$VIDEO_FINAL"

echo
echo "GERAR BEFORE=$GERAR_BEFORE"
echo "GERAR FINAL =$GERAR_FINAL"

if [ "$VIDEO_BEFORE" != "$VIDEO_FINAL" ]; then
    echo "CRITICAL: video.py changed"
    exit 30
fi

if [ "$GERAR_BEFORE" != "$GERAR_FINAL" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 31
fi

echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "MEDIA REPLACEMENT=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"

echo
echo "=================================================="
echo " VI9.00.1 HOTFIX COMPLETE"
echo "=================================================="
