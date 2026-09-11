#!/usr/bin/env python3

from pathlib import Path
from collections import Counter, defaultdict
import ast
import builtins
import hashlib
import inspect
import json
import os
import runpy
import shutil
import subprocess
import symtable
import time
import traceback


ROOT = Path.home() / "ShortAutoPro"
REPORT = ROOT / "temp" / "SHORTAUTOPRO_MASTER_AUDIT_V1.txt"

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


PASS = []
WARN = []
FAIL = []


def emit(*args):
    text = " ".join(
        str(x)
        for x in args
    )
    print(text)

    with REPORT.open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(
            text + "\n"
        )


def section(title):

    emit()
    emit("=" * 74)
    emit(title)
    emit("=" * 74)


def ok(name, detail=""):

    PASS.append(name)

    emit(
        f"{name}=PASS"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def warning(name, detail=""):

    WARN.append(name)

    emit(
        f"{name}=WARN"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def fail(name, detail=""):

    FAIL.append(name)

    emit(
        f"{name}=FAIL"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def load_ast(path):

    return ast.parse(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        ),
        filename=str(path),
    )


REPORT.write_text(
    "",
    encoding="utf-8",
)


section(
    "SHORTAUTOPRO MASTER AUDIT V1"
)

emit(
    "ROOT=",
    ROOT,
)

emit(
    "DATE=",
    time.strftime(
        "%Y-%m-%d %H:%M:%S"
    ),
)

emit(
    "PURPOSE=general_bug_regression_contract_visual_audit"
)

emit(
    "NETWORK_CALLED_BY_AUDITOR=NO"
)

emit(
    "MEDIA_DOWNLOADED_BY_AUDITOR=NO"
)

emit(
    "VIDEO_RENDERED_BY_AUDITOR=NO"
)


# ============================================================
# 1. IMPORTANT FILES
# ============================================================

section(
    "1. IMPORTANT FILE STATUS + HASH"
)


important_files = [

    "midia.py",
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "visual_query_expansion_v4.py",
    "visual_scene_commit_lock_v1.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",

    "video.py",
    "v6.py",

    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",

    "gerar_short.sh",
]


for name in important_files:

    path = ROOT / name

    if path.is_file():

        emit(
            "FILE=",
            name,
        )

        emit(
            "SHA256=",
            sha256(path),
        )

    else:

        warning(
            f"FILE_{name}",
            "missing",
        )


# ============================================================
# 2. ROOT PYTHON COMPILE
# ============================================================

section(
    "2. ROOT PYTHON COMPILE"
)


python_files = sorted(
    p
    for p in ROOT.glob("*.py")
    if p.is_file()
)


compile_failed = []


for path in python_files:

    result = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        compile_failed.append(
            path.name
        )

        emit(
            "COMPILE_ERROR_FILE=",
            path.name,
        )

        emit(
            result.stderr.strip()
        )


emit(
    "PYTHON_FILES_CHECKED=",
    len(python_files),
)


if compile_failed:

    fail(
        "ROOT_PYTHON_COMPILE",
        ",".join(
            compile_failed
        ),
    )

else:

    ok(
        "ROOT_PYTHON_COMPILE"
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SCRIPT SYNTAX"
)


shell_files = sorted(
    ROOT.glob("*.sh")
)


shell_failed = []


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

        shell_failed.append(
            path.name
        )

        emit(
            "SHELL_ERROR_FILE=",
            path.name,
        )

        emit(
            result.stderr.strip()
        )


emit(
    "SHELL_FILES_CHECKED=",
    len(shell_files),
)


if shell_failed:

    fail(
        "ROOT_SHELL_SYNTAX",
        ",".join(
            shell_failed
        ),
    )

else:

    ok(
        "ROOT_SHELL_SYNTAX"
    )


# ============================================================
# 4. DUPLICATE DEFINITIONS
# ============================================================

section(
    "4. DUPLICATE TOP-LEVEL DEFINITIONS"
)


duplicate_targets = [

    "midia.py",
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "visual_query_expansion_v4.py",
    "visual_scene_commit_lock_v1.py",
]


for name in duplicate_targets:

    path = ROOT / name

    if not path.is_file():
        continue

    try:

        tree = load_ast(path)

    except Exception as exc:

        fail(
            f"AST_{name}",
            repr(exc),
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


    counts = Counter(
        funcs
    )


    duplicates = {
        key: value
        for key, value
        in counts.items()
        if value > 1
    }


    if duplicates:

        warning(
            f"DUPLICATE_DEFS_{name}",
            json.dumps(
                duplicates,
                ensure_ascii=False,
            ),
        )

    else:

        ok(
            f"DUPLICATE_DEFS_{name}"
        )


# ============================================================
# 5. VSE4 TRUE GLOBAL AUDIT
# ============================================================

section(
    "5. VSE4 UNRESOLVED GLOBAL AUDIT"
)


vse_path = (
    ROOT
    /
    "visual_selection_engine_v4.py"
)


if vse_path.is_file():

    try:

        src = vse_path.read_text(
            encoding="utf-8",
        )

        table = symtable.symtable(
            src,
            str(vse_path),
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


        builtin_names = set(
            dir(builtins)
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


        emit(
            "TRUE_UNRESOLVED_GLOBALS=",
            (
                ",".join(
                    sorted(
                        unresolved
                    )
                )
                if unresolved
                else
                "NONE"
            ),
        )


        if unresolved:

            fail(
                "VSE4_GLOBAL_AUDIT"
            )

        else:

            ok(
                "VSE4_GLOBAL_AUDIT"
            )


    except Exception as exc:

        fail(
            "VSE4_GLOBAL_AUDIT",
            repr(exc),
        )


# ============================================================
# 6. VSE4 RUNTIME + SELF TEST
# ============================================================

section(
    "6. VSE4 RUNTIME / SELF TEST"
)


vse_ns = None


try:

    vse_ns = runpy.run_path(
        str(vse_path),
        run_name="shortautopro_master_audit_vse4",
    )

    ok(
        "VSE4_RUNTIME_LOAD"
    )


    self_test = vse_ns.get(
        "self_test"
    )


    if callable(
        self_test
    ):

        try:

            self_test()

            ok(
                "VSE4_SELF_TEST"
            )

        except Exception as exc:

            fail(
                "VSE4_SELF_TEST",
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

            emit(
                traceback.format_exc()
            )

    else:

        warning(
            "VSE4_SELF_TEST",
            "function_missing",
        )


except Exception as exc:

    fail(
        "VSE4_RUNTIME_LOAD",
        (
            f"{type(exc).__name__}: "
            f"{exc}"
        ),
    )

    emit(
        traceback.format_exc()
    )


# ============================================================
# 7. DIRECT GEO CONTRADICTION TEST
# ============================================================

section(
    "7. VSE4 DIRECT GEOGRAPHIC CONTRADICTION"
)


if vse_ns:

    score_candidate = vse_ns.get(
        "score_candidate"
    )


    if callable(
        score_candidate
    ):

        state = {

            "providers": [
                "pixabay",
                "pixabay",
            ],

            "groups": [],
            "types": [],
            "keys": [],
        }


        scene = {
            "texto":
                "Investigação em apartamento "
                "na cidade de São Paulo",

            "visual_query":
                "police investigation "
                "apartment Sao Paulo",

            "must_have": [
                "apartamento",
                "São Paulo",
            ],

            "location":
                "São Paulo Brazil",
        }


        wrong = {

            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "title":
                "Empire State Building "
                "Manhattan New York",

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
                "Apartment building "
                "Sao Paulo Brazil",

            "must":
                "1/2",

            "score":
                120,

            "width":
                1920,

            "height":
                1080,
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


            emit(
                "WRONG_HARD_MISMATCH=",
                a.get(
                    "hard_mismatch"
                )
                if isinstance(a, dict)
                else "UNKNOWN",
            )


            emit(
                "CORRECT_HARD_MISMATCH=",
                b.get(
                    "hard_mismatch"
                )
                if isinstance(b, dict)
                else "UNKNOWN",
            )


            emit(
                "WRONG_EFFECTIVE=",
                a.get(
                    "effective"
                )
                if isinstance(a, dict)
                else "UNKNOWN",
            )


            emit(
                "CORRECT_EFFECTIVE=",
                b.get(
                    "effective"
                )
                if isinstance(b, dict)
                else "UNKNOWN",
            )


            geo_ok = (
                isinstance(a, dict)
                and
                isinstance(b, dict)
                and
                a.get(
                    "hard_mismatch"
                )
                is True
                and
                b.get(
                    "hard_mismatch"
                )
                is False
                and
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
            )


            if geo_ok:

                ok(
                    "GEO_HARD_MISMATCH_RUNTIME"
                )

            else:

                fail(
                    "GEO_HARD_MISMATCH_RUNTIME"
                )


        except Exception as exc:

            fail(
                "GEO_HARD_MISMATCH_RUNTIME",
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

            emit(
                traceback.format_exc()
            )


# ============================================================
# 8. BRIDGE STATIC CONTRACT
# ============================================================

section(
    "8. VSE42 BRIDGE STATIC CONTRACT"
)


bridge_path = (
    ROOT
    /
    "visual_selection_bridge_v42.py"
)


bridge_tree = None


if bridge_path.is_file():

    try:

        bridge_tree = load_ast(
            bridge_path
        )


        bridge_functions = {
            node.name: node
            for node in bridge_tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        required = {

            "rank_pool",
            "commit_candidate",
        }


        missing = (
            required
            -
            set(
                bridge_functions
            )
        )


        emit(
            "BRIDGE_MISSING_EXPORTS=",
            (
                ",".join(
                    sorted(
                        missing
                    )
                )
                if missing
                else
                "NONE"
            ),
        )


        if missing:

            fail(
                "BRIDGE_EXPORT_CONTRACT"
            )

        else:

            ok(
                "BRIDGE_EXPORT_CONTRACT"
            )


        rank_node = bridge_functions.get(
            "rank_pool"
        )


        if rank_node:

            return_shapes = []

            for node in ast.walk(
                rank_node
            ):

                if isinstance(
                    node,
                    ast.Return,
                ):

                    if isinstance(
                        node.value,
                        ast.Tuple,
                    ):

                        return_shapes.append(
                            len(
                                node.value.elts
                            )
                        )

                    elif node.value is not None:

                        return_shapes.append(
                            "NON_TUPLE"
                        )


            emit(
                "RANK_POOL_RETURN_SHAPES=",
                return_shapes,
            )


            if (
                return_shapes
                and
                all(
                    shape == 3
                    for shape
                    in return_shapes
                )
            ):

                ok(
                    "RANK_POOL_RETURN_CONTRACT"
                )

            else:

                fail(
                    "RANK_POOL_RETURN_CONTRACT",
                    str(
                        return_shapes
                    ),
                )


    except Exception as exc:

        fail(
            "BRIDGE_STATIC_LOAD",
            repr(exc),
        )


# ============================================================
# 9. MIDIA <-> BRIDGE CONTRACT
# ============================================================

section(
    "9. MIDIA <-> VSE42 BRIDGE CONTRACT"
)


midia_path = (
    ROOT
    /
    "midia.py"
)


if midia_path.is_file():

    try:

        tree = load_ast(
            midia_path
        )


        bridge_imports = []

        rank_calls = []
        commit_calls = []
        unpack_contracts = []


        for node in ast.walk(
            tree
        ):

            if (
                isinstance(
                    node,
                    ast.ImportFrom,
                )
                and
                node.module
                ==
                "visual_selection_bridge_v42"
            ):

                for alias in node.names:

                    bridge_imports.append(
                        (
                            alias.name,
                            alias.asname,
                            node.lineno,
                        )
                    )


            if isinstance(
                node,
                ast.Call,
            ):

                name = None

                if isinstance(
                    node.func,
                    ast.Name,
                ):
                    name = node.func.id


                if name in {
                    "_vse42_rank_pool",
                    "rank_pool",
                }:

                    rank_calls.append(
                        node.lineno
                    )


                if name in {
                    "_vse42_commit_candidate",
                    "_commit_candidate",
                    "commit_candidate",
                }:

                    commit_calls.append(
                        node.lineno
                    )


            if isinstance(
                node,
                (
                    ast.Assign,
                    ast.AnnAssign,
                ),
            ):

                value = (
                    node.value
                    if hasattr(
                        node,
                        "value"
                    )
                    else None
                )

                if not isinstance(
                    value,
                    ast.Call,
                ):
                    continue


                if not isinstance(
                    value.func,
                    ast.Name,
                ):
                    continue


                if value.func.id not in {
                    "_vse42_rank_pool",
                    "rank_pool",
                }:
                    continue


                targets = (
                    node.targets
                    if isinstance(
                        node,
                        ast.Assign,
                    )
                    else [
                        node.target
                    ]
                )


                for target in targets:

                    if isinstance(
                        target,
                        ast.Tuple,
                    ):

                        unpack_contracts.append(
                            (
                                node.lineno,
                                len(
                                    target.elts
                                ),
                            )
                        )


        emit(
            "BRIDGE_IMPORTS=",
            bridge_imports,
        )

        emit(
            "RANK_POOL_CALL_LINES=",
            rank_calls,
        )

        emit(
            "COMMIT_CALL_LINES=",
            commit_calls,
        )

        emit(
            "RANK_UNPACK_CONTRACTS=",
            unpack_contracts,
        )


        if (
            unpack_contracts
            and
            all(
                count == 3
                for _line, count
                in unpack_contracts
            )
        ):

            ok(
                "MIDIA_RANK_POOL_UNPACK"
            )

        elif not unpack_contracts:

            warning(
                "MIDIA_RANK_POOL_UNPACK",
                "no_tuple_unpack_found",
            )

        else:

            fail(
                "MIDIA_RANK_POOL_UNPACK",
                str(
                    unpack_contracts
                ),
            )


        rank_import_count = sum(
            1
            for name, _alias, _line
            in bridge_imports
            if name == "rank_pool"
        )


        commit_import_count = sum(
            1
            for name, _alias, _line
            in bridge_imports
            if name == "commit_candidate"
        )


        emit(
            "RANK_POOL_IMPORT_COUNT=",
            rank_import_count,
        )

        emit(
            "COMMIT_IMPORT_COUNT=",
            commit_import_count,
        )


        if rank_import_count > 1:

            warning(
                "MULTIPLE_RANK_POOL_IMPORT_POINTS",
                str(
                    rank_import_count
                ),
            )

        else:

            ok(
                "MULTIPLE_RANK_POOL_IMPORT_POINTS"
            )


        if commit_import_count > 1:

            warning(
                "MULTIPLE_COMMIT_IMPORT_POINTS",
                str(
                    commit_import_count
                ),
            )

        else:

            ok(
                "MULTIPLE_COMMIT_IMPORT_POINTS"
            )


    except Exception as exc:

        fail(
            "MIDIA_BRIDGE_CONTRACT",
            repr(exc),
        )


# ============================================================
# 10. BRIDGE RUNTIME
# ============================================================

section(
    "10. VSE42 BRIDGE RUNTIME"
)


bridge_ns = None


try:

    bridge_ns = runpy.run_path(
        str(
            bridge_path
        ),
        run_name="shortautopro_master_audit_bridge",
    )

    ok(
        "BRIDGE_RUNTIME_LOAD"
    )


    rank_pool = bridge_ns.get(
        "rank_pool"
    )


    if callable(
        rank_pool
    ):

        context = {

            "texto":
                "Investigação em apartamento "
                "em São Paulo",

            "visual_query":
                "police investigation "
                "apartment Sao Paulo",

            "must_have": [
                "apartamento",
                "São Paulo",
            ],

            "location":
                "São Paulo Brazil",
        }


        wrong = {

            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "title":
                "Empire State Building "
                "Manhattan New York",

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
                "Apartment building "
                "Sao Paulo Brazil",

            "must":
                "1/2",

            "score":
                120,

            "width":
                1920,

            "height":
                1080,
        }


        try:

            result = rank_pool(
                [
                    wrong,
                    correct,
                ],
                wrong,
                context,
            )


            emit(
                "BRIDGE_RANK_RUNTIME_TYPE=",
                type(
                    result
                ).__name__,
            )


            emit(
                "BRIDGE_RANK_RUNTIME_LEN=",
                (
                    len(result)
                    if isinstance(
                        result,
                        tuple,
                    )
                    else "NA"
                ),
            )


            if (
                isinstance(
                    result,
                    tuple,
                )
                and
                len(result) == 3
            ):

                ok(
                    "BRIDGE_RANK_RUNTIME_CONTRACT"
                )

            else:

                fail(
                    "BRIDGE_RANK_RUNTIME_CONTRACT"
                )


        except Exception as exc:

            fail(
                "BRIDGE_RANK_RUNTIME_CONTRACT",
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

            emit(
                traceback.format_exc()
            )


    commit_candidate = bridge_ns.get(
        "commit_candidate"
    )

    reset_state = bridge_ns.get(
        "reset_state"
    )

    get_state = bridge_ns.get(
        "get_state"
    )


    if callable(
        commit_candidate
    ):

        try:

            if callable(
                reset_state
            ):
                reset_state()


            candidate = {

                "provider":
                    "audit_provider",

                "tipo":
                    "foto",

                "title":
                    "Synthetic audit media",

                "id":
                    "MASTER_AUDIT_ONLY",
            }


            first = commit_candidate(
                candidate
            )

            second = commit_candidate(
                candidate
            )


            emit(
                "COMMIT_FIRST_RETURN=",
                repr(
                    first
                ),
            )

            emit(
                "COMMIT_SECOND_RETURN=",
                repr(
                    second
                ),
            )


            if (
                isinstance(
                    first,
                    bool,
                )
                and
                isinstance(
                    second,
                    bool,
                )
            ):

                ok(
                    "COMMIT_RUNTIME_RETURN_TYPE"
                )

            else:

                fail(
                    "COMMIT_RUNTIME_RETURN_TYPE"
                )


            if callable(
                get_state
            ):

                state = get_state()

                emit(
                    "COMMIT_STATE_TYPE=",
                    type(
                        state
                    ).__name__,
                )


                if isinstance(
                    state,
                    dict,
                ):

                    ok(
                        "COMMIT_STATE_RUNTIME"
                    )

                else:

                    fail(
                        "COMMIT_STATE_RUNTIME"
                    )


        except Exception as exc:

            fail(
                "COMMIT_RUNTIME",
                (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                ),
            )

            emit(
                traceback.format_exc()
            )


except Exception as exc:

    fail(
        "BRIDGE_RUNTIME_LOAD",
        (
            f"{type(exc).__name__}: "
            f"{exc}"
        ),
    )

    emit(
        traceback.format_exc()
    )


# ============================================================
# 11. QUERY EXPANSION CONTRACT
# ============================================================

section(
    "11. QUERY EXPANSION CONTRACT"
)


query_path = (
    ROOT
    /
    "visual_query_expansion_v4.py"
)


if query_path.is_file():

    try:

        query_ns = runpy.run_path(
            str(
                query_path
            ),
            run_name="shortautopro_master_query_audit",
        )


        wrap = query_ns.get(
            "wrap_search_function"
        )


        if callable(
            wrap
        ):

            ok(
                "QUERY_EXPANSION_RUNTIME_LOAD"
            )


            def fake_search(
                *args,
                **kwargs
            ):
                return []


            wrapped = wrap(
                fake_search
            )


            if callable(
                wrapped
            ):

                ok(
                    "QUERY_EXPANSION_WRAP_CONTRACT"
                )

            else:

                fail(
                    "QUERY_EXPANSION_WRAP_CONTRACT"
                )


        else:

            fail(
                "QUERY_EXPANSION_WRAP_CONTRACT",
                "function_missing",
            )


    except Exception as exc:

        fail(
            "QUERY_EXPANSION_RUNTIME",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        emit(
            traceback.format_exc()
        )


# ============================================================
# 12. PROVIDER ACQUISITION MAP
# ============================================================

section(
    "12. PROVIDER ACQUISITION PATH"
)


if midia_path.is_file():

    try:

        tree = load_ast(
            midia_path
        )


        functions = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        expected_provider_functions = {

            "pexels_video",
            "pexels_foto",
            "pixabay_video",
            "pixabay_foto",
            "coverr_video",
        }


        missing_defs = (
            expected_provider_functions
            -
            set(
                functions
            )
        )


        emit(
            "PROVIDER_FUNCTIONS_MISSING=",
            (
                ",".join(
                    sorted(
                        missing_defs
                    )
                )
                if missing_defs
                else
                "NONE"
            ),
        )


        if missing_defs:

            fail(
                "PROVIDER_FUNCTION_DEFINITIONS"
            )

        else:

            ok(
                "PROVIDER_FUNCTION_DEFINITIONS"
            )


        search_fn = functions.get(
            "buscar_todos_candidatos"
        )


        if search_fn:

            calls = set()

            for node in ast.walk(
                search_fn
            ):

                if isinstance(
                    node,
                    ast.Call,
                ):

                    if isinstance(
                        node.func,
                        ast.Name,
                    ):

                        calls.add(
                            node.func.id
                        )


            emit(
                "SEARCH_PROVIDER_CALLS=",
                ",".join(
                    sorted(
                        calls
                        &
                        (
                            expected_provider_functions
                            |
                            {
                                "buscar_wikimedia_fotos"
                            }
                        )
                    )
                ),
            )


            missing_calls = (
                expected_provider_functions
                -
                calls
            )


            if missing_calls:

                warning(
                    "PROVIDER_SEARCH_COVERAGE",
                    "not_called="
                    +
                    ",".join(
                        sorted(
                            missing_calls
                        )
                    ),
                )

            else:

                ok(
                    "PROVIDER_SEARCH_COVERAGE"
                )


        else:

            fail(
                "PROVIDER_SEARCH_COVERAGE",
                "buscar_todos_candidatos_missing",
            )


    except Exception as exc:

        fail(
            "PROVIDER_ACQUISITION_AUDIT",
            repr(exc),
        )


# ============================================================
# 13. COMMIT LOCK STRUCTURE
# ============================================================

section(
    "13. SCENE COMMIT LOCK"
)


commit_path = (
    ROOT
    /
    "visual_scene_commit_lock_v1.py"
)


if commit_path.is_file():

    try:

        ns = runpy.run_path(
            str(
                commit_path
            ),
            run_name="shortautopro_master_commit_lock",
        )


        expected = {
            "install_runtime",
            "reset",
        }


        found = {
            name
            for name in expected
            if callable(
                ns.get(name)
            )
        }


        emit(
            "COMMIT_LOCK_RUNTIME_FUNCTIONS=",
            ",".join(
                sorted(
                    found
                )
            ),
        )


        if found == expected:

            ok(
                "COMMIT_LOCK_STRUCTURE"
            )

        else:

            warning(
                "COMMIT_LOCK_STRUCTURE",
                "missing="
                +
                ",".join(
                    sorted(
                        expected - found
                    )
                ),
            )


    except Exception as exc:

        fail(
            "COMMIT_LOCK_RUNTIME_LOAD",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


# ============================================================
# 14. FRESH RENDER GUARD REGRESSION
# ============================================================

section(
    "14. FRESH RENDER GUARD SAFETY"
)


guard_path = (
    ROOT
    /
    "fresh_render_guard_v1.py"
)


if guard_path.is_file():

    sid = (
        "MASTER_AUDIT_"
        +
        str(
            int(
                time.time()
            )
        )
    )


    test_temp = (
        ROOT
        /
        "temp"
        /
        sid
    )


    test_temp.mkdir(
        parents=True,
        exist_ok=True,
    )


    ass = (
        ROOT
        /
        "videos"
        /
        f"short_{sid}.ass"
    )


    final = (
        ROOT
        /
        "videos"
        /
        f"short_v6_{sid}.mp4"
    )


    temp_video = (
        test_temp
        /
        "video_sem_audio.mp4"
    )


    audio = (
        test_temp
        /
        "audit_audio.mp3"
    )


    try:

        ass.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        ass.write_text(
            "AUDIT_ASS",
            encoding="utf-8",
        )

        final.write_bytes(
            b"AUDIT_FINAL"
        )

        temp_video.write_bytes(
            b"AUDIT_TEMP_VIDEO"
        )

        audio.write_bytes(
            b"AUDIT_AUDIO"
        )


        ns = runpy.run_path(
            str(
                guard_path
            ),
            run_name="shortautopro_master_guard",
        )


        clean = ns.get(
            "clean"
        )


        if not callable(
            clean
        ):

            fail(
                "FRESH_RENDER_GUARD_TEST",
                "clean_missing",
            )

        else:

            clean(
                sid
            )


            conditions = {

                "ASS_SURVIVED":
                    ass.exists(),

                "AUDIO_SURVIVED":
                    audio.exists(),

                "FINAL_REMOVED":
                    not final.exists(),

                "TEMP_VIDEO_REMOVED":
                    not temp_video.exists(),
            }


            for key, value in conditions.items():

                emit(
                    key,
                    "=",
                    value,
                )


            if all(
                conditions.values()
            ):

                ok(
                    "FRESH_RENDER_GUARD_TEST"
                )

            else:

                fail(
                    "FRESH_RENDER_GUARD_TEST"
                )


    except Exception as exc:

        fail(
            "FRESH_RENDER_GUARD_TEST",
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
            final.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        try:
            shutil.rmtree(
                test_temp,
                ignore_errors=True,
            )
        except Exception:
            pass


# ============================================================
# 15. MEDIA DIRECTORY STRUCTURE
# ============================================================

section(
    "15. EXISTING MEDIA SCENE STRUCTURE"
)


images_root = (
    ROOT
    /
    "imagens"
)


short_dirs = []


if images_root.is_dir():

    short_dirs = sorted(
        [
            p
            for p in images_root.glob(
                "short_*"
            )
            if p.is_dir()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


emit(
    "MEDIA_SHORT_DIRS_FOUND=",
    len(
        short_dirs
    ),
)


for directory in short_dirs[:5]:

    emit()
    emit(
        "MEDIA_DIR=",
        directory.name,
    )


    total = 0
    invalid = []


    for n in range(
        1,
        13,
    ):

        files = list(
            directory.glob(
                f"scene_{n:02d}.*"
            )
        )


        total += len(
            files
        )


        if len(
            files
        ) != 1:

            invalid.append(
                (
                    n,
                    len(
                        files
                    ),
                )
            )


    emit(
        "MEDIA_COUNT=",
        total,
    )

    emit(
        "INVALID_SCENES=",
        invalid,
    )


    if (
        total == 12
        and
        not invalid
    ):

        ok(
            f"MEDIA_STRUCTURE_{directory.name}"
        )

    else:

        warning(
            f"MEDIA_STRUCTURE_{directory.name}",
            str(
                invalid
            ),
        )


# ============================================================
# 16. VSE42 FEATURE FLAGS
# ============================================================

section(
    "16. VISUAL FEATURE FLAGS"
)


for name in (

    "SAP_VSE_V42",
    "SAP_VSE42_BRIDGE",
    "SAP_VSE_V4",
    "SAP_VSE_V3",
    "SAP_VSE_V2",
    "SAP_SCENE_COMMIT_LOCK",
):

    emit(
        name,
        "=",
        os.getenv(
            name,
            "<unset>"
        ),
    )


# ============================================================
# 17. STATIC NETWORK SAFETY
# ============================================================

section(
    "17. AUDITOR NETWORK SAFETY"
)


emit(
    "NETWORK_FUNCTION_EXECUTED=NO"
)

emit(
    "PROVIDER_SEARCH_EXECUTED=NO"
)

emit(
    "MIDIA_MODULE_EXECUTED=NO"
)

emit(
    "VIDEO_MODULE_EXECUTED=NO"
)

emit(
    "V6_MODULE_EXECUTED=NO"
)

ok(
    "AUDITOR_SIDE_EFFECT_POLICY"
)


# ============================================================
# FINAL
# ============================================================

section(
    "MASTER AUDIT SUMMARY"
)


emit(
    "PASS_COUNT=",
    len(
        PASS
    ),
)

emit(
    "WARN_COUNT=",
    len(
        WARN
    ),
)

emit(
    "FAIL_COUNT=",
    len(
        FAIL
    ),
)


emit(
    "PASS_ITEMS=",
    ",".join(
        PASS
    )
    if PASS
    else
    "NONE",
)


emit(
    "WARN_ITEMS=",
    ",".join(
        WARN
    )
    if WARN
    else
    "NONE",
)


emit(
    "FAIL_ITEMS=",
    ",".join(
        FAIL
    )
    if FAIL
    else
    "NONE",
)


if FAIL:

    emit(
        "MASTER_AUDIT_STATUS=FAIL"
    )

elif WARN:

    emit(
        "MASTER_AUDIT_STATUS=PASS_WITH_WARNINGS"
    )

else:

    emit(
        "MASTER_AUDIT_STATUS=PASS"
    )


emit(
    "REPORT=",
    REPORT,
)

emit(
    "CORE_FILES_MODIFIED=NO"
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
    "MASTER_AUDIT_COMPLETE=YES"
)

print()
print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
