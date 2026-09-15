#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "=================================================="
echo " VI8.91 -> VI9.00"
echo " CONTROLLED SEARCH PROBE"
echo " OBSERVATIONAL ONLY"
echo "=================================================="
echo
echo "VIDEO GENERATION=OFF"
echo "DOWNLOAD=OFF"
echo "MEDIA REPLACEMENT=OFF"
echo "FFMPEG=OFF"
echo

REPORT="logs/producao/vi8_90_safe_search_adapter_latest.json"

if [ ! -f "$REPORT" ]; then
    echo "ERRO: VI8.90 report missing."
    exit 2
fi

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.91 — SAFE CONTRACT SELECTOR
# =====================================================

cat > vi8_91_safe_contract_selector.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.91"

BASE = Path.home() / "ShortAutoPro"

REPORT = (
    BASE
    / "logs/producao/"
      "vi8_90_safe_search_adapter_latest.json"
)


def select():

    data = json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    )

    gate = (
        data.get("gate")
        or {}
    )

    if gate.get("status") not in {
        "SAFE_ADAPTER_BLUEPRINT_READY",
        "READY_WITH_STATIC_REVIEW",
    }:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "vi890_not_ready",
            "contract": None,
        }

    contracts = (
        gate.get("contracts")
        or []
    )

    safe = [
        item
        for item in contracts
        if item.get("status")
        == "READ_ONLY_SIGNATURE_ACCEPTABLE"
    ]

    if not safe:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "no_safe_contract",
            "contract": None,
        }

    return {
        "version": VERSION,
        "status":
            "SAFE_CONTRACT_SELECTED",
        "reason": None,
        "contract":
            safe[0],
        "providers":
            gate.get("providers")
            or [],
    }


def self_test():
    assert VERSION == "8.91"

    print(
        "VI8.91 SAFE CONTRACT SELECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.92 — QUERY ARGUMENT BUILDER
# =====================================================

cat > vi8_92_query_argument_builder.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.92"


def build(contract, query):

    args = (
        contract.get("args")
        or []
    )

    kwargs = {}

    query_assigned = False

    for arg in args:

        low = str(arg).lower()

        if low in {
            "query",
            "q",
            "term",
            "search_term",
            "keywords",
            "keyword",
        }:
            kwargs[arg] = query
            query_assigned = True

        elif low in {
            "limit",
            "max_results",
            "count",
        }:
            kwargs[arg] = 5

        else:
            return {
                "version": VERSION,
                "status": "HOLD",
                "reason":
                    f"unsupported_arg:{arg}",
                "kwargs": {},
            }

    if not query_assigned:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "query_argument_missing",
            "kwargs": {},
        }

    return {
        "version": VERSION,
        "status":
            "ARGS_READY",
        "reason": None,
        "kwargs":
            kwargs,
    }


def self_test():

    result = build(
        {
            "args": [
                "query",
                "limit",
            ]
        },
        "test"
    )

    assert (
        result["status"]
        == "ARGS_READY"
    )

    print(
        "VI8.92 QUERY ARGUMENT BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.93 — RESULT SANITIZER
# =====================================================

cat > vi8_93_search_result_sanitizer.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.93"


def sanitize(value):

    results = []

    if value is None:
        raw = []

    elif isinstance(
        value,
        list
    ):
        raw = value

    elif isinstance(
        value,
        tuple
    ):
        raw = list(value)

    elif isinstance(
        value,
        dict
    ):
        for key in (
            "results",
            "items",
            "images",
            "data",
        ):
            if isinstance(
                value.get(key),
                list
            ):
                raw = value[key]
                break
        else:
            raw = [value]

    else:
        raw = []


    for item in raw[:10]:

        if isinstance(
            item,
            str
        ):
            results.append({
                "url":
                    item,
                "title":
                    None,
                "source":
                    None,
            })

        elif isinstance(
            item,
            dict
        ):
            url = (
                item.get("url")
                or item.get(
                    "image_url"
                )
                or item.get(
                    "src"
                )
                or item.get(
                    "thumbnail"
                )
            )

            results.append({
                "url":
                    url,

                "title":
                    item.get(
                        "title"
                    )
                    or item.get(
                        "name"
                    ),

                "source":
                    item.get(
                        "source"
                    )
                    or item.get(
                        "provider"
                    ),

                "width":
                    item.get(
                        "width"
                    ),

                "height":
                    item.get(
                        "height"
                    ),
            })


    return {
        "version":
            VERSION,

        "count":
            len(results),

        "results":
            results,
    }


def self_test():

    result = sanitize([
        {
            "url":
                "https://example.com/a.jpg"
        }
    ])

    assert result["count"] == 1

    print(
        "VI8.93 RESULT SANITIZER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.94 — RESULT SAFETY AUDIT
# =====================================================

cat > vi8_94_search_result_safety.py <<'PY'
#!/usr/bin/env python3

from urllib.parse import urlparse

VERSION = "8.94"


def evaluate(results):

    safe = []
    rejected = []


    for item in (
        results or []
    ):

        url = str(
            item.get("url")
            or ""
        ).strip()

        try:
            parsed = urlparse(
                url
            )
        except Exception:
            parsed = None


        if (
            not parsed
            or parsed.scheme not in {
                "http",
                "https",
            }
            or not parsed.netloc
        ):
            rejected.append({
                "item":
                    item,
                "reason":
                    "invalid_url",
            })

            continue


        safe.append(
            item
        )


    return {
        "version":
            VERSION,

        "safe":
            safe,

        "safe_count":
            len(safe),

        "rejected":
            rejected,

        "rejected_count":
            len(rejected),
    }


def self_test():

    result = evaluate([
        {
            "url":
                "https://example.com/a.jpg"
        },
        {
            "url":
                "/local/file.jpg"
        },
    ])

    assert result[
        "safe_count"
    ] == 1

    print(
        "VI8.94 RESULT SAFETY AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.95 — SEARCH PROBE SUBPROCESS
# =====================================================

cat > vi8_95_search_probe.py <<'PY'
#!/usr/bin/env python3

import importlib.util
import json
import multiprocessing
import os
import queue
from pathlib import Path

from vi8_92_query_argument_builder import (
    build as build_args
)

VERSION = "8.95"

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

        # Explicitly mark child as observational.
        os.environ[
            "VI900_SEARCH_PROBE"
        ] = "ON"

        os.environ[
            "VI900_DOWNLOAD_ALLOWED"
        ] = "OFF"

        os.environ[
            "VI900_MEDIA_WRITE_ALLOWED"
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

        result = function(
            **kwargs
        )

        output_queue.put({
            "ok":
                True,

            "value":
                result,
        })

    except Exception as exc:

        output_queue.put({
            "ok":
                False,

            "error":
                type(exc).__name__
                + ": "
                + str(exc)[:300],
        })


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
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "contract_incomplete",
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
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "module_path_escape",
        }


    arg_result = build_args(
        contract,
        query_text
    )

    if arg_result.get(
        "status"
    ) != "ARGS_READY":

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                arg_result.get(
                    "reason"
                ),
        }


    ctx = (
        multiprocessing
        .get_context(
            "spawn"
        )
    )

    output_queue = (
        ctx.Queue()
    )

    process = ctx.Process(
        target=_worker,
        args=(
            str(module_path),
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
        process.join()

        return {
            "version": VERSION,
            "status": "TIMEOUT",
            "reason":
                "provider_timeout",
        }


    try:
        response = (
            output_queue.get_nowait()
        )

    except queue.Empty:

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "provider_no_result",
        }


    if not response.get(
        "ok"
    ):

        return {
            "version": VERSION,
            "status":
                "PROVIDER_ERROR",

            "reason":
                response.get(
                    "error"
                ),
        }


    return {
        "version": VERSION,
        "status":
            "SEARCH_RETURNED",

        "value":
            response.get(
                "value"
            ),

        "timeout_seconds":
            timeout,
    }


def self_test():

    assert VERSION == "8.95"

    print(
        "VI8.95 SEARCH PROBE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.96 — PROBE QUERY SELECTOR
# =====================================================

cat > vi8_96_probe_query_selector.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.96"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

REPORT = (
    BASE
    / "logs/producao/"
      "vi8_70_search_shadow_foundation_latest.json"
)


def select():

    if not REPORT.exists():

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "vi870_report_missing",
        }


    data = json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    )

    gate = (
        data.get("gate")
        or {}
    )

    compiled = (
        gate.get("compiled")
        or {}
    )

    plans = (
        compiled.get("plans")
        or []
    )


    if not plans:

        return {
            "version": VERSION,
            "status":
                "NO_SEARCH_REQUIRED",
            "reason": None,
        }


    first = plans[0]

    queries = (
        first.get("queries")
        or []
    )

    if not queries:

        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "query_missing",
        }


    return {
        "version": VERSION,

        "status":
            "QUERY_SELECTED",

        "scene":
            first.get(
                "scene"
            ),

        "category":
            first.get(
                "category"
            ),

        "query":
            queries[0],

        "priority":
            first.get(
                "priority"
            ),
    }


def self_test():

    assert VERSION == "8.96"

    print(
        "VI8.96 PROBE QUERY SELECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.97 — OBSERVATIONAL PROBE GATE
# =====================================================

cat > vi8_97_observational_probe_gate.py <<'PY'
#!/usr/bin/env python3

import os

VERSION = "8.97"


def evaluate(
    contract_selection,
    query_selection
):

    blockers = []


    if (
        contract_selection.get(
            "status"
        )
        != "SAFE_CONTRACT_SELECTED"
    ):

        blockers.append(
            "safe_contract_missing"
        )


    if query_selection.get(
        "status"
    ) not in {
        "QUERY_SELECTED",
        "NO_SEARCH_REQUIRED",
    }:

        blockers.append(
            "safe_query_missing"
        )


    network_enabled = (
        os.getenv(
            "VI900_NETWORK_PROBE",
            "OFF"
        ).upper()
        == "ON"
    )


    if blockers:

        status = "HOLD"

    elif (
        query_selection.get(
            "status"
        )
        == "NO_SEARCH_REQUIRED"
    ):

        status = (
            "NO_SEARCH_REQUIRED"
        )

    elif network_enabled:

        status = (
            "CONTROLLED_PROBE_ALLOWED"
        )

    else:

        status = (
            "PROBE_READY_NETWORK_LOCKED"
        )


    return {
        "version": VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "network_enabled":
            network_enabled,

        "download_allowed":
            False,

        "media_write_allowed":
            False,

        "renderer_allowed":
            False,

        "ffmpeg_allowed":
            False,
    }


def self_test():

    assert VERSION == "8.97"

    print(
        "VI8.97 OBSERVATIONAL PROBE GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.98 — PROBE RESULT AUDIT
# =====================================================

cat > vi8_98_probe_result_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.98"


def evaluate(
    probe_status,
    safety
):

    blockers = []
    warnings = []


    if probe_status in {
        "SEARCH_RETURNED",
        "NETWORK_LOCKED",
        "NO_SEARCH_REQUIRED",
    }:
        pass

    elif probe_status in {
        "TIMEOUT",
        "PROVIDER_ERROR",
        "HOLD",
    }:

        warnings.append(
            "provider_probe_not_successful"
        )


    if safety.get(
        "download_allowed"
    ):

        blockers.append(
            "download_not_locked"
        )


    if safety.get(
        "media_write_allowed"
    ):

        blockers.append(
            "media_write_not_locked"
        )


    return {
        "version": VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    result = evaluate(
        "SEARCH_RETURNED",
        {
            "download_allowed":
                False,

            "media_write_allowed":
                False,
        }
    )

    assert result[
        "status"
    ] == "PASS"

    print(
        "VI8.98 PROBE RESULT AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.99 — VI9 RELEASE CANDIDATE
# =====================================================

cat > vi8_99_vi9_release_candidate.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.99"


def evaluate(
    audit,
    safe_result_count,
    probe_executed
):

    blockers = (
        audit.get(
            "blockers"
        )
        or []
    )

    warnings = (
        audit.get(
            "warnings"
        )
        or []
    )


    if blockers:

        status = "HOLD"


    elif not probe_executed:

        status = (
            "READY_FOR_CONTROLLED_SEARCH_PROBE"
        )


    elif safe_result_count > 0:

        status = (
            "VI9_SEARCH_OBSERVATION_CANDIDATE"
        )


    else:

        status = (
            "SEARCH_PROVIDER_TUNING_REQUIRED"
        )


    return {
        "version": VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "safe_result_count":
            safe_result_count,

        "download_activation":
            False,

        "media_replacement":
            False,

        "renderer_activation":
            False,

        "full_active":
            False,
    }


def self_test():

    assert VERSION == "8.99"

    print(
        "VI8.99 VI9 RELEASE CANDIDATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI9.00 — MASTER SEARCH OBSERVATION GATE
# =====================================================

cat > vi9_00_master_search_observation_gate.py <<'PY'
#!/usr/bin/env python3

import json
import os

from datetime import datetime
from pathlib import Path

from vi8_91_safe_contract_selector import (
    select as select_contract
)

from vi8_96_probe_query_selector import (
    select as select_query
)

from vi8_97_observational_probe_gate import (
    evaluate as probe_gate
)

from vi8_95_search_probe import (
    execute as execute_probe
)

from vi8_93_search_result_sanitizer import (
    sanitize
)

from vi8_94_search_result_safety import (
    evaluate as result_safety
)

from vi8_98_probe_result_audit import (
    evaluate as probe_audit
)

from vi8_99_vi9_release_candidate import (
    evaluate as release_candidate
)


VERSION = "9.00"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    contract_selection = (
        select_contract()
    )

    query_selection = (
        select_query()
    )

    safety = probe_gate(
        contract_selection,
        query_selection
    )


    probe_executed = False

    raw_probe = {
        "status":
            "NETWORK_LOCKED"
    }


    if (
        safety.get(
            "status"
        )
        == "CONTROLLED_PROBE_ALLOWED"
    ):

        probe_executed = True

        raw_probe = execute_probe(
            contract_selection[
                "contract"
            ],
            query_selection[
                "query"
            ],
            timeout=12
        )


    elif (
        safety.get(
            "status"
        )
        == "NO_SEARCH_REQUIRED"
    ):

        raw_probe = {
            "status":
                "NO_SEARCH_REQUIRED"
        }


    sanitized = sanitize(
        raw_probe.get(
            "value"
        )
    )


    safe_results = (
        result_safety(
            sanitized.get(
                "results"
            )
            or []
        )
    )


    audit = probe_audit(
        raw_probe.get(
            "status"
        ),
        safety
    )


    release = release_candidate(
        audit,
        safe_results.get(
            "safe_count",
            0
        ),
        probe_executed
    )


    result = {
        "version":
            VERSION,

        "status":
            release.get(
                "status"
            ),

        "contract":
            contract_selection,

        "query":
            query_selection,

        "safety":
            safety,

        "probe_executed":
            probe_executed,

        "probe_status":
            raw_probe.get(
                "status"
            ),

        "probe_reason":
            raw_probe.get(
                "reason"
            ),

        "safe_result_count":
            safe_results.get(
                "safe_count"
            ),

        "rejected_result_count":
            safe_results.get(
                "rejected_count"
            ),

        "safe_results":
            safe_results.get(
                "safe"
            )
            or [],

        "blockers":
            release.get(
                "blockers"
            ),

        "warnings":
            release.get(
                "warnings"
            ),

        "network_executed":
            probe_executed,

        "download_executed":
            False,

        "media_mutated":
            False,

        "source_recovery":
            "SHADOW_ONLY",

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "full_active_authorized":
            False,
    }


    output = (
        BASE
        / "logs/producao/"
          "vi9_00_master_search_observation_latest.json"
    )


    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    output.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


def self_test():

    assert VERSION == "9.00"

    print(
        "VI9.00 MASTER SEARCH OBSERVATION GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_91_safe_contract_selector.py \
  vi8_92_query_argument_builder.py \
  vi8_93_search_result_sanitizer.py \
  vi8_94_search_result_safety.py \
  vi8_95_search_probe.py \
  vi8_96_probe_query_selector.py \
  vi8_97_observational_probe_gate.py \
  vi8_98_probe_result_audit.py \
  vi8_99_vi9_release_candidate.py \
  vi9_00_master_search_observation_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_91_safe_contract_selector.py || exit 11
python vi8_92_query_argument_builder.py || exit 12
python vi8_93_search_result_sanitizer.py || exit 13
python vi8_94_search_result_safety.py || exit 14
python vi8_95_search_probe.py || exit 15
python vi8_96_probe_query_selector.py || exit 16
python vi8_97_observational_probe_gate.py || exit 17
python vi8_98_probe_result_audit.py || exit 18
python vi8_99_vi9_release_candidate.py || exit 19
python vi9_00_master_search_observation_gate.py || exit 20

echo "SELF TESTS=PASS"


# =====================================================
# FIRST PASS — NETWORK LOCKED
# =====================================================

echo
echo "=================================================="
echo " VI9.00 CONTROL PASS"
echo " NETWORK MUST REMAIN LOCKED"
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

print(
    "BLOCKERS:",
    r.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    r.get(
        "warnings"
    )
)

if r.get(
    "probe_executed"
):
    raise SystemExit(
        "CONTROL PASS NETWORK VIOLATION"
    )

print(
    "CONTROL NETWORK LOCK=PASS"
)
PY


# =====================================================
# REAL OBSERVATIONAL PROBE
# Network only. NO download.
# =====================================================

echo
echo "=================================================="
echo " VI9.00 CONTROLLED REAL SEARCH PROBE"
echo " NETWORK=ON"
echo " DOWNLOAD=OFF"
echo " MEDIA WRITE=OFF"
echo "=================================================="

VI900_NETWORK_PROBE=ON \
python - <<'PY'
from vi9_00_master_search_observation_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

query = (
    r.get("query")
    or {}
)

print(
    "SCENE:",
    query.get("scene")
)

print(
    "QUERY:",
    query.get("query")
)

contract = (
    r.get("contract")
    or {}
)

c = (
    contract.get("contract")
    or {}
)

print(
    "MODULE:",
    c.get("module")
)

print(
    "FUNCTION:",
    c.get("function")
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

print(
    "PROBE REASON:",
    r.get(
        "probe_reason"
    )
)

print(
    "SAFE RESULTS:",
    r.get(
        "safe_result_count"
    )
)

print(
    "REJECTED RESULTS:",
    r.get(
        "rejected_result_count"
    )
)

print()
print(
    "===== OBSERVED SEARCH RESULTS ====="
)

for index, item in enumerate(
    r.get(
        "safe_results"
    )
    or [],
    start=1
):
    print(
        index,
        "| title=",
        item.get("title"),
        "| source=",
        item.get("source"),
        "| url=",
        item.get("url"),
    )

print()
print(
    "BLOCKERS:",
    r.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    r.get(
        "warnings"
    )
)

print()
print(
    "NETWORK EXECUTED:",
    r.get(
        "network_executed"
    )
)

print(
    "DOWNLOAD EXECUTED:",
    r.get(
        "download_executed"
    )
)

print(
    "MEDIA MUTATED:",
    r.get(
        "media_mutated"
    )
)

print(
    "FFMPEG EXECUTED:",
    r.get(
        "ffmpeg_executed"
    )
)

print(
    "VIDEO GENERATED:",
    r.get(
        "video_generated"
    )
)

print(
    "FULL ACTIVE:",
    r.get(
        "full_active_authorized"
    )
)
PY


# =====================================================
# FINAL CORE INTEGRITY
# =====================================================

VIDEO_AFTER="$(sha256sum video.py | awk '{print $1}')"
GERAR_AFTER="$(sha256sum gerar_short.sh | awk '{print $1}')"

echo
echo "===== FINAL CORE INTEGRITY ====="
echo "VIDEO BEFORE=$VIDEO_BEFORE"
echo "VIDEO AFTER =$VIDEO_AFTER"
echo
echo "GERAR BEFORE=$GERAR_BEFORE"
echo "GERAR AFTER =$GERAR_AFTER"

if [ "$VIDEO_BEFORE" != "$VIDEO_AFTER" ]; then
    echo "CRITICAL: video.py changed"
    exit 30
fi

if [ "$GERAR_BEFORE" != "$GERAR_AFTER" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 31
fi

echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA REPLACEMENT=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"

echo
echo "=================================================="
echo " VI8.91 -> VI9.00 COMPLETE"
echo "=================================================="
echo
echo "CONTROLLED SEARCH PROBE=INSTALLED"
echo "TIMEOUT=12s"
echo "MAX RAW RESULTS=10"
echo "DOWNLOAD=LOCKED"
echo "MEDIA WRITE=LOCKED"
echo "RENDERER=LOCKED"
echo
echo "REPORT:"
echo "logs/producao/vi9_00_master_search_observation_latest.json"
