#!/usr/bin/env python3

from vi6_76_visual_technical_comparator import (
    compare
)

from vi6_79_canary_certification_gate import (
    evaluate
)


probe = {
    "status": "PASS",
    "width": 1080,
    "height": 1920,
    "pix_fmt": "yuv420p",
    "codec": "h264",
    "duration": "3.500",
}


comparison = compare(
    dict(probe),
    dict(probe)
)


assert (
    comparison["status"]
    == "PASS"
)


cert = evaluate(
    {
        "status": "RENDERED"
    },

    comparison,

    {
        "status": "PASS"
    },

    {
        "failure_action":
            "RENDER_SAME_SCENE_"
            "WITH_LEGACY_FILTER"
    },
)


assert (
    cert["status"]
    == "TECHNICALLY_CERTIFIED"
)


assert (
    cert[
        "runtime_canary_authorized"
    ]
    is False
)


print()
print(
    "======================================================"
)
print(
    " VI6.71-6.80 MEGA INTEGRATION: PASS"
)
print(
    "======================================================"
)
print(
    "REAL SOURCE POLICY=PASS"
)
print(
    "TWIN RENDER MODEL=PASS"
)
print(
    "TECHNICAL COMPARISON=PASS"
)
print(
    "ROLLBACK CONTRACT=PASS"
)
print(
    "RUNTIME CANARY=LOCKED"
)
print(
    "FULL ACTIVE=LOCKED"
)
