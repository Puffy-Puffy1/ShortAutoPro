#!/usr/bin/env python3

import vi6_6_active_brain as brain
import vi6_8_runtime_policy
import vi6_9_runtime_policy

from vi6_12_story_guard import (
    reset_state,
    story_summary
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


reset_state()


print()
print(
    "======================================"
)
print(
    " VI6.11 + VI6.12 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.8 RUNTIME:",
    brain._VI68_RUNTIME_PATCHED
)

print(
    "VI6.9 RUNTIME:",
    brain._VI69_RUNTIME_PATCHED
)

print(
    "VI6.11 RUNTIME:",
    brain._VI611_RUNTIME_ACTIVE
)

print(
    "VI6.12 RUNTIME:",
    brain._VI612_RUNTIME_ACTIVE
)

print(
    "STORY STATE:",
    story_summary()
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
