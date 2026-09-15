#!/usr/bin/env python3

from __future__ import annotations


# SHORTAUTOPRO RUNTIME SHORT_ID V1
#
# O ID do short deve vir da execução atual.
# Não manter IDs históricos fixos em runtime.

_SAP_RUNTIME_SHORT_ID = os.environ.get(
    "SHORT_ID",
    "",
).strip()


import ast
import hashlib
import inspect
import json
import os
import py_compile
import re
import subprocess
import sys
import traceback
from collections import defaultdict
from pathlib import Path


ROOT = Path.cwd().resolve()

SHORT_ID = os.environ.get(
    "SHORT_ID",
    _SAP_RUNTIME_SHORT_ID,
).strip()

REPORT = (
    ROOT
    / "temp"
    / f"GENERAL_AUDIT_V2_{SHORT_ID}.txt"
)

JSON_REPORT = (
    ROOT
    / "temp"
    / f"GENERAL_AUDIT_V2_{SHORT_ID}.json"
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


results = []

STATUS_ORDER = {
    "PASS": 0,
    "INFO": 1,
    "WARN": 2,
    "FAIL": 3,
}


def emit(text=""):

    print(
        text,
        flush=True,
    )


def section(title):

    emit()
    emit("=" * 72)
    emit(title)
    emit("=" * 72)


def result(status, test, detail=""):

    item = {
        "status": status,
        "test": test,
        "detail": str(detail),
    }

    results.append(item)

    emit(
        f"{status} | "
        f"{test} | "
        f"{detail}"
    )


def sha256(path):

    path = Path(path)

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def read_text(path):

    try:

        return Path(path).read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:

        return ""


def compile_python(path):

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        return True, ""

    except Exception as exc:

        return (
            False,
            f"{type(exc).__name__}: {exc}",
        )


def shell_check(path):

    try:

        p = subprocess.run(
            [
                "bash",
                "-n",
                str(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )

        return (
            p.returncode == 0,
            (
                p.stderr.strip()
                or
                p.stdout.strip()
            ),
        )

    except Exception as exc:

        return (
            False,
            f"{type(exc).__name__}: {exc}",
        )


def find_main_guard_line(tree):

    lines = []

    for node in tree.body:

        if not isinstance(
            node,
            ast.If,
        ):
            continue

        try:
            text = ast.unparse(
                node.test
            )
        except Exception:
            text = ""

        if (
            "__name__" in text
            and
            "__main__" in text
        ):
            lines.append(
                node.lineno
            )

    return lines


def call_names(fn_node):

    names = set()

    for node in ast.walk(
        fn_node
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if isinstance(
            node.func,
            ast.Name,
        ):

            names.add(
                node.func.id
            )

        elif isinstance(
            node.func,
            ast.Attribute,
        ):

            names.add(
                node.func.attr
            )

    return names


section(
    "SHORTAUTOPRO GENERAL AUDIT V2"
)

emit(
    f"ROOT={ROOT}"
)

emit(
    f"SHORT_ID={SHORT_ID}"
)

emit(
    f"PYTHON={sys.version.split()[0]}"
)


# ============================================================
# 1. PROJECT / PATH
# ============================================================

section(
    "1. PROJECT PATH SANITY"
)

expected_name = "ShortAutoPro"

if ROOT.name == expected_name:

    result(
        "PASS",
        "PROJECT_ROOT",
        ROOT,
    )

else:

    result(
        "WARN",
        "PROJECT_ROOT",
        f"unexpected root={ROOT}",
    )


media_dir = (
    ROOT
    / "imagens"
    / f"short_{SHORT_ID}"
)


if media_dir.is_dir():

    result(
        "PASS",
        "MEDIA_DIRECTORY",
        media_dir,
    )

else:

    result(
        "FAIL",
        "MEDIA_DIRECTORY",
        f"missing={media_dir}",
    )


matching_dirs = sorted(
    (
        ROOT
        / "imagens"
    ).glob(
        f"*{SHORT_ID}*"
    )
) if (
    ROOT
    / "imagens"
).is_dir() else []


emit(
    "MEDIA_DIR_CANDIDATES="
    +
    json.dumps(
        [
            str(p)
            for p in matching_dirs
        ],
        ensure_ascii=False,
    )
)


# ============================================================
# 2. ACTUAL MEDIA
# ============================================================

section(
    "2. REAL MEDIA FILESYSTEM AUDIT"
)

allowed = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
}

valid_scenes = 0
bad_scenes = 0
media_hashes = {}


for n in range(
    1,
    13,
):

    stem = f"scene_{n:02d}"

    matches = []

    if media_dir.is_dir():

        for path in media_dir.glob(
            stem + ".*"
        ):

            if (
                path.is_file()
                and
                path.suffix.casefold()
                in allowed
            ):
                matches.append(path)


    emit()

    emit(
        f"SCENE_{n:02d}_REAL_COUNT="
        f"{len(matches)}"
    )


    for path in matches:

        digest = sha256(path)

        media_hashes[
            path.name
        ] = digest

        emit(
            f"SCENE_FILE="
            f"{path.name} "
            f"bytes={path.stat().st_size} "
            f"sha256={digest}"
        )


    if len(matches) == 1:

        valid_scenes += 1

        result(
            "PASS",
            f"SCENE_{n:02d}_REAL",
            matches[0].name,
        )

    else:

        bad_scenes += 1

        result(
            "FAIL",
            f"SCENE_{n:02d}_REAL",
            f"count={len(matches)}",
        )


emit()

emit(
    f"REAL_MEDIA_VALID={valid_scenes}"
)

emit(
    f"REAL_MEDIA_BAD={bad_scenes}"
)


if (
    valid_scenes == 12
    and
    bad_scenes == 0
):

    result(
        "PASS",
        "REAL_MEDIA_12_SCENES",
        "12/12",
    )

else:

    result(
        "FAIL",
        "REAL_MEDIA_12_SCENES",
        f"valid={valid_scenes} bad={bad_scenes}",
    )


# ============================================================
# 3. OLD AUDITOR FALSE NEGATIVE
# ============================================================

section(
    "3. OLD AUDITOR CROSS-CHECK"
)

old_reports = sorted(
    (
        ROOT
        / "temp"
    ).glob(
        "GENERAL_AUDIT_*.txt"
    ),
    key=lambda p:
        p.stat().st_mtime,
    reverse=True,
)


old_media_zero = False


if old_reports:

    old = old_reports[0]

    emit(
        f"OLD_REPORT={old}"
    )

    text = read_text(old)

    if (
        "MEDIA_12_SCENES | valid=0 bad=12"
        in text
    ):

        old_media_zero = True

        emit(
            "OLD_REPORT_SAID_ZERO_MEDIA=YES"
        )

    else:

        emit(
            "OLD_REPORT_SAID_ZERO_MEDIA=NO"
        )


    if (
        old_media_zero
        and
        valid_scenes == 12
    ):

        result(
            "WARN",
            "OLD_AUDITOR_MEDIA_FALSE_NEGATIVE",
            "old audit said 0/12 but filesystem has 12/12",
        )

    else:

        result(
            "INFO",
            "OLD_AUDITOR_MEDIA_CROSSCHECK",
            "no proven false negative",
        )

else:

    result(
        "INFO",
        "OLD_AUDITOR_REPORT",
        "not found",
    )


# ============================================================
# 4. CORE FILES
# ============================================================

section(
    "4. CORE FILES"
)

core_files = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_final_gate_v3.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
]


for name in core_files:

    path = ROOT / name

    if path.is_file():

        result(
            "PASS",
            f"FILE_{name}",
            (
                f"bytes={path.stat().st_size} "
                f"sha256={sha256(path)}"
            ),
        )

    else:

        result(
            "WARN",
            f"FILE_{name}",
            "missing",
        )


# ============================================================
# 5. PYTHON COMPILE
# ============================================================

section(
    "5. PYTHON COMPILE"
)

top_python = sorted(
    ROOT.glob("*.py")
)

compile_failures = []


for path in top_python:

    ok, detail = compile_python(
        path
    )

    if ok:

        emit(
            f"PY_COMPILE=PASS | {path.name}"
        )

    else:

        compile_failures.append(
            (
                path.name,
                detail,
            )
        )

        result(
            "FAIL",
            f"PY_COMPILE_{path.name}",
            detail,
        )


if not compile_failures:

    result(
        "PASS",
        "TOP_LEVEL_PYTHON_COMPILE",
        f"{len(top_python)} files",
    )


# ============================================================
# 6. SHELL SYNTAX
# ============================================================

section(
    "6. SHELL SYNTAX"
)

shell_files = sorted(
    ROOT.glob("*.sh")
)

shell_failures = []


for path in shell_files:

    ok, detail = shell_check(
        path
    )

    if ok:

        emit(
            f"SHELL_SYNTAX=PASS | {path.name}"
        )

    else:

        shell_failures.append(
            (
                path.name,
                detail,
            )
        )

        result(
            "FAIL",
            f"SHELL_SYNTAX_{path.name}",
            detail,
        )


if not shell_failures:

    result(
        "PASS",
        "TOP_LEVEL_SHELL_SYNTAX",
        f"{len(shell_files)} files",
    )


# ============================================================
# 7. VSE4 STRUCTURE
# ============================================================

section(
    "7. VSE4 STRUCTURAL AUDIT"
)

vse = (
    ROOT
    / "visual_selection_engine_v4.py"
)


vse_tree = None
vse_source = ""


if not vse.is_file():

    result(
        "FAIL",
        "VSE4_FILE",
        "missing",
    )

else:

    vse_source = read_text(
        vse
    )

    try:

        vse_tree = ast.parse(
            vse_source
        )

        result(
            "PASS",
            "VSE4_AST_PARSE",
            "ok",
        )

    except Exception as exc:

        result(
            "FAIL",
            "VSE4_AST_PARSE",
            f"{type(exc).__name__}: {exc}",
        )


if vse_tree is not None:

    defs = defaultdict(list)

    for node in vse_tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            defs[
                node.name
            ].append(
                node.lineno
            )


    duplicates = {
        name: lines
        for name, lines
        in defs.items()
        if len(lines) > 1
    }


    emit(
        "VSE4_DUPLICATES="
        +
        json.dumps(
            duplicates,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


    if duplicates:

        result(
            "WARN",
            "VSE4_DUPLICATE_TOPLEVEL_DEFS",
            json.dumps(
                duplicates,
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

    else:

        result(
            "PASS",
            "VSE4_DUPLICATE_TOPLEVEL_DEFS",
            "NONE",
        )


    main_lines = find_main_guard_line(
        vse_tree
    )

    emit(
        "VSE4_MAIN_GUARD_LINES="
        +
        json.dumps(
            main_lines
        )
    )


    if main_lines:

        first_main = min(
            main_lines
        )

        defs_after_main = []

        for name, lines in defs.items():

            for line in lines:

                if line > first_main:

                    defs_after_main.append(
                        (
                            line,
                            name,
                        )
                    )


        defs_after_main.sort()

        emit(
            "VSE4_DEFS_AFTER_MAIN="
            +
            json.dumps(
                defs_after_main,
                ensure_ascii=False,
            )
        )


        if defs_after_main:

            result(
                "FAIL",
                "VSE4_DEFINITIONS_AFTER_MAIN_GUARD",
                (
                    f"main_line={first_main} "
                    f"defs_after={defs_after_main[:40]}"
                ),
            )

        else:

            result(
                "PASS",
                "VSE4_DEFINITIONS_AFTER_MAIN_GUARD",
                "NONE",
            )

    else:

        result(
            "WARN",
            "VSE4_MAIN_GUARD",
            "not found",
        )


    for important in (
        "candidate_text",
        "score_candidate",
        "self_test",
        "geo_hits",
        "concept_hits",
        "objget",
    ):

        lines = defs.get(
            important,
            [],
        )

        emit(
            f"VSE4_DEF_{important}="
            f"{lines}"
        )


# ============================================================
# 8. VSE4 IMPORTED RUNTIME
# ============================================================

section(
    "8. VSE4 IMPORTED-RUNTIME TEST"
)

vse_ns = None


if vse.is_file():

    try:

        import runpy

        vse_ns = runpy.run_path(
            str(vse),
            run_name="shortautopro_general_audit_v2",
        )

        result(
            "PASS",
            "VSE4_RUNPY_LOAD",
            "loaded without __main__",
        )

    except Exception as exc:

        result(
            "FAIL",
            "VSE4_RUNPY_LOAD",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        emit(
            traceback.format_exc()
        )


if vse_ns is not None:

    for function_name in (
        "score_candidate",
        "candidate_text",
        "geo_hits",
        "concept_hits",
    ):

        fn = vse_ns.get(
            function_name
        )

        if callable(fn):

            try:

                line = inspect.getsourcelines(
                    fn
                )[1]

                emit(
                    f"VSE4_RUNTIME_{function_name}_LINE="
                    f"{line}"
                )

            except Exception:

                emit(
                    f"VSE4_RUNTIME_{function_name}_LINE="
                    "UNKNOWN"
                )

        else:

            result(
                "FAIL",
                f"VSE4_RUNTIME_{function_name}",
                "not callable",
            )


# ============================================================
# 9. VSE4 REAL QUALITY TEST
# ============================================================

section(
    "9. VSE4 QUALITY SEMANTIC TEST"
)

if vse_ns is not None:

    score = vse_ns.get(
        "score_candidate"
    )

    geo = vse_ns.get(
        "geo_hits"
    )


    scene = (
        "Investigação em apartamento "
        "na cidade de São Paulo"
    )


    wrong = {
        "provider":
            "Pixabay",

        "tipo":
            "foto",

        "title":
            "Empire State Building New York",

        "must":
            "2/2",

        "score":
            220,

        "width":
            1920,

        "height":
            1080,
    }


    correct = {
        "provider":
            "Wikimedia",

        "tipo":
            "foto",

        "title":
            "Apartment building Sao Paulo Brazil",

        "must":
            "1/2",

        "score":
            120,

        "width":
            1920,

        "height":
            1080,
    }


    state = {
        "providers": [
            "pixabay",
            "pixabay",
        ],

        "groups": [],
        "types": [],
        "keys": [],
    }


    try:

        if callable(geo):

            emit(
                "QUALITY_SCENE_GEO="
                +
                repr(
                    sorted(
                        geo(scene)
                    )
                )
            )

            emit(
                "QUALITY_WRONG_GEO="
                +
                repr(
                    sorted(
                        geo(
                            wrong["title"]
                        )
                    )
                )
            )

            emit(
                "QUALITY_CORRECT_GEO="
                +
                repr(
                    sorted(
                        geo(
                            correct["title"]
                        )
                    )
                )
            )


        a = score(
            wrong,
            scene,
            state,
        )

        b = score(
            correct,
            scene,
            state,
        )


        emit(
            "QUALITY_WRONG_RESULT="
            +
            repr(a)
        )

        emit(
            "QUALITY_CORRECT_RESULT="
            +
            repr(b)
        )


        wrong_hard = (
            isinstance(a, dict)
            and
            a.get(
                "hard_mismatch"
            )
            is True
        )

        correct_safe = (
            isinstance(b, dict)
            and
            b.get(
                "hard_mismatch"
            )
            is False
        )


        if wrong_hard:

            result(
                "PASS",
                "VSE4_SP_VS_NY_HARD_MISMATCH",
                "wrong candidate rejected",
            )

        else:

            result(
                "FAIL",
                "VSE4_SP_VS_NY_HARD_MISMATCH",
                (
                    "Empire State Building/New York "
                    "not marked hard mismatch for São Paulo"
                ),
            )


        if correct_safe:

            result(
                "PASS",
                "VSE4_SP_CORRECT_NOT_HARD",
                "São Paulo candidate accepted",
            )

        else:

            result(
                "FAIL",
                "VSE4_SP_CORRECT_NOT_HARD",
                repr(b),
            )


        try:

            ae = float(
                a.get(
                    "effective",
                    0,
                )
            )

            be = float(
                b.get(
                    "effective",
                    0,
                )
            )

            if be > ae:

                result(
                    "PASS",
                    "VSE4_CORRECT_RANKS_ABOVE_WRONG",
                    f"correct={be} wrong={ae}",
                )

            else:

                result(
                    "FAIL",
                    "VSE4_CORRECT_RANKS_ABOVE_WRONG",
                    f"correct={be} wrong={ae}",
                )

        except Exception as exc:

            result(
                "FAIL",
                "VSE4_EFFECTIVE_SCORE_COMPARE",
                str(exc),
            )


    except Exception as exc:

        result(
            "FAIL",
            "VSE4_QUALITY_RUNTIME",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        emit(
            traceback.format_exc()
        )


# ============================================================
# 10. SELF TEST IN IMPORTED RUNTIME
# ============================================================

section(
    "10. VSE4 SELF_TEST - IMPORTED RUNTIME"
)

if vse_ns is not None:

    self_test = vse_ns.get(
        "self_test"
    )

    if callable(
        self_test
    ):

        try:

            self_test()

            result(
                "PASS",
                "VSE4_IMPORTED_SELF_TEST",
                "PASS",
            )

        except AssertionError:

            result(
                "FAIL",
                "VSE4_IMPORTED_SELF_TEST",
                "AssertionError",
            )

        except Exception as exc:

            result(
                "FAIL",
                "VSE4_IMPORTED_SELF_TEST",
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

    else:

        result(
            "WARN",
            "VSE4_IMPORTED_SELF_TEST",
            "function missing",
        )


# ============================================================
# 11. SCRIPT-MODE SELF TEST
# ============================================================

section(
    "11. VSE4 SCRIPT-MODE SELF TEST"
)

if vse.is_file():

    p = subprocess.run(
        [
            sys.executable,
            str(vse),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


    emit(
        f"VSE4_SCRIPT_RETURN_CODE="
        f"{p.returncode}"
    )


    combined = (
        p.stdout
        +
        "\n"
        +
        p.stderr
    ).strip()


    emit(
        "VSE4_SCRIPT_TAIL_BEGIN"
    )

    for line in combined.splitlines()[
        -60:
    ]:

        emit(line)

    emit(
        "VSE4_SCRIPT_TAIL_END"
    )


    if p.returncode == 0:

        result(
            "PASS",
            "VSE4_SCRIPT_SELF_TEST",
            "returncode=0",
        )

    else:

        result(
            "FAIL",
            "VSE4_SCRIPT_SELF_TEST",
            f"returncode={p.returncode}",
        )


# ============================================================
# 12. SCRIPT VS IMPORT BEHAVIOR
# ============================================================

section(
    "12. SCRIPT VS IMPORT CONSISTENCY"
)

script_pass = any(
    item[
        "test"
    ]
    ==
    "VSE4_SCRIPT_SELF_TEST"
    and
    item[
        "status"
    ]
    ==
    "PASS"
    for item in results
)

import_pass = any(
    item[
        "test"
    ]
    ==
    "VSE4_IMPORTED_SELF_TEST"
    and
    item[
        "status"
    ]
    ==
    "PASS"
    for item in results
)


if script_pass == import_pass:

    result(
        "PASS",
        "VSE4_SCRIPT_IMPORT_CONSISTENCY",
        (
            f"script={script_pass} "
            f"import={import_pass}"
        ),
    )

else:

    result(
        "FAIL",
        "VSE4_SCRIPT_IMPORT_CONSISTENCY",
        (
            f"script={script_pass} "
            f"import={import_pass}; "
            "likely definitions after __main__"
        ),
    )


# ============================================================
# 13. MIDIA INTEGRATION
# ============================================================

section(
    "13. MIDIA INTEGRATION"
)

midia = (
    ROOT
    / "midia.py"
)

midia_src = read_text(
    midia
)


markers = {
    "VSE4":
        (
            "visual_selection_engine_v4"
            in midia_src
            or
            "VSE4"
            in midia_src
        ),

    "VSE3":
        (
            "visual_selection_final_gate_v3"
            in midia_src
            or
            "VSE3"
            in midia_src
        ),

    "DIVERSITY":
        (
            "media_diversity_guard_v1"
            in midia_src
        ),

    "PROVENANCE":
        (
            "media_provenance_capture_v1"
            in midia_src
        ),

    "COMMIT_LOCK":
        (
            "visual_scene_commit_lock_v1"
            in midia_src
            or
            "SCENE_COMMIT_LOCK"
            in midia_src
        ),
}


for name, present in markers.items():

    emit(
        f"MIDIA_MARKER_{name}="
        f"{'YES' if present else 'NO'}"
    )


if markers["PROVENANCE"]:

    result(
        "PASS",
        "MIDIA_PROVENANCE_INTEGRATION",
        "found",
    )

else:

    result(
        "WARN",
        "MIDIA_PROVENANCE_INTEGRATION",
        "marker not found directly",
    )


if markers["VSE4"]:

    result(
        "INFO",
        "MIDIA_VSE4_INTEGRATION",
        "marker found",
    )

else:

    result(
        "INFO",
        "MIDIA_VSE4_INTEGRATION",
        "not integrated yet",
    )


# ============================================================
# 14. PROVIDER ACQUISITION
# ============================================================

section(
    "14. PROVIDER ACQUISITION"
)

provider_functions = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
]


if midia.is_file():

    try:

        midia_tree = ast.parse(
            midia_src
        )

        fn_nodes = {
            node.name: node
            for node in midia_tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }


        for name in provider_functions:

            if name in fn_nodes:

                result(
                    "PASS",
                    f"PROVIDER_FUNCTION_{name}",
                    f"line={fn_nodes[name].lineno}",
                )

            else:

                result(
                    "FAIL",
                    f"PROVIDER_FUNCTION_{name}",
                    "missing",
                )


        buscar = fn_nodes.get(
            "buscar_todos_candidatos"
        )


        if buscar is not None:

            calls = sorted(
                call_names(
                    buscar
                )
            )

            emit(
                "BUSCAR_TODOS_CALLS="
                +
                ",".join(calls)
            )


            expected_calls = {
                "pexels_video",
                "pexels_foto",
                "pixabay_video",
                "pixabay_foto",
                "coverr_video",
            }


            missing_calls = sorted(
                expected_calls
                -
                set(calls)
            )


            if missing_calls:

                result(
                    "FAIL",
                    "PROVIDER_CALL_COVERAGE",
                    (
                        "missing="
                        +
                        ",".join(
                            missing_calls
                        )
                    ),
                )

            else:

                result(
                    "PASS",
                    "PROVIDER_CALL_COVERAGE",
                    "Pexels/Pixabay/Coverr all called",
                )


    except Exception as exc:

        result(
            "FAIL",
            "MIDIA_AST_PROVIDER_AUDIT",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


# ============================================================
# 15. RENDER CHAIN
# ============================================================

section(
    "15. EXISTING RENDER CHAIN"
)

render_files = {
    "AUDIO":
        ROOT
        / "audios"
        / f"short_{SHORT_ID}.mp3",

    "ASS":
        ROOT
        / "videos"
        / f"short_{SHORT_ID}.ass",

    "VIDEO_BASE":
        ROOT
        / "temp"
        / SHORT_ID
        / "video_sem_audio.mp4",

    "FINAL":
        ROOT
        / "videos"
        / f"short_v6_{SHORT_ID}.mp4",
}


for name, path in render_files.items():

    if (
        path.is_file()
        and
        path.stat().st_size > 0
    ):

        result(
            "PASS",
            f"RENDER_INPUT_{name}",
            (
                f"bytes={path.stat().st_size} "
                f"sha256={sha256(path)}"
            ),
        )

    else:

        status = (
            "WARN"
            if name == "FINAL"
            else
            "FAIL"
        )

        result(
            status,
            f"RENDER_INPUT_{name}",
            f"missing={path}",
        )


# ============================================================
# 16. FRESH RENDER GUARD SAFETY
# ============================================================

section(
    "16. FRESH RENDER GUARD STATIC SAFETY"
)

guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    guard_src = read_text(
        guard
    )


    protections = {
        "ASS":
            '".ass"' in guard_src,

        "MP3":
            '".mp3"' in guard_src,

        "JPG":
            '".jpg"' in guard_src,

        "JSON":
            '".json"' in guard_src,
    }


    emit(
        "GUARD_PROTECTIONS="
        +
        repr(
            protections
        )
    )


    if all(
        protections.values()
    ):

        result(
            "PASS",
            "FRESH_RENDER_GUARD_PROTECTION",
            protections,
        )

    else:

        result(
            "WARN",
            "FRESH_RENDER_GUARD_PROTECTION",
            protections,
        )

else:

    result(
        "WARN",
        "FRESH_RENDER_GUARD",
        "missing",
    )


# ============================================================
# 17. CRITICAL HISTORICAL LOG ERRORS
# ============================================================

section(
    "17. RECENT LOG ERROR SCAN"
)

log_dir = (
    ROOT
    / "logs"
    / "producao"
)


error_pattern = re.compile(
    r"Traceback|"
    r"AssertionError|"
    r"NameError|"
    r"TypeError|"
    r"KeyError|"
    r"SyntaxError|"
    r"ERRO:",
    re.I,
)


log_hits = []


if log_dir.is_dir():

    logs = sorted(
        log_dir.glob("*.log"),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:30]


    for log in logs:

        text = read_text(
            log
        )

        matches = error_pattern.findall(
            text
        )

        if matches:

            log_hits.append(
                (
                    log.name,
                    len(matches),
                )
            )


emit(
    "RECENT_LOG_ERROR_FILES="
    +
    repr(
        log_hits
    )
)


if log_hits:

    result(
        "WARN",
        "RECENT_HISTORICAL_LOG_ERRORS",
        (
            "historical logs contain errors; "
            "not automatically an active failure: "
            +
            repr(
                log_hits
            )
        ),
    )

else:

    result(
        "PASS",
        "RECENT_HISTORICAL_LOG_ERRORS",
        "none in latest logs",
    )


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

section(
    "18. FINAL SUMMARY"
)

counts = {
    key: 0
    for key in (
        "PASS",
        "WARN",
        "FAIL",
        "INFO",
    )
}


for item in results:

    counts[
        item["status"]
    ] += 1


overall = "PASS"

if counts["FAIL"]:

    overall = "FAIL"

elif counts["WARN"]:

    overall = "WARN"


for key in (
    "PASS",
    "WARN",
    "FAIL",
    "INFO",
):

    emit(
        f"{key}="
        f"{counts[key]}"
    )


emit(
    f"AUDIT_OVERALL={overall}"
)


section(
    "19. FAILURES"
)

failures = [
    item
    for item in results
    if item[
        "status"
    ]
    ==
    "FAIL"
]


if failures:

    for item in failures:

        emit(
            "FAIL | "
            f"{item['test']} | "
            f"{item['detail']}"
        )

else:

    emit(
        "FAILURES=NONE"
    )


section(
    "20. WARNINGS"
)

warnings = [
    item
    for item in results
    if item[
        "status"
    ]
    ==
    "WARN"
]


if warnings:

    for item in warnings:

        emit(
            "WARN | "
            f"{item['test']} | "
            f"{item['detail']}"
        )

else:

    emit(
        "WARNINGS=NONE"
    )


payload = {
    "short_id":
        SHORT_ID,

    "root":
        str(ROOT),

    "overall":
        overall,

    "counts":
        counts,

    "media": {
        "directory":
            str(media_dir),

        "valid":
            valid_scenes,

        "bad":
            bad_scenes,

        "hashes":
            media_hashes,
    },

    "results":
        results,
}


JSON_REPORT.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


emit()
emit(
    f"JSON_REPORT={JSON_REPORT}"
)

emit(
    "NETWORK_EXECUTED=NO"
)

emit(
    "MEDIA_DOWNLOADED=NO"
)

emit(
    "VIDEO_RENDERED=NO"
)

emit(
    "CORE_FILES_MODIFIED=NO"
)

emit(
    "GENERAL_AUDIT_V2_COMPLETE=YES"
)
