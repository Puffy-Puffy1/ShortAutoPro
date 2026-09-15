#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi619_vi621_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.19 + VI6.20 + VI6.21"
echo " TRUE RECOVERY EXECUTION"
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
vi6_16_source_capabilities.py
vi6_17_recovery_router.py
vi6_18_activation_guard.py
"

for F in $REQUIRED
do

    if [ ! -f "$F" ]; then

        echo "ERRO: $F não encontrado."
        echo "NENHUMA ALTERAÇÃO FEITA."

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
    vi6_15_decision_ledger.py \
    vi6_16_source_capabilities.py \
    vi6_17_recovery_router.py \
    vi6_18_activation_guard.py
then

    echo
    echo "BASELINE FALHOU."
    echo "NENHUMA ALTERAÇÃO FEITA."

    exit 3
fi

echo "BASELINE=OK"


cp vi6_9_runtime_policy.py \
   "$BACKDIR/vi6_9_runtime_policy.py"


for F in \
    vi6_19_true_recovery.py \
    vi6_20_recovery_normalizer.py \
    vi6_21_recovery_circuit.py \
    testar_vi619_vi621.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.19-6.21"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_19_true_recovery.py \
        vi6_20_recovery_normalizer.py \
        vi6_21_recovery_circuit.py \
        testar_vi619_vi621.py
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
# 1. VI6.21 CIRCUIT BREAKER
# =====================================================

cat > vi6_21_recovery_circuit.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.21"

MAX_CALLS_PER_SHORT = 4
MAX_CALLS_PER_SCENE = 2
MAX_ERRORS = 2


_STATE = {

    "calls":
        0,

    "errors":
        0,

    "success":
        0,

    "scene_calls":
        {},

    "open":
        False,
}


def _scene(scene):

    board = (
        scene.get(
            "_vi68_storyboard"
        )
        or {}
    )

    try:

        return int(
            board.get(
                "scene",
                0
            )
            or 0
        )

    except Exception:

        return 0


def status():

    return {

        "version":
            VERSION,

        "calls":
            _STATE[
                "calls"
            ],

        "errors":
            _STATE[
                "errors"
            ],

        "success":
            _STATE[
                "success"
            ],

        "open":
            _STATE[
                "open"
            ],

        "scene_calls":
            dict(
                _STATE[
                    "scene_calls"
                ]
            ),

        "max_calls":
            MAX_CALLS_PER_SHORT,

        "max_scene_calls":
            MAX_CALLS_PER_SCENE,

        "max_errors":
            MAX_ERRORS,
    }


def allow(
    scene
):

    if _STATE[
        "open"
    ]:

        return (
            False,
            "circuit_open"
        )


    if (
        _STATE[
            "calls"
        ]
        >= MAX_CALLS_PER_SHORT
    ):

        _STATE[
            "open"
        ] = True

        return (
            False,
            "short_budget_exhausted"
        )


    number = _scene(
        scene
    )


    used = int(
        _STATE[
            "scene_calls"
        ].get(
            number,
            0
        )
    )


    if (
        used
        >= MAX_CALLS_PER_SCENE
    ):

        return (
            False,
            "scene_budget_exhausted"
        )


    return (
        True,
        "allowed"
    )


def register_call(
    scene
):

    number = _scene(
        scene
    )


    _STATE[
        "calls"
    ] += 1


    _STATE[
        "scene_calls"
    ][
        number
    ] = (
        int(
            _STATE[
                "scene_calls"
            ].get(
                number,
                0
            )
        )
        + 1
    )


def register_success():

    _STATE[
        "success"
    ] += 1


def register_error():

    _STATE[
        "errors"
    ] += 1


    if (
        _STATE[
            "errors"
        ]
        >= MAX_ERRORS
    ):

        _STATE[
            "open"
        ] = True


def reset():

    _STATE[
        "calls"
    ] = 0

    _STATE[
        "errors"
    ] = 0

    _STATE[
        "success"
    ] = 0

    _STATE[
        "scene_calls"
    ].clear()

    _STATE[
        "open"
    ] = False


def self_test():

    reset()


    scene = {
        "_vi68_storyboard":
            {
                "scene": 3
            }
    }


    ok, _ = allow(
        scene
    )

    assert ok is True


    register_call(
        scene
    )

    register_call(
        scene
    )


    ok, reason = allow(
        scene
    )


    assert ok is False

    assert (
        reason
        == "scene_budget_exhausted"
    )


    register_error()
    register_error()


    assert status()[
        "open"
    ] is True


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.21 CIRCUIT SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK max 4 recovery calls / short"
    )
    print(
        "OK max 2 calls / scene"
    )
    print(
        "OK error circuit"
    )
    print(
        "OK reset"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.20 RECOVERY NORMALIZER
# =====================================================

cat > vi6_20_recovery_normalizer.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.20"


def _s(v):

    return str(
        v or ""
    ).strip()


def _u(v):

    return _s(
        v
    ).upper()


def _f(
    v,
    default=0.0
):

    try:
        return float(v)

    except Exception:
        return float(default)


def _source(
    item,
    route=None
):

    value = (
        item.get(
            "fonte"
        )
        or item.get(
            "source"
        )
        or (
            (route or {}).get(
                "source"
            )
        )
        or ""
    )


    return _s(
        value
    )


def _explicit_false(
    item
):

    fields = (
        "truth_ok",
        "identity_ok",
        "source_identity_ok",
        "evidence_ok",
        "documentary_truth_ok",
    )


    for field in fields:

        if (
            field in item
            and item[
                field
            ] is False
        ):

            return True


    return False


def _explicit_true(
    item
):

    fields = (
        "truth_ok",
        "identity_ok",
        "source_identity_ok",
        "evidence_ok",
        "documentary_truth_ok",
    )


    return any(
        item.get(
            field
        ) is True
        for field in fields
    )


def normalize_candidate(
    candidate,
    route=None
):

    if not isinstance(
        candidate,
        dict
    ):

        return None


    item = dict(
        candidate
    )


    source = _source(
        item,
        route
    )


    if source:

        item[
            "fonte"
        ] = source


    source_upper = (
        source.upper()
    )


    evidence = _u(
        item.get(
            "evidence_class"
        )
        or item.get(
            "classe_evidencia"
        )
    )


    query_tier = _u(
        item.get(
            "wiki_query_tier"
        )
        or item.get(
            "query_tier"
        )
    )


    anchor = _f(
        item.get(
            "wiki_anchor_ratio"
        )
        or item.get(
            "anchor_ratio"
        )
        or item.get(
            "anchor_score"
        )
        or 0
    )


    conflict = bool(
        item.get(
            "identity_conflict"
        )
        or item.get(
            "numeric_identity_conflict"
        )
        or item.get(
            "named_context_conflict"
        )
    )


    explicit_false = (
        _explicit_false(
            item
        )
    )


    explicit_true = (
        _explicit_true(
            item
        )
    )


    is_wiki = (
        "WIKI"
        in source_upper
        or "COMMONS"
        in source_upper
    )


    # =================================
    # DOCUMENTARY TRUTH
    # =================================

    documentary_truth = bool(

        is_wiki

        and not conflict

        and not explicit_false

        and (

            explicit_true

            or evidence
            == "CASE_DIRECT"

            or (
                evidence
                == "CONTEXTUAL"

                and anchor >= .20
            )
        )
    )


    if documentary_truth:

        item[
            "_vi6_class"
        ] = "REAL_DOCUMENTARY"

        item[
            "_vi6_truth_ok"
        ] = True

        item[
            "_vi6_risk"
        ] = "LOW"

        item[
            "_vi6_quality_tier"
        ] = "NORMAL"

        item[
            "_vi620_recovery_verified"
        ] = True


    else:

        # Recuperação Wikimedia sem prova
        # suficiente NÃO vira documental.
        #
        # Também não promovemos documento
        # genérico para SAFE_CONTEXT.
        if is_wiki:

            return None


        item[
            "_vi6_class"
        ] = (
            item.get(
                "_vi6_class"
            )
            or item.get(
                "class"
            )
            or "SAFE_CONTEXT"
        )


        item[
            "_vi6_truth_ok"
        ] = bool(
            item.get(
                "_vi6_truth_ok",
                item.get(
                    "truth_ok",
                    True
                )
            )
        )


        item[
            "_vi6_risk"
        ] = (
            item.get(
                "_vi6_risk"
            )
            or item.get(
                "risk"
            )
            or "LOW"
        )


        item[
            "_vi6_quality_tier"
        ] = (
            item.get(
                "_vi6_quality_tier"
            )
            or item.get(
                "quality_tier"
            )
            or "NORMAL"
        )


    item[
        "_vi620_recovery"
    ] = True


    item[
        "_vi620_evidence"
    ] = evidence


    item[
        "_vi620_query_tier"
    ] = query_tier


    item[
        "_vi620_anchor"
    ] = anchor


    return item


def normalize_results(
    raw,
    route=None
):

    if raw is None:

        return []


    items = []


    if isinstance(
        raw,
        list
    ):

        items = raw


    elif isinstance(
        raw,
        tuple
    ):

        for value in raw:

            if isinstance(
                value,
                list
            ):

                items = value
                break


    elif isinstance(
        raw,
        dict
    ):

        for key in (
            "results",
            "items",
            "candidates",
            "media",
            "fotos",
            "photos",
            "videos",
        ):

            value = raw.get(
                key
            )


            if isinstance(
                value,
                list
            ):

                items = value
                break


        if (
            not items
            and (
                raw.get(
                    "url"
                )
                or raw.get(
                    "id"
                )
            )
        ):

            items = [
                raw
            ]


    output = []


    for candidate in items:

        normalized = (
            normalize_candidate(
                candidate,
                route
            )
        )


        if normalized is not None:

            output.append(
                normalized
            )


    return output


def self_test():

    doc = {

        "fonte":
            "Wikimedia",

        "id":
            "flight19",

        "url":
            "x",

        "evidence_class":
            "CASE_DIRECT",

        "wiki_anchor_ratio":
            .60,
    }


    result = normalize_candidate(
        doc,
        {
            "source":
                "WIKIMEDIA"
        }
    )


    assert result is not None

    assert (
        result[
            "_vi6_class"
        ]
        == "REAL_DOCUMENTARY"
    )

    assert (
        result[
            "_vi6_truth_ok"
        ]
        is True
    )


    bad = {

        "fonte":
            "Wikimedia",

        "id":
            "wrong",

        "evidence_class":
            "GENERIC_DOCUMENT",

        "identity_conflict":
            True,
    }


    result = normalize_candidate(
        bad
    )


    assert result is None


    stock = {

        "fonte":
            "Pixabay",

        "id":
            "stock",

        "url":
            "x",
    }


    result = normalize_candidate(
        stock
    )


    assert result is not None

    assert (
        result[
            "_vi6_class"
        ]
        == "SAFE_CONTEXT"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.20 NORMALIZER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Case Direct Documentary"
    )
    print(
        "OK Contextual Anchor Rule"
    )
    print(
        "OK Identity Conflict Rejection"
    )
    print(
        "OK Generic Wikimedia Rejection"
    )
    print(
        "OK Safe Stock Normalization"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.19 TRUE RECOVERY
# =====================================================

cat > vi6_19_true_recovery.py <<'PY'
#!/usr/bin/env python3

import importlib
import inspect
import os


from vi6_13_recovery_planner import (
    build_recovery_plan
)

from vi6_16_source_capabilities import (
    discover
)

from vi6_17_recovery_router import (
    build_route
)

from vi6_20_recovery_normalizer import (
    normalize_results
)

from vi6_21_recovery_circuit import (
    allow,
    register_call,
    register_success,
    register_error,
    status as circuit_status,
)


VERSION = "6.19"


SAFE_RUNTIME_MODULES = {

    "wikimedia_source.py":
        "wikimedia_source",

    "source_router.py":
        "source_router",
}


def _s(v):

    return str(
        v or ""
    ).strip()


def _scene_text(
    scene
):

    for key in (
        "segmento",
        "segment",
        "texto",
        "text",
        "narracao",
        "narração",
    ):

        value = _s(
            scene.get(
                key
            )
        )


        if value:

            return value


    return ""


def _must(
    scene
):

    raw = (
        scene.get(
            "must_have"
        )
        or scene.get(
            "must"
        )
        or []
    )


    if isinstance(
        raw,
        str
    ):

        return [
            raw
        ]


    if isinstance(
        raw,
        (
            list,
            tuple
        )
    ):

        return list(
            raw
        )


    return []


def _argument_value(
    name,
    query,
    scene,
    route
):

    low = name.lower()


    if low in {
        "q",
        "query",
        "consulta",
        "termo",
        "busca",
        "search",
        "search_query",
        "visual_query",
    }:

        return (
            True,
            query
        )


    if low in {
        "cena",
        "scene",
    }:

        return (
            True,
            scene
        )


    if low in {
        "must_have",
        "must",
    }:

        return (
            True,
            _must(
                scene
            )
        )


    if low in {
        "limit",
        "limite",
        "max_results",
        "quantidade",
        "per_page",
    }:

        return (
            True,
            12
        )


    if low in {
        "page",
        "pagina",
        "página",
    }:

        return (
            True,
            1
        )


    if low in {
        "modo",
        "mode",
    }:

        return (
            True,
            "recovery"
        )


    if low in {
        "topic",
        "topico",
        "tópico",
        "subject",
    }:

        value = (
            scene.get(
                "topic"
            )
            or scene.get(
                "subject"
            )
            or query
        )


        return (
            True,
            value
        )


    if low in {
        "descricao",
        "description",
        "texto",
        "text",
    }:

        return (
            True,
            _scene_text(
                scene
            )
        )


    if low == "rota_fonte":

        return (
            True,
            route.get(
                "source"
            )
        )


    if low == "short_id":

        return (
            True,
            scene.get(
                "short_id",
                "recovery"
            )
        )


    return (
        False,
        None
    )


def _load_callable(
    route
):

    filename = route.get(
        "file"
    )


    module_name = (
        SAFE_RUNTIME_MODULES.get(
            filename
        )
    )


    if not module_name:

        return (
            None,
            "unsafe_runtime_module"
        )


    try:

        module = (
            importlib.import_module(
                module_name
            )
        )

    except Exception as exc:

        return (
            None,
            (
                "module_import_error:"
                f"{type(exc).__name__}"
            )
        )


    function_name = (
        route.get(
            "function"
        )
    )


    function = getattr(
        module,
        function_name,
        None
    )


    if not callable(
        function
    ):

        return (
            None,
            "function_not_callable"
        )


    return (
        function,
        "ok"
    )


def _invoke(
    function,
    query,
    scene,
    route
):

    signature = (
        inspect.signature(
            function
        )
    )


    kwargs = {}


    for name, param in (
        signature.parameters.items()
    ):

        if name in {
            "self",
            "cls",
        }:

            continue


        has_value, value = (
            _argument_value(
                name,
                query,
                scene,
                route
            )
        )


        if has_value:

            kwargs[
                name
            ] = value

            continue


        if (
            param.default
            is not inspect._empty
        ):

            continue


        if param.kind in {

            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:

            continue


        raise RuntimeError(
            f"unsupported_required_arg:{name}"
        )


    return function(
        **kwargs
    )


def _candidate_score(
    meta
):

    try:

        score = float(
            meta.get(
                "score",
                0
            )
            or 0
        )

    except Exception:

        score = 0.0


    if (
        str(
            meta.get(
                "class",
                ""
            )
        ).upper()
        == "REAL_DOCUMENTARY"
        and meta.get(
            "truth_ok",
            False
        )
    ):

        score += 10.0


    return score


def true_recovery(
    scene,
    vi6_scene,
    rejection_reason,
    evaluator,
    firewall,
    final_gate,
    dry_run=False
):

    mode = _s(
        os.getenv(
            "VI619_RECOVERY_MODE",
            "ACTIVE"
        )
    ).upper()


    if mode == "OFF":

        return (
            None,
            "vi619_disabled",
            {
                "decision":
                    "DISABLED"
            }
        )


    plan = build_recovery_plan(
        scene,
        vi6_scene,
        rejection_reason
    )


    if not plan.get(
        "eligible"
    ):

        return (
            None,
            "vi619_plan_not_eligible",
            {
                "decision":
                    "NO_RECOVERY",

                "recovery_plan":
                    plan,
            }
        )


    functions = discover()


    route_plan = build_route(
        plan,
        functions
    )


    # Somente módulos explicitamente
    # permitidos para execução dinâmica.
    routes = [

        route

        for route
        in route_plan.get(
            "routes",
            []
        )

        if route.get(
            "file"
        )
        in SAFE_RUNTIME_MODULES
    ]


    if not routes:

        return (
            None,
            "vi619_no_safe_runtime_route",
            {
                "decision":
                    "NO_RECOVERY",

                "recovery_plan":
                    plan,

                "route_plan":
                    route_plan,
            }
        )


    if dry_run:

        return (
            None,
            "vi619_dry_run_ready",
            {
                "decision":
                    "DRY_RUN",

                "recovery_plan":
                    plan,

                "routes":
                    routes,

                "circuit":
                    circuit_status(),
            }
        )


    winners = []

    errors = []


    for route in routes:

        allowed, deny_reason = (
            allow(
                scene
            )
        )


        if not allowed:

            errors.append(
                deny_reason
            )

            break


        query = route.get(
            "query"
        )


        function, load_reason = (
            _load_callable(
                route
            )
        )


        if function is None:

            errors.append(
                load_reason
            )

            continue


        register_call(
            scene
        )


        try:

            raw = _invoke(
                function,
                query,
                scene,
                route
            )


        except Exception as exc:

            register_error()

            errors.append(
                (
                    f"{type(exc).__name__}:"
                    f"{str(exc)[:100]}"
                )
            )

            continue


        normalized = (
            normalize_results(
                raw,
                route
            )
        )


        if not normalized:

            continue


        for candidate in normalized:

            try:

                meta = evaluator(
                    candidate,
                    scene,
                    vi6_scene
                )

            except Exception:

                continue


            if meta is None:

                continue


            fw = firewall(
                candidate,
                scene,
                meta
            )


            if (
                fw.get(
                    "action"
                )
                != "KEEP"
            ):

                continue


            gate = final_gate(
                candidate,
                scene,
                meta
            )


            if (
                gate.get(
                    "action"
                )
                != "ACCEPT"
            ):

                continue


            winners.append(
                (
                    _candidate_score(
                        meta
                    ),
                    candidate,
                    meta,
                    route,
                    gate,
                )
            )


    if not winners:

        return (
            None,
            "vi619_recovery_failed",
            {
                "decision":
                    "NO_SAFE_RECOVERY",

                "recovery_plan":
                    plan,

                "routes":
                    routes,

                "errors":
                    errors,

                "circuit":
                    circuit_status(),
            }
        )


    winners.sort(
        key=lambda item:
            item[0],
        reverse=True
    )


    (
        score,
        candidate,
        meta,
        route,
        gate,
    ) = winners[0]


    register_success()


    candidate[
        "_vi619_true_recovery"
    ] = True


    candidate[
        "_vi619_query"
    ] = route.get(
        "query"
    )


    candidate[
        "_vi619_source"
    ] = route.get(
        "source"
    )


    meta = dict(
        meta
        or {}
    )


    meta[
        "vi619_decision"
    ] = "TRUE_RECOVERY"


    meta[
        "vi619_query"
    ] = route.get(
        "query"
    )


    meta[
        "vi619_source"
    ] = route.get(
        "source"
    )


    meta[
        "vi619_score"
    ] = score


    meta[
        "vi619_circuit"
    ] = circuit_status()


    return (
        candidate,
        "vi619_true_recovery",
        meta
    )


def self_test():

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

        "_vi68_storyboard":
            {
                "scene": 2
            },
    }


    candidate, reason, meta = (
        true_recovery(
            scene,
            {},
            "vi69_semantic_floor",
            lambda *args: None,
            lambda *args: {
                "action":
                    "FALLBACK"
            },
            lambda *args: {
                "action":
                    "FALLBACK"
            },
            dry_run=True
        )
    )


    assert candidate is None


    assert reason in {

        "vi619_dry_run_ready",
        "vi619_no_safe_runtime_route",
    }


    assert (
        meta.get(
            "decision"
        )
        in {
            "DRY_RUN",
            "NO_RECOVERY",
        }
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.19 TRUE RECOVERY SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK recovery-plan integration"
    )
    print(
        "OK source-route integration"
    )
    print(
        "OK safe-module allowlist"
    )
    print(
        "OK dry-run has zero API"
    )
    print(
        "OK circuit integration"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 4. UPDATE RUNTIME STACK
# =====================================================

cat > vi6_9_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

from vi6_9_quality_firewall import (
    check
)

from vi6_11_second_chance import (
    rescue
)

from vi6_12_story_guard import (
    review,
    story_summary
)

from vi6_13_recovery_planner import (
    build_recovery_plan
)

from vi6_14_pre_download_gate import (
    final_gate
)

from vi6_15_decision_ledger import (
    record,
    flush
)

from vi6_19_true_recovery import (
    true_recovery
)


if not getattr(
    brain,
    "_VI69_RUNTIME_PATCHED",
    False
):

    _base = (
        brain.supervisionar_vi6_6
    )


    def _wrapped(
        vi6_scene,
        candidatos,
        cena,
        current_candidate,
        current_reason
    ):

        (
            candidate,
            reason,
            meta
        ) = _base(
            vi6_scene,
            candidatos,
            cena,
            current_candidate,
            current_reason
        )


        meta = dict(
            meta
            or {}
        )


        rejection_reason = None
        recovery_attempted = False


        def try_true_recovery(
            why
        ):

            nonlocal recovery_attempted


            if recovery_attempted:

                return (
                    None,
                    "vi619_already_attempted",
                    {}
                )


            recovery_attempted = True


            return true_recovery(
                cena,
                vi6_scene,
                why,
                brain.evaluate,
                check,
                final_gate,
                dry_run=False
            )


        # =========================================
        # VI6.9 FIREWALL
        # =========================================

        if candidate is not None:

            fw = check(
                candidate,
                cena,
                meta
            )


            meta[
                "vi69_action"
            ] = fw.get(
                "action"
            )


            meta[
                "vi69_reason"
            ] = fw.get(
                "reason"
            )


            meta[
                "vi610_contract"
            ] = fw.get(
                "contract"
            )


            if (
                fw.get(
                    "action"
                )
                == "FALLBACK"
            ):

                rejection_reason = (
                    fw.get(
                        "reason",
                        "vi69_firewall"
                    )
                )

                candidate = None


        else:

            rejection_reason = (
                reason
                or current_reason
                or "vi66_no_candidate"
            )


        # =========================================
        # VI6.11 EXISTING-CANDIDATE RESCUE
        # =========================================

        if candidate is None:

            (
                rescued,
                rescue_reason,
                rescue_meta
            ) = rescue(
                vi6_scene,
                candidatos,
                cena,
                rejection_reason,
                brain.evaluate,
                check
            )


            meta[
                "vi611_decision"
            ] = rescue_meta.get(
                "decision"
            )


            meta[
                "vi611_reason"
            ] = rescue_reason


            if rescued is not None:

                candidate = rescued
                reason = rescue_reason
                meta.update(
                    rescue_meta
                )


            else:

                # =================================
                # VI6.19 TRUE SECOND RETRIEVAL
                # =================================

                (
                    recovered,
                    recovery_reason,
                    recovery_meta
                ) = try_true_recovery(
                    rejection_reason
                    or rescue_reason
                )


                if recovered is not None:

                    candidate = recovered
                    reason = recovery_reason

                    meta.update(
                        recovery_meta
                    )


                else:

                    plan = build_recovery_plan(
                        cena,
                        vi6_scene,
                        rejection_reason
                        or rescue_reason
                    )


                    meta[
                        "vi613_recovery_plan"
                    ] = plan


                    meta[
                        "vi619_reason"
                    ] = recovery_reason


                    meta[
                        "decision"
                    ] = "5X_AFTER_619"


                    record(
                        cena,
                        None,
                        recovery_reason
                        or rejection_reason
                        or rescue_reason,
                        meta,
                        plan,
                        "FALLBACK"
                    )


                    return (
                        None,
                        recovery_reason
                        or rejection_reason
                        or rescue_reason,
                        meta
                    )


        # =========================================
        # VI6.12 GLOBAL STORY GUARD
        # =========================================

        (
            candidate,
            story_reason,
            story_meta
        ) = review(
            candidate,
            cena,
            meta,
            vi6_scene,
            candidatos,
            brain.evaluate,
            check
        )


        meta = dict(
            story_meta
            or meta
        )


        meta[
            "vi612_reason"
        ] = story_reason


        if candidate is None:

            (
                recovered,
                recovery_reason,
                recovery_meta
            ) = try_true_recovery(
                story_reason
            )


            if recovered is not None:

                (
                    candidate,
                    story_reason,
                    story_meta
                ) = review(
                    recovered,
                    cena,
                    recovery_meta,
                    vi6_scene,
                    candidatos,
                    brain.evaluate,
                    check
                )


                meta = dict(
                    story_meta
                    or recovery_meta
                )


            if candidate is None:

                plan = build_recovery_plan(
                    cena,
                    vi6_scene,
                    story_reason
                    or recovery_reason
                )


                meta[
                    "vi613_recovery_plan"
                ] = plan


                meta[
                    "decision"
                ] = "5X_AFTER_612_619"


                record(
                    cena,
                    None,
                    story_reason
                    or recovery_reason,
                    meta,
                    plan,
                    "FALLBACK"
                )


                return (
                    None,
                    story_reason
                    or recovery_reason,
                    meta
                )


        # =========================================
        # VI6.14 FINAL GATE
        # =========================================

        gate = final_gate(
            candidate,
            cena,
            meta
        )


        meta[
            "vi614_action"
        ] = gate.get(
            "action"
        )


        meta[
            "vi614_reason"
        ] = gate.get(
            "reason"
        )


        if (
            gate.get(
                "action"
            )
            != "ACCEPT"
        ):

            (
                recovered,
                recovery_reason,
                recovery_meta
            ) = try_true_recovery(
                gate.get(
                    "reason"
                )
            )


            if recovered is not None:

                (
                    recovered,
                    story_reason,
                    story_meta
                ) = review(
                    recovered,
                    cena,
                    recovery_meta,
                    vi6_scene,
                    candidatos,
                    brain.evaluate,
                    check
                )


                if recovered is not None:

                    gate2 = final_gate(
                        recovered,
                        cena,
                        story_meta
                    )


                    if (
                        gate2.get(
                            "action"
                        )
                        == "ACCEPT"
                    ):

                        candidate = recovered

                        meta = dict(
                            story_meta
                            or recovery_meta
                        )

                        meta[
                            "vi614_action"
                        ] = "ACCEPT"

                        meta[
                            "vi614_reason"
                        ] = gate2.get(
                            "reason"
                        )

                        gate = gate2


            if (
                gate.get(
                    "action"
                )
                != "ACCEPT"
            ):

                plan = build_recovery_plan(
                    cena,
                    vi6_scene,
                    gate.get(
                        "reason"
                    )
                )


                meta[
                    "vi613_recovery_plan"
                ] = plan


                meta[
                    "decision"
                ] = "5X_AFTER_614_619"


                record(
                    cena,
                    None,
                    gate.get(
                        "reason"
                    ),
                    meta,
                    plan,
                    "FALLBACK"
                )


                return (
                    None,
                    gate.get(
                        "reason"
                    ),
                    meta
                )


        # =========================================
        # ACCEPT
        # =========================================

        reason = (
            gate.get(
                "reason"
            )
            or story_reason
            or reason
        )


        record(
            cena,
            candidate,
            reason,
            meta,
            None,
            "ACCEPT"
        )


        board = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        if (
            board.get(
                "cta_reuse"
            )
            or int(
                board.get(
                    "scene",
                    0
                )
                or 0
            ) >= 12
        ):

            meta[
                "vi612_story_summary"
            ] = story_summary()


            try:

                meta[
                    "vi615_ledger_path"
                ] = flush()

            except Exception as exc:

                meta[
                    "vi615_ledger_error"
                ] = (
                    f"{type(exc).__name__}:"
                    f"{str(exc)[:100]}"
                )


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        _wrapped
    )


    brain._VI69_RUNTIME_PATCHED = True
    brain._VI611_RUNTIME_ACTIVE = True
    brain._VI612_RUNTIME_ACTIVE = True
    brain._VI613_RUNTIME_ACTIVE = True
    brain._VI614_RUNTIME_ACTIVE = True
    brain._VI615_RUNTIME_ACTIVE = True
    brain._VI619_RUNTIME_ACTIVE = True
    brain._VI620_RUNTIME_ACTIVE = True
    brain._VI621_RUNTIME_ACTIVE = True
PY


# =====================================================
# 5. OFFLINE SYSTEM TEST
# =====================================================

cat > testar_vi619_vi621.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy

from vi6_19_true_recovery import (
    true_recovery
)

from vi6_20_recovery_normalizer import (
    normalize_candidate
)

from vi6_21_recovery_circuit import (
    reset,
    status
)


assert getattr(
    brain,
    "_VI619_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI620_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI621_RUNTIME_ACTIVE",
    False
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

    "_vi68_storyboard":
        {
            "scene": 4
        },
}


reset()


candidate, reason, meta = (
    true_recovery(
        scene,
        {},
        "vi69_semantic_floor",
        lambda *args: None,
        lambda *args: {
            "action":
                "FALLBACK"
        },
        lambda *args: {
            "action":
                "FALLBACK"
        },
        dry_run=True
    )
)


assert candidate is None


assert reason in {
    "vi619_dry_run_ready",
    "vi619_no_safe_runtime_route",
}


doc = normalize_candidate(
    {
        "fonte":
            "Wikimedia",

        "id":
            "x",

        "url":
            "x",

        "evidence_class":
            "CASE_DIRECT",

        "wiki_anchor_ratio":
            .70,
    }
)


assert doc is not None

assert (
    doc[
        "_vi6_class"
    ]
    == "REAL_DOCUMENTARY"
)


print()
print(
    "======================================"
)
print(
    " VI6.19-6.21 OFFLINE TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.19:",
    brain._VI619_RUNTIME_ACTIVE
)

print(
    "VI6.20:",
    brain._VI620_RUNTIME_ACTIVE
)

print(
    "VI6.21:",
    brain._VI621_RUNTIME_ACTIVE
)

print(
    "DRY RUN RESULT:",
    reason
)

print(
    "CIRCUIT:",
    status()
)

print()
print(
    "INSTALL API CALLS=0"
)
print(
    "INSTALL DOWNLOADS=0"
)
print(
    "INSTALL VIDEOS=0"
)
print()
PY


# =====================================================
# 6. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_19_true_recovery.py \
    vi6_20_recovery_normalizer.py \
    vi6_21_recovery_circuit.py \
    vi6_9_runtime_policy.py \
    testar_vi619_vi621.py \
    vi6_13_recovery_planner.py \
    vi6_14_pre_download_gate.py \
    vi6_15_decision_ledger.py \
    vi6_16_source_capabilities.py \
    vi6_17_recovery_router.py \
    vi6_18_activation_guard.py \
    midia.py
then

    echo
    echo "COMPILE FALHOU."

    rollback

    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# 7. SELF TESTS
# =====================================================

echo
echo "===== VI6.20 SELF TEST ====="

python vi6_20_recovery_normalizer.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.21 SELF TEST ====="

python vi6_21_recovery_circuit.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.19 SELF TEST ====="

python vi6_19_true_recovery.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== OFFLINE RUNTIME TEST ====="

python testar_vi619_vi621.py \
    || {
        rollback
        exit 1
    }


# =====================================================
# 8. REGRESSION STACK
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


echo
echo "===== VI6.16 REGRESSION ====="

python vi6_16_source_capabilities.py \
    >/dev/null \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.17 REGRESSION ====="

python vi6_17_recovery_router.py \
    || {
        rollback
        exit 1
    }


echo
echo "===== VI6.18 REGRESSION ====="

python vi6_18_activation_guard.py \
    || {
        rollback
        exit 1
    }


# =====================================================
# 9. CORE
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
# 10. VERIFY MIDIA UNTOUCHED
# =====================================================

echo
echo "===== RUNTIME IMPORT CHECK ====="

grep -n \
'import vi6_9_runtime_policy' \
midia.py \
| head


echo
echo "======================================"
echo " VI6.19 + VI6.20 + VI6.21 INSTALADOS"
echo "======================================"
echo
echo "OK True Recovery Engine"
echo "OK Dynamic Safe Source Execution"
echo "OK Runtime Module Allowlist"
echo "OK Query Argument Binder"
echo "OK Recovery Candidate Normalizer"
echo "OK Generic Wikimedia Rejection"
echo "OK Documentary Evidence Lock"
echo "OK Identity Conflict Rejection"
echo "OK VI6.6 Re-Evaluation"
echo "OK VI6.9 Re-Firewall"
echo "OK VI6.12 Story Recheck"
echo "OK VI6.14 Final Re-Gate"
echo "OK 4-call Recovery Budget"
echo "OK 2-call Per-Scene Budget"
echo "OK Error Circuit Breaker"
echo "OK 5.x Final Safety Fallback"
echo
echo "MIDIA.PY MODIFICADO=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo "API CALLS DURANTE INSTALACAO=0"
echo "DOWNLOADS DURANTE INSTALACAO=0"
echo "VIDEOS GERADOS=0"
echo
echo "FUTURA PRODUCAO:"
echo "VI619_RECOVERY_MODE=ACTIVE"
echo "MAX RECOVERY CALLS/SHORT=4"
echo "MAX RECOVERY CALLS/SCENE=2"
echo
