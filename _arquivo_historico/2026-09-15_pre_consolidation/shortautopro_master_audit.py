#!/usr/bin/env python3

from pathlib import Path
from collections import Counter, defaultdict
import ast
import builtins
import hashlib
import json
import os
import py_compile
import runpy
import shutil
import subprocess
import symtable
import time
import traceback


ROOT = Path.home() / "ShortAutoPro"

STAMP = time.strftime(
    "%Y%m%d_%H%M%S"
)

REPORT = (
    ROOT
    / "temp"
    / f"SHORTAUTOPRO_MASTER_AUDIT_{STAMP}.txt"
)

JSON_REPORT = (
    ROOT
    / "manifests"
    / f"master_audit_{STAMP}.json"
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

JSON_REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT.write_text(
    "",
    encoding="utf-8",
)

RESULTS = []


def emit(text=""):

    text = str(text)

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
    emit(
        "=" * 70
    )

    emit(
        title
    )

    emit(
        "=" * 70
    )


def result(
    status,
    name,
    detail="",
):

    status = str(
        status
    ).upper()

    record = {
        "status": status,
        "name": name,
        "detail": str(detail),
    }

    RESULTS.append(
        record
    )

    line = (
        f"[{status}] "
        f"{name}"
    )

    if detail:

        line += (
            f" | {detail}"
        )

    emit(
        line
    )


def source(path):

    try:

        return Path(
            path
        ).read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:

        return ""


def parse_python(path):

    try:

        return ast.parse(
            source(path)
        )

    except Exception as exc:

        result(
            "FAIL",
            f"AST_{Path(path).name}",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        return None


def sha256(path):

    path = Path(
        path
    )

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


def run_cmd(
    command,
    timeout=120,
):

    try:

        proc = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )

        return (
            proc.returncode,
            proc.stdout,
        )

    except Exception as exc:

        return (
            999,
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


def get_function(
    tree,
    name,
):

    if tree is None:
        return None

    for node in tree.body:

        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and
            node.name == name
        ):

            return node

    return None


def detect_short_id():

    explicit = os.getenv(
        "SHORT_ID",
        "",
    ).strip()

    if explicit:

        return explicit


    base = (
        ROOT
        / "imagens"
    )

    if not base.is_dir():
        return ""


    candidates = []

    for path in base.glob(
        "short_*"
    ):

        if not path.is_dir():
            continue

        try:

            candidates.append(
                (
                    path.stat().st_mtime,
                    path.name[
                        len("short_"):
                    ],
                )
            )

        except Exception:
            pass


    if not candidates:
        return ""


    candidates.sort(
        reverse=True
    )

    return candidates[
        0
    ][1]


section(
    "SHORTAUTOPRO MASTER AUDIT"
)

emit(
    f"DATE={time.ctime()}"
)

emit(
    f"ROOT={ROOT}"
)

SHORT_ID = detect_short_id()

emit(
    f"SHORT_ID={SHORT_ID or 'NOT_DETECTED'}"
)


# ============================================================
# 1. CRITICAL FILES
# ============================================================

section(
    "1. CRITICAL FILES"
)


critical_files = [

    "gerar_short.sh",

    "midia.py",

    "video.py",

    "v6.py",

    "legenda_dinamica.py",

    "visual_selection_engine_v4.py",

    "media_diversity_guard_v1.py",

    "media_provenance_capture_v1.py",

    "visual_scene_commit_lock_v1.py",

    "visual_must_rescue_v1.py",

    "fresh_render_guard_v1.py",

    "render_input_fingerprint_v1.py",
]


for name in critical_files:

    path = (
        ROOT
        / name
    )

    if path.is_file():

        result(
            "PASS",
            f"FILE_{name}",
            (
                f"{path.stat().st_size} bytes "
                f"sha256={sha256(path)[:16]}"
            ),
        )

    else:

        result(
            "FAIL",
            f"FILE_{name}",
            "missing",
        )


# ============================================================
# 2. PYTHON COMPILE - ROOT
# ============================================================

section(
    "2. PYTHON COMPILE"
)


python_files = sorted(
    ROOT.glob(
        "*.py"
    )
)

compile_failures = []


for path in python_files:

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        compile_failures.append(
            (
                path.name,
                str(exc),
            )
        )


emit(
    f"PYTHON_FILES_TESTED={len(python_files)}"
)


if compile_failures:

    for name, error in compile_failures:

        result(
            "FAIL",
            f"PY_COMPILE_{name}",
            error,
        )

else:

    result(
        "PASS",
        "PYTHON_COMPILE_ALL",
        (
            f"{len(python_files)} "
            "root Python files"
        ),
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)


shell_files = sorted(
    ROOT.glob(
        "*.sh"
    )
)

shell_failures = []


for path in shell_files:

    code, output = run_cmd(
        [
            "bash",
            "-n",
            str(path),
        ],
        timeout=30,
    )

    if code != 0:

        shell_failures.append(
            (
                path.name,
                output.strip(),
            )
        )


emit(
    f"SHELL_FILES_TESTED={len(shell_files)}"
)


if shell_failures:

    for name, error in shell_failures:

        result(
            "FAIL",
            f"SHELL_SYNTAX_{name}",
            error,
        )

else:

    result(
        "PASS",
        "SHELL_SYNTAX_ALL",
        (
            f"{len(shell_files)} "
            "root shell files"
        ),
    )


# ============================================================
# 4. DUPLICATE TOP-LEVEL DEFINITIONS
# ============================================================

section(
    "4. DUPLICATE DEFINITIONS"
)


duplicate_targets = [

    "midia.py",

    "video.py",

    "v6.py",

    "legenda_dinamica.py",

    "visual_selection_engine_v4.py",
]


for name in duplicate_targets:

    path = (
        ROOT
        / name
    )

    tree = parse_python(
        path
    )

    if not tree:
        continue


    defs = Counter()


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
            ] += 1


    duplicated = {

        key: count

        for key, count
        in defs.items()

        if count > 1
    }


    if duplicated:

        result(
            "WARN",
            f"DUPLICATE_DEFS_{name}",
            json.dumps(
                duplicated,
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

    else:

        result(
            "PASS",
            f"DUPLICATE_DEFS_{name}",
            "none",
        )


# ============================================================
# 5. VSE4 GLOBAL / STATIC INTEGRITY
# ============================================================

section(
    "5. VSE4 STATIC INTEGRITY"
)


vse_path = (
    ROOT
    / "visual_selection_engine_v4.py"
)

vse_src = source(
    vse_path
)


try:

    table = symtable.symtable(
        vse_src,
        str(vse_path),
        "exec",
    )


    module_defined = set()


    for symbol in table.get_symbols():

        if (
            symbol.is_assigned()
            or
            symbol.is_imported()
            or
            symbol.is_namespace()
        ):

            module_defined.add(
                symbol.get_name()
            )


    builtin_names = set(
        dir(builtins)
    )


    unresolved = set()


    def walk_scope(scope):

        for child in scope.get_children():

            for symbol in child.get_symbols():

                name = symbol.get_name()

                if not symbol.is_referenced():
                    continue

                if not symbol.is_global():
                    continue

                if name in module_defined:
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

        result(
            "FAIL",
            "VSE4_UNRESOLVED_GLOBALS",
            ",".join(
                sorted(
                    unresolved
                )
            ),
        )

    else:

        result(
            "PASS",
            "VSE4_UNRESOLVED_GLOBALS",
            "NONE",
        )


except Exception as exc:

    result(
        "FAIL",
        "VSE4_GLOBAL_AUDIT",
        (
            f"{type(exc).__name__}: "
            f"{exc}"
        ),
    )


# ============================================================
# 6. VSE4 REQUIRED SYMBOLS
# ============================================================

section(
    "6. VSE4 REQUIRED SYMBOLS"
)


vse_tree = parse_python(
    vse_path
)


required_functions = {

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


required_globals = {

    "CONCEPTS",

    "GEO_GROUPS",

    "GENERIC_LIFESTYLE",

    "MEDICINE_TERMS",

    "STOP",

    "ROOT",
}


module_functions = set()

module_assignments = set()


if vse_tree:

    for node in vse_tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            module_functions.add(
                node.name
            )


        elif isinstance(
            node,
            (
                ast.Assign,
                ast.AnnAssign,
            ),
        ):

            targets = []

            if isinstance(
                node,
                ast.Assign,
            ):

                targets = node.targets

            else:

                targets = [
                    node.target
                ]


            for target in targets:

                if isinstance(
                    target,
                    ast.Name,
                ):

                    module_assignments.add(
                        target.id
                    )


missing_functions = sorted(
    required_functions
    -
    module_functions
)


missing_globals = sorted(
    required_globals
    -
    module_assignments
)


if missing_functions:

    result(
        "FAIL",
        "VSE4_REQUIRED_FUNCTIONS",
        ",".join(
            missing_functions
        ),
    )

else:

    result(
        "PASS",
        "VSE4_REQUIRED_FUNCTIONS",
        "all",
    )


if missing_globals:

    result(
        "FAIL",
        "VSE4_REQUIRED_GLOBALS",
        ",".join(
            missing_globals
        ),
    )

else:

    result(
        "PASS",
        "VSE4_REQUIRED_GLOBALS",
        "all",
    )


# ============================================================
# 7. VSE4 RUNTIME / SELF TEST
# ============================================================

section(
    "7. VSE4 RUNTIME / SELF TEST"
)


vse_ns = None


try:

    vse_ns = runpy.run_path(
        str(vse_path),
        run_name="shortautopro_master_audit",
    )

    try:

        vse_ns[
            "self_test"
        ]()

        result(
            "PASS",
            "VSE4_SELF_TEST",
        )

    except AssertionError:

        result(
            "FAIL",
            "VSE4_SELF_TEST",
            "AssertionError",
        )

        emit(
            traceback.format_exc()
        )

    except Exception as exc:

        result(
            "FAIL",
            "VSE4_SELF_TEST",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        emit(
            traceback.format_exc()
        )


except Exception as exc:

    result(
        "FAIL",
        "VSE4_MODULE_LOAD",
        (
            f"{type(exc).__name__}: "
            f"{exc}"
        ),
    )


# ============================================================
# 8. DIRECT VSE4 SEMANTICS
# ============================================================

section(
    "8. VSE4 DIRECT SEMANTIC TESTS"
)


if vse_ns:

    try:

        score_candidate = vse_ns[
            "score_candidate"
        ]

        geo_hits = vse_ns[
            "geo_hits"
        ]


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
            "WRONG_SCORE="
            +
            json.dumps(
                a,
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            )
        )

        emit(
            "CORRECT_SCORE="
            +
            json.dumps(
                b,
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            )
        )


        if (
            a.get(
                "hard_mismatch"
            )
            is True
        ):

            result(
                "PASS",
                "VSE4_GEO_HARD_MISMATCH",
            )

        else:

            result(
                "FAIL",
                "VSE4_GEO_HARD_MISMATCH",
                (
                    "São Paulo scene accepted "
                    "Empire State/New York"
                ),
            )


        if (
            b.get(
                "hard_mismatch"
            )
            is False
        ):

            result(
                "PASS",
                "VSE4_CORRECT_GEO_ACCEPTED",
            )

        else:

            result(
                "FAIL",
                "VSE4_CORRECT_GEO_ACCEPTED",
                (
                    "São Paulo candidate "
                    "marked hard mismatch"
                ),
            )


        effective_wrong = float(
            a.get(
                "effective",
                -999999,
            )
        )

        effective_correct = float(
            b.get(
                "effective",
                -999999,
            )
        )


        if (
            effective_correct
            >
            effective_wrong
        ):

            result(
                "PASS",
                "VSE4_GEO_RANKING",
                (
                    f"correct={effective_correct} "
                    f"wrong={effective_wrong}"
                ),
            )

        else:

            result(
                "FAIL",
                "VSE4_GEO_RANKING",
                (
                    f"correct={effective_correct} "
                    f"wrong={effective_wrong}"
                ),
            )


        sp_geo = set(
            geo_hits(
                scene
            )
        )

        ny_geo = set(
            geo_hits(
                wrong[
                    "title"
                ]
            )
        )


        emit(
            f"SCENE_GEO={sorted(sp_geo)}"
        )

        emit(
            f"WRONG_GEO={sorted(ny_geo)}"
        )


        if (
            sp_geo
            and
            ny_geo
            and
            sp_geo != ny_geo
        ):

            result(
                "PASS",
                "VSE4_GEO_DETECTION",
            )

        else:

            result(
                "FAIL",
                "VSE4_GEO_DETECTION",
            )


        # ----------------------------------------------------
        # False medical association
        # ----------------------------------------------------

        forensic_scene = (
            "O laudo pericial revelou "
            "evidências importantes "
            "na investigação"
        )


        forensic_good = {

            "provider":
                "Pexels",

            "tipo":
                "foto",

            "title":
                "Forensic laboratory evidence investigation",

            "score":
                120,

            "must":
                "2/2",

            "width":
                1920,

            "height":
                1080,
        }


        medicine_bad = {

            "provider":
                "Pixabay",

            "tipo":
                "foto",

            "title":
                "Pills medication pharmacy tablets",

            "score":
                180,

            "must":
                "1/2",

            "width":
                1920,

            "height":
                1080,
        }


        good_result = score_candidate(
            forensic_good,
            forensic_scene,
            {
                "providers": [],
                "groups": [],
                "types": [],
                "keys": [],
            },
        )

        bad_result = score_candidate(
            medicine_bad,
            forensic_scene,
            {
                "providers": [],
                "groups": [],
                "types": [],
                "keys": [],
            },
        )


        if (
            float(
                good_result.get(
                    "effective",
                    -999999,
                )
            )
            >
            float(
                bad_result.get(
                    "effective",
                    -999999,
                )
            )
        ):

            result(
                "PASS",
                "VSE4_MEDICINE_FALSE_ASSOCIATION",
            )

        else:

            result(
                "WARN",
                "VSE4_MEDICINE_FALSE_ASSOCIATION",
                (
                    "medicine stock media "
                    "not sufficiently penalized"
                ),
            )


        # ----------------------------------------------------
        # Generic lifestyle
        # ----------------------------------------------------

        crime_scene = (
            "A polícia iniciou a investigação "
            "na cena do crime"
        )


        documentary = {

            "provider":
                "Pexels",

            "tipo":
                "video",

            "title":
                "Police crime scene investigation",

            "score":
                120,

            "must":
                "2/2",

            "width":
                1920,

            "height":
                1080,
        }


        lifestyle = {

            "provider":
                "Pixabay",

            "tipo":
                "video",

            "title":
                "Happy woman relaxing in bedroom",

            "score":
                180,

            "must":
                "1/2",

            "width":
                1920,

            "height":
                1080,
        }


        doc_result = score_candidate(
            documentary,
            crime_scene,
            {
                "providers": [],
                "groups": [],
                "types": [],
                "keys": [],
            },
        )

        life_result = score_candidate(
            lifestyle,
            crime_scene,
            {
                "providers": [],
                "groups": [],
                "types": [],
                "keys": [],
            },
        )


        if (
            float(
                doc_result.get(
                    "effective",
                    -999999,
                )
            )
            >
            float(
                life_result.get(
                    "effective",
                    -999999,
                )
            )
        ):

            result(
                "PASS",
                "VSE4_GENERIC_LIFESTYLE_CONTROL",
            )

        else:

            result(
                "WARN",
                "VSE4_GENERIC_LIFESTYLE_CONTROL",
                (
                    "generic lifestyle media "
                    "can outrank documentary media"
                ),
            )


    except Exception as exc:

        result(
            "FAIL",
            "VSE4_DIRECT_SEMANTICS",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        emit(
            traceback.format_exc()
        )


# ============================================================
# 9. MIDIA.PY INTEGRATION
# ============================================================

section(
    "9. MIDIA.PY INTEGRATION"
)


midia_path = (
    ROOT
    / "midia.py"
)

midia_src = source(
    midia_path
)


integration_markers = {

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
            "SCENE_COMMIT"
            in midia_src
            or
            "visual_scene_commit_lock"
            in midia_src
        ),

    "PROVENANCE":
        (
            "media_provenance_capture"
            in midia_src
        ),

    "DIVERSITY":
        (
            "media_diversity_guard"
            in midia_src
        ),
}


for name, active in integration_markers.items():

    if active:

        result(
            "PASS",
            f"MIDIA_INTEGRATION_{name}",
            "reference found",
        )

    else:

        level = (
            "WARN"
            if name in {
                "VSE4",
                "VSE3",
                "COMMIT_LOCK",
            }
            else
            "FAIL"
        )

        result(
            level,
            f"MIDIA_INTEGRATION_{name}",
            "reference not found",
        )


result(
    "PASS",
    "MIDIA_SHA256",
    sha256(
        midia_path
    )
    if midia_path.is_file()
    else
    "missing",
)


# ============================================================
# 10. PROVIDER ACQUISITION
# ============================================================

section(
    "10. PROVIDER ACQUISITION"
)


midia_tree = parse_python(
    midia_path
)


provider_functions = [

    "pexels_video",

    "pexels_foto",

    "pixabay_video",

    "pixabay_foto",

    "coverr_video",
]


defined_provider_functions = set()


if midia_tree:

    for node in midia_tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            if (
                node.name
                in
                provider_functions
            ):

                defined_provider_functions.add(
                    node.name
                )


for name in provider_functions:

    if (
        name
        in
        defined_provider_functions
    ):

        result(
            "PASS",
            f"PROVIDER_FUNCTION_{name}",
        )

    else:

        result(
            "FAIL",
            f"PROVIDER_FUNCTION_{name}",
            "missing",
        )


buscar_node = get_function(
    midia_tree,
    "buscar_todos_candidatos",
)


provider_calls = set()


if buscar_node:

    for node in ast.walk(
        buscar_node
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

            if (
                node.func.id
                in
                provider_functions
            ):

                provider_calls.add(
                    node.func.id
                )


    result(
        "PASS",
        "BUSCAR_TODOS_CANDIDATOS",
        (
            f"lines="
            f"{buscar_node.lineno}-"
            f"{buscar_node.end_lineno}"
        ),
    )

else:

    result(
        "FAIL",
        "BUSCAR_TODOS_CANDIDATOS",
        "function missing",
    )


for name in provider_functions:

    if name in provider_calls:

        result(
            "PASS",
            f"PROVIDER_CALL_{name}",
        )

    else:

        result(
            "WARN",
            f"PROVIDER_CALL_{name}",
            (
                "defined but not called "
                "inside buscar_todos_candidatos"
            ),
        )


# Environment variable NAMES only.
env_names = set()


if midia_tree:

    for node in ast.walk(
        midia_tree
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        try:

            call_name = ast.unparse(
                node.func
            )

        except Exception:

            call_name = ""


        if (
            call_name
            not in {
                "os.getenv",
                "os.environ.get",
            }
        ):

            continue


        if not node.args:
            continue


        first = node.args[
            0
        ]


        if (
            isinstance(
                first,
                ast.Constant,
            )
            and
            isinstance(
                first.value,
                str,
            )
        ):

            env_names.add(
                first.value
            )


provider_env_names = sorted(
    name
    for name in env_names
    if any(
        token in name.upper()
        for token in (
            "PEXELS",
            "PIXABAY",
            "COVERR",
            "WIKI",
        )
    )
)


emit(
    "PROVIDER_ENV_NAMES="
    +
    (
        ",".join(
            provider_env_names
        )
        if provider_env_names
        else
        "NONE_DETECTED"
    )
)


# ============================================================
# 11. CURRENT SHORT MEDIA HEALTH
# ============================================================

section(
    "11. CURRENT SHORT MEDIA HEALTH"
)


if not SHORT_ID:

    result(
        "WARN",
        "CURRENT_SHORT",
        "SHORT_ID not detected",
    )

else:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{SHORT_ID}"
    )


    if not media_dir.is_dir():

        result(
            "FAIL",
            "CURRENT_MEDIA_DIR",
            str(media_dir),
        )

    else:

        result(
            "PASS",
            "CURRENT_MEDIA_DIR",
            str(media_dir),
        )


        all_hashes = defaultdict(
            list
        )

        scene_total = 0

        invalid_scene_count = 0


        for number in range(
            1,
            13,
        ):

            pattern = (
                f"scene_{number:02d}.*"
            )

            files = [
                path

                for path
                in media_dir.glob(
                    pattern
                )

                if path.is_file()
            ]


            scene_total += len(
                files
            )


            if len(files) != 1:

                invalid_scene_count += 1

                result(
                    "FAIL",
                    f"SCENE_{number:02d}_COUNT",
                    str(
                        len(files)
                    ),
                )

                continue


            path = files[
                0
            ]

            size = path.stat().st_size

            digest = sha256(
                path
            )

            all_hashes[
                digest
            ].append(
                path.name
            )


            if size <= 0:

                result(
                    "FAIL",
                    f"SCENE_{number:02d}_SIZE",
                    (
                        f"{path.name} "
                        f"{size}"
                    ),
                )

            elif (
                path.suffix.lower()
                in {
                    ".mp4",
                    ".mov",
                    ".webm",
                }
                and
                size < 100_000
            ):

                result(
                    "WARN",
                    f"SCENE_{number:02d}_SIZE",
                    (
                        f"small video "
                        f"{size} bytes"
                    ),
                )

            elif (
                path.suffix.lower()
                in {
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                }
                and
                size < 10_000
            ):

                result(
                    "WARN",
                    f"SCENE_{number:02d}_SIZE",
                    (
                        f"small image "
                        f"{size} bytes"
                    ),
                )

            else:

                result(
                    "PASS",
                    f"SCENE_{number:02d}",
                    (
                        f"{path.name} "
                        f"{size} bytes "
                        f"{digest[:12]}"
                    ),
                )


        emit(
            f"MEDIA_TOTAL={scene_total}"
        )

        emit(
            (
                "INVALID_SCENE_COUNT="
                f"{invalid_scene_count}"
            )
        )


        duplicates = {

            digest: names

            for digest, names
            in all_hashes.items()

            if len(names) > 1
        }


        if duplicates:

            result(
                "WARN",
                "EXACT_MEDIA_DUPLICATES",
                json.dumps(
                    duplicates,
                    ensure_ascii=False,
                ),
            )

        else:

            result(
                "PASS",
                "EXACT_MEDIA_DUPLICATES",
                "none",
            )


# ============================================================
# 12. RENDER CHAIN
# ============================================================

section(
    "12. RENDER CHAIN"
)


video_src = source(
    ROOT
    / "video.py"
)

v6_src = source(
    ROOT
    / "v6.py"
)


for name, src in (
    (
        "video.py",
        video_src,
    ),
    (
        "v6.py",
        v6_src,
    ),
):

    if (
        "SHORT_ID"
        in src
        and
        "os.getenv"
        in src
    ):

        result(
            "PASS",
            f"SHORT_ID_ENV_{name}",
        )

    else:

        result(
            "FAIL",
            f"SHORT_ID_ENV_{name}",
            (
                "explicit SHORT_ID env "
                "resolver not detected"
            ),
        )


if (
    "short_{SHORT_ID}.ass"
    in v6_src
    or
    'f"short_{SHORT_ID}.ass"'
    in v6_src
):

    result(
        "PASS",
        "V6_ASS_INPUT_DECLARED",
    )

else:

    result(
        "WARN",
        "V6_ASS_INPUT_DECLARED",
        "pattern not detected",
    )


if SHORT_ID:

    render_inputs = {

        "AUDIO":
            (
                ROOT
                / "audios"
                / f"short_{SHORT_ID}.mp3"
            ),

        "ASS":
            (
                ROOT
                / "videos"
                / f"short_{SHORT_ID}.ass"
            ),

        "VIDEO_BASE":
            (
                ROOT
                / "temp"
                / SHORT_ID
                / "video_sem_audio.mp4"
            ),

        "FINAL":
            (
                ROOT
                / "videos"
                / f"short_v6_{SHORT_ID}.mp4"
            ),
    }


    for name, path in render_inputs.items():

        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            result(
                "PASS",
                f"RENDER_ASSET_{name}",
                (
                    f"{path.stat().st_size} "
                    "bytes"
                ),
            )

        else:

            result(
                "WARN",
                f"RENDER_ASSET_{name}",
                "not present",
            )


# ============================================================
# 13. FRESH RENDER GUARD SAFETY
# ============================================================

section(
    "13. FRESH RENDER GUARD"
)


guard_path = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if not guard_path.is_file():

    result(
        "FAIL",
        "FRESH_RENDER_GUARD",
        "module missing",
    )

else:

    try:

        guard_ns = runpy.run_path(
            str(guard_path),
            run_name="master_audit_guard",
        )

        clean = guard_ns[
            "clean"
        ]


        test_sid = (
            f"AUDIT_GUARD_{os.getpid()}_"
            f"{int(time.time())}"
        )


        temp_test = (
            ROOT
            / "temp"
            / test_sid
        )

        videos = (
            ROOT
            / "videos"
        )


        temp_test.mkdir(
            parents=True,
            exist_ok=True,
        )

        videos.mkdir(
            parents=True,
            exist_ok=True,
        )


        ass_test = (
            videos
            / f"short_{test_sid}.ass"
        )

        final_test = (
            videos
            / f"short_v6_{test_sid}.mp4"
        )

        temp_video = (
            temp_test
            / "video_sem_audio.mp4"
        )

        audio_test = (
            temp_test
            / "test.mp3"
        )


        ass_test.write_text(
            "protected subtitle",
            encoding="utf-8",
        )

        final_test.write_bytes(
            b"fake final"
        )

        temp_video.write_bytes(
            b"fake temp"
        )

        audio_test.write_bytes(
            b"protected audio"
        )


        clean(
            test_sid
        )


        checks = {

            "ASS_PROTECTED":
                ass_test.exists(),

            "AUDIO_PROTECTED":
                audio_test.exists(),

            "FINAL_REMOVED":
                not final_test.exists(),

            "TEMP_VIDEO_REMOVED":
                not temp_video.exists(),
        }


        for name, passed in checks.items():

            result(
                (
                    "PASS"
                    if passed
                    else
                    "FAIL"
                ),
                f"GUARD_{name}",
            )


        try:

            ass_test.unlink(
                missing_ok=True
            )

        except Exception:
            pass


        try:

            shutil.rmtree(
                temp_test,
                ignore_errors=True,
            )

        except Exception:
            pass


    except Exception as exc:

        result(
            "FAIL",
            "FRESH_RENDER_GUARD_RUNTIME",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


# ============================================================
# 14. EXECUTABLES / ENVIRONMENT
# ============================================================

section(
    "14. EXECUTABLES / ENVIRONMENT"
)


for executable in (

    "python",

    "bash",

    "ffmpeg",

    "ffprobe",
):

    resolved = shutil.which(
        executable
    )

    if resolved:

        result(
            "PASS",
            f"EXECUTABLE_{executable}",
            resolved,
        )

    else:

        result(
            "FAIL",
            f"EXECUTABLE_{executable}",
            "not found",
        )


whisper = (
    Path.home()
    / "whisper.cpp"
    / "build"
    / "bin"
    / "whisper-cli"
)

whisper_model = (
    Path.home()
    / "whisper.cpp"
    / "models"
    / "ggml-base.bin"
)


for name, path in (

    (
        "WHISPER_CLI",
        whisper,
    ),

    (
        "WHISPER_MODEL",
        whisper_model,
    ),
):

    if path.is_file():

        result(
            "PASS",
            name,
            (
                f"{path.stat().st_size} "
                "bytes"
            ),
        )

    else:

        result(
            "WARN",
            name,
            "not found",
        )


usage = shutil.disk_usage(
    ROOT
)

free_mb = (
    usage.free
    /
    1024
    /
    1024
)

emit(
    f"FREE_DISK_MB={free_mb:.1f}"
)


if free_mb < 300:

    result(
        "FAIL",
        "FREE_DISK",
        f"{free_mb:.1f} MB",
    )

elif free_mb < 800:

    result(
        "WARN",
        "FREE_DISK",
        f"{free_mb:.1f} MB",
    )

else:

    result(
        "PASS",
        "FREE_DISK",
        f"{free_mb:.1f} MB",
    )


# ============================================================
# 15. CORE HASHES / STATIC RISKS
# ============================================================

section(
    "15. CORE HASHES / STATIC RISKS"
)


for name in (

    "midia.py",

    "video.py",

    "v6.py",

    "gerar_short.sh",

    "legenda_dinamica.py",

    "visual_selection_engine_v4.py",
):

    path = (
        ROOT
        / name
    )

    if path.is_file():

        emit(
            f"SHA256 {name} "
            f"{sha256(path)}"
        )


# Detect obvious /tmp use in project core.
for name in (

    "midia.py",

    "video.py",

    "v6.py",

    "gerar_short.sh",
):

    src = source(
        ROOT
        / name
    )

    if "/tmp/" in src:

        result(
            "WARN",
            f"TMP_USAGE_{name}",
            "/tmp/ reference found",
        )

    else:

        result(
            "PASS",
            f"TMP_USAGE_{name}",
            "none",
        )


# ============================================================
# 16. FINAL SUMMARY
# ============================================================

section(
    "16. MASTER AUDIT SUMMARY"
)


counts = Counter(
    row[
        "status"
    ]
    for row in RESULTS
)


fails = [
    row
    for row in RESULTS
    if row[
        "status"
    ] == "FAIL"
]


warns = [
    row
    for row in RESULTS
    if row[
        "status"
    ] == "WARN"
]


emit(
    f"PASS_COUNT={counts.get('PASS', 0)}"
)

emit(
    f"WARN_COUNT={counts.get('WARN', 0)}"
)

emit(
    f"FAIL_COUNT={counts.get('FAIL', 0)}"
)


if fails:

    overall = (
        "FAIL"
    )

elif warns:

    overall = (
        "PASS_WITH_WARNINGS"
    )

else:

    overall = (
        "PASS"
    )


emit(
    f"MASTER_AUDIT_STATUS={overall}"
)


if fails:

    emit()
    emit(
        "===== FAILURES ====="
    )

    for row in fails:

        emit(
            (
                f"FAIL: "
                f"{row['name']} "
                f"{row['detail']}"
            )
        )


if warns:

    emit()
    emit(
        "===== WARNINGS ====="
    )

    for row in warns:

        emit(
            (
                f"WARN: "
                f"{row['name']} "
                f"{row['detail']}"
            )
        )


payload = {

    "timestamp":
        STAMP,

    "short_id":
        SHORT_ID,

    "status":
        overall,

    "counts":
        dict(
            counts
        ),

    "results":
        RESULTS,

    "text_report":
        str(
            REPORT
        ),
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
    f"REPORT={REPORT}"
)

emit(
    f"JSON_REPORT={JSON_REPORT}"
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
