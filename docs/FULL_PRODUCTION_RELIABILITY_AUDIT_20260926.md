# FULL PRODUCTION RELIABILITY AUDIT — 2026-09-26

## Scope

Repository: `Puffy-Puffy1/ShortAutoPro`

Baseline audited before changes:
- `main = 79fb95ee165dbd5125f40ddd61da71ff56af6355`
- `termux-stable = 79fb95ee165dbd5125f40ddd61da71ff56af6355`
- no open PR at mission start
- inventory: 415 tracked files, 312 Python, 15 shell, 67 JSON, 142 simulated test files

This audit did not recreate the project or replace the canonical professional pipeline. The existing `main.py`, Stage 1–6 chain, render stack, QA gates and release gate remain authoritative.

## Executive summary

The primary reliability defect was architectural rather than a single media bug: batch orchestration duplicated production-state rules outside the canonical runtime. The old recovery path stored only contiguous counters and called a fresh `main.py run` when a partially produced deterministic batch ID already had artifacts. That conflicts with the fresh-run identity contract and could cause a resumed batch item to execute under a different Short ID while the batch still waited for the original ID.

The second critical defect was failure propagation: a recoverable failure in one item caused `batch_recovery.sh` to exit immediately, preventing later healthy items from running.

The remediation introduces one canonical sequential batch engine with per-item state, exact identity, exact release validation, bounded recovery, global-vs-item failure classification, atomic state, stable flock locking, transient environment isolation, storage preflight, structured logs and reports.

## Findings

### CRITICAL — partial batch item could return through fresh-run path

**Files:** previous `batch_recovery.sh`, `main.py`

**Root cause:** deterministic `SHORT_ID=batch_id_XX` was exported and recovery called `main.py run`. A normal run intentionally refuses to reuse an ID when artifacts already exist.

**Impact:** batch item identity and produced release could diverge; a partial item could become impossible to finalize under the ID the batch expected.

**Fix:** `batch_runtime.py` decides per item:
- no artifacts + queued => fresh `main.py run`
- partial/running/retry state => `main.py resume --short-id <exact-id>`
- completed => exact release revalidation; never rerun when valid

### CRITICAL — one recoverable Short aborted the remaining batch

**File:** previous `batch_recovery.sh`

**Root cause:** first failed item stored `retry_pending` and immediately exited.

**Impact:** a temporary provider/render failure in item 2 could prevent items 3–10 from being attempted.

**Fix:** recoverable item failures are deferred, later queued items continue, then bounded recovery rounds retry deferred IDs. Only a classified global blocker halts the batch.

### CRITICAL — contiguous batch state could not represent sparse success/failure

**File:** previous `queue/batch_state.json` schema

**Root cause:** `current/successes/failures/last_completed_index` assumed contiguous progress.

**Impact:** impossible to represent 1 PASS, 2 retry, 3 PASS safely.

**Fix:** `BATCH_STATE_3.0_PER_ITEM` stores per item:
`index, short_id, status, attempts, recovery_count, timestamps, last_stage, last_error, error_class, exit code, topic, release, output path, log path`.

Atomic JSON replacement is used for every state write.

### CRITICAL — persisted completion could become a false PASS

**File:** new batch migration/execution path

**Root cause found during cross-review:** trusting an old `current` or persisted `completed` label without checking the release artifact can preserve a stale/corrupt success.

**Fix:** migrated and current completed items are revalidated with `release_artifact_guard.py --short-id <exact-id>`. A failed revalidation becomes queued/retry work instead of being silently skipped.

### HIGH — transient per-Short environment could leak into the next item

**Areas:** `SHORT_ID`, `SAP_REUSE_SHORT_ID`, topic overrides, media/recovery flags

**Fix:** each subprocess receives a freshly constructed environment with known transient keys removed and only the current item’s `SHORT_ID` reintroduced. Fresh and resume mode are explicit.

### HIGH — Stage 6 resilience migration was memory-only until a later write

**File:** `media_external_resilience.py`

**Root cause:** v1.1→v1.2 cleanup of stale transient provider circuit debt modified memory but did not immediately persist the migrated snapshot.

**Impact:** another Python process could reload the old transient debt and repeat the bad state.

**Fix:** migration now atomically writes v1.2 immediately while preserving long-lived AUTH/RATE_LIMIT protections.

### HIGH — storage cleanup did not know about batch items waiting for recovery

**File:** `storage_manager.py`

**Impact:** a `retry_pending` Short can temporarily have no active run flock while still depending on partial media/temp artifacts.

**Fix:** active/protected IDs now include batch items in `running`, `recovering`, `retry_pending` and `blocked_global`. Batch preflight estimates free-space need before item 1 based on batch size.

### HIGH — local approved asset library existed but was not usable as a strict fallback

**Files:** `shortauto_asset_library.py`, `media_stage_runtime.py`

**Existing safety:** the library indexes media only after Media Master Gate PASS.

**Fix:** Stage 6 can now reuse a local asset only when:
- source file still exists and is non-trivial
- source and license are known
- quality >= 78
- requested MUST entities are a subset of indexed entities
- requested location/era match when present
- metadata came from a previously approved asset

Unknown/local-random files cannot satisfy MUST. The fallback runs before editorial reuse; neutral slates remain prohibited for production.

### MEDIUM — duplicate batch implementations could drift

**Files:** `batch_queue.sh`, `batch_recovery.sh`

**Fix:** both are now thin wrappers around `batch_runtime.py`. Control Center can keep invoking the same shell interfaces without duplicating ID/retry/state policy.

### MEDIUM — fixed cooldown ignored failure context

**Fix:** the canonical runtime applies bounded adaptive inter-item/backoff delays: rate limits receive longer delay; timeouts receive intermediate delay; healthy runs stay short. This does not reset provider circuits or bypass Retry-After/provider health controls.

## Canonical batch architecture

```
control_center.sh / batch_queue.sh / batch_recovery.sh
                         |
                         v
                  batch_runtime.py
                         |
       +-----------------+-----------------+
       |                                   |
 fresh item                         partial/retry item
 main.py run                 main.py resume --short-id X
       |                                   |
       +-----------------+-----------------+
                         |
               release_artifact_guard
                         |
            per-item state + report
                         |
          continue next safe item
                         |
             bounded recovery rounds
```

Complete Shorts execute sequentially. Parallelism remains confined to safe internal provider/media work.

## Failure classes

Batch runtime distinguishes:
- `GLOBAL_BLOCKER`: e.g. STORAGE_LOW, CONFIG_INVALID
- `PERMANENT_ITEM`: e.g. MEDIA_SEMANTIC_FAILURE, AI_CONTENT_BLOCK
- `RECOVERABLE`: provider timeout, rate limit, media incomplete, render/QA/release block, lock contention, state issue, unknown exception

A recoverable item does not automatically kill later items. Retry count and recovery rounds are bounded.

## Locks and interruption

- canonical batch lock uses `flock`
- lock inode is kept stable
- stale text/PID inside an unlocked flock file does not block a new runner
- an actually held flock blocks a second runner
- SIGINT/SIGTERM converts active work to resumable state and atomically persists the batch before exit
- per-Short locking remains owned by `main.py` / `resume_short_runtime.py`

## Release contract

Batch success never means only “subprocess returned 0”.

An item becomes `completed` only after exact-ID `release_artifact_guard` PASS. Existing render/visual/audio/manifest/release gates remain authoritative, including neutral-placeholder and blank-opening protection.

## Stage 6 safety retained

The mission does not relax:
- explicit MUST
- Media Master Gate
- render preflight
- Visual QA
- neutral-slate rejection
- provider AUTH/RATE_LIMIT protection
- controller timeout separation from real provider timeout
- EMPTY being query-specific
- partial-media preservation

## Topic state

`register_topic.py` remains atomic/locked and normalized duplicate registration exits idempotently without rewriting a valid history file. Batch subprocess isolation removes stale `SHORT_TOPIC_EXACT` and `SHORT_ALLOW_REPEAT_TOPIC` inheritance from one item to the next.

A future product-level feature may add an explicit per-item topic list for a multi-video exact-topic batch; the batch engine does not silently propagate an inherited exact-topic variable.

## Test additions

New/expanded deterministic tests cover:
- immediate second fresh run gets a different ID
- batch 10 unique IDs/state entries
- partial item chooses exact-ID resume
- transient environment isolation
- item 3 failure does not stop items 4–5
- independent item 2 provider timeout + item 7 render failure recover separately
- global storage failure stops later work
- legacy contiguous-state migration
- stale persisted completion is rejected without exact release
- atomic state round-trip
- active batch flock blocks a duplicate runner
- stale lock-file content does not block
- exact release ID controls completion
- retry-pending batch media is storage-protected
- v1.1 Stage 6 transient circuit migration persists immediately
- verified local asset accepts valid provenance/MUST metadata
- verified local asset rejects unknown/mismatched metadata

CI additionally runs compileall, explicit AST parse, py_compile, import smoke, JSON parse, deploy smoke, full unittest discovery, Critical Stage 6 gate, FFmpeg synthetic E2E, Bash syntax, repository audit and optional ShellCheck.

## Risks intentionally not hidden

- CI uses deterministic mocks/synthetic media and does not prove internet/provider behavior on an Android device.
- Real-device qualification must still progress 1 Short → second immediate Short → batch 2 → batch 5 → batch 10.
- External services can still fail; the acceptance criterion is that external failure does not corrupt identity/state or create a false release.
- Verified local reuse is deliberately strict and may decline a usable-looking asset when provenance metadata is insufficient. That is preferred to weakening semantic safety.

## CI / promotion status

To be filled with exact workflow run, validated SHA, merge SHA and `termux-stable` comparison after the PR gate and post-merge gate complete.

## Android qualification checklist

1. Sync `termux-stable` with `automation/termux_bridge.sh`.
2. Run deploy smoke, preflight and health.
3. Produce one real Short and confirm exact release.
4. Immediately produce a second fresh Short and confirm distinct ID.
5. Run batch 2.
6. Run batch 5.
7. Only after those pass, run batch 10.
8. If interrupted, run batch resume and confirm completed items are not repeated.
9. Inspect `queue/batch_state.json` and `reports/batch/` for per-item outcomes.
