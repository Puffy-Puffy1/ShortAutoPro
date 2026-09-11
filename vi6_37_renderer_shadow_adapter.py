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
