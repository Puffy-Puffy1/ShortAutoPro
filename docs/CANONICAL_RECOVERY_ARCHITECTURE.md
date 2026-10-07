# Canonical Recovery Architecture

## Single authority

The canonical recovery boundary is:

- `production_recovery.py::RecoveryController`

It performs at most one bounded repair pass per invocation. It is corrective, fail-closed, and evidence-driven.

## Responsibilities

RecoveryController may:

1. inspect preflight evidence;
2. repair a canonical upstream artifact;
3. rebuild Media Acquisition V3 artifacts when media is invalid;
4. rebuild Render Plan V2 when the plan is invalid;
5. rebuild audio/captions when those artifacts are invalid;
6. stop immediately when the problem is non-repairable or the repair pass fails.

RecoveryController must **not**:

- select providers;
- relax MUST constraints;
- call Stage 6;
- call Media Engine V2;
- call Provider V2;
- invoke another recovery engine;
- retry indefinitely;
- decide rendering policy.

## Legacy systems

The following remain compatibility/legacy until a dependency audit proves they can be removed:

- `shortauto_repair_engine.py`
- `media_acquisition_recovery.py`
- `media_external_resilience.py`
- `vi6_13_recovery_planner.py`
- `vi6_17_recovery_router.py`
- `vi6_19_true_recovery.py`
- `vi6_20_recovery_normalizer.py`
- `vi6_21_recovery_circuit.py`

They are not allowed to become a second canonical recovery authority.

## Termination guarantee

The canonical controller caps attempts at one. A failed repair returns BLOCKED with evidence; it does not recurse into another recovery system.

This is intentional: recovery must be bounded and observable rather than a loop that hides the original failure.
