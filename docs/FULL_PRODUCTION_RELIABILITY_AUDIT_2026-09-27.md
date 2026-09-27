# FULL PRODUCTION RELIABILITY AUDIT — 2026-09-27

## Scope and baseline
Baseline inspected: `main` and `termux-stable` at `79fb95ee165dbd5125f40ddd61da71ff56af6355`.
Mission focus: continuous sequential production, exact identity, batch recovery, state isolation, locks, Stage 6 regressions and release truth.

## Findings

### CRITICAL — partial batch item re-entered fresh-run path
**Location:** legacy `batch_recovery.sh` loop + `main.py:allocate_id`.

The batch assigned deterministic IDs, but a resumed partial item invoked `main.py run`. Normal run deliberately refuses an ID that already owns artifacts and can allocate a new ID. The batch then checked the old ID. This can make a recoverable item impossible to complete under its batch identity.

**Correction:** canonical `batch_runtime.py` selects fresh only for artifact-free QUEUED items. Any item with artifacts/checkpoint or recovery status invokes `main.py resume --short-id <exact-id>`.

### CRITICAL — recoverable item aborted the whole batch
**Location:** legacy `batch_recovery.sh`.

A failed item was saved as retry_pending followed by immediate exit. Items after it were never attempted.

**Correction:** recoverable failures become per-item `RETRY_PENDING`; first pass continues later items; bounded recovery rounds revisit only pending items.

### HIGH — contiguous batch state could not represent holes
**Location:** legacy `queue/batch_state.json` schema.

`current/successes/failures` assumed contiguous progress and could not faithfully represent item 2 failed while 3–10 completed.

**Correction:** `BATCH_STATE_3.0_PER_ITEM` with stable item identity, status, attempts, recovery count, error class/code, exit code, release/output/log fields and atomic replace.

### HIGH — two batch implementations could drift
**Location:** `batch_queue.sh`, `batch_recovery.sh`.

**Correction:** both are compatibility wrappers over one canonical Python runtime.

### HIGH — inherited transient environment could contaminate the next Short
Batch subprocesses inherited caller state including Short/topic/recovery variables.

**Correction:** each item builds a subprocess environment that explicitly removes `SHORT_ID`, `SAP_REUSE_SHORT_ID`, `SHORT_TOPIC_EXACT`, `SHORT_ALLOW_REPEAT_TOPIC` and recovery transients, then injects only its exact Short identity.

### HIGH — batch success could be inferred too early
Exit code alone is insufficient.

**Correction:** an item is `COMPLETED` only after `release_artifact_guard.py --short-id <exact-id>` passes. Existing exact releases are idempotently accepted without rerunning the item.

### HIGH — batch runner serialization
Concurrent batch runners can race on one state file.

**Correction:** stable `flock` inode in `queue/.batch_runtime.lock`; active owner blocks a second runner and lock release is scoped by context manager.

### MEDIUM — manual resume UI did not require explicit identity
**Location:** `control_center.sh`.

**Correction:** “Retomar Short” now asks for and passes `--short-id`.

## Preserved contracts
No neutral slate/placeholder relaxation was introduced. No explicit MUST relaxation was introduced. Stage 6 provider circuit v1.2 behavior remains intact: controller deadline is not provider health debt, EMPTY is query-specific, transient family failures are deduplicated, and AUTH/RATE_LIMIT protections are retained.

## New regression coverage
`tests/test_batch_runtime.py` covers:
- ten unique per-item IDs and valid atomic JSON;
- artifact-bearing partial item uses exact-ID resume;
- artifact-free item uses fresh run;
- failure in the middle does not prevent later items and is recovered later;
- already completed items are not repeated after interruption/resume;
- cross-video transient environment variables are stripped.

Existing repository CI remains responsible for compile/syntax, deployment smoke, simulated regressions, Critical Stage 6 Gate, JSON integrity, FFmpeg synthetic E2E, Bash syntax, pipeline contract and repository audit.

## Residual risks / real-device qualification
Mocked CI cannot prove external provider availability, Android memory pressure, real API rate-limit behavior or real network quality. Those failures must not corrupt batch state. Real-device qualification must progress 1 Short → immediate second Short → batch 2 → batch 5 → batch 10.

## Acceptance checklist
- [x] Fresh/resume architectural conflict corrected.
- [x] Per-item state introduced.
- [x] Recoverable middle failure no longer terminates first pass.
- [x] Exact Short ID release verification.
- [x] Environment isolation.
- [x] Canonical batch engine.
- [x] Bounded retry policy.
- [x] Atomic state/report writes.
- [x] Stable batch flock.
- [x] 10-item deterministic simulated coverage.
- [ ] PR exact-head CI green (must be verified after final commit).
- [ ] Merge and post-merge CI.
- [ ] Promote `termux-stable`.
- [ ] Real Android qualification.
