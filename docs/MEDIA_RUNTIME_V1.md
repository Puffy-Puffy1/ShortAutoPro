# ShortAutoPro Media Runtime V1

This hotfix aligns the real Termux media-selection runtime with the Consolidation 3.0 single-pipeline architecture.

## Production authority

`visual_engine_unified.py` is the sole production reranker. Query expansion remains enabled only to enrich the candidate pool. VI6 runs in SHADOW for telemetry. VSE4.2/VG4X legacy decision bridges are disabled by `media_runtime_adapter_v1.py`.

## Candidate normalization

Provider candidates are normalized at the acquisition boundary before canonical scoring:

- `descricao` -> `description`
- `fonte` -> `provider`
- `tipo` -> `media_type`
- legacy dimensions -> canonical dimensions when present
- `must_coverage` is derived from the provider's literal `must_hits`

Visual Unified now preserves `must_have` as a structured scene field so VSE independently re-verifies every explicit MUST against the asset metadata instead of trusting a declared hit.

## Missing providers

If the Pexels key is absent, Pexels is skipped once with an explicit diagnostic. Pixabay, Wikimedia, Coverr and local fallback remain available according to configuration.

## Contextual rescue

Contextual rescue is available only in the existing relaxed retry path after strict MUST selection fails. It never fabricates a MUST match. A rescued candidate remains `must_hits=0`, is treated as low-trust metadata, and must satisfy minimum semantic score, zero avoid hits, no explicit geographic contradiction and no identity-sensitive risk.

Literal/verified MUST candidates always keep priority over contextual rescue.

## Regression protection

The repository audit and simulated tests require the canonical adapter, structured MUST behavior, provider skip behavior, single visual authority and safe contextual rescue policy.
