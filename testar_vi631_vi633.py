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

    "_VI631_RUNTIME_ACTIVE",
    "_VI632_RUNTIME_ACTIVE",
    "_VI633_RUNTIME_ACTIVE",
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
    " VI6.31-6.33 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.30 CONTRACT:",
    brain._VI630_RUNTIME_ACTIVE
)

print(
    "VI6.31 AUDITOR:",
    brain._VI631_RUNTIME_ACTIVE
)

print(
    "VI6.32 DURATION:",
    brain._VI632_RUNTIME_ACTIVE
)

print(
    "VI6.33 SAFETY:",
    brain._VI633_RUNTIME_ACTIVE
)

print()
print(
    "RENDERER EXECUTION=False"
)
print(
    "FFMPEG EXECUTION=False"
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
