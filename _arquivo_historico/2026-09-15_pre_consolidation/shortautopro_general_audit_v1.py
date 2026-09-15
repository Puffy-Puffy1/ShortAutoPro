#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

REPORT_DIR = ROOT / "temp"
REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

STAMP = time.strftime(
    "%Y%m%d_%H%M%S"
)

REPORT = (
    REPORT_DIR
    / f"SHORTAUTOPRO_GENERAL_AUDIT_{STAMP}.txt"
)


# ============================================================
# CONFIG
# ============================================================

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "backups",
    "backup",
    "node_modules",
    "whisper.cpp",
    ".venv",
    "venv",
}


CRITICAL_FILES = (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
)


VISUAL_FILES = (
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "visual_selection_runtime_v42.py",
    "visual_engine_unified.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
)


EXPECTED_PROVIDER_FUNCTIONS = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
    "baixar_candidato_5_2",
)


COMMIT_MARKERS = (
    "commit_candidate",
    "_vse42_commit_candidate",
    "_vse42_commit_safe",
    "note_commit_runtime",
    "_sap_visual_commit",
    "note_commit",
    "VSE42_SCENE_COMMIT",
    "VSE42_FIRST_SUCCESS_LOCK",
    "VISUAL_UNIFIED_COMMIT",
    "SCENE_COMMIT_LOCK",
)


DANGEROUS_PATTERNS = (
    r"\brm\s+-rf\b",
    r"\bshutil\.rmtree\b",
    r"\.unlink\s*\(",
    r"\bos\.remove\s*\(",
)


# ============================================================
# OUTPUT
# ============================================================

LINES = []

COUNTS = Counter()


def emit(*parts):

    text = " ".join(
        str(x)
        for x in parts
    )

    print(text)

    LINES.append(text)


def section(title):

    emit()
    emit("=" * 78)
    emit(title)
    emit("=" * 78)


def finding(
    severity,
    code,
    message,
):

    severity = severity.upper()

    COUNTS[
        severity
    ] += 1

    emit(
        f"[{severity}]",
        code,
        "-",
        message,
    )


# ============================================================
# HELPERS
# ============================================================

def excluded(path: Path):

    try:

        relative = path.relative_to(
            ROOT
        )

    except Exception:

        return True


    return any(
        part in EXCLUDED_DIRS
        for part in relative.parts
    )


def read_text(path: Path):

    try:

        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception as exc:

        finding(
            "ERROR",
            "READ_ERROR",
            f"{path}: "
            f"{type(exc).__name__}: {exc}",
        )

        return ""


def parse_ast(path: Path):

    src = read_text(
        path
    )

    try:

        return (
            src,
            ast.parse(
                src,
                filename=str(path),
            ),
        )

    except SyntaxError as exc:

        finding(
            "CRITICAL",
            "PYTHON_SYNTAX",
            f"{path.name}:{exc.lineno}: "
            f"{exc.msg}",
        )

        return (
            src,
            None,
        )


def run_command(
    args,
    timeout=120,
):

    try:

        proc = subprocess.run(
            args,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )

        return (
            proc.returncode,
            proc.stdout,
        )

    except subprocess.TimeoutExpired:

        return (
            124,
            "TIMEOUT",
        )

    except Exception as exc:

        return (
            125,
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 1. PROJECT
# ============================================================

section(
    "1. PROJECT STRUCTURE"
)

emit(
    "ROOT=",
    ROOT,
)


if not ROOT.is_dir():

    finding(
        "CRITICAL",
        "ROOT_MISSING",
        str(ROOT),
    )

    raise SystemExit(1)


for name in CRITICAL_FILES:

    path = ROOT / name

    if path.is_file():

        emit(
            f"CORE_FILE=PASS {name} "
            f"bytes={path.stat().st_size}"
        )

    else:

        finding(
            "CRITICAL",
            "CORE_FILE_MISSING",
            name,
        )


# ============================================================
# 2. PYTHON SYNTAX
# ============================================================

section(
    "2. PYTHON SYNTAX - TOP LEVEL"
)


python_files = sorted(
    p
    for p in ROOT.glob("*.py")
    if p.is_file()
)


emit(
    "PYTHON_FILE_COUNT=",
    len(python_files),
)


compile_failures = []


for path in python_files:

    code, output = run_command(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(path),
        ],
        timeout=30,
    )

    if code != 0:

        compile_failures.append(
            path.name
        )

        finding(
            "CRITICAL",
            "PY_COMPILE_FAIL",
            f"{path.name}: "
            f"{output.strip()[-500:]}",
        )


if not compile_failures:

    emit(
        "PYTHON_COMPILE_ALL=PASS"
    )

else:

    emit(
        "PYTHON_COMPILE_ALL=FAIL"
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)


shell_files = sorted(
    p
    for p in ROOT.glob("*.sh")
    if p.is_file()
)


shell_failures = []


for path in shell_files:

    code, output = run_command(
        [
            "bash",
            "-n",
            str(path),
        ],
        timeout=30,
    )

    if code != 0:

        shell_failures.append(
            path.name
        )

        finding(
            "CRITICAL",
            "SHELL_SYNTAX_FAIL",
            f"{path.name}: "
            f"{output.strip()}",
        )


emit(
    "SHELL_FILE_COUNT=",
    len(shell_files),
)


if not shell_failures:

    emit(
        "SHELL_SYNTAX_ALL=PASS"
    )

else:

    emit(
        "SHELL_SYNTAX_ALL=FAIL"
    )


# ============================================================
# 4. UNREACHABLE CODE
# ============================================================

section(
    "4. UNREACHABLE / DEAD CODE AUDIT"
)


def analyze_block(
    body,
    file_name,
    scope_name,
):

    for index, stmt in enumerate(
        body
    ):

        terminator = isinstance(
            stmt,
            (
                ast.Break,
                ast.Continue,
                ast.Return,
                ast.Raise,
            ),
        )

        if (
            terminator
            and
            index + 1 < len(body)
        ):

            next_stmt = body[
                index + 1
            ]

            kind = type(
                stmt
            ).__name__

            finding(
                "ERROR",
                "UNREACHABLE_CODE",
                f"{file_name}:"
                f"{stmt.lineno} "
                f"{scope_name} -> "
                f"{kind} followed by statement "
                f"at line {next_stmt.lineno}",
            )


        nested_lists = []


        if isinstance(
            stmt,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            nested_lists.append(
                (
                    stmt.body,
                    f"{scope_name}/{stmt.name}",
                )
            )


        elif isinstance(
            stmt,
            ast.If,
        ):

            nested_lists.extend(
                [
                    (
                        stmt.body,
                        f"{scope_name}/if@{stmt.lineno}",
                    ),
                    (
                        stmt.orelse,
                        f"{scope_name}/else@{stmt.lineno}",
                    ),
                ]
            )


        elif isinstance(
            stmt,
            (
                ast.For,
                ast.AsyncFor,
                ast.While,
            ),
        ):

            nested_lists.extend(
                [
                    (
                        stmt.body,
                        f"{scope_name}/loop@{stmt.lineno}",
                    ),
                    (
                        stmt.orelse,
                        f"{scope_name}/loop_else@{stmt.lineno}",
                    ),
                ]
            )


        elif isinstance(
            stmt,
            ast.Try,
        ):

            nested_lists.append(
                (
                    stmt.body,
                    f"{scope_name}/try@{stmt.lineno}",
                )
            )

            nested_lists.append(
                (
                    stmt.orelse,
                    f"{scope_name}/try_else@{stmt.lineno}",
                )
            )

            nested_lists.append(
                (
                    stmt.finalbody,
                    f"{scope_name}/finally@{stmt.lineno}",
                )
            )

            for handler in stmt.handlers:

                nested_lists.append(
                    (
                        handler.body,
                        f"{scope_name}/except@{stmt.lineno}",
                    )
                )


        elif isinstance(
            stmt,
            ast.With,
        ):

            nested_lists.append(
                (
                    stmt.body,
                    f"{scope_name}/with@{stmt.lineno}",
                )
            )


        for child_body, child_scope in nested_lists:

            if child_body:

                analyze_block(
                    child_body,
                    file_name,
                    child_scope,
                )


for path in python_files:

    src, tree = parse_ast(
        path
    )

    if tree is None:
        continue

    analyze_block(
        tree.body,
        path.name,
        "module",
    )


# ============================================================
# 5. MIDIA.PY CONTROL FLOW
# ============================================================

section(
    "5. MIDIA.PY DOWNLOAD / COMMIT CONTROL FLOW"
)


midia = ROOT / "midia.py"

midia_src, midia_tree = parse_ast(
    midia
)


if midia_tree is not None:

    functions = {
        node.name:
            node

        for node in midia_tree.body

        if isinstance(
            node,
            ast.FunctionDef,
        )
    }


    for required in EXPECTED_PROVIDER_FUNCTIONS:

        if required in functions:

            emit(
                f"FUNCTION_PRESENT=PASS "
                f"{required} "
                f"line={functions[required].lineno}"
            )

        else:

            finding(
                "ERROR",
                "FUNCTION_MISSING",
                required,
            )


    # --------------------------------------------------------
    # Calls to downloader.
    # --------------------------------------------------------

    downloader_calls = []


    for node in ast.walk(
        midia_tree
    ):

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
            ==
            "baixar_candidato_5_2"
        ):

            downloader_calls.append(
                node.lineno
            )


    emit(
        "DOWNLOAD_CALL_COUNT=",
        len(
            downloader_calls
        ),
    )

    emit(
        "DOWNLOAD_CALL_LINES=",
        ",".join(
            str(x)
            for x in downloader_calls
        ),
    )


    # --------------------------------------------------------
    # Commit markers.
    # --------------------------------------------------------

    for marker in COMMIT_MARKERS:

        count = midia_src.count(
            marker
        )

        if count:

            emit(
                f"COMMIT_MARKER "
                f"{marker} count={count}"
            )


    commit_total = sum(
        midia_src.count(
            marker
        )
        for marker in COMMIT_MARKERS
    )


    if commit_total >= 8:

        finding(
            "WARN",
            "COMMIT_COMPLEXITY",
            f"{commit_total} commit-marker references "
            f"found in midia.py",
        )


# ============================================================
# 6. SPECIFIC FIRST-SUCCESS BUG
# ============================================================

section(
    "6. FIRST-SUCCESS LOCK AUDIT"
)


if midia_tree is not None:

    suspicious_success_blocks = 0


    for node in ast.walk(
        midia_tree
    ):

        if not isinstance(
            node,
            ast.If,
        ):
            continue


        # Detecta "if ok:"
        if not (
            isinstance(
                node.test,
                ast.Name,
            )
            and
            node.test.id == "ok"
        ):
            continue


        breaks = [
            child
            for child in node.body
            if isinstance(
                child,
                ast.Break,
            )
        ]


        if not breaks:
            continue


        first_break = min(
            x.lineno
            for x in breaks
        )


        statements_after = [
            child
            for child in node.body
            if child.lineno > first_break
        ]


        emit(
            f"IF_OK_BLOCK line={node.lineno} "
            f"first_break={first_break} "
            f"after_break={len(statements_after)}"
        )


        if statements_after:

            suspicious_success_blocks += 1

            finding(
                "CRITICAL",
                "FIRST_SUCCESS_DEAD_CODE",
                f"midia.py if-ok line {node.lineno}: "
                f"break at {first_break} leaves "
                f"{len(statements_after)} direct statements "
                f"unreachable",
            )


            for child in statements_after[:20]:

                emit(
                    f"  DEAD_STATEMENT "
                    f"line={child.lineno} "
                    f"type={type(child).__name__}"
                )


    if suspicious_success_blocks == 0:

        emit(
            "FIRST_SUCCESS_DIRECT_DEAD_CODE=NONE"
        )


# ============================================================
# 7. BREAK BEFORE DESTINO / MARCAR_USADO / COMMIT
# ============================================================

section(
    "7. SUCCESS ORDERING AUDIT"
)


if midia_tree is not None:

    lines = midia_src.splitlines()


    for call_line in downloader_calls:

        start = max(
            0,
            call_line - 5,
        )

        end = min(
            len(lines),
            call_line + 100,
        )


        window = [
            (
                idx + 1,
                lines[idx],
            )
            for idx in range(
                start,
                end,
            )
        ]


        ok_line = None


        for line_no, text in window:

            if (
                line_no > call_line
                and
                re.search(
                    r"\bif\s+ok\s*:",
                    text,
                )
            ):

                ok_line = line_no
                break


        if not ok_line:
            continue


        block_window = [
            (
                ln,
                text,
            )
            for ln, text in window
            if (
                ln >= ok_line
                and
                ln <= ok_line + 70
            )
        ]


        interesting = {}


        patterns = {
            "break":
                r"^\s*break\s*$",

            "destino":
                r"\bdestino\s*=\s*destino_teste",

            "marcar_usado":
                r"\bmarcar_usado\s*\(",

            "visual_commit":
                r"_sap_visual_commit\s*\(",

            "vse42_commit":
                r"_vse42_commit_candidate\s*\(",

            "runtime_commit":
                r"_vse42_note_commit\s*\(",

            "sibling_cleanup":
                r"_vse42_cleanup_scene_sibling\s*\(",
        }


        for label, pattern in patterns.items():

            for ln, text in block_window:

                if re.search(
                    pattern,
                    text,
                ):

                    interesting[
                        label
                    ] = ln

                    break


        emit(
            f"SUCCESS_PATH download_line={call_line} "
            f"if_ok={ok_line} "
            f"{interesting}"
        )


        first_break = interesting.get(
            "break"
        )


        if first_break:

            for label in (
                "destino",
                "marcar_usado",
                "vse42_commit",
                "runtime_commit",
                "sibling_cleanup",
            ):

                target = interesting.get(
                    label
                )

                if (
                    target
                    and
                    target > first_break
                ):

                    finding(
                        "CRITICAL",
                        "POST_BREAK_SUCCESS_LOGIC",
                        f"{label} line {target} "
                        f"occurs after break "
                        f"line {first_break}",
                    )


# ============================================================
# 8. PROVIDER ACQUISITION
# ============================================================

section(
    "8. PROVIDER ACQUISITION"
)


provider_names = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
)


if midia_tree is not None:

    buscar = None


    for node in midia_tree.body:

        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name
            ==
            "buscar_todos_candidatos"
        ):

            buscar = node
            break


    if buscar is None:

        finding(
            "CRITICAL",
            "BUSCAR_TODOS_MISSING",
            "buscar_todos_candidatos",
        )

    else:

        calls = []


        for node in ast.walk(
            buscar
        ):

            if isinstance(
                node,
                ast.Call,
            ):

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


        for provider_name in provider_names:

            found = [
                line
                for name, line in calls
                if name == provider_name
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
                )


# ============================================================
# 9. VSE FILES
# ============================================================

section(
    "9. VISUAL ENGINE FILES"
)


for name in VISUAL_FILES:

    path = ROOT / name

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
# 10. VSE4 SELF TEST
# ============================================================

section(
    "10. VSE4 SELF TEST"
)


vse4 = ROOT / "visual_selection_engine_v4.py"


if vse4.is_file():

    code, output = run_command(
        [
            sys.executable,
            str(vse4),
        ],
        timeout=60,
    )


    emit(
        "VSE4_SELF_TEST_STATUS=",
        code,
    )


    tail = "\n".join(
        output.splitlines()[-40:]
    )


    emit(
        "VSE4_SELF_TEST_TAIL_BEGIN"
    )

    emit(
        tail
    )

    emit(
        "VSE4_SELF_TEST_TAIL_END"
    )


    if code != 0:

        finding(
            "ERROR",
            "VSE4_SELF_TEST_FAIL",
            "visual_selection_engine_v4.py "
            f"returned {code}",
        )

    else:

        emit(
            "VSE4_SELF_TEST=PASS"
        )


else:

    finding(
        "WARN",
        "VSE4_MISSING",
        "visual_selection_engine_v4.py",
    )


# ============================================================
# 11. DUPLICATE FUNCTION DEFINITIONS
# ============================================================

section(
    "11. DUPLICATE DEFINITIONS"
)


for path in python_files:

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
                f"{path.name}: {name} "
                f"lines={locations}",
            )


# ============================================================
# 12. SHADOWED / MULTIPLE VISUAL ENGINES
# ============================================================

section(
    "12. VISUAL ENGINE OVERLAP"
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
                "visual" in module.casefold()
                or
                "media_diversity" in module.casefold()
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


modules = {
    module
    for module, _ in visual_imports
}


if len(
    modules
) >= 5:

    finding(
        "WARN",
        "VISUAL_ENGINE_OVERLAP",
        f"{len(modules)} visual-related modules "
        f"imported by midia.py",
    )


# ============================================================
# 13. MEDIA FOLDER INTEGRITY
# ============================================================

section(
    "13. MEDIA FOLDER INTEGRITY"
)


image_root = ROOT / "imagens"

duplicate_scene_folders = []


if image_root.is_dir():

    short_dirs = sorted(
        image_root.glob(
            "short_*"
        )
    )


    emit(
        "SHORT_MEDIA_DIR_COUNT=",
        len(short_dirs),
    )


    for directory in short_dirs:

        if not directory.is_dir():
            continue


        scene_files = defaultdict(
            list
        )


        for media in directory.glob(
            "scene_*.*"
        ):

            match = re.match(
                r"scene_(\d+)\.",
                media.name,
            )

            if not match:
                continue


            scene_files[
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
            in scene_files.items()

            if len(files) > 1
        }


        if duplicates:

            duplicate_scene_folders.append(
                directory.name
            )

            finding(
                "ERROR",
                "DUPLICATE_SCENE_MEDIA",
                f"{directory.name}: "
                +
                "; ".join(
                    f"{scene:02d}="
                    +
                    ",".join(
                        f.name
                        for f in files
                    )

                    for scene, files
                    in duplicates.items()
                ),
            )


    if not duplicate_scene_folders:

        emit(
            "DUPLICATE_SCENE_MEDIA=NONE"
        )


# ============================================================
# 14. CURRENT/LATEST MEDIA COUNT
# ============================================================

section(
    "14. LATEST MEDIA DIRECTORY"
)


if image_root.is_dir():

    dirs = [
        p
        for p in image_root.glob(
            "short_*"
        )
        if p.is_dir()
    ]


    if dirs:

        latest = max(
            dirs,
            key=lambda x:
                x.stat().st_mtime,
        )


        emit(
            "LATEST_MEDIA_DIR=",
            latest.name,
        )


        found = defaultdict(
            list
        )


        for path in latest.glob(
            "scene_*.*"
        ):

            m = re.match(
                r"scene_(\d+)\.",
                path.name,
            )

            if m:

                found[
                    int(
                        m.group(1)
                    )
                ].append(
                    path.name
                )


        emit(
            "LATEST_SCENE_NUMBERS=",
            sorted(
                found
            ),
        )


        missing = [
            n
            for n in range(
                1,
                13,
            )
            if n not in found
        ]


        if missing:

            finding(
                "ERROR",
                "LATEST_SCENES_MISSING",
                str(
                    missing
                ),
            )


        duplicates = [
            n
            for n, values
            in found.items()
            if len(values) != 1
        ]


        if duplicates:

            finding(
                "ERROR",
                "LATEST_SCENE_COUNT_INVALID",
                str(
                    duplicates
                ),
            )


# ============================================================
# 15. JSON INTEGRITY
# ============================================================

section(
    "15. JSON INTEGRITY"
)


json_roots = (
    ROOT / "roteiros",
    ROOT / "manifests",
)


json_files = []


for base in json_roots:

    if not base.is_dir():
        continue


    json_files.extend(
        [
            p
            for p in base.rglob(
                "*.json"
            )
            if (
                p.is_file()
                and not excluded(
                    p
                )
            )
        ]
    )


# Mais recentes para evitar milhares.
json_files = sorted(
    json_files,
    key=lambda x:
        x.stat().st_mtime,
    reverse=True,
)[:300]


json_bad = []


for path in json_files:

    try:

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:

            json.load(
                file
            )

    except Exception as exc:

        json_bad.append(
            path
        )

        finding(
            "ERROR",
            "INVALID_JSON",
            f"{path.relative_to(ROOT)}: "
            f"{type(exc).__name__}",
        )


emit(
    "JSON_CHECKED=",
    len(json_files),
)


if not json_bad:

    emit(
        "JSON_INTEGRITY=PASS"
    )


# ============================================================
# 16. DANGEROUS DELETE / CACHE LOGIC
# ============================================================

section(
    "16. DELETE / CACHE SAFETY"
)


for path in python_files:

    src = read_text(
        path
    )


    for pattern in DANGEROUS_PATTERNS:

        for match in re.finditer(
            pattern,
            src,
            flags=re.IGNORECASE,
        ):

            line = (
                src.count(
                    "\n",
                    0,
                    match.start(),
                )
                + 1
            )

            emit(
                f"DELETE_OPERATION "
                f"{path.name}:{line} "
                f"pattern={pattern}"
            )


guard = ROOT / "fresh_render_guard_v1.py"


if guard.is_file():

    guard_src = read_text(
        guard
    )


    if ".ass" in guard_src:

        emit(
            "RENDER_GUARD_ASS_REFERENCE=YES"
        )


    if (
        "PROTECTED_SUFFIXES"
        in guard_src
        and
        '".ass"'
        in guard_src
    ):

        emit(
            "RENDER_GUARD_ASS_PROTECTION=PASS"
        )

    elif "'.ass'" in guard_src:

        emit(
            "RENDER_GUARD_ASS_PROTECTION=POSSIBLE"
        )

    else:

        finding(
            "WARN",
            "RENDER_GUARD_ASS_UNKNOWN",
            "Unable to confirm .ass protection",
        )


# ============================================================
# 17. /tmp USAGE
# ============================================================

section(
    "17. TEMP PATH POLICY"
)


tmp_refs = []


for path in (
    python_files
    +
    shell_files
):

    src = read_text(
        path
    )


    for index, line in enumerate(
        src.splitlines(),
        start=1,
    ):

        if "/tmp" in line:

            tmp_refs.append(
                (
                    path.name,
                    index,
                    line.strip(),
                )
            )


for item in tmp_refs[:100]:

    finding(
        "WARN",
        "TMP_REFERENCE",
        f"{item[0]}:{item[1]} "
        f"{item[2][:150]}",
    )


if not tmp_refs:

    emit(
        "TMP_REFERENCES=NONE"
    )


# ============================================================
# 18. PROVIDER MONOPOLY TELEMETRY
# ============================================================

section(
    "18. PROVIDER TELEMETRY FROM LOGS"
)


logs_dir = ROOT / "logs" / "producao"

providers = Counter()


if logs_dir.is_dir():

    recent_logs = sorted(
        logs_dir.glob(
            "*.log"
        ),
        key=lambda x:
            x.stat().st_mtime,
        reverse=True,
    )[:30]


    patterns = (
        re.compile(
            r"ESCOLHIDO:\s*([^/\n]+)",
            re.I,
        ),

        re.compile(
            r"DOWNLOAD PRIORITÁRIO:\s*([^/\n]+)",
            re.I,
        ),
    )


    for log in recent_logs:

        src = read_text(
            log
        )


        for pattern in patterns:

            for match in pattern.finditer(
                src
            ):

                value = (
                    match.group(1)
                    .strip()
                    .casefold()
                )


                if value:

                    providers[
                        value
                    ] += 1


emit(
    "PROVIDER_COUNTS=",
    dict(
        providers
    ),
)


if providers:

    total = sum(
        providers.values()
    )

    top_provider, top_count = (
        providers.most_common(
            1
        )[0]
    )


    ratio = (
        top_count
        /
        total
    )


    emit(
        f"TOP_PROVIDER={top_provider} "
        f"ratio={ratio:.3f}"
    )


    if (
        total >= 12
        and
        ratio >= 0.85
    ):

        finding(
            "WARN",
            "PROVIDER_MONOPOLY",
            f"{top_provider} represents "
            f"{ratio:.1%} of logged selections",
        )


# ============================================================
# 19. MIDIA CORE HASH
# ============================================================

section(
    "19. CORE HASHES"
)


for name in CRITICAL_FILES:

    path = ROOT / name

    if not path.is_file():
        continue


    code, output = run_command(
        [
            "sha256sum",
            str(path),
        ],
        timeout=10,
    )


    if code == 0:

        emit(
            output.strip()
        )


# ============================================================
# 20. AST CONTROL-FLOW FOCUS AROUND KNOWN LINES
# ============================================================

section(
    "20. MIDIA CONTROL-FLOW CONTEXT"
)


if midia.is_file():

    lines = midia_src.splitlines()


    targets = (
        1055,
        3307,
        4519,
        4569,
        4591,
        4733,
    )


    for target in targets:

        if target > len(
            lines
        ):
            continue


        emit()
        emit(
            f"--- CONTEXT line {target} ---"
        )


        lo = max(
            1,
            target - 12,
        )

        hi = min(
            len(lines),
            target + 25,
        )


        for n in range(
            lo,
            hi + 1,
        ):

            emit(
                f"{n:05d} | "
                f"{lines[n - 1]}"
            )


# ============================================================
# 21. SUMMARY
# ============================================================

section(
    "21. FINAL SUMMARY"
)


emit(
    "CRITICAL_COUNT=",
    COUNTS[
        "CRITICAL"
    ],
)

emit(
    "ERROR_COUNT=",
    COUNTS[
        "ERROR"
    ],
)

emit(
    "WARN_COUNT=",
    COUNTS[
        "WARN"
    ],
)


if (
    COUNTS["CRITICAL"] == 0
    and
    COUNTS["ERROR"] == 0
):

    emit(
        "GENERAL_STATUS=PASS"
    )


elif COUNTS[
    "CRITICAL"
] == 0:

    emit(
        "GENERAL_STATUS=PASS_WITH_ERRORS"
    )


else:

    emit(
        "GENERAL_STATUS=FAIL"
    )


emit()
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
    "CORE_MODIFIED=NO"
)


REPORT.write_text(
    "\n".join(
        LINES
    )
    +
    "\n",
    encoding="utf-8",
)


emit()
emit(
    "REPORT=",
    REPORT,
)

emit(
    "AUDIT_COMPLETE=YES"
)
