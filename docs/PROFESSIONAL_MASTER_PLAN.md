# ShortAutoPro Professional Master Plan

## Goal
Move ShortAutoPro from technically correct automated assembly to intentional, professional-looking editing while preserving factual safety, Termux compatibility, the V6 output contract, and the existing fail-closed production gates.

## Professional editing principles
1. Correct media is necessary but not sufficient: the edit must have framing variety, controlled motion, pacing contrast, and visual continuity.
2. Professional documentary editing uses more restrained cuts and movement than template-driven Ken Burns automation.
3. Hooks may receive stronger emphasis, but only briefly; the middle needs rhythm variation and the ending needs visual stability.
4. Color treatment should be subtle, profile-specific, and consistent across the full piece.
5. Audio should obey the configured loudness/true-peak policy rather than a renderer-local hard-coded target.
6. Failures must remain recoverable and no new professional layer may bypass factual, media, technical, publish-integrity, or final-quality gates.

## Architecture
### Professional Edit Director
Creates `roteiros/pro_edit_plan_<SHORT_ID>.json` from the scene map + motion/rhythm plans. It assigns:
- scene pacing multipliers;
- restrained transition durations;
- motion curves;
- hook/reveal emphasis;
- profile-specific finish settings;
- deterministic quality/variety checks;
- an editing score and repair notes.

### Professional Scene Assembler
`video_professional.py` renders the scene edit using:
- semantic caption-aware duration allocation;
- variable pacing by narrative role;
- smoothstep easing for still-image motion;
- restrained near-cut/soft-fade transitions instead of a fixed crossfade everywhere;
- the same 1080x1920 / 30 fps contract.

### Professional Final Renderer
`v6_professional.py` preserves the V6 final contract but adds:
- profile-aware finish;
- restrained hook punch;
- deterministic music selection;
- curated-SFX-first behavior;
- configurable final loudness and true peak;
- more restrained retention-caption treatment.

### Professional Quality Gate
`professional_quality_gate.py` scores the professional edit plan and final artifact. Initial rollout is observational unless `SAP_PROFESSIONAL_ENFORCE=1` is set. Existing blocking quality gates remain authoritative during calibration.

## Rollout
- `SAP_PRO_EDIT=1` enables the professional edit path.
- `SAP_PROFESSIONAL_ENFORCE=0` initially keeps the new professional score observational.
- Existing `video.py` and `v6.py` remain available as rollback paths.
- Safe resume uses the professional assembler/renderer when Professional Edit is enabled.

## Target quality
Professional plan target: >= 88/100.

Signals:
- no three consecutive repeated neutral shot framings;
- no three consecutive identical directional pans;
- limited high-intensity motion;
- hook emphasis only where narratively justified;
- pacing variety across the scene arc;
- restrained transitions (mostly near-cuts and short fades);
- profile-specific but subtle visual finish;
- final technical output remains H.264 + AAC, 1080x1920, ~30 fps.

## Profiles
### true_crime
Documentary suspense, cooler/desaturated finish, restrained motion, tighter cuts in hook/escalation, calm evidence/reveal holds.

### cinepulsar
More energetic pacing, slightly richer saturation, stronger but controlled hook emphasis.

### psicotoon
Retro-leaning contrast/saturation balance with stable framing and deliberately paced visual beats.

### default
Neutral premium documentary treatment.

## Success criteria
1. CI syntax/regression/Bash/health all pass.
2. `termux-stable` is promoted only from the exact tested commit.
3. A real Termux Short reaches `JOB_STATUS=PASS` with the professional path active.
4. No regression in factual, media, publish-integrity, or final-quality gates.
5. After several real samples, calibrate and optionally enable `SAP_PROFESSIONAL_ENFORCE=1`.
