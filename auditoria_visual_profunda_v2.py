#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict
import ast
import hashlib
import os
import re
import subprocess
import sys
import time


ROOT = Path.home() / "ShortAutoPro"

MIDIA = ROOT / "midia.py"
VSE = ROOT / "visual_selection_engine_v4.py"
GERAR = ROOT / "gerar_short.sh"

REPORT = ROOT / "temp" / "AUDITORIA_VISUAL_PROFUNDA_V2.txt"

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


lines_out = []


def emit(text=""):

    text = str(text)

    print(text)

    lines_out.append(text)


def section(title):

    emit()
    emit("=" * 76)
    emit(title)
    emit("=" * 76)


def sha(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def read(path):

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


# ============================================================
# 1. CORE
# ============================================================

section("1. CORE HEALTH")

for path in (
    MIDIA,
    VSE,
    GERAR,
):

    if path.is_file():

        emit(
            f"FOUND={path.name} "
            f"bytes={path.stat().st_size} "
            f"sha256={sha(path)}"
        )

    else:

        emit(
            f"MISSING={path}"
        )


# ============================================================
# 2. FLAGS
# ============================================================

section("2. VISUAL FLAGS - EXACT ASSIGNMENTS")

shell = read(GERAR)

flag_names = (
    "SAP_VSE4",
    "SAP_VSE42",
    "SAP_VSE4_RUNTIME",
    "SAP_SCENE_COMMIT_LOCK",
)

shell_lines = shell.splitlines()

flag_values = defaultdict(list)


for number, line in enumerate(
    shell_lines,
    start=1,
):

    for flag in flag_names:

        match = re.search(
            rf"\b{re.escape(flag)}\s*=\s*"
            r"""(?:"([^"]*)"|'([^']*)'|([^\s#;]+))""",
            line,
        )

        if match:

            value = next(
                (
                    item
                    for item in match.groups()
                    if item is not None
                ),
                "",
            )

            flag_values[flag].append(
                (
                    number,
                    value,
                    line.strip(),
                )
            )


for flag in flag_names:

    values = flag_values.get(
        flag,
        [],
    )

    if not values:

        emit(
            f"{flag}=NO_ASSIGNMENT"
        )

        continue


    for number, value, raw in values:

        emit(
            f"{flag} line={number} "
            f"value={value!r}"
        )

        emit(
            f"    {raw}"
        )


disabled_main = []

for flag in (
    "SAP_VSE4",
    "SAP_VSE42",
    "SAP_VSE4_RUNTIME",
):

    values = flag_values.get(
        flag,
        [],
    )

    if values:

        last_value = values[-1][1]

        if last_value == "0":
            disabled_main.append(
                flag
            )


emit()

emit(
    "EXPLICITLY_DISABLED_MAIN_FLAGS="
    +
    (
        ",".join(disabled_main)
        if disabled_main
        else "NONE"
    )
)


# ============================================================
# 3. VSE DUPLICATE FUNCTIONS
# ============================================================

section("3. VSE4 DUPLICATE FUNCTION FORENSICS")

vse_source = read(VSE)
vse_tree = ast.parse(vse_source)

definitions = defaultdict(list)


for node in vse_tree.body:

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):

        dump = ast.dump(
            node,
            include_attributes=False,
        )

        digest = hashlib.sha256(
            dump.encode("utf-8")
        ).hexdigest()[:16]

        definitions[node.name].append(
            {
                "line":
                    node.lineno,

                "end":
                    node.end_lineno,

                "hash":
                    digest,

                "node":
                    node,
            }
        )


duplicate_names = {
    name: items
    for name, items in definitions.items()
    if len(items) > 1
}


if not duplicate_names:

    emit(
        "VSE4_DUPLICATE_FUNCTIONS=NONE"
    )

else:

    for name, items in sorted(
        duplicate_names.items()
    ):

        emit(
            f"DUPLICATE={name} "
            f"count={len(items)}"
        )

        unique_hashes = {
            item["hash"]
            for item in items
        }

        for index, item in enumerate(
            items,
            start=1,
        ):

            effective = (
                index == len(items)
            )

            emit(
                f"  def#{index} "
                f"lines={item['line']}-{item['end']} "
                f"ast_hash={item['hash']} "
                f"effective={effective}"
            )


        emit(
            "  IDENTICAL_BODIES="
            +
            (
                "YES"
                if len(unique_hashes) == 1
                else "NO"
            )
        )


score_defs = definitions.get(
    "score_candidate",
    [],
)

emit()

emit(
    f"SCORE_CANDIDATE_DEFINITION_COUNT="
    f"{len(score_defs)}"
)


if score_defs:

    emit(
        "SCORE_CANDIDATE_EFFECTIVE_LINE="
        f"{score_defs[-1]['line']}"
    )


# ============================================================
# 4. MIDIA FUNCTION SPANS
# ============================================================

section("4. MIDIA VISUAL CONTROL FLOW")

midia_source = read(MIDIA)
midia_lines = midia_source.splitlines()
midia_tree = ast.parse(midia_source)


function_spans = []


for node in ast.walk(
    midia_tree
):

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    ):

        function_spans.append(
            (
                node.lineno,
                node.end_lineno,
                node.name,
            )
        )


def enclosing_function(line_number):

    matches = [
        item
        for item in function_spans
        if (
            item[0]
            <= line_number
            <= item[1]
        )
    ]

    if not matches:
        return "<module>"

    matches.sort(
        key=lambda item:
            item[1] - item[0]
    )

    return matches[0][2]


markers = (
    "VSE417",
    "VISUAL_UNIFIED",
    "VSE42_FINAL_GATE",
    "VSE42_PRIMARY_RANK",
    "VSE42_FINAL_POOL",
    "VSE42_SCENE_COMMIT",
    "VSE42_SUCCESS_COMMIT",
)


marker_hits = []


for number, line in enumerate(
    midia_lines,
    start=1,
):

    for marker in markers:

        if marker in line:

            indent = (
                len(line)
                -
                len(line.lstrip())
            )

            function = enclosing_function(
                number
            )

            marker_hits.append(
                (
                    number,
                    marker,
                    function,
                    indent,
                    line.strip(),
                )
            )


for (
    number,
    marker,
    function,
    indent,
    text,
) in marker_hits:

    emit(
        f"{marker} "
        f"line={number} "
        f"function={function} "
        f"indent={indent}"
    )

    emit(
        f"    {text[:180]}"
    )


visual_functions = defaultdict(
    list
)

for hit in marker_hits:

    visual_functions[
        hit[2]
    ].append(
        hit
    )


emit()

emit(
    "VISUAL_FUNCTION_COUNT="
    f"{len(visual_functions)}"
)


for function, hits in sorted(
    visual_functions.items()
):

    emit(
        f"FUNCTION={function} "
        f"visual_markers={len(hits)}"
    )


# ============================================================
# 5. CONTEXT AROUND COMMIT POINTS
# ============================================================

section("5. COMMIT POINT CONTEXT")

commit_hits = [
    hit
    for hit in marker_hits
    if "COMMIT" in hit[1]
]


for hit in commit_hits:

    number = hit[0]

    emit()
    emit(
        f"--- COMMIT line={number} "
        f"function={hit[2]} ---"
    )

    start = max(
        1,
        number - 7,
    )

    end = min(
        len(midia_lines),
        number + 10,
    )

    for line_no in range(
        start,
        end + 1,
    ):

        emit(
            f"{line_no:05d}: "
            f"{midia_lines[line_no - 1]}"
        )


# ============================================================
# 6. DOWNLOAD PATHS
# ============================================================

section("6. DOWNLOAD CALL CONTROL FLOW")

for node in ast.walk(
    midia_tree
):

    if not isinstance(
        node,
        ast.Call,
    ):
        continue

    name = ""

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


    if name != "baixar_candidato_5_2":
        continue


    emit(
        "DOWNLOAD_CALL "
        f"line={node.lineno} "
        f"function={enclosing_function(node.lineno)}"
    )

    start = max(
        1,
        node.lineno - 4,
    )

    end = min(
        len(midia_lines),
        node.end_lineno + 5,
    )

    for line_no in range(
        start,
        end + 1,
    ):

        emit(
            f"  {line_no:05d}: "
            f"{midia_lines[line_no - 1]}"
        )


# ============================================================
# 7. WIKIMEDIA RESOLUTION
# ============================================================

section("7. WIKIMEDIA PROVIDER SYMBOL RESOLUTION")

target = "buscar_wikimedia_fotos"

module_symbols = set()


for node in midia_tree.body:

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
        ),
    ):

        module_symbols.add(
            node.name
        )


    elif isinstance(
        node,
        ast.Import,
    ):

        for alias in node.names:

            module_symbols.add(
                alias.asname
                or
                alias.name.split(".")[0]
            )


    elif isinstance(
        node,
        ast.ImportFrom,
    ):

        for alias in node.names:

            module_symbols.add(
                alias.asname
                or
                alias.name
            )


    elif isinstance(
        node,
        ast.Assign,
    ):

        for target_node in node.targets:

            if isinstance(
                target_node,
                ast.Name,
            ):

                module_symbols.add(
                    target_node.id
                )


emit(
    f"{target}_MODULE_SYMBOL="
    f"{target in module_symbols}"
)


references = []


for number, line in enumerate(
    midia_lines,
    start=1,
):

    if target in line:

        references.append(
            number
        )


emit(
    f"{target}_REFERENCE_LINES="
    +
    (
        ",".join(
            map(str, references)
        )
        if references
        else "NONE"
    )
)


for number in references:

    emit()

    start = max(
        1,
        number - 4,
    )

    end = min(
        len(midia_lines),
        number + 4,
    )

    for line_no in range(
        start,
        end + 1,
    ):

        emit(
            f"{line_no:05d}: "
            f"{midia_lines[line_no - 1]}"
        )


# ============================================================
# 8. COMPLETED / PARTIAL SHORTS
# ============================================================

section("8. RECENT SHORT ARTIFACT MATRIX")

images_root = ROOT / "imagens"

runs = []


if images_root.is_dir():

    for folder in images_root.glob(
        "short_*"
    ):

        if not folder.is_dir():
            continue

        sid = folder.name[
            len("short_"):
        ]

        scenes = set()

        for file in folder.glob(
            "scene_*.*"
        ):

            match = re.match(
                r"scene_(\d+)\.",
                file.name,
            )

            if match:

                scenes.add(
                    int(
                        match.group(1)
                    )
                )


        audio = (
            ROOT
            / "audios"
            / f"short_{sid}.mp3"
        )

        ass = (
            ROOT
            / "videos"
            / f"short_{sid}.ass"
        )

        video_base = (
            ROOT
            / "temp"
            / sid
            / "video_sem_audio.mp4"
        )

        final = (
            ROOT
            / "videos"
            / f"short_v6_{sid}.mp4"
        )


        mtime = folder.stat().st_mtime


        runs.append(
            {
                "sid": sid,
                "mtime": mtime,
                "scenes": len(scenes),
                "audio": audio.is_file(),
                "ass": ass.is_file(),
                "base": video_base.is_file(),
                "final": final.is_file(),
            }
        )


runs.sort(
    key=lambda item:
        item["mtime"],
    reverse=True,
)


for item in runs[:10]:

    complete = (
        item["scenes"] == 12
        and
        item["audio"]
        and
        item["ass"]
        and
        item["base"]
        and
        item["final"]
    )

    emit(
        f"SHORT={item['sid']} "
        f"scenes={item['scenes']} "
        f"audio={item['audio']} "
        f"ass={item['ass']} "
        f"base={item['base']} "
        f"final={item['final']} "
        f"complete={complete}"
    )


complete_runs = [
    item
    for item in runs
    if (
        item["scenes"] == 12
        and
        item["final"]
    )
]


if complete_runs:

    emit()

    emit(
        "LATEST_COMPLETED_MEDIA_SHORT="
        f"{complete_runs[0]['sid']}"
    )

else:

    emit(
        "LATEST_COMPLETED_MEDIA_SHORT=NONE"
    )


# ============================================================
# 9. RECENT LOGS
# ============================================================

section("9. RECENT LOG ERROR FORENSICS")

logs = ROOT / "logs" / "producao"

log_rows = []


if logs.is_dir():

    files = [
        path
        for path in logs.iterdir()
        if path.is_file()
    ]

    files.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


    for path in files[:30]:

        text = read(path)

        counts = {
            "traceback":
                text.lower().count(
                    "traceback"
                ),

            "nameerror":
                text.lower().count(
                    "nameerror"
                ),

            "file_not_found":
                text.lower().count(
                    "file not found"
                )
                +
                text.lower().count(
                    "arquivo não encontrado"
                ),

            "fail_open":
                text.lower().count(
                    "fail_open"
                ),

            "erro":
                len(
                    re.findall(
                        r"\berro\b",
                        text,
                        flags=re.IGNORECASE,
                    )
                ),
        }


        total = sum(
            counts.values()
        )


        if total:

            log_rows.append(
                (
                    path,
                    counts,
                )
            )


for path, counts in log_rows[:15]:

    age_hours = (
        time.time()
        -
        path.stat().st_mtime
    ) / 3600

    emit(
        f"LOG={path.name} "
        f"age_hours={age_hours:.1f} "
        f"errors={counts}"
    )


# ============================================================
# 10. SELF TEST / SYNTAX
# ============================================================

section("10. LIVE SAFE CHECKS")

vse_test = subprocess.run(
    [
        sys.executable,
        str(VSE),
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
)


emit(
    f"VSE4_SELF_TEST_RC="
    f"{vse_test.returncode}"
)

if vse_test.stdout.strip():

    emit(
        "VSE4_STDOUT_TAIL="
        +
        " | ".join(
            vse_test.stdout.strip().splitlines()[-5:]
        )
    )


if vse_test.stderr.strip():

    emit(
        "VSE4_STDERR_TAIL="
        +
        " | ".join(
            vse_test.stderr.strip().splitlines()[-5:]
        )
    )


shell_test = subprocess.run(
    [
        "bash",
        "-n",
        str(GERAR),
    ],
    cwd=ROOT,
)


emit(
    f"GERAR_SHORT_SYNTAX_RC="
    f"{shell_test.returncode}"
)


python_test = subprocess.run(
    [
        sys.executable,
        "-m",
        "py_compile",
        str(MIDIA),
        str(VSE),
    ],
    cwd=ROOT,
)


emit(
    f"CORE_PYTHON_COMPILE_RC="
    f"{python_test.returncode}"
)


# ============================================================
# 11. DECISION
# ============================================================

section("11. REPAIR READINESS SUMMARY")

different_score_defs = False

if len(score_defs) > 1:

    score_hashes = {
        item["hash"]
        for item in score_defs
    }

    different_score_defs = (
        len(score_hashes) > 1
    )


visual_marker_count = len(
    marker_hits
)

commit_count = len(
    commit_hits
)


emit(
    "MAIN_VISUAL_FLAGS_DISABLED="
    f"{len(disabled_main)}"
)

emit(
    "SCORE_CANDIDATE_DUPLICATE="
    f"{len(score_defs) > 1}"
)

emit(
    "SCORE_CANDIDATE_BODIES_DIFFER="
    f"{different_score_defs}"
)

emit(
    "VISUAL_MARKER_COUNT="
    f"{visual_marker_count}"
)

emit(
    "COMMIT_MARKER_COUNT="
    f"{commit_count}"
)


hard_blockers = []


if vse_test.returncode != 0:

    hard_blockers.append(
        "VSE4_SELF_TEST"
    )


if shell_test.returncode != 0:

    hard_blockers.append(
        "GERAR_SHORT_SYNTAX"
    )


if python_test.returncode != 0:

    hard_blockers.append(
        "CORE_PYTHON_COMPILE"
    )


if hard_blockers:

    emit(
        "HARD_BLOCKERS="
        +
        ",".join(
            hard_blockers
        )
    )

else:

    emit(
        "HARD_BLOCKERS=NONE"
    )


# Não autoriza simplesmente ligar flags se ainda
# existem múltiplas decisões/commits sem revisão.
safe_to_enable = (
    not hard_blockers
    and
    len(disabled_main) > 0
    and
    commit_count <= 1
    and
    not different_score_defs
)


emit(
    "SAFE_TO_ENABLE_VISUAL_FLAGS_NOW="
    +
    (
        "YES"
        if safe_to_enable
        else "NO"
    )
)


if (
    not hard_blockers
    and
    len(disabled_main) > 0
):

    emit(
        "NEXT_ACTION="
        "UNIFY_VISUAL_DECISION_PATH_BEFORE_ACTIVATION"
    )

else:

    emit(
        "NEXT_ACTION="
        "FIX_HARD_BLOCKERS_FIRST"
        if hard_blockers
        else
        "REVIEW_CONFIGURATION"
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
    "DEEP_AUDIT_COMPLETE=YES"
)


REPORT.write_text(
    "\n".join(
        lines_out
    )
    +
    "\n",
    encoding="utf-8",
)


print()
print(
    f"REPORT={REPORT}"
)
