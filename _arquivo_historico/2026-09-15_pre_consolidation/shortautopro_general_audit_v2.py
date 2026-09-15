#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import re
import runpy
import subprocess
import symtable
import sys

from collections import defaultdict
from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)

TEMP = (
    ROOT
    / "temp"
)

TEMP.mkdir(
    parents=True,
    exist_ok=True,
)


REPORT_TXT = (
    TEMP
    / "GENERAL_AUDIT_V2.txt"
)

REPORT_JSON = (
    TEMP
    / "GENERAL_AUDIT_V2.json"
)


CORE = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
]


VISUAL_FILES = [
    "visual_selection_engine_v2.py",
    "visual_selection_final_gate_v3.py",
    "visual_selection_engine_v4.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
]


PROVIDERS = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
]


lines = []

findings = []


def emit(*parts):

    text = " ".join(
        str(x)
        for x in parts
    )

    lines.append(
        text
    )

    print(
        text
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


def finding(
    level,
    code,
    detail,
    file=None,
    line=None,
):

    item = {
        "level":
            level,

        "code":
            code,

        "detail":
            detail,
    }

    if file:
        item[
            "file"
        ] = file

    if line:
        item[
            "line"
        ] = line


    findings.append(
        item
    )


    where = ""

    if file:
        where += (
            f" file={file}"
        )

    if line:
        where += (
            f" line={line}"
        )


    emit(
        f"FINDING[{level}] "
        f"{code}: "
        f"{detail}"
        f"{where}"
    )


def read_text(path):

    try:

        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception as exc:

        finding(
            "ERROR",
            "READ_FAIL",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            path.name,
        )

        return ""


def parse_ast(path):

    src = read_text(
        path
    )

    if not src:

        return (
            src,
            None,
        )


    try:

        tree = ast.parse(
            src,
            filename=str(
                path
            ),
        )

        return (
            src,
            tree,
        )


    except SyntaxError as exc:

        finding(
            "ERROR",
            "PY_SYNTAX",
            str(exc),
            path.name,
            exc.lineno,
        )

        return (
            src,
            None,
        )


def sha256(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


def run_command(
    cmd,
    timeout=30,
):

    try:

        result = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )

        return (
            result.returncode,
            result.stdout,
        )


    except subprocess.TimeoutExpired as exc:

        output = (
            exc.stdout
            or ""
        )

        return (
            124,
            str(output)
            + "\nTIMEOUT",
        )


    except Exception as exc:

        return (
            125,
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def python_files():

    return sorted(
        p
        for p in ROOT.glob(
            "*.py"
        )
        if p.name
        !=
        Path(
            __file__
        ).name
    )


def shell_files():

    result = set(
        ROOT.glob(
            "*.sh"
        )
    )

    for dirname in (
        "scripts",
        "bin",
    ):

        directory = (
            ROOT
            / dirname
        )

        if directory.is_dir():

            result.update(
                directory.rglob(
                    "*.sh"
                )
            )


    return sorted(
        result
    )


python_files_all = (
    python_files()
)

shell_files_all = (
    shell_files()
)


MIDIA = (
    ROOT
    / "midia.py"
)


if MIDIA.is_file():

    midia_src, midia_tree = (
        parse_ast(
            MIDIA
        )
    )

else:

    midia_src = ""

    midia_tree = None


# ============================================================
# 1
# ============================================================

section(
    "1. PROJECT / CORE INVENTORY"
)


emit(
    "ROOT=",
    ROOT,
)

emit(
    "PYTHON_FILES=",
    len(
        python_files_all
    ),
)

emit(
    "SHELL_FILES=",
    len(
        shell_files_all
    ),
)


for name in (
    CORE
    +
    VISUAL_FILES
):

    path = (
        ROOT
        / name
    )


    if path.is_file():

        emit(
            f"FOUND {name} "
            f"bytes={path.stat().st_size} "
            f"sha256={sha256(path)}"
        )

    else:

        finding(
            "WARN",
            "FILE_MISSING",
            name,
        )


# ============================================================
# 2
# ============================================================

section(
    "2. PYTHON SYNTAX"
)


syntax_pass = 0


for path in python_files_all:

    src = read_text(
        path
    )

    if not src:
        continue


    try:

        compile(
            src,
            str(path),
            "exec",
        )

        syntax_pass += 1


    except SyntaxError as exc:

        finding(
            "ERROR",
            "PY_SYNTAX",
            str(exc),
            path.name,
            exc.lineno,
        )


emit(
    "PYTHON_SYNTAX_PASS=",
    syntax_pass,
)

emit(
    "PYTHON_SYNTAX_TOTAL=",
    len(
        python_files_all
    ),
)


# ============================================================
# 3
# ============================================================

section(
    "3. SHELL SYNTAX"
)


for path in shell_files_all:

    code, output = run_command(
        [
            "bash",
            "-n",
            str(path),
        ],
        timeout=15,
    )


    if code == 0:

        emit(
            "SHELL_SYNTAX=PASS",
            path.relative_to(
                ROOT
            ),
        )

    else:

        finding(
            "ERROR",
            "SHELL_SYNTAX",
            output.strip()[:500],
            str(
                path.relative_to(
                    ROOT
                )
            ),
        )


# ============================================================
# 4
# ============================================================

section(
    "4. UNRESOLVED GLOBAL REFERENCES"
)


builtin_names = set(
    dir(
        builtins
    )
)


for path in python_files_all:

    src = read_text(
        path
    )

    if not src:
        continue


    try:

        table = symtable.symtable(
            src,
            str(path),
            "exec",
        )

    except Exception:
        continue


    defined = set()


    for symbol in table.get_symbols():

        if (
            symbol.is_assigned()
            or
            symbol.is_imported()
            or
            symbol.is_namespace()
        ):

            defined.add(
                symbol.get_name()
            )


    unresolved = set()


    def walk_scope(scope):

        for child in scope.get_children():

            for symbol in child.get_symbols():

                name = (
                    symbol.get_name()
                )

                if not symbol.is_referenced():
                    continue

                if not symbol.is_global():
                    continue

                if name in defined:
                    continue

                if name in builtin_names:
                    continue

                unresolved.add(
                    name
                )


            walk_scope(
                child
            )


    walk_scope(
        table
    )


    if unresolved:

        finding(
            "WARN",
            "UNRESOLVED_GLOBALS",
            ",".join(
                sorted(
                    unresolved
                )
            ),
            path.name,
        )


emit(
    "GLOBAL_REFERENCE_AUDIT=COMPLETE"
)


# ============================================================
# 5
# ============================================================

section(
    "5. LOCAL FUNCTION CALL ARITY"
)


for path in python_files_all:

    src, tree = parse_ast(
        path
    )

    if tree is None:
        continue


    definitions = {}


    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            total = (
                len(
                    node.args.posonlyargs
                )
                +
                len(
                    node.args.args
                )
            )

            defaults = len(
                node.args.defaults
            )

            minimum = max(
                0,
                total - defaults,
            )

            maximum = (
                None
                if node.args.vararg
                else total
            )


            definitions[
                node.name
            ] = (
                minimum,
                maximum,
            )


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if not isinstance(
            node.func,
            ast.Name,
        ):
            continue


        name = (
            node.func.id
        )

        if name not in definitions:
            continue


        minimum, maximum = (
            definitions[
                name
            ]
        )


        argc = len(
            node.args
        )


        if (
            argc < minimum
            or
            (
                maximum
                is not None
                and
                argc > maximum
            )
        ):

            finding(
                "WARN",
                "CALL_ARITY",
                (
                    f"{name} called "
                    f"with {argc}; "
                    f"expected "
                    f"{minimum}..{maximum}"
                ),
                path.name,
                node.lineno,
            )


# ============================================================
# 6
# ============================================================

section(
    "6. SILENT EXCEPTION / DYNAMIC CODE"
)


for path in python_files_all:

    src, tree = parse_ast(
        path
    )

    if tree is None:
        continue


    for node in ast.walk(
        tree
    ):

        if isinstance(
            node,
            ast.ExceptHandler,
        ):

            if node.type is None:

                finding(
                    "WARN",
                    "BARE_EXCEPT",
                    "bare except",
                    path.name,
                    node.lineno,
                )


            if (
                len(
                    node.body
                )
                ==
                1
                and
                isinstance(
                    node.body[0],
                    ast.Pass,
                )
            ):

                finding(
                    "WARN",
                    "EXCEPT_PASS",
                    "exception swallowed",
                    path.name,
                    node.lineno,
                )


        if (
            isinstance(
                node,
                ast.Call,
            )
            and
            isinstance(
                node.func,
                ast.Name,
            )
            and
            node.func.id
            in {
                "eval",
                "exec",
            }
        ):

            finding(
                "WARN",
                "DYNAMIC_EXEC",
                node.func.id,
                path.name,
                node.lineno,
            )


# ============================================================
# 7
# ============================================================

section(
    "7. DESTRUCTIVE FILE OPERATIONS"
)


danger_pattern = re.compile(
    r"(rmtree\s*\(|"
    r"unlink\s*\(|"
    r"os\.remove\s*\(|"
    r"os\.unlink\s*\(|"
    r"rm\s+-rf|"
    r"rm\s+-f)",
    re.I,
)


for path in (
    python_files_all
    +
    shell_files_all
):

    src = read_text(
        path
    )


    for line_number, line in enumerate(
        src.splitlines(),
        1,
    ):

        if danger_pattern.search(
            line
        ):

            finding(
                "INFO",
                "DESTRUCTIVE_OP",
                line.strip()[:220],
                path.name,
                line_number,
            )


# ============================================================
# 8
# ============================================================

section(
    "8. PROVIDER ACQUISITION"
)


provider_functions = {}


if midia_tree is None:

    finding(
        "ERROR",
        "MIDIA_PARSE_FAIL",
        "midia.py unavailable",
    )


else:

    for node in midia_tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            provider_functions[
                node.name
            ] = node


    for provider_name in PROVIDERS:

        node = provider_functions.get(
            provider_name
        )


        if node:

            emit(
                f"PROVIDER_DEF=PASS "
                f"{provider_name} "
                f"line={node.lineno}"
            )

        else:

            finding(
                "WARN",
                "PROVIDER_DEF_MISSING",
                provider_name,
                "midia.py",
            )


    search_function = (
        provider_functions.get(
            "buscar_todos_candidatos"
        )
    )


    if search_function is None:

        finding(
            "ERROR",
            "BUSCAR_TODOS_MISSING",
            "buscar_todos_candidatos",
            "midia.py",
        )


    else:

        calls = []


        for node in ast.walk(
            search_function
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

                calls.append(
                    (
                        node.func.id,
                        node.lineno,
                    )
                )


            elif isinstance(
                node.func,
                ast.Attribute,
            ):

                calls.append(
                    (
                        node.func.attr,
                        node.lineno,
                    )
                )


        for provider_name in PROVIDERS:

            found = [
                line
                for name, line
                in calls
                if name
                ==
                provider_name
            ]


            if found:

                emit(
                    f"PROVIDER_CALL=PASS "
                    f"{provider_name} "
                    f"lines={found}"
                )

            else:

                finding(
                    "ERROR",
                    "PROVIDER_NOT_CALLED",
                    provider_name,
                    "midia.py",
                )


# ============================================================
# 9
# ============================================================

section(
    "9. VISUAL ENGINE FILES"
)


for name in VISUAL_FILES:

    path = (
        ROOT
        / name
    )


    if path.is_file():

        emit(
            f"VISUAL_FILE=FOUND "
            f"{name} "
            f"bytes={path.stat().st_size}"
        )

    else:

        emit(
            f"VISUAL_FILE=MISSING "
            f"{name}"
        )


# ============================================================
# 10
# ============================================================

section(
    "10. VSE4 SELF TEST"
)


VSE4 = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if VSE4.is_file():

    code, output = run_command(
        [
            sys.executable,
            str(VSE4),
        ],
        timeout=60,
    )


    emit(
        "VSE4_SELF_TEST_STATUS=",
        code,
    )

    emit(
        "VSE4_SELF_TEST_TAIL_BEGIN"
    )

    emit(
        "\n".join(
            output.splitlines()[
                -60:
            ]
        )
    )

    emit(
        "VSE4_SELF_TEST_TAIL_END"
    )


    if code != 0:

        finding(
            "ERROR",
            "VSE4_SELF_TEST_FAIL",
            f"returned {code}",
            VSE4.name,
        )

    else:

        emit(
            "VSE4_SELF_TEST=PASS"
        )


else:

    finding(
        "WARN",
        "VSE4_MISSING",
        VSE4.name,
    )


# ============================================================
# 11
# ============================================================

section(
    "11. VSE4 GEO / HARD-MISMATCH DIRECT REGRESSION"
)


if VSE4.is_file():

    try:

        namespace = runpy.run_path(
            str(VSE4),
            run_name="general_audit_vse4",
        )


        score_candidate = (
            namespace[
                "score_candidate"
            ]
        )


        scene = (
            "Investigação em apartamento "
            "na cidade de São Paulo"
        )


        state = {
            "providers": [
                "pixabay",
                "pixabay",
            ],
            "groups": [],
            "types": [],
            "keys": [],
        }


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
                (
                    "Apartment building "
                    "Sao Paulo Brazil"
                ),

            "must":
                "1/2",

            "score":
                120,

            "width":
                1920,

            "height":
                1080,
        }


        wrong_result = (
            score_candidate(
                wrong,
                scene,
                state,
            )
        )


        correct_result = (
            score_candidate(
                correct,
                scene,
                state,
            )
        )


        emit(
            "WRONG_HARD_MISMATCH=",
            wrong_result.get(
                "hard_mismatch"
            ),
        )

        emit(
            "WRONG_EFFECTIVE=",
            wrong_result.get(
                "effective"
            ),
        )

        emit(
            "CORRECT_HARD_MISMATCH=",
            correct_result.get(
                "hard_mismatch"
            ),
        )

        emit(
            "CORRECT_EFFECTIVE=",
            correct_result.get(
                "effective"
            ),
        )


        if (
            wrong_result.get(
                "hard_mismatch"
            )
            is not True
        ):

            finding(
                "ERROR",
                "GEO_HARD_MISMATCH_FAIL",
                (
                    "São Paulo scene did not "
                    "hard-reject Empire State "
                    "Building / New York"
                ),
                VSE4.name,
            )


        if (
            correct_result.get(
                "hard_mismatch"
            )
            is True
        ):

            finding(
                "ERROR",
                "GEO_FALSE_POSITIVE",
                (
                    "São Paulo candidate "
                    "was hard-rejected"
                ),
                VSE4.name,
            )


        wrong_effective = (
            wrong_result.get(
                "effective",
                0,
            )
        )

        correct_effective = (
            correct_result.get(
                "effective",
                0,
            )
        )


        if (
            correct_effective
            <=
            wrong_effective
        ):

            finding(
                "ERROR",
                "GEO_RANKING_FAIL",
                (
                    "correct São Paulo "
                    "candidate does not outrank "
                    "New York candidate"
                ),
                VSE4.name,
            )


    except Exception as exc:

        finding(
            "ERROR",
            "VSE4_DIRECT_TEST_EXCEPTION",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
            VSE4.name,
        )


# ============================================================
# 12
# ============================================================

section(
    "12. DUPLICATE TOP-LEVEL DEFINITIONS"
)


for path in python_files_all:

    src, tree = parse_ast(
        path
    )

    if tree is None:
        continue


    names = defaultdict(
        list
    )


    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            names[
                node.name
            ].append(
                node.lineno
            )


    for name, locations in names.items():

        if len(
            locations
        ) > 1:

            finding(
                "WARN",
                "DUPLICATE_DEFINITION",
                (
                    f"{name} "
                    f"lines={locations}"
                ),
                path.name,
            )


# ============================================================
# 13
# ============================================================

section(
    "13. VISUAL ENGINE OVERLAP"
)


visual_imports = []


if midia_tree is not None:

    for node in ast.walk(
        midia_tree
    ):

        if isinstance(
            node,
            ast.ImportFrom,
        ):

            module = (
                node.module
                or ""
            )


            if (
                "visual"
                in
                module.casefold()
                or
                "media_diversity"
                in
                module.casefold()
            ):

                visual_imports.append(
                    (
                        module,
                        node.lineno,
                    )
                )


        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                module = (
                    alias.name
                )


                if (
                    "visual"
                    in
                    module.casefold()
                    or
                    "media_diversity"
                    in
                    module.casefold()
                ):

                    visual_imports.append(
                        (
                            module,
                            node.lineno,
                        )
                    )


for module, line in visual_imports:

    emit(
        f"VISUAL_IMPORT "
        f"line={line} "
        f"module={module}"
    )


visual_modules = {
    module
    for module, _
    in visual_imports
}


if len(
    visual_modules
) >= 5:

    finding(
        "WARN",
        "VISUAL_ENGINE_OVERLAP",
        (
            f"{len(visual_modules)} "
            f"visual modules "
            f"referenced by midia.py"
        ),
    )


if (
    VSE4.is_file()
    and
    "visual_selection_engine_v4"
    not in visual_modules
):

    finding(
        "WARN",
        "VSE4_NOT_ACTIVE_IN_MIDIA",
        (
            "VSE4 exists but no direct "
            "midia.py import was detected"
        ),
    )


# ============================================================
# 14
# ============================================================

section(
    "14. MEDIA FOLDER INTEGRITY"
)


IMAGE_ROOT = (
    ROOT
    / "imagens"
)


if IMAGE_ROOT.is_dir():

    short_dirs = sorted(
        [
            p
            for p in IMAGE_ROOT.glob(
                "short_*"
            )
            if p.is_dir()
        ],
        key=lambda p:
            p.stat().st_mtime,
    )

else:

    short_dirs = []


emit(
    "SHORT_MEDIA_DIR_COUNT=",
    len(
        short_dirs
    ),
)


for directory in short_dirs:

    scenes = defaultdict(
        list
    )


    for media in directory.glob(
        "scene_*.*"
    ):

        match = re.match(
            r"scene_(\d+)\.",
            media.name,
        )


        if match:

            scenes[
                int(
                    match.group(1)
                )
            ].append(
                media
            )


    duplicates = {
        scene:
            files

        for scene, files
        in scenes.items()

        if len(files) > 1
    }


    if duplicates:

        finding(
            "ERROR",
            "DUPLICATE_SCENE_MEDIA",
            (
                directory.name
                +
                ": "
                +
                "; ".join(
                    (
                        f"{scene:02d}="
                        +
                        ",".join(
                            f.name
                            for f in files
                        )
                    )
                    for scene, files
                    in duplicates.items()
                )
            ),
        )


    if scenes:

        numbers = sorted(
            scenes
        )


        expected = list(
            range(
                min(numbers),
                max(numbers) + 1,
            )
        )


        missing = [
            number
            for number in expected
            if number not in scenes
        ]


        if missing:

            finding(
                "WARN",
                "SCENE_GAPS",
                (
                    f"{directory.name}: "
                    f"{missing}"
                ),
            )


        zero_files = [
            f.name
            for files in scenes.values()
            for f in files
            if f.stat().st_size == 0
        ]


        if zero_files:

            finding(
                "ERROR",
                "ZERO_BYTE_MEDIA",
                (
                    f"{directory.name}: "
                    f"{zero_files}"
                ),
            )


        tiny_files = [
            f.name
            for files in scenes.values()
            for f in files
            if (
                f.stat().st_size
                >
                0
                and
                f.stat().st_size
                <
                2048
            )
        ]


        if tiny_files:

            finding(
                "WARN",
                "TINY_MEDIA",
                (
                    f"{directory.name}: "
                    f"{tiny_files}"
                ),
            )


# ============================================================
# 15
# ============================================================

section(
    "15. LATEST MEDIA SET"
)


latest_media_dir = (
    short_dirs[-1]
    if short_dirs
    else None
)


if latest_media_dir:

    emit(
        "LATEST_MEDIA_DIR=",
        latest_media_dir.name,
    )


    latest_scenes = defaultdict(
        list
    )


    for media in latest_media_dir.glob(
        "scene_*.*"
    ):

        match = re.match(
            r"scene_(\d+)\.",
            media.name,
        )


        if match:

            latest_scenes[
                int(
                    match.group(1)
                )
            ].append(
                media
            )


    emit(
        "LATEST_SCENES=",
        sorted(
            latest_scenes
        ),
    )


    exact = sum(
        1
        for files in latest_scenes.values()
        if len(files) == 1
    )


    emit(
        "LATEST_UNIQUE_SCENES=",
        exact,
    )


    if exact != 12:

        finding(
            "WARN",
            "LATEST_NOT_12_UNIQUE_SCENES",
            (
                f"{latest_media_dir.name}: "
                f"{exact}"
            ),
        )


else:

    finding(
        "WARN",
        "NO_MEDIA_SETS",
        "imagens/short_* not found",
    )


# ============================================================
# 16
# ============================================================

section(
    "16. LATEST MEDIA SIGNATURE / FFPROBE"
)


if latest_media_dir:

    for media in sorted(
        latest_media_dir.glob(
            "scene_*.*"
        )
    ):

        suffix = (
            media.suffix.casefold()
        )


        if suffix in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:

            try:

                header = (
                    media.read_bytes()[
                        :16
                    ]
                )


                valid = (
                    header.startswith(
                        b"\xff\xd8\xff"
                    )
                    or
                    header.startswith(
                        b"\x89PNG\r\n\x1a\n"
                    )
                    or
                    header.startswith(
                        b"RIFF"
                    )
                )


                if valid:

                    emit(
                        "IMAGE_SIGNATURE=PASS",
                        media.name,
                    )

                else:

                    finding(
                        "ERROR",
                        "IMAGE_SIGNATURE",
                        (
                            "invalid or unknown "
                            "signature"
                        ),
                        media.name,
                    )


            except Exception as exc:

                finding(
                    "ERROR",
                    "MEDIA_READ_FAIL",
                    str(exc),
                    media.name,
                )


        elif suffix in {
            ".mp4",
            ".mov",
            ".mkv",
            ".webm",
        }:

            code, output = run_command(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration,size",
                    "-of",
                    (
                        "default="
                        "noprint_wrappers=1"
                    ),
                    str(media),
                ],
                timeout=20,
            )


            if code == 0:

                emit(
                    "FFPROBE=PASS",
                    media.name,
                    output.strip().replace(
                        "\n",
                        " ",
                    ),
                )

            else:

                finding(
                    "ERROR",
                    "FFPROBE_FAIL",
                    output.strip()[:300],
                    media.name,
                )


# ============================================================
# 17
# ============================================================

section(
    "17. FRESH RENDER GUARD SAFETY"
)


GUARD = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if GUARD.is_file():

    guard_src = read_text(
        GUARD
    )


    protect_ass = (
        ".ass"
        in
        guard_src
    )

    protect_mp3 = (
        ".mp3"
        in
        guard_src
    )

    protect_wav = (
        ".wav"
        in
        guard_src
    )


    emit(
        "GUARD_ASS_REFERENCE=",
        protect_ass,
    )

    emit(
        "GUARD_MP3_REFERENCE=",
        protect_mp3,
    )

    emit(
        "GUARD_WAV_REFERENCE=",
        protect_wav,
    )


    if not (
        protect_ass
        and
        protect_mp3
        and
        protect_wav
    ):

        finding(
            "ERROR",
            "RENDER_GUARD_INPUT_PROTECTION",
            (
                "ASS/audio protection "
                "appears incomplete"
            ),
            GUARD.name,
        )


else:

    finding(
        "WARN",
        "RENDER_GUARD_MISSING",
        GUARD.name,
    )


# ============================================================
# 18
# ============================================================

section(
    "18. NETWORK SAFETY"
)


network_names = {
    "get",
    "post",
    "request",
}


for path in python_files_all:

    src, tree = parse_ast(
        path
    )

    if tree is None:
        continue


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue


        function_name = ""


        if isinstance(
            node.func,
            ast.Attribute,
        ):

            function_name = (
                node.func.attr
            )


        elif isinstance(
            node.func,
            ast.Name,
        ):

            function_name = (
                node.func.id
            )


        if function_name in network_names:

            keywords = {
                keyword.arg
                for keyword in node.keywords
                if keyword.arg
            }


            if (
                "timeout"
                not in
                keywords
            ):

                finding(
                    "WARN",
                    "NETWORK_NO_TIMEOUT",
                    function_name,
                    path.name,
                    node.lineno,
                )


        if (
            isinstance(
                node.func,
                ast.Attribute,
            )
            and
            node.func.attr
            in {
                "run",
                "Popen",
                "call",
            }
        ):

            for keyword in node.keywords:

                if (
                    keyword.arg
                    ==
                    "shell"
                    and
                    isinstance(
                        keyword.value,
                        ast.Constant,
                    )
                    and
                    keyword.value.value
                    is True
                ):

                    finding(
                        "WARN",
                        "SUBPROCESS_SHELL_TRUE",
                        "shell=True",
                        path.name,
                        node.lineno,
                    )


# ============================================================
# 19
# ============================================================

section(
    "19. ENVIRONMENT / API CONFIG"
)


env_names = set()


env_pattern = re.compile(
    r"""(?:getenv|environ\.get)\(\s*["']([A-Z0-9_]+)["']"""
)


for path in python_files_all:

    env_names.update(
        env_pattern.findall(
            read_text(
                path
            )
        )
    )


for name in sorted(
    env_names
):

    if any(
        token
        in
        name
        for token in (
            "API",
            "KEY",
            "TOKEN",
            "MODEL",
        )
    ):

        status = (
            "SET"
            if os.environ.get(
                name
            )
            else
            "UNSET"
        )


        emit(
            f"ENV {name}={status}"
        )


# ============================================================
# 20
# ============================================================

section(
    "20. VISUAL / PROVENANCE HOOK REFERENCES"
)


for target in (
    "media_provenance_capture_v1",
    "media_diversity_guard_v1",
    "visual_scene_commit_lock_v1",
):

    if target in midia_src:

        emit(
            "MIDIA_HOOK_REFERENCE=YES",
            target,
        )

    else:

        finding(
            "WARN",
            "MIDIA_HOOK_REFERENCE_MISSING",
            target,
            "midia.py",
        )


# ============================================================
# 21
# ============================================================

section(
    "21. SCENE JPG/MP4 COLLISION RISK"
)


if (
    "scene_{numero:02d}.mp4"
    in
    midia_src
    and
    "scene_{numero:02d}.jpg"
    in
    midia_src
):

    emit(
        "SCENE_DUAL_EXTENSION_OUTPUT=YES"
    )


    if (
        "visual_scene_commit_lock"
        not in
        midia_src
        and
        "SCENE_COMMIT_LOCK"
        not in
        midia_src
    ):

        finding(
            "WARN",
            "SCENE_REPLACEMENT_RISK",
            (
                "jpg/mp4 outputs coexist "
                "without direct commit-lock "
                "reference in midia.py"
            ),
        )


else:

    emit(
        "SCENE_DUAL_EXTENSION_OUTPUT="
        "NOT_DETECTED"
    )


# ============================================================
# 22
# ============================================================

section(
    "22. HARDCODED SHORT IDS"
)


short_id_pattern = re.compile(
    r"20\d{2}-\d{2}-\d{2}_\d{4}"
)


for path in (
    python_files_all
    +
    shell_files_all
):

    src = read_text(
        path
    )


    for line_number, line in enumerate(
        src.splitlines(),
        1,
    ):

        if short_id_pattern.search(
            line
        ):

            finding(
                "WARN",
                "HARDCODED_SHORT_ID",
                line.strip()[:200],
                path.name,
                line_number,
            )


# ============================================================
# 23
# ============================================================

section(
    "23. RECENT FINAL VIDEO HASHES"
)


VIDEO_DIR = (
    ROOT
    / "videos"
)


if VIDEO_DIR.is_dir():

    recent_mp4 = sorted(
        [
            p
            for p in VIDEO_DIR.glob(
                "*.mp4"
            )
            if p.is_file()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[
        :12
    ]

else:

    recent_mp4 = []


hash_groups = defaultdict(
    list
)


for video in recent_mp4:

    try:

        digest = sha256(
            video
        )


        hash_groups[
            digest
        ].append(
            video.name
        )


        emit(
            "VIDEO_HASH",
            video.name,
            digest,
        )


    except Exception as exc:

        finding(
            "WARN",
            "VIDEO_HASH_FAIL",
            str(exc),
            video.name,
        )


for digest, names in hash_groups.items():

    if len(
        names
    ) > 1:

        finding(
            "WARN",
            "DUPLICATE_FINAL_HASH",
            (
                f"{digest}: "
                f"{names}"
            ),
        )


# ============================================================
# 24
# ============================================================

section(
    "24. TODO / FIXME / DEBUG MARKERS"
)


marker_pattern = re.compile(
    r"\b("
    r"TODO|"
    r"FIXME|"
    r"HACK|"
    r"TEMPORARY|"
    r"TEMP PATCH|"
    r"DEBUG"
    r")\b",
    re.I,
)


for path in (
    python_files_all
    +
    shell_files_all
):

    src = read_text(
        path
    )


    hits = [
        (
            line_number,
            line.strip(),
        )
        for line_number, line
        in enumerate(
            src.splitlines(),
            1,
        )
        if marker_pattern.search(
            line
        )
    ]


    for line_number, text in hits[
        :20
    ]:

        finding(
            "INFO",
            "DEV_MARKER",
            text[:180],
            path.name,
            line_number,
        )


# ============================================================
# 25
# ============================================================

section(
    "25. CORE FINAL SAFETY"
)


for name in (
    "midia.py",
    "video.py",
    "v6.py",
):

    path = (
        ROOT
        / name
    )


    if not path.is_file():

        finding(
            "ERROR",
            "CORE_MISSING",
            name,
        )

        continue


    try:

        compile(
            read_text(
                path
            ),
            str(path),
            "exec",
        )


        emit(
            "CORE_COMPILE=PASS",
            name,
        )


    except SyntaxError as exc:

        finding(
            "ERROR",
            "CORE_COMPILE_FAIL",
            str(exc),
            name,
            exc.lineno,
        )


GERAR = (
    ROOT
    / "gerar_short.sh"
)


if GERAR.is_file():

    code, output = run_command(
        [
            "bash",
            "-n",
            str(GERAR),
        ],
        timeout=15,
    )


    emit(
        "GERAR_SHORT_SYNTAX=",
        code,
    )


    if code != 0:

        finding(
            "ERROR",
            "GERAR_SHORT_SYNTAX_FAIL",
            output.strip()[:500],
            GERAR.name,
        )


# ============================================================
# 26
# ============================================================

section(
    "26. FINAL SUMMARY"
)


counts = defaultdict(
    int
)


for item in findings:

    counts[
        item[
            "level"
        ]
    ] += 1


emit(
    "ERRORS=",
    counts[
        "ERROR"
    ],
)

emit(
    "WARNINGS=",
    counts[
        "WARN"
    ],
)

emit(
    "INFO=",
    counts[
        "INFO"
    ],
)


if (
    counts[
        "ERROR"
    ]
    ==
    0
    and
    counts[
        "WARN"
    ]
    ==
    0
):

    status = (
        "CLEAN"
    )


elif (
    counts[
        "ERROR"
    ]
    ==
    0
):

    status = (
        "PASS_WITH_WARNINGS"
    )


else:

    status = (
        "FAIL"
    )


emit(
    "GENERAL_AUDIT_STATUS=",
    status,
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
    "PROJECT_LOGIC_MODIFIED=NO"
)


payload = {
    "root":
        str(
            ROOT
        ),

    "status":
        status,

    "counts":
        dict(
            counts
        ),

    "findings":
        findings,
}


REPORT_TXT.write_text(
    "\n".join(
        lines
    )
    +
    "\n",
    encoding="utf-8",
)


REPORT_JSON.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    "=" * 72
)

print(
    " AUDIT COMPLETE"
)

print(
    "=" * 72
)

print(
    f"REPORT_TXT={REPORT_TXT}"
)

print(
    f"REPORT_JSON={REPORT_JSON}"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
