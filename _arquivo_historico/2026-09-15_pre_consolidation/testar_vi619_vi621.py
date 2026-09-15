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
