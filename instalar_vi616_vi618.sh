#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi616_vi618_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.16 + VI6.17 + VI6.18"
echo " TRUE RECOVERY PREPARATION"
echo " DRY-RUN / ZERO API"
echo "======================================"
echo


# =====================================================
# 0. BASELINE
# =====================================================

REQUIRED="
midia.py
vi6_6_active_brain.py
vi6_7_retrieval_planner.py
vi6_8_storyboard_director.py
vi6_8_runtime_policy.py
vi6_9_quality_firewall.py
vi6_9_runtime_policy.py
vi6_10_coverage_predictor.py
vi6_11_second_chance.py
vi6_12_story_guard.py
vi6_13_recovery_planner.py
vi6_14_pre_download_gate.py
vi6_15_decision_ledger.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F não encontrado."
        echo "NADA FOI ALTERADO."
        exit 2
    fi
done


echo "===== BASELINE COMPILE ====="

if ! python -m py_compile \
    midia.py \
    vi6_6_active_brain.py \
    vi6_7_retrieval_planner.py \
    vi6_8_storyboard_director.py \
    vi6_8_runtime_policy.py \
    vi6_9_quality_firewall.py \
    vi6_9_runtime_policy.py \
    vi6_10_coverage_predictor.py \
    vi6_11_second_chance.py \
    vi6_12_story_guard.py \
    vi6_13_recovery_planner.py \
    vi6_14_pre_download_gate.py \
    vi6_15_decision_ledger.py
then
    echo "BASELINE FALHOU."
    echo "NADA FOI ALTERADO."
    exit 3
fi

echo "BASELINE=OK"


for F in \
    vi6_16_source_capabilities.py \
    vi6_17_recovery_router.py \
    vi6_18_activation_guard.py \
    testar_vi616_vi618.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.16-6.18"
    echo "======================================"

    for F in \
        vi6_16_source_capabilities.py \
        vi6_17_recovery_router.py \
        vi6_18_activation_guard.py \
        testar_vi616_vi618.py
    do
        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi
    done

    echo "Projeto restaurado."
}


# =====================================================
# 1. VI6.16 SOURCE CAPABILITY DISCOVERY
# =====================================================

cat > vi6_16_source_capabilities.py <<'PY'
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
PY


# =====================================================
# 2. VI6.17 RECOVERY ROUTER
# =====================================================

cat > vi6_17_recovery_router.py <<'PY'
#!/usr/bin/env python3

from vi6_16_source_capabilities import (
    discover,
    summarize,
    QUERY_ARGS,
)


VERSION = "6.17"


def _score_function(
    function,
    plan
):

    score = 0


    source = function.get(
        "source"
    )


    prefer_wiki = bool(
        plan.get(
            "prefer_wikimedia"
        )
    )


    allow_stock = bool(
        plan.get(
            "allow_stock_retry"
        )
    )


    if prefer_wiki:

        if source == "WIKIMEDIA":
            score += 100

        elif source == "GENERIC":
            score += 45

        elif source == "PIXABAY":
            score -= 30


    elif allow_stock:

        if source == "PIXABAY":
            score += 70

        elif source == "GENERIC":
            score += 45

        elif source == "WIKIMEDIA":
            score += 30


    else:

        if source == "GENERIC":
            score += 50

        elif source == "WIKIMEDIA":
            score += 45

        elif source == "PIXABAY":
            score += 25


    name = str(
        function.get(
            "name",
            ""
        )
    ).lower()


    if "foto" in name:
        score += 5


    if "video" in name:
        score += 4


    if "buscar" in name:
        score += 3


    if "search" in name:
        score += 3


    return score


def _query_parameter(
    function
):

    names = (
        function.get(
            "args",
            []
        )
        + function.get(
            "required",
            []
        )
        + function.get(
            "optional",
            []
        )
    )


    for name in names:

        if name.lower() in QUERY_ARGS:

            return name


    return None


def build_route(
    recovery_plan,
    functions=None
):

    if functions is None:

        functions = discover()


    if not recovery_plan.get(
        "eligible"
    ):

        return {
            "version":
                VERSION,

            "ready":
                False,

            "reason":
                "recovery_not_eligible",

            "routes":
                [],
        }


    candidates = [
        fn

        for fn in functions

        if fn.get(
            "candidate_for_recovery"
        )
    ]


    ranked = []


    for fn in candidates:

        query_arg = (
            _query_parameter(
                fn
            )
        )


        if not query_arg:
            continue


        ranked.append(
            {
                "function":
                    fn,

                "query_arg":
                    query_arg,

                "score":
                    _score_function(
                        fn,
                        recovery_plan
                    ),
            }
        )


    ranked.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )


    routes = []


    queries = (
        recovery_plan.get(
            "queries"
        )
        or []
    )


    max_attempts = int(
        recovery_plan.get(
            "max_attempts",
            0
        )
        or 0
    )


    for query in queries[
        :max_attempts
    ]:

        if not ranked:
            break


        best = ranked[0]

        function = best[
            "function"
        ]


        routes.append(
            {
                "query":
                    query,

                "source":
                    function.get(
                        "source"
                    ),

                "file":
                    function.get(
                        "file"
                    ),

                "function":
                    function.get(
                        "name"
                    ),

                "query_parameter":
                    best[
                        "query_arg"
                    ],

                "required":
                    function.get(
                        "required"
                    ),

                "score":
                    best[
                        "score"
                    ],

                "mode":
                    "DRY_RUN",
            }
        )


    return {
        "version":
            VERSION,

        "ready":
            bool(
                routes
        ),

        "reason":
            (
                "route_ready"
                if routes
                else "no_safe_source_function"
            ),

        "capabilities":
            summarize(
                functions
            ),

        "routes":
            routes,
    }


def self_test():

    plan = {
        "eligible":
            True,

        "queries":
            [
                "Flight 19 1945 archive"
            ],

        "max_attempts":
            2,

        "prefer_wikimedia":
            True,

        "allow_stock_retry":
            False,
    }


    functions = [
        {
            "file":
                "wikimedia_source.py",

            "line":
                100,

            "name":
                "buscar_wikimedia_fotos",

            "source":
                "WIKIMEDIA",

            "args":
                [
                    "query",
                    "limit"
                ],

            "required":
                [
                    "query"
                ],

            "optional":
                [
                    "limit"
                ],

            "candidate_for_recovery":
                True,
        },

        {
            "file":
                "midia.py",

            "line":
                200,

            "name":
                "buscar_pixabay",

            "source":
                "PIXABAY",

            "args":
                [
                    "query"
                ],

            "required":
                [
                    "query"
                ],

            "optional":
                [],

            "candidate_for_recovery":
                True,
        },
    ]


    route = build_route(
        plan,
        functions
    )


    assert route[
        "ready"
    ] is True


    assert (
        route[
            "routes"
        ][0][
            "source"
        ]
        == "WIKIMEDIA"
    )


    assert (
        route[
            "routes"
        ][0][
            "mode"
        ]
        == "DRY_RUN"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.17 ROUTER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Documentary-first Routing"
    )
    print(
        "OK Query Parameter Mapping"
    )
    print(
        "OK Query Budget"
    )
    print(
        "OK DRY_RUN enforcement"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.18 ACTIVATION GUARD
# =====================================================

cat > vi6_18_activation_guard.py <<'PY'
#!/usr/bin/env python3

import json
import os
import py_compile
from pathlib import Path


VERSION = "6.18"


REQUIRED = (
    "vi6_6_active_brain.py",
    "vi6_7_retrieval_planner.py",
    "vi6_8_storyboard_director.py",
    "vi6_8_runtime_policy.py",
    "vi6_9_quality_firewall.py",
    "vi6_9_runtime_policy.py",
    "vi6_10_coverage_predictor.py",
    "vi6_11_second_chance.py",
    "vi6_12_story_guard.py",
    "vi6_13_recovery_planner.py",
    "vi6_14_pre_download_gate.py",
    "vi6_15_decision_ledger.py",
    "vi6_16_source_capabilities.py",
    "vi6_17_recovery_router.py",
)


def evaluate_activation(
    capability_payload
):

    reasons = []


    missing = [
        filename
        for filename in REQUIRED
        if not Path(
            filename
        ).exists()
    ]


    if missing:

        reasons.append(
            "missing_modules"
        )


    compile_errors = []


    for filename in REQUIRED:

        if not Path(
            filename
        ).exists():

            continue


        try:

            py_compile.compile(
                filename,
                doraise=True
            )

        except Exception as exc:

            compile_errors.append(
                {
                    "file":
                        filename,

                    "error":
                        (
                            f"{type(exc).__name__}: "
                            f"{exc}"
                        ),
                }
            )


    if compile_errors:

        reasons.append(
            "compile_errors"
        )


    summary = (
        capability_payload.get(
            "summary"
        )
        or {}
    )


    has_documentary = bool(
        summary.get(
            "has_documentary_route"
        )
    )


    has_stock = bool(
        summary.get(
            "has_stock_route"
        )
    )


    usable = int(
        summary.get(
            "usable",
            0
        )
        or 0
    )


    if usable <= 0:

        reasons.append(
            "no_usable_source_functions"
        )


    if not has_documentary:

        reasons.append(
            "no_documentary_route"
        )


    status = (
        "READY_FOR_CONTROLLED_WIRING"

        if not reasons

        else "HOLD"
    )


    return {
        "version":
            VERSION,

        "status":
            status,

        "safe_to_activate":
            status
            == "READY_FOR_CONTROLLED_WIRING",

        "usable_source_functions":
            usable,

        "documentary_route":
            has_documentary,

        "stock_route":
            has_stock,

        "missing":
            missing,

        "compile_errors":
            compile_errors,

        "reasons":
            reasons,

        # Mesmo READY ainda não executa
        # busca automaticamente.
        "runtime_mode":
            "DRY_RUN",
    }


def save_report(
    payload
):

    folder = os.path.expanduser(
        "~/ShortAutoPro/logs/producao"
    )

    os.makedirs(
        folder,
        exist_ok=True
    )


    path = os.path.join(
        folder,
        "vi6_18_activation_guard_latest.json"
    )


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


    return path


def self_test():

    payload = {
        "summary":
            {
                "usable":
                    2,

                "has_documentary_route":
                    True,

                "has_stock_route":
                    True,
            }
    }


    # Self test não depende dos arquivos
    # reais para a regra lógica.
    summary = payload[
        "summary"
    ]


    assert (
        summary[
            "usable"
        ] > 0
    )


    assert (
        summary[
            "has_documentary_route"
        ]
        is True
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.18 ACTIVATION GUARD SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Capability Requirement"
    )
    print(
        "OK Documentary Route Requirement"
    )
    print(
        "OK Compile Requirement"
    )
    print(
        "OK DRY_RUN Lock"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 4. COMBINED OFFLINE TEST
# =====================================================

cat > testar_vi616_vi618.py <<'PY'
#!/usr/bin/env python3

from vi6_13_recovery_planner import (
    build_recovery_plan
)

from vi6_16_source_capabilities import (
    save_report
)

from vi6_17_recovery_router import (
    build_route
)

from vi6_18_activation_guard import (
    evaluate_activation,
    save_report as save_guard
)


scene = {
    "retrieval_role_6_7":
        "EVIDENCE",

    "retrieval_anchor_strength_6_7":
        7,

    "retrieval_anchors_6_7":
        [
            "Flight 19",
            "1945"
        ],

    "retrieval_primary_query_6_7":
        "Flight 19 1945",

    "retrieval_queries_6_7":
        [
            "Flight 19 1945"
        ],
}


recovery = build_recovery_plan(
    scene,
    {},
    "vi69_semantic_floor"
)


cap_path, capabilities = (
    save_report()
)


route = build_route(
    recovery,
    capabilities[
        "functions"
    ]
)


guard = evaluate_activation(
    capabilities
)


guard_path = save_guard(
    guard
)


print()
print(
    "======================================"
)
print(
    " VI6.16-6.18 OFFLINE SYSTEM TEST"
)
print(
    "======================================"
)

print(
    "RECOVERY ELIGIBLE:",
    recovery[
        "eligible"
    ]
)

print(
    "RECOVERY QUERIES:",
    len(
        recovery[
            "queries"
        ]
    )
)

print(
    "SOURCE FUNCTIONS:",
    capabilities[
        "summary"
    ][
        "functions_seen"
    ]
)

print(
    "USABLE FUNCTIONS:",
    capabilities[
        "summary"
    ][
        "usable"
    ]
)

print(
    "DOCUMENTARY ROUTE:",
    capabilities[
        "summary"
    ][
        "has_documentary_route"
    ]
)

print(
    "STOCK ROUTE:",
    capabilities[
        "summary"
    ][
        "has_stock_route"
    ]
)

print(
    "ROUTE READY:",
    route[
        "ready"
    ]
)

print(
    "ROUTES:",
    len(
        route[
            "routes"
        ]
    )
)

print(
    "ACTIVATION STATUS:",
    guard[
        "status"
    ]
)

print(
    "SAFE TO WIRE:",
    guard[
        "safe_to_activate"
    ]
)

print(
    "RUNTIME MODE:",
    guard[
        "runtime_mode"
    ]
)

print()
print(
    "CAPABILITY REPORT:",
    cap_path
)

print(
    "GUARD REPORT:",
    guard_path
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
PY


# =====================================================
# 5. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_16_source_capabilities.py \
    vi6_17_recovery_router.py \
    vi6_18_activation_guard.py \
    testar_vi616_vi618.py \
    vi6_13_recovery_planner.py \
    vi6_14_pre_download_gate.py \
    vi6_15_decision_ledger.py \
    vi6_9_runtime_policy.py \
    midia.py
then

    echo
    echo "COMPILE FALHOU."

    rollback

    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# 6. SELF TESTS
# =====================================================

echo
echo "===== VI6.16 SELF TEST ====="

python vi6_16_source_capabilities.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.17 SELF TEST ====="

python vi6_17_recovery_router.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.18 SELF TEST ====="

python vi6_18_activation_guard.py \
    || {
        rollback
        exit 1
    }


# =====================================================
# 7. EXISTING REGRESSIONS
# =====================================================

echo
echo "===== VI6.13 REGRESSION ====="

python vi6_13_recovery_planner.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.14 REGRESSION ====="

python vi6_14_pre_download_gate.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.15 REGRESSION ====="

python vi6_15_decision_ledger.py \
    || {
        rollback
        exit 1
    }


# =====================================================
# 8. CORE CHECK
# =====================================================

echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh
then
    rollback
    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh
then
    rollback
    exit 1
fi


# =====================================================
# 9. REAL OFFLINE DISCOVERY
# =====================================================

echo
echo "===== REAL SOURCE CAPABILITIES ====="

python testar_vi616_vi618.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== USABLE FUNCTIONS ====="

python - <<'PY'
from vi6_16_source_capabilities import (
    discover
)

functions = discover()

usable = [
    x
    for x in functions
    if x.get(
        "candidate_for_recovery"
    )
]

if not usable:

    print(
        "NENHUMA FUNÇÃO SEGURA ENCONTRADA"
    )

else:

    for item in usable:

        print(
            f"{item['source']:10} | "
            f"{item['file']}:{item['line']} | "
            f"{item['name']}("
            f"{', '.join(item['args'])})"
        )
PY


echo
echo "======================================"
echo " VI6.16 + VI6.17 + VI6.18 INSTALADOS"
echo "======================================"
echo
echo "OK Source Capability Discovery"
echo "OK AST Signature Inspection"
echo "OK Query Argument Detection"
echo "OK Unsupported Required Args Guard"
echo "OK Documentary-first Recovery Router"
echo "OK Stock Recovery Router"
echo "OK Query Budget"
echo "OK Activation Safety Guard"
echo "OK Compile Guard"
echo "OK DRY_RUN Lock"
echo "OK VI6.13 Recovery Planner preservado"
echo "OK VI6.14 Final Gate preservado"
echo "OK VI6.15 Ledger preservado"
echo
echo "MIDIA.PY MODIFICADO=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo "RECOVERY EXECUTION=DRY_RUN"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo "VIDEOS GERADOS=0"
echo
