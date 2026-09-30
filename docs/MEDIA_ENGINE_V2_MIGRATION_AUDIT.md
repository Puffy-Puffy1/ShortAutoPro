# ShortAutoPro — Media Engine V2 Migration Audit

Base: `main` at `bbf16716b2e6a46271b778a5b2a2cde879e3b5c4`
Migration branch: `feature/retire-stage6-media-engine-v2`

## Architectural inventory

| Component | Previous responsibility | V2 owner | Migration status |
|---|---|---|---|
| `media_stage_runtime.py` | acquisition orchestration, recovery, editorial tail | Media Engine V2 | bypassed from main production path |
| `midia.py` | mature provider search/download/semantic selection | `media_provider_v2.py` adapter boundary | preserved behind adapter |
| `media_master_gate.py` | media completeness gate | Media Engine V2 manifest validation + downstream gates | bypassed from main path |
| `shortauto_asset_library.py` | validated local asset index | Media Engine V2 final acquisition fallback | integrated as validated fallback |
| `professional_edit_director.py` and repair chain | edit-plan generation | Render Plan V2 / Render Engine V2 | bypassed from main path |
| `motion_director.py`, `rhythm_director.py` | presentation planning | Render Engine V2 | bypassed from main path |
| `retention_engine.py` | editorial repair | Render planning/quality policy | bypassed from main path |
| `production_recovery.py` | mixed media/edit recovery | Job/Batch Runtime + Media/Render boundaries | refactored |
| `render_engine_v2.py` | composition/render/FFmpeg/FFprobe | Render Engine V2 | preserved, now consumes frozen media manifest |
| FFmpeg | multimedia processing | Render Engine V2 backend | preserved |
| FFprobe | technical inspection | Render Engine V2 / final quality boundary | preserved |
| Batch Runtime | job identity/state/recovery | Batch/Job Runtime | preserved |

## New production path

```
ROTEIRO
  -> MEDIA ENGINE V2
       search -> bounded provider fallback -> download -> validation
       -> media-manifest-v2 (frozen)
  -> RENDER PLAN V2
  -> audio/captions
  -> RENDER ENGINE V2
       -> FFmpeg on Android/Termux
       -> Remotion where supported
       -> FFprobe
       -> Quality Gate
       -> atomic final MP4
```

## Non-goals

- No Termux development during migration.
- No destructive deletion of the legacy code before qualification.
- No provider/API requirement in deterministic CI.
- No weakening of MUST verification.
- No placeholder media acceptance.
- No new SHORT_ID during resume/retry.

## Current risk

The provider implementation is still physically hosted in `midia.py`. It is no longer invoked through the old production controller, but the provider extraction into dedicated provider modules is a later migration checkpoint. This is intentional so the first architectural cut remains reversible and testable.

## Optimization and cleanup checkpoint

- Provider calls now cross one explicit adapter boundary.
- Local assets are accepted only when stored provenance, SHA-256 and technical validation pass.
- Partial per-scene assets require a validated sidecar before reuse on resume.
- Frozen manifests require immutable=true and complete MUST evidence.
- Final MP4 validation no longer depends on an arbitrary 500 KB threshold; Render Engine V2 remains authoritative through FFprobe and Quality Gate.
- CI keeps legacy Stage 6 tests as compatibility regression coverage, but the production path is audited to bypass the Stage 6 controller.
- Local Android/Remotion build directories are ignored and never become production source.
