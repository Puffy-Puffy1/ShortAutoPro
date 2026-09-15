#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import symtable
import sys
import traceback

from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime


ROOT = Path.home() / "ShortAutoPro"

EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "backups",
    "backup",
    "temp",
    "venv",
    ".venv",
    "node_modules",
}

CORE_FILES = (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "legenda_dinamica.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v2.py",
    "visual_selection_final_gate_v3.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "visual_selection_engine_v4.py",
)

PROVIDER_FUNCTIONS = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
    "buscar_todos_candidatos",
    "baixar_candidato_5_2",
)

DANGEROUS_SHARED_NAMES = {
    "enabled",
    "reset_state",
    "finalize_pool",
    "note_success",
    "commit_media",
    "install",
    "install_hooks",
    "install_search_rescue",
    "wrap",
    "patch",
}

VISUAL_NAME_PATTERNS = (
    "visual",
    "media_diversity",
    "media_provenance",
)

results = []
errors = []
warnings = []
passes = []


def out(*args):
    line = " ".join(str(x) for x in args)
    print(line)
    results.append(line)


def section(title):
    out()
    out("=" * 72)
    out(title)
    out("=" * 72)


def add_error(message):
    errors.append(message)
    out("ERROR=" + message)


def add_warning(message):
    warnings.append(message)
    out("WARNING=" + message)


def add_pass(message):
    passes.append(message)
    out("PASS=" + message)


def read(path: Path):
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def sha256(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def parse(path: Path):
    return ast.parse(
        read(path),
        filename=str(path),
    )


def ignored(path: Path):
    try:
        rel = path.relative_to(ROOT)
    except Exception:
        return True

    return any(
        part in EXCLUDED_DIRS
        for part in rel.parts[:-1]
    )


def project_python_files():
    files = []

    for path in ROOT.rglob("*.py"):
        if ignored(path):
            continue

        files.append(path)

    return sorted(files)


def root_shell_files():
    return sorted(
        path
        for path in ROOT.glob("*.sh")
        if path.is_file()
    )


def visual_files():
    found = []

    for path in ROOT.glob("*.py"):

        low = path.name.casefold()

        if any(
            pattern in low
            for pattern in VISUAL_NAME_PATTERNS
        ):
            found.append(path)

    return sorted(found)


def resolve_short_id():

    env = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if env:
        return env, "ENV"

    media_root = ROOT / "imagens"

    if not media_root.is_dir():
        return None, "NONE"

    candidates = []

    for path in media_root.glob("short_*"):

        if not path.is_dir():
            continue

        sid = path.name.removeprefix(
            "short_"
        )

        try:
            mtime = path.stat().st_mtime
        except Exception:
            continue

        candidates.append(
            (
                mtime,
                sid,
            )
        )

    if not candidates:
        return None, "NONE"

    candidates.sort(
        reverse=True
    )

    return candidates[0][1], "LATEST_MEDIA_DIR"


def safe_ffprobe(path: Path):

    if not shutil.which("ffprobe"):
        return None

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,r_frame_rate",
                "-of",
                "json",
                str(path),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        if result.returncode != 0:
            return {
                "error":
                    result.stderr.strip()[
                        :500
                    ],
            }

        return json.loads(
            result.stdout
        )

    except Exception as exc:

        return {
            "error":
                f"{type(exc).__name__}: {exc}",
        }


# ============================================================
# 0. HEADER
# ============================================================

section(
    "0. SHORTAUTOPRO MASTER AUDIT"
)

out(
    "DATE=",
    datetime.now().isoformat(
        timespec="seconds"
    ),
)

out(
    "ROOT=",
    ROOT,
)

out(
    "PYTHON=",
    sys.version.replace(
        "\n",
        " ",
    ),
)

out(
    "NETWORK_EXECUTED=NO"
)

out(
    "MEDIA_DOWNLOADED=NO"
)

out(
    "VIDEO_RENDERED=NO"
)

out(
    "MIDIA_EXECUTED=NO"
)


# ============================================================
# 1. CORE FILES + HASHES
# ============================================================

section(
    "1. CORE FILES AND HASHES"
)

for name in CORE_FILES:

    path = ROOT / name

    if path.is_file():

        out(
            f"CORE={name}:FOUND:"
            f"{path.stat().st_size}:"
            f"{sha256(path)}"
        )

    else:

        add_warning(
            f"CORE_FILE_MISSING:{name}"
        )


# ============================================================
# 2. PYTHON SYNTAX
# ============================================================

section(
    "2. PYTHON SYNTAX"
)

python_files = project_python_files()

syntax_failures = []

out(
    "PYTHON_FILES_SCANNED=",
    len(python_files),
)

for path in python_files:

    try:

        compile(
            read(path),
            str(path),
            "exec",
        )

    except Exception as exc:

        syntax_failures.append(
            path
        )

        add_error(
            f"PYTHON_SYNTAX:"
            f"{path.relative_to(ROOT)}:"
            f"{type(exc).__name__}:{exc}"
        )


if not syntax_failures:

    add_pass(
        "ALL_PYTHON_SYNTAX"
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)

shell_files = root_shell_files()

out(
    "SHELL_FILES_SCANNED=",
    len(shell_files),
)

shell_failures = []


for path in shell_files:

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

    if result.returncode != 0:

        shell_failures.append(
            path
        )

        add_error(
            f"SHELL_SYNTAX:"
            f"{path.name}:"
            f"{result.stderr.strip()[:500]}"
        )


if not shell_failures:

    add_pass(
        "ALL_SHELL_SYNTAX"
    )


# ============================================================
# 4. DUPLICATE TOP-LEVEL DEFINITIONS
# ============================================================

section(
    "4. DUPLICATE DEFINITIONS"
)

duplicate_def_count = 0


for path in python_files:

    try:
        tree = parse(path)
    except Exception:
        continue

    defs = defaultdict(
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

            defs[
                node.name
            ].append(
                node.lineno
            )


    duplicates = {
        name: lines
        for name, lines in defs.items()
        if len(lines) > 1
    }


    for name, lines in duplicates.items():

        duplicate_def_count += 1

        add_warning(
            f"DUPLICATE_TOPLEVEL:"
            f"{path.relative_to(ROOT)}:"
            f"{name}:"
            f"{','.join(map(str, lines))}"
        )


if duplicate_def_count == 0:

    add_pass(
        "NO_DUPLICATE_TOPLEVEL_DEFS"
    )


# ============================================================
# 5. VISUAL MODULE EXPORT OVERLAP
# ============================================================

section(
    "5. VISUAL MODULE EXPORT OVERLAP"
)

vfiles = visual_files()

out(
    "VISUAL_FILES=",
    len(vfiles),
)

exports = defaultdict(
    list
)


for path in vfiles:

    try:
        tree = parse(path)
    except Exception:
        continue


    names = set()

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            names.add(
                node.name
            )


    for name in names:

        exports[
            name
        ].append(
            path.name
        )


for name in sorted(
    DANGEROUS_SHARED_NAMES
):

    files = exports.get(
        name,
        [],
    )

    if len(files) > 1:

        add_warning(
            f"MULTIPLE_IMPLEMENTATIONS:"
            f"{name}:"
            f"{','.join(files)}"
        )


# ============================================================
# 6. FEATURE FLAGS
# ============================================================

section(
    "6. FEATURE FLAGS"
)

flags_by_file = defaultdict(
    set
)

flag_regex = re.compile(
    r"SAP_[A-Z0-9_]+"
)


for path in vfiles + [ROOT / "midia.py"]:

    if not path.is_file():
        continue

    flags = set(
        flag_regex.findall(
            read(path)
        )
    )

    flags_by_file[
        path.name
    ] = flags


all_flags = set()


for name, flags in sorted(
    flags_by_file.items()
):

    all_flags.update(
        flags
    )

    out(
        f"FLAGS={name}:"
        +
        ",".join(
            sorted(flags)
        )
    )


v4_flags = sorted(
    flag
    for flag in all_flags
    if (
        "V4" in flag
        or
        "V42" in flag
    )
)

out(
    "V4_RELATED_FLAGS="
    +
    ",".join(v4_flags)
)


if len(v4_flags) > 3:

    add_warning(
        "MANY_V4_FEATURE_FLAGS:"
        +
        ",".join(v4_flags)
    )


# ============================================================
# 7. SILENT EXCEPTIONS
# ============================================================

section(
    "7. SILENT EXCEPTION AUDIT"
)


for path in python_files:

    try:
        tree = parse(path)
    except Exception:
        continue


    silent = []


    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.ExceptHandler,
        ):
            continue


        if (
            len(node.body) == 1
            and
            isinstance(
                node.body[0],
                ast.Pass,
            )
        ):

            silent.append(
                node.lineno
            )


    if silent:

        out(
            f"SILENT_EXCEPT_PASS="
            f"{path.relative_to(ROOT)}:"
            +
            ",".join(
                map(str, silent)
            )
        )


        if len(silent) >= 5:

            add_warning(
                f"MANY_SILENT_EXCEPTIONS:"
                f"{path.relative_to(ROOT)}:"
                f"{len(silent)}"
            )


# ============================================================
# 8. DESTRUCTIVE OPERATIONS
# ============================================================

section(
    "8. DESTRUCTIVE OPERATION AUDIT"
)

danger_regex = re.compile(
    r"\b("
    r"os\.remove|"
    r"os\.unlink|"
    r"shutil\.rmtree|"
    r"\.unlink\s*\(|"
    r"rmtree\s*\("
    r")"
)


for path in vfiles + [
    ROOT / "midia.py",
    ROOT / "fresh_render_guard_v1.py",
]:

    if not path.is_file():
        continue


    hits = []


    for line_no, line in enumerate(
        read(path).splitlines(),
        start=1,
    ):

        if danger_regex.search(
            line
        ):

            hits.append(
                (
                    line_no,
                    line.strip(),
                )
            )


    out(
        f"DESTRUCTIVE_OPS="
        f"{path.name}:"
        f"{len(hits)}"
    )


    for line_no, text in hits[:25]:

        out(
            f"  LINE={line_no}:"
            f"{text}"
        )


# ============================================================
# 9. MIDIA VISUAL INTEGRATION
# ============================================================

section(
    "9. MIDIA VISUAL INTEGRATION"
)

midia = ROOT / "midia.py"


if not midia.is_file():

    add_error(
        "MIDIA_PY_NOT_FOUND"
    )

else:

    src = read(
        midia
    )


    bridge_patterns = (
        "visual_selection_engine_v4",
        "visual_selection_bridge_v42",
        "visual_pipeline_bridge_v42",
        "visual_selection_runtime_v42",
        "visual_runtime_v42",
        "VSE4",
        "VSE42",
    )


    integration_total = 0


    for pattern in bridge_patterns:

        count = src.count(
            pattern
        )

        integration_total += count

        out(
            f"MIDIA_REFERENCE="
            f"{pattern}:{count}"
        )


    out(
        "MIDIA_V4_TOTAL_REFERENCES=",
        integration_total,
    )


    if integration_total == 0:

        add_error(
            "MIDIA_HAS_NO_V4_REFERENCE"
        )


    elif integration_total > 20:

        add_warning(
            "MIDIA_HAS_MANY_V4_REFERENCES:"
            "POSSIBLE_DOUBLE_INTEGRATION"
        )


# ============================================================
# 10. PROVIDER ACQUISITION
# ============================================================

section(
    "10. PROVIDER ACQUISITION"
)


if midia.is_file():

    try:

        tree = parse(
            midia
        )

        definitions = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        for name in PROVIDER_FUNCTIONS:

            if name in definitions:

                out(
                    f"PROVIDER_FUNCTION="
                    f"{name}:PASS"
                )

            else:

                add_warning(
                    f"PROVIDER_FUNCTION_MISSING:"
                    f"{name}"
                )


        buscar = definitions.get(
            "buscar_todos_candidatos"
        )


        if buscar:

            calls = []


            for node in ast.walk(
                buscar
            ):

                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue


                try:

                    calls.append(
                        ast.unparse(
                            node.func
                        )
                    )

                except Exception:
                    pass


            for provider_name in (
                "pexels_video",
                "pexels_foto",
                "pixabay_video",
                "pixabay_foto",
                "coverr_video",
                "buscar_wikimedia_fotos",
            ):

                found = (
                    provider_name
                    in calls
                )

                out(
                    f"PROVIDER_CALL="
                    f"{provider_name}:"
                    f"{'YES' if found else 'NO'}"
                )


                if not found:

                    add_warning(
                        f"PROVIDER_NOT_CALLED:"
                        f"{provider_name}"
                    )


    except Exception as exc:

        add_error(
            f"PROVIDER_AST_FAILURE:"
            f"{type(exc).__name__}:{exc}"
        )


# ============================================================
# 11. DOWNLOAD / COMMIT FLOW
# ============================================================

section(
    "11. DOWNLOAD AND COMMIT FLOW"
)


if midia.is_file():

    src = read(
        midia
    )


    patterns = {
        "baixar_candidato_5_2":
            r"\bbaixar_candidato_5_2\b",

        "FAILOVER_QUALIDADE":
            r"FAILOVER:\s*QUALIDADE",

        "SCENE_COMMIT_LOCK":
            r"SCENE_COMMIT_LOCK",

        "commit_media":
            r"\bcommit_media\b",

        "note_success":
            r"\bnote_success\b",

        "VSE3":
            r"\bVSE3",

        "VSE4":
            r"\bVSE4",
    }


    for name, pattern in patterns.items():

        count = len(
            re.findall(
                pattern,
                src,
                flags=re.I,
            )
        )

        out(
            f"MIDIA_FLOW="
            f"{name}:{count}"
        )


# ============================================================
# 12. TRUE GLOBAL AUDIT — VISUAL FILES
# ============================================================

section(
    "12. TRUE GLOBAL AUDIT"
)

builtin_names = set(
    dir(builtins)
)


for path in vfiles:

    try:

        source = read(
            path
        )

        table = symtable.symtable(
            source,
            str(path),
            "exec",
        )


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


        def walk(scope):

            for child in scope.get_children():

                for symbol in child.get_symbols():

                    name = symbol.get_name()

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


                walk(
                    child
                )


        walk(
            table
        )


        if unresolved:

            add_error(
                f"UNRESOLVED_GLOBAL:"
                f"{path.name}:"
                +
                ",".join(
                    sorted(unresolved)
                )
            )

        else:

            out(
                f"GLOBAL_AUDIT="
                f"{path.name}:PASS"
            )


    except Exception as exc:

        add_error(
            f"GLOBAL_AUDIT_FAILURE:"
            f"{path.name}:"
            f"{type(exc).__name__}:{exc}"
        )


# ============================================================
# 13. VSE4 RUNTIME
# ============================================================

section(
    "13. VSE4 RUNTIME"
)

engine = ROOT / "visual_selection_engine_v4.py"


if not engine.is_file():

    add_error(
        "VSE4_ENGINE_NOT_FOUND"
    )

else:

    try:

        import runpy

        ns = runpy.run_path(
            str(engine),
            run_name="shortautopro_master_audit",
        )

        add_pass(
            "VSE4_IMPORT_RUNTIME"
        )


        required_functions = (
            "score_candidate",
            "geo_hits",
            "concept_hits",
            "candidate_text",
            "tokens",
            "provider",
            "source_group",
        )


        for name in required_functions:

            obj = ns.get(
                name
            )

            if callable(
                obj
            ):

                out(
                    f"VSE4_FUNCTION="
                    f"{name}:PASS"
                )

            else:

                add_error(
                    f"VSE4_FUNCTION_MISSING:"
                    f"{name}"
                )


        # -----------------------------------------------
        # Geography unit test
        # -----------------------------------------------

        geo_hits = ns.get(
            "geo_hits"
        )


        if callable(
            geo_hits
        ):

            sp = set(
                geo_hits(
                    "São Paulo Brasil"
                )
            )

            ny = set(
                geo_hits(
                    "Empire State Building "
                    "Manhattan New York USA"
                )
            )


            out(
                "VSE4_GEO_SP=",
                sorted(sp),
            )

            out(
                "VSE4_GEO_NY=",
                sorted(ny),
            )


            if (
                sp
                and ny
                and sp != ny
            ):

                add_pass(
                    "VSE4_GEO_DISTINCTION"
                )

            else:

                add_error(
                    "VSE4_GEO_DISTINCTION_FAILED"
                )


        # -----------------------------------------------
        # Core semantic ranking test
        # -----------------------------------------------

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


            try:

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


                out(
                    "VSE4_WRONG_RESULT=",
                    repr(a),
                )

                out(
                    "VSE4_CORRECT_RESULT=",
                    repr(b),
                )


                a_hard = (
                    isinstance(a, dict)
                    and
                    a.get(
                        "hard_mismatch"
                    )
                    is True
                )

                b_hard = (
                    isinstance(b, dict)
                    and
                    b.get(
                        "hard_mismatch"
                    )
                    is True
                )


                if a_hard:

                    add_pass(
                        "VSE4_WRONG_GEO_HARD_MISMATCH"
                    )

                else:

                    add_error(
                        "VSE4_WRONG_GEO_NOT_HARD_MISMATCH"
                    )


                if not b_hard:

                    add_pass(
                        "VSE4_CORRECT_GEO_ACCEPTED"
                    )

                else:

                    add_error(
                        "VSE4_CORRECT_GEO_REJECTED"
                    )


                if (
                    isinstance(a, dict)
                    and
                    isinstance(b, dict)
                    and
                    "effective" in a
                    and
                    "effective" in b
                ):

                    if (
                        b["effective"]
                        >
                        a["effective"]
                    ):

                        add_pass(
                            "VSE4_CORRECT_RANKS_ABOVE_WRONG"
                        )

                    else:

                        add_error(
                            "VSE4_WRONG_MEDIA_OUTRANKS_CORRECT"
                        )


            except Exception as exc:

                add_error(
                    f"VSE4_SCORE_RUNTIME:"
                    f"{type(exc).__name__}:{exc}"
                )


        # -----------------------------------------------
        # Native self-test
        # -----------------------------------------------

        self_test = ns.get(
            "self_test"
        )


        if callable(
            self_test
        ):

            try:

                self_test()

                add_pass(
                    "VSE4_NATIVE_SELF_TEST"
                )

            except AssertionError:

                add_error(
                    "VSE4_NATIVE_SELF_TEST_ASSERTION"
                )

            except Exception as exc:

                add_error(
                    f"VSE4_NATIVE_SELF_TEST_EXCEPTION:"
                    f"{type(exc).__name__}:{exc}"
                )


    except Exception as exc:

        add_error(
            f"VSE4_IMPORT_RUNTIME_FAILURE:"
            f"{type(exc).__name__}:{exc}"
        )

        out(
            traceback.format_exc()
        )


# ============================================================
# 14. IMPORT DEPENDENCY CYCLES
# ============================================================

section(
    "14. LOCAL IMPORT CYCLES"
)

module_files = {
    path.stem: path
    for path in python_files
    if path.parent == ROOT
}

graph = defaultdict(
    set
)


for module, path in module_files.items():

    try:
        tree = parse(path)
    except Exception:
        continue


    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                target = (
                    alias.name
                    .split(".")[0]
                )

                if target in module_files:
                    graph[module].add(
                        target
                    )


        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if not node.module:
                continue

            target = (
                node.module
                .split(".")[0]
            )

            if target in module_files:
                graph[module].add(
                    target
                )


cycles = set()


def dfs(node, stack, active):

    if node in active:

        if node in stack:

            index = stack.index(
                node
            )

            cycle = tuple(
                stack[index:]
                +
                [node]
            )

            cycles.add(
                cycle
            )

        return


    active.add(
        node
    )

    stack.append(
        node
    )


    for nxt in graph.get(
        node,
        ()
    ):

        dfs(
            nxt,
            stack,
            active,
        )


    stack.pop()

    active.remove(
        node
    )


for module in module_files:

    try:

        dfs(
            module,
            [],
            set(),
        )

    except RecursionError:

        add_warning(
            "IMPORT_GRAPH_RECURSION_LIMIT"
        )

        break


if cycles:

    normalized = set()

    for cycle in cycles:

        normalized.add(
            " -> ".join(
                cycle
            )
        )


    for cycle in sorted(
        normalized
    )[:30]:

        add_warning(
            "IMPORT_CYCLE:"
            +
            cycle
        )

else:

    add_pass(
        "NO_LOCAL_IMPORT_CYCLES"
    )


# ============================================================
# 15. ACTIVE SHORT INTEGRITY
# ============================================================

section(
    "15. ACTIVE SHORT INTEGRITY"
)

sid, sid_source = resolve_short_id()

out(
    "SHORT_ID=",
    sid,
)

out(
    "SHORT_ID_SOURCE=",
    sid_source,
)


if not sid:

    add_warning(
        "NO_SHORT_ID_DISCOVERED"
    )

else:

    media_dir = (
        ROOT
        /
        "imagens"
        /
        f"short_{sid}"
    )


    if not media_dir.is_dir():

        add_error(
            f"MEDIA_DIR_MISSING:"
            f"{media_dir}"
        )

    else:

        media_count = 0
        scene_problems = 0
        media_hashes = defaultdict(
            list
        )


        for number in range(
            1,
            13,
        ):

            stem = (
                f"scene_{number:02d}"
            )

            matches = sorted(
                path
                for path in media_dir.glob(
                    stem + ".*"
                )
                if path.is_file()
            )


            media_count += len(
                matches
            )


            out(
                f"SCENE_{number:02d}_COUNT="
                f"{len(matches)}"
            )


            if len(matches) != 1:

                scene_problems += 1

                add_error(
                    f"SCENE_MEDIA_COUNT:"
                    f"{number:02d}:"
                    f"{len(matches)}"
                )


            for path in matches:

                try:

                    digest = sha256(
                        path
                    )

                    media_hashes[
                        digest
                    ].append(
                        path.name
                    )


                    out(
                        f"SCENE_MEDIA="
                        f"{number:02d}:"
                        f"{path.name}:"
                        f"{path.stat().st_size}:"
                        f"{digest}"
                    )


                except Exception as exc:

                    add_error(
                        f"MEDIA_HASH_FAILURE:"
                        f"{path.name}:"
                        f"{exc}"
                    )


        out(
            "MEDIA_TOTAL=",
            media_count,
        )

        out(
            "INVALID_SCENES=",
            scene_problems,
        )


        duplicates = {
            digest: files
            for digest, files
            in media_hashes.items()
            if len(files) > 1
        }


        if duplicates:

            for digest, files in duplicates.items():

                add_warning(
                    "DUPLICATE_MEDIA_HASH:"
                    +
                    digest
                    +
                    ":"
                    +
                    ",".join(files)
                )

        else:

            add_pass(
                "NO_EXACT_MEDIA_DUPLICATES"
            )


    # --------------------------------------------------------
    # Required render assets
    # --------------------------------------------------------

    expected = {
        "AUDIO":
            ROOT
            /
            "audios"
            /
            f"short_{sid}.mp3",

        "ASS":
            ROOT
            /
            "videos"
            /
            f"short_{sid}.ass",

        "VIDEO_BASE":
            ROOT
            /
            "temp"
            /
            sid
            /
            "video_sem_audio.mp4",

        "FINAL":
            ROOT
            /
            "videos"
            /
            f"short_v6_{sid}.mp4",

        "SCENE_MAP":
            ROOT
            /
            "roteiros"
            /
            f"scene_map_{sid}.json",
    }


    for name, path in expected.items():

        if path.is_file():

            out(
                f"ASSET={name}:FOUND:"
                f"{path.stat().st_size}:"
                f"{path}"
            )

        else:

            out(
                f"ASSET={name}:MISSING:"
                f"{path}"
            )


            if name in {
                "AUDIO",
                "ASS",
                "SCENE_MAP",
            }:

                add_warning(
                    f"EXPECTED_ASSET_MISSING:"
                    f"{name}"
                )


    final = expected[
        "FINAL"
    ]


    if final.is_file():

        probe = safe_ffprobe(
            final
        )

        out(
            "FINAL_FFPROBE="
            +
            json.dumps(
                probe,
                ensure_ascii=False,
                separators=(
                    ",",
                    ":",
                ),
            )
        )


        if (
            isinstance(
                probe,
                dict,
            )
            and
            probe.get(
                "error"
            )
        ):

            add_error(
                "FINAL_FFPROBE_FAILED:"
                +
                str(
                    probe["error"]
                )
            )

        else:

            add_pass(
                "FINAL_VIDEO_READABLE"
            )


# ============================================================
# 16. CONFIG / PROVIDER KEY NAMES ONLY
# ============================================================

section(
    "16. PROVIDER CONFIG PRESENCE"
)

config_candidates = (
    ROOT / "config.env",
    ROOT / ".env",
)


for config in config_candidates:

    if not config.is_file():
        continue


    out(
        f"CONFIG_FILE={config.name}:FOUND"
    )


    keys = set()


    for raw in read(
        config
    ).splitlines():

        raw = raw.strip()

        if (
            not raw
            or raw.startswith("#")
            or "=" not in raw
        ):
            continue


        key = raw.split(
            "=",
            1,
        )[0].strip()


        if key:

            keys.add(
                key
            )


    for pattern in (
        "PEXELS",
        "PIXABAY",
        "COVERR",
        "WIKIMEDIA",
    ):

        found = sorted(
            key
            for key in keys
            if pattern in key.upper()
        )


        out(
            f"CONFIG_KEYS_{pattern}="
            +
            (
                ",".join(found)
                if found
                else
                "NONE"
            )
        )


# ============================================================
# 17. FIXED / NON-NAMESPACED VIDEO TEMP PATHS
# ============================================================

section(
    "17. POSSIBLE CACHE / TEMP COLLISIONS"
)

generic_video_regex = re.compile(
    r"""['"]([^'"]*(?:temp|videos)[^'"]*\.mp4)['"]""",
    re.I,
)


for name in (
    "video.py",
    "v6.py",
    "gerar_short.sh",
):

    path = ROOT / name

    if not path.is_file():
        continue


    source = read(
        path
    )


    hits = []


    for line_no, line in enumerate(
        source.splitlines(),
        start=1,
    ):

        if ".mp4" not in line:
            continue


        if (
            "SHORT_ID" not in line
            and
            "TEMP" not in line
            and
            "temp" in line.casefold()
        ):

            hits.append(
                (
                    line_no,
                    line.strip(),
                )
            )


    out(
        f"GENERIC_TEMP_MP4_LINES="
        f"{name}:{len(hits)}"
    )


    for line_no, text in hits[:30]:

        out(
            f"  LINE={line_no}:"
            f"{text}"
        )


    if hits:

        add_warning(
            f"POSSIBLE_NON_NAMESPACED_CACHE:"
            f"{name}:"
            f"{len(hits)}"
        )


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

section(
    "18. MASTER AUDIT SUMMARY"
)

out(
    "PASS_COUNT=",
    len(passes),
)

out(
    "WARNING_COUNT=",
    len(warnings),
)

out(
    "ERROR_COUNT=",
    len(errors),
)


if errors:

    out()
    out(
        "===== ERRORS ====="
    )

    for item in errors:

        out(
            "ERROR_ITEM=",
            item,
        )


if warnings:

    out()
    out(
        "===== WARNINGS ====="
    )

    for item in warnings:

        out(
            "WARNING_ITEM=",
            item,
        )


out()

if not errors:

    out(
        "MASTER_AUDIT_STATUS=PASS"
    )

elif len(errors) <= 3:

    out(
        "MASTER_AUDIT_STATUS=FAIL_LOCALIZED"
    )

else:

    out(
        "MASTER_AUDIT_STATUS=FAIL_MULTIPLE"
    )


out(
    "SAFE_TO_RENDER="
    +
    (
        "YES"
        if not errors
        else
        "NO"
    )
)

out(
    "AUDIT_COMPLETE=YES"
)

out(
    "PROJECT_FILES_MODIFIED=NO"
)

out(
    "NETWORK_EXECUTED=NO"
)

out(
    "MEDIA_DOWNLOADED=NO"
)

out(
    "VIDEO_RENDERED=NO"
)
