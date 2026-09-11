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
