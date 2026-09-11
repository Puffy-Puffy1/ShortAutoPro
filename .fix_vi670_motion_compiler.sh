#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACK="backups/stable_release_ready/vi670_motion_compiler_${STAMP}"

mkdir -p "$BACK"

echo
echo "======================================================"
echo " VI6.61.1 MOTION FILTER COMPILER"
echo " VI6.70 CANARY PREVIEW REPAIR"
echo "======================================================"

FILES="
vi6_61_motion_filter_compiler.py
vi6_65_canary_candidate_selector.py
vi6_66_canary_filter_preview.py
"

for F in $FILES
do
    if [ -f "$F" ]; then
        cp "$F" "$BACK/$F"
    fi
done

VIDEO_HASH_BEFORE="$(
    sha256sum video.py |
    awk '{print $1}'
)"


rollback() {

    echo
    echo "===== ROLLBACK ====="

    for F in $FILES
    do
        if [ -f "$BACK/$F" ]; then
            cp "$BACK/$F" "$F"
        else
            rm -f "$F"
        fi
    done

    echo "Rollback concluído."
}


# =====================================================
# 1. REAL MOTION FILTER COMPILER
# =====================================================

cat > vi6_61_motion_filter_compiler.py <<'PY'
#!/usr/bin/env python3

import math


VERSION = "6.61.1"


PROFILES = {

    "HOOK_PUSH": {
        "zoom_total": 0.060,
        "direction": "CENTER",
    },

    "DOCUMENTARY_DRIFT": {
        "zoom_total": 0.035,
        "direction": "CENTER",
    },

    "SLOW_PUSH": {
        "zoom_total": 0.045,
        "direction": "CENTER",
    },

    "HORIZONTAL_DISCOVERY": {
        "zoom_total": 0.035,
        "direction": "LEFT_TO_RIGHT",
    },

    "REVERSE_DRIFT": {
        "zoom_total": 0.035,
        "direction": "RIGHT_TO_LEFT",
    },

    "DETAIL_PUSH": {
        "zoom_total": 0.055,
        "direction": "CENTER",
    },

    "MICRO_MOTION": {
        "zoom_total": 0.020,
        "direction": "CENTER",
    },

    "CLIMAX_PUSH": {
        "zoom_total": 0.055,
        "direction": "CENTER",
    },

    "CLIMAX_PAN": {
        "zoom_total": 0.045,
        "direction": "LEFT_TO_RIGHT",
    },

    "CLIMAX_LOCK": {
        "zoom_total": 0.025,
        "direction": "CENTER",
    },

    "CTA_SETTLE": {
        "zoom_total": 0.020,
        "direction": "CENTER",
    },
}


def compile_filter(
    profile,
    duration_seconds,
    fps=30.0
):

    blockers = []
    warnings = []


    try:
        duration = float(
            duration_seconds
        )
    except Exception:
        duration = None


    try:
        fps = float(fps)
    except Exception:
        fps = None


    if (
        duration is None
        or duration <= 0
    ):
        blockers.append(
            "duration_invalid"
        )


    if (
        fps is None
        or fps <= 0
    ):
        blockers.append(
            "fps_invalid"
        )


    spec = PROFILES.get(
        profile
    )


    if spec is None:
        blockers.append(
            "unknown_motion_profile"
        )


    if blockers:

        return {
            "version": VERSION,
            "status": "HOLD",
            "profile": profile,
            "vf": None,
            "frames": None,
            "fps": fps,
            "blockers": blockers,
            "warnings": warnings,
        }


    frames = max(
        1,
        int(
            math.ceil(
                duration * fps
            )
        )
    )


    zoom_total = float(
        spec["zoom_total"]
    )


    zoom_step = (
        zoom_total
        / max(
            frames - 1,
            1
        )
    )


    zoom_end = (
        1.0
        + zoom_total
    )


    zoom_expr = (
        "if(eq(on,1),"
        "1.000000,"
        f"min(zoom+{zoom_step:.8f},"
        f"{zoom_end:.6f}))"
    )


    direction = spec[
        "direction"
    ]


    if direction == "LEFT_TO_RIGHT":

        x_expr = (
            "(iw-iw/zoom)"
            "*on/"
            f"{max(frames - 1, 1)}"
        )

        y_expr = (
            "(ih-ih/zoom)/2"
        )


    elif direction == "RIGHT_TO_LEFT":

        x_expr = (
            "(iw-iw/zoom)"
            "*(1-on/"
            f"{max(frames - 1, 1)})"
        )

        y_expr = (
            "(ih-ih/zoom)/2"
        )


    else:

        x_expr = (
            "(iw-iw/zoom)/2"
        )

        y_expr = (
            "(ih-ih/zoom)/2"
        )


    vf = (
        "scale="
        "1200:2133:"
        "force_original_aspect_ratio="
        "increase,"
        "crop=1200:2133,"
        "zoompan="
        f"z='{zoom_expr}':"
        f"x='{x_expr}':"
        f"y='{y_expr}':"
        f"d={frames}:"
        "s=1080x1920:"
        f"fps={fps:g},"
        "setsar=1,"
        "format=yuv420p"
    )


    return {
        "version": VERSION,

        "status": "COMPILED",

        "profile": profile,

        "direction": direction,

        "duration_seconds":
            duration,

        "fps":
            fps,

        "frames":
            frames,

        "zoom_total":
            zoom_total,

        "zoom_step":
            round(
                zoom_step,
                8
            ),

        "vf":
            vf,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "filter_applied":
            False,
    }


def self_test():

    for profile in PROFILES:

        result = compile_filter(
            profile,
            3.4,
            30
        )

        assert (
            result["status"]
            == "COMPILED"
        )

        assert (
            "zoompan="
            in result["vf"]
        )

        assert (
            "format=yuv420p"
            in result["vf"]
        )

        assert (
            result[
                "filter_applied"
            ]
            is False
        )


    assert (
        compile_filter(
            "SLOW_PUSH",
            3.4,
            30
        )["frames"]
        == 102
    )


    print(
        "VI6.61.1 MOTION FILTER COMPILER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 2. UPGRADE VI6.65
# =====================================================

cat > vi6_65_canary_candidate_selector.py <<'PY'
#!/usr/bin/env python3

from vi6_61_motion_diversity_planner import (
    plan as diversity_plan
)

from vi6_61_motion_filter_compiler import (
    compile_filter
)


VERSION = "6.65.1"


SAFE = {
    "SAFE_DIFFERENCE",
    "EXACT_MATCH",
}


def _score(event):

    scene = event.get("scene")

    duration = event.get(
        "duration_seconds"
    )

    status = event.get("status")


    try:
        duration = float(duration)
    except Exception:
        return None


    if event.get(
        "branch"
    ) != "STILL":
        return None


    if scene in {
        None,
        1,
        12,
    }:
        return None


    if status not in SAFE:
        return None


    if event.get("blockers"):
        return None


    if not (
        2.0
        <= duration
        <= 6.5
    ):
        return None


    role = (
        event.get("mega", {})
        .get("contract", {})
        .get("role")
    )


    score = 100.0


    score -= abs(
        duration - 3.5
    ) * 8.0


    if role == "CONTEXT":
        score += 15


    elif role == "CLIMAX":
        score -= 8


    if status == "SAFE_DIFFERENCE":
        score += 12


    if scene in {
        2,
        11,
    }:
        score -= 10


    interval = (
        event.get("mega", {})
        .get(
            "inter_event_wall_seconds"
        )
    )


    try:
        interval = float(interval)
    except Exception:
        interval = None


    if (
        interval is not None
        and interval > 7
    ):
        score -= 8


    return round(
        score,
        2
    )


def select(events):

    events = list(
        events
        or []
    )


    diversity = diversity_plan(
        events
    )


    profile_by_scene = {

        item.get("scene"):
            item.get(
                "recommended_profile"
            )

        for item in (
            diversity.get("plan")
            or []
        )
    }


    candidates = []


    for event in events:

        score = _score(
            event
        )


        if score is None:
            continue


        scene = event.get(
            "scene"
        )


        duration = event.get(
            "duration_seconds"
        )


        profile = profile_by_scene.get(
            scene
        )


        compiled = compile_filter(
            profile,
            duration,
            30
        )


        if compiled.get(
            "status"
        ) != "COMPILED":
            continue


        candidate = {
            "scene":
                scene,

            "score":
                score,

            "duration_seconds":
                duration,

            "status":
                event.get("status"),

            "role":
                (
                    event.get("mega", {})
                    .get("contract", {})
                    .get("role")
                ),

            "previous_motion_profile":
                (
                    event.get("mega", {})
                    .get("motion", {})
                    .get("profile")
                ),

            "recommended_motion_profile":
                profile,

            "legacy_vf":
                event.get(
                    "legacy_vf"
                ),

            # Important:
            # use actual compiled cinematic filter,
            # not VI6.50 structural dry-plan vf.
            "proposed_vi6_vf":
                compiled.get("vf"),

            "previous_dry_plan_vf":
                event.get(
                    "proposed_vi6_vf"
                ),

            "motion_compile":
                compiled,

            "command_fingerprint":
                event.get(
                    "command_fingerprint"
                ),
        }


        candidates.append(
            candidate
        )


    candidates.sort(
        key=lambda item: (
            item["score"],
            -item["scene"],
        ),
        reverse=True
    )


    winner = (
        candidates[0]
        if candidates
        else None
    )


    return {
        "version": VERSION,

        "status":
            (
                "SELECTED"
                if winner
                else "HOLD"
            ),

        "winner":
            winner,

        "candidates":
            candidates,

        "motion_diversity_status":
            diversity.get(
                "status"
            ),

        "active_authorized":
            False,
    }


def self_test():

    events = []


    for scene in range(
        1,
        13
    ):

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


        events.append(
            {
                "scene":
                    scene,

                "branch":
                    "STILL",

                "duration_seconds":
                    3.4,

                "status":
                    "SAFE_DIFFERENCE",

                "blockers":
                    [],

                "legacy_vf":
                    (
                        "scale=1200:2133,"
                        "zoompan="
                        "z='1.01':"
                        "x='0':y='0':"
                        "d=102:"
                        "s=1080x1920:"
                        "fps=30,"
                        "setsar=1,"
                        "format=yuv420p"
                    ),

                "proposed_vi6_vf":
                    (
                        "scale=1080:1920,"
                        "crop=1080:1920,"
                        "fps=30"
                    ),

                "mega": {
                    "contract": {
                        "role":
                            role
                    },

                    "motion": {
                        "profile":
                            "DOCUMENTARY_DRIFT"
                    },

                    "inter_event_wall_seconds":
                        4,
                },
            }
        )


    result = select(
        events
    )


    assert (
        result["status"]
        == "SELECTED"
    )


    winner = result[
        "winner"
    ]


    assert (
        "zoompan="
        in winner[
            "proposed_vi6_vf"
        ]
    )


    assert (
        winner[
            "previous_dry_plan_vf"
        ]
        != winner[
            "proposed_vi6_vf"
        ]
    )


    print(
        "VI6.65.1 CANARY SELECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 3. UPGRADE VI6.66
# =====================================================

cat > vi6_66_canary_filter_preview.py <<'PY'
#!/usr/bin/env python3


VERSION = "6.66.1"


FORBIDDEN = (
    ";",
    "\n",
    "\r",
    "`",
    "$(",
)


def _validate(vf):

    blockers = []
    warnings = []


    if not isinstance(
        vf,
        str
    ):

        return (
            ["filter_missing"],
            warnings
        )


    if len(vf) > 6000:

        blockers.append(
            "filter_too_large"
        )


    for token in FORBIDDEN:

        if token in vf:

            blockers.append(
                "unsafe_filter_token"
            )


    REQUIRED = (
        "scale=",
        "crop=",
        "zoompan=",
        "setsar=1",
        "format=yuv420p",
    )


    for item in REQUIRED:

        if item not in vf:

            blockers.append(
                "missing:"
                + item
            )


    if ":fps=" not in vf:

        blockers.append(
            "zoompan_fps_missing"
        )


    return (
        blockers,
        warnings
    )


def preview(candidate):

    if not candidate:

        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers":
                ["candidate_missing"],
            "filter_applied":
                False,
        }


    legacy = candidate.get(
        "legacy_vf"
    )


    proposed = candidate.get(
        "proposed_vi6_vf"
    )


    blockers, warnings = _validate(
        proposed
    )


    if not isinstance(
        legacy,
        str
    ):

        blockers.append(
            "legacy_filter_missing"
        )


    different = (
        isinstance(legacy, str)
        and isinstance(
            proposed,
            str
        )
        and legacy != proposed
    )


    if not different:

        blockers.append(
            "vi6_filter_not_different"
        )


    compile_data = (
        candidate.get(
            "motion_compile"
        )
        or {}
    )


    if (
        compile_data.get(
            "status"
        )
        != "COMPILED"
    ):

        blockers.append(
            "motion_filter_not_compiled"
        )


    return {
        "version":
            VERSION,

        "status":
            (
                "PREVIEW_READY"
                if not blockers
                else "HOLD"
            ),

        "scene":
            candidate.get(
                "scene"
            ),

        "motion_profile":
            candidate.get(
                "recommended_motion_profile"
            ),

        "legacy_vf":
            legacy,

        "proposed_vi6_vf":
            proposed,

        "previous_dry_plan_vf":
            candidate.get(
                "previous_dry_plan_vf"
            ),

        "different_from_legacy":
            different,

        "blockers":
            sorted(
                set(blockers)
            ),

        "warnings":
            warnings,

        "filter_applied":
            False,

        "command_mutated":
            False,
    }


def self_test():

    proposed = (
        "scale=1200:2133:"
        "force_original_aspect_ratio=increase,"
        "crop=1200:2133,"
        "zoompan="
        "z='1.01':"
        "x='0':"
        "y='0':"
        "d=102:"
        "s=1080x1920:"
        "fps=30,"
        "setsar=1,"
        "format=yuv420p"
    )


    result = preview(
        {
            "scene":
                5,

            "recommended_motion_profile":
                "SLOW_PUSH",

            "legacy_vf":
                "legacy",

            "proposed_vi6_vf":
                proposed,

            "motion_compile": {
                "status":
                    "COMPILED"
            },
        }
    )


    assert (
        result["status"]
        == "PREVIEW_READY"
    )


    assert (
        result["filter_applied"]
        is False
    )


    print(
        "VI6.66.1 FILTER PREVIEW=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 4. COMPILE
# =====================================================

echo
echo "===== COMPILE ====="

if ! python -m py_compile \
    vi6_61_motion_filter_compiler.py \
    vi6_65_canary_candidate_selector.py \
    vi6_66_canary_filter_preview.py \
    vi6_70_master_canary_gate.py
then

    rollback
    exit 10
fi


echo "COMPILE=PASS"


# =====================================================
# 5. SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

python vi6_61_motion_filter_compiler.py || {
    rollback
    exit 11
}


python vi6_65_canary_candidate_selector.py || {
    rollback
    exit 12
}


python vi6_66_canary_filter_preview.py || {
    rollback
    exit 13
}


# =====================================================
# 6. PROVE REAL SCENE 5 BEFORE RE-EVALUATION
# =====================================================

echo
echo "===== REAL SCENE 5 COMPILATION PROOF ====="

python - <<'PY'
import json
from pathlib import Path

from vi6_65_canary_candidate_selector import (
    select
)


BASE = Path.home() / "ShortAutoPro"


session = json.loads(
    (
        BASE
        / "logs/producao/"
          "vi6_60_shadow_session_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["session"]


result = select(
    session.get(
        "events"
    )
)


winner = (
    result.get(
        "winner"
    )
    or {}
)


print(
    "STATUS:",
    result.get("status")
)

print(
    "SCENE:",
    winner.get("scene")
)

print(
    "ROLE:",
    winner.get("role")
)

print(
    "DURATION:",
    winner.get(
        "duration_seconds"
    )
)

print(
    "OLD MOTION:",
    winner.get(
        "previous_motion_profile"
    )
)

print(
    "NEW MOTION:",
    winner.get(
        "recommended_motion_profile"
    )
)

print(
    "COMPILE STATUS:",
    (
        winner.get(
            "motion_compile"
        )
        or {}
    ).get(
        "status"
    )
)


vf = winner.get(
    "proposed_vi6_vf"
)


print(
    "VI6 HAS ZOOMPAN:",
    (
        isinstance(vf, str)
        and "zoompan=" in vf
    )
)

print(
    "VI6 HAS YUV420P:",
    (
        isinstance(vf, str)
        and "format=yuv420p"
        in vf
    )
)


if (
    result.get("status")
    != "SELECTED"
    or not isinstance(vf, str)
    or "zoompan=" not in vf
):

    raise SystemExit(
        "REAL_COMPILATION_PROOF_FAILED"
    )
PY


if [ "$?" -ne 0 ]; then

    rollback
    exit 14
fi


# =====================================================
# 7. RE-RUN VI6.70 OFFLINE
# =====================================================

echo
echo "======================================================"
echo " RE-EVALUATING VI6.70 OFFLINE"
echo "======================================================"

python \
    vi6_70_master_canary_gate.py \
    --real


# =====================================================
# 8. VERIFY REAL VI6.70
# =====================================================

echo
echo "===== VI6.70 FINAL VERIFICATION ====="

python - <<'PY'
import json
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"


gate = json.loads(
    (
        BASE
        / "logs/producao/"
          "vi6_70_master_canary_gate_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["gate"]


candidate = (
    gate.get(
        "candidate"
    )
    or {}
)


preview = (
    gate.get(
        "filter_preview"
    )
    or {}
)


print(
    "STATUS:",
    gate.get("status")
)

print(
    "SCENE:",
    candidate.get("scene")
)

print(
    "ROLE:",
    candidate.get("role")
)

print(
    "MOTION PROFILE:",
    candidate.get(
        "recommended_motion_profile"
    )
)

print(
    "FILTER PREVIEW:",
    preview.get("status")
)

print(
    "HAS ZOOMPAN:",
    (
        "zoompan="
        in (
            preview.get(
                "proposed_vi6_vf"
            )
            or ""
        )
    )
)

print(
    "DIFFERENT FROM LEGACY:",
    preview.get(
        "different_from_legacy"
    )
)

print(
    "BLOCKERS:",
    gate.get("blockers")
)

print(
    "WARNINGS:",
    gate.get("warnings")
)

print(
    "ACTIVE CANARY AUTHORIZED:",
    gate.get(
        "active_canary_authorized"
    )
)


if gate.get("status") not in {
    "CANARY_PREVIEW_READY",
    "CANARY_PREVIEW_READY_WITH_WARNINGS",
}:

    raise SystemExit(
        "VI670_STILL_HOLD"
    )


if preview.get(
    "status"
) != "PREVIEW_READY":

    raise SystemExit(
        "PREVIEW_STILL_HOLD"
    )
PY


if [ "$?" -ne 0 ]; then

    echo
    echo "VI6.70 ainda bloqueado."
    echo "Não execute VI6.71-6.80 ainda."

    exit 15
fi


# =====================================================
# 9. VIDEO.PY INTEGRITY
# =====================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py |
    awk '{print $1}'
)"


echo
echo "===== VIDEO.PY INTEGRITY ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"
echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo "CRITICAL: video.py mudou."

    rollback
    exit 16
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 10. RELEASE
# =====================================================

./release_check.sh || {
    rollback
    exit 17
}


echo
echo "======================================================"
echo " VI6.70 MOTION COMPILER REPAIR COMPLETE"
echo "======================================================"
echo
echo "REAL MOTION FILTER COMPILER=INSTALLED"
echo "CANARY FILTER=ZOOMPAN CAPABLE"
echo "VIDEO.PY MODIFIED=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "CANARY APPLIED=NO"
echo "ACTIVE=LOCKED"
echo
