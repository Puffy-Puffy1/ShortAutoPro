#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI634_RUNTIME_ACTIVE",
    "_VI635_RUNTIME_ACTIVE",
    "_VI636_RUNTIME_ACTIVE",

    "_VI637_RUNTIME_ACTIVE",
    "_VI638_RUNTIME_ACTIVE",
    "_VI639_RUNTIME_ACTIVE",
)


for flag in FLAGS:

    assert getattr(
        brain,
        flag,
        False
    ), flag


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)


report = inspect_renderer(
    "video.py"
)


assert (
    report[
        "file_modified"
    ]
    is False
)


assert (
    report[
        "renderer_executed"
    ]
    is False
)


assert (
    report[
        "ffmpeg_executed"
    ]
    is False
)


print()
print(
    "======================================"
)
print(
    " VI6.37-6.39 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.34 AUTO REPAIR:",
    brain._VI634_RUNTIME_ACTIVE
)

print(
    "VI6.35 DRY COMPILER:",
    brain._VI635_RUNTIME_ACTIVE
)

print(
    "VI6.36 COMPATIBILITY:",
    brain._VI636_RUNTIME_ACTIVE
)

print(
    "VI6.37 SHADOW ADAPTER:",
    brain._VI637_RUNTIME_ACTIVE
)

print(
    "VI6.38 FILTER VALIDATOR:",
    brain._VI638_RUNTIME_ACTIVE
)

print(
    "VI6.39 ACTIVATION GATE:",
    brain._VI639_RUNTIME_ACTIVE
)

print()
print(
    "REAL VIDEO.PY MAP STATUS:",
    report[
        "status"
    ]
)

print(
    "RENDERER CANDIDATES:",
    report[
        "candidate_count"
    ]
)


if report.get(
    "best"
):

    print(
        "BEST FUNCTION:",
        report[
            "best"
        ][
            "function"
        ]
    )

    print(
        "BEST LINE:",
        report[
            "best"
        ][
            "line_start"
        ]
    )

    print(
        "BEST SCORE:",
        report[
            "best"
        ][
            "score"
        ]
    )


print()
print(
    "VIDEO.PY MODIFIED=False"
)
print(
    "FFMPEG EXECUTION=False"
)
print(
    "RENDERER EXECUTION=False"
)
print(
    "VIDEOS=0"
)
print()
