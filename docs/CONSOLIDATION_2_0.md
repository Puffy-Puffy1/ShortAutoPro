# ShortAutoPro Consolidation 2.0

Date: 2026-09-15

## Objective

Consolidation 2.0 turns the staged Professional rollout into one canonical runtime architecture, removes historical/dead worktree content, and adds fail-closed repository auditing.

## Canonical execution

- `gerar_short.sh` is the only Short generation orchestrator.
  - `SAP_PRO_EDIT=1` (default): Professional path.
  - `SAP_PRO_EDIT=0`: explicit standard rollback.
- `profile_run.sh` always calls `gerar_short.sh` after exporting the selected profile.
- `v6_runtime.py` is the only V6 supervisor.
  - Professional mode renders through `v6_professional.py`.
  - rollback mode renders through `v6.py`.
- `resume_short_runtime.py` is the only safe-resume runtime.
- `resume_short.sh` always calls the unified resume runtime.

The Professional implementation files `video_professional.py` and `v6_professional.py` remain because they are distinct edit/render implementations, not duplicate orchestration layers.

## Removed obsolete paths

The following rollout/migration artifacts were removed from the current tree:

- `gerar_short_professional.sh`
- `professional_pipeline_runtime.py`
- `resume_short_professional_runtime.py`
- `v6_professional_runtime.py`
- `tools/apply_consolidation_1_0.py`
- `_arquivo_historico/2026-09-15_pre_consolidation/`
- `.resume_vi710_after_semantic_fix.sh.pre_segment_fix`
- `31`
- `SYNC_TEST.TXT`

They remain recoverable from Git history; they are not shipped to the Termux operational worktree.

## Production bug fixes

### Exact video identity

An explicit Short ID without its own final render no longer falls back to another Short's newest V6 file. This prevents false technical health/quality scores after failed productions.

### Profile recovery

Manual Evolution audits can recover the production profile from:

1. current `SAP_CHANNEL_PROFILE`, when present;
2. `pro_edit_plan_<short_id>.json`;
3. the Professional manifest;
4. the owning client job.

This prevents a `true_crime` production from being mislabeled `default` only because the original shell process ended.

### Final status reporting

The canonical pipeline no longer prints a fixed `STATUS: QUALITY PASS`; it reports the quality state actually computed by the final gates.

## Safe resume contract

Professional partial resume requires both normal artifact validation and a valid `pro_edit_plan` covering the configured scene count. If the plan is missing, resume fails closed to a full rerun rather than mixing standard and Professional edit paths.

## Evolution compatibility

The pre-consolidation Evolution implementation is preserved as `shortautopro_evolution_core.py`. `shortautopro_evolution.py` is a compatibility facade that applies the exact-video/profile-context fixes while preserving the established import surface and test/runtime assignment behavior.

## Permanent audit

`tools/repo_audit.py` blocks the repository when:

- an obsolete wrapper or historical worktree file returns;
- a required canonical runtime disappears;
- Professional/rollback integration tokens disappear from the canonical pipeline;
- the fixed fake final PASS string returns;
- any `.py` or `.sh` becomes unreachable from operational entrypoints, tests, or workflows.

`tools/map_active_graph.py` no longer treats documentation as a code root. Documentation can describe historical files without accidentally keeping them alive.

## Validation policy

The portable GitHub validator now runs on pull requests as well as `main` pushes. Promotion remains separate and may only advance an exact validated `main` commit to `termux-stable` using fast-forward-only promotion.

Before this consolidation was accepted on the PR branch:

- Python compile passed;
- 259/259 simulated regression tests passed;
- Bash syntax passed;
- unified Professional pipeline contract passed;
- repository architecture audit passed with no unreachable code;
- required FFmpeg capabilities passed.
