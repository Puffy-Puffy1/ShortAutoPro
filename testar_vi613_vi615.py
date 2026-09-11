#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy

from vi6_13_recovery_planner import (
    build_recovery_plan
)

from vi6_14_pre_download_gate import (
    final_gate
)

from vi6_15_decision_ledger import (
    reset,
    record,
    summary
)


assert getattr(
    brain,
    "_VI68_RUNTIME_PATCHED",
    False
)

assert getattr(
    brain,
    "_VI69_RUNTIME_PATCHED",
    False
)

assert getattr(
    brain,
    "_VI611_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI612_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI613_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI614_RUNTIME_ACTIVE",
    False
)

assert getattr(
    brain,
    "_VI615_RUNTIME_ACTIVE",
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
}


recovery = build_recovery_plan(
    scene,
    {},
    "vi69_semantic_floor"
)


assert recovery[
    "eligible"
] is True


strong_candidate = {

    "_vi6_class":
        "SAFE_CONTEXT",

    "_vi6_risk":
        "LOW",

    "_vi6_score":
        90,
}


gate = final_gate(
    strong_candidate,
    scene,
    {
        "class":
            "SAFE_CONTEXT",

        "score":
            90,

        "semantic":
            78,

        "anchor":
            .50,

        "role":
            "EVIDENCE",
    }
)


assert gate[
    "action"
] == "ACCEPT"


reset()


record(
    scene,
    {
        "fonte":
            "Wikimedia",

        "tipo":
            "foto"
    },
    "vi614_documentary_accept",
    {
        "class":
            "REAL_DOCUMENTARY",

        "score":
            95,
    },
    None,
    "ACCEPT"
)


ledger = summary()


assert ledger[
    "events"
] == 1

assert ledger[
    "accepted"
] == 1


print()
print(
    "======================================"
)
print(
    " VI6.13-6.15 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.8:",
    brain._VI68_RUNTIME_PATCHED
)

print(
    "VI6.9:",
    brain._VI69_RUNTIME_PATCHED
)

print(
    "VI6.11:",
    brain._VI611_RUNTIME_ACTIVE
)

print(
    "VI6.12:",
    brain._VI612_RUNTIME_ACTIVE
)

print(
    "VI6.13:",
    brain._VI613_RUNTIME_ACTIVE
)

print(
    "VI6.14:",
    brain._VI614_RUNTIME_ACTIVE
)

print(
    "VI6.15:",
    brain._VI615_RUNTIME_ACTIVE
)

print()
print(
    "RECOVERY QUERIES:",
    len(
        recovery[
            "queries"
        ]
    )
)

print(
    "FINAL GATE:",
    gate[
        "action"
    ]
)

print(
    "LEDGER:",
    ledger
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
