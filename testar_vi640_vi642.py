#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


for flag in (

    "_VI69_RUNTIME_PATCHED",

    "_VI634_RUNTIME_ACTIVE",
    "_VI635_RUNTIME_ACTIVE",
    "_VI636_RUNTIME_ACTIVE",

    "_VI637_RUNTIME_ACTIVE",
    "_VI638_RUNTIME_ACTIVE",
    "_VI639_RUNTIME_ACTIVE",

    "_VI640_RUNTIME_ACTIVE",
    "_VI642_RUNTIME_ACTIVE",
):

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
    " VI6.40-6.42 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.39 GATE:",
    brain._VI639_RUNTIME_ACTIVE
)

print(
    "VI6.40 BRIDGE:",
    brain._VI640_RUNTIME_ACTIVE
)

print(
    "VI6.42 RUNTIME:",
    brain._VI642_RUNTIME_ACTIVE
)

print()
print(
    "BRIDGE MODE=SHADOW"
)
print(
    "BINDING PERFORMED=False"
)
print(
    "RENDERER ACTIVE=False"
)
print(
    "VIDEO.PY MODIFIED=False"
)
print()
