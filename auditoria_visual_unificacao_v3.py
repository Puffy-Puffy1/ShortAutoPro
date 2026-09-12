#!/usr/bin/env python3

from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess
import sys
import symtable


ROOT = Path.home() / "ShortAutoPro"

MIDIA = ROOT / "midia.py"
VSE = ROOT / "visual_selection_engine_v4.py"
GERAR = ROOT / "gerar_short.sh"

REPORT = ROOT / "temp" / "AUDITORIA_VISUAL_UNIFICACAO_V3.txt"
REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

out = []


def emit(*items):

    text = " ".join(
        str(x)
        for x in items
    )

    print(text)
    out.append(text)


def section(title):

    emit()
    emit("=" * 78)
    emit(title)
    emit("=" * 78)


def read(path):

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def sha(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def parse(path):

    return ast.parse(
        read(path),
        filename=str(path),
    )


def enclosing_function(tree, line):

    best = None

    for node in ast.walk(tree):

        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        start = node.lineno
        end = getattr(
            node,
            "end_lineno",
            start,
        )

        if start <= line <= end:

            if (
                best is None
                or
                start >= best[1]
            ):
                best = (
                    node.name,
                    start,
                    end,
                )

    return (
        best[0]
        if best
        else "<module>"
    )


# ============================================================
# 1. CORE BASELINE
# ============================================================

section(
    "1. CORE BASELINE"
)

for path in (
    MIDIA,
    VSE,
    GERAR,
):

    if path.is_file():

        emit(
            "FOUND="
            + path.name,
            "bytes="
            + str(path.stat().st_size),
            "sha256="
            + sha(path),
        )

    else:

        emit(
            "MISSING="
            + path.name
        )


# ============================================================
# 2. DUPLICATE DEFINITIONS - VSE
# ============================================================

section(
    "2. ALL DUPLICATE FUNCTIONS IN VSE4"
)

vse_src = read(VSE)
vse_tree = parse(VSE)

definitions = {}

for node in vse_tree.body:

    if not isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):
        continue

    definitions.setdefault(
        node.name,
        [],
    ).append(node)


duplicates = {
    name: nodes
    for name, nodes
    in definitions.items()
    if len(nodes) > 1
}


emit(
    "TOTAL_TOP_LEVEL_FUNCTIONS=",
    sum(
        len(v)
        for v
        in definitions.values()
    ),
)

emit(
    "UNIQUE_FUNCTION_NAMES=",
    len(definitions),
)

emit(
    "DUPLICATE_FUNCTION_NAMES=",
    len(duplicates),
)


for name in sorted(duplicates):

    nodes = duplicates[name]

    emit()
    emit(
        f"DUPLICATE_FUNCTION={name} "
        f"count={len(nodes)}"
    )

    hashes = []

    for index, node in enumerate(
        nodes,
        start=1,
    ):

        dumped = ast.dump(
            node,
            include_attributes=False,
        )

        ahash = hashlib.sha256(
            dumped.encode()
        ).hexdigest()[:16]

        hashes.append(
            ahash
        )

        emit(
            f"  DEF#{index} "
            f"lines={node.lineno}-"
            f"{node.end_lineno} "
            f"ast_hash={ahash} "
            f"effective="
            f"{index == len(nodes)}"
        )

    emit(
        "  IDENTICAL_BODIES="
        +
        (
            "YES"
            if len(set(hashes)) == 1
            else "NO"
        )
    )


# ============================================================
# 3. SCORE_CANDIDATE CALL GRAPH
# ============================================================

section(
    "3. SCORE_CANDIDATE CALL GRAPH"
)

calls = []

for node in ast.walk(vse_tree):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    name = None

    if isinstance(
        node.func,
        ast.Name,
    ):
        name = node.func.id

    elif isinstance(
        node.func,
        ast.Attribute,
    ):
        name = node.func.attr

    if name != "score_candidate":
        continue

    calls.append(
        (
            node.lineno,
            enclosing_function(
                vse_tree,
                node.lineno,
            ),
        )
    )


emit(
    "SCORE_CANDIDATE_CALL_COUNT=",
    len(calls),
)

for line, fn in sorted(calls):

    emit(
        f"CALL line={line} "
        f"function={fn}"
    )


# ============================================================
# 4. REFERENCES TO SCORE_CANDIDATE ACROSS PROJECT
# ============================================================

section(
    "4. PROJECT-WIDE SCORE_CANDIDATE REFERENCES"
)

project_refs = []

for path in ROOT.glob("*.py"):

    try:
        text = read(path)
    except Exception:
        continue

    if "score_candidate" not in text:
        continue

    for n, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        if "score_candidate" in line:

            project_refs.append(
                (
                    path.name,
                    n,
                    line.strip(),
                )
            )


emit(
    "PROJECT_SCORE_REFERENCES=",
    len(project_refs),
)

for file_name, line, text in project_refs:

    emit(
        f"{file_name}:{line}: "
        f"{text[:180]}"
    )


# ============================================================
# 5. MIDIA CONTROL FLOW
# ============================================================

section(
    "5. MIDIA VISUAL CONTROL FLOW"
)

midia_src = read(MIDIA)
midia_tree = parse(MIDIA)
midia_lines = midia_src.splitlines()

visual_patterns = (
    "VSE4",
    "VSE42",
    "VSE417",
    "VISUAL_UNIFIED",
    "SCENE_COMMIT",
    "FINAL_POOL",
    "score_candidate",
    "visual_selection",
    "visual_runtime",
)


visual_lines = []

for n, text in enumerate(
    midia_lines,
    start=1,
):

    if any(
        pattern in text
        for pattern
        in visual_patterns
    ):

        visual_lines.append(n)


emit(
    "VISUAL_RELATED_LINES=",
    len(visual_lines),
)


# Agrupa blocos próximos.
groups = []

for line in visual_lines:

    if (
        not groups
        or
        line - groups[-1][-1] > 12
    ):
        groups.append(
            [line]
        )
    else:
        groups[-1].append(
            line
        )


emit(
    "VISUAL_BLOCK_GROUPS=",
    len(groups),
)


for index, group in enumerate(
    groups,
    start=1,
):

    lo = max(
        1,
        group[0] - 4,
    )

    hi = min(
        len(midia_lines),
        group[-1] + 4,
    )

    emit()
    emit(
        f"--- VISUAL BLOCK #{index} "
        f"lines={lo}-{hi} ---"
    )

    for line in range(
        lo,
        hi + 1,
    ):

        emit(
            f"{line:05d}: "
            f"{midia_lines[line - 1]}"
        )


# ============================================================
# 6. DOWNLOAD FUNCTION INVENTORY
# ============================================================

section(
    "6. DOWNLOAD CALL INVENTORY"
)

download_calls = []

for node in ast.walk(midia_tree):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    called = None

    if isinstance(
        node.func,
        ast.Name,
    ):

        called = node.func.id

    elif isinstance(
        node.func,
        ast.Attribute,
    ):

        called = node.func.attr


    if not called:
        continue


    lower = called.casefold()

    if (
        "baixar" in lower
        or
        "download" in lower
    ):

        download_calls.append(
            (
                node.lineno,
                called,
                enclosing_function(
                    midia_tree,
                    node.lineno,
                ),
            )
        )


emit(
    "DOWNLOAD_CALL_COUNT=",
    len(download_calls),
)

for line, name, fn in sorted(
    download_calls
):

    emit(
        f"DOWNLOAD line={line} "
        f"name={name} "
        f"function={fn}"
    )


# ============================================================
# 7. BREAK / SUCCESS CONTROL
# ============================================================

section(
    "7. DOWNLOAD SUCCESS / BREAK FORENSICS"
)

target_download_lines = [
    line
    for line, name, fn
    in download_calls
    if name == "baixar_candidato_5_2"
]


for dl in target_download_lines:

    lo = max(
        1,
        dl - 12,
    )

    hi = min(
        len(midia_lines),
        dl + 45,
    )

    emit()
    emit(
        f"--- DOWNLOAD PATH "
        f"line={dl} ---"
    )

    for line in range(
        lo,
        hi + 1,
    ):

        text = midia_lines[
            line - 1
        ]

        marker = ""

        if "break" in text:
            marker += " <BREAK>"

        if "continue" in text:
            marker += " <CONTINUE>"

        if "if ok" in text:
            marker += " <SUCCESS_CHECK>"

        if "COMMIT" in text.upper():
            marker += " <COMMIT>"

        emit(
            f"{line:05d}: "
            f"{text}"
            f"{marker}"
        )


# ============================================================
# 8. FLAGS AND ENV CONTROL
# ============================================================

section(
    "8. VISUAL FLAGS"
)

flag_names = (
    "SAP_VSE4",
    "SAP_VSE42",
    "SAP_VSE4_RUNTIME",
    "SAP_SCENE_COMMIT_LOCK",
)


for flag in flag_names:

    matches = []

    for n, line in enumerate(
        read(GERAR).splitlines(),
        start=1,
    ):

        if flag in line:
            matches.append(
                (
                    n,
                    line.strip(),
                )
            )

    emit(
        f"{flag}_REFERENCES="
        f"{len(matches)}"
    )

    for n, text in matches:

        emit(
            f"  line={n} "
            f"{text}"
        )


# ============================================================
# 9. TOP-LEVEL SIDE EFFECTS IN VSE
# ============================================================

section(
    "9. VSE4 TOP-LEVEL SIDE EFFECT AUDIT"
)

side_effect_calls = []

safe_top_calls = {
    "Path",
    "set",
    "dict",
    "list",
    "tuple",
}


for node in vse_tree.body:

    if not isinstance(
        node,
        ast.Expr,
    ):
        continue

    call = node.value

    if not isinstance(
        call,
        ast.Call,
    ):
        continue

    try:
        name = ast.unparse(
            call.func
        )
    except Exception:
        name = "UNKNOWN"


    if name in safe_top_calls:
        continue

    side_effect_calls.append(
        (
            node.lineno,
            name,
        )
    )


emit(
    "VSE_TOP_LEVEL_CALLS=",
    len(side_effect_calls),
)

for line, name in side_effect_calls:

    emit(
        f"TOP_LEVEL_CALL "
        f"line={line} "
        f"name={name}"
    )


# ============================================================
# 10. IMPORT SAFETY
# ============================================================

section(
    "10. VSE4 IMPORT SAFETY"
)

proc = subprocess.run(
    [
        sys.executable,
        "-c",
        (
            "import visual_selection_engine_v4;"
            "print('IMPORT_OK=YES')"
        ),
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
    timeout=30,
)

emit(
    "VSE4_IMPORT_RC=",
    proc.returncode,
)

stdout = (
    proc.stdout
    or ""
).strip()

stderr = (
    proc.stderr
    or ""
).strip()

if stdout:

    emit(
        "IMPORT_STDOUT="
        +
        stdout.replace(
            "\n",
            " | ",
        )[-1500:]
    )

if stderr:

    emit(
        "IMPORT_STDERR="
        +
        stderr.replace(
            "\n",
            " | ",
        )[-1500:]
    )


# ============================================================
# 11. SELF TEST
# ============================================================

section(
    "11. VSE4 SELF TEST"
)

proc = subprocess.run(
    [
        sys.executable,
        "visual_selection_engine_v4.py",
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
    timeout=60,
)

emit(
    "VSE4_SELF_TEST_RC=",
    proc.returncode,
)

if proc.stdout:

    emit(
        "SELF_TEST_STDOUT="
        +
        proc.stdout.strip().replace(
            "\n",
            " | ",
        )[-2000:]
    )

if proc.stderr:

    emit(
        "SELF_TEST_STDERR="
        +
        proc.stderr.strip().replace(
            "\n",
            " | ",
        )[-2000:]
    )


# ============================================================
# 12. CORE COMPILE
# ============================================================

section(
    "12. CORE COMPILE"
)

py_files = [
    "midia.py",
    "visual_selection_engine_v4.py",
    "visual_selection_runtime_v42.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
]


compile_failures = []


for name in py_files:

    path = ROOT / name

    if not path.is_file():

        emit(
            f"COMPILE {name}=MISSING"
        )

        continue


    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


    emit(
        f"COMPILE {name}="
        f"{proc.returncode}"
    )


    if proc.returncode != 0:

        compile_failures.append(
            name
        )


proc = subprocess.run(
    [
        "bash",
        "-n",
        "gerar_short.sh",
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
)

emit(
    "GERAR_SHORT_SYNTAX_RC=",
    proc.returncode,
)


# ============================================================
# 13. PROJECT-WIDE TRACEBACK SOURCE SCAN
# ============================================================

section(
    "13. RECENT ERROR SCAN"
)

logs_dir = ROOT / "logs" / "producao"

error_summary = []


if logs_dir.is_dir():

    logs = sorted(
        logs_dir.glob("*.log"),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:40]


    for path in logs:

        try:
            text = read(path)
        except Exception:
            continue

        lowered = text.casefold()

        counts = {
            "traceback":
                lowered.count(
                    "traceback"
                ),

            "nameerror":
                lowered.count(
                    "nameerror"
                ),

            "typeerror":
                lowered.count(
                    "typeerror"
                ),

            "attributeerror":
                lowered.count(
                    "attributeerror"
                ),

            "filenotfound":
                lowered.count(
                    "file not found"
                )
                +
                lowered.count(
                    "arquivo não encontrado"
                ),

            "fail_open":
                lowered.count(
                    "fail_open"
                ),
        }


        if any(
            counts.values()
        ):

            error_summary.append(
                (
                    path.name,
                    counts,
                )
            )


emit(
    "RECENT_LOGS_WITH_ERRORS=",
    len(error_summary),
)

for name, counts in error_summary[:20]:

    emit(
        f"LOG={name} "
        f"errors={counts}"
    )


# ============================================================
# 14. ARCHITECTURE VERDICT
# ============================================================

section(
    "14. ARCHITECTURE VERDICT"
)

score_defs = len(
    definitions.get(
        "score_candidate",
        [],
    )
)

commit_count = sum(
    1
    for line
    in midia_lines
    if "VSE42_SCENE_COMMIT=FIRST_SUCCESS"
    in line
)

download_core_count = sum(
    1
    for line, name, fn
    in download_calls
    if name
    ==
    "baixar_candidato_5_2"
)


blockers = []


if score_defs > 1:

    blockers.append(
        "DUPLICATE_SCORE_CANDIDATE"
    )


if commit_count > 1:

    blockers.append(
        "MULTIPLE_SCENE_COMMIT_POINTS"
    )


if download_core_count > 1:

    blockers.append(
        "MULTIPLE_DOWNLOAD_PATHS"
    )


if proc.returncode != 0:

    blockers.append(
        "GERAR_SHORT_SYNTAX"
    )


emit(
    "SCORE_CANDIDATE_DEFS=",
    score_defs,
)

emit(
    "SCENE_COMMIT_POINTS=",
    commit_count,
)

emit(
    "CORE_DOWNLOAD_PATHS=",
    download_core_count,
)

emit(
    "ARCHITECTURE_BLOCKERS="
    +
    (
        ",".join(
            blockers
        )
        if blockers
        else
        "NONE"
    )
)


safe = (
    score_defs == 1
    and
    commit_count == 1
    and
    download_core_count == 1
    and
    not compile_failures
)


emit(
    "SAFE_FOR_SINGLE_VISUAL_RUNTIME="
    +
    (
        "YES"
        if safe
        else "NO"
    )
)


if score_defs > 1:

    emit(
        "NEXT_ACTION_1="
        "CONSOLIDATE_SCORE_CANDIDATE"
    )


if commit_count > 1:

    emit(
        "NEXT_ACTION_2="
        "CONSOLIDATE_SCENE_COMMIT"
    )


if download_core_count > 1:

    emit(
        "NEXT_ACTION_3="
        "CONSOLIDATE_DOWNLOAD_STATE_MACHINE"
    )


if (
    score_defs == 1
    and
    commit_count == 1
    and
    download_core_count == 1
):

    emit(
        "NEXT_ACTION="
        "ENABLE_CANARY_RUNTIME"
    )

else:

    emit(
        "NEXT_ACTION="
        "UNIFY_VISUAL_RUNTIME"
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
    "CORE_FILES_MODIFIED=NO"
)

emit(
    "AUDIT_V3_COMPLETE=YES"
)


REPORT.write_text(
    "\n".join(out)
    +
    "\n",
    encoding="utf-8",
)

emit(
    f"REPORT={REPORT}"
)
