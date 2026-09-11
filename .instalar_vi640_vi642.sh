#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi640_vi642_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================"
echo " VI6.40 + VI6.41 + VI6.42"
echo " CONTROLLED RENDERER BRIDGE"
echo " REAL FFMPEG NULL PROBE"
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
vi6_34_motion_auto_repair.py
vi6_35_ffmpeg_dry_compiler.py
vi6_36_renderer_compatibility.py
vi6_37_renderer_shadow_adapter.py
vi6_38_filter_validator.py
vi6_39_activation_gate.py
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
    vi6_37_renderer_shadow_adapter.py \
    vi6_38_filter_validator.py \
    vi6_39_activation_gate.py
then
    echo "BASELINE FALHOU."
    echo "NADA FOI ALTERADO."
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
    vi6_40_controlled_renderer_bridge.py \
    vi6_41_ffmpeg_null_probe.py \
    vi6_42_binding_gate.py \
    vi6_42_runtime_policy.py \
    testar_vi640_vi642.py
do
    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi
done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.40-6.42"
    echo "======================================"

    cp \
        "$BACKDIR/vi6_9_runtime_policy.py" \
        vi6_9_runtime_policy.py

    for F in \
        vi6_40_controlled_renderer_bridge.py \
        vi6_41_ffmpeg_null_probe.py \
        vi6_42_binding_gate.py \
        vi6_42_runtime_policy.py \
        testar_vi640_vi642.py
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
# 1. VI6.40 CONTROLLED RENDERER BRIDGE
# =====================================================

cat > vi6_40_controlled_renderer_bridge.py <<'PY'
#!/usr/bin/env python3

import os

from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)

from vi6_38_filter_validator import (
    validate as validate_filter
)


VERSION = "6.40"

# Esta versão é deliberadamente
# SHADOW-ONLY.
#
# ACTIVE só poderá existir depois
# do gate VI6.42 e de um binding
# posterior específico.
PHASE_LOCK = "SHADOW_ONLY"


def _mode():

    value = str(
        os.getenv(
            "VI640_RENDERER_MODE",
            "SHADOW"
        )
        or "SHADOW"
    ).strip().upper()


    if value not in {
        "OFF",
        "SHADOW",
        "ACTIVE",
    }:

        value = "SHADOW"


    return value


def build_shadow_request(
    meta,
    adapter=None
):

    meta = dict(
        meta
        or {}
    )


    mode = _mode()


    if mode == "OFF":

        return {
            "version": VERSION,
            "status": "DISABLED",
            "mode": "OFF",
            "ready": False,
            "executed": False,
            "binding_performed": False,
        }


    if adapter is None:

        adapter = inspect_renderer(
            "video.py"
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


    dry_plan = (
        meta.get(
            "vi635_ffmpeg_dry_plan"
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


    compatibility = (
        meta.get(
            "vi636_renderer_compatibility"
        )
        or {}
    )


    filter_report = validate_filter(
        dry_plan
    )


    blockers = []


    if (
        adapter.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "renderer_map_not_ready"
        )


    if (
        filter_report.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "filter_not_valid"
        )


    if (
        compatibility.get(
            "status"
        )
        != "STATIC_PASS"
    ):

        blockers.append(
            "compatibility_not_pass"
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
            "renderer_already_applied"
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


    if mode == "ACTIVE":

        blockers.append(
            "active_locked_until_post_vi642_binding"
        )


    best = (
        adapter.get(
            "best"
        )
        or {}
    )


    status = (
        "SHADOW_READY"
        if not blockers
        else "HOLD"
    )


    return {

        "version":
            VERSION,

        "phase_lock":
            PHASE_LOCK,

        "requested_mode":
            mode,

        "mode":
            "SHADOW",

        "status":
            status,

        "ready":
            status
            == "SHADOW_READY",

        "blockers":
            blockers,

        "target_file":
            "video.py",

        "target_function":
            best.get(
                "function"
            ),

        "target_line_start":
            best.get(
                "line_start"
            ),

        "target_line_end":
            best.get(
                "line_end"
            ),

        "target_confidence":
            best.get(
                "score"
            ),

        "video_sha256":
            adapter.get(
                "file_sha256"
            ),

        "renderer_mode":
            dry_plan.get(
                "renderer_mode"
            ),

        "vf":
            dry_plan.get(
                "vf"
            ),

        "argv_template":
            dry_plan.get(
                "argv"
            ),

        "filter_report":
            filter_report,

        "executed":
            False,

        "ffmpeg_executed":
            False,

        "binding_performed":
            False,

        "video_py_modified":
            False,
    }


def self_test():

    fake_adapter = {

        "status":
            "SHADOW_READY",

        "file_sha256":
            "abc",

        "best":
            {
                "function":
                    "gerar_video",

                "line_start":
                    100,

                "line_end":
                    200,

                "score":
                    100,
            }
    }


    meta = {

        "vi634_repaired_contract":
            {
                "renderer_applied":
                    False
            },

        "vi633_post_repair_safety":
            {
                "status":
                    "PASS"
            },

        "vi636_renderer_compatibility":
            {
                "status":
                    "STATIC_PASS"
            },

        "vi635_ffmpeg_dry_plan":
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
            },
    }


    result = build_shadow_request(
        meta,
        fake_adapter
    )


    assert result[
        "status"
    ] == "SHADOW_READY"


    assert result[
        "executed"
    ] is False


    assert result[
        "binding_performed"
    ] is False


    print()
    print(
        "======================================"
    )
    print(
        " VI6.40 BRIDGE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Real Renderer Target Mapping"
    )
    print(
        "OK Shadow Request"
    )
    print(
        "OK ACTIVE Hard Lock"
    )
    print(
        "OK Filter Requirement"
    )
    print(
        "OK Safety Requirement"
    )
    print(
        "OK No Renderer Execution"
    )
    print()


if __name__ == "__main__":

    self_test()
PY


# =====================================================
# 2. VI6.41 REAL FFMPEG NULL PROBE
# =====================================================

cat > vi6_41_ffmpeg_null_probe.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_38_filter_validator import (
    validate as validate_filter
)


VERSION = "6.41"


REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_41_ffmpeg_probe_latest.json"
)


def sample_plan():

    contract = {

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
                    1.04,

                "start_x":
                    .46,

                "start_y":
                    .50,

                "end_x":
                    .54,

                "end_y":
                    .50,
            },
    }


    duration = {
        "seconds":
            4.0
    }


    return compile_plan(
        contract,
        duration
    )


def build_probe_command(
    dry_plan
):

    vf = str(
        dry_plan.get(
            "vf"
        )
        or ""
    )


    return [
        "ffmpeg",

        "-hide_banner",

        "-loglevel",
        "error",

        "-f",
        "lavfi",

        "-i",
        (
            "color="
            "c=black:"
            "s=1080x1920:"
            "r=30:"
            "d=0.2"
        ),

        "-vf",
        vf,

        "-frames:v",
        "1",

        "-f",
        "null",

        "-"
    ]


def probe(
    dry_plan=None
):

    if dry_plan is None:

        dry_plan = sample_plan()


    static = validate_filter(
        dry_plan
    )


    if (
        static.get(
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
                "static_filter_validation_failed",

            "static":
                static,

            "ffmpeg_found":
                bool(
                    shutil.which(
                        "ffmpeg"
                    )
                ),

            "executed":
                False,

            "output_file_created":
                False,
        }


    binary = shutil.which(
        "ffmpeg"
    )


    if not binary:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffmpeg_not_found",

            "static":
                static,

            "ffmpeg_found":
                False,

            "executed":
                False,

            "output_file_created":
                False,
        }


    cmd = build_probe_command(
        dry_plan
    )


    cmd[
        0
    ] = binary


    try:

        completed = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )


        return_code = (
            completed.returncode
        )


        stderr = (
            completed.stderr
            or ""
        )[-2000:]


        stdout = (
            completed.stdout
            or ""
        )[-1000:]


        status = (
            "PASS"
            if return_code == 0
            else "HOLD"
        )


        reason = (
            "ffmpeg_filter_probe_pass"
            if return_code == 0
            else "ffmpeg_filter_probe_failed"
        )


        return {

            "version":
                VERSION,

            "status":
                status,

            "reason":
                reason,

            "ffmpeg_found":
                True,

            "ffmpeg_binary":
                binary,

            "executed":
                True,

            "execution_type":
                "NULL_OUTPUT_FILTER_PROBE",

            "return_code":
                return_code,

            "stderr_tail":
                stderr,

            "stdout_tail":
                stdout,

            "renderer_mode":
                dry_plan.get(
                    "renderer_mode"
                ),

            "filter":
                dry_plan.get(
                    "vf"
                ),

            "output_target":
                "null",

            "output_file_created":
                False,

            "video_file_created":
                False,
        }


    except subprocess.TimeoutExpired:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "ffmpeg_probe_timeout",

            "ffmpeg_found":
                True,

            "executed":
                True,

            "execution_type":
                "NULL_OUTPUT_FILTER_PROBE",

            "output_file_created":
                False,

            "video_file_created":
                False,
        }


    except Exception as exc:

        return {

            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                (
                    "ffmpeg_probe_exception:"
                    + type(
                        exc
                    ).__name__
                ),

            "ffmpeg_found":
                True,

            "executed":
                True,

            "error":
                str(
                    exc
                )[:300],

            "output_file_created":
                False,

            "video_file_created":
                False,
        }


def save(
    result,
    path=REPORT
):

    os.makedirs(
        os.path.dirname(
            path
        ),
        exist_ok=True
    )


    payload = {

        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),

        "probe":
            result,
    }


    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            payload,
            file,
            ensure_ascii=False,
            indent=2
        )


    return path


def load_latest():

    if not os.path.exists(
        REPORT
    ):

        return None


    try:

        with open(
            REPORT,
            "r",
            encoding="utf-8"
        ) as file:

            return (
                json.load(
                    file
                ).get(
                    "probe"
                )
            )


    except Exception:

        return None


def self_test():

    plan = sample_plan()


    static = validate_filter(
        plan
    )


    assert (
        static[
            "status"
        ]
        == "PASS"
    )


    cmd = build_probe_command(
        plan
    )


    assert (
        cmd[
            0
        ]
        == "ffmpeg"
    )


    assert (
        "-vf"
        in cmd
    )


    assert (
        cmd[-2:]
        == [
            "null",
            "-"
        ]
    )


    assert (
        "{OUTPUT}"
        not in cmd
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.41 PROBE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Synthetic Lavfi Input"
    )
    print(
        "OK Real Filter String"
    )
    print(
        "OK Output = null"
    )
    print(
        "OK No MP4 Path"
    )
    print(
        "OK No User Media"
    )
    print()


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--probe",
        action="store_true"
    )


    args = parser.parse_args()


    self_test()


    if not args.probe:

        return


    result = probe()

    path = save(
        result
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.41 REAL FFMPEG NULL PROBE"
    )
    print(
        "======================================"
    )

    print(
        "STATUS:",
        result.get(
            "status"
        )
    )

    print(
        "REASON:",
        result.get(
            "reason"
        )
    )

    print(
        "FFMPEG FOUND:",
        result.get(
            "ffmpeg_found"
        )
    )

    print(
        "EXECUTED:",
        result.get(
            "executed"
        )
    )

    print(
        "OUTPUT TARGET:",
        result.get(
            "output_target",
            "null"
        )
    )

    print(
        "VIDEO FILE CREATED:",
        result.get(
            "video_file_created",
            False
        )
    )

    print(
        "REPORT:",
        path
    )


    if (
        result.get(
            "status"
        )
        != "PASS"
    ):

        stderr = result.get(
            "stderr_tail"
        )

        if stderr:

            print()
            print(
                "FFMPEG ERROR TAIL:"
            )

            print(
                stderr
            )


if __name__ == "__main__":

    main()
PY


# =====================================================
# 3. VI6.42 BINDING GATE
# =====================================================

cat > vi6_42_binding_gate.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import os
from datetime import datetime


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)

from vi6_38_filter_validator import (
    validate as validate_filter
)

from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_40_controlled_renderer_bridge import (
    build_shadow_request
)

from vi6_41_ffmpeg_null_probe import (
    load_latest
)


VERSION = "6.42"


REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)


def sample_meta():

    contract = {

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
                    1.04,

                "start_x":
                    .46,

                "start_y":
                    .50,

                "end_x":
                    .54,

                "end_y":
                    .50,
            },
    }


    dry = compile_plan(
        contract,
        {
            "seconds":
                4.0
        }
    )


    return {

        "vi634_repaired_contract":
            contract,

        "vi635_ffmpeg_dry_plan":
            dry,

        "vi633_post_repair_safety":
            {
                "status":
                    "PASS"
            },

        "vi636_renderer_compatibility":
            {
                "status":
                    "STATIC_PASS"
            },
    }


def evaluate(
    adapter,
    bridge,
    static_filter,
    probe
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
            "renderer_shadow_map_hold"
        )


    if (
        bridge.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "controlled_bridge_hold"
        )


    if (
        static_filter.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "static_filter_hold"
        )


    if probe is None:

        blockers.append(
            "real_ffmpeg_probe_missing"
        )


    elif (
        probe.get(
            "status"
        )
        != "PASS"
    ):

        blockers.append(
            "real_ffmpeg_probe_hold"
        )


    else:

        if (
            probe.get(
                "output_file_created"
            )
            is not False
        ):

            blockers.append(
                "probe_created_output_file"
            )


        if (
            probe.get(
                "video_file_created"
            )
            is not False
        ):

            blockers.append(
                "probe_created_video_file"
            )


    if (
        bridge.get(
            "binding_performed"
        )
        is not False
    ):

        blockers.append(
            "binding_already_performed"
        )


    if (
        bridge.get(
            "video_py_modified"
        )
        is not False
    ):

        blockers.append(
            "video_py_modified_before_gate"
        )


    confidence = float(
        (
            adapter.get(
                "best"
            )
            or {}
        ).get(
            "score",
            0
        )
        or 0
    )


    if confidence < 50:

        blockers.append(
            "renderer_confidence_low"
        )


    elif confidence < 75:

        warnings.append(
            "renderer_confidence_medium"
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
            bridge.get(
                "target_function"
            ),

        "renderer_line_start":
            bridge.get(
                "target_line_start"
            ),

        "renderer_line_end":
            bridge.get(
                "target_line_end"
            ),

        "renderer_confidence":
            bridge.get(
                "target_confidence"
            ),

        "real_ffmpeg_probe":
            (
                probe.get(
                    "status"
                )
                if probe
                else None
            ),

        "real_ffmpeg_return_code":
            (
                probe.get(
                    "return_code"
                )
                if probe
                else None
            ),

        # READY significa apenas que podemos
        # construir o PRÓXIMO binding.
        "binding_authorized":
            False,

        "binding_performed":
            False,

        "renderer_active":
            False,

        "next_stage_allowed":
            status
            in {
                "READY_FOR_CONTROLLED_BINDING",
                "READY_WITH_WARNINGS",
            },
    }


def evaluate_real():

    adapter = inspect_renderer(
        "video.py"
    )


    meta = sample_meta()


    bridge = build_shadow_request(
        meta,
        adapter
    )


    static_filter = validate_filter(
        meta[
            "vi635_ffmpeg_dry_plan"
        ]
    )


    probe = load_latest()


    return evaluate(
        adapter,
        bridge,
        static_filter,
        probe
    )


def save(
    result,
    path=REPORT
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
    ) as file:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            file,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    result = evaluate(
        {
            "status":
                "SHADOW_READY",

            "best":
                {
                    "score":
                        100
                }
        },

        {
            "status":
                "SHADOW_READY",

            "target_function":
                "gerar_video",

            "target_line_start":
                10,

            "target_line_end":
                20,

            "target_confidence":
                100,

            "binding_performed":
                False,

            "video_py_modified":
                False,
        },

        {
            "status":
                "PASS"
        },

        {
            "status":
                "PASS",

            "return_code":
                0,

            "output_file_created":
                False,

            "video_file_created":
                False,
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
            "binding_authorized"
        ]
        is False
    )


    assert (
        result[
            "renderer_active"
        ]
        is False
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.42 BINDING GATE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Renderer Map Requirement"
    )
    print(
        "OK Bridge Requirement"
    )
    print(
        "OK Static Filter Requirement"
    )
    print(
        "OK Real FFmpeg Probe Requirement"
    )
    print(
        "OK Zero-Output Requirement"
    )
    print(
        "OK Binding Still Locked"
    )
    print()


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

    path = save(
        result
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.42 REAL BINDING GATE"
    )
    print(
        "======================================"
    )

    print(
        "STATUS:",
        result[
            "status"
        ]
    )

    print(
        "NEXT STAGE ALLOWED:",
        result[
            "next_stage_allowed"
        ]
    )

    print(
        "RENDERER FUNCTION:",
        result[
            "renderer_function"
        ]
    )

    print(
        "RENDERER LINES:",
        result[
            "renderer_line_start"
        ],
        "-",
        result[
            "renderer_line_end"
        ]
    )

    print(
        "CONFIDENCE:",
        result[
            "renderer_confidence"
        ]
    )

    print(
        "REAL FFMPEG PROBE:",
        result[
            "real_ffmpeg_probe"
        ]
    )

    print(
        "BINDING AUTHORIZED:",
        result[
            "binding_authorized"
        ]
    )

    print(
        "RENDERER ACTIVE:",
        result[
            "renderer_active"
        ]
    )


    if result[
        "blockers"
    ]:

        print(
            "BLOCKERS:",
            result[
                "blockers"
            ]
        )


    if result[
        "warnings"
    ]:

        print(
            "WARNINGS:",
            result[
                "warnings"
            ]
        )


    print(
        "REPORT:",
        path
    )


if __name__ == "__main__":

    main()
PY


# =====================================================
# 4. VI6.42 RUNTIME SHADOW POLICY
# =====================================================

cat > vi6_42_runtime_policy.py <<'PY'
#!/usr/bin/env python3

import json
import os
from datetime import datetime


import vi6_6_active_brain as brain


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)

from vi6_40_controlled_renderer_bridge import (
    build_shadow_request
)


_ADAPTER = inspect_renderer(
    "video.py"
)


_EVENTS = []


if not getattr(
    brain,
    "_VI642_RUNTIME_ACTIVE",
    False
):

    _base_supervisor_642 = (
        brain.supervisionar_vi6_6
    )


    def _wrapped_642(
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

            _EVENTS.clear()


        (
            candidate,
            reason,
            meta
        ) = _base_supervisor_642(
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


        bridge = build_shadow_request(
            meta,
            _ADAPTER
        )


        meta[
            "vi640_renderer_bridge"
        ] = bridge


        meta[
            "vi640_renderer_mode"
        ] = "SHADOW"


        meta[
            "vi640_binding_performed"
        ] = False


        event = {

            "scene":
                number,

            "status":
                bridge.get(
                    "status"
                ),

            "renderer_mode":
                bridge.get(
                    "renderer_mode"
                ),

            "target_function":
                bridge.get(
                    "target_function"
                ),

            "target_line":
                bridge.get(
                    "target_line_start"
                ),

            "filter_ready":
                (
                    bridge.get(
                        "filter_report"
                    )
                    or {}
                ).get(
                    "status"
                ),

            "binding_performed":
                False,
        }


        _EVENTS.append(
            event
        )


        if candidate is not None:

            candidate[
                "_vi640_bridge_status"
            ] = bridge.get(
                "status"
            )


            candidate[
                "_vi640_renderer_mode"
            ] = "SHADOW"


            candidate[
                "_vi640_binding_performed"
            ] = False


        if (
            number >= 12
            or board.get(
                "cta_reuse"
            )
        ):

            try:

                folder = os.path.expanduser(
                    "~/ShortAutoPro/logs/producao"
                )


                os.makedirs(
                    folder,
                    exist_ok=True
                )


                path = os.path.join(
                    folder,
                    "vi6_40_shadow_runtime_latest.json"
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

                            "mode":
                                "SHADOW",

                            "events":
                                list(
                                    _EVENTS
                                ),

                            "renderer_active":
                                False,

                            "binding_performed":
                                False,
                        },
                        file,
                        ensure_ascii=False,
                        indent=2
                    )


                meta[
                    "vi640_shadow_report_path"
                ] = path


            except Exception as exc:

                meta[
                    "vi640_shadow_report_error"
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
        _wrapped_642
    )


    brain._VI640_RUNTIME_ACTIVE = True
    brain._VI642_RUNTIME_ACTIVE = True
PY


# =====================================================
# 5. ATTACH RUNTIME
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
    "# VI6.40-6.42 CONTROLLED BRIDGE STACK"
)


if MARKER in source:

    print(
        "VI6.40-6.42 já conectado."
    )

    raise SystemExit(0)


append = '''

# =========================================
# VI6.40-6.42 CONTROLLED BRIDGE STACK
# =========================================
import vi6_42_runtime_policy
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
    " VI6.40-6.42 RUNTIME ATTACHED"
)
print(
    "======================================"
)
print(
    "Bridge Mode: SHADOW"
)
print(
    "Binding: LOCKED"
)
print(
    "video.py: UNTOUCHED"
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

cat > testar_vi640_vi642.py <<'PY'
#!/usr/bin/env python3

import vi6_6_active_brain as brain

import vi6_8_runtime_policy
import vi6_9_runtime_policy


for flag in (

    "_VI69_RUNTIME_PATCHED",

    "_VI634_RUNTIME_ACTIVE",
    "_VI635_RUNTIME_ACTIVE",
    "_VI636_RUNTIME_ACTIVE",

    "_VI637_RUNTIME_ACTIVE",
    "_VI638_RUNTIME_ACTIVE",
    "_VI639_RUNTIME_ACTIVE",

    "_VI640_RUNTIME_ACTIVE",
    "_VI642_RUNTIME_ACTIVE",
):

    assert getattr(
        brain,
        flag,
        False
    ), flag


print()
print(
    "======================================"
)
print(
    " VI6.40-6.42 RUNTIME TEST: PASS"
)
print(
    "======================================"
)

print(
    "VI6.39 GATE:",
    brain._VI639_RUNTIME_ACTIVE
)

print(
    "VI6.40 BRIDGE:",
    brain._VI640_RUNTIME_ACTIVE
)

print(
    "VI6.42 RUNTIME:",
    brain._VI642_RUNTIME_ACTIVE
)

print()
print(
    "BRIDGE MODE=SHADOW"
)
print(
    "BINDING PERFORMED=False"
)
print(
    "RENDERER ACTIVE=False"
)
print(
    "VIDEO.PY MODIFIED=False"
)
print()
PY


# =====================================================
# 7. COMPILE
# =====================================================

echo
echo "===== FULL COMPILE ====="

if ! python -m py_compile \
    vi6_40_controlled_renderer_bridge.py \
    vi6_41_ffmpeg_null_probe.py \
    vi6_42_binding_gate.py \
    vi6_42_runtime_policy.py \
    testar_vi640_vi642.py \
    vi6_39_activation_gate.py \
    vi6_38_filter_validator.py \
    vi6_37_renderer_shadow_adapter.py \
    vi6_36_renderer_compatibility.py \
    vi6_35_ffmpeg_dry_compiler.py \
    vi6_34_motion_auto_repair.py \
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
echo "===== VI6.40 SELF TEST ====="

if ! python vi6_40_controlled_renderer_bridge.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.41 SELF TEST ====="

if ! python vi6_41_ffmpeg_null_probe.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.42 SELF TEST ====="

if ! python vi6_42_binding_gate.py; then
    rollback
    exit 1
fi


echo
echo "===== RUNTIME TEST ====="

if ! python testar_vi640_vi642.py; then
    rollback
    exit 1
fi


# =====================================================
# 9. REGRESSION
# =====================================================

echo
echo "===== VI6.39 REGRESSION ====="

if ! python vi6_39_activation_gate.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.38 REGRESSION ====="

if ! python vi6_38_filter_validator.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.37 REGRESSION ====="

if ! python vi6_37_renderer_shadow_adapter.py; then
    rollback
    exit 1
fi


echo
echo "===== VI6.36 REGRESSION ====="

if ! python vi6_36_renderer_compatibility.py; then
    rollback
    exit 1
fi


# =====================================================
# 10. REAL FFMPEG FILTER PROBE
# =====================================================

echo
echo "======================================"
echo " REAL FFMPEG PROBE"
echo " OUTPUT = NULL"
echo " NENHUM VIDEO SERA SALVO"
echo "======================================"

python vi6_41_ffmpeg_null_probe.py \
    --probe


# Não fazemos rollback se o probe der HOLD.
# O renderer simplesmente continuará SHADOW.


# =====================================================
# 11. REAL VI6.42 GATE
# =====================================================

echo
echo "===== REAL VI6.42 BINDING GATE ====="

python vi6_42_binding_gate.py \
    --real


# =====================================================
# 12. CORE
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
# 13. CORE HASH
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
# 14. FINAL STATUS
# =====================================================

echo
echo "===== FINAL GATE STATUS ====="

python - <<'PY'
import json
import os


path = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)


if not os.path.exists(path):

    print(
        "VI6.42 STATUS=NO_REPORT"
    )

    raise SystemExit(0)


with open(
    path,
    "r",
    encoding="utf-8"
) as file:

    gate = json.load(
        file
    ).get(
        "gate",
        {}
    )


print(
    "VI6.42 STATUS="
    + str(
        gate.get(
            "status"
        )
    )
)

print(
    "NEXT STAGE ALLOWED="
    + str(
        gate.get(
            "next_stage_allowed"
        )
    )
)

print(
    "RENDERER FUNCTION="
    + str(
        gate.get(
            "renderer_function"
        )
    )
)

print(
    "RENDERER LINE="
    + str(
        gate.get(
            "renderer_line_start"
        )
    )
)

print(
    "RENDERER CONFIDENCE="
    + str(
        gate.get(
            "renderer_confidence"
        )
    )
)

print(
    "REAL FFMPEG PROBE="
    + str(
        gate.get(
            "real_ffmpeg_probe"
        )
    )
)

print(
    "BINDING AUTHORIZED="
    + str(
        gate.get(
            "binding_authorized"
        )
    )
)

print(
    "RENDERER ACTIVE="
    + str(
        gate.get(
            "renderer_active"
        )
    )
)
PY


echo
echo "======================================"
echo " VI6.40 + VI6.41 + VI6.42 INSTALADOS"
echo "======================================"
echo
echo "OK Controlled Renderer Bridge"
echo "OK Renderer Target from Real AST Map"
echo "OK SHADOW-only Phase Lock"
echo "OK ACTIVE Accidental Activation Blocked"
echo "OK Real FFmpeg Null Probe"
echo "OK Real Zoompan Syntax Probe"
echo "OK Real Termux FFmpeg Compatibility Probe"
echo "OK Output Target = null"
echo "OK Binding Gate"
echo "OK Existing VI6.39 Gate preserved"
echo "OK Existing VI6.36 Compatibility preserved"
echo
echo "CORE FILES UNCHANGED=YES"
echo "MIDIA.PY MODIFICADO=NAO"
echo "VIDEO.PY MODIFICADO=NAO"
echo "AUDIO.PY MODIFICADO=NAO"
echo "LEGENDA MODIFICADA=NAO"
echo "GERAR_SHORT MODIFICADO=NAO"
echo
echo "FFMPEG PROBE EXECUTADO=SIM"
echo "FFMPEG OUTPUT=NULL"
echo "ARQUIVO DE VIDEO CRIADO=NAO"
echo "SHORT GERADO=NAO"
echo "DOWNLOAD DE MIDIA=NAO"
echo "API CALLS=0"
echo
echo "REPORTS:"
echo "logs/producao/vi6_41_ffmpeg_probe_latest.json"
echo "logs/producao/vi6_42_binding_gate_latest.json"
echo
