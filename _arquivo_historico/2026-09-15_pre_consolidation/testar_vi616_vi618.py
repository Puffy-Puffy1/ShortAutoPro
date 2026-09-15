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
