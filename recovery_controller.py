#!/usr/bin/env python3
"""Canonical bounded recovery boundary.

RecoveryController is the only orchestration boundary allowed to coordinate
repair actions after a canonical stage reports a recoverable failure.

It deliberately does NOT:
- acquire media or choose providers;
- relax MUST/quality requirements;
- invoke retired Stage 6/V2 runtimes;
- invoke another recovery engine;
- retry indefinitely.

Stage-specific modules remain owners of their own repair operation. This module
only decides whether a bounded repair action may be attempted and records the
result.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class RecoveryAction:
    """One explicitly declared, bounded repair action."""

    name: str
    run: Callable[[], dict[str, Any]]


@dataclass
class RecoveryResult:
    status: str
    reason: str
    attempts: int = 0
    actions: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "controller": "RecoveryController",
            "status": self.status,
            "reason": self.reason,
            "attempts": self.attempts,
            "actions": list(self.actions),
        }


class RecoveryController:
    """Execute at most one bounded repair pass.

    A repair action must be supplied by the canonical stage owner. The
    controller never discovers or invents recovery paths dynamically.
    """

    MAX_ACTIONS = 4

    def __init__(self, *, max_actions: int = MAX_ACTIONS):
        self.max_actions = max(1, min(int(max_actions), self.MAX_ACTIONS))

    def run(
        self,
        actions: list[RecoveryAction],
        *,
        stop_on_failure: bool = True,
    ) -> RecoveryResult:
        selected = actions[: self.max_actions]
        if not selected:
            return RecoveryResult("READY", "no_recovery_actions", 0, [])

        results: list[dict[str, Any]] = []
        for action in selected:
            try:
                raw = action.run()
                result = dict(raw) if isinstance(raw, dict) else {
                    "status": "FAIL",
                    "reason": "invalid_action_result",
                }
            except Exception as exc:
                result = {
                    "status": "FAIL",
                    "reason": "recovery_action_exception",
                    "error": str(exc),
                }
            result["action"] = action.name
            results.append(result)

            if stop_on_failure and result.get("status") not in {"PASS", "READY", "RECOVERED"}:
                return RecoveryResult(
                    "BLOCKED",
                    "recovery_action_failed",
                    len(results),
                    results,
                )

        return RecoveryResult(
            "RECOVERED",
            "bounded_recovery_pass_complete",
            len(results),
            results,
        )


__all__ = ["RecoveryAction", "RecoveryController", "RecoveryResult"]
