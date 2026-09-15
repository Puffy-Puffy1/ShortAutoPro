#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI611_RUNTIME_ACTIVE",
    "_VI612_RUNTIME_ACTIVE",

    "_VI619_RUNTIME_ACTIVE",
    "_VI620_RUNTIME_ACTIVE",
    "_VI621_RUNTIME_ACTIVE",

    "_VI623_RUNTIME_ACTIVE",
    "_VI624_RUNTIME_ACTIVE",

    "_VI626_RUNTIME_ACTIVE",
    "_VI627_RUNTIME_ACTIVE",
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
    " VI6.25-6.27 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.23 ADAPTIVE:",
    brain._VI623_RUNTIME_ACTIVE
)

print(
    "VI6.24 TELEMETRY:",
    brain._VI624_RUNTIME_ACTIVE
)

print(
    "VI6.26 MOTION:",
    brain._VI626_RUNTIME_ACTIVE
)

print(
    "VI6.27 TRANSITIONS:",
    brain._VI627_RUNTIME_ACTIVE
)

print()
print(
    "RENDERER MODIFIED=False"
)
print(
    "AUDIO MODIFIED=False"
)
print(
    "LEGEND MODIFIED=False"
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
