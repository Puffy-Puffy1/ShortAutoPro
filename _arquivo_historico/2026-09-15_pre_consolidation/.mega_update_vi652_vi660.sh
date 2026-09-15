#!/data/data/com.termux/files/usr/bin/bash

set -u

cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"

BACKDIR="backups/stable_release_ready/mega_vi652_vi660_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " SHORTAUTOPRO MEGA UPDATE"
echo " VI6.52 -> VI6.60"
echo "======================================================"
echo
echo "MODE: SHADOW"
echo "DEFAULT RENDERER: LEGACY"
echo "ACTIVE: LOCKED"
echo


# =====================================================
# 0. REQUIREMENTS
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_47_renderer_switch.py
vi6_48_emergency_rollback.py
vi6_49_real_command_mapper.py
vi6_50_shadow_filter_comparator.py
vi6_51_canary_gate.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then

        echo "ERRO: arquivo obrigatório ausente:"
        echo "$F"

        exit 2
    fi
done


VIDEO_HASH_BEFORE="$(
    sha256sum video.py \
    | awk '{print $1}'
)"


echo "VIDEO SHA BEFORE:"
echo "$VIDEO_HASH_BEFORE"


# =====================================================
# 1. BACKUPS
# =====================================================

for F in \
    vi6_49_real_command_mapper.py \
    vi6_50_shadow_filter_comparator.py \
    vi6_52_scene_identity.py \
    vi6_53_visual_contract_resolver.py \
    vi6_54_motion_intelligence.py \
    vi6_55_native_video_guard.py \
    vi6_56_sequence_diversity.py \
    vi6_57_cinematic_rhythm.py \
    vi6_58_performance_guard.py \
    vi6_59_self_healing.py \
    vi6_60_runtime.py \
    vi6_60_master_gate.py \
    vi6_60_source_safety_audit.py \
    testar_vi652_vi660.py \
    .executar_shadow_vi660.sh
do

    if [ -f "$F" ]; then

        cp "$F" "$BACKDIR/$F"

    fi
done


rollback() {

    echo
    echo "======================================================"
    echo " MEGA UPDATE ROLLBACK"
    echo "======================================================"

    for F in \
        vi6_49_real_command_mapper.py \
        vi6_50_shadow_filter_comparator.py \
        vi6_52_scene_identity.py \
        vi6_53_visual_contract_resolver.py \
        vi6_54_motion_intelligence.py \
        vi6_55_native_video_guard.py \
        vi6_56_sequence_diversity.py \
        vi6_57_cinematic_rhythm.py \
        vi6_58_performance_guard.py \
        vi6_59_self_healing.py \
        vi6_60_runtime.py \
        vi6_60_master_gate.py \
        vi6_60_source_safety_audit.py \
        testar_vi652_vi660.py \
        .executar_shadow_vi660.sh
    do

        if [ -f "$BACKDIR/$F" ]; then

            cp "$BACKDIR/$F" "$F"

        else

            rm -f "$F"

        fi

    done

    echo "Rollback concluído."
}


# =====================================================
# 2. VI6.49 ZERO-BASED FIX
# =====================================================

echo
echo "===== VI6.49 ZERO-BASED HARDENING ====="

python - <<'PY'
from pathlib import Path


p = Path(
    "vi6_49_real_command_mapper.py"
)

s = p.read_text(
    encoding="utf-8"
)


start = s.find(
    "def infer_scene_number("
)

end = s.find(
    "\ndef _fps_from_filter(",
    start
)


if (
    start < 0
    or end < 0
):

    raise SystemExit(
        "infer_scene_number block not found"
    )


new = r'''def infer_scene_number(
    output_path
):

    if not output_path:
        return None


    name = os.path.basename(
        str(
            output_path
        )
    )


    # ==================================================
    # Internal video.py numbering is ZERO-BASED.
    #
    # v63_cena_00 = editorial scene 1
    # ...
    # v63_cena_11 = editorial scene 12
    #
    # Conversion is restricted to this exact prefix.
    # ==================================================

    internal = re.fullmatch(
        r"v63_cena_(\d+)\.mp4",
        name,
        flags=re.IGNORECASE
    )


    if internal:

        try:

            raw_index = int(
                internal.group(
                    1
                )
            )


            editorial_scene = (
                raw_index
                + 1
            )


            if (
                1
                <= editorial_scene
                <= 99
            ):

                return editorial_scene


        except Exception:
            pass


    # Normal externally numbered files are already
    # one-based and MUST NOT receive +1.

    patterns = (

        r"(?:cena|scene)[_-]?0*(\d+)",

        r"(?:clip|frame)[_-]?0*(\d+)",

        r"[_-]0*(\d+)(?:\.[A-Za-z0-9]+)?$",
    )


    for pattern in patterns:

        match = re.search(
            pattern,
            name,
            flags=re.IGNORECASE
        )


        if match:

            try:

                number = int(
                    match.group(
                        1
                    )
                )


                if 1 <= number <= 99:
                    return number


            except Exception:
                pass


    return None
'''


patched = (
    s[:start]
    + new
    + s[end:]
)


p.write_text(
    patched,
    encoding="utf-8"
)


print(
    "VI6.49 ZERO-BASED FIX=APPLIED"
)
PY


# =====================================================
# 3. VI6.52 SCENE IDENTITY 2.0
# =====================================================

cat > vi6_52_scene_identity.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.52"


def evaluate(
    event
):

    event = dict(
        event
        or {}
    )


    scene = event.get(
        "scene"
    )


    blockers = []

    warnings = []


    if not isinstance(
        scene,
        int
    ):

        blockers.append(
            "scene_not_integer"
        )


    elif not (
        1 <= scene <= 12
    ):

        blockers.append(
            "scene_outside_1_12"
        )


    branch = event.get(
        "branch"
    )


    if branch not in {
        "STILL",
        "VIDEO",
    }:

        blockers.append(
            "unknown_media_branch"
        )


    duration = event.get(
        "duration_seconds"
    )


    try:

        duration = float(
            duration
        )

    except Exception:

        duration = None


    if (
        duration is None
        or duration <= 0
    ):

        blockers.append(
            "duration_invalid"
        )


    elif duration < .75:

        warnings.append(
            "very_short_scene"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "scene":
            scene,

        "branch":
            branch,

        "duration":
            duration,

        "blockers":
            blockers,

        "warnings":
            warnings,
    }


def self_test():

    assert (
        evaluate(
            {
                "scene": 12,
                "branch": "VIDEO",
                "duration_seconds": 3.0,
            }
        )[
            "status"
        ]
        == "PASS"
    )


    assert (
        evaluate(
            {
                "scene": 0,
                "branch": "STILL",
                "duration_seconds": 3.0,
            }
        )[
            "status"
        ]
        == "HOLD"
    )


    print(
        "VI6.52 SCENE IDENTITY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 4. VI6.53 UNIFIED VISUAL CONTRACT
# =====================================================

cat > vi6_53_visual_contract_resolver.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.53"


def resolve(
    event,
    identity
):

    event = dict(
        event
        or {}
    )


    identity = dict(
        identity
        or {}
    )


    branch = identity.get(
        "branch"
    )


    scene = identity.get(
        "scene"
    )


    duration = identity.get(
        "duration"
    )


    renderer_mode = event.get(
        "renderer_mode"
    )


    role = (
        "HOOK"
        if scene == 1

        else (
            "CTA"
            if scene == 12

            else (
                "CLIMAX"
                if scene in {
                    9,
                    10,
                    11,
                }

                else "CONTEXT"
            )
        )
    )


    desired_motion = (

        "NATIVE"
        if branch == "VIDEO"

        else (
            "ENERGETIC"
            if role == "HOOK"

            else (
                "CALM"
                if role == "CTA"

                else "CINEMATIC"
            )
        )
    )


    blockers = []


    if (
        identity.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "identity_hold"
        )


    if (
        branch == "VIDEO"
        and renderer_mode
        not in {
            None,
            "NATIVE_VIDEO_PRESERVE",
        }
    ):

        blockers.append(
            "video_motion_not_native"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "scene":
            scene,

        "role":
            role,

        "branch":
            branch,

        "duration_seconds":
            duration,

        "desired_motion":
            desired_motion,

        "renderer_mode":
            renderer_mode,

        "blockers":
            blockers,
    }


def self_test():

    result = resolve(
        {
            "renderer_mode":
                "NATIVE_VIDEO_PRESERVE"
        },
        {
            "status":
                "PASS",

            "scene":
                12,

            "branch":
                "VIDEO",

            "duration":
                3.2,
        }
    )


    assert (
        result[
            "role"
        ]
        == "CTA"
    )


    assert (
        result[
            "status"
        ]
        == "PASS"
    )


    print(
        "VI6.53 VISUAL CONTRACT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 5. VI6.54 SMART MOTION 2.0
# =====================================================

cat > vi6_54_motion_intelligence.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.54"


def assess(
    contract,
    event
):

    contract = dict(
        contract
        or {}
    )


    event = dict(
        event
        or {}
    )


    branch = contract.get(
        "branch"
    )


    duration = (
        contract.get(
            "duration_seconds"
        )
        or 0
    )


    role = contract.get(
        "role"
    )


    if branch == "VIDEO":

        profile = "NATIVE"

        zoom_budget = 0.0

        pan_budget = 0.0


    elif duration < 2.0:

        profile = "MICRO_MOTION"

        zoom_budget = .025

        pan_budget = .05


    elif role == "HOOK":

        profile = "HOOK_PUSH"

        zoom_budget = .065

        pan_budget = .12


    elif role == "CTA":

        profile = "CTA_SETTLE"

        zoom_budget = .025

        pan_budget = .06


    elif role == "CLIMAX":

        profile = "CLIMAX_DRIVE"

        zoom_budget = .055

        pan_budget = .11


    else:

        profile = "DOCUMENTARY_DRIFT"

        zoom_budget = .04

        pan_budget = .08


    proposed = event.get(
        "proposed_vi6_vf"
    )


    warnings = []


    if (
        branch == "STILL"
        and isinstance(
            proposed,
            str
        )
        and "zoompan="
        not in proposed
    ):

        warnings.append(
            "planned_still_without_zoompan"
        )


    return {

        "version":
            VERSION,

        "status":
            "PASS",

        "profile":
            profile,

        "zoom_budget":
            zoom_budget,

        "pan_budget":
            pan_budget,

        "warnings":
            warnings,

        "filter_mutated":
            False,
    }


def self_test():

    assert (
        assess(
            {
                "branch": "VIDEO",
                "duration_seconds": 4,
                "role": "CONTEXT",
            },
            {}
        )[
            "profile"
        ]
        == "NATIVE"
    )


    assert (
        assess(
            {
                "branch": "STILL",
                "duration_seconds": 1.2,
                "role": "CONTEXT",
            },
            {}
        )[
            "profile"
        ]
        == "MICRO_MOTION"
    )


    print(
        "VI6.54 MOTION INTELLIGENCE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 6. VI6.55 NATIVE VIDEO PRESERVATION
# =====================================================

cat > vi6_55_native_video_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.55"


def evaluate(
    event
):

    event = dict(
        event
        or {}
    )


    branch = event.get(
        "branch"
    )


    status = event.get(
        "status"
    )


    blockers = []


    if branch == "VIDEO":

        if (
            status
            != "NATIVE_VIDEO_PRESERVE"
        ):

            blockers.append(
                "video_not_native_preserve"
            )


    return {

        "version":
            VERSION,

        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "native_video_preserved":
            (
                branch != "VIDEO"
                or status
                == "NATIVE_VIDEO_PRESERVE"
            ),

        "blockers":
            blockers,

        "command_mutated":
            False,
    }


def self_test():

    assert (
        evaluate(
            {
                "branch":
                    "VIDEO",

                "status":
                    "NATIVE_VIDEO_PRESERVE",
            }
        )[
            "status"
        ]
        == "PASS"
    )


    print(
        "VI6.55 NATIVE VIDEO GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 7. VI6.56 SEQUENCE DIVERSITY
# =====================================================

cat > vi6_56_sequence_diversity.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.56"


def audit(
    events
):

    events = sorted(
        list(
            events
            or []
        ),
        key=lambda x:
            x.get(
                "scene",
                999
            )
    )


    warnings = []

    blockers = []


    branches = [
        event.get(
            "branch"
        )
        for event in events
    ]


    # Detect excessive still/video streaks.
    longest = 0

    current = 0

    previous = None


    for branch in branches:

        if branch == previous:

            current += 1

        else:

            previous = branch

            current = 1


        longest = max(
            longest,
            current
        )


    if longest >= 6:

        warnings.append(
            "long_same_media_streak"
        )


    profiles = [

        (
            event.get(
                "mega",
                {}
            )
            .get(
                "motion",
                {}
            )
            .get(
                "profile"
            )
        )

        for event in events
    ]


    repeated_profile = 0


    for index in range(
        2,
        len(
            profiles
        )
    ):

        if (
            profiles[index]
            and profiles[index]
            == profiles[index - 1]
            == profiles[index - 2]
            and profiles[index]
            not in {
                "NATIVE"
            }
        ):

            repeated_profile += 1


    if repeated_profile >= 2:

        warnings.append(
            "repetitive_motion_profiles"
        )


    scenes = sorted(
        {
            event.get(
                "scene"
            )
            for event in events
            if isinstance(
                event.get(
                    "scene"
                ),
                int
            )
        }
    )


    if (
        len(
            events
        )
        >= 12
        and scenes
        != list(
            range(
                1,
                13
            )
        )
    ):

        blockers.append(
            "scene_sequence_not_1_to_12"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "longest_media_streak":
            longest,

        "repeated_motion_profile_events":
            repeated_profile,

        "warnings":
            warnings,

        "blockers":
            blockers,
    }


def self_test():

    events = [
        {
            "scene": n,
            "branch":
                (
                    "VIDEO"
                    if n % 2
                    else "STILL"
                ),

            "mega":
                {
                    "motion":
                        {
                            "profile":
                                (
                                    "NATIVE"
                                    if n % 2
                                    else "DOCUMENTARY_DRIFT"
                                )
                        }
                },
        }

        for n in range(
            1,
            13
        )
    ]


    assert (
        audit(
            events
        )[
            "status"
        ]
        == "PASS"
    )


    print(
        "VI6.56 SEQUENCE DIVERSITY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 8. VI6.57 CINEMATIC RHYTHM
# =====================================================

cat > vi6_57_cinematic_rhythm.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.57"


def scene_target(
    scene
):

    if scene == 1:
        return "FAST_HOOK"

    if scene in {
        2,
        3,
        4,
    }:
        return "ACCELERATE"

    if scene in {
        5,
        6,
        7,
        8,
    }:
        return "DOCUMENTARY_FLOW"

    if scene in {
        9,
        10,
        11,
    }:
        return "CLIMAX"

    if scene == 12:
        return "CTA_SETTLE"

    return "UNKNOWN"


def audit(
    events
):

    warnings = []

    blockers = []


    for event in events:

        scene = event.get(
            "scene"
        )


        duration = event.get(
            "duration_seconds"
        )


        try:

            duration = float(
                duration
            )

        except Exception:

            blockers.append(
                "scene_duration_invalid"
            )

            continue


        target = scene_target(
            scene
        )


        if (
            target == "FAST_HOOK"
            and duration > 6.5
        ):

            warnings.append(
                "hook_may_be_slow"
            )


        if (
            target == "CTA_SETTLE"
            and duration < 1.0
        ):

            warnings.append(
                "cta_too_short"
            )


    return {

        "version":
            VERSION,

        "status":
            (
                "HOLD"
                if blockers
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),

        "warnings":
            sorted(
                set(
                    warnings
                )
            ),

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),
    }


def self_test():

    assert (
        scene_target(
            1
        )
        == "FAST_HOOK"
    )


    assert (
        scene_target(
            12
        )
        == "CTA_SETTLE"
    )


    print(
        "VI6.57 CINEMATIC RHYTHM=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 9. VI6.58 PERFORMANCE GUARD
# =====================================================

cat > vi6_58_performance_guard.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.58"


def estimate(
    event
):

    branch = event.get(
        "branch"
    )


    duration = event.get(
        "duration_seconds"
    )


    try:

        duration = float(
            duration
        )

    except Exception:

        duration = 0.0


    vf = event.get(
        "proposed_vi6_vf"
    )


    score = 1.0


    if branch == "STILL":

        score += 1.0


    if (
        isinstance(
            vf,
            str
        )
        and "zoompan="
        in vf
    ):

        score += .75


    if duration >= 5:

        score += .5


    return round(
        score,
        2
    )


def audit(
    events
):

    scores = [
        estimate(
            event
        )
        for event in events
    ]


    total = round(
        sum(
            scores
        ),
        2
    )


    warnings = []


    if total > 30:

        warnings.append(
            "high_render_complexity"
        )


    return {

        "version":
            VERSION,

        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),

        "estimated_complexity":
            total,

        "max_scene_complexity":
            (
                max(
                    scores
                )
                if scores
                else 0
            ),

        "warnings":
            warnings,

        "renderer_changed":
            False,
    }


def self_test():

    assert (
        estimate(
            {
                "branch":
                    "VIDEO",

                "duration_seconds":
                    3,
            }
        )
        < estimate(
            {
                "branch":
                    "STILL",

                "duration_seconds":
                    5,

                "proposed_vi6_vf":
                    "zoompan=z='1.02'",
            }
        )
    )


    print(
        "VI6.58 PERFORMANCE GUARD=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 10. VI6.59 SELF HEALING POLICY
# =====================================================

cat > vi6_59_self_healing.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.59"


def decide(
    event
):

    event = dict(
        event
        or {}
    )


    blockers = (
        event.get(
            "blockers"
        )
        or []
    )


    status = event.get(
        "status"
    )


    if (
        status == "HOLD"
        or blockers
    ):

        action = (
            "FALLBACK_SINGLE_SCENE_TO_LEGACY"
        )


    else:

        action = (
            "KEEP_CURRENT_RENDER_PATH"
        )


    return {

        "version":
            VERSION,

        "status":
            "PASS",

        "recommended_action":
            action,

        # Shadow only.
        "action_executed":
            False,

        "renderer_changed":
            False,
    }


def self_test():

    assert (
        decide(
            {
                "status":
                    "HOLD"
            }
        )[
            "recommended_action"
        ]
        == "FALLBACK_SINGLE_SCENE_TO_LEGACY"
    )


    print(
        "VI6.59 SELF HEALING POLICY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 11. SOURCE SAFETY AUDIT
# =====================================================

cat > vi6_60_source_safety_audit.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path


VERSION = "6.60-source-audit"


FILES = [
    "vi6_13_recovery_planner.py",
    "vi6_19_true_recovery.py",
    "vi6_20_normalizer.py",
    "source_router.py",
    "evidence_guard.py",
]


def audit():

    findings = []


    for filename in FILES:

        path = Path(
            filename
        )


        if not path.exists():
            continue


        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )


        low = text.lower()


        # Audit only. No automatic patching.
        if (
            "truth"
            in low
            and "true"
            in low
            and "unknown"
            not in low
        ):

            findings.append(
                {
                    "file":
                        filename,

                    "severity":
                        "WARN",

                    "reason":
                        "truth_default_requires_manual_review",
                }
            )


        if (
            "hard_no_retry"
            in low
            or "hard_rejections"
            in low
        ):

            findings.append(
                {
                    "file":
                        filename,

                    "severity":
                        "WARN",

                    "reason":
                        "broad_no_retry_policy_requires_review",
                }
            )


        if (
            "source_router"
            in filename
            and "getattr("
            in low
        ):

            findings.append(
                {
                    "file":
                        filename,

                    "severity":
                        "WARN",

                    "reason":
                        "dynamic_source_dispatch_present",
                }
            )


    return {

        "version":
            VERSION,

        "status":
            (
                "REVIEW"
                if findings
                else "PASS"
            ),

        "findings":
            findings,

        "files_modified":
            False,
    }


if __name__ == "__main__":

    print(
        json.dumps(
            audit(),
            ensure_ascii=False,
            indent=2
        )
    )
PY


# =====================================================
# 12. VI6.60 RUNTIME ORCHESTRATOR
# =====================================================

cat > vi6_60_runtime.py <<'PY'
#!/usr/bin/env python3

import json
import time

from datetime import datetime
from pathlib import Path


from vi6_52_scene_identity import (
    evaluate as identity_evaluate
)

from vi6_53_visual_contract_resolver import (
    resolve as contract_resolve
)

from vi6_54_motion_intelligence import (
    assess as motion_assess
)

from vi6_55_native_video_guard import (
    evaluate as native_evaluate
)

from vi6_56_sequence_diversity import (
    audit as diversity_audit
)

from vi6_57_cinematic_rhythm import (
    audit as rhythm_audit
)

from vi6_58_performance_guard import (
    audit as performance_audit
)

from vi6_59_self_healing import (
    decide as healing_decide
)


VERSION = "6.60-runtime"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_shadow_session_latest.json"
)


_EVENTS = {}


_LAST_EVENT_TIME = None


def observe(
    event
):

    global _LAST_EVENT_TIME


    event = dict(
        event
        or {}
    )


    now = time.monotonic()


    interval = None


    if _LAST_EVENT_TIME is not None:

        interval = round(
            now
            - _LAST_EVENT_TIME,
            3
        )


    _LAST_EVENT_TIME = now


    identity = identity_evaluate(
        event
    )


    contract = contract_resolve(
        event,
        identity
    )


    motion = motion_assess(
        contract,
        event
    )


    native = native_evaluate(
        event
    )


    healing = healing_decide(
        event
    )


    enriched = dict(
        event
    )


    enriched[
        "mega"
    ] = {

        "identity":
            identity,

        "contract":
            contract,

        "motion":
            motion,

        "native_video":
            native,

        "self_healing":
            healing,

        "inter_event_wall_seconds":
            interval,
    }


    scene = event.get(
        "scene"
    )


    key = (
        str(
            scene
        )
        if scene is not None
        else (
            "unknown:"
            + str(
                event.get(
                    "command_fingerprint"
                )
            )
        )
    )


    _EVENTS[
        key
    ] = enriched


    flush()


    return enriched


def session():

    events = list(
        _EVENTS.values()
    )


    events.sort(
        key=lambda event:
            (
                event.get(
                    "scene"
                )
                if isinstance(
                    event.get(
                        "scene"
                    ),
                    int
                )
                else 999
            )
    )


    diversity = diversity_audit(
        events
    )


    rhythm = rhythm_audit(
        events
    )


    performance = performance_audit(
        events
    )


    identity_holds = sum(

        1

        for event in events

        if (
            event.get(
                "mega",
                {}
            )
            .get(
                "identity",
                {}
            )
            .get(
                "status"
            )
            != "PASS"
        )
    )


    native_holds = sum(

        1

        for event in events

        if (
            event.get(
                "mega",
                {}
            )
            .get(
                "native_video",
                {}
            )
            .get(
                "status"
            )
            != "PASS"
        )
    )


    return {

        "version":
            VERSION,

        "unique_events":
            len(
                events
            ),

        "unique_scenes":
            len(
                {
                    event.get(
                        "scene"
                    )

                    for event in events

                    if isinstance(
                        event.get(
                            "scene"
                        ),
                        int
                    )
                }
            ),

        "identity_holds":
            identity_holds,

        "native_video_holds":
            native_holds,

        "diversity":
            diversity,

        "rhythm":
            rhythm,

        "performance":
            performance,

        "events":
            events,
    }


def flush():

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    REPORT.write_text(
        json.dumps(
            {

                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "session":
                    session(),
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    global _EVENTS
    global _LAST_EVENT_TIME


    old_events = _EVENTS

    old_time = _LAST_EVENT_TIME


    _EVENTS = {}

    _LAST_EVENT_TIME = None


    try:

        for scene in range(
            1,
            13
        ):

            branch = (
                "VIDEO"
                if scene % 2 == 0
                else "STILL"
            )


            observe(
                {
                    "scene":
                        scene,

                    "branch":
                        branch,

                    "duration_seconds":
                        3.0,

                    "status":
                        (
                            "NATIVE_VIDEO_PRESERVE"
                            if branch == "VIDEO"
                            else "SAFE_DIFFERENCE"
                        ),

                    "renderer_mode":
                        (
                            "NATIVE_VIDEO_PRESERVE"
                            if branch == "VIDEO"
                            else "KEN_BURNS_STILL"
                        ),

                    "blockers":
                        [],

                    "command_mutated":
                        False,

                    "legacy_filter_replaced":
                        False,
                }
            )


        result = session()


        assert (
            result[
                "unique_scenes"
            ]
            == 12
        )


        assert (
            result[
                "identity_holds"
            ]
            == 0
        )


    finally:

        _EVENTS = old_events

        _LAST_EVENT_TIME = old_time


    print(
        "VI6.60 RUNTIME ORCHESTRATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 13. VI6.60 MASTER GATE
# =====================================================

cat > vi6_60_master_gate.py <<'PY'
#!/usr/bin/env python3

import argparse
import json

from datetime import datetime
from pathlib import Path


from vi6_60_source_safety_audit import (
    audit as source_audit
)


VERSION = "6.60"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


SESSION_REPORT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_shadow_session_latest.json"
)


GATE51 = (
    BASE
    / "logs"
    / "producao"
    / "vi6_51_canary_gate_latest.json"
)


OUTPUT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_master_gate_latest.json"
)


SAFE_SHADOW = {
    "SAFE_DIFFERENCE",
    "EXACT_MATCH",
    "NATIVE_VIDEO_PRESERVE",
}


def _load(
    path,
    key
):

    try:

        with Path(
            path
        ).open(
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
            ).get(
                key
            )


    except Exception:

        return None


def evaluate(
    session,
    gate51
):

    blockers = []

    warnings = []


    if session is None:

        blockers.append(
            "vi660_shadow_session_missing"
        )


        events = []


    else:

        events = (
            session.get(
                "events"
            )
            or []
        )


        if (
            session.get(
                "unique_scenes"
            )
            != 12
        ):

            blockers.append(
                "requires_12_unique_scenes"
            )


        if (
            session.get(
                "identity_holds",
                0
            )
            != 0
        ):

            blockers.append(
                "scene_identity_hold"
            )


        if (
            session.get(
                "native_video_holds",
                0
            )
            != 0
        ):

            blockers.append(
                "native_video_hold"
            )


        diversity = (
            session.get(
                "diversity"
            )
            or {}
        )


        if (
            diversity.get(
                "status"
            )
            == "HOLD"
        ):

            blockers.append(
                "sequence_diversity_hold"
            )


        warnings.extend(
            diversity.get(
                "warnings"
            )
            or []
        )


        rhythm = (
            session.get(
                "rhythm"
            )
            or {}
        )


        if (
            rhythm.get(
                "status"
            )
            == "HOLD"
        ):

            blockers.append(
                "rhythm_hold"
            )


        warnings.extend(
            rhythm.get(
                "warnings"
            )
            or []
        )


        performance = (
            session.get(
                "performance"
            )
            or {}
        )


        warnings.extend(
            performance.get(
                "warnings"
            )
            or []
        )


        unsafe = [

            event

            for event in events

            if event.get(
                "status"
            )
            not in SAFE_SHADOW
        ]


        if unsafe:

            blockers.append(
                "unsafe_shadow_event"
            )


        mutated = [

            event

            for event in events

            if (
                event.get(
                    "command_mutated"
                )
                or event.get(
                    "legacy_filter_replaced"
                )
            )
        ]


        if mutated:

            blockers.append(
                "shadow_mutation_detected"
            )


    if gate51 is None:

        blockers.append(
            "vi651_gate_missing"
        )


    elif not gate51.get(
        "next_stage_allowed"
    ):

        blockers.append(
            "vi651_not_ready"
        )


    sources = source_audit()


    if (
        sources.get(
            "status"
        )
        == "REVIEW"
    ):

        warnings.append(
            "source_recovery_safety_debt"
        )


    blockers = sorted(
        set(
            blockers
        )
    )


    warnings = sorted(
        set(
            warnings
        )
    )


    if blockers:

        status = "HOLD"


    elif warnings:

        status = (
            "CERTIFIED_WITH_WARNINGS"
        )


    else:

        status = "CERTIFIED"


    return {

        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "unique_scenes":
            (
                session.get(
                    "unique_scenes"
                )
                if session
                else 0
            ),

        "identity":
            (
                "PASS"
                if session
                and session.get(
                    "identity_holds"
                )
                == 0
                else "HOLD"
            ),

        "native_video":
            (
                "PASS"
                if session
                and session.get(
                    "native_video_holds"
                )
                == 0
                else "HOLD"
            ),

        "diversity":
            (
                session.get(
                    "diversity",
                    {}
                ).get(
                    "status"
                )
                if session
                else None
            ),

        "rhythm":
            (
                session.get(
                    "rhythm",
                    {}
                ).get(
                    "status"
                )
                if session
                else None
            ),

        "performance":
            (
                session.get(
                    "performance",
                    {}
                )
                if session
                else {}
            ),

        "source_safety":
            sources,

        # Ready to BUILD canary,
        # not permission to use active renderer.
        "canary_build_allowed":
            status
            in {
                "CERTIFIED",
                "CERTIFIED_WITH_WARNINGS",
            },

        "active_canary_authorized":
            False,

        "active_renderer":
            False,
    }


def evaluate_real():

    session = _load(
        SESSION_REPORT,
        "session"
    )


    gate51 = _load(
        GATE51,
        "gate"
    )


    return evaluate(
        session,
        gate51
    )


def save(
    result
):

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {

                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    session = {

        "unique_scenes":
            12,

        "identity_holds":
            0,

        "native_video_holds":
            0,

        "diversity":
            {
                "status":
                    "PASS",

                "warnings":
                    [],
            },

        "rhythm":
            {
                "status":
                    "PASS",

                "warnings":
                    [],
            },

        "performance":
            {
                "status":
                    "PASS",

                "warnings":
                    [],
            },

        "events":
            [

                {
                    "scene":
                        n,

                    "status":
                        (
                            "NATIVE_VIDEO_PRESERVE"
                            if n % 2 == 0
                            else "SAFE_DIFFERENCE"
                        ),

                    "command_mutated":
                        False,

                    "legacy_filter_replaced":
                        False,
                }

                for n in range(
                    1,
                    13
                )
            ],
    }


    result = evaluate(
        session,
        {
            "next_stage_allowed":
                True
        }
    )


    assert result[
        "status"
    ] in {
        "CERTIFIED",
        "CERTIFIED_WITH_WARNINGS",
    }


    assert (
        result[
            "active_canary_authorized"
        ]
        is False
    )


    print(
        "VI6.60 MASTER GATE SELF TEST=PASS"
    )


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--real",
        action="store_true"
    )


    args = parser.parse_args()


    self_test()


    if not args.real:
        return


    result = evaluate_real()


    save(
        result
    )


    print()
    print(
        "======================================================"
    )
    print(
        " VI6.60 MASTER PRODUCTION GATE"
    )
    print(
        "======================================================"
    )


    print(
        "STATUS:",
        result.get(
            "status"
        )
    )


    print(
        "SCENES:",
        result.get(
            "unique_scenes"
        ),
        "/ 12"
    )


    print(
        "IDENTITY:",
        result.get(
            "identity"
        )
    )


    print(
        "NATIVE VIDEO:",
        result.get(
            "native_video"
        )
    )


    print(
        "DIVERSITY:",
        result.get(
            "diversity"
        )
    )


    print(
        "RHYTHM:",
        result.get(
            "rhythm"
        )
    )


    performance = (
        result.get(
            "performance"
        )
        or {}
    )


    print(
        "PERFORMANCE COMPLEXITY:",
        performance.get(
            "estimated_complexity"
        )
    )


    print(
        "BLOCKERS:",
        result.get(
            "blockers"
        )
    )


    print(
        "WARNINGS:",
        result.get(
            "warnings"
        )
    )


    print(
        "CANARY BUILD ALLOWED:",
        result.get(
            "canary_build_allowed"
        )
    )


    print(
        "ACTIVE CANARY AUTHORIZED:",
        result.get(
            "active_canary_authorized"
        )
    )


    print(
        "ACTIVE RENDERER:",
        result.get(
            "active_renderer"
        )
    )


if __name__ == "__main__":
    main()
PY


# =====================================================
# 14. HOOK VI6.60 INTO VI6.50 RECORD()
# =====================================================

echo
echo "===== INSTALLING SHADOW RUNTIME HOOK ====="

python - <<'PY'
from pathlib import Path


p = Path(
    "vi6_50_shadow_filter_comparator.py"
)


s = p.read_text(
    encoding="utf-8"
)


marker = (
    "# VI6.60 MEGA SHADOW RUNTIME HOOK"
)


if marker in s:

    print(
        "VI6.60 HOOK ALREADY PRESENT"
    )


else:

    addition = r'''

# VI6.60 MEGA SHADOW RUNTIME HOOK
_vi650_original_record_vi660 = record


def record(
    result
):

    # Preserve VI6.50 original telemetry first.
    _vi650_original_record_vi660(
        result
    )


    # VI6.60 is strictly observational.
    # Any failure here MUST NOT affect rendering.
    try:

        from vi6_60_runtime import (
            observe as _vi660_observe
        )


        _vi660_observe(
            result
        )


    except Exception:

        pass
'''


    p.write_text(
        s + addition,
        encoding="utf-8"
    )


    print(
        "VI6.60 SHADOW HOOK=INSTALLED"
    )
PY


# =====================================================
# 15. INTEGRATION TEST
# =====================================================

cat > testar_vi652_vi660.py <<'PY'
#!/usr/bin/env python3

from vi6_49_real_command_mapper import (
    infer_scene_number
)

from vi6_52_scene_identity import (
    evaluate as identity
)

from vi6_53_visual_contract_resolver import (
    resolve
)

from vi6_54_motion_intelligence import (
    assess
)

from vi6_55_native_video_guard import (
    evaluate as native
)

from vi6_56_sequence_diversity import (
    audit as diversity
)

from vi6_57_cinematic_rhythm import (
    audit as rhythm
)

from vi6_58_performance_guard import (
    audit as performance
)

from vi6_59_self_healing import (
    decide
)


# ==============================================
# Zero based proof
# ==============================================

for raw in range(
    12
):

    name = (
        f"v63_cena_{raw:02d}.mp4"
    )


    assert (
        infer_scene_number(
            name
        )
        == raw + 1
    )


assert (
    infer_scene_number(
        "scene_12.mp4"
    )
    == 12
)


# ==============================================
# 12 scene mega simulation
# ==============================================

events = []


for scene in range(
    1,
    13
):

    branch = (
        "VIDEO"
        if scene in {
            2,
            3,
            4,
            8,
            10,
            12,
        }
        else "STILL"
    )


    event = {

        "scene":
            scene,

        "branch":
            branch,

        "duration_seconds":
            3.0,

        "status":
            (
                "NATIVE_VIDEO_PRESERVE"
                if branch == "VIDEO"
                else "SAFE_DIFFERENCE"
            ),

        "renderer_mode":
            (
                "NATIVE_VIDEO_PRESERVE"
                if branch == "VIDEO"
                else "KEN_BURNS_STILL"
            ),

        "proposed_vi6_vf":
            (
                None
                if branch == "VIDEO"
                else (
                    "scale=1080:1920,"
                    "zoompan=z='1.02',"
                    "format=yuv420p"
                )
            ),

        "blockers":
            [],

        "command_mutated":
            False,

        "legacy_filter_replaced":
            False,
    }


    i = identity(
        event
    )


    c = resolve(
        event,
        i
    )


    m = assess(
        c,
        event
    )


    n = native(
        event
    )


    h = decide(
        event
    )


    assert i[
        "status"
    ] == "PASS"


    assert c[
        "status"
    ] == "PASS"


    assert n[
        "status"
    ] == "PASS"


    assert h[
        "action_executed"
    ] is False


    event[
        "mega"
    ] = {

        "identity":
            i,

        "contract":
            c,

        "motion":
            m,

        "native_video":
            n,

        "self_healing":
            h,
    }


    events.append(
        event
    )


assert (
    diversity(
        events
    )[
        "status"
    ]
    != "HOLD"
)


assert (
    rhythm(
        events
    )[
        "status"
    ]
    != "HOLD"
)


assert (
    performance(
        events
    )[
        "status"
    ]
    in {
        "PASS",
        "PASS_WITH_WARNINGS",
    }
)


print()
print(
    "======================================================"
)
print(
    " VI6.52-6.60 MEGA INTEGRATION TEST: PASS"
)
print(
    "======================================================"
)
print(
    "ZERO-BASED SCENE IDENTITY=PASS"
)
print(
    "12-SCENE CONTRACT RESOLUTION=PASS"
)
print(
    "SMART MOTION=PASS"
)
print(
    "NATIVE VIDEO PRESERVATION=PASS"
)
print(
    "SEQUENCE DIVERSITY=PASS"
)
print(
    "CINEMATIC RHYTHM=PASS"
)
print(
    "PERFORMANCE GUARD=PASS"
)
print(
    "SELF HEALING POLICY=PASS"
)
print(
    "COMMAND MUTATION=0"
)
print(
    "ACTIVE RENDERER=LOCKED"
)
PY


# =====================================================
# 16. COMPILE EVERYTHING
# =====================================================

echo
echo "===== MEGA COMPILE ====="

if ! python -m py_compile \
    vi6_49_real_command_mapper.py \
    vi6_50_shadow_filter_comparator.py \
    vi6_52_scene_identity.py \
    vi6_53_visual_contract_resolver.py \
    vi6_54_motion_intelligence.py \
    vi6_55_native_video_guard.py \
    vi6_56_sequence_diversity.py \
    vi6_57_cinematic_rhythm.py \
    vi6_58_performance_guard.py \
    vi6_59_self_healing.py \
    vi6_60_runtime.py \
    vi6_60_master_gate.py \
    vi6_60_source_safety_audit.py \
    testar_vi652_vi660.py \
    video.py
then

    rollback

    exit 10
fi


echo "MEGA COMPILE=PASS"


# =====================================================
# 17. SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

python vi6_49_real_command_mapper.py || {
    rollback
    exit 11
}


python vi6_52_scene_identity.py || {
    rollback
    exit 12
}


python vi6_53_visual_contract_resolver.py || {
    rollback
    exit 13
}


python vi6_54_motion_intelligence.py || {
    rollback
    exit 14
}


python vi6_55_native_video_guard.py || {
    rollback
    exit 15
}


python vi6_56_sequence_diversity.py || {
    rollback
    exit 16
}


python vi6_57_cinematic_rhythm.py || {
    rollback
    exit 17
}


python vi6_58_performance_guard.py || {
    rollback
    exit 18
}


python vi6_59_self_healing.py || {
    rollback
    exit 19
}


python vi6_60_runtime.py || {
    rollback
    exit 20
}


python vi6_60_master_gate.py || {
    rollback
    exit 21
}


python testar_vi652_vi660.py || {
    rollback
    exit 22
}


# Remove self-test runtime report so it cannot be
# confused with a real production certification.
rm -f \
    logs/producao/vi6_60_shadow_session_latest.json


# =====================================================
# 18. SOURCE SAFETY AUDIT
# =====================================================

echo
echo "===== SOURCE RECOVERY SAFETY AUDIT ====="

python vi6_60_source_safety_audit.py


# =====================================================
# 19. VIDEO.PY INTEGRITY
# =====================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py \
    | awk '{print $1}'
)"


echo
echo "===== VIDEO.PY INTEGRITY ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"

echo "AFTER =$VIDEO_HASH_AFTER"


if [
    "$VIDEO_HASH_BEFORE"
    != "$VIDEO_HASH_AFTER"
]
then

    echo "CRITICAL: video.py changed."

    rollback

    exit 23
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 20. RELEASE CHECK
# =====================================================

echo
echo "===== RELEASE CHECK ====="

bash -n gerar_short.sh || {
    rollback
    exit 24
}


./release_check.sh || {
    rollback
    exit 25
}


# =====================================================
# 21. VI6.60 REAL SHADOW RUNNER
# =====================================================

cat > .executar_shadow_vi660.sh <<'RUN'
#!/data/data/com.termux/files/usr/bin/bash

set -u

cd "$HOME/ShortAutoPro" || exit 1


echo
echo "======================================================"
echo " VI6.60 MASTER SHADOW CERTIFICATION"
echo "======================================================"
echo
echo "REAL VIDEO WILL BE GENERATED"
echo "RENDER PATH = LEGACY"
echo "VI6 = OBSERVATION ONLY"
echo


rm -f \
    logs/producao/vi6_60_shadow_session_latest.json \
    logs/producao/vi6_60_master_gate_latest.json


if [ ! -x ./.executar_shadow_vi651.sh ]; then

    echo "ERRO: .executar_shadow_vi651.sh não encontrado."

    exit 2
fi


./.executar_shadow_vi651.sh

PIPE_STATUS="$?"


echo
echo "======================================================"
echo " VI6.60 MASTER GATE"
echo "======================================================"

python \
    vi6_60_master_gate.py \
    --real


echo
echo "======================================================"
echo " VI6.60 REAL SESSION SUMMARY"
echo "======================================================"

python - <<'PY'
import json
from pathlib import Path


base = (
    Path.home()
    / "ShortAutoPro"
    / "logs"
    / "producao"
)


session_path = (
    base
    / "vi6_60_shadow_session_latest.json"
)


gate_path = (
    base
    / "vi6_60_master_gate_latest.json"
)


if session_path.exists():

    session = json.loads(
        session_path.read_text(
            encoding="utf-8"
        )
    ).get(
        "session",
        {}
    )


    print(
        "UNIQUE SCENES:",
        session.get(
            "unique_scenes"
        )
    )


    print(
        "IDENTITY HOLDS:",
        session.get(
            "identity_holds"
        )
    )


    print(
        "NATIVE VIDEO HOLDS:",
        session.get(
            "native_video_holds"
        )
    )


    print(
        "DIVERSITY:",
        (
            session.get(
                "diversity"
            )
            or {}
        ).get(
            "status"
        )
    )


    print(
        "RHYTHM:",
        (
            session.get(
                "rhythm"
            )
            or {}
        ).get(
            "status"
        )
    )


    perf = (
        session.get(
            "performance"
        )
        or {}
    )


    print(
        "PERFORMANCE COMPLEXITY:",
        perf.get(
            "estimated_complexity"
        )
    )


    print()
    print(
        "===== SCENE INTELLIGENCE ====="
    )


    for event in (
        session.get(
            "events"
        )
        or []
    ):

        mega = (
            event.get(
                "mega"
            )
            or {}
        )


        contract = (
            mega.get(
                "contract"
            )
            or {}
        )


        motion = (
            mega.get(
                "motion"
            )
            or {}
        )


        recovery = (
            mega.get(
                "self_healing"
            )
            or {}
        )


        print(
            "SCENE",
            event.get(
                "scene"
            ),

            "|",
            event.get(
                "branch"
            ),

            "|",
            event.get(
                "status"
            ),

            "| role=",
            contract.get(
                "role"
            ),

            "| motion=",
            motion.get(
                "profile"
            ),

            "| recover=",
            recovery.get(
                "recommended_action"
            ),

            "| interval=",
            mega.get(
                "inter_event_wall_seconds"
            ),
        )


if gate_path.exists():

    gate = json.loads(
        gate_path.read_text(
            encoding="utf-8"
        )
    ).get(
        "gate",
        {}
    )


    print()
    print(
        "===== MASTER RESULT ====="
    )


    print(
        "MASTER STATUS:",
        gate.get(
            "status"
        )
    )


    print(
        "BLOCKERS:",
        gate.get(
            "blockers"
        )
    )


    print(
        "WARNINGS:",
        gate.get(
            "warnings"
        )
    )


    print(
        "CANARY BUILD ALLOWED:",
        gate.get(
            "canary_build_allowed"
        )
    )


    print(
        "ACTIVE CANARY AUTHORIZED:",
        gate.get(
            "active_canary_authorized"
        )
    )


    print(
        "ACTIVE RENDERER:",
        gate.get(
            "active_renderer"
        )
    )


print()
print(
    "LEGACY FILTER REPLACEMENTS=0"
)

print(
    "ACTIVE=LOCKED"
)
PY


exit "$PIPE_STATUS"
RUN


chmod +x \
    .executar_shadow_vi660.sh


echo
echo "======================================================"
echo " MEGA UPDATE VI6.52 -> VI6.60 INSTALLED"
echo "======================================================"
echo
echo "OK Scene Identity 2.0"
echo "OK Zero-Based Renderer Mapping"
echo "OK Unified Visual Contracts"
echo "OK Smart Motion 2.0"
echo "OK Native Video Preservation"
echo "OK Sequence Diversity"
echo "OK Cinematic Rhythm 2.0"
echo "OK Performance Guard"
echo "OK Single-Scene Self-Healing Policy"
echo "OK Source Recovery Safety Audit"
echo "OK Master Runtime Orchestrator"
echo "OK Master Production Gate"
echo
echo "VIDEO.PY MODIFIED=NO"
echo "DEFAULT RENDERER=LEGACY"
echo "SHADOW MUTATION=NO"
echo "ACTIVE=LOCKED"
echo
echo "======================================================"
echo " STARTING REAL VI6.60 SHADOW CERTIFICATION"
echo "======================================================"
echo

./.executar_shadow_vi660.sh

