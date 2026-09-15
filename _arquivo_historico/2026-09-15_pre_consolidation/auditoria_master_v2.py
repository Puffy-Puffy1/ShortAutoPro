#!/usr/bin/env python3

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

REPORT = (
    ROOT
    / "temp"
    / "AUDITORIA_MASTER_V2.txt"
)

SUMMARY = (
    ROOT
    / "temp"
    / "AUDITORIA_MASTER_V2_SUMMARY.json"
)


PASS_COUNT = 0
WARN_COUNT = 0
FAIL_COUNT = 0

RESULTS = []


EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "backups",
    "temp",
    ".venv",
    "venv",
}


CORE_FILES = [
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


def emit(text=""):

    print(
        text,
        flush=True,
    )


def section(title):

    emit()
    emit(
        "=" * 72
    )
    emit(
        title
    )
    emit(
        "=" * 72
    )


def record(
    level,
    code,
    detail="",
):

    global PASS_COUNT
    global WARN_COUNT
    global FAIL_COUNT

    if level == "PASS":
        PASS_COUNT += 1

    elif level == "WARN":
        WARN_COUNT += 1

    elif level == "FAIL":
        FAIL_COUNT += 1


    RESULTS.append(
        {
            "level": level,
            "code": code,
            "detail": str(detail),
        }
    )


    if detail:

        emit(
            f"{level} | {code} | {detail}"
        )

    else:

        emit(
            f"{level} | {code}"
        )


def sha256(path):

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


def active_files(pattern):

    result = []

    for path in ROOT.rglob(pattern):

        try:
            rel = path.relative_to(
                ROOT
            )

        except Exception:
            continue


        if any(
            part in EXCLUDED_DIRS
            for part in rel.parts
        ):
            continue


        if path.is_file():

            result.append(
                path
            )


    return sorted(result)


def run_process(
    name,
    command,
    timeout=60,
):

    emit(
        f"RUN_START={name}"
    )

    emit(
        "COMMAND="
        +
        " ".join(
            str(x)
            for x in command
        )
    )


    started = time.time()


    try:

        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "PYTHONUNBUFFERED": "1",
                "SAP_NO_PUBLISH": "1",
            },
        )


        elapsed = (
            time.time()
            -
            started
        )


        emit(
            f"RUN_SECONDS={elapsed:.2f}"
        )

        emit(
            f"RUN_STATUS={result.returncode}"
        )


        if result.stdout:

            emit(
                result.stdout[-12000:]
            )


        return {
            "status":
                result.returncode,

            "timeout":
                False,

            "seconds":
                elapsed,

            "output":
                result.stdout or "",
        }


    except subprocess.TimeoutExpired as exc:

        elapsed = (
            time.time()
            -
            started
        )


        output = ""

        if exc.stdout:

            if isinstance(
                exc.stdout,
                bytes,
            ):

                output = exc.stdout.decode(
                    errors="replace"
                )

            else:

                output = exc.stdout


        emit(
            f"RUN_TIMEOUT={name}"
        )

        emit(
            f"RUN_SECONDS={elapsed:.2f}"
        )


        if output:

            emit(
                output[-12000:]
            )


        return {
            "status":
                124,

            "timeout":
                True,

            "seconds":
                elapsed,

            "output":
                output,
        }


def parse_python_file(path):

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    return ast.parse(
        text
    )


# ============================================================
# 1. PROJECT INVENTORY
# ============================================================

section(
    "1. PROJECT INVENTORY"
)


py_files = active_files(
    "*.py"
)

sh_files = active_files(
    "*.sh"
)


emit(
    f"ACTIVE_PY_FILES={len(py_files)}"
)

emit(
    f"ACTIVE_SH_FILES={len(sh_files)}"
)


for name in CORE_FILES:

    path = ROOT / name

    if path.is_file():

        record(
            "PASS",
            "CORE_PRESENT",
            name,
        )

    else:

        record(
            "FAIL",
            "CORE_MISSING",
            name,
        )


# ============================================================
# 2. ALL PYTHON SYNTAX
# ============================================================

section(
    "2. PYTHON SYNTAX"
)


syntax_bad = []


for path in py_files:

    rel = path.relative_to(
        ROOT
    )

    try:

        parse_python_file(
            path
        )

    except Exception as exc:

        syntax_bad.append(
            (
                str(rel),
                type(exc).__name__,
                str(exc),
            )
        )


if syntax_bad:

    for item in syntax_bad:

        record(
            "FAIL",
            "PY_SYNTAX",
            " | ".join(item),
        )

else:

    record(
        "PASS",
        "PYTHON_PROJECT_SYNTAX",
        f"{len(py_files)} files",
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)


shell_bad = []


for path in sh_files:

    rel = path.relative_to(
        ROOT
    )

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


    if result.returncode != 0:

        shell_bad.append(
            (
                str(rel),
                result.stderr.strip(),
            )
        )


if shell_bad:

    for path, error in shell_bad:

        record(
            "FAIL",
            "SH_SYNTAX",
            f"{path} | {error}",
        )

else:

    record(
        "PASS",
        "SHELL_PROJECT_SYNTAX",
        f"{len(sh_files)} files",
    )


# ============================================================
# 4. DUPLICATE TOP-LEVEL FUNCTIONS
# ============================================================

section(
    "4. DUPLICATE FUNCTION DEFINITIONS"
)


duplicate_total = 0


for path in py_files:

    try:

        tree = parse_python_file(
            path
        )

    except Exception:
        continue


    funcs = {}

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            funcs.setdefault(
                node.name,
                []
            ).append(
                node.lineno
            )


    duplicated = {
        name: lines
        for name, lines
        in funcs.items()
        if len(lines) > 1
    }


    if duplicated:

        duplicate_total += len(
            duplicated
        )

        for name, lines in duplicated.items():

            record(
                "WARN",
                "DUPLICATE_FUNCTION",
                (
                    f"{path.relative_to(ROOT)} "
                    f"{name} lines={lines}"
                ),
            )


if duplicate_total == 0:

    record(
        "PASS",
        "DUPLICATE_FUNCTIONS",
        "none",
    )


# ============================================================
# 5. DANGEROUS PATTERN AUDIT
# ============================================================

section(
    "5. DANGEROUS PATTERNS"
)


patterns = {

    "SHELL_TRUE":
        re.compile(
            r"shell\s*=\s*True"
        ),

    "OS_SYSTEM":
        re.compile(
            r"\bos\.system\s*\("
        ),

    "BARE_EXCEPT":
        re.compile(
            r"^\s*except\s*:\s*$",
            re.MULTILINE,
        ),

    "EVAL":
        re.compile(
            r"\beval\s*\("
        ),

    "EXEC":
        re.compile(
            r"\bexec\s*\("
        ),

    "HARDCODED_TMP":
        re.compile(
            r"""['"]/tmp/"""
        ),

}


danger_count = 0


for path in py_files:

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    rel = path.relative_to(
        ROOT
    )


    for code, regex in patterns.items():

        matches = list(
            regex.finditer(
                text
            )
        )


        if not matches:
            continue


        # eval/exec may be intentional in auditors/testing.
        level = (
            "WARN"
            if code in {
                "EVAL",
                "EXEC",
            }
            else
            "WARN"
        )


        for match in matches[:10]:

            line = (
                text.count(
                    "\n",
                    0,
                    match.start(),
                )
                +
                1
            )

            record(
                level,
                code,
                f"{rel}:{line}",
            )

            danger_count += 1


if danger_count == 0:

    record(
        "PASS",
        "DANGEROUS_PATTERN_SCAN",
        "clean",
    )


# ============================================================
# 6. TOP-LEVEL SYS.EXIT
# ============================================================

section(
    "6. TOP LEVEL SYS.EXIT AUDIT"
)


top_exit = 0


for path in py_files:

    try:

        tree = parse_python_file(
            path
        )

    except Exception:
        continue


    for node in tree.body:

        found = False

        for child in ast.walk(
            node
        ):

            if not isinstance(
                child,
                ast.Call,
            ):
                continue


            func = child.func


            if (
                isinstance(
                    func,
                    ast.Attribute,
                )
                and
                isinstance(
                    func.value,
                    ast.Name,
                )
                and
                func.value.id == "sys"
                and
                func.attr == "exit"
            ):

                # Function definitions aren't immediate execution.
                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.ClassDef,
                    ),
                ):

                    continue


                found = True
                break


        if found:

            top_exit += 1

            record(
                "WARN",
                "TOP_LEVEL_SYS_EXIT",
                (
                    f"{path.relative_to(ROOT)}:"
                    f"{node.lineno}"
                ),
            )


if top_exit == 0:

    record(
        "PASS",
        "TOP_LEVEL_SYS_EXIT",
        "none",
    )


# ============================================================
# 7. VSE4 STATIC GLOBAL AUDIT
# ============================================================

section(
    "7. VSE4 STATIC CHECK"
)


vse = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if vse.is_file():

    result = run_process(
        "VSE4_SELF_TEST",
        [
            sys.executable,
            "-u",
            str(vse),
        ],
        timeout=60,
    )


    if result[
        "timeout"
    ]:

        record(
            "FAIL",
            "VSE4_TIMEOUT",
            f"{result['seconds']:.1f}s",
        )


    elif result[
        "status"
    ] == 0:

        record(
            "PASS",
            "VSE4_SELF_TEST",
        )


    else:

        record(
            "FAIL",
            "VSE4_SELF_TEST",
            f"exit={result['status']}",
        )


else:

    record(
        "FAIL",
        "VSE4_MISSING",
    )


# ============================================================
# 8. MIDIA INTEGRATION MAP
# ============================================================

section(
    "8. MEDIA ACQUISITION / VSE MAP"
)


midia = ROOT / "midia.py"


if midia.is_file():

    text = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )


    required_names = [
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
        "buscar_todos_candidatos",
        "baixar_candidato_5_2",
    ]


    for name in required_names:

        found = bool(
            re.search(
                rf"def\s+{re.escape(name)}\s*\(",
                text,
            )
        )


        record(
            "PASS" if found else "FAIL",
            "MEDIA_FUNCTION",
            name,
        )


    for marker in [
        "visual_selection_engine_v4",
        "VSE4",
        "SAP_VSE_V4",
    ]:

        if marker in text:

            record(
                "PASS",
                "MIDIA_VSE4_MARKER",
                marker,
            )

        else:

            record(
                "WARN",
                "MIDIA_VSE4_MARKER_MISSING",
                marker,
            )


# ============================================================
# 9. CURRENT SHORT MEDIA STRUCTURE
# ============================================================

section(
    "9. CURRENT SHORT MEDIA STRUCTURE"
)


short_ids = []


image_root = (
    ROOT
    / "imagens"
)


if image_root.is_dir():

    for path in image_root.glob(
        "short_*"
    ):

        if path.is_dir():

            short_ids.append(
                path.name[
                    len("short_"):
                ]
            )


short_ids.sort(
    key=lambda sid: (
        image_root
        / f"short_{sid}"
    ).stat().st_mtime,
    reverse=True,
)


if short_ids:

    sid = short_ids[0]

    emit(
        f"LATEST_MEDIA_SHORT_ID={sid}"
    )

    folder = (
        image_root
        / f"short_{sid}"
    )


    invalid = 0


    for n in range(
        1,
        13,
    ):

        files = list(
            folder.glob(
                f"scene_{n:02d}.*"
            )
        )


        emit(
            f"SCENE_{n:02d}_COUNT={len(files)}"
        )


        if len(files) != 1:

            invalid += 1


    if invalid:

        record(
            "FAIL",
            "MEDIA_SCENE_STRUCTURE",
            f"invalid={invalid}",
        )

    else:

        record(
            "PASS",
            "MEDIA_SCENE_STRUCTURE",
            "12/12 unique",
        )


else:

    record(
        "WARN",
        "NO_MEDIA_SHORT_FOUND",
    )


# ============================================================
# 10. ORPHAN / DUPLICATE SCENE EXTENSIONS
# ============================================================

section(
    "10. DUPLICATE SCENE FILES"
)


duplicate_scenes = 0


if image_root.is_dir():

    for folder in image_root.glob(
        "short_*"
    ):

        if not folder.is_dir():
            continue


        by_scene = {}


        for path in folder.glob(
            "scene_*.*"
        ):

            stem = path.stem

            by_scene.setdefault(
                stem,
                []
            ).append(
                path
            )


        for stem, items in by_scene.items():

            if len(items) > 1:

                duplicate_scenes += 1

                record(
                    "WARN",
                    "DUPLICATE_SCENE_ASSET",
                    (
                        f"{folder.name}/{stem} "
                        f"count={len(items)}"
                    ),
                )


if duplicate_scenes == 0:

    record(
        "PASS",
        "DUPLICATE_SCENE_ASSETS",
        "none",
    )


# ============================================================
# 11. RENDER INPUT RELATIONSHIP
# ============================================================

section(
    "11. RENDER PIPELINE CONTRACT"
)


checks = {

    "VIDEO_SHORT_ID":
        (
            "SHORT_ID"
            in
            (
                ROOT
                / "video.py"
            ).read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
        if (
            ROOT
            / "video.py"
        ).is_file()
        else False,

    "V6_SHORT_ID":
        (
            "SHORT_ID"
            in
            (
                ROOT
                / "v6.py"
            ).read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
        if (
            ROOT
            / "v6.py"
        ).is_file()
        else False,

    "V6_ASS":
        (
            ".ass"
            in
            (
                ROOT
                / "v6.py"
            ).read_text(
                encoding="utf-8",
                errors="replace",
            )
        )
        if (
            ROOT
            / "v6.py"
        ).is_file()
        else False,

}


for name, ok in checks.items():

    record(
        "PASS" if ok else "FAIL",
        name,
    )


# ============================================================
# 12. FRESH RENDER GUARD SAFETY
# ============================================================

section(
    "12. FRESH RENDER GUARD SAFETY"
)


guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    text = guard.read_text(
        encoding="utf-8",
        errors="replace",
    )


    if (
        ".ass"
        in text
        and
        "PROTECTED_SUFFIXES"
        in text
    ):

        record(
            "PASS",
            "RENDER_GUARD_ASS_PROTECTION",
        )

    else:

        record(
            "WARN",
            "RENDER_GUARD_ASS_PROTECTION",
            "protection marker not obvious",
        )


    if (
        "video_sem_audio.mp4"
        in text
    ):

        record(
            "PASS",
            "RENDER_GUARD_TEMP_VIDEO",
        )

    else:

        record(
            "WARN",
            "RENDER_GUARD_TEMP_VIDEO",
        )


else:

    record(
        "WARN",
        "RENDER_GUARD_MISSING",
    )


# ============================================================
# 13. RECENT LOG FAILURES
# ============================================================

section(
    "13. RECENT LOG FAILURE SCAN"
)


log_root = (
    ROOT
    / "logs"
)


error_regex = re.compile(
    (
        r"traceback|"
        r"exception|"
        r"fatal|"
        r"segmentation|"
        r"\berro:|"
        r"\berror:|"
        r"status=fail|"
        r"certified=fail"
    ),
    re.IGNORECASE,
)


recent_errors = 0


if log_root.is_dir():

    now = time.time()

    for path in log_root.rglob("*"):

        if not path.is_file():
            continue


        try:

            if (
                now
                -
                path.stat().st_mtime
                >
                3 * 86400
            ):

                continue


            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )


        except Exception:
            continue


        matches = list(
            error_regex.finditer(
                text
            )
        )


        if matches:

            recent_errors += 1

            last = matches[-1]

            line = (
                text.count(
                    "\n",
                    0,
                    last.start(),
                )
                +
                1
            )


            record(
                "WARN",
                "RECENT_LOG_ERROR",
                (
                    f"{path.relative_to(ROOT)}:"
                    f"{line}"
                ),
            )


if recent_errors == 0:

    record(
        "PASS",
        "RECENT_LOG_FAILURE_SCAN",
        "none",
    )


# ============================================================
# 14. CORE HASHES
# ============================================================

section(
    "14. CORE HASHES"
)


hashes = {}


for name in CORE_FILES:

    path = ROOT / name

    if not path.is_file():
        continue


    try:

        digest = sha256(
            path
        )

        hashes[
            name
        ] = digest

        emit(
            f"HASH={digest} | {name}"
        )


    except Exception as exc:

        record(
            "WARN",
            "HASH_ERROR",
            f"{name}: {exc}",
        )


# ============================================================
# 15. LEGACY AUDITOR - BOUNDED
# ============================================================

section(
    "15. LEGACY AUDITOR WATCHDOG"
)


legacy = (
    ROOT
    / "auditoria_geral_extra_v1.py"
)


if legacy.is_file():

    result = run_process(
        "LEGACY_AUDITOR",
        [
            sys.executable,
            "-u",
            str(legacy),
        ],
        timeout=300,
    )


    if result[
        "timeout"
    ]:

        record(
            "WARN",
            "LEGACY_AUDITOR_TIMEOUT",
            (
                f"{result['seconds']:.1f}s; "
                "see last output above"
            ),
        )


    elif result[
        "status"
    ] == 0:

        record(
            "PASS",
            "LEGACY_AUDITOR",
        )


    else:

        record(
            "WARN",
            "LEGACY_AUDITOR_EXIT",
            result[
                "status"
            ],
        )


else:

    record(
        "WARN",
        "LEGACY_AUDITOR_MISSING",
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

section(
    "FINAL SUMMARY"
)


emit(
    f"PASS_COUNT={PASS_COUNT}"
)

emit(
    f"WARN_COUNT={WARN_COUNT}"
)

emit(
    f"FAIL_COUNT={FAIL_COUNT}"
)


if FAIL_COUNT == 0:

    if WARN_COUNT == 0:

        status = (
            "CERTIFIED_CLEAN"
        )

    else:

        status = (
            "PASS_WITH_WARNINGS"
        )

else:

    status = (
        "FAIL_ACTION_REQUIRED"
    )


emit(
    f"GENERAL_STATUS={status}"
)


summary = {

    "status":
        status,

    "pass":
        PASS_COUNT,

    "warn":
        WARN_COUNT,

    "fail":
        FAIL_COUNT,

    "core_hashes":
        hashes,

    "results":
        RESULTS,

    "safety": {

        "network_media_download":
            False,

        "video_render":
            False,

        "media_selection":
            False,

        "intentional_project_mutation":
            False,
    },
}


SUMMARY.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


emit(
    f"SUMMARY_JSON={SUMMARY}"
)

emit(
    "NETWORK_MEDIA_DOWNLOAD=NO"
)

emit(
    "VIDEO_RENDER=NO"
)

emit(
    "MEDIA_SELECTION=NO"
)

emit(
    "PROJECT_FILES_INTENTIONALLY_MODIFIED=NO"
)

emit(
    "AUDIT_MASTER_COMPLETE=YES"
)
