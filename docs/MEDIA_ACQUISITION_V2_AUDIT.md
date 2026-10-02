# Media Acquisition V2 Audit

## 1. Executive Summary

Audit target: `Puffy-Puffy1/ShortAutoPro`, HEAD `929f982a13fde6c6513506916603394630941ead`.

This is a **read-only architectural audit** of the current GitHub state. No production code was changed. A documentation-only branch `audit/media-acquisition-v2` was created from the exact HEAD after the initial state was recorded.

**Primary conclusion:** the production entrypoint has successfully moved from direct Stage 6 control to Media Engine V2, but the V2 acquisition boundary is **not yet independent of `midia.py`**. `media_provider_v2.py` lazily imports `buscar_todos_candidatos`, `preparar_candidatos` and `baixar_candidato_5_2` from `midia.py`. The import is especially dangerous because `midia.py` contains a top-level production scene loop rather than an import-safe module boundary. Therefore the claimed V2 separation is architectural, not runtime-independent.

A second concrete gap is that V2 acquisition selects only the first strict prepared candidate. If its download fails, V2 falls directly to Local Library rather than trying the next valid provider candidate. That is not the requested per-asset provider failover contract.

The current manifest is useful and validated with SHA-256/FFprobe, but `immutable=true` is a logical field; there is no manifest self-hash/write-once mechanism, and validation does not fully bind every asset path/provenance field to the current Short contract.

**Etapa B: NO-GO.**

The main blockers are:
1. remove the V2 -> `midia.py` runtime dependency without losing validated provider behavior;
2. create a true per-asset Provider Router/fallback contract;
3. extract technical Asset Validation independently;
4. prove Short isolation and manifest immutability;
5. add acquisition-specific 1/2/5/10, provider failure, timeout, empty, invalid asset, resume and contamination tests;
6. only then retire legacy acquisition code.

## 2. Repository State

| Item | Result | Evidence |
|---|---|---|
| Repository | `Puffy-Puffy1/ShortAutoPro` | GitHub repository metadata |
| Default branch | `main` | repository metadata |
| HEAD main | `929f982a13fde6c6513506916603394630941ead` | refs/heads/main |
| HEAD termux-stable | same SHA | refs/heads/termux-stable |
| main == termux-stable | **YES** | both refs resolve to same SHA |
| Latest commit | `feat: retire Stage 6 from production path and introduce Media Engine V2` | HEAD commit |
| PR #132 | merged | migration PR |
| PR #133 | merged | promotion PR |
| Local working tree | **UNKNOWN** | GitHub API exposes remote refs, not a local Termux working tree |
| Audit branch | `audit/media-acquisition-v2` | created from HEAD |
| Recent relevant Actions | success | Media Engine/Render V2 and promotion runs on current HEAD |

Current-head relevant workflow results observed:
- Promote Termux Stable: success.
- Render Engine V2: success.
- Render Engine V2 Stress: success on the migration sequence.
- Migration workflow and portable validation were part of the merge checkpoint, but their existing tests do not prove that `media_provider_v2` is independent of `midia.py`.

## 3. Current Production Path

Verified from `main.py`:

`main.py -> media_engine_v2.py -> media_provider_v2.py -> midia.py provider primitives`

Then:

`media_engine_v2.py -> render_plan_v2.py -> audio/captions -> production_recovery -> render_preflight -> render_engine_v2.py`

The direct Stage 6 controller is not invoked by `main.py`.

However, the acquisition boundary is not clean because:
- `media_engine_v2.py` imports `MediaProviderV2`;
- `MediaProviderV2` imports three functions from `midia.py`;
- those functions are not isolated provider adapters; they are embedded in a monolithic script.

Key evidence:
- `main.py:L384-L423`
- `media_engine_v2.py:L15-L29,L205-L245`
- `media_provider_v2.py:L14-L58`
- `midia.py:L1726-L4759`

## 4. Stage 6 Status

### Production path
**GREEN:** `main.py` no longer directly invokes `media_stage_runtime.py`.

### Legacy code existence
**YELLOW:** `media_stage_runtime.py`, VI6 modules and many Stage 6-era tests remain in the repository.

### Indirect resurrection risk
**RED:** `midia.py` still imports VI6/VI6.8/VI6.9/VSE42-related modules and contains the legacy acquisition/selection chain. Because V2 currently imports `midia.py`, legacy code can still execute through the V2 adapter boundary.

### Test-only legacy protection
The portable workflow intentionally still runs many Stage 6 regression tests. This protects old contracts but is not evidence that Stage 6 is absent from all runtime dependencies.

**Conclusion:** Stage 6 is bypassed at the canonical `main.py` controller level, but the repository is not yet legacy-free and the V2 provider boundary still reaches legacy acquisition code.

## 5. midia.py Overview

`midia.py` is not a small provider helper. It is a **large monolithic media runtime**.

It contains:
- configuration and API credentials;
- Short ID/environment resolution;
- topic/scene loading;
- HTTP sessions;
- incremental checkpoints;
- cache restoration;
- FFprobe checks;
- SHA-256;
- text normalization;
- semantic scoring;
- MUST/avoid scoring;
- Pexels/Pixabay/Coverr/Wikimedia/Local acquisition;
- candidate ranking;
- documentary evidence policy;
- failover;
- degraded fallback;
- Asset Library fallback;
- provider circuit interaction;
- bad-asset quarantine;
- visual intelligence;
- VSE42/VG4X/Visual Unified hooks;
- scene commit/provenance;
- the complete scene acquisition loop;
- final success/failure exit.

The file is approximately 159 KB and contains dozens of top-level functions plus a module-level production loop.

Most important architectural fact: the production scene loop begins at module scope around `midia.py:L5080+` and continues through the end of the file. There is no import-safe `if __name__ == "__main__"` boundary around that production loop.

## 6. Function-by-Function Audit

The following matrix covers every top-level function discovered in the current `midia.py`. Where a caller could not be proven conclusively by the current static inspection, the report uses **UNKNOWN** rather than inventing one.

| Function | Lines | Responsibility | Caller(s) | State/I/O | Failure/Safety | Classification | Verdict |
|---|---|---|---|---|---|---|---|
| __module__ | 1-~ | top-level production script; import-time execution | media_provider_v2._legacy imports midia; otherwise entrypoint | reads scene_map; writes media/checkpoints/reports | side effects on import; not idempotent as library | BUG | production side effects are outside a callable boundary |
| _sap_http_session | 197-218 | per-provider requests.Session cache | providers + baixar | global memory _HTTP_SESSIONS + lock | shared session, no semantic Short state | REUSABLE | safe if kept transport-only |
| _ler_topic | 244-258 | read topic | module init | topic files | missing file becomes empty | LEGACY | module initialization concern |
| _sap_atomic_media_checkpoint | 637-669 | incremental media checkpoint | scene loop | reports/media/acquisition_missing_<SID>.json | atomic write; PID/time | REUSABLE | SHORT_ID-scoped |
| _sap_probe_existing_media | 670-717 | probe cached visual asset | resume init | reads media file | ffprobe; technical only | REFACTOR | does not fully enforce V2 validation contract |
| _sap_sha256_existing | 718-~730 | hash existing asset | resume init | reads file | hash failure returns empty | REUSABLE | identity primitive |
| normalizar | 1075-1083 | normalize text | UNKNOWN/legacy scoring | memory | deterministic | LEGACY | not shown as current V2 boundary |
| tokenizar | 1085-1095 | tokenize text | normalizar/scoring helpers | memory | deterministic | REUSABLE | generic primitive |
| similaridade | 1097-1114 | token overlap score | avaliar_relevancia | memory | deterministic | REUSABLE | selection logic |
| similaridade_conjuntos | 1116-1138 | Jaccard-like overlap | UNKNOWN | memory | deterministic | NEEDS_INVESTIGATION | caller not conclusively identified |
| termo_presente | 1140-1184 | MUST/avoid term presence | avaliar_relevancia | memory | heuristic 75% token match | REFACTOR | semantic policy should leave legacy selector |
| avaliar_relevancia | 1186-1237 | candidate relevance score | provider functions | memory | deterministic heuristic | REFACTOR | mixes semantic policy with provider acquisition |
| baixar | 1239-1460 | HTTP download + technical probe + quarantine | baixar_candidato_5_2 | target .part + destination; global resilience | network/content-type/size/ffprobe; cleanup | REFACTOR | good transport primitive, wrong ownership |
| penalidade_usado | 1462-1474 | anti-repeat score penalty | provider functions | global `usados` set | process-global | ARCHITECTURAL RISK | not Short-scoped |
| marcar_usado | 1476-1494 | mark provider asset used | scene loop | global `usados` | process-global | ARCHITECTURAL RISK | can persist across scenes in same process |
| _vse42_cleanup_scene_sibling | 1496-1615 | remove sibling scene files after success | scene loop/fallbacks | filesystem in short media dir | destructive after success | LEGACY | VSE42-specific compatibility |
| _vse42_commit_safe | 1617-1664 | legacy candidate commit hook | local fallback | external visual bridge | fail-open warning | LEGACY | not needed in isolated acquisition |
| _sap_provider_diag_v1 | 1666-1724 | provider diagnostics | provider funcs | logs + resilience | may expose exception text; no secrets intentionally | REFACTOR | provider concerns belong adapters |
| pexels_video | 1726-1868 | Pexels video search | buscar_todos_candidatos | HTTP + Pexels key | returns [] on error | REFACTOR | provider adapter candidate |
| pexels_foto | 1870-1984 | Pexels image search | buscar_todos_candidatos | HTTP + Pexels key | returns [] on error | REFACTOR | provider adapter candidate |
| pixabay_video | 1986-2131 | Pixabay video search | buscar_todos_candidatos | HTTP + Pixabay key | returns [] on error | REFACTOR | provider adapter candidate |
| pixabay_foto | 2133-2240 | Pixabay image search | buscar_todos_candidatos | HTTP + Pixabay key | returns [] on error | REFACTOR | provider adapter candidate |
| coverr_video | 2242-2355 | Coverr video search | buscar_todos_candidatos | HTTP + Coverr key | returns [] on error | REFACTOR | provider adapter candidate |
| buscar_local | 2357-2407 | legacy local directory fallback | scene loop | midia_local global directory | random selection | LEGACY | not equivalent to validated Asset Library |
| aceitavel | 2409-2463 | legacy candidate acceptance gate | preparation/legacy selector | memory | MUST/score heuristic | LEGACY | must not be carried wholesale |
| simplificar_busca | 2465-2538 | query rescue generation | scene loop | memory | deterministic | REFACTOR | belongs acquisition retry policy |
| _sap_local_library_candidates | 2540-2562 | query persistent Asset Library | buscar_todos_candidatos | global .sap_state library | library fallback | REUSABLE | keep as resource access, isolate policy |
| buscar_todos_candidatos | 2564-3263 | orchestrate all providers, resilience, semantic filtering, library | scene loop + MediaProviderV2 | global provider state + candidates | parallelism, gates, rescue, quarantine | REMOVE | monolithic acquisition orchestrator |
| metadata_confiavel | 3265-3290 | legacy metadata trust heuristic | scene loop | memory | heuristic | REFACTOR | policy should be explicit validator |
| cobertura_must | 3292-3307 | MUST coverage calculation | candidato_semanticamente_valido/selection | memory | deterministic | REUSABLE | semantic primitive after verification |
| candidato_semanticamente_valido | 3309-3399 | strict candidate semantic gate | buscar_todos_candidatos | memory | fail closed depending inputs | REUSABLE | extract as validator policy |
| score_diversidade | 3401-3436 | candidate diversity score | UNKNOWN/prepare path | memory/global used | heuristic | REFACTOR | selection policy |
| score_semantico | 3438-3486 | semantic score | preparar_candidatos | memory | heuristic | REFACTOR | selection policy |
| preparar_candidatos | 3488-3581 | filter/rank candidate pool | MediaProviderV2.prepare; legacy selector | memory | relaxado flag; ranking | REFACTOR | core ranking to extract carefully |
| documentary_provenance_rank_5_4_2 | 3583-3693 | documentary provenance ranking | ordenar_documentais_5_4_2 | memory | heuristic/evidence metadata | REFACTOR | policy layer |
| ordenar_documentais_5_4_2 | 3695-3709 | documentary sort | escolher_documental_prioritario | memory | deterministic | REFACTOR | policy layer |
| escolher_documental_prioritario | 3711-3880 | documentary winner | scene loop | memory | deterministic ranking | REFACTOR | selection policy |
| escolher_relaxado | 3882-3917 | relaxed candidate selection | scene loop retry | memory | may lower semantic strictness | LEGACY | dangerous to transplant without contract |
| escolher_com_movimento | 3919-4083 | motion preference winner | scene loop | memory | video preference heuristics | REFACTOR | selection policy |
| score_real_5_2 | 4085-4102 | canonical candidate score | selection/fallback | memory | deterministic | REUSABLE | extract as pure policy |
| chave_candidato_5_2 | 4104-4128 | candidate identity key | failover/download loops | memory | deterministic | REUSABLE | candidate identity primitive |
| evidence_rank_5_2 | 4130-4141 | evidence ranking | sorting | memory | deterministic | REUSABLE | policy primitive |
| enriquecer_wikimedia_5_2 | 4143-4325 | Wikimedia evidence enrichment | scene loop | provider metadata | network/search semantics | REFACTOR | belongs Wikimedia adapter/evidence layer |
| ordenar_failover_5_2 | 4327-4419 | failover pool ranking | scene loop | memory | deterministic | REFACTOR | Router/selection responsibility |
| fallback_preserva_5_2 | 4421-4491 | quality-preserving fallback test | download loop | memory | deterministic | REUSABLE | policy primitive |
| fallback_degradado_ok_5_2 | 4493-4535 | controlled degraded fallback gate | scene loop | memory | relaxes quality | LEGACY | must be re-specified before reuse |
| _sap_professional_media_accept_v1 | 4537-4607 | resolution gate after download | baixar_candidato_5_2 | destination file + ffprobe | deletes rejected asset | REFACTOR | validator responsibility |
| _sap_copy_library_asset | 4609-4632 | copy/hash-check library asset | baixar_candidato_5_2 | global library path -> short media path | SHA check | REUSABLE | transport primitive |
| baixar_candidato_5_2 | 4634-4759 | choose extension, download/copy, resolution gate | scene loop; MediaProviderV2.download | short media dir + network | first candidate only at V2 boundary | REFACTOR | split download from validation |
| reencontrar_vi6_original_6_3 | 4761-4857 | map VI6 winner to original candidate | decidir_vi6_3_active | memory | identity matching | LEGACY | Stage6/VI6 dependency |
| decidir_vi6_3_active | 4859-5130 | VI6 active winner policy | scene loop | VI6 modules + candidate pool | complex semantic/risk policy | REMOVE | Stage6 decision authority |

### Critical functions

- `buscar_todos_candidatos`: the current monolithic acquisition orchestrator. It owns provider scheduling, provider health gates, parallelism, Wikimedia evidence processing, Asset Library merge, quarantine filtering and semantic triage.
- `preparar_candidatos`: legacy ranking/filtering authority still exposed through the V2 adapter.
- `baixar_candidato_5_2`: combines destination naming, download/copy, professional-resolution validation and VSE cleanup.
- `decidir_vi6_3_active`: explicit legacy VI6 decision authority in `midia.py`.
- `baixar`: technically useful transport primitive, but coupled to global resilience state.
- `_sap_copy_library_asset`: useful hash-checked local transport primitive.
- `_sap_atomic_media_checkpoint`: useful atomic Short-scoped checkpoint primitive, but belongs in a dedicated runtime contract rather than provider code.

## 7. Caller Map

### Canonical runtime

```
main.py
  -> media_engine_v2.py
      -> MediaProviderV2
          -> midia.buscar_todos_candidatos
          -> midia.preparar_candidatos
          -> midia.baixar_candidato_5_2
      -> media_engine_v2 validation
      -> media_<SHORT_ID>.json

main.py
  -> render_plan_v2.py
  -> production_recovery.py
  -> render_preflight.py
  -> render_engine_v2.py
```

### Legacy runtime embedded behind the adapter

```
MediaProviderV2.search
  -> import midia
      -> midia module initialization
      -> midia scene loop
      -> provider calls
      -> selection
      -> download
      -> scene commits
      -> final exit
  -> buscar_todos_candidatos(...)
```

This is the central architectural defect. The adapter is not wrapping a side-effect-free provider library; it is importing a script with production behavior.

## 8. Dependency Graph

```
main.py
  |
  +--> Media Engine V2
          |
          +--> MediaProviderV2
          |       |
          |       +--> midia.py
          |              +--> Pexels
          |              +--> Pixabay
          |              +--> Coverr
          |              +--> Wikimedia
          |              +--> Local
          |              +--> Asset Library
          |              +--> resilience
          |              +--> VI6 / VSE42 / Visual Unified
          |
          +--> SHA256
          +--> FFprobe
          +--> frozen manifest
  |
  +--> Render Plan V2
  |
  +--> Render Engine V2
          +--> frozen media manifest
          +--> FFmpeg / Remotion
```

### Independence answer

**No. Media Engine V2 is not currently independent of `midia.py`.**

It is independent at the file/interface naming level, but not at runtime dependency level.

## 9. Provider Map

| Provider | Current implementation | API/endpoint | Media | Auth | Timeout | Retry/circuit |
|---|---|---|---|---|---|---|
| Pexels video | `midia.py:1726` | `https://api.pexels.com/videos/search` | video | API key | `_MEDIA_API_TIMEOUT`, 3–8s | resilience family + no transport retry |
| Pexels photo | `midia.py:1870` | `https://api.pexels.com/v1/search` | image | API key | same | same |
| Pixabay video | `midia.py:1986` | `https://pixabay.com/api/videos/` | video | API key | same | same |
| Pixabay photo | `midia.py:2133` | `https://pixabay.com/api/` | image | API key | same | same |
| Coverr video | `midia.py:2242` | `https://api.coverr.co/videos` | video | Bearer API key | same | same |
| Wikimedia | `wikimedia_source.py` | Commons `/w/api.php` | image | none | default 10s, bounded 4–30s | provider resilience |
| Local Library | `shortauto_asset_library.py` | filesystem | image/video | none | local | no network |
| Legacy Local | `midia.py:2357` | `midia_local/` | image/video | none | local | random selection |

Current V2 provider is the legacy adapter:
`MediaProviderV2.name = "legacy-provider-adapter"`.

## 10. Retry Map

Current acquisition retry layers are distributed:

1. Provider API calls have request timeouts but no general HTTP retry loop.
2. `buscar_todos_candidatos` uses concurrent provider futures with a shared controller deadline.
3. Circuit recheck can wait a short bounded backoff.
4. Scene-level retry can generate simplified queries.
5. Explicit-MUST late recovery can query again.
6. Candidate-level download tries candidates in the legacy scene loop.
7. V2 itself only tries the first strict prepared candidate.

This means retry ownership is not centralized.

**Important:** the V2 adapter loses much of the legacy candidate loop's failover semantics because `acquire_scene` chooses `strict[0]` and calls `download` once.

## 11. Circuit Breaker Map

`media_external_resilience.py` stores state at:

`cache/media_resilience/state.json`

It is:
- process-memory cached in `_STATE`;
- protected by `RLock`;
- persisted to disk;
- provider-family scoped;
- not Short-scoped.

Provider thresholds/cooldowns:
- AUTH: 1 / 900s
- RATE_LIMIT: 1 / 60s
- SERVER: 2 / 20s
- NETWORK: 3 / 8s
- TIMEOUT: 3 / 8s
- MALFORMED: 2 / 30s

The current code deliberately does **not** open a provider-health circuit for EMPTY search responses. This is correct for query-specific emptiness.

### Isolation judgement

**SAFE:** provider health and rate-limit protection as global infrastructure state.

**RISK:** bad-asset quarantine is also global by provider+asset identity. This is generally legitimate, but its effects must remain limited to the asset/provider and never become a Short-specific selection state.

**UNSAFE if reused for V2 scene state:** selected asset, scene, manifest, checkpoint, download destination or Short state must never be placed in this global file.

## 12. Cache Map

| Cache/state | Scope | Persistent | Isolation |
|---|---|---|---|
| `_HTTP_SESSIONS` | process/provider | no | SAFE transport-only |
| `usados` in `midia.py` | process-wide | no | RISK; not Short-scoped |
| `media_resilience/state.json` | provider/asset | yes | SAFE for health/quarantine only |
| `asset_library.json` | global library | yes | SAFE only if treated as immutable shared resource |
| `acquisition_missing_<SID>.json` | Short | yes | SAFE scope |
| `media_quality_<SID>.json` | Short | yes | SAFE scope, legacy contract |
| `media_<SID>.json` | Short | yes | core V2 manifest |
| scene sidecars `scene_NN.json` | Short media directory | yes | SAFE by directory, but contract should bind SID |
| `.sap_state/pipeline_<SID>.json` | Short | yes | SAFE |
| render job state | Short/render ID | yes | SAFE if render_id is bound |

## 13. Global State Map

### Global and legitimate
- Provider health.
- Rate limit/circuit status.
- Bad asset quarantine.
- Shared Asset Library.
- HTTP session pools.

### Must not be global
- current `SHORT_ID`;
- current scene;
- candidate list;
- selected asset;
- scene checkpoint;
- manifest;
- download destination;
- retry counter for a specific Short;
- current render state.

The current `midia.py` global `SHORT_ID` is resolved from environment at import time. Combined with import-time execution, this is a significant coupling.

## 14. SHORT_ID Isolation Audit

### Positive findings

`main.py:116-148` has explicit fresh-ID logic. A normal run ignores a stale `SHORT_ID` when artifacts already exist. Resume explicitly uses the existing ID.

`main.py:150-180` provides a per-Short filesystem lock.

`resume_short_runtime.py:380-399` reruns with:
`main.py run --reuse-short-id`
and explicitly injects the same `SHORT_ID`.

### Risks

- `midia.py` binds `SHORT_ID` at import time, making import context part of acquisition behavior.
- `usados` is process-global inside `midia.py`.
- The global resilience state is intentionally cross-Short.
- V2 sidecars do not explicitly store `short_id`.
- V2 manifest validation checks `short_id`, but does not cryptographically bind the manifest itself.
- Asset paths from manifest/sidecars are not explicitly required to resolve inside `imagens/short_<SHORT_ID>`.

**Status: YELLOW/RED.**

## 15. Resume Flow Audit

Current resume logic is substantially improved.

```
resume_short_runtime.resume(SID)
  -> boundary(SID)
  -> if V2 media plan incomplete:
       post_scene_plan
  -> media_planning_tail(SID)
       -> media_engine_v2.py --short-id SID
       -> render_plan_v2.py --short-id SID
```

A valid frozen V2 manifest is authoritative in `media_engine_v2.run`: if it exists and validates, the engine returns it without provider acquisition.

This is a strong design decision.

### Remaining risks

1. If the frozen manifest is absent, V2 can reconstruct missing media from sidecars/providers.
2. The sidecar contract is weaker than the manifest contract.
3. Manifest immutability is logical, not cryptographic.
4. V2 acquisition can reach `midia.py`, so resume can indirectly execute legacy acquisition when no frozen manifest exists.

**Status: YELLOW.**

## 16. Media Manifest Audit

Current manifest:
`manifests/media_<SHORT_ID>.json`

Verified fields:
- schema_version = media-manifest-v2;
- version = 2;
- engine/version;
- short_id;
- immutable=true;
- creation timestamp;
- scene_id;
- scene number;
- query;
- must_have;
- avoid;
- asset;
- checksum_sha256;
- provider/source;
- provenance;
- FFprobe data;
- validated flag.

### Strengths
- atomic JSON write;
- SHA-256 asset identity;
- FFprobe revalidation;
- Short ID embedded;
- exact scene count checked;
- full-manifest reuse on resume.

### Weaknesses
- no manifest self-hash;
- no signature;
- no write-once enforcement;
- `immutable` is a claim in JSON;
- no explicit schema validation library/version contract;
- asset path containment is not enforced;
- provenance is not fully validated during manifest reuse.

**Status: YELLOW.**

## 17. Asset Validation Audit

### Current V2 validation
`ffprobe_asset` checks:
- file exists;
- size > 1000 bytes;
- FFprobe succeeds;
- JSON parses;
- video stream exists;
- width/height > 0;
- duration is not negative;
- format metadata;
- SHA-256 is used around the manifest/sidecar.

### Gaps
- duration == 0 is not rejected;
- MIME/content signature is not independently checked;
- image decode is delegated to FFprobe without an explicit image decoder gate;
- no actual pixel/content test for placeholder/slate/error imagery;
- no robust rejection rule for a valid-but-wrong media file beyond semantic candidate metadata;
- manifest reuse does not independently verify all semantic metadata against the current scene map.

### Specific malformed cases
- HTML as JPG: likely rejected if FFprobe cannot decode it, but there is no explicit content-signature rule.
- JSON as MP4: likely rejected by FFprobe.
- empty file: rejected.
- truncated file: generally rejected if FFprobe cannot parse/stream, but a dedicated decode gate is not defined for acquisition.
- slate/placeholder: filename-based renderer protection exists, but V2 acquisition itself does not provide a content-level placeholder detector.
- zero-duration video: not explicitly rejected.

**Status: YELLOW.**

## 18. Asset Library Audit

The Asset Library is a global persistent index:
`.sap_state/asset_library.json`.

It stores:
- asset_id;
- SHA-256;
- visual hash;
- file/path;
- dimensions/duration;
- source/license;
- entities;
- location;
- era;
- visual style;
- quality;
- used_count;
- short_ids;
- last_used_at.

Search requires:
- MUST list;
- file exists;
- size;
- supported extension;
- known source/license;
- stored metadata matching every MUST;
- no blocked anchor.

It rechecks SHA before V2 local use.

This is a reasonable shared resource model.

**Risk:** `path` and provenance are stored globally, while the actual asset belongs to a previous Short. Reuse is safe only if the library contract treats the asset as immutable and never copies mutable Short state into the library record.

**Status: YELLOW/SAFE-with-contract.**

## 19. Contamination Risk Analysis

### Scenario A
`SHORT_A -> provider timeout -> global provider circuit opens -> SHORT_B`

This can legitimately affect B at provider-health level. That is expected global infrastructure behavior.

It must not affect:
- B's scene list;
- B's selected asset;
- B's manifest;
- B's download path;
- B's checkpoint.

### Scenario B
`SHORT_A -> bad asset quarantine -> SHORT_B requests same asset`

This is intentionally shared asset-health state. It prevents reusing a known bad external asset. This is acceptable.

### Scenario C
`SHORT_A -> import midia -> top-level acquisition -> SHORT_B imports midia in a new process`

Because module state is process-local, the Python module cache itself does not persist across separate processes. However, the top-level code writes persistent Short-scoped/global artifacts. The real risk is therefore filesystem and resilience side effects, not Python object memory.

### Overall contamination classification

| Mechanism | Status | Reason |
|---|---|---|
| provider circuit | SAFE | legitimate global provider health |
| bad asset quarantine | SAFE | asset/provider identity scoped |
| HTTP session | SAFE | transport only |
| Asset Library | YELLOW | shared immutable resource required |
| `usados` | RISK | process-global selector memory |
| scene checkpoint | SAFE if SID path | current implementation is SID-named |
| media manifest | SAFE if validated/frozen | needs stronger immutability |
| `midia.py` import | RED | triggers production side effects |

## 20. Bugs

### BUG-001 — V2 imports a production script as a provider backend
Evidence:
- `media_provider_v2.py:L14-L25`
- `midia.py:L5080+` contains a top-level acquisition loop and final exit path.
- no import-safe main guard surrounds the production loop.

Impact:
- importing the legacy provider backend can execute production acquisition before V2 invokes the requested function;
- can write Short-scoped files;
- can query providers;
- can run legacy visual selection;
- can consume provider circuit/quarantine state;
- can duplicate work.

### BUG-002 — V2 does not implement true per-asset provider failover
Evidence:
`media_engine_v2.py:L205-L245`:
- search;
- prepare;
- choose `strict[0]`;
- one download;
- Local Library fallback.

There is no loop over the remaining strict candidates after a failed download.

### BUG-003 — V2 validation permits non-negative zero duration
Evidence:
`media_engine_v2.py:L59-L106` rejects duration < 0, not duration == 0.

For videos, zero-duration media should be explicitly rejected.

### BUG-004 — current acquisition migration tests do not exercise the real adapter import path
The V2 contract tests mock `PROVIDER.search/prepare/download` in the relevant failure tests. They therefore do not prove that `MediaProviderV2._legacy()` can import/use `midia.py` safely without executing its top-level loop.

This is a test coverage bug, not evidence that the tests themselves are broken.

## 21. Architectural Risks

### AR-001 — adapter is not a real adapter boundary
The adapter points directly into a monolithic script.

### AR-002 — provider health is global by design
Correct for provider health, but future V2 code must not add scene state there.

### AR-003 — global `usados` state
Can bias later scenes within a process and is not Short-keyed.

### AR-004 — selection and acquisition are mixed
Search, evidence, scoring, download, validation and fallback live in `midia.py`.

### AR-005 — manifest immutability is semantic
No self-hash/write-once protection.

### AR-006 — sidecar contract weaker than frozen manifest
A sidecar can be used when manifest is absent.

### AR-007 — Asset Library contains shared mutable usage metadata
Usage metadata is global and must never be treated as per-Short runtime state.

### AR-008 — legacy visual intelligence remains reachable
V2 can reach VI6/VSE-related code through `midia.py`.

## 22. Legacy Debt

High legacy debt remains in:
- `midia.py`;
- `media_stage_runtime.py`;
- VI6 module family;
- VSE42/VG4X bridge family;
- legacy selection/ranking functions;
- legacy local directory fallback;
- Stage 6 recovery contracts retained for regression.

The correct migration is **extraction first, retirement later**.

## 23. Reusable Components

Strong candidates to preserve:
- atomic JSON writing;
- SHA-256 hashing;
- FFprobe invocation pattern;
- HTTP session pool;
- provider resilience state machine;
- bad-asset quarantine;
- Asset Library SHA-verified retrieval;
- candidate identity key;
- deterministic scoring primitives;
- source/license/provenance capture;
- per-Short lock from main pipeline;
- V2 frozen manifest concept.

## 24. Components To Refactor

Refactor/extract:
- provider HTTP calls;
- provider normalization;
- candidate preparation;
- semantic MUST verification;
- download transport;
- technical asset validation;
- provenance;
- provider health;
- fallback policy;
- Wikimedia evidence adapter;
- Asset Library adapter.

These must be separate modules with narrow contracts.

## 25. Components To Retire

Retirement candidates after parity tests:
- `media_provider_v2.py` legacy adapter;
- `midia.py` acquisition path;
- `buscar_todos_candidatos` monolithic orchestration;
- `baixar_candidato_5_2` combined selection/download;
- `decidir_vi6_3_active`;
- VSE42/VG4X runtime decision bridges;
- Stage 6 runtime controller from production and, later, its obsolete implementation files.

Do not delete any of these during Etapa A.

## 26. Proposed Architecture

The audit supports a narrower target:

```
main.py
  |
  v
Media Engine V2
  |
  v
Media Acquisition V2
  |
  v
Provider Router
  |---- Pexels Adapter
  |---- Pixabay Adapter
  |---- Coverr Adapter
  |---- Wikimedia Adapter
  |---- Local Asset Library Adapter
  |
  v
Asset Validator
  |---- content signature
  |---- decode/FFprobe
  |---- dimensions
  |---- duration
  |---- placeholder/content gate
  |---- SHA-256
  |
  v
Frozen Media Manifest
  |
  v
Render Plan V2
  |
  v
Render Engine V2
```

The Router must operate per scene/asset and may try:
`Pexels -> Pixabay -> Wikimedia -> Local`
without failing the entire Short merely because the first provider failed.

After manifest freeze:
**Render, resume and recovery must not query providers for already-frozen assets.**

## 27. Migration Strategy

### Phase B1 — provider extraction
Create pure provider adapters from the currently verified provider code.

### Phase B2 — independent validator
Extract technical validation and content integrity.

### Phase B3 — Router
Implement per-asset fallback and typed failure classes.

### Phase B4 — manifest hardening
Add schema versioning, manifest SHA/self-integrity, path containment and immutable-write rules.

### Phase B5 — V2 integration
Change Media Engine V2 to depend only on Acquisition V2.

### Phase B6 — compatibility verification
Run old-vs-new candidate parity fixtures without making old code production authority.

### Phase B7 — stress qualification
Run 1 -> 2 -> 5 -> 10, mixed failures, resume and contamination tests.

### Phase B8 — legacy retirement
Only after all gates are green, remove the V2 legacy adapter and then retire `midia.py` acquisition responsibilities.

### Phase B9 — post-merge
CI green -> merge -> post-merge main validation -> promote `termux-stable` -> verify equality -> only then Termux.

## 28. Test Strategy

Required:

| Test | Expected evidence |
|---|---|
| T1 normal acquisition | SID, scene, provider, SHA, validation, manifest |
| T2 two Shorts | A/B isolated artifacts and manifests |
| T3 batch 5 | five distinct SID contracts |
| T4 batch 10 | ten distinct SID contracts |
| T5 provider failure | typed failure + fallback provider evidence |
| T6 timeout | timeout class + next provider |
| T7 provider empty | EMPTY only for query/scene; provider remains reusable |
| T8 invalid asset | validator rejection evidence |
| T9 resume | same SID + same frozen asset hashes |
| T10 contamination | A failure cannot alter B scene/manifest/path |
| T11 concurrency | separate locks and directories |
| T12 repeatability | same frozen manifest yields same render inputs |
| T13 mixed stress | 1 OK / 2 timeout / 3 OK / 4 empty / 5 OK / 6 invalid / 7 OK / 8 timeout / 9 OK / 10 OK |

No test is PASS from exit code alone.

Minimum PASS evidence:
`short_id, scene_id, asset_id, provider, sha256, validated, manifest, error_class/retry/fallback when applicable`.

## 29. Observability Strategy

Every acquisition event should carry:
- SHORT_ID;
- SCENE_ID;
- PROVIDER;
- REQUEST;
- RESPONSE;
- DOWNLOAD;
- VALIDATION;
- SHA256;
- RESULT;
- ERROR_CLASS;
- RETRY;
- FALLBACK.

Secrets must never be logged.

Failure classes:
- TRANSIENT_NETWORK
- PROVIDER_TIMEOUT
- RATE_LIMIT
- PROVIDER_UNAVAILABLE
- PROVIDER_EMPTY
- INVALID_ASSET
- DOWNLOAD_FAILED
- VALIDATION_FAILED
- CORRUPTED_ASSET
- CONFIG_ERROR
- AUTH_ERROR
- PERMANENT_FAILURE

Separate:
- business logic failure;
- system/runtime failure.

## 30. Remaining Risks

1. Runtime independence from `midia.py` is unresolved.
2. True provider-router fallback is unresolved.
3. Acquisition validator is not yet independent.
4. Manifest immutability is not cryptographically enforced.
5. Sidecar recovery is weaker than frozen-manifest recovery.
6. Placeholder/content-level validation is incomplete at acquisition.
7. Global selector state remains in legacy code.
8. Legacy Stage 6/VI6 modules remain reachable indirectly.
9. Existing migration CI does not test the real adapter-import side effect.
10. GitHub cannot certify a local Termux working tree from remote refs alone.

## 31. Go / No-Go Recommendation

**NO-GO for Etapa B implementation.**

| Area | Status | Evidence | Risk | Action |
|---|---|---|---|---|
| Git refs | GREEN | main == termux-stable at HEAD | low | preserve |
| Production path | GREEN | main.py invokes V2, not Stage6 | medium indirect risk | keep |
| Stage 6 direct path | GREEN | main.py gate | legacy remains | keep bypass |
| Stage 6 indirect reachability | RED | V2 -> adapter -> midia.py | high | remove dependency |
| midia.py audit | GREEN | full file/function inventory | high legacy complexity | extract |
| Providers | GREEN/YELLOW | Pexels/Pixabay/Coverr/Wikimedia/Library mapped | fallback coupling | adapters |
| Retry | YELLOW | multiple distributed layers | inconsistent | centralize |
| Circuit breaker | GREEN/YELLOW | provider-scoped persisted state | global side effects | preserve only health |
| Cache | YELLOW | multiple layers | mixed legacy/V2 semantics | separate |
| SHORT_ID | YELLOW | main/resume contracts strong | midia/import + path binding | harden |
| Resume | YELLOW | frozen manifest authoritative | absent-manifest fallback can reach legacy | harden |
| Manifest | YELLOW | SHA/FFprobe/frozen field | not self-hashed | harden |
| Asset validation | YELLOW | FFprobe/SHA | content/zero-duration gaps | extract |
| Asset Library | YELLOW | SHA/license/MUST search | global metadata | formalize |
| Tests | RED for Etapa B | current tests mock adapter boundary | runtime import not covered | add real-path tests |
| Migration architecture | YELLOW | target is clear | implementation not yet independent | define contracts |

### Etapa B gate

**BLOCKED until critical RED items are resolved and evidenced in GitHub CI.**

## Audit branch

`audit/media-acquisition-v2`

No production file was modified in this audit. No Termux synchronization was performed.
