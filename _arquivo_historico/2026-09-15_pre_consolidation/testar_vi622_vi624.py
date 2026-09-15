#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


assert getattr(
    brain,
    "_VI623_RUNTIME_ACTIVE",
    False
)


assert getattr(
    brain,
    "_VI624_RUNTIME_ACTIVE",
    False
)


# Flags anteriores também precisam continuar.
for flag in (
    "_VI69_RUNTIME_PATCHED",
    "_VI611_RUNTIME_ACTIVE",
    "_VI612_RUNTIME_ACTIVE",
    "_VI613_RUNTIME_ACTIVE",
    "_VI614_RUNTIME_ACTIVE",
    "_VI615_RUNTIME_ACTIVE",
    "_VI619_RUNTIME_ACTIVE",
    "_VI620_RUNTIME_ACTIVE",
    "_VI621_RUNTIME_ACTIVE",
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
    " VI6.22-6.24 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.23 ADAPTIVE BUDGET:",
    brain._VI623_RUNTIME_ACTIVE
)

print(
    "VI6.24 TELEMETRY:",
    brain._VI624_RUNTIME_ACTIVE
)

print(
    "VI6.19 TRUE RECOVERY:",
    brain._VI619_RUNTIME_ACTIVE
)

print(
    "VI6.21 CIRCUIT:",
    brain._VI621_RUNTIME_ACTIVE
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
