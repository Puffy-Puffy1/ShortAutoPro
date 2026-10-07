# ShortAutoPro — Canonical Architecture Legacy Classification

Status: working classification for PR #148. This document is a safety inventory, not permission to delete files.

## A — Canonical production path

- `main.py`
- `first_video.py`
- `pipeline_contracts.py`
- `media_acquisition_v3.py`
- `media_v3/*`
- `render_plan_v2.py`
- `render_engine_v2.py`
- canonical Technical/Professional/Release QA
- `production_recovery.py`

These components form the production contract. New code must connect through their contracts instead of bypassing them.

## B — Compatibility/dependencies

- legacy manifest readers/adapters that are still required by compatibility tests
- V1/V2 adapters that explicitly terminate at the V3 boundary
- Remotion validation/bundling checks where they do not become an Android runtime dependency

Compatibility code may remain temporarily, but it must not become the production authority.

## C — Recovery

- `recovery_controller.py` is the single orchestration boundary.
- `production_recovery.py` is a compatibility entrypoint that delegates one bounded pass to `RecoveryController`.
- Specialized repair helpers may remain while their call graph is audited; they do not orchestrate one another.
- Recovery must be bounded: retry/fallback/repair, then fail with evidence.
- No recovery helper may select render providers or own the render pipeline.

## D — Legacy candidates — do not delete blindly

- `media_stage_runtime.py`
- `media_engine_v2.py`
- `media_provider_v2.py`
- `media_provider_router_v2.py`
- older VI6 recovery/gate modules
- `media_acquisition_recovery.py` when used as a standalone orchestration layer; its retrieval policy must terminate at the V3 acquisition contract
- `shortauto_repair_engine.py` is a legacy compatibility/planning engine only; canonical production entrypoints must use `production_recovery.py` → `RecoveryController`
- `media_master_gate.py` and `media_strict_must_guard.py` are policy/compatibility layers, not competing acquisition engines
- `midia.py` if present in a checked-out historical/runtime copy
- `vi6_13_recovery_planner.py`, `vi6_17_recovery_router.py`, `vi6_19_true_recovery.py`, `vi6_20_recovery_normalizer.py`, `vi6_21_recovery_circuit.py` — legacy VI6 recovery chain; retained only while compatibility tests/older tooling still reference them
- `vg4x_bridge.py` — compatibility bridge; it may install legacy policy helpers for older callers, but it is not a canonical production seed

The correct retirement sequence is:
1. prove no canonical production import;
2. prove no required compatibility/test dependency;
3. replace any remaining bridge with a V3 contract;
4. run architecture + unit + integration tests;
5. retire in a dedicated commit;
6. rerun the full pipeline.

## E — Orphan candidates

Any tracked `.py`/ `.sh` file that is neither reachable from an approved seed nor deliberately declared as a compatibility/recovery entrypoint is an orphan candidate.

An orphan is not automatically safe to delete: generated/runtime files, manual recovery entrypoints and test fixtures require explicit classification.

## Non-negotiable boundary

The canonical runtime must never import or invoke the old Media Stage/Media Engine V2/provider-router runtime.

The repository audit now fails if those legacy runtime references are reintroduced into the canonical path.


## Legacy dependency audit — 2026-10-07

The current canonical seeds were checked for direct imports of the legacy recovery/gate set. The canonical seeds do not import:

- `media_acquisition_recovery`
- `media_external_resilience`
- `media_master_gate`
- `media_strict_must_guard`
- `shortauto_repair_engine`
- the VI6 recovery chain listed above

Important exception: `vg4x_bridge.py` remains a compatibility bridge and still contains legacy policy installation hooks. It is therefore not classified as canonical. It must not be introduced into `main.py`, `first_video.py`, Media Acquisition V3, Render Plan V2, Render Engine V2, or RecoveryController.

The remaining legacy files are **not deleted in this phase** because the repository still contains dedicated compatibility/simulation tests for older media/recovery behavior. Their retirement requires either migrating those tests to canonical contracts or explicitly quarantining them before deletion.


## Test-suite separation — 2026-10-07

The test corpus now has an explicit boundary:

- `tests/` is the canonical contract suite. Tests here may not import the retired Media V2/Stage 6 runtime.
- `tests_compat/legacy_media/` is the quarantined compatibility suite for historical Media V2, Stage 6, `midia.py`, and recovery behavior.
- `tests_sim/` remains a historical simulation corpus. It is not treated as a production graph root and is not allowed to make legacy runtime code appear production-reachable.
- The canonical CI workflow executes the canonical suite and the boundary guard; it does not use the quarantined legacy suite as production qualification.
- Legacy compatibility tests remain preserved for migration/reference. They are not evidence that the retired architecture is part of the canonical runtime.

This separation is intentional: a test that proves legacy behavior is useful during retirement, but it must not silently define the architecture that the production pipeline is required to use.


## First legacy retirement — 2026-10-07

The first legacy runtime block has been retired from the branch:

- `media_stage_runtime.py`
- `media_engine_v2.py`
- `media_provider_v2.py`
- `media_provider_router_v2.py`
- `shortauto_repair_engine.py`

Evidence for retirement:
1. These modules are outside the canonical production seeds.
2. Canonical tests contain zero imports of these modules.
3. Their historical tests were already separated from `tests/` into `tests_compat/legacy_media/`.
4. The historical V2/Stage 6 tests for the retired block are now archived as `.py.disabled`, so they cannot be mistaken for executable qualification.
5. The canonical runtime uses Media Acquisition V3 + ProviderRegistry + RecoveryController.

This is a retirement, not a destructive rewrite: the implementation remains recoverable from Git history, while the active branch no longer exposes the retired engines as runtime modules.


## Second legacy retirement — 2026-10-07

A second compatibility/recovery block has now been retired from the active branch:

- `media_acquisition_recovery.py`
- `media_master_gate.py`
- `media_strict_must_guard.py`
- `midia.py`
- `vg4x_bridge.py`
- `vi6_13_recovery_planner.py`
- `vi6_17_recovery_router.py`
- `vi6_19_true_recovery.py`
- `vi6_20_recovery_normalizer.py`
- `vi6_21_recovery_circuit.py`

Evidence:
1. Canonical production seeds were checked for imports and none of these modules are part of the canonical graph.
2. `media_v3` owns provider selection/acquisition; `RecoveryController` owns bounded recovery orchestration.
3. The old bridge only connected retired adapters/policy helpers and therefore no longer has a legitimate canonical boundary to serve.
4. Historical compatibility tests for `media_acquisition_recovery`, `media_strict_must_guard`, and `midia.py` are archived as `.py.disabled`.
5. `media_external_resilience.py` is intentionally retained for now because `wikimedia_source.py` still imports it; it will not be removed until that dependency is migrated or explicitly classified.

The retirement is non-destructive: all retired implementations remain recoverable from Git history. The active branch now prevents these modules from silently becoming production authorities.


## Third legacy retirement — 2026-10-07

`media_external_resilience.py` has now been removed from the active branch. Its provider-health, retry, and asset-quarantine authority was redundant with the canonical `ProviderRegistry` + `MediaAcquisitionV3` boundary.

`wikimedia_source.py` remains only as a thin compatibility shim that delegates directly to `media_v3.providers.WikimediaAdapter`; it no longer owns provider health, retries, or acquisition policy.

The historical Wikimedia/resilience tests remain present only as explicitly skipped compatibility artifacts and are no longer production qualification gates.
