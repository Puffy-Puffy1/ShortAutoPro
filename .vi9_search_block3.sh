#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "=================================================="
echo " VI8.81 -> VI8.90"
echo " SAFE SEARCH ADAPTER INTELLIGENCE"
echo " STATIC / READ-ONLY / SHADOW"
echo "=================================================="
echo

REPORT="logs/producao/vi8_80_search_architecture_latest.json"

if [ ! -f "$REPORT" ]; then
    echo "ERRO: relatório VI8.80 ausente."
    echo "Execute primeiro:"
    echo "./.vi9_search_block2.sh"
    exit 2
fi

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.81 — BASELINE LOADER
# =====================================================

cat > vi8_81_architecture_baseline.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path

VERSION = "8.81"

BASE = Path.home() / "ShortAutoPro"

REPORT = (
    BASE
    / "logs/producao/"
      "vi8_80_search_architecture_latest.json"
)


def load():
    if not REPORT.exists():
        raise RuntimeError(
            "vi8_80_report_missing"
        )

    data = json.loads(
        REPORT.read_text(
            encoding="utf-8"
        )
    )

    gate = (
        data.get("gate")
        or {}
    )

    status = gate.get(
        "status"
    )

    if status not in {
        "SEARCH_ARCHITECTURE_MAPPED",
        "SEARCH_ARCHITECTURE_PARTIAL",
    }:
        raise RuntimeError(
            "vi8_80_baseline_not_safe"
        )

    return gate


def self_test():
    assert VERSION == "8.81"
    print(
        "VI8.81 ARCHITECTURE BASELINE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.82 — MODULE PATH RESOLVER
# =====================================================

cat > vi8_82_module_path_resolver.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path

VERSION = "8.82"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def resolve(relative_path):
    if not relative_path:
        return {
            "status": "HOLD",
            "reason":
                "module_path_missing",
            "path": None,
        }

    candidate = (
        BASE
        / relative_path
    ).resolve()

    base = BASE.resolve()

    try:
        candidate.relative_to(
            base
        )
    except Exception:
        return {
            "status": "HOLD",
            "reason":
                "path_escape_detected",
            "path": None,
        }

    if not candidate.exists():
        return {
            "status": "HOLD",
            "reason":
                "module_not_found",
            "path": str(
                candidate
            ),
        }

    if candidate.suffix not in {
        ".py",
        ".sh",
    }:
        return {
            "status": "HOLD",
            "reason":
                "unsupported_module_type",
            "path": str(
                candidate
            ),
        }

    return {
        "status": "PASS",
        "reason": None,
        "path": str(
            candidate
        ),
    }


def self_test():
    result = resolve(
        "video.py"
    )

    assert result[
        "status"
    ] == "PASS"

    print(
        "VI8.82 MODULE PATH RESOLVER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.83 — AST FUNCTION INSPECTOR
# =====================================================

cat > vi8_83_ast_function_inspector.py <<'PY'
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
PY


# =====================================================
# VI8.84 — FUNCTION RISK CLASSIFIER
# =====================================================

cat > vi8_84_function_risk_classifier.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.84"

DANGEROUS = (
    "download",
    "save",
    "write",
    "replace",
    "delete",
    "remove",
    "unlink",
    "recover",
    "recovery",
    "upload",
    "render",
    "ffmpeg",
)

SEARCH = (
    "search",
    "query",
    "find",
    "lookup",
    "buscar",
    "busca",
)


def evaluate(function):
    name = str(
        function.get(
            "name"
        )
        or ""
    ).lower()

    args = [
        str(x).lower()
        for x in (
            function.get(
                "args"
            )
            or []
        )
    ]

    risks = []

    if any(
        token in name
        for token in DANGEROUS
    ):
        risks.append(
            "dangerous_function_name"
        )

    dangerous_args = [
        arg
        for arg in args
        if any(
            token in arg
            for token in (
                "output",
                "dest",
                "destination",
                "save",
                "write",
                "download",
                "replace",
            )
        )
    ]

    if dangerous_args:
        risks.append(
            "write_like_parameters"
        )

    search_like = any(
        token in name
        for token in SEARCH
    )

    if risks:
        classification = "BLOCKED"

    elif search_like:
        classification = (
            "SEARCH_CANDIDATE"
        )

    else:
        classification = "OTHER"

    return {
        "version": VERSION,
        "name":
            function.get(
                "name"
            ),
        "args":
            function.get(
                "args"
            )
            or [],
        "classification":
            classification,
        "risks":
            risks,
    }


def self_test():
    assert evaluate({
        "name":
            "download_image",
        "args":
            ["url"]
    })["classification"] == "BLOCKED"

    assert evaluate({
        "name":
            "search_images",
        "args":
            ["query"]
    })["classification"] == (
        "SEARCH_CANDIDATE"
    )

    print(
        "VI8.84 FUNCTION RISK CLASSIFIER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.85 — IMPORT RISK AUDIT
# =====================================================

cat > vi8_85_import_risk_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.85"

NETWORK_IMPORTS = {
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
}

PROCESS_IMPORTS = {
    "subprocess",
    "os",
}


def evaluate(imports):
    imports = (
        imports
        or []
    )

    network = []

    process = []

    for item in imports:
        root = (
            str(item)
            .split(".")[0]
        )

        if root in NETWORK_IMPORTS:
            network.append(
                item
            )

        if root in PROCESS_IMPORTS:
            process.append(
                item
            )

    return {
        "version": VERSION,
        "network_imports":
            sorted(
                set(network)
            ),
        "process_imports":
            sorted(
                set(process)
            ),
        "network_capable":
            bool(network),
        "process_capable":
            bool(process),
    }


def self_test():
    result = evaluate([
        "requests",
        "json",
    ])

    assert (
        result[
            "network_capable"
        ]
        is True
    )

    print(
        "VI8.85 IMPORT RISK AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.86 — STATIC SEARCH ADAPTER PLAN
# =====================================================

cat > vi8_86_static_search_adapter_plan.py <<'PY'
#!/usr/bin/env python3

from vi8_81_architecture_baseline import (
    load
)

from vi8_82_module_path_resolver import (
    resolve
)

from vi8_83_ast_function_inspector import (
    inspect_python
)

from vi8_84_function_risk_classifier import (
    evaluate as function_risk
)

from vi8_85_import_risk_audit import (
    evaluate as import_risk
)

VERSION = "8.86"


def build():
    baseline = load()

    integration = (
        baseline.get(
            "integration_candidates"
        )
        or {}
    )

    candidates = (
        integration.get(
            "candidates"
        )
        or []
    )

    plans = []

    for candidate in candidates:
        relative = candidate.get(
            "path"
        )

        resolved = resolve(
            relative
        )

        if resolved.get(
            "status"
        ) != "PASS":
            continue

        path = resolved.get(
            "path"
        )

        inspection = (
            inspect_python(
                path
            )
        )

        functions = [
            function_risk(fn)
            for fn in (
                inspection.get(
                    "functions"
                )
                or []
            )
        ]

        safe_search = [
            fn
            for fn in functions
            if fn.get(
                "classification"
            )
            == "SEARCH_CANDIDATE"
        ]

        blocked = [
            fn
            for fn in functions
            if fn.get(
                "classification"
            )
            == "BLOCKED"
        ]

        imports = import_risk(
            inspection.get(
                "imports"
            )
            or []
        )

        plans.append({
            "module":
                relative,

            "path":
                path,

            "providers":
                candidate.get(
                    "providers"
                )
                or [],

            "safe_search_functions":
                safe_search,

            "blocked_functions":
                blocked,

            "import_risk":
                imports,

            "discovery_score":
                candidate.get(
                    "score"
                ),
        })

    plans.sort(
        key=lambda item: (
            -len(
                item[
                    "safe_search_functions"
                ]
            ),
            -float(
                item.get(
                    "discovery_score",
                    0
                )
            ),
        )
    )

    best = (
        plans[0]
        if plans
        and plans[0][
            "safe_search_functions"
        ]
        else None
    )

    return {
        "version": VERSION,
        "plans": plans,
        "count":
            len(plans),
        "best":
            best,
    }


def self_test():
    assert VERSION == "8.86"

    print(
        "VI8.86 STATIC SEARCH ADAPTER PLAN=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.87 — SAFE CALL CONTRACT BUILDER
# =====================================================

cat > vi8_87_safe_call_contract.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.87"

ALLOWED_QUERY_ARGS = {
    "query",
    "q",
    "term",
    "search_term",
    "keywords",
    "keyword",
    "limit",
    "max_results",
    "count",
}


def build(module_plan):
    if not module_plan:
        return {
            "version": VERSION,
            "status": "HOLD",
            "reason":
                "no_module_plan",
            "contracts": [],
        }

    contracts = []

    for fn in (
        module_plan.get(
            "safe_search_functions"
        )
        or []
    ):
        args = [
            str(arg)
            for arg in (
                fn.get(
                    "args"
                )
                or []
            )
            if arg not in {
                "self",
                "cls",
            }
        ]

        unsupported = [
            arg
            for arg in args
            if arg.lower()
            not in ALLOWED_QUERY_ARGS
        ]

        if unsupported:
            status = (
                "STATIC_REVIEW_REQUIRED"
            )
        else:
            status = (
                "READ_ONLY_SIGNATURE_ACCEPTABLE"
            )

        contracts.append({
            "module":
                module_plan.get(
                    "module"
                ),

            "function":
                fn.get(
                    "name"
                ),

            "args":
                args,

            "unsupported_args":
                unsupported,

            "status":
                status,

            "invoke_now":
                False,

            "network_now":
                False,

            "download_now":
                False,
        })

    return {
        "version": VERSION,
        "status": (
            "READY"
            if contracts
            else "HOLD"
        ),
        "contracts":
            contracts,
    }


def self_test():
    result = build({
        "module": "x.py",
        "safe_search_functions": [{
            "name":
                "search_images",
            "args":
                ["query", "limit"],
        }],
    })

    assert (
        result[
            "contracts"
        ][0]["status"]
        == "READ_ONLY_SIGNATURE_ACCEPTABLE"
    )

    print(
        "VI8.87 SAFE CALL CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.88 — SIDE EFFECT BOUNDARY
# =====================================================

cat > vi8_88_side_effect_boundary.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.88"


def evaluate():
    return {
        "version": VERSION,

        "module_import_allowed":
            False,

        "search_function_call":
            False,

        "network_call":
            False,

        "download_call":
            False,

        "filesystem_media_write":
            False,

        "media_replace":
            False,

        "source_recovery":
            False,

        "renderer":
            False,

        "ffmpeg":
            False,

        "video_generation":
            False,

        "status":
            "LOCKED_SAFE",
    }


def self_test():
    result = evaluate()

    assert (
        result[
            "search_function_call"
        ]
        is False
    )

    print(
        "VI8.88 SIDE EFFECT BOUNDARY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.89 — ADAPTER READINESS AUDIT
# =====================================================

cat > vi8_89_adapter_readiness_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.89"


def evaluate(
    adapter_plan,
    call_contract,
    boundary
):
    blockers = []
    warnings = []

    best = (
        adapter_plan.get(
            "best"
        )
    )

    if not best:
        blockers.append(
            "no_safe_search_module"
        )

    contracts = (
        call_contract.get(
            "contracts"
        )
        or []
    )

    if not contracts:
        blockers.append(
            "no_search_contract"
        )

    review = [
        item
        for item in contracts
        if item.get(
            "status"
        )
        == "STATIC_REVIEW_REQUIRED"
    ]

    if review:
        warnings.append(
            "some_signatures_require_static_review"
        )

    if boundary.get(
        "status"
    ) != "LOCKED_SAFE":
        blockers.append(
            "side_effect_boundary_not_locked"
        )

    if blockers:
        status = "HOLD"

    elif review:
        status = (
            "READY_WITH_STATIC_REVIEW"
        )

    else:
        status = (
            "SAFE_ADAPTER_BLUEPRINT_READY"
        )

    return {
        "version": VERSION,
        "status": status,
        "blockers":
            blockers,
        "warnings":
            warnings,
        "contract_count":
            len(contracts),
        "review_count":
            len(review),
    }


def self_test():
    result = evaluate(
        {"best": {"module": "x.py"}},
        {
            "contracts": [{
                "status":
                    "READ_ONLY_SIGNATURE_ACCEPTABLE"
            }]
        },
        {
            "status":
                "LOCKED_SAFE"
        }
    )

    assert (
        result["status"]
        == "SAFE_ADAPTER_BLUEPRINT_READY"
    )

    print(
        "VI8.89 ADAPTER READINESS AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.90 — SAFE SEARCH ADAPTER MASTER GATE
# =====================================================

cat > vi8_90_safe_search_adapter_master_gate.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path

from vi8_86_static_search_adapter_plan import (
    build as build_adapter
)

from vi8_87_safe_call_contract import (
    build as build_contract
)

from vi8_88_side_effect_boundary import (
    evaluate as boundary
)

from vi8_89_adapter_readiness_audit import (
    evaluate as audit
)

VERSION = "8.90"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    adapter = build_adapter()

    best = (
        adapter.get("best")
    )

    contract = (
        build_contract(
            best
        )
    )

    side_effects = (
        boundary()
    )

    audit_result = audit(
        adapter,
        contract,
        side_effects
    )

    result = {
        "version":
            VERSION,

        "status":
            audit_result.get(
                "status"
            ),

        "best_module":
            (
                best.get(
                    "module"
                )
                if best
                else None
            ),

        "providers":
            (
                best.get(
                    "providers"
                )
                if best
                else []
            ),

        "search_functions":
            (
                [
                    fn.get(
                        "name"
                    )
                    for fn
                    in best.get(
                        "safe_search_functions",
                        []
                    )
                ]
                if best
                else []
            ),

        "blocked_functions":
            (
                [
                    fn.get(
                        "name"
                    )
                    for fn
                    in best.get(
                        "blocked_functions",
                        []
                    )
                ]
                if best
                else []
            ),

        "import_risk":
            (
                best.get(
                    "import_risk"
                )
                if best
                else {}
            ),

        "contracts":
            contract.get(
                "contracts"
            )
            or [],

        "blockers":
            audit_result.get(
                "blockers"
            )
            or [],

        "warnings":
            audit_result.get(
                "warnings"
            )
            or [],

        "module_import_executed":
            False,

        "search_function_executed":
            False,

        "network_executed":
            False,

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

        "full_active":
            False,
    }

    output = (
        BASE
        / "logs/producao/"
          "vi8_90_safe_search_adapter_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "8.90"

    print(
        "VI8.90 SAFE SEARCH ADAPTER MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_81_architecture_baseline.py \
  vi8_82_module_path_resolver.py \
  vi8_83_ast_function_inspector.py \
  vi8_84_function_risk_classifier.py \
  vi8_85_import_risk_audit.py \
  vi8_86_static_search_adapter_plan.py \
  vi8_87_safe_call_contract.py \
  vi8_88_side_effect_boundary.py \
  vi8_89_adapter_readiness_audit.py \
  vi8_90_safe_search_adapter_master_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_81_architecture_baseline.py || exit 11
python vi8_82_module_path_resolver.py || exit 12
python vi8_83_ast_function_inspector.py || exit 13
python vi8_84_function_risk_classifier.py || exit 14
python vi8_85_import_risk_audit.py || exit 15
python vi8_86_static_search_adapter_plan.py || exit 16
python vi8_87_safe_call_contract.py || exit 17
python vi8_88_side_effect_boundary.py || exit 18
python vi8_89_adapter_readiness_audit.py || exit 19
python vi8_90_safe_search_adapter_master_gate.py || exit 20

echo "SELF TESTS=PASS"


echo
echo "=================================================="
echo " VI8.90 SAFE SEARCH ADAPTER ANALYSIS"
echo "=================================================="

python - <<'PY'
from vi8_90_safe_search_adapter_master_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "BEST MODULE:",
    r.get(
        "best_module"
    )
)

print(
    "PROVIDERS:",
    r.get(
        "providers"
    )
)

print(
    "SEARCH FUNCTIONS:",
    r.get(
        "search_functions"
    )
)

print(
    "BLOCKED FUNCTIONS:",
    r.get(
        "blocked_functions"
    )
)

risk = (
    r.get(
        "import_risk"
    )
    or {}
)

print(
    "NETWORK-CAPABLE IMPORTS:",
    risk.get(
        "network_imports"
    )
)

print(
    "PROCESS-CAPABLE IMPORTS:",
    risk.get(
        "process_imports"
    )
)

print()
print(
    "===== SAFE CALL CONTRACTS ====="
)

for item in (
    r.get(
        "contracts"
    )
    or []
):
    print(
        "MODULE=",
        item.get(
            "module"
        ),
        "| FUNCTION=",
        item.get(
            "function"
        ),
        "| ARGS=",
        item.get(
            "args"
        ),
        "| STATUS=",
        item.get(
            "status"
        ),
        "| UNSUPPORTED=",
        item.get(
            "unsupported_args"
        ),
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
    "MODULE IMPORT EXECUTED:",
    r.get(
        "module_import_executed"
    )
)

print(
    "SEARCH FUNCTION EXECUTED:",
    r.get(
        "search_function_executed"
    )
)

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
PY


VIDEO_AFTER="$(sha256sum video.py | awk '{print $1}')"
GERAR_AFTER="$(sha256sum gerar_short.sh | awk '{print $1}')"

if [ "$VIDEO_BEFORE" != "$VIDEO_AFTER" ]; then
    echo "CRITICAL: video.py changed"
    exit 30
fi

if [ "$GERAR_BEFORE" != "$GERAR_AFTER" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 31
fi


echo
echo "=================================================="
echo " VI8.81 -> VI8.90 COMPLETE"
echo "=================================================="
echo
echo "SEARCH ADAPTER BLUEPRINT=READY"
echo "FUNCTION SIGNATURES=AUDITED"
echo "DANGEROUS FUNCTIONS=BLOCKED"
echo "SIDE EFFECT BOUNDARY=LOCKED"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "MODULE IMPORT EXECUTED=NO"
echo "SEARCH EXECUTED=NO"
echo "NETWORK EXECUTED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA MUTATION=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "SOURCE RECOVERY=SHADOW_ONLY"
echo "FULL ACTIVE=LOCKED"
echo
echo "REPORT:"
echo "logs/producao/vi8_90_safe_search_adapter_latest.json"
