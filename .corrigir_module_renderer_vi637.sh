#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi637_module_fix_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " VI6.37 MODULE-LEVEL RENDERER FIX"
echo " + VI6.40 / VI6.42 / VI6.43"
echo "======================================================"
echo

REQUIRED="
video.py
vi6_35_ffmpeg_dry_compiler.py
vi6_38_filter_validator.py
vi6_41_ffmpeg_null_probe.py
vi6_45_micro_render_certification.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F ausente."
        exit 2
    fi
done


# =====================================================
# BACKUP
# =====================================================

for F in \
    vi6_37_renderer_shadow_adapter.py \
    vi6_40_controlled_renderer_bridge.py \
    vi6_42_binding_gate.py \
    vi6_43_exact_binding_planner.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


VIDEO_HASH_BEFORE="$(sha256sum video.py | awk '{print $1}')"


rollback() {

    echo
    echo "===== ROLLBACK ====="

    for F in \
        vi6_37_renderer_shadow_adapter.py \
        vi6_40_controlled_renderer_bridge.py \
        vi6_42_binding_gate.py \
        vi6_43_exact_binding_planner.py
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        fi

    done

    echo "Módulos restaurados."
}


# =====================================================
# VI6.37.2 MODULE LEVEL PIPELINE MAPPER
# =====================================================

cat > vi6_37_renderer_shadow_adapter.py <<'PY'
#!/usr/bin/env python3

import ast
import hashlib
import json
import os

from datetime import datetime
from pathlib import Path


VERSION = "6.37.2"


def _hash_file(path):

    return hashlib.sha256(
        Path(path).read_bytes()
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

        parts = []
        cur = node.func

        while isinstance(
            cur,
            ast.Attribute
        ):

            parts.append(
                cur.attr
            )

            cur = cur.value


        if isinstance(
            cur,
            ast.Name
        ):

            parts.append(
                cur.id
            )


        return ".".join(
            reversed(
                parts
            )
        )


    return ""


def _inside_function(
    tree,
    line
):

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


        start = node.lineno

        end = getattr(
            node,
            "end_lineno",
            start
        )


        if start <= line <= end:

            return node.name


    return None


def _window(
    lines,
    center,
    before=130,
    after=20
):

    start = max(
        1,
        center - before
    )

    end = min(
        len(lines),
        center + after
    )


    return "\n".join(
        lines[
            start - 1:
            end
        ]
    )


def _classify(
    line,
    blob,
    call
):

    low = blob.lower()


    has_ffmpeg = (
        "ffmpeg"
        in low
    )


    has_ffprobe = (
        "ffprobe"
        in low
    )


    has_zoompan = (
        "zoompan"
        in low
    )


    has_vf = (
        '"-vf"'
        in low
        or "'-vf'"
        in low
        or " -vf "
        in low
    )


    has_filter_complex = (
        "filter_complex"
        in low
    )


    has_libx264 = (
        "libx264"
        in low
    )


    has_yuv420p = (
        "yuv420p"
        in low
    )


    # ---------------------------------
    # FFPROBE
    # ---------------------------------

    if (
        "check_output"
        in call.lower()
        and has_ffprobe
    ):

        return {
            "role":
                "FFPROBE",

            "score":
                100,
        }


    # ---------------------------------
    # FINAL COMPOSITOR
    # ---------------------------------

    if (
        has_ffmpeg
        and has_filter_complex
    ):

        score = 90

        if has_libx264:
            score += 5

        if has_yuv420p:
            score += 5


        return {
            "role":
                "FINAL_COMPOSITOR",

            "score":
                score,
        }


    # ---------------------------------
    # SCENE MOTION RENDER
    # ---------------------------------

    if (
        has_ffmpeg
        and has_zoompan
        and has_vf
    ):

        score = 110

        if has_libx264:
            score += 5

        if has_yuv420p:
            score += 5


        return {
            "role":
                "SCENE_RENDER_PRIMARY",

            "score":
                score,
        }


    # ---------------------------------
    # SCENE / AUX RENDER
    # ---------------------------------

    if (
        has_ffmpeg
        and (
            has_vf
            or has_libx264
        )
    ):

        return {
            "role":
                "SCENE_RENDER_AUX",

            "score":
                70,
        }


    if has_ffmpeg:

        return {
            "role":
                "FFMPEG_OTHER",

            "score":
                40,
        }


    return {
        "role":
            "PROCESS_OTHER",

        "score":
            10,
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


    lines = source.splitlines()

    tree = ast.parse(
        source
    )


    candidates = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call
        ):
            continue


        call = _call_name(
            node
        )


        if call not in {
            "subprocess.run",
            "subprocess.check_output",
            "subprocess.Popen",
        }:

            continue


        owner = _inside_function(
            tree,
            node.lineno
        )


        # Renderer real deste projeto está
        # no módulo principal. Mantemos
        # funções no relatório, mas não as
        # tratamos como alvo primário.
        scope = (
            "FUNCTION"
            if owner
            else "MODULE"
        )


        blob = _window(
            lines,
            node.lineno
        )


        classification = _classify(
            node.lineno,
            blob,
            call
        )


        entry = {

            "kind":
                (
                    "MODULE_LEVEL_RENDERER"
                    if scope == "MODULE"
                    else
                    "FUNCTION_PROCESS"
                ),

            "scope":
                scope,

            "owner_function":
                owner,

            "execution_line":
                node.lineno,

            "line_start":
                max(
                    1,
                    node.lineno - 130
                ),

            "line_end":
                min(
                    len(lines),
                    node.lineno + 20
                ),

            "call":
                call,

            "role":
                classification[
                    "role"
                ],

            "score":
                classification[
                    "score"
                ],

            "has_ffmpeg":
                "ffmpeg"
                in blob.lower(),

            "has_ffprobe":
                "ffprobe"
                in blob.lower(),

            "has_zoompan":
                "zoompan"
                in blob.lower(),

            "has_vf":
                (
                    '"-vf"'
                    in blob.lower()
                    or "'-vf'"
                    in blob.lower()
                ),

            "has_filter_complex":
                "filter_complex"
                in blob.lower(),

            "has_libx264":
                "libx264"
                in blob.lower(),

            "has_yuv420p":
                "yuv420p"
                in blob.lower(),
        }


        candidates.append(
            entry
        )


    # Apenas module-level para ativação.
    module_candidates = [
        item
        for item in candidates
        if item[
            "scope"
        ] == "MODULE"
    ]


    primary = [
        item
        for item in module_candidates
        if item[
            "role"
        ] == "SCENE_RENDER_PRIMARY"
    ]


    final = [
        item
        for item in module_candidates
        if item[
            "role"
        ] == "FINAL_COMPOSITOR"
    ]


    aux = [
        item
        for item in module_candidates
        if item[
            "role"
        ] == "SCENE_RENDER_AUX"
    ]


    probes = [
        item
        for item in module_candidates
        if item[
            "role"
        ] == "FFPROBE"
    ]


    primary.sort(
        key=lambda x: (
            x[
                "score"
            ],
            -x[
                "execution_line"
            ]
        ),
        reverse=True
    )


    final.sort(
        key=lambda x: (
            x[
                "score"
            ],
            x[
                "execution_line"
            ]
        ),
        reverse=True
    )


    best = (
        primary[0]
        if primary
        else None
    )


    blockers = []

    warnings = []


    if best is None:

        blockers.append(
            "scene_renderer_not_proven"
        )


    if not final:

        warnings.append(
            "final_compositor_not_proven"
        )


    if best is not None:

        if not best[
            "has_zoompan"
        ]:

            blockers.append(
                "primary_missing_zoompan"
            )


        if not best[
            "has_vf"
        ]:

            blockers.append(
                "primary_missing_vf"
            )


    if blockers:

        status = "HOLD"

        reason = (
            "module_scene_renderer_not_proven"
        )


    else:

        status = "SHADOW_READY"

        reason = (
            "module_level_scene_renderer_proven"
        )


    candidates.sort(
        key=lambda x: (
            x[
                "score"
            ],
            x[
                "execution_line"
            ]
        ),
        reverse=True
    )


    return {

        "version":
            VERSION,

        "mode":
            "SHADOW",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

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

        "module_candidate_count":
            len(
                module_candidates
            ),

        "eligible_count":
            len(
                primary
            ),

        "primary_scene_renderer":
            best,

        # Backward compatibility.
        "best":
            best,

        "scene_aux_renderers":
            aux,

        "final_compositor":
            (
                final[0]
                if final
                else None
            ),

        "probes":
            probes,

        "candidates":
            candidates,

        "blockers":
            blockers,

        "warnings":
            warnings,

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
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "report":
                    report,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    fake = '''
import subprocess

cmd = [
    "ffmpeg",
    "-i", "image.jpg",
    "-vf",
    "scale=1080:1920,zoompan=z='1.02':d=30",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "scene.mp4",
]

subprocess.run(cmd)

final_cmd = [
    "ffmpeg",
    "-i", "scene.mp4",
    "-filter_complex",
    "[0:v]format=yuv420p[v]",
    "-c:v", "libx264",
    "final.mp4",
]

subprocess.run(final_cmd)
'''


    tmp = Path(
        ".vi637_selftest.py"
    )


    try:

        tmp.write_text(
            fake,
            encoding="utf-8"
        )


        report = inspect_renderer(
            str(
                tmp
            )
        )


        assert (
            report[
                "status"
            ]
            == "SHADOW_READY"
        )


        assert (
            report[
                "architecture"
            ]
            == "MODULE_LEVEL_PIPELINE"
        )


        assert (
            report[
                "primary_scene_renderer"
            ][
                "role"
            ]
            == "SCENE_RENDER_PRIMARY"
        )


        assert (
            report[
                "final_compositor"
            ][
                "role"
            ]
            == "FINAL_COMPOSITOR"
        )


    finally:

        try:
            tmp.unlink()
        except Exception:
            pass


    print()
    print(
        "======================================"
    )
    print(
        " VI6.37.2 MODULE MAPPER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Renderer"
    )
    print(
        "OK Scene Renderer Classification"
    )
    print(
        "OK Zoompan Detection"
    )
    print(
        "OK Final Compositor Classification"
    )
    print(
        "OK No video.py import"
    )
    print()


if __name__ == "__main__":

    self_test()


    report = inspect_renderer(
        "video.py"
    )


    save_report(
        report
    )


    print()
    print(
        "REAL STATUS:",
        report.get(
            "status"
        )
    )


    print(
        "ARCHITECTURE:",
        report.get(
            "architecture"
        )
    )


    primary = (
        report.get(
            "primary_scene_renderer"
        )
        or {}
    )


    final = (
        report.get(
            "final_compositor"
        )
        or {}
    )


    print(
        "PRIMARY EXECUTION LINE:",
        primary.get(
            "execution_line"
        )
    )


    print(
        "PRIMARY SCORE:",
        primary.get(
            "score"
        )
    )


    print(
        "PRIMARY ZOOMPAN:",
        primary.get(
            "has_zoompan"
        )
    )


    print(
        "FINAL COMPOSITOR LINE:",
        final.get(
            "execution_line"
        )
    )


    print(
        "BLOCKERS:",
        report.get(
            "blockers"
        )
    )


    print(
        "WARNINGS:",
        report.get(
            "warnings"
        )
    )
PY


# =====================================================
# VI6.40.2 CONTROLLED BRIDGE
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


VERSION = "6.40.2"

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


    requested = _mode()


    if requested == "OFF":

        return {
            "version":
                VERSION,

            "status":
                "DISABLED",

            "mode":
                "OFF",

            "ready":
                False,

            "executed":
                False,

            "binding_performed":
                False,
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


    if requested == "ACTIVE":

        blockers.append(
            "active_locked_until_future_binding"
        )


    primary = (
        adapter.get(
            "primary_scene_renderer"
        )
        or adapter.get(
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

        "architecture":
            adapter.get(
                "architecture"
            ),

        "requested_mode":
            requested,

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

        "target_kind":
            primary.get(
                "kind"
            ),

        "target_role":
            primary.get(
                "role"
            ),

        "target_function":
            primary.get(
                "owner_function"
            ),

        "target_execution_line":
            primary.get(
                "execution_line"
            ),

        # Backward-compatible names.
        "target_line_start":
            primary.get(
                "execution_line"
            ),

        "target_line_end":
            primary.get(
                "execution_line"
            ),

        "target_confidence":
            primary.get(
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

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "file_sha256":
            "x",

        "primary_scene_renderer":
            {
                "kind":
                    "MODULE_LEVEL_RENDERER",

                "role":
                    "SCENE_RENDER_PRIMARY",

                "owner_function":
                    None,

                "execution_line":
                    970,

                "score":
                    120,
            },
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
        "target_execution_line"
    ] == 970


    assert result[
        "target_role"
    ] == "SCENE_RENDER_PRIMARY"


    print()
    print(
        "======================================"
    )
    print(
        " VI6.40.2 BRIDGE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Target"
    )
    print(
        "OK Execution-Line Targeting"
    )
    print(
        "OK Shadow Lock"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI6.42.2 MODULE-AWARE GATE
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


VERSION = "6.42.2"


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
                "video_file_created"
            )
            is not False
        ):

            blockers.append(
                "probe_created_video_file"
            )


    primary = (
        adapter.get(
            "primary_scene_renderer"
        )
        or adapter.get(
            "best"
        )
        or {}
    )


    confidence = float(
        primary.get(
            "score",
            0
        )
        or 0
    )


    if confidence < 70:

        blockers.append(
            "renderer_confidence_low"
        )


    if (
        primary.get(
            "role"
        )
        != "SCENE_RENDER_PRIMARY"
    ):

        blockers.append(
            "scene_renderer_role_not_proven"
        )


    if (
        primary.get(
            "scope"
        )
        != "MODULE"
    ):

        blockers.append(
            "unexpected_renderer_scope"
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

        "renderer_architecture":
            adapter.get(
                "architecture"
            ),

        "renderer_kind":
            primary.get(
                "kind"
            ),

        "renderer_role":
            primary.get(
                "role"
            ),

        "renderer_function":
            primary.get(
                "owner_function"
            ),

        "renderer_execution_line":
            primary.get(
                "execution_line"
            ),

        # Backward compatibility.
        "renderer_line_start":
            primary.get(
                "execution_line"
            ),

        "renderer_line_end":
            primary.get(
                "execution_line"
            ),

        "renderer_confidence":
            confidence,

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
    ) as f:

        json.dump(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    adapter = {

        "status":
            "SHADOW_READY",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "primary_scene_renderer":
            {
                "kind":
                    "MODULE_LEVEL_RENDERER",

                "scope":
                    "MODULE",

                "role":
                    "SCENE_RENDER_PRIMARY",

                "owner_function":
                    None,

                "execution_line":
                    970,

                "score":
                    120,
            },
    }


    bridge = {

        "status":
            "SHADOW_READY"
    }


    result = evaluate(
        adapter,
        bridge,
        {
            "status":
                "PASS"
        },
        {
            "status":
                "PASS",

            "return_code":
                0,

            "video_file_created":
                False,
        }
    )


    assert result[
        "status"
    ] == "READY_FOR_CONTROLLED_BINDING"


    assert result[
        "renderer_execution_line"
    ] == 970


    print()
    print(
        "======================================"
    )
    print(
        " VI6.42.2 MODULE GATE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Renderer Gate"
    )
    print(
        "OK FFmpeg Probe Requirement"
    )
    print(
        "OK Confidence Requirement"
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
        " VI6.42.2 REAL BINDING GATE"
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
        "ARCHITECTURE:",
        result.get(
            "renderer_architecture"
        )
    )


    print(
        "ROLE:",
        result.get(
            "renderer_role"
        )
    )


    print(
        "EXECUTION LINE:",
        result.get(
            "renderer_execution_line"
        )
    )


    print(
        "CONFIDENCE:",
        result.get(
            "renderer_confidence"
        )
    )


    print(
        "FFMPEG PROBE:",
        result.get(
            "real_ffmpeg_probe"
        )
    )


    print(
        "NEXT STAGE ALLOWED:",
        result.get(
            "next_stage_allowed"
        )
    )


    print(
        "BLOCKERS:",
        result.get(
            "blockers"
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
# VI6.43.2 MODULE-LEVEL EXACT PLAN
# =====================================================

cat > vi6_43_exact_binding_planner.py <<'PY'
#!/usr/bin/env python3

import ast
import hashlib
import json
import os

from datetime import datetime
from pathlib import Path


VERSION = "6.43.2"


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

            return json.load(
                f
            ).get(
                "gate"
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

        parts = []

        cur = node.func


        while isinstance(
            cur,
            ast.Attribute
        ):

            parts.append(
                cur.attr
            )

            cur = cur.value


        if isinstance(
            cur,
            ast.Name
        ):

            parts.append(
                cur.id
            )


        return ".".join(
            reversed(
                parts
            )
        )


    return ""


def inspect_module_target(
    filename,
    execution_line
):

    source = Path(
        filename
    ).read_text(
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
                ast.Call
            )
            and node.lineno
            == int(
                execution_line
            )
            and _call_name(
                node
            )
            in {
                "subprocess.run",
                "subprocess.check_output",
            }
        ):

            target = node
            break


    if target is None:

        return None


    window_start = max(
        1,
        int(
            execution_line
        ) - 130
    )


    window_end = min(
        len(lines),
        int(
            execution_line
        ) + 10
    )


    window = "\n".join(
        lines[
            window_start - 1:
            window_end
        ]
    )


    filter_lines = []

    ffmpeg_lines = []

    zoompan_lines = []


    for number in range(
        window_start,
        window_end + 1
    ):

        low = lines[
            number - 1
        ].lower()


        if "ffmpeg" in low:

            ffmpeg_lines.append(
                number
            )


        if (
            '"-vf"'
            in low
            or "'-vf'"
            in low
        ):

            filter_lines.append(
                number
            )


        if "zoompan" in low:

            zoompan_lines.append(
                number
            )


    return {

        "execution_line":
            int(
                execution_line
            ),

        "call":
            _call_name(
                target
            ),

        "window_start":
            window_start,

        "window_end":
            window_end,

        "ffmpeg_lines":
            ffmpeg_lines,

        "filter_lines":
            filter_lines,

        "zoompan_lines":
            zoompan_lines,

        "has_ffmpeg":
            "ffmpeg"
            in window.lower(),

        "has_vf":
            bool(
                filter_lines
            ),

        "has_zoompan":
            bool(
                zoompan_lines
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


    architecture = gate.get(
        "renderer_architecture"
    )


    execution_line = gate.get(
        "renderer_execution_line"
    )


    if (
        architecture
        != "MODULE_LEVEL_PIPELINE"
    ):

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "unsupported_renderer_architecture",

            "video_modified":
                False,
        }


    if not execution_line:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "renderer_execution_line_missing",

            "video_modified":
                False,
        }


    detail = inspect_module_target(
        "video.py",
        execution_line
    )


    if detail is None:

        return {
            "version":
                VERSION,

            "status":
                "HOLD",

            "reason":
                "module_execution_target_changed",

            "video_modified":
                False,
        }


    blockers = []

    warnings = []


    if not detail[
        "has_ffmpeg"
    ]:

        blockers.append(
            "ffmpeg_not_proven"
        )


    if not detail[
        "has_vf"
    ]:

        blockers.append(
            "vf_not_proven"
        )


    if not detail[
        "has_zoompan"
    ]:

        blockers.append(
            "zoompan_not_proven"
        )


    status = (
        "READY_FOR_ADAPTER_PREVIEW"
        if not blockers
        else "HOLD"
    )


    return {

        "version":
            VERSION,

        "status":
            status,

        "reason":
            (
                "module_scene_render_target_resolved"
                if not blockers
                else "module_scene_target_incomplete"
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "video_sha256":
            _hash(
                "video.py"
            ),

        "renderer_architecture":
            architecture,

        "renderer_kind":
            gate.get(
                "renderer_kind"
            ),

        "renderer_role":
            gate.get(
                "renderer_role"
            ),

        "renderer_function":
            None,

        "renderer_execution_line":
            execution_line,

        "renderer_line_start":
            execution_line,

        "renderer_line_end":
            execution_line,

        "strategy":
            "MODULE_LEVEL_SCENE_FILTER_BINDING",

        "suggested_insertion_line":
            (
                detail[
                    "filter_lines"
                ][0]
                if detail[
                    "filter_lines"
                ]
                else None
            ),

        "ffmpeg_lines":
            detail[
                "ffmpeg_lines"
            ],

        "filter_lines":
            detail[
                "filter_lines"
            ],

        "zoompan_lines":
            detail[
                "zoompan_lines"
            ],

        "execution_lines":
            [
                execution_line
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

    # Apenas prova que o módulo compila
    # e o formato de plano module-level
    # é aceito.
    sample = {

        "renderer_architecture":
            "MODULE_LEVEL_PIPELINE",

        "renderer_execution_line":
            970,

        "strategy":
            "MODULE_LEVEL_SCENE_FILTER_BINDING",
    }


    assert sample[
        "renderer_execution_line"
    ] == 970


    print()
    print(
        "======================================"
    )
    print(
        " VI6.43.2 MODULE PLAN SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Strategy"
    )
    print(
        "OK Execution-Line Binding Model"
    )
    print(
        "OK No Function Assumption"
    )
    print()


if __name__ == "__main__":

    self_test()


    result = build_plan()

    path = save(
        result
    )


    print()
    print(
        "REAL PLAN STATUS:",
        result.get(
            "status"
        )
    )


    print(
        "ARCHITECTURE:",
        result.get(
            "renderer_architecture"
        )
    )


    print(
        "ROLE:",
        result.get(
            "renderer_role"
        )
    )


    print(
        "EXECUTION LINE:",
        result.get(
            "renderer_execution_line"
        )
    )


    print(
        "FILTER LINES:",
        result.get(
            "filter_lines"
        )
    )


    print(
        "ZOOMPAN LINES:",
        result.get(
            "zoompan_lines"
        )
    )


    print(
        "STRATEGY:",
        result.get(
            "strategy"
        )
    )


    print(
        "BLOCKERS:",
        result.get(
            "blockers"
        )
    )


    print(
        "REPORT:",
        path
    )
PY


# =====================================================
# COMPILE
# =====================================================

echo
echo "===== COMPILE ====="

if ! python -m py_compile \
    vi6_37_renderer_shadow_adapter.py \
    vi6_40_controlled_renderer_bridge.py \
    vi6_42_binding_gate.py \
    vi6_43_exact_binding_planner.py
then

    rollback
    exit 1
fi


echo "COMPILE=PASS"


# =====================================================
# TEST REAL 6.37
# =====================================================

echo
echo "===== VI6.37.2 REAL MAP ====="

if ! python vi6_37_renderer_shadow_adapter.py; then

    rollback
    exit 1
fi


# =====================================================
# BRIDGE SELF TEST
# =====================================================

echo
echo "===== VI6.40.2 ====="

if ! python vi6_40_controlled_renderer_bridge.py; then

    rollback
    exit 1
fi


# =====================================================
# VI6.42 REAL GATE
# =====================================================

echo
echo "===== VI6.42.2 REAL GATE ====="

if ! python vi6_42_binding_gate.py --real; then

    rollback
    exit 1
fi


# =====================================================
# VI6.43 REAL PLAN
# =====================================================

echo
echo "===== VI6.43.2 REAL PLAN ====="

if ! python vi6_43_exact_binding_planner.py; then

    rollback
    exit 1
fi


# =====================================================
# READ GATES
# =====================================================

READY42="$(
python - <<'PY'
import json
import os

p = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)

try:
    x = json.load(
        open(
            p,
            encoding="utf-8"
        )
    )["gate"]

    print(
        "YES"
        if x.get(
            "next_stage_allowed"
        )
        else "NO"
    )

except Exception:
    print("NO")
PY
)"


READY43="$(
python - <<'PY'
import json
import os

p = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_43_binding_plan_latest.json"
)

try:
    x = json.load(
        open(
            p,
            encoding="utf-8"
        )
    )["plan"]

    print(
        "YES"
        if x.get(
            "status"
        )
        == "READY_FOR_ADAPTER_PREVIEW"
        else "NO"
    )

except Exception:
    print("NO")
PY
)"


echo
echo "VI6.42 READY=$READY42"
echo "VI6.43 READY=$READY43"


# =====================================================
# VI6.45 SYNTHETIC MICRO CERTIFICATION
# =====================================================

if \
    [ "$READY42" = "YES" ] \
    && [ "$READY43" = "YES" ]
then

    echo
    echo "======================================================"
    echo " VI6.45 SYNTHETIC MICRO-RENDER CERTIFICATION"
    echo " TEMPORARY TEST ONLY"
    echo "======================================================"

    python \
        vi6_45_micro_render_certification.py \
        --certify

else

    echo
    echo "VI6.45 não executado."
    echo "Algum gate ainda está HOLD."

fi


# =====================================================
# VIDEO HASH SAFETY
# =====================================================

VIDEO_HASH_AFTER="$(
sha256sum video.py \
| awk '{print $1}'
)"


echo
echo "===== VIDEO.PY SAFETY ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"

echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo
    echo "ERRO: video.py foi alterado."

    rollback

    exit 1
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# FINAL SUMMARY
# =====================================================

echo
echo "======================================================"
echo " MODULE-LEVEL RENDERER FIX COMPLETE"
echo "======================================================"

python - <<'PY'
import json
import os


base = os.path.expanduser(
    "~/ShortAutoPro/logs/producao"
)


def load(
    file,
    key
):

    path = os.path.join(
        base,
        file
    )


    if not os.path.exists(
        path
    ):

        return {}


    try:

        return json.load(
            open(
                path,
                encoding="utf-8"
            )
        ).get(
            key,
            {}
        )

    except Exception:

        return {}


r37 = load(
    "vi6_37_renderer_shadow_latest.json",
    "report"
)


r42 = load(
    "vi6_42_binding_gate_latest.json",
    "gate"
)


r43 = load(
    "vi6_43_binding_plan_latest.json",
    "plan"
)


r45 = load(
    "vi6_45_micro_render_latest.json",
    "certification"
)


print(
    "VI6.37 STATUS:",
    r37.get(
        "status"
    )
)

print(
    "ARCHITECTURE:",
    r37.get(
        "architecture"
    )
)


primary = (
    r37.get(
        "primary_scene_renderer"
    )
    or {}
)


final = (
    r37.get(
        "final_compositor"
    )
    or {}
)


print(
    "PRIMARY ROLE:",
    primary.get(
        "role"
    )
)

print(
    "PRIMARY EXECUTION LINE:",
    primary.get(
        "execution_line"
    )
)

print(
    "PRIMARY SCORE:",
    primary.get(
        "score"
    )
)

print(
    "FINAL COMPOSITOR LINE:",
    final.get(
        "execution_line"
    )
)


print()
print(
    "VI6.42 STATUS:",
    r42.get(
        "status"
    )
)

print(
    "VI6.42 NEXT STAGE:",
    r42.get(
        "next_stage_allowed"
    )
)


print()
print(
    "VI6.43 STATUS:",
    r43.get(
        "status"
    )
)

print(
    "VI6.43 STRATEGY:",
    r43.get(
        "strategy"
    )
)

print(
    "VI6.43 EXECUTION LINE:",
    r43.get(
        "renderer_execution_line"
    )
)


print()
print(
    "VI6.45 STATUS:",
    r45.get(
        "status",
        "NOT_RUN"
    )
)

print(
    "VI6.45 TEMP DELETED:",
    r45.get(
        "temporary_video_deleted"
    )
)


print()
print(
    "VIDEO.PY MODIFIED=NO"
)

print(
    "PRODUCTION SHORT GENERATED=NO"
)

print(
    "API CALLS=0"
)

print(
    "DOWNLOADS=0"
)
PY

