#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"
TEMP = ROOT / "temp"
LOGS = ROOT / "logs" / "producao"

REPORT = TEMP / "MASTER_AUDIT_REPORT_V2.txt"

TEMP.mkdir(
    parents=True,
    exist_ok=True,
)

LOGS.mkdir(
    parents=True,
    exist_ok=True,
)


PASS_COUNT = 0
WARN_COUNT = 0
FAIL_COUNT = 0
INFO_COUNT = 0

FAILURES = []
WARNINGS = []


def section(title):
    print()
    print("=" * 76)
    print(title)
    print("=" * 76)


def PASS(name, detail=""):
    global PASS_COUNT
    PASS_COUNT += 1

    if detail:
        print(f"PASS | {name} | {detail}")
    else:
        print(f"PASS | {name}")


def WARN(name, detail=""):
    global WARN_COUNT
    WARN_COUNT += 1

    text = (
        f"WARN | {name}"
        + (
            f" | {detail}"
            if detail
            else ""
        )
    )

    print(text)
    WARNINGS.append(text)


def FAIL(name, detail=""):
    global FAIL_COUNT
    FAIL_COUNT += 1

    text = (
        f"FAIL | {name}"
        + (
            f" | {detail}"
            if detail
            else ""
        )
    )

    print(text)
    FAILURES.append(text)


def INFO(name, detail=""):
    global INFO_COUNT
    INFO_COUNT += 1

    if detail != "":
        print(f"INFO | {name} | {detail}")
    else:
        print(f"INFO | {name}")


def source_text(path):
    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def python_compile(path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return (
        result.returncode,
        result.stdout,
        result.stderr,
    )


def shell_syntax(path):
    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return (
        result.returncode,
        result.stdout,
        result.stderr,
    )


def ffprobe_duration(path):
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()

        return float(out)

    except Exception:
        return None


def parse_ast(path):
    try:
        src = source_text(path)

        return (
            ast.parse(src),
            src,
            None,
        )

    except Exception as exc:
        return (
            None,
            "",
            exc,
        )


def latest_short_id():

    env = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if env:
        return env


    images = ROOT / "imagens"

    candidates = []

    if images.is_dir():

        for p in images.glob(
            "short_*"
        ):

            if not p.is_dir():
                continue

            sid = p.name[
                len("short_"):
            ]

            try:
                mt = p.stat().st_mtime
            except Exception:
                mt = 0

            candidates.append(
                (
                    mt,
                    sid,
                )
            )


    if candidates:

        candidates.sort(
            reverse=True
        )

        return candidates[0][1]


    return ""


def candidate_scene_files(media_dir):

    result = defaultdict(
        list
    )

    if not media_dir.is_dir():
        return result


    rx = re.compile(
        r"^scene_(\d{2})\.(.+)$",
        re.I,
    )


    for p in media_dir.iterdir():

        if not p.is_file():
            continue

        m = rx.match(
            p.name
        )

        if not m:
            continue

        result[
            int(
                m.group(1)
            )
        ].append(
            p
        )


    return result


# ============================================================
# HEADER
# ============================================================

section(
    "SHORTAUTOPRO MASTER AUDIT V2"
)

INFO(
    "DATE",
    time.strftime(
        "%Y-%m-%d %H:%M:%S"
    ),
)

INFO(
    "ROOT",
    str(ROOT),
)

INFO(
    "PYTHON",
    sys.version.replace(
        "\n",
        " ",
    ),
)


if ROOT.is_dir():
    PASS(
        "PROJECT_ROOT",
        str(ROOT),
    )
else:
    FAIL(
        "PROJECT_ROOT",
        "missing",
    )


# ============================================================
# 1. DISK
# ============================================================

section(
    "1. STORAGE"
)


try:

    usage = shutil.disk_usage(
        ROOT
    )

    free_gb = (
        usage.free
        /
        1024
        /
        1024
        /
        1024
    )

    INFO(
        "FREE_GB",
        f"{free_gb:.2f}",
    )


    if free_gb >= 1.0:

        PASS(
            "DISK_FREE",
            f"{free_gb:.2f} GB",
        )

    elif free_gb >= 0.4:

        WARN(
            "DISK_FREE",
            f"low: {free_gb:.2f} GB",
        )

    else:

        FAIL(
            "DISK_FREE",
            f"critical: {free_gb:.2f} GB",
        )


except Exception as exc:

    WARN(
        "DISK_CHECK",
        str(exc),
    )


# ============================================================
# 2. CORE FILES
# ============================================================

section(
    "2. CORE FILES"
)


core_files = [
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_provenance_capture_v1.py",
    "media_diversity_guard_v1.py",
    "visual_selection_engine_v4.py",
    "visual_scene_commit_lock_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


for name in core_files:

    path = ROOT / name

    if path.is_file():

        PASS(
            f"CORE_{name}",
            f"{path.stat().st_size} bytes",
        )

        try:

            INFO(
                f"HASH_{name}",
                sha256(path),
            )

        except Exception as exc:

            WARN(
                f"HASH_{name}",
                str(exc),
            )

    else:

        FAIL(
            f"CORE_{name}",
            "missing",
        )


# ============================================================
# 3. ROOT PYTHON COMPILE
# ============================================================

section(
    "3. PYTHON COMPILE"
)


py_files = sorted(
    ROOT.glob(
        "*.py"
    )
)


compile_failed = []


for path in py_files:

    code, out, err = python_compile(
        path
    )

    if code == 0:

        PASS(
            f"COMPILE_{path.name}",
        )

    else:

        FAIL(
            f"COMPILE_{path.name}",
            err.strip()[
                :500
            ],
        )

        compile_failed.append(
            path.name
        )


INFO(
    "ROOT_PY_COUNT",
    len(py_files),
)


if compile_failed:

    FAIL(
        "PYTHON_COMPILE_SUMMARY",
        compile_failed,
    )

else:

    PASS(
        "PYTHON_COMPILE_SUMMARY",
        f"{len(py_files)} files",
    )


# ============================================================
# 4. SHELL SYNTAX
# ============================================================

section(
    "4. SHELL SYNTAX"
)


sh_files = sorted(
    ROOT.glob(
        "*.sh"
    )
)


shell_failed = []


for path in sh_files:

    code, out, err = shell_syntax(
        path
    )

    if code == 0:

        PASS(
            f"SHELL_{path.name}",
        )

    else:

        FAIL(
            f"SHELL_{path.name}",
            err.strip()[
                :500
            ],
        )

        shell_failed.append(
            path.name
        )


INFO(
    "ROOT_SH_COUNT",
    len(sh_files),
)


# ============================================================
# 5. HARDCODED SHORT IDS
# ============================================================

section(
    "5. HARDCODED SHORT-ID AUDIT"
)


hard_id_rx = re.compile(
    r"20\d{2}-\d{2}-\d{2}_\d{4}"
)


hardcoded_targets = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "legenda_dinamica.py",
]


hardcoded_found = []


for name in hardcoded_targets:

    path = ROOT / name

    if not path.is_file():
        continue

    src = source_text(
        path
    )

    matches = sorted(
        set(
            hard_id_rx.findall(
                src
            )
        )
    )

    if matches:

        WARN(
            f"HARDCODED_ID_{name}",
            matches,
        )

        hardcoded_found.extend(
            (
                name,
                m,
            )
            for m in matches
        )

    else:

        PASS(
            f"HARDCODED_ID_{name}",
            "none",
        )


# ============================================================
# 6. SHORT_ID RESOLUTION
# ============================================================

section(
    "6. SHORT_ID RESOLUTION"
)


for name in (
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
):

    path = ROOT / name

    if not path.is_file():
        continue

    src = source_text(
        path
    )


    if (
        'os.getenv(' in src
        and
        '"SHORT_ID"' in src
    ):

        PASS(
            f"SHORT_ID_ENV_{name}",
        )

    else:

        WARN(
            f"SHORT_ID_ENV_{name}",
            "explicit env resolver not obvious",
        )


# ============================================================
# 7. DUPLICATE TOP-LEVEL FUNCTIONS
# ============================================================

section(
    "7. DUPLICATE FUNCTION DEFINITIONS"
)


for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "visual_selection_engine_v4.py",
):

    path = ROOT / name

    if not path.is_file():
        continue


    tree, src, error = parse_ast(
        path
    )


    if error:

        FAIL(
            f"AST_{name}",
            str(error),
        )

        continue


    funcs = [
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]


    duplicates = sorted(
        name_
        for name_, count
        in Counter(funcs).items()
        if count > 1
    )


    if duplicates:

        WARN(
            f"DUPLICATE_FUNCTIONS_{name}",
            duplicates,
        )

    else:

        PASS(
            f"DUPLICATE_FUNCTIONS_{name}",
            "none",
        )


# ============================================================
# 8. VSE4 STATIC FOUNDATION
# ============================================================

section(
    "8. VSE4 STATIC FOUNDATION"
)


vse = ROOT / "visual_selection_engine_v4.py"


required_vse_functions = {
    "norm",
    "objget",
    "number",
    "provider",
    "source_group",
    "media_type",
    "candidate_key",
    "base_score",
    "must_tier",
    "flatten_candidates",
    "concept_hits",
    "geo_hits",
    "candidate_text",
    "tokens",
    "score_candidate",
    "self_test",
}


if vse.is_file():

    tree, src, error = parse_ast(
        vse
    )


    if error:

        FAIL(
            "VSE4_AST",
            str(error),
        )

    else:

        funcs = {
            node.name
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }


        missing = sorted(
            required_vse_functions
            -
            funcs
        )


        if missing:

            FAIL(
                "VSE4_REQUIRED_FUNCTIONS",
                missing,
            )

        else:

            PASS(
                "VSE4_REQUIRED_FUNCTIONS",
                len(required_vse_functions),
            )


        for global_name in (
            "CONCEPTS",
            "GEO_GROUPS",
            "GENERIC_LIFESTYLE",
            "MEDICINE_TERMS",
            "STOP",
        ):

            if re.search(
                rf"^{re.escape(global_name)}\s*=",
                src,
                re.M,
            ):

                PASS(
                    f"VSE4_GLOBAL_{global_name}",
                )

            else:

                FAIL(
                    f"VSE4_GLOBAL_{global_name}",
                    "missing",
                )


# ============================================================
# 9. VSE4 SELF TEST
# ============================================================

section(
    "9. VSE4 RUNTIME SELF TEST"
)


if vse.is_file():

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(vse),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
        )


        output = result.stdout or ""


        INFO(
            "VSE4_SELF_TEST_EXIT",
            result.returncode,
        )


        if result.returncode == 0:

            PASS(
                "VSE4_SELF_TEST",
            )

        else:

            FAIL(
                "VSE4_SELF_TEST",
                "runtime assertion/exception",
            )


        print(
            "----- VSE4 SELF TEST TAIL -----"
        )

        print(
            "\n".join(
                output.splitlines()[
                    -50:
                ]
            )
        )


    except subprocess.TimeoutExpired:

        FAIL(
            "VSE4_SELF_TEST",
            "timeout > 60s",
        )


    except Exception as exc:

        FAIL(
            "VSE4_SELF_TEST",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


# ============================================================
# 10. VSE4 GEO CONTRADICTION DIRECT TEST
# ============================================================

section(
    "10. VSE4 GEO CONTRADICTION"
)


if vse.is_file():

    try:

        ns = runpy.run_path(
            str(vse),
            run_name="master_audit_vse4",
        )


        score_candidate = ns.get(
            "score_candidate"
        )


        if callable(
            score_candidate
        ):

            scene = (
                "Investigação em apartamento "
                "na cidade de São Paulo"
            )


            wrong = {
                "provider": "Pixabay",
                "tipo": "foto",
                "title":
                    "Empire State Building New York",
                "must": "2/2",
                "score": 220,
                "width": 1920,
                "height": 1080,
            }


            correct = {
                "provider": "Wikimedia",
                "tipo": "foto",
                "title":
                    "Apartment building Sao Paulo Brazil",
                "must": "1/2",
                "score": 120,
                "width": 1920,
                "height": 1080,
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


            a = score_candidate(
                wrong,
                scene,
                state,
            )

            b = score_candidate(
                correct,
                scene,
                state,
            )


            INFO(
                "WRONG_HARD_MISMATCH",
                a.get(
                    "hard_mismatch"
                ),
            )

            INFO(
                "WRONG_EFFECTIVE",
                a.get(
                    "effective"
                ),
            )

            INFO(
                "CORRECT_HARD_MISMATCH",
                b.get(
                    "hard_mismatch"
                ),
            )

            INFO(
                "CORRECT_EFFECTIVE",
                b.get(
                    "effective"
                ),
            )


            if (
                a.get(
                    "hard_mismatch"
                )
                is True
            ):

                PASS(
                    "GEO_WRONG_BLOCKED",
                )

            else:

                FAIL(
                    "GEO_WRONG_BLOCKED",
                    (
                        "São Paulo scene accepted "
                        "New York candidate"
                    ),
                )


            if (
                b.get(
                    "hard_mismatch"
                )
                is False
            ):

                PASS(
                    "GEO_CORRECT_ALLOWED",
                )

            else:

                FAIL(
                    "GEO_CORRECT_ALLOWED",
                    b,
                )


            try:

                if (
                    float(
                        b.get(
                            "effective",
                            -999999,
                        )
                    )
                    >
                    float(
                        a.get(
                            "effective",
                            999999,
                        )
                    )
                ):

                    PASS(
                        "GEO_CORRECT_RANKS_HIGHER",
                    )

                else:

                    FAIL(
                        "GEO_CORRECT_RANKS_HIGHER",
                        (
                            f"wrong={a.get('effective')} "
                            f"correct={b.get('effective')}"
                        ),
                    )

            except Exception as exc:

                FAIL(
                    "GEO_EFFECTIVE_COMPARE",
                    str(exc),
                )


        else:

            FAIL(
                "VSE4_SCORE_CANDIDATE",
                "not callable",
            )


    except Exception as exc:

        FAIL(
            "VSE4_GEO_RUNTIME",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


# ============================================================
# 11. PROVIDER ACQUISITION MAP
# ============================================================

section(
    "11. PROVIDER ACQUISITION MAP"
)


midia = ROOT / "midia.py"


expected_provider_functions = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}


midia_src = ""


if midia.is_file():

    tree, midia_src, error = parse_ast(
        midia
    )


    if error:

        FAIL(
            "MIDIA_AST",
            str(error),
        )

    else:

        funcs = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }


        for name in sorted(
            expected_provider_functions
        ):

            node = funcs.get(
                name
            )

            if node is not None:

                PASS(
                    f"PROVIDER_FUNCTION_{name}",
                    (
                        f"line={node.lineno} "
                        f"end={node.end_lineno}"
                    ),
                )

            else:

                FAIL(
                    f"PROVIDER_FUNCTION_{name}",
                    "missing",
                )


        buscar = funcs.get(
            "buscar_todos_candidatos"
        )


        if buscar is None:

            FAIL(
                "BUSCAR_TODOS_CANDIDATOS",
                "missing",
            )

        else:

            calls = set()


            for node in ast.walk(
                buscar
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

                    calls.add(
                        node.func.id
                    )


            INFO(
                "BUSCAR_TODOS_CALLS",
                sorted(
                    calls
                ),
            )


            missing_calls = (
                expected_provider_functions
                -
                calls
            )


            if missing_calls:

                FAIL(
                    "PROVIDER_CALL_COVERAGE",
                    sorted(
                        missing_calls
                    ),
                )

            else:

                PASS(
                    "PROVIDER_CALL_COVERAGE",
                    (
                        "Pexels video/photo + "
                        "Pixabay video/photo + "
                        "Coverr video"
                    ),
                )


# ============================================================
# 12. PROVIDER CONFIG PRESENCE
# ============================================================

section(
    "12. PROVIDER CONFIG PRESENCE"
)


config_keys = set()

config = ROOT / "config.env"


if config.is_file():

    for line in source_text(
        config
    ).splitlines():

        line = line.strip()

        if (
            not line
            or
            line.startswith("#")
            or
            "=" not in line
        ):
            continue

        key = line.split(
            "=",
            1,
        )[0].strip()

        config_keys.add(
            key
        )


    PASS(
        "CONFIG_ENV",
        (
            f"{len(config_keys)} "
            "variable names"
        ),
    )

else:

    WARN(
        "CONFIG_ENV",
        "not found",
    )


provider_config_names = sorted(
    key
    for key in (
        config_keys
        |
        set(
            os.environ.keys()
        )
    )
    if any(
        word in key.upper()
        for word in (
            "PEXELS",
            "PIXABAY",
            "COVERR",
        )
    )
)


INFO(
    "PROVIDER_CONFIG_NAMES",
    provider_config_names,
)


# ============================================================
# 13. VSE INTEGRATION INTO MIDIA
# ============================================================

section(
    "13. VSE -> MIDIA INTEGRATION"
)


if midia_src:

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

        "COMMIT_LOCK":
            (
                "SCENE_COMMIT_LOCK"
                in midia_src
                or
                "visual_scene_commit_lock"
                in midia_src
            ),

        "PROVENANCE":
            (
                "media_provenance_capture"
                in midia_src
                or
                "PROVENANCE"
                in midia_src
            ),
    }


    for name, present in (
        markers.items()
    ):

        if present:

            PASS(
                f"MIDIA_MARKER_{name}",
            )

        else:

            if name == "VSE4":

                WARN(
                    f"MIDIA_MARKER_{name}",
                    (
                        "VSE4 not clearly wired "
                        "into active midia.py"
                    ),
                )

            else:

                INFO(
                    f"MIDIA_MARKER_{name}",
                    "not directly present",
                )


# ============================================================
# 14. COMMIT LOCK
# ============================================================

section(
    "14. SCENE COMMIT LOCK"
)


lock_path = (
    ROOT
    / "visual_scene_commit_lock_v1.py"
)


if lock_path.is_file():

    lock_src = source_text(
        lock_path
    )


    if (
        "COMMITTED"
        in lock_src
        and
        "BLOCKED"
        in lock_src
    ):

        PASS(
            "COMMIT_LOCK_TELEMETRY",
        )

    else:

        WARN(
            "COMMIT_LOCK_TELEMETRY",
            (
                "COMMITTED/BLOCKED "
                "markers incomplete"
            ),
        )


    if (
        "SAP_SCENE_COMMIT_LOCK"
        in lock_src
    ):

        PASS(
            "COMMIT_LOCK_KILL_SWITCH",
        )

    else:

        WARN(
            "COMMIT_LOCK_KILL_SWITCH",
            "missing",
        )

else:

    FAIL(
        "SCENE_COMMIT_LOCK_MODULE",
        "missing",
    )


# ============================================================
# 15. FRESH RENDER GUARD SYNTHETIC TEST
# ============================================================

section(
    "15. FRESH RENDER GUARD SAFETY"
)


guard_path = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard_path.is_file():

    sid_guard = (
        "MASTER_AUDIT_GUARD_"
        f"{os.getpid()}"
    )


    temp_dir = (
        ROOT
        / "temp"
        / sid_guard
    )


    video_dir = (
        ROOT
        / "videos"
    )


    temp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    video_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    ass = (
        video_dir
        / f"short_{sid_guard}.ass"
    )


    audio = (
        temp_dir
        / "protected.mp3"
    )


    base_video = (
        temp_dir
        / "video_sem_audio.mp4"
    )


    final_video = (
        video_dir
        / f"short_v6_{sid_guard}.mp4"
    )


    try:

        ass.write_text(
            "ASS_PROTECTED",
            encoding="utf-8",
        )


        audio.write_bytes(
            b"AUDIO_PROTECTED"
        )


        base_video.write_bytes(
            b"VIDEO_DISPOSABLE"
        )


        final_video.write_bytes(
            b"FINAL_DISPOSABLE"
        )


        guard_ns = runpy.run_path(
            str(
                guard_path
            ),
            run_name="fresh_guard_master_test",
        )


        clean = guard_ns.get(
            "clean"
        )


        if not callable(
            clean
        ):

            FAIL(
                "FRESH_GUARD_CLEAN",
                "not callable",
            )

        else:

            clean(
                sid_guard
            )


            checks = {

                "ASS_PROTECTED":
                    ass.exists(),

                "AUDIO_PROTECTED":
                    audio.exists(),

                "BASE_VIDEO_REMOVED":
                    not base_video.exists(),

                "FINAL_VIDEO_REMOVED":
                    not final_video.exists(),
            }


            for name, ok in (
                checks.items()
            ):

                if ok:

                    PASS(
                        f"FRESH_GUARD_{name}",
                    )

                else:

                    FAIL(
                        f"FRESH_GUARD_{name}",
                    )


    except Exception as exc:

        FAIL(
            "FRESH_GUARD_RUNTIME",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


    finally:

        try:
            ass.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        try:
            final_video.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

else:

    FAIL(
        "FRESH_RENDER_GUARD",
        "missing",
    )


# ============================================================
# 16. CURRENT SHORT
# ============================================================

section(
    "16. CURRENT SHORT"
)


sid = latest_short_id()


if sid:

    INFO(
        "CURRENT_SHORT_ID",
        sid,
    )

else:

    WARN(
        "CURRENT_SHORT_ID",
        "not found",
    )


# ============================================================
# 17. CURRENT MEDIA SET
# ============================================================

section(
    "17. CURRENT MEDIA SET"
)


if sid:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{sid}"
    )


    INFO(
        "MEDIA_DIR",
        str(media_dir),
    )


    if media_dir.is_dir():

        scenes = candidate_scene_files(
            media_dir
        )


        total_files = sum(
            len(v)
            for v in scenes.values()
        )


        INFO(
            "MEDIA_TOTAL",
            total_files,
        )


        exact_12 = True

        hashes = defaultdict(
            list
        )


        for n in range(
            1,
            13,
        ):

            files = scenes.get(
                n,
                [],
            )


            if len(files) == 1:

                p = files[0]

                try:
                    size = p.stat().st_size
                except Exception:
                    size = 0


                if size > 0:

                    PASS(
                        f"SCENE_{n:02d}",
                        (
                            f"{p.name} "
                            f"{size} bytes"
                        ),
                    )

                else:

                    FAIL(
                        f"SCENE_{n:02d}",
                        "zero-byte media",
                    )

                    exact_12 = False


                try:

                    h = sha256(
                        p
                    )

                    hashes[
                        h
                    ].append(
                        p.name
                    )

                except Exception as exc:

                    WARN(
                        f"SCENE_HASH_{n:02d}",
                        str(exc),
                    )


            elif len(files) == 0:

                FAIL(
                    f"SCENE_{n:02d}",
                    "missing",
                )

                exact_12 = False


            else:

                FAIL(
                    f"SCENE_{n:02d}",
                    (
                        "multiple media: "
                        +
                        ",".join(
                            p.name
                            for p in files
                        )
                    ),
                )

                exact_12 = False


        extras = sorted(
            n
            for n in scenes
            if n < 1
            or n > 12
        )


        if extras:

            WARN(
                "EXTRA_SCENE_NUMBERS",
                extras,
            )


        if (
            exact_12
            and
            total_files == 12
        ):

            PASS(
                "MEDIA_STRUCTURE",
                "12 scenes / one media each",
            )

        else:

            FAIL(
                "MEDIA_STRUCTURE",
                (
                    f"files={total_files}"
                ),
            )


        duplicate_hashes = {
            h: names
            for h, names
            in hashes.items()
            if len(names) > 1
        }


        if duplicate_hashes:

            WARN(
                "EXACT_MEDIA_DUPLICATES",
                duplicate_hashes,
            )

        else:

            PASS(
                "EXACT_MEDIA_DUPLICATES",
                "none",
            )


    else:

        FAIL(
            "MEDIA_DIR",
            "missing",
        )


# ============================================================
# 18. AUDIO / ASS / VIDEO BASE / FINAL
# ============================================================

section(
    "18. CURRENT RENDER INPUTS / OUTPUT"
)


if sid:

    expected = {

        "AUDIO":
            (
                ROOT
                / "audios"
                / f"short_{sid}.mp3"
            ),

        "ASS":
            (
                ROOT
                / "videos"
                / f"short_{sid}.ass"
            ),

        "VIDEO_BASE":
            (
                ROOT
                / "temp"
                / sid
                / "video_sem_audio.mp4"
            ),

        "FINAL":
            (
                ROOT
                / "videos"
                / f"short_v6_{sid}.mp4"
            ),
    }


    for name, path in (
        expected.items()
    ):

        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            PASS(
                name,
                (
                    f"{path.stat().st_size} "
                    f"bytes | {path}"
                ),
            )

        else:

            if name == "FINAL":

                WARN(
                    name,
                    f"not present | {path}",
                )

            else:

                WARN(
                    name,
                    f"missing | {path}",
                )


    audio = expected[
        "AUDIO"
    ]


    base = expected[
        "VIDEO_BASE"
    ]


    final = expected[
        "FINAL"
    ]


    ad = (
        ffprobe_duration(audio)
        if audio.is_file()
        else None
    )


    bd = (
        ffprobe_duration(base)
        if base.is_file()
        else None
    )


    fd = (
        ffprobe_duration(final)
        if final.is_file()
        else None
    )


    INFO(
        "AUDIO_DURATION",
        ad,
    )

    INFO(
        "BASE_DURATION",
        bd,
    )

    INFO(
        "FINAL_DURATION",
        fd,
    )


    if (
        ad is not None
        and
        bd is not None
    ):

        delta = abs(
            ad - bd
        )


        if delta <= 1.0:

            PASS(
                "AUDIO_BASE_DURATION_SYNC",
                f"delta={delta:.3f}s",
            )

        else:

            WARN(
                "AUDIO_BASE_DURATION_SYNC",
                f"delta={delta:.3f}s",
            )


# ============================================================
# 19. ASS STRUCTURE
# ============================================================

section(
    "19. SUBTITLE STRUCTURE"
)


if sid:

    ass = (
        ROOT
        / "videos"
        / f"short_{sid}.ass"
    )


    if ass.is_file():

        text = source_text(
            ass
        )


        events = sum(
            1
            for line in text.splitlines()
            if line.startswith(
                "Dialogue:"
            )
        )


        INFO(
            "ASS_EVENTS",
            events,
        )


        if (
            "[Events]" in text
            and
            events > 0
        ):

            PASS(
                "ASS_STRUCTURE",
                f"{events} events",
            )

        else:

            FAIL(
                "ASS_STRUCTURE",
                "invalid/empty",
            )

    else:

        WARN(
            "ASS_STRUCTURE",
            "ASS missing",
        )


# ============================================================
# 20. JSON VALIDITY
# ============================================================

section(
    "20. CURRENT JSON VALIDITY"
)


if sid:

    json_candidates = []


    for folder in (
        ROOT / "roteiros",
        ROOT / "manifests",
    ):

        if not folder.is_dir():
            continue

        json_candidates.extend(
            folder.glob(
                f"*{sid}*.json"
            )
        )


    bad_json = []


    for path in sorted(
        set(
            json_candidates
        )
    ):

        try:

            json.loads(
                source_text(
                    path
                )
            )

            PASS(
                f"JSON_{path.name}",
            )

        except Exception as exc:

            FAIL(
                f"JSON_{path.name}",
                str(exc),
            )

            bad_json.append(
                path.name
            )


    INFO(
        "CURRENT_JSON_COUNT",
        len(
            json_candidates
        ),
    )


# ============================================================
# 21. PROVENANCE
# ============================================================

section(
    "21. PROVENANCE"
)


prov_module = (
    ROOT
    / "media_provenance_capture_v1.py"
)


if prov_module.is_file():

    PASS(
        "PROVENANCE_MODULE",
    )

else:

    FAIL(
        "PROVENANCE_MODULE",
        "missing",
    )


prov_dir = (
    ROOT
    / "manifests"
    / "source_provenance_live"
)


if prov_dir.is_dir():

    jsons = list(
        prov_dir.rglob(
            "*.json"
        )
    )


    INFO(
        "LIVE_PROVENANCE_JSON_COUNT",
        len(jsons),
    )


    if jsons:

        PASS(
            "LIVE_PROVENANCE_STORE",
        )

    else:

        WARN(
            "LIVE_PROVENANCE_STORE",
            "empty",
        )

else:

    WARN(
        "LIVE_PROVENANCE_STORE",
        "directory missing",
    )


# ============================================================
# 22. ACTIVE LOG MEDIA DISTRIBUTION
# ============================================================

section(
    "22. MEDIA PROVIDER DISTRIBUTION"
)


if sid:

    candidate_logs = sorted(
        LOGS.glob(
            f"*{sid}*.log"
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


    provider_counts = Counter()


    for path in candidate_logs[:10]:

        text = source_text(
            path
        )


        for line in text.splitlines():

            m = re.search(
                r"ESCOLHIDO:\s*([^/]+?)\s*/",
                line,
                re.I,
            )

            if m:

                provider_counts[
                    m.group(1).strip().lower()
                ] += 1


    INFO(
        "PROVIDER_COUNTS_FROM_LOGS",
        dict(
            provider_counts
        ),
    )


    if provider_counts:

        if (
            len(provider_counts) == 1
            and
            sum(
                provider_counts.values()
            ) >= 8
        ):

            WARN(
                "PROVIDER_MONOCULTURE",
                dict(
                    provider_counts
                ),
            )

        else:

            PASS(
                "PROVIDER_VARIETY",
                dict(
                    provider_counts
                ),
            )

    else:

        INFO(
            "PROVIDER_VARIETY",
            "no chosen-provider lines found",
        )


# ============================================================
# 23. /tmp REFERENCES
# ============================================================

section(
    "23. TEMP PATH AUDIT"
)


tmp_refs = []


for name in (
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
):

    path = ROOT / name

    if not path.is_file():
        continue

    src = source_text(
        path
    )


    if "/tmp/" in src:

        tmp_refs.append(
            name
        )


if tmp_refs:

    WARN(
        "SYSTEM_TMP_REFERENCES",
        tmp_refs,
    )

else:

    PASS(
        "SYSTEM_TMP_REFERENCES",
        "none in core",
    )


# ============================================================
# 24. CORE SAFETY
# ============================================================

section(
    "24. CORE SAFETY SUMMARY"
)


if not compile_failed:

    PASS(
        "PYTHON_CORE_COMPILE",
    )

else:

    FAIL(
        "PYTHON_CORE_COMPILE",
        compile_failed,
    )


if not shell_failed:

    PASS(
        "SHELL_CORE_SYNTAX",
    )

else:

    FAIL(
        "SHELL_CORE_SYNTAX",
        shell_failed,
    )


# ============================================================
# 25. FINAL REPORT
# ============================================================

section(
    "MASTER AUDIT FINAL RESULT"
)


print(
    f"PASS_COUNT={PASS_COUNT}"
)

print(
    f"WARN_COUNT={WARN_COUNT}"
)

print(
    f"FAIL_COUNT={FAIL_COUNT}"
)

print(
    f"INFO_COUNT={INFO_COUNT}"
)


print()
print(
    "===== FAILURES ====="
)


if FAILURES:

    for item in FAILURES:
        print(item)

else:

    print(
        "NONE"
    )


print()
print(
    "===== WARNINGS ====="
)


if WARNINGS:

    for item in WARNINGS:
        print(item)

else:

    print(
        "NONE"
    )


print()


if FAIL_COUNT == 0:

    if WARN_COUNT == 0:

        print(
            "MASTER_AUDIT_STATUS=CERTIFIED"
        )

    else:

        print(
            "MASTER_AUDIT_STATUS=PASS_WITH_WARNINGS"
        )

else:

    print(
        "MASTER_AUDIT_STATUS=FAIL"
    )


print(
    "NETWORK_EXECUTED=NO"
)

print(
    "MEDIA_DOWNLOADED=NO"
)

print(
    "VIDEO_RENDERED=NO"
)

print(
    "CORE_FILES_MODIFIED=NO"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
