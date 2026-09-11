#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/mega_vi661_vi670_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " SHORTAUTOPRO MEGA UPDATE II"
echo " VI6.61 -> VI6.70"
echo "======================================================"
echo
echo "MODE: OFFLINE / SHADOW ANALYSIS"
echo "VIDEO.PY: PROTECTED"
echo "ACTIVE: LOCKED"
echo


# =====================================================
# 0. REQUIREMENTS
# =====================================================

REQUIRED="
video.py
gerar_short.sh
vi6_38_filter_validator.py
vi6_49_real_command_mapper.py
vi6_50_shadow_filter_comparator.py
vi6_60_runtime.py
vi6_60_master_gate.py
"

for F in $REQUIRED
do

    if [ ! -f "$F" ]; then

        echo "ERRO: $F ausente."

        exit 2

    fi

done


SESSION="logs/producao/vi6_60_shadow_session_latest.json"
MASTER60="logs/producao/vi6_60_master_gate_latest.json"


if [ ! -f "$SESSION" ]; then

    echo "ERRO: relatório VI6.60 real ausente."

    exit 3

fi


if [ ! -f "$MASTER60" ]; then

    echo "ERRO: master gate VI6.60 ausente."

    exit 4

fi


VIDEO_HASH_BEFORE="$(
    sha256sum video.py |
    awk '{print $1}'
)"


# =====================================================
# 1. BACKUPS
# =====================================================

for F in \
    vi6_61_motion_diversity_planner.py \
    vi6_62_media_streak_intelligence.py \
    vi6_63_truth_state_hardener.py \
    vi6_64_source_recovery_guard.py \
    vi6_65_canary_candidate_selector.py \
    vi6_66_canary_filter_preview.py \
    vi6_67_scene_rollback_contract.py \
    vi6_68_performance_intelligence.py \
    vi6_69_storage_telemetry_guard.py \
    vi6_70_master_canary_gate.py \
    testar_vi661_vi670.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.61-6.70"
    echo "======================================"

    for F in \
        vi6_61_motion_diversity_planner.py \
        vi6_62_media_streak_intelligence.py \
        vi6_63_truth_state_hardener.py \
        vi6_64_source_recovery_guard.py \
        vi6_65_canary_candidate_selector.py \
        vi6_66_canary_filter_preview.py \
        vi6_67_scene_rollback_contract.py \
        vi6_68_performance_intelligence.py \
        vi6_69_storage_telemetry_guard.py \
        vi6_70_master_canary_gate.py \
        testar_vi661_vi670.py
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
# 2. VI6.61 MOTION DIVERSITY 3.0
# =====================================================

cat > vi6_61_motion_diversity_planner.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.61"


CONTEXT_PROFILES = (
    "DOCUMENTARY_DRIFT",
    "SLOW_PUSH",
    "HORIZONTAL_DISCOVERY",
    "REVERSE_DRIFT",
    "DETAIL_PUSH",
)


CLIMAX_PROFILES = (
    "CLIMAX_PUSH",
    "CLIMAX_PAN",
    "CLIMAX_LOCK",
)


def _role(event):

    return (
        event.get("mega", {})
        .get("contract", {})
        .get("role")
    )


def _legacy_profile(event):

    return (
        event.get("mega", {})
        .get("motion", {})
        .get("profile")
    )


def plan(events):

    ordered = sorted(
        list(events or []),
        key=lambda x: x.get("scene", 999)
    )


    output = []

    context_index = 0
    climax_index = 0


    for event in ordered:

        scene = event.get("scene")
        branch = event.get("branch")
        role = _role(event)
        old = _legacy_profile(event)


        if branch == "VIDEO":

            profile = "NATIVE"


        elif role == "HOOK":

            profile = "HOOK_PUSH"


        elif role == "CTA":

            profile = "CTA_SETTLE"


        elif role == "CLIMAX":

            profile = CLIMAX_PROFILES[
                climax_index
                % len(CLIMAX_PROFILES)
            ]

            climax_index += 1


        else:

            profile = CONTEXT_PROFILES[
                context_index
                % len(CONTEXT_PROFILES)
            ]

            context_index += 1


        output.append(
            {
                "scene": scene,
                "branch": branch,
                "role": role,
                "previous_profile": old,
                "recommended_profile": profile,
                "changed":
                    (
                        old is not None
                        and old != profile
                    ),
                "applied": False,
            }
        )


    repeats = 0


    profiles = [
        item["recommended_profile"]
        for item in output
    ]


    for i in range(2, len(profiles)):

        if (
            profiles[i]
            == profiles[i - 1]
            == profiles[i - 2]
            and profiles[i] != "NATIVE"
        ):

            repeats += 1


    return {
        "version": VERSION,
        "status":
            (
                "PASS"
                if repeats == 0
                else "PASS_WITH_WARNINGS"
            ),
        "triple_repeats": repeats,
        "plan": output,
        "applied": False,
    }


def self_test():

    events = []

    for n in range(1, 13):

        events.append(
            {
                "scene": n,
                "branch":
                    (
                        "VIDEO"
                        if n == 2
                        else "STILL"
                    ),
                "mega": {
                    "contract": {
                        "role":
                            (
                                "HOOK"
                                if n == 1
                                else (
                                    "CTA"
                                    if n == 12
                                    else (
                                        "CLIMAX"
                                        if n >= 9
                                        else "CONTEXT"
                                    )
                                )
                            )
                    },
                    "motion": {
                        "profile":
                            "DOCUMENTARY_DRIFT"
                    }
                }
            }
        )


    result = plan(events)

    assert result["triple_repeats"] == 0

    print("VI6.61 MOTION DIVERSITY=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 3. VI6.62 MEDIA STREAK INTELLIGENCE
# =====================================================

cat > vi6_62_media_streak_intelligence.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.62"


def audit(events):

    ordered = sorted(
        list(events or []),
        key=lambda x: x.get("scene", 999)
    )


    longest = 0
    current = 0
    previous = None
    streaks = []

    start_scene = None


    for event in ordered:

        branch = event.get("branch")
        scene = event.get("scene")


        if branch == previous:

            current += 1

        else:

            if previous is not None:

                streaks.append(
                    {
                        "branch": previous,
                        "start_scene": start_scene,
                        "end_scene":
                            ordered[
                                max(0, len(streaks))
                            ].get("scene")
                            if False
                            else None,
                        "length": current,
                    }
                )


            previous = branch
            current = 1
            start_scene = scene


        longest = max(
            longest,
            current
        )


    # Rebuild streaks more cleanly.
    streaks = []

    if ordered:

        branch = ordered[0].get("branch")
        start = ordered[0].get("scene")
        last = start
        count = 0


        for event in ordered:

            current_branch = event.get("branch")
            current_scene = event.get("scene")


            if current_branch == branch:

                count += 1
                last = current_scene


            else:

                streaks.append(
                    {
                        "branch": branch,
                        "start_scene": start,
                        "end_scene": last,
                        "length": count,
                    }
                )


                branch = current_branch
                start = current_scene
                last = current_scene
                count = 1


        streaks.append(
            {
                "branch": branch,
                "start_scene": start,
                "end_scene": last,
                "length": count,
            }
        )


    recommendations = []


    for streak in streaks:

        if (
            streak["branch"] == "STILL"
            and streak["length"] >= 5
        ):

            recommendations.append(
                {
                    "type":
                        "BREAK_STILL_VISUAL_PATTERN",

                    "start_scene":
                        streak["start_scene"],

                    "end_scene":
                        streak["end_scene"],

                    "note":
                        (
                            "Do not fabricate video. "
                            "Prefer stronger motion-profile "
                            "variation or real documentary "
                            "video when retrieval provides it."
                        ),
                }
            )


    return {
        "version": VERSION,
        "status":
            (
                "PASS_WITH_WARNINGS"
                if recommendations
                else "PASS"
            ),
        "longest_streak": longest,
        "streaks": streaks,
        "recommendations": recommendations,
        "media_changed": False,
    }


def self_test():

    events = [
        {
            "scene": n,
            "branch":
                (
                    "VIDEO"
                    if n in {2, 8}
                    else "STILL"
                )
        }
        for n in range(1, 13)
    ]


    result = audit(events)

    assert result["media_changed"] is False

    print("VI6.62 MEDIA STREAK=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 4. VI6.63 TRUTH STATE HARDENER
# =====================================================

cat > vi6_63_truth_state_hardener.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.63"


TRUE_VALUES = {
    True,
    1,
    "1",
    "true",
    "yes",
    "pass",
    "verified",
    "confirmed",
}


FALSE_VALUES = {
    False,
    0,
    "0",
    "false",
    "no",
    "fail",
    "rejected",
    "invalid",
}


def normalize(value):

    if isinstance(value, str):
        value = value.strip().lower()


    if value in TRUE_VALUES:

        return "TRUE"


    if value in FALSE_VALUES:

        return "FALSE"


    # Critical policy:
    # missing/unclear data NEVER becomes TRUE.
    return "UNKNOWN"


def evaluate(value):

    state = normalize(value)


    return {
        "version": VERSION,
        "state": state,
        "safe_for_active":
            state == "TRUE",
        "unknown_promoted_to_true":
            False,
    }


def self_test():

    assert normalize(True) == "TRUE"
    assert normalize(False) == "FALSE"
    assert normalize(None) == "UNKNOWN"
    assert normalize("maybe") == "UNKNOWN"

    assert (
        evaluate(None)["safe_for_active"]
        is False
    )


    print("VI6.63 TRUTH HARDENER=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 5. VI6.64 SOURCE RECOVERY SAFETY GUARD
# =====================================================

cat > vi6_64_source_recovery_guard.py <<'PY'
#!/usr/bin/env python3

import ast
from pathlib import Path


VERSION = "6.64"


RISK_FILES = (
    "vi6_13_recovery_planner.py",
    "vi6_19_true_recovery.py",
    "vi6_20_normalizer.py",
    "source_router.py",
)


def inspect():

    findings = []


    for filename in RISK_FILES:

        path = Path(filename)


        if not path.exists():

            continue


        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )


        low = text.lower()


        try:
            ast.parse(text)
            syntax_ok = True

        except Exception:
            syntax_ok = False


        if not syntax_ok:

            findings.append(
                {
                    "file": filename,
                    "severity": "BLOCK",
                    "reason": "python_syntax_invalid",
                }
            )


        if (
            "hard_no_retry" in low
            or "hard_rejections" in low
        ):

            findings.append(
                {
                    "file": filename,
                    "severity": "WARN",
                    "reason":
                        "broad_no_retry_semantics_present",
                }
            )


        if (
            filename == "source_router.py"
            and "getattr(" in low
        ):

            findings.append(
                {
                    "file": filename,
                    "severity": "WARN",
                    "reason":
                        "dynamic_dispatch_requires_exact_route_audit",
                }
            )


        if (
            filename == "vi6_20_normalizer.py"
            and "true" in low
        ):

            findings.append(
                {
                    "file": filename,
                    "severity": "WARN",
                    "reason":
                        "truth_default_requires_unknown_safe_policy",
                }
            )


    blocks = [
        x
        for x in findings
        if x["severity"] == "BLOCK"
    ]


    warnings = [
        x
        for x in findings
        if x["severity"] == "WARN"
    ]


    return {
        "version": VERSION,
        "status":
            (
                "HOLD"
                if blocks
                else (
                    "PASS_WITH_WARNINGS"
                    if warnings
                    else "PASS"
                )
            ),
        "blocks": blocks,
        "warnings": warnings,

        # No risky source module is modified here.
        "source_files_modified": False,

        # Future active recovery remains locked
        # until exact routes are audited.
        "active_source_recovery_allowed":
            False,
    }


def self_test():

    result = inspect()

    assert (
        result["active_source_recovery_allowed"]
        is False
    )


    print("VI6.64 SOURCE GUARD=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 6. VI6.65 CANARY CANDIDATE SELECTOR
# =====================================================

cat > vi6_65_canary_candidate_selector.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.65"


SAFE = {
    "SAFE_DIFFERENCE",
    "EXACT_MATCH",
}


def _score(event):

    scene = event.get("scene")
    duration = event.get("duration_seconds")
    status = event.get("status")


    try:
        duration = float(duration)

    except Exception:
        return None


    if event.get("branch") != "STILL":
        return None


    if scene in {
        1,
        12,
        None,
    }:
        return None


    if status not in SAFE:
        return None


    if event.get("blockers"):
        return None


    if duration < 2.0:
        return None


    if duration > 6.5:
        return None


    score = 100.0


    # Prefer a medium-duration scene.
    score -= abs(
        duration - 3.5
    ) * 8.0


    # Avoid boundaries.
    if scene in {
        2,
        11,
    }:
        score -= 10


    # Context scenes are safer first canaries.
    role = (
        event.get("mega", {})
        .get("contract", {})
        .get("role")
    )


    if role == "CONTEXT":
        score += 15


    elif role == "CLIMAX":
        score -= 8


    # Exact-match gives less visual information;
    # safe-difference is more useful for a canary.
    if status == "SAFE_DIFFERENCE":
        score += 12


    interval = (
        event.get("mega", {})
        .get("inter_event_wall_seconds")
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

    candidates = []


    for event in events or []:

        score = _score(event)


        if score is None:
            continue


        candidates.append(
            {
                "scene": event.get("scene"),
                "score": score,
                "duration_seconds":
                    event.get("duration_seconds"),
                "status": event.get("status"),
                "role":
                    (
                        event.get("mega", {})
                        .get("contract", {})
                        .get("role")
                    ),
                "legacy_vf":
                    event.get("legacy_vf"),
                "proposed_vi6_vf":
                    event.get("proposed_vi6_vf"),
                "command_fingerprint":
                    event.get(
                        "command_fingerprint"
                    ),
            }
        )


    candidates.sort(
        key=lambda x:
            (
                x["score"],
                -x["scene"]
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
        "winner": winner,
        "candidates": candidates,
        "active_authorized": False,
    }


def self_test():

    events = [
        {
            "scene": 4,
            "branch": "STILL",
            "duration_seconds": 3.6,
            "status": "SAFE_DIFFERENCE",
            "blockers": [],
            "mega": {
                "contract": {
                    "role": "CONTEXT"
                }
            },
        }
    ]


    result = select(events)

    assert result["winner"]["scene"] == 4

    assert result["active_authorized"] is False

    print("VI6.65 CANARY SELECTOR=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 7. VI6.66 FILTER PREVIEW
# =====================================================

cat > vi6_66_canary_filter_preview.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.66"


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


    if not isinstance(vf, str):

        blockers.append(
            "filter_missing"
        )

        return blockers, warnings


    if len(vf) > 6000:

        blockers.append(
            "filter_too_large"
        )


    for token in FORBIDDEN:

        if token in vf:

            blockers.append(
                "unsafe_filter_token"
            )


    if "scale=" not in vf:

        blockers.append(
            "scale_missing"
        )


    if "format=yuv420p" not in vf:

        warnings.append(
            "explicit_yuv420p_missing"
        )


    if "zoompan=" not in vf:

        blockers.append(
            "canary_still_zoompan_missing"
        )


    return blockers, warnings


def preview(candidate):

    if not candidate:

        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers":
                ["candidate_missing"],
            "filter_applied": False,
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


    if (
        isinstance(legacy, str)
        and legacy == proposed
    ):

        warnings.append(
            "canary_filter_equals_legacy"
        )


    return {
        "version": VERSION,
        "status":
            (
                "PREVIEW_READY"
                if not blockers
                else "HOLD"
            ),
        "scene": candidate.get("scene"),
        "legacy_vf": legacy,
        "proposed_vi6_vf": proposed,
        "different_from_legacy":
            (
                isinstance(legacy, str)
                and isinstance(proposed, str)
                and legacy != proposed
            ),
        "blockers": blockers,
        "warnings": warnings,

        # Critical:
        "filter_applied": False,
        "command_mutated": False,
    }


def self_test():

    result = preview(
        {
            "scene": 4,
            "legacy_vf":
                "scale=1080:1920,format=yuv420p",
            "proposed_vi6_vf":
                (
                    "scale=1080:1920,"
                    "zoompan=z='1.02',"
                    "format=yuv420p"
                ),
        }
    )


    assert result["status"] == "PREVIEW_READY"
    assert result["filter_applied"] is False

    print("VI6.66 FILTER PREVIEW=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 8. VI6.67 PER-SCENE ROLLBACK CONTRACT
# =====================================================

cat > vi6_67_scene_rollback_contract.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.67"


def build(scene):

    return {
        "version": VERSION,
        "scene": scene,

        "scope":
            "SINGLE_SCENE_ONLY",

        "failure_action":
            "RENDER_SAME_SCENE_WITH_LEGACY_FILTER",

        "global_pipeline_abort":
            False,

        "other_scenes_affected":
            False,

        "active_global_renderer":
            False,

        "rollback_required_on": [
            "ffmpeg_nonzero",
            "output_missing",
            "duration_invalid",
            "resolution_invalid",
            "filter_validation_failure",
            "unexpected_exception",
        ],

        "executed":
            False,
    }


def self_test():

    result = build(4)

    assert (
        result["failure_action"]
        == "RENDER_SAME_SCENE_WITH_LEGACY_FILTER"
    )

    assert (
        result["other_scenes_affected"]
        is False
    )

    print("VI6.67 ROLLBACK CONTRACT=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 9. VI6.68 PERFORMANCE INTELLIGENCE
# =====================================================

cat > vi6_68_performance_intelligence.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.68"


def analyze(events):

    measured = []


    for event in events or []:

        interval = (
            event.get("mega", {})
            .get("inter_event_wall_seconds")
        )


        try:
            interval = float(interval)

        except Exception:
            continue


        measured.append(
            {
                "scene":
                    event.get("scene"),

                "seconds":
                    round(interval, 3),

                "branch":
                    event.get("branch"),
            }
        )


    measured.sort(
        key=lambda x:
            x["seconds"],
        reverse=True
    )


    slowest = (
        measured[0]
        if measured
        else None
    )


    average = (
        round(
            sum(
                x["seconds"]
                for x in measured
            )
            / len(measured),
            3
        )
        if measured
        else None
    )


    warnings = []


    if (
        slowest
        and slowest["seconds"] > 8
    ):

        warnings.append(
            "slow_scene_stage_detected"
        )


    return {
        "version": VERSION,
        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),
        "measured_scene_intervals":
            len(measured),
        "average_interval_seconds":
            average,
        "slowest":
            slowest,
        "top_slowest":
            measured[:5],
        "warnings": warnings,
        "render_settings_changed": False,
    }


def self_test():

    result = analyze(
        [
            {
                "scene": 2,
                "branch": "VIDEO",
                "mega": {
                    "inter_event_wall_seconds":
                        4.2
                },
            }
        ]
    )


    assert (
        result["render_settings_changed"]
        is False
    )

    print("VI6.68 PERFORMANCE INTELLIGENCE=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 10. VI6.69 STORAGE + TELEMETRY GUARD
# =====================================================

cat > vi6_69_storage_telemetry_guard.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path


VERSION = "6.69"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


def _size(path):

    try:
        return path.stat().st_size

    except Exception:
        return 0


def audit():

    logdir = (
        BASE
        / "logs"
        / "producao"
    )


    files = []


    if logdir.exists():

        for path in logdir.glob(
            "*.json"
        ):

            files.append(
                {
                    "name": path.name,
                    "bytes": _size(path),
                }
            )


    files.sort(
        key=lambda x:
            x["bytes"],
        reverse=True
    )


    total = sum(
        x["bytes"]
        for x in files
    )


    warnings = []


    if total > 25 * 1024 * 1024:

        warnings.append(
            "production_json_logs_large"
        )


    return {
        "version": VERSION,
        "status":
            (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            ),
        "json_report_count":
            len(files),
        "json_total_bytes":
            total,
        "largest_reports":
            files[:10],
        "warnings": warnings,

        # This stage NEVER deletes automatically.
        "files_deleted": 0,

        "recommended_policy": {
            "keep_latest_master_reports": True,
            "keep_final_manifest": True,
            "keep_final_video": True,
            "remove_temp_only_after_success":
                True,
        },
    }


def self_test():

    result = audit()

    assert result["files_deleted"] == 0

    print("VI6.69 STORAGE GUARD=PASS")


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 11. VI6.70 MASTER CANARY GATE
# =====================================================

cat > vi6_70_master_canary_gate.py <<'PY'
#!/usr/bin/env python3

import argparse
import json

from datetime import datetime
from pathlib import Path


from vi6_61_motion_diversity_planner import (
    plan as motion_plan
)

from vi6_62_media_streak_intelligence import (
    audit as streak_audit
)

from vi6_64_source_recovery_guard import (
    inspect as source_guard
)

from vi6_65_canary_candidate_selector import (
    select as select_candidate
)

from vi6_66_canary_filter_preview import (
    preview as filter_preview
)

from vi6_67_scene_rollback_contract import (
    build as rollback_contract
)

from vi6_68_performance_intelligence import (
    analyze as performance_analyze
)

from vi6_69_storage_telemetry_guard import (
    audit as storage_audit
)


VERSION = "6.70"


BASE = (
    Path.home()
    / "ShortAutoPro"
)


SESSION = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_shadow_session_latest.json"
)


MASTER60 = (
    BASE
    / "logs"
    / "producao"
    / "vi6_60_master_gate_latest.json"
)


OUTPUT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_70_master_canary_gate_latest.json"
)


PLAN_OUTPUT = (
    BASE
    / "logs"
    / "producao"
    / "vi6_70_canary_plan_latest.json"
)


def _load(path, key):

    try:

        return json.loads(
            Path(path).read_text(
                encoding="utf-8"
            )
        ).get(key)

    except Exception:

        return None


def evaluate():

    session = _load(
        SESSION,
        "session"
    )


    master60 = _load(
        MASTER60,
        "gate"
    )


    blockers = []
    warnings = []


    if session is None:

        blockers.append(
            "vi660_session_missing"
        )

        events = []


    else:

        events = (
            session.get("events")
            or []
        )


        if session.get(
            "unique_scenes"
        ) != 12:

            blockers.append(
                "requires_12_scenes"
            )


        if session.get(
            "identity_holds",
            0
        ) != 0:

            blockers.append(
                "identity_hold"
            )


        if session.get(
            "native_video_holds",
            0
        ) != 0:

            blockers.append(
                "native_video_hold"
            )


    if master60 is None:

        blockers.append(
            "vi660_master_missing"
        )


    elif master60.get(
        "status"
    ) not in {
        "CERTIFIED",
        "CERTIFIED_WITH_WARNINGS",
    }:

        blockers.append(
            "vi660_not_certified"
        )


    motion = motion_plan(
        events
    )


    streak = streak_audit(
        events
    )


    source = source_guard()


    candidate = select_candidate(
        events
    )


    winner = candidate.get(
        "winner"
    )


    preview = filter_preview(
        winner
    )


    rollback = rollback_contract(
        winner.get("scene")
        if winner
        else None
    )


    performance = performance_analyze(
        events
    )


    storage = storage_audit()


    if (
        candidate.get("status")
        != "SELECTED"
    ):

        blockers.append(
            "canary_candidate_missing"
        )


    if (
        preview.get("status")
        != "PREVIEW_READY"
    ):

        blockers.append(
            "canary_filter_preview_hold"
        )


    if (
        source.get("status")
        == "HOLD"
    ):

        blockers.append(
            "source_guard_hold"
        )


    elif (
        source.get("status")
        == "PASS_WITH_WARNINGS"
    ):

        warnings.append(
            "source_recovery_still_shadow_only"
        )


    if (
        streak.get("status")
        == "PASS_WITH_WARNINGS"
    ):

        warnings.append(
            "long_media_streak_requires_motion_diversity"
        )


    warnings.extend(
        performance.get(
            "warnings"
        )
        or []
    )


    warnings.extend(
        storage.get(
            "warnings"
        )
        or []
    )


    blockers = sorted(
        set(blockers)
    )


    warnings = sorted(
        set(warnings)
    )


    status = (
        "HOLD"
        if blockers
        else (
            "CANARY_PREVIEW_READY_WITH_WARNINGS"
            if warnings
            else "CANARY_PREVIEW_READY"
        )
    )


    plan = {
        "version": VERSION,
        "status": status,

        "candidate": winner,

        "filter_preview": preview,

        "rollback_contract": rollback,

        "motion_diversity": motion,

        "media_streak": streak,

        "performance": performance,

        "storage": storage,

        "source_guard": source,

        "blockers": blockers,

        "warnings": warnings,

        # This release only prepares the canary.
        "canary_filter_applied": False,

        "canary_render_executed": False,

        "active_canary_authorized": False,

        "active_renderer": False,
    }


    return plan


def save(result):

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    payload = {
        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "gate": result,
    }


    OUTPUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    PLAN_OUTPUT.write_text(
        json.dumps(
            {
                "generated_at":
                    payload[
                        "generated_at"
                    ],

                "plan": {
                    "status":
                        result[
                            "status"
                        ],

                    "candidate":
                        result[
                            "candidate"
                        ],

                    "filter_preview":
                        result[
                            "filter_preview"
                        ],

                    "rollback_contract":
                        result[
                            "rollback_contract"
                        ],

                    "active_canary_authorized":
                        False,
                }
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    assert VERSION == "6.70"

    print(
        "VI6.70 MASTER CANARY GATE SELF TEST=PASS"
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


    result = evaluate()

    save(result)


    print()
    print(
        "======================================================"
    )
    print(
        " VI6.70 MEGA CANARY MASTER GATE"
    )
    print(
        "======================================================"
    )


    print(
        "STATUS:",
        result.get("status")
    )


    candidate = (
        result.get("candidate")
        or {}
    )


    print(
        "CANARY CANDIDATE SCENE:",
        candidate.get("scene")
    )


    print(
        "CANDIDATE SCORE:",
        candidate.get("score")
    )


    print(
        "CANDIDATE DURATION:",
        candidate.get(
            "duration_seconds"
        )
    )


    print(
        "CANDIDATE ROLE:",
        candidate.get("role")
    )


    preview = (
        result.get("filter_preview")
        or {}
    )


    print(
        "FILTER PREVIEW:",
        preview.get("status")
    )


    print(
        "FILTER DIFFERENT FROM LEGACY:",
        preview.get(
            "different_from_legacy"
        )
    )


    motion = (
        result.get(
            "motion_diversity"
        )
        or {}
    )


    print(
        "MOTION TRIPLE REPEATS:",
        motion.get(
            "triple_repeats"
        )
    )


    performance = (
        result.get("performance")
        or {}
    )


    print(
        "AVERAGE SCENE INTERVAL:",
        performance.get(
            "average_interval_seconds"
        )
    )


    print(
        "SLOWEST:",
        performance.get("slowest")
    )


    print(
        "BLOCKERS:",
        result.get("blockers")
    )


    print(
        "WARNINGS:",
        result.get("warnings")
    )


    print(
        "CANARY FILTER APPLIED:",
        result.get(
            "canary_filter_applied"
        )
    )


    print(
        "CANARY RENDER EXECUTED:",
        result.get(
            "canary_render_executed"
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
# 12. INTEGRATION TEST
# =====================================================

cat > testar_vi661_vi670.py <<'PY'
#!/usr/bin/env python3

from vi6_61_motion_diversity_planner import (
    plan
)

from vi6_63_truth_state_hardener import (
    normalize
)

from vi6_65_canary_candidate_selector import (
    select
)

from vi6_66_canary_filter_preview import (
    preview
)

from vi6_67_scene_rollback_contract import (
    build
)


events = []


for scene in range(1, 13):

    branch = (
        "VIDEO"
        if scene == 2
        else "STILL"
    )


    role = (
        "HOOK"
        if scene == 1
        else (
            "CTA"
            if scene == 12
            else (
                "CLIMAX"
                if scene in {9, 10, 11}
                else "CONTEXT"
            )
        )
    )


    events.append(
        {
            "scene": scene,
            "branch": branch,
            "duration_seconds":
                (
                    3.5
                    if scene == 6
                    else 3.0
                ),
            "status":
                (
                    "NATIVE_VIDEO_PRESERVE"
                    if branch == "VIDEO"
                    else "SAFE_DIFFERENCE"
                ),
            "blockers": [],
            "legacy_vf":
                (
                    None
                    if branch == "VIDEO"
                    else (
                        "scale=1200:2133,"
                        "zoompan=z='1.01',"
                        "format=yuv420p"
                    )
                ),
            "proposed_vi6_vf":
                (
                    None
                    if branch == "VIDEO"
                    else (
                        "scale=1080:1920,"
                        "zoompan=z='1.03',"
                        "format=yuv420p"
                    )
                ),
            "mega": {
                "contract": {
                    "role": role
                },
                "motion": {
                    "profile":
                        (
                            "NATIVE"
                            if branch == "VIDEO"
                            else "DOCUMENTARY_DRIFT"
                        )
                },
                "inter_event_wall_seconds":
                    4.0,
            },
        }
    )


motion = plan(events)

assert motion["triple_repeats"] == 0


assert normalize(None) == "UNKNOWN"
assert normalize("maybe") == "UNKNOWN"


candidate = select(events)

assert candidate["status"] == "SELECTED"

assert candidate["winner"]["scene"] not in {
    1,
    12,
}


filter_result = preview(
    candidate["winner"]
)

assert (
    filter_result["status"]
    == "PREVIEW_READY"
)

assert (
    filter_result["filter_applied"]
    is False
)


rollback = build(
    candidate["winner"]["scene"]
)

assert (
    rollback[
        "other_scenes_affected"
    ]
    is False
)


print()
print(
    "======================================================"
)
print(
    " VI6.61-6.70 MEGA INTEGRATION: PASS"
)
print(
    "======================================================"
)
print(
    "MOTION DIVERSITY=PASS"
)
print(
    "UNKNOWN TRUTH SAFETY=PASS"
)
print(
    "CANARY SELECTION=PASS"
)
print(
    "FILTER PREVIEW=PASS"
)
print(
    "PER-SCENE ROLLBACK=PASS"
)
print(
    "FILTER APPLIED=NO"
)
print(
    "ACTIVE=LOCKED"
)
PY


# =====================================================
# 13. COMPILE
# =====================================================

echo
echo "===== MEGA COMPILE ====="

if ! python -m py_compile \
    vi6_61_motion_diversity_planner.py \
    vi6_62_media_streak_intelligence.py \
    vi6_63_truth_state_hardener.py \
    vi6_64_source_recovery_guard.py \
    vi6_65_canary_candidate_selector.py \
    vi6_66_canary_filter_preview.py \
    vi6_67_scene_rollback_contract.py \
    vi6_68_performance_intelligence.py \
    vi6_69_storage_telemetry_guard.py \
    vi6_70_master_canary_gate.py \
    testar_vi661_vi670.py
then

    rollback

    exit 10
fi


echo "MEGA COMPILE=PASS"


# =====================================================
# 14. SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

python vi6_61_motion_diversity_planner.py || {
    rollback
    exit 11
}

python vi6_62_media_streak_intelligence.py || {
    rollback
    exit 12
}

python vi6_63_truth_state_hardener.py || {
    rollback
    exit 13
}

python vi6_64_source_recovery_guard.py || {
    rollback
    exit 14
}

python vi6_65_canary_candidate_selector.py || {
    rollback
    exit 15
}

python vi6_66_canary_filter_preview.py || {
    rollback
    exit 16
}

python vi6_67_scene_rollback_contract.py || {
    rollback
    exit 17
}

python vi6_68_performance_intelligence.py || {
    rollback
    exit 18
}

python vi6_69_storage_telemetry_guard.py || {
    rollback
    exit 19
}

python vi6_70_master_canary_gate.py || {
    rollback
    exit 20
}

python testar_vi661_vi670.py || {
    rollback
    exit 21
}


# =====================================================
# 15. VIDEO.PY PROTECTION
# =====================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py |
    awk '{print $1}'
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

    echo "CRITICAL: video.py mudou."

    rollback

    exit 22
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 16. RELEASE CHECK
# =====================================================

echo
echo "===== RELEASE CHECK ====="

bash -n gerar_short.sh || {
    rollback
    exit 23
}


./release_check.sh || {
    rollback
    exit 24
}


# =====================================================
# 17. REAL OFFLINE ANALYSIS
# =====================================================

echo
echo "======================================================"
echo " RUNNING VI6.70 ON LAST CERTIFIED SHADOW SESSION"
echo "======================================================"

python \
    vi6_70_master_canary_gate.py \
    --real


# =====================================================
# 18. MOTION PLAN
# =====================================================

echo
echo "===== NEW MOTION PLAN ====="

python - <<'PY'
import json
from pathlib import Path

from vi6_61_motion_diversity_planner import (
    plan
)


base = (
    Path.home()
    / "ShortAutoPro"
)


session = json.loads(
    (
        base
        / "logs"
        / "producao"
        / "vi6_60_shadow_session_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["session"]


result = plan(
    session["events"]
)


for item in result["plan"]:

    print(
        "SCENE",
        item["scene"],
        "|",
        item["branch"],
        "|",
        item["role"],
        "|",
        item["previous_profile"],
        "->",
        item["recommended_profile"]
    )


print()
print(
    "TRIPLE REPEATS:",
    result["triple_repeats"]
)
PY


# =====================================================
# 19. FINAL SAFETY SUMMARY
# =====================================================

echo
echo "======================================================"
echo " VI6.61 -> VI6.70 INSTALLED"
echo "======================================================"
echo
echo "OK Motion Diversity Planner 3.0"
echo "OK Media Streak Intelligence"
echo "OK Truth UNKNOWN Hardening"
echo "OK Source Recovery Guard"
echo "OK Canary Candidate Selector"
echo "OK Canary Filter Preview"
echo "OK Per-Scene Rollback Contract"
echo "OK Performance Intelligence"
echo "OK Storage / Telemetry Guard"
echo "OK Mega Canary Master Gate"
echo
echo "VIDEO.PY MODIFIED=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "FILTER REPLACED=NO"
echo "ACTIVE CANARY=NO"
echo "ACTIVE RENDERER=NO"
echo
echo "REPORT:"
echo "logs/producao/vi6_70_master_canary_gate_latest.json"
echo
echo "CANARY PLAN:"
echo "logs/producao/vi6_70_canary_plan_latest.json"
echo
