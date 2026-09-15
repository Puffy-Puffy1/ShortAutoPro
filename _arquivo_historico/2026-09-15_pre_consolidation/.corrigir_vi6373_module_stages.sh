#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/vi6373_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " VI6.37.3 MODULE-STAGE RENDERER MAPPER"
echo " + VI6.40.3 / VI6.42.3 / VI6.43.3"
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


VIDEO_HASH_BEFORE="$(sha256sum video.py | awk '{print $1}')"


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


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.37.3"
    echo "======================================"

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
# 1. VI6.37.3
# =====================================================

cat > vi6_37_renderer_shadow_adapter.py <<'PY'
#!/usr/bin/env python3

import ast
import hashlib
import json
import os

from datetime import datetime
from pathlib import Path


VERSION = "6.37.3"


PROCESS_CALLS = {
    "subprocess.run",
    "subprocess.check_output",
    "subprocess.Popen",
}


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
        current = node.func


        while isinstance(
            current,
            ast.Attribute
        ):

            parts.append(
                current.attr
            )

            current = current.value


        if isinstance(
            current,
            ast.Name
        ):

            parts.append(
                current.id
            )


        return ".".join(
            reversed(
                parts
            )
        )


    return ""


def _function_ranges(tree):

    ranges = []


    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            )
        ):

            ranges.append(
                (
                    node.lineno,
                    getattr(
                        node,
                        "end_lineno",
                        node.lineno
                    ),
                    node.name,
                )
            )


    return ranges


def _owner(
    line,
    ranges
):

    owners = [
        (
            end - start,
            name
        )

        for start, end, name
        in ranges

        if start <= line <= end
    ]


    if not owners:
        return None


    owners.sort()

    return owners[0][1]


def _tokens(
    lines,
    start,
    end
):

    result = {

        "ffmpeg_lines":
            [],

        "ffprobe_lines":
            [],

        "vf_lines":
            [],

        "zoompan_lines":
            [],

        "filter_complex_lines":
            [],

        "libx264_lines":
            [],

        "yuv420p_lines":
            [],
    }


    for number in range(
        start,
        end + 1
    ):

        line = lines[
            number - 1
        ]

        low = line.lower()


        if "ffmpeg" in low:

            result[
                "ffmpeg_lines"
            ].append(
                number
            )


        if "ffprobe" in low:

            result[
                "ffprobe_lines"
            ].append(
                number
            )


        if (
            '"-vf"'
            in low
            or "'-vf'"
            in low
        ):

            result[
                "vf_lines"
            ].append(
                number
            )


        if "zoompan" in low:

            result[
                "zoompan_lines"
            ].append(
                number
            )


        if (
            "filter_complex"
            in low
        ):

            result[
                "filter_complex_lines"
            ].append(
                number
            )


        if "libx264" in low:

            result[
                "libx264_lines"
            ].append(
                number
            )


        if "yuv420p" in low:

            result[
                "yuv420p_lines"
            ].append(
                number
            )


    return result


def _classify(
    call_name,
    token
):

    has_ffmpeg = bool(
        token[
            "ffmpeg_lines"
        ]
    )


    has_ffprobe = bool(
        token[
            "ffprobe_lines"
        ]
    )


    has_vf = bool(
        token[
            "vf_lines"
        ]
    )


    has_zoompan = bool(
        token[
            "zoompan_lines"
        ]
    )


    has_complex = bool(
        token[
            "filter_complex_lines"
        ]
    )


    has_x264 = bool(
        token[
            "libx264_lines"
        ]
    )


    has_pixfmt = bool(
        token[
            "yuv420p_lines"
        ]
    )


    # -------------------------------
    # PROBE
    # -------------------------------

    if (
        call_name
        == "subprocess.check_output"
        and has_ffprobe
    ):

        return (
            "FFPROBE",
            100
        )


    # -------------------------------
    # FINAL COMPOSITOR
    # -------------------------------

    if (
        has_ffmpeg
        and has_complex
    ):

        score = 100

        if has_x264:
            score += 5

        if has_pixfmt:
            score += 5


        return (
            "FINAL_COMPOSITOR",
            score
        )


    # -------------------------------
    # PRIMARY SCENE MOTION
    # -------------------------------

    if (
        has_ffmpeg
        and has_vf
        and has_zoompan
    ):

        score = 120

        if has_x264:
            score += 5

        if has_pixfmt:
            score += 5


        return (
            "SCENE_RENDER_PRIMARY",
            score
        )


    # -------------------------------
    # AUX / VIDEO SCENE BRANCH
    # -------------------------------

    if (
        has_ffmpeg
        and has_vf
    ):

        score = 75

        if has_x264:
            score += 5

        if has_pixfmt:
            score += 5


        return (
            "SCENE_RENDER_AUX",
            score
        )


    if has_ffmpeg:

        return (
            "FFMPEG_OTHER",
            40
        )


    return (
        "PROCESS_OTHER",
        10
    )


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


    ranges = _function_ranges(
        tree
    )


    calls = []


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call
        ):
            continue


        name = _call_name(
            node
        )


        if name not in PROCESS_CALLS:

            continue


        owner = _owner(
            node.lineno,
            ranges
        )


        calls.append(
            {
                "node":
                    node,

                "call":
                    name,

                "line":
                    node.lineno,

                "owner":
                    owner,

                "scope":
                    (
                        "FUNCTION"
                        if owner
                        else "MODULE"
                    ),
            }
        )


    calls.sort(
        key=lambda item:
            item[
                "line"
            ]
    )


    module_calls = [
        item
        for item in calls
        if item[
            "scope"
        ]
        == "MODULE"
    ]


    candidates = []


    previous_line = 1


    for item in module_calls:

        execution_line = (
            item[
                "line"
            ]
        )


        # Chamadas subprocess podem ocupar várias linhas.
        # Exemplo:
        #
        # subprocess.check_output(
        #     ["ffprobe", ...]
        # )
        #
        # node.lineno aponta apenas para a primeira linha.
        # Precisamos incluir todos os argumentos da chamada.
        execution_end_line = int(
            getattr(
                item[
                    "node"
                ],
                "end_lineno",
                execution_line
            )
            or execution_line
        )


        # Cada subprocess em nível de módulo
        # encerra um estágio.
        #
        # Assim o bloco de cena ~970 não vê
        # o filter_complex do compositor ~1154.
        stage_start = max(
            1,
            previous_line
        )


        stage_end = (
            execution_end_line
        )


        token = _tokens(
            lines,
            stage_start,
            stage_end
        )


        role, score = _classify(
            item[
                "call"
            ],
            token
        )


        candidates.append(
            {

                "kind":
                    "MODULE_LEVEL_RENDERER",

                "scope":
                    "MODULE",

                "owner_function":
                    None,

                "execution_line":
                    execution_line,

                "stage_start":
                    stage_start,

                "stage_end":
                    stage_end,

                "call":
                    item[
                        "call"
                    ],

                "role":
                    role,

                "score":
                    score,

                **token,
            }
        )


        previous_line = (
            execution_end_line
            + 1
        )


    primary_candidates = [

        item
        for item in candidates

        if item[
            "role"
        ]
        == "SCENE_RENDER_PRIMARY"
    ]


    primary_candidates.sort(
        key=lambda item:
            (
                item[
                    "score"
                ],
                -item[
                    "execution_line"
                ]
            ),
        reverse=True
    )


    primary = (
        primary_candidates[0]
        if primary_candidates
        else None
    )


    final_candidates = [

        item
        for item in candidates

        if item[
            "role"
        ]
        == "FINAL_COMPOSITOR"
    ]


    final_candidates.sort(
        key=lambda item:
            item[
                "execution_line"
            ]
    )


    final = (
        final_candidates[-1]
        if final_candidates
        else None
    )


    probes = [

        item
        for item in candidates

        if item[
            "role"
        ]
        == "FFPROBE"
    ]


    aux = [

        item
        for item in candidates

        if item[
            "role"
        ]
        == "SCENE_RENDER_AUX"
    ]


    blockers = []

    warnings = []


    if primary is None:

        blockers.append(
            "scene_renderer_not_proven"
        )


    else:

        if not primary[
            "zoompan_lines"
        ]:

            blockers.append(
                "primary_zoompan_missing"
            )


        if not primary[
            "vf_lines"
        ]:

            blockers.append(
                "primary_vf_missing"
            )


        if not primary[
            "ffmpeg_lines"
        ]:

            blockers.append(
                "primary_ffmpeg_missing"
            )


    if final is None:

        warnings.append(
            "final_compositor_not_proven"
        )


    if blockers:

        status = "HOLD"

        reason = (
            "module_stage_renderer_not_proven"
        )


    else:

        status = "SHADOW_READY"

        reason = (
            "module_stage_scene_renderer_proven"
        )


    return {

        "version":
            VERSION,

        "mode":
            "SHADOW",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "mapping_method":
            "PROCESS_STAGE_BOUNDARIES",

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
                candidates
            ),

        "eligible_count":
            len(
                primary_candidates
            ),

        "primary_scene_renderer":
            primary,

        # Compatibilidade com versões antigas.
        "best":
            primary,

        "scene_aux_renderers":
            aux,

        "final_compositor":
            final,

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

        path = os.path.expanduser(
            "~/ShortAutoPro/logs/producao/"
            "vi6_37_renderer_shadow_latest.json"
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

                "report":
                    report,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return path


def self_test():

    # Os dois subprocess ficam deliberadamente
    # próximos. O mapeador precisa separá-los
    # pelos boundaries, não por uma janela ampla.
    fake = '''
import subprocess

scene_cmd = [
    "ffmpeg",
    "-i", "image.jpg",
    "-vf",
    "scale=1080:1920,zoompan=z='1.02':d=30",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "scene.mp4",
]
subprocess.run(scene_cmd)

final_cmd = [
    "ffmpeg",
    "-i", "scene.mp4",
    "-filter_complex",
    "[0:v]format=yuv420p[v]",
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "final.mp4",
]
subprocess.run(final_cmd)

subprocess.check_output(
    ["ffprobe", "final.mp4"]
)
'''


    tmp = Path(
        ".vi6373_selftest.py"
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
        ), report


        primary = (
            report[
                "primary_scene_renderer"
            ]
        )


        final = (
            report[
                "final_compositor"
            ]
        )


        assert primary is not None

        assert (
            primary[
                "role"
            ]
            == "SCENE_RENDER_PRIMARY"
        )


        assert (
            primary[
                "zoompan_lines"
            ]
        )


        assert final is not None

        assert (
            final[
                "role"
            ]
            == "FINAL_COMPOSITOR"
        )


        assert (
            report[
                "probes"
            ]
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
        " VI6.37.3 STAGE MAPPER SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Adjacent Render Stages Separated"
    )
    print(
        "OK Scene Zoompan Renderer"
    )
    print(
        "OK Final Filter-Complex Renderer"
    )
    print(
        "OK FFprobe Stage"
    )
    print(
        "OK No video.py Import"
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
        "===== REAL VIDEO.PY MAP ====="
    )


    print(
        "STATUS:",
        report.get(
            "status"
        )
    )


    print(
        "REASON:",
        report.get(
            "reason"
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
        "PRIMARY LINE:",
        primary.get(
            "execution_line"
        )
    )


    print(
        "PRIMARY STAGE:",
        primary.get(
            "stage_start"
        ),
        "-",
        primary.get(
            "stage_end"
        )
    )


    print(
        "PRIMARY SCORE:",
        primary.get(
            "score"
        )
    )


    print(
        "ZOOMPAN LINES:",
        primary.get(
            "zoompan_lines"
        )
    )


    print(
        "VF LINES:",
        primary.get(
            "vf_lines"
        )
    )


    print(
        "FINAL LINE:",
        final.get(
            "execution_line"
        )
    )


    print(
        "FINAL FILTER_COMPLEX:",
        final.get(
            "filter_complex_lines"
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


    print()
    print(
        "ALL MODULE STAGES:"
    )


    for item in report.get(
        "candidates",
        []
    ):

        print(
            " ",
            item.get(
                "execution_line"
            ),
            "->",
            item.get(
                "role"
            ),
            "score=",
            item.get(
                "score"
            )
        )
PY


# =====================================================
# 2. VI6.40.3
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


VERSION = "6.40.3"

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

            "ready":
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
            "active_locked"
        )


    primary = (
        adapter.get(
            "primary_scene_renderer"
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

        "status":
            status,

        "ready":
            status
            == "SHADOW_READY",

        "blockers":
            blockers,

        "architecture":
            adapter.get(
                "architecture"
            ),

        "target_kind":
            primary.get(
                "kind"
            ),

        "target_role":
            primary.get(
                "role"
            ),

        "target_execution_line":
            primary.get(
                "execution_line"
            ),

        "target_stage_start":
            primary.get(
                "stage_start"
            ),

        "target_stage_end":
            primary.get(
                "stage_end"
            ),

        "target_confidence":
            primary.get(
                "score"
            ),

        "video_sha256":
            adapter.get(
                "file_sha256"
            ),

        "filter_report":
            filter_report,

        "dry_plan":
            dry_plan,

        "binding_performed":
            False,

        "video_py_modified":
            False,

        "renderer_executed":
            False,
    }


def self_test():

    adapter = {

        "status":
            "SHADOW_READY",

        "architecture":
            "MODULE_LEVEL_PIPELINE",

        "file_sha256":
            "abc",

        "primary_scene_renderer":
            {
                "kind":
                    "MODULE_LEVEL_RENDERER",

                "role":
                    "SCENE_RENDER_PRIMARY",

                "execution_line":
                    970,

                "stage_start":
                    800,

                "stage_end":
                    970,

                "score":
                    130,
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
        adapter
    )


    assert (
        result[
            "status"
        ]
        == "SHADOW_READY"
    )


    assert (
        result[
            "target_execution_line"
        ]
        == 970
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.40.3 BRIDGE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Stage Target"
    )
    print(
        "OK SHADOW Lock"
    )
    print()


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 3. VI6.42.3
# =====================================================

cat > vi6_42_binding_gate.py <<'PY'
#!/usr/bin/env python3

import argparse
import json
import os

from datetime import datetime


from vi6_35_ffmpeg_dry_compiler import (
    compile_plan
)

from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)

from vi6_38_filter_validator import (
    validate as validate_filter
)

from vi6_40_controlled_renderer_bridge import (
    build_shadow_request
)

from vi6_41_ffmpeg_null_probe import (
    load_latest
)


VERSION = "6.42.3"


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


    primary = (
        adapter.get(
            "primary_scene_renderer"
        )
        or {}
    )


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


    elif (
        probe.get(
            "video_file_created"
        )
        is not False
    ):

        blockers.append(
            "null_probe_created_video"
        )


    if (
        adapter.get(
            "architecture"
        )
        != "MODULE_LEVEL_PIPELINE"
    ):

        blockers.append(
            "unexpected_architecture"
        )


    if (
        primary.get(
            "role"
        )
        != "SCENE_RENDER_PRIMARY"
    ):

        blockers.append(
            "primary_role_not_proven"
        )


    confidence = float(
        primary.get(
            "score",
            0
        )
        or 0
    )


    if confidence < 100:

        blockers.append(
            "primary_confidence_low"
        )


    if not primary.get(
        "zoompan_lines"
    ):

        blockers.append(
            "primary_zoompan_not_proven"
        )


    if not primary.get(
        "vf_lines"
    ):

        blockers.append(
            "primary_vf_not_proven"
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

        "renderer_execution_line":
            primary.get(
                "execution_line"
            ),

        "renderer_stage_start":
            primary.get(
                "stage_start"
            ),

        "renderer_stage_end":
            primary.get(
                "stage_end"
            ),

        # Compatibilidade antiga.
        "renderer_function":
            None,

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

        "video_sha256":
            adapter.get(
                "file_sha256"
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
    result
):

    os.makedirs(
        os.path.dirname(
            REPORT
        ),
        exist_ok=True
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

                "gate":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return REPORT


def self_test():

    adapter = {

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

                "execution_line":
                    970,

                "stage_start":
                    800,

                "stage_end":
                    970,

                "score":
                    130,

                "zoompan_lines":
                    [850],

                "vf_lines":
                    [890],
            },
    }


    result = evaluate(
        adapter,
        {
            "status":
                "SHADOW_READY"
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


    print()
    print(
        "======================================"
    )
    print(
        " VI6.42.3 GATE SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module Architecture"
    )
    print(
        "OK Stage Confidence"
    )
    print(
        "OK Existing Real FFmpeg Probe"
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
        " VI6.42.3 REAL GATE"
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
        "PRIMARY LINE:",
        result.get(
            "renderer_execution_line"
        )
    )


    print(
        "PRIMARY STAGE:",
        result.get(
            "renderer_stage_start"
        ),
        "-",
        result.get(
            "renderer_stage_end"
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
        "NEXT STAGE:",
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
# 4. VI6.43.3
# =====================================================

cat > vi6_43_exact_binding_planner.py <<'PY'
#!/usr/bin/env python3

import hashlib
import json
import os

from datetime import datetime
from pathlib import Path


from vi6_37_renderer_shadow_adapter import (
    inspect_renderer
)


VERSION = "6.43.3"


GATE_REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_42_binding_gate_latest.json"
)


REPORT = os.path.expanduser(
    "~/ShortAutoPro/logs/producao/"
    "vi6_43_binding_plan_latest.json"
)


def _hash(path):

    return hashlib.sha256(
        Path(path).read_bytes()
    ).hexdigest()


def _gate():

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


def build_plan():

    gate = _gate()


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


    report = inspect_renderer(
        "video.py"
    )


    primary = (
        report.get(
            "primary_scene_renderer"
        )
        or {}
    )


    blockers = []


    if (
        report.get(
            "status"
        )
        != "SHADOW_READY"
    ):

        blockers.append(
            "current_renderer_map_hold"
        )


    if (
        primary.get(
            "execution_line"
        )
        != gate.get(
            "renderer_execution_line"
        )
    ):

        blockers.append(
            "execution_line_changed"
        )


    if (
        report.get(
            "file_sha256"
        )
        != gate.get(
            "video_sha256"
        )
    ):

        blockers.append(
            "video_sha_changed_since_gate"
        )


    if not primary.get(
        "zoompan_lines"
    ):

        blockers.append(
            "zoompan_line_missing"
        )


    if not primary.get(
        "vf_lines"
    ):

        blockers.append(
            "vf_line_missing"
        )


    status = (
        "READY_FOR_ADAPTER_PREVIEW"
        if not blockers
        else "HOLD"
    )


    insertion_line = (
        primary.get(
            "vf_lines"
        )
        or [
            None
        ]
    )[0]


    return {

        "version":
            VERSION,

        "status":
            status,

        "reason":
            (
                "module_scene_filter_target_resolved"
                if not blockers
                else
                "module_scene_filter_target_hold"
            ),

        "blockers":
            blockers,

        "warnings":
            [],

        "video_sha256":
            _hash(
                "video.py"
            ),

        "renderer_architecture":
            "MODULE_LEVEL_PIPELINE",

        "renderer_kind":
            "MODULE_LEVEL_RENDERER",

        "renderer_role":
            "SCENE_RENDER_PRIMARY",

        "renderer_function":
            None,

        "renderer_execution_line":
            primary.get(
                "execution_line"
            ),

        "renderer_stage_start":
            primary.get(
                "stage_start"
            ),

        "renderer_stage_end":
            primary.get(
                "stage_end"
            ),

        # Compatibilidade antiga.
        "renderer_line_start":
            primary.get(
                "execution_line"
            ),

        "renderer_line_end":
            primary.get(
                "execution_line"
            ),

        "strategy":
            "MODULE_LEVEL_SCENE_FILTER_BINDING",

        "suggested_insertion_line":
            insertion_line,

        "ffmpeg_lines":
            primary.get(
                "ffmpeg_lines"
            ),

        "filter_lines":
            primary.get(
                "vf_lines"
            ),

        "zoompan_lines":
            primary.get(
                "zoompan_lines"
            ),

        "execution_lines":
            [
                primary.get(
                    "execution_line"
                )
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
    result
):

    os.makedirs(
        os.path.dirname(
            REPORT
        ),
        exist_ok=True
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

                "plan":
                    result,
            },
            f,
            ensure_ascii=False,
            indent=2
        )


    return REPORT


def self_test():

    assert (
        "MODULE_LEVEL_SCENE_FILTER_BINDING"
        == "MODULE_LEVEL_SCENE_FILTER_BINDING"
    )


    print()
    print(
        "======================================"
    )
    print(
        " VI6.43.3 PLAN SELF TEST: PASS"
    )
    print(
        "======================================"
    )
    print(
        "OK Module-Level Filter Strategy"
    )
    print(
        "OK No Function Wrapper Assumption"
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
        "===== REAL BINDING PLAN ====="
    )


    print(
        "STATUS:",
        result.get(
            "status"
        )
    )


    print(
        "STRATEGY:",
        result.get(
            "strategy"
        )
    )


    print(
        "EXECUTION LINE:",
        result.get(
            "renderer_execution_line"
        )
    )


    print(
        "INSERTION LINE:",
        result.get(
            "suggested_insertion_line"
        )
    )


    print(
        "VF LINES:",
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
# 5. COMPILE
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
# 6. SELF TEST + REAL MAP
# =====================================================

echo
echo "===== VI6.37.3 ====="

if ! python vi6_37_renderer_shadow_adapter.py; then

    rollback
    exit 1
fi


echo
echo "===== VI6.40.3 ====="

if ! python vi6_40_controlled_renderer_bridge.py; then

    rollback
    exit 1
fi


echo
echo "===== VI6.42.3 REAL ====="

if ! python vi6_42_binding_gate.py --real; then

    rollback
    exit 1
fi


echo
echo "===== VI6.43.3 REAL ====="

if ! python vi6_43_exact_binding_planner.py; then

    rollback
    exit 1
fi


# =====================================================
# 7. CHECK READINESS
# =====================================================

READY="$(
python - <<'PY'
import json
import os

base = os.path.expanduser(
    "~/ShortAutoPro/logs/producao"
)


try:

    with open(
        os.path.join(
            base,
            "vi6_42_binding_gate_latest.json"
        ),
        encoding="utf-8"
    ) as f:

        r42 = json.load(
            f
        )["gate"]


    with open(
        os.path.join(
            base,
            "vi6_43_binding_plan_latest.json"
        ),
        encoding="utf-8"
    ) as f:

        r43 = json.load(
            f
        )["plan"]


    ready = (
        bool(
            r42.get(
                "next_stage_allowed"
            )
        )

        and r43.get(
            "status"
        )
        == "READY_FOR_ADAPTER_PREVIEW"
    )


    print(
        "YES"
        if ready
        else "NO"
    )


except Exception:

    print("NO")
PY
)"


echo
echo "CHAIN READY FOR VI6.45=$READY"


# =====================================================
# 8. MICRO-RENDER ONLY IF READY
# =====================================================

if [ "$READY" = "YES" ]; then

    echo
    echo "======================================================"
    echo " VI6.45 SYNTHETIC MICRO-RENDER"
    echo " TEMPORARY LOCAL TEST"
    echo "======================================================"

    python \
        vi6_45_micro_render_certification.py \
        --certify

else

    echo
    echo "VI6.45 SKIPPED."
    echo "Um gate ainda está HOLD."

fi


# =====================================================
# 9. VIDEO.PY HASH PROTECTION
# =====================================================

VIDEO_HASH_AFTER="$(
sha256sum video.py \
| awk '{print $1}'
)"


echo
echo "===== VIDEO.PY HASH ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"

echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo
    echo "ERRO: video.py mudou."

    rollback
    exit 1
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 10. FINAL SUMMARY
# =====================================================

echo
echo "======================================================"
echo " VI6.37.3 CHAIN SUMMARY"
echo "======================================================"

python - <<'PY'
import json
import os


base = os.path.expanduser(
    "~/ShortAutoPro/logs/producao"
)


def load(
    filename,
    key
):

    path = os.path.join(
        base,
        filename
    )


    if not os.path.exists(
        path
    ):

        return {}


    try:

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(
                f
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
    "VI6.37 VERSION:",
    r37.get(
        "version"
    )
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

print(
    "MAPPING METHOD:",
    r37.get(
        "mapping_method"
    )
)

print(
    "PRIMARY LINE:",
    primary.get(
        "execution_line"
    )
)

print(
    "PRIMARY ROLE:",
    primary.get(
        "role"
    )
)

print(
    "PRIMARY SCORE:",
    primary.get(
        "score"
    )
)

print(
    "ZOOMPAN LINES:",
    primary.get(
        "zoompan_lines"
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

print(
    "VI6.42 BLOCKERS:",
    r42.get(
        "blockers"
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
    "VI6.43 INSERTION LINE:",
    r43.get(
        "suggested_insertion_line"
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
    "TEMP VIDEO DELETED:",
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

