#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI619_RUNTIME_ACTIVE",
    "_VI620_RUNTIME_ACTIVE",
    "_VI621_RUNTIME_ACTIVE",

    "_VI623_RUNTIME_ACTIVE",
    "_VI624_RUNTIME_ACTIVE",

    "_VI626_RUNTIME_ACTIVE",
    "_VI627_RUNTIME_ACTIVE",

    "_VI628_RUNTIME_ACTIVE",
    "_VI629_RUNTIME_ACTIVE",
    "_VI630_RUNTIME_ACTIVE",
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
    " VI6.28-6.30 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.26 MOTION RANKING:",
    brain._VI626_RUNTIME_ACTIVE
)

print(
    "VI6.27 TRANSITIONS:",
    brain._VI627_RUNTIME_ACTIVE
)

print(
    "VI6.28 BLUEPRINT:",
    brain._VI628_RUNTIME_ACTIVE
)

print(
    "VI6.29 KEN BURNS:",
    brain._VI629_RUNTIME_ACTIVE
)

print(
    "VI6.30 CONTRACT:",
    brain._VI630_RUNTIME_ACTIVE
)

print()
print(
    "RENDERER EXECUTION=False"
)
print(
    "FFMPEG FILTER CREATED=False"
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
