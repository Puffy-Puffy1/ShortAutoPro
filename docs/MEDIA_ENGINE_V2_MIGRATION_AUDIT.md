# ShortAutoPro — Media Acquisition V3 / Media Engine V2 Retirement Audit

Base for migration: `main` at `42f0e8f84e599d7b1b39471274dd898901f6de80`
Migration branch: `feat/media-acquisition-v3-migration-20261003`
PR: #141

## 1. Root-cause evidence

The production error:

`media_engine_v2.py --short-id ... returned non-zero exit status 1`

is only an outer-process diagnosis. The earlier confirmed V2 failure was `MEDIA_INCOMPLETE:scene_04:providers_empty`: the provider router exhausted its search path for a scene query and the monolithic V2 boundary surfaced only the terminal failure.

PR #140 added bounded query variants, but the Termux production run still demonstrated that patching the V2 block was not sufficient. The architectural decision is therefore to move acquisition responsibility to V3 rather than add another recovery layer around V2.

The V3 branch removes V2 from the canonical `main.py` execution path and, after green qualification, removes the obsolete V2 acquisition/controller files. Render Engine V2 remains active and is not part of this retirement.

## 2. Canonical production flow

```
ROTEIRO
  -> SCENE DIRECTOR / VISUAL PLANNING
  -> MEDIA ACQUISITION V3
       planner -> query variants -> provider registry
       -> candidate pool -> relevance/MUST/AVOID
       -> download -> technical validation
       -> diagnostics -> frozen media-manifest-v2
  -> RENDER PLAN V2
  -> AUDIO / SUBTITLES
  -> PRE-RENDER / RECOVERY
  -> RENDER ENGINE V2
       -> Remotion where supported
       -> FFmpeg on Termux/Android
       -> FFprobe
       -> Quality Gate
  -> atomic final MP4
```

Render Engine V2 does not query media providers.

## 3. V3 components

- `media_acquisition_v3.py`: manifest orchestration, resume validation and atomic persistence.
- `media_v3/query.py`: bounded progressive query plan.
- `media_v3/providers.py`: provider registry/adapters and credential status.
- `media_v3/acquisition.py`: candidate acquisition, scoring, fallback, download and validation.
- `media_v3/diagnostics.py`: typed per-scene diagnostics.
- `media_validator_v2.py`: retained technical validator boundary; it is not a provider or renderer.
- `media-manifest-v2`: retained as the frozen interchange contract so Render Engine V2 does not need a schema rewrite.

## 4. Provider failure semantics

V3 distinguishes:

- `NO_API_KEY`
- `PROVIDER_UNAVAILABLE`
- `TIMEOUT`
- `RATE_LIMIT`
- `ZERO_RESULTS`
- `HTTP_ERROR`
- candidate rejection
- technical validation failure

A provider returning candidates does not resolve a scene. Candidates must survive technical validation and semantic rules before entering the frozen manifest.

If all candidates from one query are rejected, V3 continues with the next bounded query variant and then the next provider.

## 5. MUST / AVOID policy

- HARD MUST remains fail-closed.
- SOFT MUST contributes relevance.
- AVOID remains a rejection/penalty boundary.
- No placeholder/slate/editorial-reuse asset is accepted as a success substitute.
- Query expansion changes retrieval only; it does not weaken the acceptance contract.

## 6. Isolation and recovery

Every media artifact is scoped by `SHORT_ID`.

Frozen manifests and sidecars contain identity/checksum information and are written atomically.

Resume revalidates:

- SHORT_ID
- scene number
- scene ID
- checksum
- technical media validation
- manifest integrity

Recovery calls V3 and Render Plan V2 only on the canonical path; it does not re-enter Stage 6.

## 7. Render preservation

Render Engine V2, FFmpeg, FFprobe, Remotion, subtitles, audio and Quality Gate are preserved.

The migration does not replace the renderer. It replaces only the unstable acquisition boundary.

## 8. Legacy classification

| Component | Classification during migration |
|---|---|
| `media_engine_v2.py` | REMOVED |
| `media_provider_v2.py` | REMOVED |
| `media_provider_router_v2.py` | REMOVED |
| `media_stage_runtime.py` | REMOVED |
| `midia.py` | LEGACY provider implementation retained only until final parity/cleanup gate |
| `render_plan_v2.py` | ACTIVE |
| `render_engine_v2.py` | ACTIVE |
| `render_v2/ffmpeg_visual_renderer.py` | ACTIVE |
| `media_v3/*` | ACTIVE migration target |

## 9. Validation status

The branch has already produced real GitHub evidence for:

- V3 unit tests: PASS
- V3 acquisition/render integration: PASS
- Render V2 contract: PASS
- Render V2 stress workflow: still under qualification
- Portable validation: previous run exposed one repository-audit defect; that defect was isolated to the architecture graph and is being corrected, not suppressed

The GitHub qualification gates now include real 1/2/5/10 end-to-end FFmpeg jobs, failure injection, resume/isolation coverage and green portable/render checks. The migration is still not complete until this cleanup branch itself is merged to `main`, `main` is green, `termux-stable` is synchronized, and Termux 1/2/5/10 validation is performed.

## 10. Non-negotiables

- GitHub is the source of truth.
- No Termux changes during migration.
- No destructive reset.
- No placeholder success.
- No disabled Quality Gate.
- No infinite retries.
- No false PASS.
