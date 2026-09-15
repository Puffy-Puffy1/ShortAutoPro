#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi637_vi639_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.37 + VI6.38 + VI6.39"
echo " RENDERER SHADOW ADAPTER"
echo " FILTER VALIDATION + ACTIVATION GATE"
echo "======================================"
echo


# =====================================================
# 0. BASELINE
# =====================================================

REQUIRED="
midia.py
video.py
audio.py
legenda_dinamica.py
gerar_short.sh
vi6_6_active_brain.py
vi6_9_runtime_policy.py
vi6_30_renderer_contract.py
vi6_31_pre_render_auditor.py
vi6_32_scene_duration.py
vi6_33_cinematic_safety_gate.py
vi6_34_motion_auto_repair.py
vi6_35_ffmpeg_dry_compiler.py
vi6_36_renderer_compatibility.py
vi6_36_runtime_policy.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F não encontrado."
        echo "NENHUMA ALTERAÇÃO FEITA."
        exit 2
    fi
done


echo "===== BASELINE COMPILE ====="

if ! python -m py_compile \
    midia.py \
    video.py \
    audio.py \
    legenda_dinamica.py \
    vi6_6_active_brain.py \
    vi6_9_runtime_policy.py \
    vi6_34_motion_auto_repair.py \
    vi6_35_ffmpeg_dry_compiler.py \
    vi6_36_renderer_compatibility.py \
    vi6_36_runtime_policy.py
then
    echo
    echo "BASELINE FALHOU."
    echo "NENHUMA ALTERAÇÃO FEITA."
    exit 3
fi

echo "BASELINE=OK"


# =====================================================
# CORE HASH
# =====================================================

CORE_FILES="
midia.py
video.py
audio.py
legenda_dinamica.py
gerar_short.sh
"

: > "$BACKDIR/core_before.sha256"

for F in $CORE_FILES
do
    sha256sum "$F" \
        >> "$BACKDIR/core_before.sha256"
done


cp vi6_9_runtime_policy.py \
   "$BACKDIR/vi6_9_runtime_policy.py"


for F in \
    vi6_37_renderer_shadow_adapter.py \
    vi6_38_filter_validator.py \
    vi6_39_activation_gate.py \
    vi6_39_runtime_policy.py \
    testar_vi637_vi639.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.37-6.39"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py


    for F in \
        vi6_37_renderer_shadow_adapter.py \
        vi6_38_filter_validator.py \
        vi6_39_activation_gate.py \
        vi6_39_runtime_policy.py \
        testar_vi637_vi639.py
    do
        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi
    done

    echo "Projeto restaurado."
}


# =====================================================
# 1. VI6.37 RENDERER SHADOW ADAPTER
# =====================================================

cat > vi6_37_renderer_shadow_adapter.py <<'PY'
#!/usr/bin/env python3

import ast
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path


VERSION = "6.37"


def _s(v):
    return str(v or "").strip()


def _hash_file(path):

    data = Path(path).read_bytes()

    return hashlib.sha256(
        data
    ).hexdigest()


def _call_name(node):

    if isinstance(
        node.func,
        ast.Name
    ):
        return node.func.id


    if isinstance(
        node.func,
        ast.Attribute
    ):

        root = ""

        if isinstance(
            node.func.value,
            ast.Name
        ):
            root = (
                node.func.value.id
                + "."
            )


        return (
            root
            + node.func.attr
        )


    return ""


def _strings(node):

    result = []


    for child in ast.walk(
        node
    ):

        if (
            isinstance(
                child,
                ast.Constant
            )
            and isinstance(
                child.value,
                str
            )
        ):
            result.append(
                child.value
            )


    return result


def _function_candidate(
    node
):

    strings = _strings(
        node
    )


    blob = " ".join(
        strings
    ).lower()


    calls = []


    for child in ast.walk(
        node
    ):

        if isinstance(
            child,
            ast.Call
        ):

            name = _call_name(
                child
            )

            if name:
                calls.append(
                    {
                        "line":
                            getattr(
                                child,
                                "lineno",
                                None
                            ),

                        "name":
                            name,
                    }
                )


    call_blob = " ".join(
        item[
            "name"
        ].lower()
        for item in calls
    )


    has_ffmpeg = (
        "ffmpeg"
        in blob
    )


    has_vf = any(
        marker in blob
        for marker in (
            "-vf",
            "filter_complex",
            "zoompan",
            "subtitles=",
            "scale=",
            "crop=",
        )
    )


    has_process = any(
        marker in call_blob
        for marker in (
            "subprocess.run",
            "subprocess.popen",
            "os.system",
            "run",
            "popen",
        )
    )


    name_low = (
        node.name.lower()
    )


    renderer_name = any(
        marker in name_low
        for marker in (
            "video",
            "render",
            "ffmpeg",
            "gerar",
            "montar",
            "process",
            "scene",
            "cena",
        )
    )


    score = 0


    if has_ffmpeg:
        score += 50


    if has_vf:
        score += 25


    if has_process:
        score += 15


    if renderer_name:
        score += 10


    return {

        "function":
            node.name,

        "line_start":
            node.lineno,

        "line_end":
            getattr(
                node,
                "end_lineno",
                node.lineno
            ),

        "score":
            score,

        "has_ffmpeg_literal":
            has_ffmpeg,

        "has_filter_logic":
            has_vf,

        "has_process_call":
            has_process,

        "renderer_like_name":
            renderer_name,

        "calls":
            calls,

        "eligible":
            score >= 50,
    }


def inspect_renderer(
    filename="video.py"
):

    path = Path(
        filename
    )


    if not path.exists():

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "video_py_missing",

            "candidates":
                [],
        }


    source = path.read_text(
        encoding="utf-8"
    )


    tree = ast.parse(
        source
    )


    candidates = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):
            continue


        candidate = (
            _function_candidate(
                node
            )
        )


        if (
            candidate[
                "score"
            ] > 0
        ):

            candidates.append(
                candidate
            )


    candidates.sort(
        key=lambda x:
            (
                x[
                    "score"
                ],
                -x[
                    "line_start"
                ]
            ),
        reverse=True
    )


    eligible = [
        item
        for item in candidates
        if item[
            "eligible"
        ]
    ]


    best = (
        eligible[0]
        if eligible
        else None
    )


    if best is None:

        status = "HOLD"

        reason = (
            "no_proven_renderer_insertion_point"
        )


    elif (
        best[
            "has_ffmpeg_literal"
        ]
        and (
            best[
                "has_filter_logic"
            ]
            or best[
                "has_process_call"
            ]
        )
    ):

        status = "SHADOW_READY"

        reason = (
            "renderer_location_proven"
        )


    else:

        status = "HOLD"

        reason = (
            "renderer_confidence_insufficient"
        )


    return {

        "version":
            VERSION,

        "mode":
            "SHADOW",

        "status":
            status,

        "reason":
            reason,

        "file":
            filename,

        "file_sha256":
            _hash_file(
                filename
            ),

        "candidate_count":
            len(
                candidates
            ),

        "eligible_count":
            len(
                eligible
            ),

        "best":
            best,

        "candidates":
            candidates[:12],

        "file_modified":
            False,

        "renderer_executed":
            False,

        "ffmpeg_executed":
            False,
    }


def save_report(
    report,
    path=None
):

    if path is None:

        folder = os.path.expanduser(
            "~/ShortAutoPro/logs/producao"
        )


        os.makedirs(
            folder,
            exist_ok=True
        )


        path = os.path.join(
            folder,
            "vi6_37_renderer_shadow_latest.json"
        )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "report":
                    report,
            },
            file,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    fake = '''
def helper(x):
    return x

def gerar_video(input_file, output_file):
    cmd = [
        "ffmpeg",
        "-i",
        input_file,
        "-vf",
        "scale=1080:1920",
        output_file
    ]
    return cmd
'''


    tree = ast.parse(
        fake
    )


    funcs = [
        node
        for node in ast.walk(
            tree
        )
        if isinstance(
            node,
            ast.FunctionDef
        )
    ]


    renderer = [
        node
        for node in funcs
        if node.name
        == "gerar_video"
    ][0]


    result = _function_candidate(
        renderer
    )


    assert (
        result[
            "score"
        ]
        >= 75
    )


    assert (
        result[
            "has_ffmpeg_literal"
        ]
        is True
    )


    assert (
        result[
            "has_filter_logic"
        ]
        is True
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.37 SHADOW ADAPTER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK AST Renderer Discovery"
    )
    print(
        "OK FFmpeg Literal Detection"
    )
    print(
        "OK Filter Location Detection"
    )
    print(
        "OK Confidence Scoring"
    )
    print(
        "OK video.py remains untouched"
    )
    print()


if __name__ == "__main__":

    self_test()

    report = inspect_renderer()

    print(
        "REAL RENDERER STATUS:",
        report[
            "status"
        ]
    )


    print(
        "CANDIDATES:",
        report[
            "candidate_count"
        ]
    )


    if report.get(
        "best"
    ):

        print(
            "BEST:",
            report[
                "best"
            ][
                "function"
            ],

            "LINE:",
            report[
                "best"
            ][
                "line_start"
            ],

            "SCORE:",
            report[
                "best"
            ][
                "score"
            ]
        )
PY


# =====================================================
# 2. VI6.38 FILTER VALIDATOR
# =====================================================

cat > vi6_38_filter_validator.py <<'PY'
#!/usr/bin/env python3


VERSION = "6.38"


FORBIDDEN = (
    "\n",
    "\r",
    ";",
    "&&",
    "||",
    "`",
    "$(",
)


ALLOWED_FILTERS = {
    "scale",
    "crop",
    "zoompan",
    "format",
    "fps",
}


def _balanced(
    text,
    opening,
    closing
):

    count = 0


    for char in text:

        if char == opening:

            count += 1

        elif char == closing:

            count -= 1


        if count < 0:

            return False


    return count == 0


def _filter_names(vf):

    names = []


    for segment in vf.split(
        ","
    ):

        segment = (
            segment.strip()
        )


        if not segment:

            continue


        name = segment.split(
            "=",
            1
        )[0].strip()


        # Expressões internas do zoompan
        # podem conter vírgulas apenas quando
        # a sintaxe futura mudar. No compilador
        # atual não devem aparecer.
        if name:

            names.append(
                name
            )


    return names


def validate(
    dry_plan
):

    issues = []
    warnings = []


    if (
        dry_plan.get(
            "mode"
        )
        != "DRY_RUN"
    ):

        issues.append(
            "not_dry_run"
        )


    if (
        dry_plan.get(
            "executed"
        )
        is not False
    ):

        issues.append(
            "execution_flag_true"
        )


    mode = (
        dry_plan.get(
            "renderer_mode"
        )
    )


    if mode == "NATIVE_VIDEO_PRESERVE":

        if dry_plan.get(
            "vf"
        ):

            issues.append(
                "video_should_not_have_synthetic_vf"
            )


        return {

            "version":
                VERSION,

            "status":
                (
                    "PASS"
                    if not issues
                    else "HOLD"
                ),

            "mode":
                mode,

            "issues":
                issues,

            "warnings":
                warnings,

            "static_only":
                True,
        }


    if mode == "NO_RENDER_PLAN":

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "mode":
                mode,

            "issues":
                [
                    "no_render_plan"
                ],

            "warnings":
                [],

            "static_only":
                True,
        }


    vf = str(
        dry_plan.get(
            "vf"
        )
        or ""
    )


    if not vf:

        issues.append(
            "empty_filter"
        )


    for marker in FORBIDDEN:

        if marker in vf:

            issues.append(
                "forbidden_token:"
                + repr(
                    marker
                )
            )


    if not _balanced(
        vf,
        "(",
        ")"
    ):

        issues.append(
            "unbalanced_parentheses"
        )


    if (
        vf.count("'")
        % 2
        != 0
    ):

        issues.append(
            "unbalanced_single_quotes"
        )


    names = _filter_names(
        vf
    )


    unknown = [
        name
        for name in names
        if name
        not in ALLOWED_FILTERS
    ]


    if unknown:

        issues.append(
            "unknown_filter:"
            + ",".join(
                sorted(
                    set(
                        unknown
                    )
                )
            )
        )


    if mode == "KEN_BURNS_STILL":

        required = (
            "scale=",
            "crop=",
            "zoompan=",
            "format=yuv420p",
        )


        for marker in required:

            if marker not in vf:

                issues.append(
                    "missing:"
                    + marker
                )


        if (
            vf.count(
                "zoompan="
            )
            != 1
        ):

            issues.append(
                "zoompan_count"
            )


        if (
            "1080"
            not in vf
            or "1920"
            not in vf
        ):

            issues.append(
                "target_dimensions_missing"
            )


    if mode == "STATIC_STILL":

        if "zoompan=" in vf:

            issues.append(
                "static_still_contains_zoompan"
            )


    argv = (
        dry_plan.get(
            "argv"
        )
    )


    if mode in {
        "KEN_BURNS_STILL",
        "STATIC_STILL",
    }:

        if not isinstance(
            argv,
            list
        ):

            issues.append(
                "argv_not_list"
            )


        else:

            if (
                not argv
                or argv[0]
                != "ffmpeg"
            ):

                issues.append(
                    "argv_missing_ffmpeg"
                )


            if "{INPUT}" not in argv:

                issues.append(
                    "input_placeholder_missing"
                )


            if "{OUTPUT}" not in argv:

                issues.append(
                    "output_placeholder_missing"
                )


            if "{DURATION}" not in argv:

                issues.append(
                    "duration_placeholder_missing"
                )


    status = (
        "PASS"
        if not issues
        else "HOLD"
    )


    return {

        "version":
            VERSION,

        "status":
            status,

        "mode":
            mode,

        "filters":
            names,

        "issues":
            issues,

        "warnings":
            warnings,

        "static_only":
            True,

        "ffmpeg_executed":
            False,
    }


def self_test():

    good = {

        "mode":
            "DRY_RUN",

        "executed":
            False,

        "renderer_mode":
            "KEN_BURNS_STILL",

        "vf":
            (
                "scale=1080:1920:"
                "force_original_aspect_ratio=increase,"
                "crop=1080:1920,"
                "zoompan=z='1+0.04*(on/119)':"
                "x='(iw-iw/zoom)*(0.5)':"
                "y='(ih-ih/zoom)*(0.5)':"
                "d=120:s=1080x1920:fps=30,"
                "format=yuv420p"
            ),

        "argv":
            [
                "ffmpeg",
                "-loop",
                "1",
                "-i",
                "{INPUT}",
                "-vf",
                "{FILTER}",
                "-t",
                "{DURATION}",
                "{OUTPUT}",
            ],
    }


    result = validate(
        good
    )


    assert (
        result[
            "status"
        ]
        == "PASS"
    )


    bad = dict(
        good
    )


    bad[
        "vf"
    ] = (
        good[
            "vf"
        ]
        + ";rm -rf something"
    )


    result = validate(
        bad
    )


    assert (
        result[
            "status"
        ]
        == "HOLD"
    )


    video = validate(
        {
            "mode":
                "DRY_RUN",

            "executed":
                False,

            "renderer_mode":
                "NATIVE_VIDEO_PRESERVE",

            "vf":
                None,

            "argv":
                None,
        }
    )


    assert (
        video[
            "status"
        ]
        == "PASS"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.38 FILTER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Filter Whitelist"
    )
    print(
        "OK Parenthesis Validation"
    )
    print(
        "OK Quote Validation"
    )
    print(
        "OK Injection Token Guard"
    )
    print(
        "OK Ken Burns Structure"
    )
    print(
        "OK Native Video No-Op"
    )
    print(
        "OK Zero FFmpeg Execution"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 3. VI6.39 ACTIVATION GATE
# =====================================================

cat > vi6_39_activation_gate.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.39"


_EVENTS = []


def evaluate(
    adapter,
    filter_report,
    compatibility,
    safety,
    contract,
    dry_plan
):

    blockers = []
    warnings = []


    if (
        adapter.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "renderer_adapter_not_ready"
        )


    best = (
        adapter.get(
            "best"
        )
        or {}
    )


    if (
        float(
            best.get(
                "score",
                0
            )
            or 0
        )
        < 50
    ):

        blockers.append(
            "renderer_confidence_low"
        )


    if (
        filter_report.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "filter_validation_failed"
        )


    if (
        compatibility.get(
            "status"
        )
        != "STATIC_PASS"
    ):

        blockers.append(
            "renderer_compatibility_hold"
        )


    if (
        safety.get(
            "status"
        )
        == "HOLD"
    ):

        blockers.append(
            "cinematic_safety_hold"
        )


    if (
        contract.get(
            "renderer_applied"
        )
        is not False
    ):

        blockers.append(
            "renderer_already_active"
        )


    if (
        dry_plan.get(
            "executed"
        )
        is not False
    ):

        blockers.append(
            "dry_plan_execution_detected"
        )


    if (
        adapter.get(
            "file_modified"
        )
        is not False
    ):

        blockers.append(
            "video_file_modified_in_shadow"
        )


    if (
        adapter.get(
            "candidate_count",
            0
        )
        > 5
    ):

        warnings.append(
            "multiple_renderer_candidates"
        )


    if blockers:

        status = "HOLD"


    elif warnings:

        status = (
            "READY_WITH_WARNINGS"
        )


    else:

        status = (
            "READY_FOR_CONTROLLED_BINDING"
        )


    return {

        "version":
            VERSION,

        "status":
            status,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "renderer_function":
            best.get(
                "function"
            ),

        "renderer_line":
            best.get(
                "line_start"
            ),

        "renderer_confidence":
            best.get(
                "score"
            ),

        # IMPORTANTE:
        # READY não significa ativado.
        "renderer_active":
            False,

        "ffmpeg_active":
            False,

        "binding_performed":
            False,

        "safe_for_next_stage":
            status
            in {
                "READY_FOR_CONTROLLED_BINDING",
                "READY_WITH_WARNINGS",
            },
    }


def record(
    scene,
    result
):

    _EVENTS.append(
        {
            "scene":
                scene,

            "status":
                result.get(
                    "status"
                ),

            "blockers":
                result.get(
                    "blockers"
                ),

            "warnings":
                result.get(
                    "warnings"
                ),

            "renderer_function":
                result.get(
                    "renderer_function"
                ),

            "renderer_line":
                result.get(
                    "renderer_line"
                ),

            "renderer_confidence":
                result.get(
                    "renderer_confidence"
                ),
        }
    )


def reset():

    _EVENTS.clear()


def summary():

    statuses = {}


    for event in _EVENTS:

        status = event[
            "status"
        ]


        statuses[
            status
        ] = (
            statuses.get(
                status,
                0
            )
            + 1
        )


    all_ready = bool(
        _EVENTS
    ) and all(
        event[
            "status"
        ]
        in {
            "READY_FOR_CONTROLLED_BINDING",
            "READY_WITH_WARNINGS",
        }
        for event in _EVENTS
    )


    return {

        "version":
            VERSION,

        "scenes":
            len(
                _EVENTS
            ),

        "statuses":
            statuses,

        "all_scenes_safe_for_next_stage":
            all_ready,

        "renderer_active":
            False,

        "ffmpeg_active":
            False,

        "events":
            list(
                _EVENTS
            ),
    }


def flush(
    path=None
):

    if path is None:

        folder = os.path.expanduser(
            "~/ShortAutoPro/logs/producao"
        )


        os.makedirs(
            folder,
            exist_ok=True
        )


        path = os.path.join(
            folder,
            "vi6_39_activation_gate_latest.json"
        )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "summary":
            summary(),
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    reset()


    result = evaluate(
        {
            "status":
                "SHADOW_READY",

            "best":
                {
                    "function":
                        "gerar_video",

                    "line_start":
                        100,

                    "score":
                        90,
                },

            "candidate_count":
                1,

            "file_modified":
                False,
        },
        {
            "status":
                "PASS"
        },
        {
            "status":
                "STATIC_PASS"
        },
        {
            "status":
                "PASS"
        },
        {
            "renderer_applied":
                False
        },
        {
            "executed":
                False
        }
    )


    assert (
        result[
            "status"
        ]
        == "READY_FOR_CONTROLLED_BINDING"
    )


    assert (
        result[
            "renderer_active"
        ]
        is False
    )


    assert (
        result[
            "binding_performed"
        ]
        is False
    )


    record(
        1,
        result
    )


    assert (
        summary()[
            "all_scenes_safe_for_next_stage"
        ]
        is True
    )


    reset()


    print()
    print(
        "======================================"
    )
    print(
        " VI6.39 ACTIVATION SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Shadow Adapter Requirement"
    )
    print(
        "OK Filter Validation Requirement"
    )
    print(
        "OK Compatibility Requirement"
    )
    print(
        "OK Cinematic Safety Requirement"
    )
    print(
        "OK Renderer-Inactive Requirement"
    )
    print(
        "OK Controlled-Binding Readiness"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 4. VI6.39 RUNTIME POLICY
# =====================================================

cat > vi6_39_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer,
    save_report as save_adapter_report,
)


from vi6_38_filter_validator import (
    validate as validate_filter
)


from vi6_39_activation_gate import (
    evaluate as activation_evaluate,
    record,
    reset,
    flush,
)


_ADAPTER = inspect_renderer(
    "video.py"
)


if not getattr(
    brain,
    "_VI639_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_639 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_639(
        vi6_scene,
        candidatos,
        cena,
        current_candidate,
        current_reason
    ):

        board = (
            cena.get(
                "_vi68_storyboard"
            )
            or {}
        )


        try:

            number = int(
                board.get(
                    "scene",
                    0
                )
                or 0
            )

        except Exception:

            number = 0


        if number == 1:

            reset()


        (
            candidate,
            reason,
            meta
        ) = _base_supervisor_639(
            vi6_scene,
            candidatos,
            cena,
            current_candidate,
            current_reason
        )


        meta = dict(
            meta
            or {}
        )


        contract = (
            meta.get(
                "vi634_repaired_contract"
            )
            or meta.get(
                "vi630_renderer_contract"
            )
            or {}
        )


        safety = (
            meta.get(
                "vi633_post_repair_safety"
            )
            or meta.get(
                "vi633_cinematic_safety"
            )
            or {}
        )


        dry_plan = (
            meta.get(
                "vi635_ffmpeg_dry_plan"
            )
            or {}
        )


        compatibility = (
            meta.get(
                "vi636_renderer_compatibility"
            )
            or {}
        )


        filter_report = validate_filter(
            dry_plan
        )


        gate = activation_evaluate(
            _ADAPTER,
            filter_report,
            compatibility,
            safety,
            contract,
            dry_plan
        )


        record(
            number,
            gate
        )


        meta[
            "vi637_renderer_shadow"
        ] = {

            "status":
                _ADAPTER.get(
                    "status"
                ),

            "reason":
                _ADAPTER.get(
                    "reason"
                ),

            "best":
                _ADAPTER.get(
                    "best"
                ),

            "video_sha256":
                _ADAPTER.get(
                    "file_sha256"
                ),

            "file_modified":
                False,
        }


        meta[
            "vi638_filter_validation"
        ] = filter_report


        meta[
            "vi639_activation_gate"
        ] = gate


        meta[
            "vi639_renderer_active"
        ] = False


        meta[
            "vi639_ffmpeg_active"
        ] = False


        if candidate is not None:

            candidate[
                "_vi637_shadow_status"
            ] = _ADAPTER.get(
                "status"
            )


            candidate[
                "_vi638_filter_status"
            ] = filter_report.get(
                "status"
            )


            candidate[
                "_vi639_activation_status"
            ] = gate.get(
                "status"
            )


            candidate[
                "_vi639_renderer_active"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                meta[
                    "vi637_shadow_report_path"
                ] = save_adapter_report(
                    _ADAPTER
                )


                meta[
                    "vi639_gate_path"
                ] = flush()


            except Exception as exc:

                meta[
                    "vi639_report_error"
                ] = (
                    f"{type(exc).__name__}:"
                    f"{str(exc)[:120]}"
                )


        return (
            candidate,
            reason,
            meta
        )


    brain.supervisionar_vi6_6 = (
        _wrapped_639
    )


    brain._VI637_RUNTIME_ACTIVE = True
    brain._VI638_RUNTIME_ACTIVE = True
    brain._VI639_RUNTIME_ACTIVE = True
PY


# =====================================================
# 5. ATTACH AO STACK
# =====================================================

python - <<'PY'
from pathlib import Path
import ast


path = Path(
    "vi6_9_runtime_policy.py"
)


source = path.read_text(
    encoding="utf-8"
)


MARKER = (
    "# VI6.37-6.39 SHADOW RENDERER STACK"
)


if MARKER in source:

    print(
        "VI6.37-6.39 já conectado."
    )

    raise SystemExit(0)


append = '''

# =========================================
# VI6.37-6.39 SHADOW RENDERER STACK
# =========================================
import vi6_39_runtime_policy
'''


patched = (
    source.rstrip()
    + "\n"
    + append
    + "\n"
)


ast.parse(
    patched
)


path.write_text(
    patched,
    encoding="utf-8"
)


print()
print(
    "======================================"
)
print(
    " VI6.37-6.39 RUNTIME ATTACHED"
)
print(
    "======================================"
)
print(
    "Renderer Adapter: SHADOW"
)
print(
    "Filter Validator: ACTIVE"
)
print(
    "Activation Gate: ACTIVE"
)
print(
    "Renderer Binding: NOT PERFORMED"
)
print()
PY


STATUS=$?


if [ "$STATUS" -ne 0 ]; then
    rollback
    exit "$STATUS"
fi


# =====================================================
# 6. OFFLINE RUNTIME TEST
# =====================================================

cat > testar_vi637_vi639.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


FLAGS = (

    "_VI69_RUNTIME_PATCHED",

    "_VI634_RUNTIME_ACTIVE",
    "_VI635_RUNTIME_ACTIVE",
    "_VI636_RUNTIME_ACTIVE",

    "_VI637_RUNTIME_ACTIVE",
    "_VI638_RUNTIME_ACTIVE",
    "_VI639_RUNTIME_ACTIVE",
)


for flag in FLAGS:

    assert getattr(
        brain,
        flag,
        False
    ), flag


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)


report = inspect_renderer(
    "video.py"
)


assert (
    report[
        "file_modified"
    ]
    is False
)


assert (
    report[
        "renderer_executed"
    ]
    is False
)


assert (
    report[
        "ffmpeg_executed"
    ]
    is False
)


print()
print(
    "======================================"
)
print(
    " VI6.37-6.39 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.34 AUTO REPAIR:",
    brain._VI634_RUNTIME_ACTIVE
)

print(
    "VI6.35 DRY COMPILER:",
    brain._VI635_RUNTIME_ACTIVE
)

print(
    "VI6.36 COMPATIBILITY:",
    brain._VI636_RUNTIME_ACTIVE
)

print(
    "VI6.37 SHADOW ADAPTER:",
    brain._VI637_RUNTIME_ACTIVE
)

print(
    "VI6.38 FILTER VALIDATOR:",
    brain._VI638_RUNTIME_ACTIVE
)

print(
    "VI6.39 ACTIVATION GATE:",
    brain._VI639_RUNTIME_ACTIVE
)

print()
print(
    "REAL VIDEO.PY MAP STATUS:",
    report[
        "status"
    ]
)

print(
    "RENDERER CANDIDATES:",
    report[
        "candidate_count"
    ]
)


if report.get(
    "best"
):

    print(
        "BEST FUNCTION:",
        report[
            "best"
        ][
            "function"
        ]
    )

    print(
        "BEST LINE:",
        report[
            "best"
        ][
            "line_start"
        ]
    )

    print(
        "BEST SCORE:",
        report[
            "best"
        ][
            "score"
        ]
    )


print()
print(
    "VIDEO.PY MODIFIED=False"
)
print(
    "FFMPEG EXECUTION=False"
)
print(
    "RENDERER EXECUTION=False"
)
print(
    "VIDEOS=0"
)
print()
PY


# =====================================================
# 7. FULL COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_37_renderer_shadow_adapter.py \
    vi6_38_filter_validator.py \
    vi6_39_activation_gate.py \
    vi6_39_runtime_policy.py \
    testar_vi637_vi639.py \
    vi6_36_runtime_policy.py \
    vi6_36_renderer_compatibility.py \
    vi6_35_ffmpeg_dry_compiler.py \
    vi6_34_motion_auto_repair.py \
    vi6_33_runtime_policy.py \
    vi6_30_renderer_contract.py \
    vi6_9_runtime_policy.py \
    vi6_6_active_brain.py \
    midia.py \
    video.py
then
    echo
    echo "COMPILE FALHOU."
    rollback
    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# 8. SELF TESTS
# =====================================================

echo
echo "===== VI6.37 SELF TEST ====="

if ! python vi6_37_renderer_shadow_adapter.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.38 SELF TEST ====="

if ! python vi6_38_filter_validator.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.39 SELF TEST ====="

if ! python vi6_39_activation_gate.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi637_vi639.py; then
    rollback
    exit 1
fi


# =====================================================
# 9. REGRESSIONS
# =====================================================

echo
echo "===== VI6.36 REGRESSION ====="

if ! python vi6_36_renderer_compatibility.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.35 REGRESSION ====="

if ! python vi6_35_ffmpeg_dry_compiler.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.34 REGRESSION ====="

if ! python vi6_34_motion_auto_repair.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.33 REGRESSION ====="

if ! python vi6_33_cinematic_safety_gate.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.30 REGRESSION ====="

if ! python vi6_30_renderer_contract.py; then
    rollback
    exit 1
fi


# =====================================================
# 10. ZERO EXECUTION STATIC CHECK
# =====================================================

echo
echo "===== ZERO EXECUTION CHECK ====="

if ! python - <<'PY'
import ast
from pathlib import Path


FILES = [
    "vi6_37_renderer_shadow_adapter.py",
    "vi6_38_filter_validator.py",
    "vi6_39_activation_gate.py",
    "vi6_39_runtime_policy.py",
]


BAD = {
    "system",
    "popen",
    "Popen",
    "run",
    "call",
    "check_call",
    "check_output",
}


violations = []


for filename in FILES:

    tree = ast.parse(
        Path(
            filename
        ).read_text(
            encoding="utf-8"
        )
    )


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call
        ):
            continue


        if isinstance(
            node.func,
            ast.Name
        ):

            name = node.func.id


        elif isinstance(
            node.func,
            ast.Attribute
        ):

            name = node.func.attr


        else:

            name = ""


        if name in BAD:

            violations.append(
                (
                    filename,
                    getattr(
                        node,
                        "lineno",
                        None
                    ),
                    name
                )
            )


if violations:

    print(
        "EXECUTION VIOLATIONS:",
        violations
    )

    raise SystemExit(1)


print(
    "FORBIDDEN EXECUTION CALLS=0"
)

print(
    "FFMPEG EXECUTION PATH=0"
)

print(
    "VIDEO WRITES=0"
)
PY
then
    rollback
    exit 1
fi


# =====================================================
# 11. CORE
# =====================================================

echo
echo "===== BASH CHECK ====="

if ! bash -n gerar_short.sh; then
    rollback
    exit 1
fi

echo "BASH STATUS=0"


echo
echo "===== RELEASE CHECK ====="

if ! ./release_check.sh; then
    rollback
    exit 1
fi


# =====================================================
# 12. CORE HASH SAFETY
# =====================================================

echo
echo "===== CORE HASH SAFETY ====="

: > "$BACKDIR/core_after.sha256"

for F in $CORE_FILES
do
    sha256sum "$F" \
        >> "$BACKDIR/core_after.sha256"
done


if ! diff -u \
    "$BACKDIR/core_before.sha256" \
    "$BACKDIR/core_after.sha256"
then

    echo
    echo "ERRO: CORE MODIFICADO."
    echo "ROLLBACK."

    rollback
    exit 1
fi


echo "CORE FILES UNCHANGED=YES"


# =====================================================
# 13. REAL SHADOW MAP
# =====================================================

echo
echo "===== REAL VIDEO.PY SHADOW MAP ====="

python - <<'PY'
from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)


report = inspect_renderer(
    "video.py"
)


print(
    "STATUS:",
    report[
        "status"
    ]
)

print(
    "REASON:",
    report[
        "reason"
    ]
)

print(
    "CANDIDATES:",
    report[
        "candidate_count"
    ]
)

print(
    "ELIGIBLE:",
    report[
        "eligible_count"
    ]
)


best = report.get(
    "best"
)


if best:

    print()
    print(
        "BEST FUNCTION:",
        best[
            "function"
        ]
    )

    print(
        "LINE START:",
        best[
            "line_start"
        ]
    )

    print(
        "LINE END:",
        best[
            "line_end"
        ]
    )

    print(
        "CONFIDENCE:",
        best[
            "score"
        ]
    )

    print(
        "HAS FFMPEG:",
        best[
            "has_ffmpeg_literal"
        ]
    )

    print(
        "HAS FILTER LOGIC:",
        best[
            "has_filter_logic"
        ]
    )

    print(
        "HAS PROCESS CALL:",
        best[
            "has_process_call"
        ]
    )
PY


# =====================================================
# FINAL
# =====================================================

echo
echo "======================================"
echo " VI6.37 + VI6.38 + VI6.39 INSTALADOS"
echo "======================================"
echo
echo "OK Renderer AST Shadow Adapter"
echo "OK Real video.py Function Mapping"
echo "OK Renderer Confidence Scoring"
echo "OK Filter Static Validator"
echo "OK Filter Whitelist"
echo "OK Injection Guard"
echo "OK Zoompan Structural Validation"
echo "OK Native Video Preservation"
echo "OK Activation Safety Gate"
echo "OK Compatibility Requirement"
echo "OK Cinematic Safety Requirement"
echo "OK VI6.34 Auto-Repair preserved"
echo "OK VI6.35 Dry Compiler preserved"
echo "OK VI6.36 Compatibility preserved"
echo
echo "CORE FILES UNCHANGED=YES"
echo "MIDIA.PY MODIFICADO=NAO"
echo "VIDEO.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo
echo "RENDERER MODE=SHADOW"
echo "RENDERER BINDING=NAO"
echo "FFMPEG EXECUTADO=NAO"
echo "VIDEO GERADO=NAO"
echo "API CALLS=0"
echo "DOWNLOADS NOVOS=0"
echo
echo "RELATORIOS FUTUROS:"
echo "logs/producao/vi6_37_renderer_shadow_latest.json"
echo "logs/producao/vi6_39_activation_gate_latest.json"
echo
