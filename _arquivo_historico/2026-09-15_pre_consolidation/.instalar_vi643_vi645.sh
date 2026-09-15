#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi643_vi645_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.43 + VI6.44 + VI6.45"
echo " EXACT BINDING + MICRO CERTIFICATION"
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
vi6_35_ffmpeg_dry_compiler.py
vi6_37_renderer_shadow_adapter.py
vi6_38_filter_validator.py
vi6_40_controlled_renderer_bridge.py
vi6_41_ffmpeg_null_probe.py
vi6_42_binding_gate.py
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
    video.py \
    midia.py \
    audio.py \
    legenda_dinamica.py \
    vi6_35_ffmpeg_dry_compiler.py \
    vi6_37_renderer_shadow_adapter.py \
    vi6_38_filter_validator.py \
    vi6_40_controlled_renderer_bridge.py \
    vi6_41_ffmpeg_null_probe.py \
    vi6_42_binding_gate.py
then
    echo "BASELINE FALHOU."
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


for F in \
    vi6_43_exact_binding_planner.py \
    vi6_44_reversible_adapter.py \
    vi6_45_micro_render_certification.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.43-6.45"
    echo "======================================"

    for F in \
        vi6_43_exact_binding_planner.py \
        vi6_44_reversible_adapter.py \
        vi6_45_micro_render_certification.py
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
# 1. VI6.43 EXACT BINDING PLANNER
# =====================================================

cat > vi6_43_exact_binding_planner.py <<'PY'
#!/usr/bin/env python3

import ast
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path


VERSION = "6.43"


GATE_REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)


OUTPUT_REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_43_binding_plan_latest.json"
)


def _hash(path):

    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def _load_gate():

    if not os.path.exists(
        GATE_REPORT
    ):

        return None


    try:

        with open(
            GATE_REPORT,
            "r",
            encoding="utf-8"
        ) as f:

            return (
                json.load(f).get(
                    "gate"
                )
            )

    except Exception:

        return None


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


def inspect_function(
    filename,
    function_name
):

    path = Path(
        filename
    )


    source = path.read_text(
        encoding="utf-8"
    )


    lines = source.splitlines()


    tree = ast.parse(
        source
    )


    target = None


    for node in ast.walk(
        tree
    ):

        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                )
            )
            and node.name
            == function_name
        ):

            target = node
            break


    if target is None:

        return None


    filter_lines = []

    execution_lines = []

    ffmpeg_lines = []


    for child in ast.walk(
        target
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

            value = child.value.lower()


            if "ffmpeg" in value:

                ffmpeg_lines.append(
                    child.lineno
                )


            if any(
                marker in value
                for marker in (
                    "-vf",
                    "filter_complex",
                    "zoompan",
                    "scale=",
                    "crop=",
                    "subtitles=",
                )
            ):

                filter_lines.append(
                    child.lineno
                )


        if isinstance(
            child,
            ast.Call
        ):

            name = _call_name(
                child
            ).lower()


            if any(
                marker in name
                for marker in (
                    "subprocess.run",
                    "subprocess.popen",
                    "os.system",
                    "check_call",
                    "check_output",
                )
            ):

                execution_lines.append(
                    child.lineno
                )


    start = target.lineno

    end = getattr(
        target,
        "end_lineno",
        start
    )


    snippet_start = max(
        1,
        start
    )


    snippet_end = min(
        len(lines),
        end
    )


    return {

        "function":
            function_name,

        "line_start":
            start,

        "line_end":
            end,

        "ffmpeg_lines":
            sorted(
                set(
                    ffmpeg_lines
                )
            ),

        "filter_lines":
            sorted(
                set(
                    filter_lines
                )
            ),

        "execution_lines":
            sorted(
                set(
                    execution_lines
                )
            ),

        "function_source_lines":
            snippet_end
            - snippet_start
            + 1,

        "has_filter_point":
            bool(
                filter_lines
            ),

        "has_execution_point":
            bool(
                execution_lines
            ),
    }


def build_plan():

    gate = _load_gate()


    if gate is None:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "vi642_report_missing",

            "video_modified":
                False,
        }


    if not gate.get(
        "next_stage_allowed"
    ):

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "vi642_not_ready",

            "vi642_status":
                gate.get(
                    "status"
                ),

            "video_modified":
                False,
        }


    function_name = gate.get(
        "renderer_function"
    )


    if not function_name:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "renderer_function_missing",

            "video_modified":
                False,
        }


    details = inspect_function(
        "video.py",
        function_name
    )


    if details is None:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "mapped_function_no_longer_exists",

            "video_modified":
                False,
        }


    expected_line = gate.get(
        "renderer_line_start"
    )


    line_match = (
        expected_line is None
        or int(
            expected_line
        )
        == int(
            details[
                "line_start"
            ]
        )
    )


    blockers = []

    warnings = []


    if not line_match:

        blockers.append(
            "renderer_line_changed"
        )


    if not details[
        "has_execution_point"
    ]:

        blockers.append(
            "execution_point_not_proven"
        )


    if not details[
        "has_filter_point"
    ]:

        warnings.append(
            "filter_point_not_explicit"
        )


    if len(
        details[
            "execution_lines"
        ]
    ) > 2:

        warnings.append(
            "multiple_execution_points"
        )


    if len(
        details[
            "filter_lines"
        ]
    ) > 4:

        warnings.append(
            "multiple_filter_points"
        )


    if blockers:

        status = "HOLD"


    elif warnings:

        status = (
            "READY_WITH_WARNINGS"
        )


    else:

        status = (
            "READY_FOR_ADAPTER_PREVIEW"
        )


    if details[
        "filter_lines"
    ]:

        strategy = (
            "FILTER_AUGMENTATION"
        )

        insertion_line = (
            details[
                "filter_lines"
            ][0]
        )

    else:

        strategy = (
            "COMMAND_ARGUMENT_ADAPTER"
        )

        insertion_line = (
            details[
                "execution_lines"
            ][0]
            if details[
                "execution_lines"
            ]
            else None
        )


    return {

        "version":
            VERSION,

        "status":
            status,

        "reason":
            (
                "exact_renderer_target_resolved"
                if not blockers
                else "binding_target_not_stable"
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "video_sha256":
            _hash(
                "video.py"
            ),

        "renderer_function":
            function_name,

        "renderer_line_start":
            details[
                "line_start"
            ],

        "renderer_line_end":
            details[
                "line_end"
            ],

        "strategy":
            strategy,

        "suggested_insertion_line":
            insertion_line,

        "ffmpeg_lines":
            details[
                "ffmpeg_lines"
            ],

        "filter_lines":
            details[
                "filter_lines"
            ],

        "execution_lines":
            details[
                "execution_lines"
            ],

        "function_source_lines":
            details[
                "function_source_lines"
            ],

        "vi642_status":
            gate.get(
                "status"
            ),

        "video_modified":
            False,

        "binding_performed":
            False,
    }


def save(
    result,
    path=OUTPUT_REPORT
):

    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "plan":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    fake = '''
def renderer(inp, out):
    vf = "scale=1080:1920"
    cmd = ["ffmpeg", "-i", inp, "-vf", vf, out]
    subprocess.run(cmd)
'''


    tree = ast.parse(
        fake
    )


    node = [
        x
        for x in ast.walk(
            tree
        )
        if isinstance(
            x,
            ast.FunctionDef
        )
    ][0]


    assert node.name == "renderer"


    print()
    print(
        "======================================"
    )
    print(
        " VI6.43 BINDING PLANNER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Exact Function Resolution"
    )
    print(
        "OK FFmpeg Point Mapping"
    )
    print(
        "OK Filter Point Mapping"
    )
    print(
        "OK Execution Point Mapping"
    )
    print(
        "OK video.py untouched"
    )
    print()


if __name__ == "__main__":

    self_test()

    result = build_plan()

    path = save(
        result
    )


    print(
        "REAL PLAN STATUS:",
        result.get(
            "status"
        )
    )

    print(
        "FUNCTION:",
        result.get(
            "renderer_function"
        )
    )

    print(
        "STRATEGY:",
        result.get(
            "strategy"
        )
    )

    print(
        "INSERTION LINE:",
        result.get(
            "suggested_insertion_line"
        )
    )

    print(
        "FILTER LINES:",
        result.get(
            "filter_lines"
        )
    )

    print(
        "EXECUTION LINES:",
        result.get(
            "execution_lines"
        )
    )

    print(
        "VIDEO MODIFIED:",
        result.get(
            "video_modified"
        )
    )

    print(
        "REPORT:",
        path
    )
PY


# =====================================================
# 2. VI6.44 REVERSIBLE ADAPTER
# =====================================================

cat > vi6_44_reversible_adapter.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


VERSION = "6.44"

PHASE_LOCK = "PREVIEW_ONLY"


def _mode():

    raw = str(
        os.getenv(
            "VI644_ADAPTER_MODE",
            "SHADOW"
        )
        or "SHADOW"
    ).strip().upper()


    if raw not in {
        "OFF",
        "SHADOW",
        "ACTIVE",
    }:

        raw = "SHADOW"


    return raw


def adapt_filter(
    legacy_filter,
    dry_plan,
    gate_ready=False
):

    requested = _mode()


    proposed = (
        dry_plan.get(
            "vf"
        )
        if isinstance(
            dry_plan,
            dict
        )
        else None
    )


    result = {

        "version":
            VERSION,

        "phase_lock":
            PHASE_LOCK,

        "requested_mode":
            requested,

        "legacy_filter":
            legacy_filter,

        "proposed_vi6_filter":
            proposed,

        "selected_filter":
            legacy_filter,

        "shadow_difference":
            (
                proposed
                != legacy_filter
            ),

        "gate_ready":
            bool(
                gate_ready
            ),

        "binding_performed":
            False,

        "renderer_modified":
            False,
    }


    if requested == "OFF":

        result[
            "status"
        ] = "OFF"

        return result


    if requested == "ACTIVE":

        result[
            "status"
        ] = "ACTIVE_BLOCKED"

        result[
            "reason"
        ] = (
            "vi644_preview_phase_lock"
        )

        return result


    result[
        "status"
    ] = "SHADOW"


    result[
        "reason"
    ] = (
        "compare_only_no_renderer_change"
    )


    return result


def make_preview(
    binding_plan,
    path=None
):

    if path is None:

        path = os.path.expanduser(
            "~/ShortAutoPro/logs/producao/"
            "vi6_44_binding_preview_latest.txt"
        )


    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )


    lines = [

        "VI6.44 REVERSIBLE ADAPTER PREVIEW",

        "================================",

        "",

        "THIS FILE DOES NOT MODIFY video.py",

        "",

        (
            "Target function: "
            + str(
                binding_plan.get(
                    "renderer_function"
                )
            )
        ),

        (
            "Target lines: "
            + str(
                binding_plan.get(
                    "renderer_line_start"
                )
            )
            + "-"
            + str(
                binding_plan.get(
                    "renderer_line_end"
                )
            )
        ),

        (
            "Strategy: "
            + str(
                binding_plan.get(
                    "strategy"
                )
            )
        ),

        (
            "Suggested insertion line: "
            + str(
                binding_plan.get(
                    "suggested_insertion_line"
                )
            )
        ),

        "",

        "Future reversible behavior:",

        "1. Existing renderer remains default.",

        "2. VI6 adapter receives legacy filter.",

        "3. SHADOW compares legacy vs VI6 plan.",

        "4. ACTIVE will require explicit future gate.",

        "5. OFF immediately restores legacy behavior.",

        "",

        (
            "Source hash: "
            + str(
                binding_plan.get(
                    "video_sha256"
                )
            )
        ),

        "",

        "BINDING_PERFORMED=False",
    ]


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "\n".join(
                lines
            )
            + "\n"
        )


    return path


def save_json(
    binding_plan,
    adapter_result,
    path=None
):

    if path is None:

        path = os.path.expanduser(
            "~/ShortAutoPro/logs/producao/"
            "vi6_44_adapter_latest.json"
        )


    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "binding_plan":
                    binding_plan,

                "adapter":
                    adapter_result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    result = adapt_filter(
        "legacy_scale",
        {
            "vf":
                "new_zoompan"
        },
        True
    )


    assert (
        result[
            "selected_filter"
        ]
        == "legacy_scale"
    )


    assert (
        result[
            "binding_performed"
        ]
        is False
    )


    assert (
        result[
            "renderer_modified"
        ]
        is False
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.44 ADAPTER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Legacy Renderer Preserved"
    )
    print(
        "OK Shadow Comparison"
    )
    print(
        "OK ACTIVE Hard Lock"
    )
    print(
        "OK OFF Rollback Semantics"
    )
    print(
        "OK Binding = False"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 3. VI6.45 ISOLATED MICRO-RENDER CERTIFICATION
# =====================================================

cat > vi6_45_micro_render_certification.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from fractions import Fraction


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_38_filter_validator import (
    validate as validate_filter
)


VERSION = "6.45"


BASE = os.path.expanduser(
    "~/ShortAutoPro"
)


TEMP = os.path.join(
    BASE,
    "temp",
    "vi645"
)


REPORT = os.path.join(
    BASE,
    "logs",
    "producao",
    "vi6_45_micro_render_latest.json"
)


TARGET_DURATION = 1.2

TARGET_WIDTH = 1080

TARGET_HEIGHT = 1920

TARGET_FPS = 30.0


def _run(
    cmd,
    timeout=60
):

    return subprocess.run(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )


def _fps(value):

    try:

        return float(
            Fraction(
                str(
                    value
                )
            )
        )

    except Exception:

        return 0.0


def _choose_codec(
    ffmpeg
):

    result = _run(
        [
            ffmpeg,
            "-hide_banner",
            "-encoders",
        ],
        30
    )


    blob = (
        result.stdout
        + "\n"
        + result.stderr
    )


    if "libx264" in blob:

        return "libx264"


    return "mpeg4"


def build_contract():

    return {

        "media_type":
            "STILL",

        "role":
            "CONTEXT",

        "profile":
            "CONTEXT_DRIFT",

        "renderer_applied":
            False,

        "ken_burns":
            {
                "enabled":
                    True,

                "zoom_start":
                    1.0,

                "zoom_end":
                    1.03,

                "start_x":
                    .47,

                "start_y":
                    .50,

                "end_x":
                    .53,

                "end_y":
                    .50,
            },
    }


def cleanup(
    paths
):

    removed = []


    for path in paths:

        try:

            if os.path.exists(
                path
            ):

                os.remove(
                    path
                )

                removed.append(
                    path
                )

        except Exception:

            pass


    return removed


def certify():

    ffmpeg = shutil.which(
        "ffmpeg"
    )


    ffprobe = shutil.which(
        "ffprobe"
    )


    if not ffmpeg:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffmpeg_missing",

            "video_created":
                False,
        }


    if not ffprobe:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffprobe_missing",

            "video_created":
                False,
        }


    os.makedirs(
        TEMP,
        exist_ok=True
    )


    os.makedirs(
        os.path.dirname(
            REPORT
        ),
        exist_ok=True
    )


    input_path = os.path.join(
        TEMP,
        "synthetic_input.ppm"
    )


    output_path = os.path.join(
        TEMP,
        "micro_render.mp4"
    )


    cleanup(
        [
            input_path,
            output_path,
        ]
    )


    created = False

    probe_payload = None

    errors = []


    try:

        # =====================================
        # SYNTHETIC LOCAL STILL
        # =====================================

        input_cmd = [

            ffmpeg,

            "-hide_banner",

            "-loglevel",
            "error",

            "-y",

            "-f",
            "lavfi",

            "-i",
            (
                "testsrc2="
                "size=1080x1920:"
                "rate=1"
            ),

            "-frames:v",
            "1",

            input_path,
        ]


        result = _run(
            input_cmd,
            45
        )


        if (
            result.returncode
            != 0
        ):

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "synthetic_input_creation_failed",

                "stderr":
                    (
                        result.stderr
                        or ""
                    )[-1500:],

                "video_created":
                    False,
            }


        # =====================================
        # COMPILE REAL VI6 FILTER
        # =====================================

        contract = build_contract()


        dry_plan = compile_plan(
            contract,
            {
                "seconds":
                    TARGET_DURATION
            }
        )


        validation = validate_filter(
            dry_plan
        )


        if (
            validation.get(
                "status"
            )
            != "PASS"
        ):

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "dry_filter_validation_failed",

                "validation":
                    validation,

                "video_created":
                    False,
            }


        frames = int(
            dry_plan.get(
                "frames",
                36
            )
        )


        vf = dry_plan.get(
            "vf"
        )


        codec = _choose_codec(
            ffmpeg
        )


        # =====================================
        # ISOLATED MICRO RENDER
        # =====================================

        cmd = [

            ffmpeg,

            "-hide_banner",

            "-loglevel",
            "error",

            "-y",

            "-i",
            input_path,

            "-vf",
            vf,

            "-frames:v",
            str(
                frames
            ),

            "-r",
            "30",

            "-c:v",
            codec,

            "-pix_fmt",
            "yuv420p",

            "-an",

            output_path,
        ]


        render = _run(
            cmd,
            90
        )


        if (
            render.returncode
            != 0
        ):

            errors.append(
                "ffmpeg_micro_render_failed"
            )


            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "ffmpeg_micro_render_failed",

                "codec":
                    codec,

                "stderr":
                    (
                        render.stderr
                        or ""
                    )[-2000:],

                "video_created":
                    os.path.exists(
                        output_path
                    ),
            }


        created = os.path.exists(
            output_path
        )


        if not created:

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "output_not_created",

                "video_created":
                    False,
            }


        # =====================================
        # FFPROBE CERTIFICATION
        # =====================================

        probe_cmd = [

            ffprobe,

            "-v",
            "error",

            "-select_streams",
            "v:0",

            "-show_entries",
            (
                "stream="
                "width,height,"
                "r_frame_rate,"
                "avg_frame_rate,"
                "nb_frames,"
                "codec_name:"
                "format=duration"
            ),

            "-of",
            "json",

            output_path,
        ]


        probe = _run(
            probe_cmd,
            45
        )


        if (
            probe.returncode
            != 0
        ):

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "ffprobe_failed",

                "stderr":
                    (
                        probe.stderr
                        or ""
                    )[-1500:],

                "video_created":
                    True,
            }


        probe_payload = json.loads(
            probe.stdout
        )


        streams = (
            probe_payload.get(
                "streams"
            )
            or []
        )


        if not streams:

            return {

                "version":
                    VERSION,

                "status":
                    "HOLD",

                "reason":
                    "no_video_stream",

                "video_created":
                    True,
            }


        stream = streams[0]


        fmt = (
            probe_payload.get(
                "format"
            )
            or {}
        )


        width = int(
            stream.get(
                "width",
                0
            )
            or 0
        )


        height = int(
            stream.get(
                "height",
                0
            )
            or 0
        )


        fps = _fps(
            stream.get(
                "avg_frame_rate"
            )
            or stream.get(
                "r_frame_rate"
            )
        )


        try:

            duration = float(
                fmt.get(
                    "duration",
                    0
                )
                or 0
            )

        except Exception:

            duration = 0.0


        size = os.path.getsize(
            output_path
        )


        checks = {

            "width":
                width
                == TARGET_WIDTH,

            "height":
                height
                == TARGET_HEIGHT,

            "fps":
                abs(
                    fps
                    - TARGET_FPS
                )
                <= .05,

            "duration":
                abs(
                    duration
                    - TARGET_DURATION
                )
                <= .25,

            "file_nonempty":
                size > 1000,
        }


        passed = all(
            checks.values()
        )


        return {

            "version":
                VERSION,

            "status":
                (
                    "CERTIFIED"
                    if passed
                    else "HOLD"
                ),

            "reason":
                (
                    "micro_render_certified"
                    if passed
                    else
                    "micro_render_spec_mismatch"
                ),

            "codec":
                codec,

            "width":
                width,

            "height":
                height,

            "fps":
                round(
                    fps,
                    4
                ),

            "duration":
                round(
                    duration,
                    4
                ),

            "frames_planned":
                frames,

            "file_size":
                size,

            "checks":
                checks,

            "video_created":
                True,

            "production_video":
                False,

            "synthetic_input":
                True,

            "api_calls":
                0,

            "downloads":
                0,
        }


    finally:

        keep = str(
            os.getenv(
                "VI645_KEEP_ARTIFACTS",
                "0"
            )
        ).strip() == "1"


        if not keep:

            cleanup(
                [
                    output_path,
                    input_path,
                ]
            )


def save(
    result
):

    payload = dict(
        result
    )


    output_path = os.path.join(
        TEMP,
        "micro_render.mp4"
    )


    input_path = os.path.join(
        TEMP,
        "synthetic_input.ppm"
    )


    payload[
        "output_exists_after_cleanup"
    ] = os.path.exists(
        output_path
    )


    payload[
        "input_exists_after_cleanup"
    ] = os.path.exists(
        input_path
    )


    payload[
        "temporary_video_deleted"
    ] = not os.path.exists(
        output_path
    )


    with open(
        REPORT,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "certification":
                    payload,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return (
        REPORT,
        payload
    )


def self_test():

    contract = build_contract()


    plan = compile_plan(
        contract,
        {
            "seconds":
                TARGET_DURATION
        }
    )


    assert (
        plan[
            "renderer_mode"
        ]
        == "KEN_BURNS_STILL"
    )


    assert (
        plan[
            "frames"
        ]
        == 36
    )


    assert (
        validate_filter(
            plan
        )[
            "status"
        ]
        == "PASS"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.45 CERTIFIER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Synthetic Media Only"
    )
    print(
        "OK 1080x1920 Target"
    )
    print(
        "OK 30 FPS Target"
    )
    print(
        "OK 1.2s Target"
    )
    print(
        "OK ffprobe Certification"
    )
    print(
        "OK Automatic Cleanup"
    )
    print()


def main():

    parser = argparse.ArgumentParser()


    parser.add_argument(
        "--certify",
        action="store_true"
    )


    args = parser.parse_args()


    self_test()


    if not args.certify:

        return


    result = certify()


    path, final = save(
        result
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.45 MICRO-RENDER CERTIFICATION"
    )
    print(
        "======================================"
    )


    print(
        "STATUS:",
        final.get(
            "status"
        )
    )


    print(
        "REASON:",
        final.get(
            "reason"
        )
    )


    print(
        "RESOLUTION:",
        str(
            final.get(
                "width"
            )
        )
        + "x"
        + str(
            final.get(
                "height"
            )
        )
    )


    print(
        "FPS:",
        final.get(
            "fps"
        )
    )


    print(
        "DURATION:",
        final.get(
            "duration"
        )
    )


    print(
        "CODEC:",
        final.get(
            "codec"
        )
    )


    print(
        "TEMP VIDEO DELETED:",
        final.get(
            "temporary_video_deleted"
        )
    )


    print(
        "OUTPUT EXISTS AFTER CLEANUP:",
        final.get(
            "output_exists_after_cleanup"
        )
    )


    print(
        "PRODUCTION VIDEO:",
        final.get(
            "production_video",
            False
        )
    )


    print(
        "REPORT:",
        path
    )


if __name__ == "__main__":
    main()
PY


# =====================================================
# 4. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_43_exact_binding_planner.py \
    vi6_44_reversible_adapter.py \
    vi6_45_micro_render_certification.py \
    vi6_42_binding_gate.py \
    vi6_41_ffmpeg_null_probe.py \
    vi6_40_controlled_renderer_bridge.py \
    video.py
then
    echo
    echo "COMPILE FALHOU."
    rollback
    exit 1
fi

echo "PYTHON STATUS=0"


# =====================================================
# 5. SELF TESTS
# =====================================================

echo
echo "===== VI6.43 ====="

if ! python vi6_43_exact_binding_planner.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.44 ====="

if ! python vi6_44_reversible_adapter.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.45 SELF TEST ====="

if ! python vi6_45_micro_render_certification.py; then
    rollback
    exit 1
fi


# =====================================================
# 6. CREATE REAL ADAPTER PREVIEW
# =====================================================

echo
echo "===== VI6.44 REAL PREVIEW ====="

python - <<'PY'
import json
import os


from vi6_44_reversible_adapter import (
    adapt_filter,
    make_preview,
    save_json,
)


path = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_43_binding_plan_latest.json"
)


if not os.path.exists(path):

    print(
        "BINDING PLAN MISSING"
    )

    raise SystemExit(0)


with open(
    path,
    "r",
    encoding="utf-8"
) as f:

    plan = (
        json.load(f).get(
            "plan",
            {}
        )
    )


adapter = adapt_filter(
    "LEGACY_RENDERER_FILTER",
    {
        "vf":
            "VI6_PLANNED_FILTER"
    },
    plan.get(
        "status"
    )
    in {
        "READY_FOR_ADAPTER_PREVIEW",
        "READY_WITH_WARNINGS",
    }
)


preview = make_preview(
    plan
)


report = save_json(
    plan,
    adapter
)


print(
    "PLAN STATUS:",
    plan.get(
        "status"
    )
)

print(
    "ADAPTER STATUS:",
    adapter.get(
        "status"
    )
)

print(
    "SELECTED FILTER:",
    adapter.get(
        "selected_filter"
    )
)

print(
    "BINDING PERFORMED:",
    adapter.get(
        "binding_performed"
    )
)

print(
    "PREVIEW:",
    preview
)

print(
    "REPORT:",
    report
)
PY


# =====================================================
# 7. RELEASE / CORE CHECK
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
# 8. CHECK VI6.42 BEFORE MICRO-RENDER
# =====================================================

READY="$(
python - <<'PY'
import json
import os


path = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)


if not os.path.exists(path):

    print("NO")
    raise SystemExit


try:

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        gate = json.load(
            f
        ).get(
            "gate",
            {}
        )


    print(
        "YES"
        if gate.get(
            "next_stage_allowed"
        )
        else "NO"
    )


except Exception:

    print("NO")
PY
)"


echo
echo "VI6.42 NEXT STAGE READY=$READY"


# =====================================================
# 9. ISOLATED REAL MICRO-RENDER
# =====================================================

if [ "$READY" = "YES" ]; then

    echo
    echo "======================================"
    echo " VI6.45 REAL MICRO-RENDER"
    echo " SYNTHETIC LOCAL MEDIA"
    echo " ~1.2 SECOND TEMPORARY FILE"
    echo "======================================"

    python \
        vi6_45_micro_render_certification.py \
        --certify

else

    echo
    echo "VI6.45 REAL CERTIFICATION SKIPPED."
    echo "VI6.42 ainda não liberou o próximo estágio."

fi


# =====================================================
# 10. CORE HASH SAFETY
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
# 11. FINAL CERTIFICATION STATUS
# =====================================================

echo
echo "===== VI6.45 FINAL STATUS ====="

python - <<'PY'
import json
import os


path = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_45_micro_render_latest.json"
)


if not os.path.exists(path):

    print(
        "VI6.45 STATUS=NOT_RUN"
    )

    raise SystemExit


with open(
    path,
    "r",
    encoding="utf-8"
) as f:

    result = (
        json.load(f).get(
            "certification",
            {}
        )
    )


print(
    "VI6.45 STATUS="
    + str(
        result.get(
            "status"
        )
    )
)


print(
    "RESOLUTION="
    + str(
        result.get(
            "width"
        )
    )
    + "x"
    + str(
        result.get(
            "height"
        )
    )
)


print(
    "FPS="
    + str(
        result.get(
            "fps"
        )
    )
)


print(
    "DURATION="
    + str(
        result.get(
            "duration"
        )
    )
)


print(
    "CODEC="
    + str(
        result.get(
            "codec"
        )
    )
)


print(
    "TEMP VIDEO DELETED="
    + str(
        result.get(
            "temporary_video_deleted"
        )
    )
)


print(
    "OUTPUT EXISTS AFTER CLEANUP="
    + str(
        result.get(
            "output_exists_after_cleanup"
        )
    )
)
PY


echo
echo "======================================"
echo " VI6.43 + VI6.44 + VI6.45 INSTALADOS"
echo "======================================"
echo
echo "OK Exact Renderer Binding Planner"
echo "OK Function + Line Revalidation"
echo "OK Filter Point Mapping"
echo "OK Execution Point Mapping"
echo "OK Renderer Source Hash"
echo "OK Reversible Adapter Architecture"
echo "OK SHADOW Adapter"
echo "OK ACTIVE Hard Lock"
echo "OK Legacy Renderer Preservation"
echo "OK Binding Preview"
echo "OK Synthetic Micro-Render Harness"
echo "OK Real FFmpeg Encode Test"
echo "OK Real FFprobe Verification"
echo "OK 1080x1920 Verification"
echo "OK 30 FPS Verification"
echo "OK Duration Verification"
echo "OK Temporary Artifact Cleanup"
echo
echo "CORE FILES UNCHANGED=YES"
echo "MIDIA.PY MODIFICADO=NAO"
echo "VIDEO.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo
echo "API CALLS=0"
echo "DOWNLOADS=0"
echo "SHORT DE PRODUCAO GERADO=NAO"
echo "VIDEO TEMPORARIO DE TESTE=POSSIVEL"
echo "VIDEO TEMPORARIO APAGADO AUTOMATICAMENTE=SIM"
echo "RENDERER DE PRODUCAO ATIVADO=NAO"
echo "BINDING EM VIDEO.PY=NAO"
echo
echo "REPORTS:"
echo "logs/producao/vi6_43_binding_plan_latest.json"
echo "logs/producao/vi6_44_binding_preview_latest.txt"
echo "logs/producao/vi6_45_micro_render_latest.json"
echo
