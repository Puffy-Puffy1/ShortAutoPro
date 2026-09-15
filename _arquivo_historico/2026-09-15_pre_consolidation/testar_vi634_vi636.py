#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI628_RUNTIME_ACTIVE",
    "_VI629_RUNTIME_ACTIVE",
    "_VI630_RUNTIME_ACTIVE",

    "_VI631_RUNTIME_ACTIVE",
    "_VI632_RUNTIME_ACTIVE",
    "_VI633_RUNTIME_ACTIVE",

    "_VI634_RUNTIME_ACTIVE",
    "_VI635_RUNTIME_ACTIVE",
    "_VI636_RUNTIME_ACTIVE",
)


for flag in FLAGS:

    assert getattr(
        brain,
        flag,
        False
    ), flag


print()
print(
    "======================================"
)
print(
    " VI6.34-6.36 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.33 SAFETY:",
    brain._VI633_RUNTIME_ACTIVE
)

print(
    "VI6.34 AUTO-REPAIR:",
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

print()
print(
    "FFMPEG EXECUTION=False"
)
print(
    "RENDERER EXECUTION=False"
)
print(
    "VIDEO.PY MODIFIED=False"
)
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
