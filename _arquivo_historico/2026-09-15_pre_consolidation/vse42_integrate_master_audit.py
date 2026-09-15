#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import importlib.util
import inspect
import json
import os
import py_compile
import re
import runpy
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

MIDIA = ROOT / "midia.py"
VSE4 = ROOT / "visual_selection_engine_v4.py"
GUARD = ROOT / "media_diversity_guard_v1.py"
GERAR = ROOT / "gerar_short.sh"

TEMP = ROOT / "temp"
BACKUPS = ROOT / "backups"
LOGS = ROOT / "logs" / "producao"

REPORT = TEMP / "VSE42_MASTER_AUDIT.txt"

MARKER = (
    "# SHORTAUTOPRO VSE4.2 FINAL POOL GATE"
)

SHORT_ID = os.environ.get(
    "SHORT_ID",
    "2026-09-02_2358",
).strip()


TEMP.mkdir(
    parents=True,
    exist_ok=True,
)

BACKUPS.mkdir(
    parents=True,
    exist_ok=True,
)

LOGS.mkdir(
    parents=True,
    exist_ok=True,
)


FAILURES = []
WARNINGS = []
PASSES = []

BACKUP_MIDIA = None
MIDIA_WAS_PATCHED = False


# ============================================================
# OUTPUT
# ============================================================

class Tee:

    def __init__(
        self,
        *streams,
    ):
        self.streams = streams

    def write(
        self,
        data,
    ):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(
        self,
    ):
        for stream in self.streams:
            stream.flush()


report_handle = REPORT.open(
    "w",
    encoding="utf-8",
)

sys.stdout = Tee(
    sys.__stdout__,
    report_handle,
)

sys.stderr = Tee(
    sys.__stderr__,
    report_handle,
)


def section(title):

    print()
    print("=" * 76)
    print(title)
    print("=" * 76)


def ok(name):

    PASSES.append(
        name
    )

    print(
        f"{name}=PASS"
    )


def warn(
    name,
    detail="",
):

    WARNINGS.append(
        (
            name,
            detail,
        )
    )

    print(
        f"{name}=WARN"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def bad(
    name,
    detail="",
):

    FAILURES.append(
        (
            name,
            detail,
        )
    )

    print(
        f"{name}=FAIL"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def sha256(path):

    path = Path(path)

    if not path.is_file():
        return None

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


def run(
    cmd,
    capture=True,
    timeout=120,
):

    try:

        return subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            capture_output=capture,
            timeout=timeout,
        )

    except Exception as exc:

        class Result:
            returncode = 999
            stdout = ""
            stderr = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

        return Result()


def load_module(
    path,
    name,
):

    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if (
        spec is None
        or
        spec.loader is None
    ):
        raise RuntimeError(
            f"não foi possível carregar {path}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


def rollback_midia():

    global MIDIA_WAS_PATCHED

    if (
        MIDIA_WAS_PATCHED
        and
        BACKUP_MIDIA
        and
        Path(BACKUP_MIDIA).is_file()
    ):

        shutil.copy2(
            BACKUP_MIDIA,
            MIDIA,
        )

        MIDIA_WAS_PATCHED = False

        print(
            "MIDIA_ROLLBACK=PASS"
        )


def critical(
    name,
    detail="",
):

    bad(
        name,
        detail,
    )

    rollback_midia()

    print()
    print(
        "CRITICAL_ABORT=YES"
    )

    final_summary()

    raise SystemExit(1)


def final_summary():

    section(
        "FINAL MASTER AUDIT SUMMARY"
    )

    print(
        f"PASS_COUNT={len(PASSES)}"
    )

    print(
        f"WARNING_COUNT={len(WARNINGS)}"
    )

    print(
        f"FAIL_COUNT={len(FAILURES)}"
    )

    if WARNINGS:

        print()
        print(
            "WARNINGS:"
        )

        for name, detail in WARNINGS:

            print(
                f"  - {name}"
                +
                (
                    f": {detail}"
                    if detail
                    else ""
                )
            )

    if FAILURES:

        print()
        print(
            "FAILURES:"
        )

        for name, detail in FAILURES:

            print(
                f"  - {name}"
                +
                (
                    f": {detail}"
                    if detail
                    else ""
                )
            )


    if not FAILURES:

        print()
        print(
            "MASTER_AUDIT=PASS"
        )

    else:

        print()
        print(
            "MASTER_AUDIT=FAIL"
        )


    print(
        f"REPORT={REPORT}"
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
        "TERMUX_CONTINUA_ABERTO=SIM"
    )


# ============================================================
# 1. ENVIRONMENT
# ============================================================

section(
    "1. ENVIRONMENT"
)

print(
    f"ROOT={ROOT}"
)

print(
    f"SHORT_ID={SHORT_ID}"
)

print(
    f"PYTHON={sys.version.split()[0]}"
)

print(
    f"DATE={time.strftime('%Y-%m-%d %H:%M:%S')}"
)


required_files = (
    MIDIA,
    VSE4,
    GUARD,
    GERAR,
)


for path in required_files:

    if path.is_file():
        print(
            f"FOUND={path.name}"
        )
    else:
        critical(
            "REQUIRED_FILE_MISSING",
            str(path),
        )


ok(
    "ENVIRONMENT"
)


# ============================================================
# 2. BACKUP
# ============================================================

section(
    "2. CORE BACKUP"
)

stamp = time.strftime(
    "%Y%m%d_%H%M%S"
)

backup_dir = (
    BACKUPS
    /
    f"vse42_master_audit_{stamp}"
)

backup_dir.mkdir(
    parents=True,
    exist_ok=True,
)


for path in (
    MIDIA,
    VSE4,
    GUARD,
    GERAR,
):

    shutil.copy2(
        path,
        backup_dir / path.name,
    )


BACKUP_MIDIA = (
    backup_dir
    /
    MIDIA.name
)


print(
    f"BACKUP_DIR={backup_dir}"
)

print(
    f"MIDIA_HASH_BEFORE={sha256(MIDIA)}"
)

print(
    f"VSE4_HASH={sha256(VSE4)}"
)

print(
    f"GUARD_HASH={sha256(GUARD)}"
)

ok(
    "CORE_BACKUP"
)


# ============================================================
# 3. CORE COMPILE
# ============================================================

section(
    "3. CORE COMPILE"
)

for path in (
    MIDIA,
    VSE4,
    GUARD,
):

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        ok(
            f"COMPILE_{path.name}"
        )

    except Exception as exc:

        critical(
            f"COMPILE_{path.name}",
            str(exc),
        )


shell = run(
    [
        "bash",
        "-n",
        str(GERAR),
    ],
)

if shell.returncode == 0:

    ok(
        "GERAR_SHORT_SYNTAX"
    )

else:

    critical(
        "GERAR_SHORT_SYNTAX",
        shell.stderr.strip(),
    )


# ============================================================
# 4. VSE4 MUST PASS
# ============================================================

section(
    "4. VSE4 SELF TEST"
)

vse = run(
    [
        sys.executable,
        str(VSE4),
    ],
    capture=True,
)


if vse.stdout:

    print(
        vse.stdout.strip()
    )


if vse.returncode != 0:

    if vse.stderr:
        print(
            vse.stderr.strip()
        )

    critical(
        "VSE4_SELF_TEST",
        f"returncode={vse.returncode}",
    )


ok(
    "VSE4_SELF_TEST"
)


# ============================================================
# 5. VSE4 SEMANTIC REGRESSION
# ============================================================

section(
    "5. VSE4 SEMANTIC / GEO REGRESSION"
)

try:

    ns = runpy.run_path(
        str(VSE4),
        run_name="vse42_regression",
    )

    score_candidate = ns[
        "score_candidate"
    ]

    geo_hits = ns[
        "geo_hits"
    ]

    concept_hits = ns[
        "concept_hits"
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


    print(
        "SCENE_GEO=",
        sorted(
            geo_hits(
                scene
            )
        ),
    )

    print(
        "WRONG_GEO=",
        sorted(
            geo_hits(
                wrong[
                    "title"
                ]
            )
        ),
    )

    print(
        "CORRECT_GEO=",
        sorted(
            geo_hits(
                correct[
                    "title"
                ]
            )
        ),
    )

    print(
        "SCENE_CONCEPTS=",
        sorted(
            concept_hits(
                scene
            )
        ),
    )

    print(
        "WRONG_HARD_MISMATCH=",
        a.get(
            "hard_mismatch"
        ),
    )

    print(
        "CORRECT_HARD_MISMATCH=",
        b.get(
            "hard_mismatch"
        ),
    )

    print(
        "WRONG_EFFECTIVE=",
        a.get(
            "effective"
        ),
    )

    print(
        "CORRECT_EFFECTIVE=",
        b.get(
            "effective"
        ),
    )


    if (
        a.get(
            "hard_mismatch"
        )
        is not True
    ):

        critical(
            "GEO_HARD_MISMATCH",
            "New York não foi bloqueado "
            "para cena São Paulo",
        )


    if (
        b.get(
            "hard_mismatch"
        )
        is True
    ):

        critical(
            "CORRECT_GEO_FALSE_BLOCK",
            "São Paulo foi marcado "
            "como incompatível",
        )


    if (
        float(
            b.get(
                "effective",
                -999999,
            )
        )
        <=
        float(
            a.get(
                "effective",
                999999,
            )
        )
    ):

        critical(
            "SEMANTIC_RANKING",
            "candidato correto não venceu "
            "candidato geograficamente errado",
        )


    ok(
        "GEO_HARD_MISMATCH"
    )

    ok(
        "SEMANTIC_RANKING"
    )


except KeyError as exc:

    critical(
        "VSE4_API",
        f"missing {exc}",
    )


except Exception as exc:

    traceback.print_exc()

    critical(
        "VSE4_REGRESSION_RUNTIME",
        f"{type(exc).__name__}: {exc}",
    )


# ============================================================
# 6. GUARD API
# ============================================================

section(
    "6. GUARD API AUDIT"
)

try:

    guard = load_module(
        GUARD,
        "sap_guard_master_audit",
    )

except Exception as exc:

    traceback.print_exc()

    critical(
        "GUARD_IMPORT",
        f"{type(exc).__name__}: {exc}",
    )


required_guard_api = (
    "install_runtime",
    "rerank_pool",
)


missing_guard = [
    name
    for name in required_guard_api
    if not callable(
        getattr(
            guard,
            name,
            None,
        )
    )
]


if missing_guard:

    critical(
        "GUARD_API",
        ",".join(
            missing_guard
        ),
    )


for name in required_guard_api:

    fn = getattr(
        guard,
        name,
    )

    print(
        f"{name}_SIGNATURE="
        f"{inspect.signature(fn)}"
    )


ok(
    "GUARD_API"
)


# ============================================================
# 7. PROVIDER ACQUISITION MAP
# ============================================================

section(
    "7. PROVIDER ACQUISITION AUDIT"
)

src = MIDIA.read_text(
    encoding="utf-8",
)

tree = ast.parse(
    src
)


functions = {
    node.name:
        node
    for node in tree.body
    if isinstance(
        node,
        ast.FunctionDef,
    )
}


provider_functions = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
)


for name in provider_functions:

    if name in functions:

        node = functions[
            name
        ]

        print(
            f"PROVIDER_FUNCTION={name} "
            f"lines={node.lineno}-"
            f"{node.end_lineno}"
        )

    else:

        warn(
            "PROVIDER_FUNCTION_MISSING",
            name,
        )


busca_fn = functions.get(
    "buscar_todos_candidatos"
)


if busca_fn is None:

    critical(
        "BUSCAR_TODOS_CANDIDATOS",
        "função ausente",
    )


calls = set()


for node in ast.walk(
    busca_fn
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


expected_calls = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}


for name in sorted(
    expected_calls
):

    if name in calls:

        ok(
            f"ACQUISITION_CALL_{name}"
        )

    else:

        warn(
            f"ACQUISITION_CALL_{name}",
            "não chamado dentro de "
            "buscar_todos_candidatos",
        )


wiki_present = any(
    name in calls
    for name in (
        "buscar_wikimedia_fotos",
        "enriquecer_wikimedia_5_2",
    )
)


if wiki_present:

    ok(
        "ACQUISITION_WIKIMEDIA"
    )

else:

    warn(
        "ACQUISITION_WIKIMEDIA",
        "nenhuma chamada encontrada",
    )


print(
    "BUSCAR_TODOS_CALLS="
    +
    ",".join(
        sorted(
            calls
        )
    )
)


# ============================================================
# 8. FIND FINAL POOL ANCHOR
# ============================================================

section(
    "8. FINAL POOL ANCHOR AUDIT"
)

src = MIDIA.read_text(
    encoding="utf-8"
)


marker_count = src.count(
    MARKER
)


print(
    f"MARKER_COUNT={marker_count}"
)


if marker_count > 1:

    critical(
        "VSE42_MARKER_DUPLICATED",
        str(
            marker_count
        ),
    )


tree = ast.parse(
    src
)


candidates = []


for node in ast.walk(
    tree
):

    if not isinstance(
        node,
        (
            ast.Assign,
            ast.AnnAssign,
        ),
    ):
        continue


    if isinstance(
        node,
        ast.Assign,
    ):

        targets = node.targets
        value = node.value

    else:

        targets = [
            node.target
        ]
        value = node.value


    is_pool = any(
        isinstance(
            target,
            ast.Name,
        )
        and
        target.id == "pool"
        for target in targets
    )


    if not is_pool:
        continue


    if value is None:
        continue


    names = {
        child.id
        for child in ast.walk(
            value
        )
        if isinstance(
            child,
            ast.Name,
        )
    }


    if "escolhido" not in names:
        continue


    segment = (
        ast.get_source_segment(
            src,
            node,
        )
        or ""
    )


    candidates.append(
        (
            node,
            segment,
        )
    )


print(
    "FINAL_POOL_ANCHORS="
    f"{len(candidates)}"
)


for index, (
    node,
    segment,
) in enumerate(
    candidates,
    start=1,
):

    print(
        f"ANCHOR_{index}_LINE="
        f"{node.lineno}"
    )

    print(
        f"ANCHOR_{index}_SOURCE="
        +
        " ".join(
            segment.split()
        )[:700]
    )


if marker_count == 0:

    if len(
        candidates
    ) != 1:

        critical(
            "FINAL_POOL_ANCHOR",
            "esperado exatamente 1; "
            f"encontrado {len(candidates)}",
        )


    # ========================================================
    # 9. PATCH FINAL POOL
    # ========================================================

    section(
        "9. INTEGRATE VSE4.2 FINAL POOL GATE"
    )


    node, _segment = (
        candidates[0]
    )


    lines = src.splitlines(
        keepends=True
    )


    source_line = lines[
        node.lineno - 1
    ]


    indent = source_line[
        :
        len(source_line)
        -
        len(
            source_line.lstrip()
        )
    ]


    block = (
        "\n"
        f"{indent}{MARKER}\n"
        f"{indent}try:\n"
        f"{indent}    import os as _sap_visual_os_v42\n"
        f"{indent}    if _sap_visual_os_v42.getenv('SAP_VSE4', '1') != '0':\n"
        f"{indent}        from media_diversity_guard_v1 import install_runtime as _sap_visual_install_v42\n"
        f"{indent}        from media_diversity_guard_v1 import rerank_pool as _sap_visual_rerank_v42\n"
        f"{indent}        _sap_visual_install_v42(globals())\n"
        f"{indent}        pool = _sap_visual_rerank_v42(\n"
        f"{indent}            pool,\n"
        f"{indent}            locals(),\n"
        f"{indent}            escolhido,\n"
        f"{indent}        )\n"
        f"{indent}        if pool:\n"
        f"{indent}            escolhido = pool[0]\n"
        f"{indent}            print('VSE42_FINAL_POOL_GATE=PASS')\n"
        f"{indent}        else:\n"
        f"{indent}            print('VSE42_FINAL_POOL_GATE=EMPTY_FAIL_OPEN')\n"
        f"{indent}    else:\n"
        f"{indent}        print('VSE42_FINAL_POOL_GATE=DISABLED')\n"
        f"{indent}except Exception as _sap_visual_error_v42:\n"
        f"{indent}    print(\n"
        f"{indent}        'VSE42_FINAL_POOL_GATE=FAIL_OPEN ' +\n"
        f"{indent}        type(_sap_visual_error_v42).__name__ +\n"
        f"{indent}        ': ' +\n"
        f"{indent}        str(_sap_visual_error_v42)\n"
        f"{indent}    )\n"
    )


    insert_index = (
        node.end_lineno
    )


    patched = (
        "".join(
            lines[
                :insert_index
            ]
        )
        +
        block
        +
        "".join(
            lines[
                insert_index:
            ]
        )
    )


    MIDIA.write_text(
        patched,
        encoding="utf-8",
    )


    MIDIA_WAS_PATCHED = True


    print(
        "VSE42_FINAL_POOL_PATCH=INSTALLED"
    )


else:

    section(
        "9. INTEGRATE VSE4.2 FINAL POOL GATE"
    )

    print(
        "VSE42_FINAL_POOL_PATCH="
        "ALREADY_INSTALLED"
    )


# ============================================================
# 10. POST-PATCH COMPILE
# ============================================================

section(
    "10. POST-INTEGRATION COMPILE"
)

try:

    py_compile.compile(
        str(MIDIA),
        doraise=True,
    )

except Exception as exc:

    traceback.print_exc()

    critical(
        "MIDIA_POST_PATCH_COMPILE",
        str(exc),
    )


ok(
    "MIDIA_POST_PATCH_COMPILE"
)


post_src = MIDIA.read_text(
    encoding="utf-8"
)


post_marker_count = (
    post_src.count(
        MARKER
    )
)


print(
    f"POST_MARKER_COUNT={post_marker_count}"
)


if post_marker_count != 1:

    critical(
        "POST_MARKER_COUNT",
        str(
            post_marker_count
        ),
    )


ok(
    "VSE42_MARKER_UNIQUE"
)


print(
    f"MIDIA_HASH_AFTER={sha256(MIDIA)}"
)


# ============================================================
# 11. PATCH STATIC STRUCTURE
# ============================================================

section(
    "11. VSE4.2 STATIC INTEGRATION CHECK"
)


required_patch_tokens = (
    "rerank_pool as _sap_visual_rerank_v42",
    "_sap_visual_rerank_v42(",
    "escolhido = pool[0]",
    "SAP_VSE4",
    "FAIL_OPEN",
)


for token in required_patch_tokens:

    if token in post_src:

        ok(
            "PATCH_TOKEN_"
            +
            re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                token,
            )[:40]
        )

    else:

        critical(
            "PATCH_TOKEN_MISSING",
            token,
        )


# ============================================================
# 12. ROOT PYTHON COMPILE SWEEP
# ============================================================

section(
    "12. ROOT PYTHON COMPILE SWEEP"
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


print(
    f"ROOT_PY_FILES={len(python_files)}"
)

print(
    f"ROOT_PY_COMPILE_FAILURES="
    f"{len(compile_failures)}"
)


for name, detail in compile_failures[
    :30
]:

    print(
        f"COMPILE_FAIL={name} | {detail}"
    )


if compile_failures:

    bad(
        "ROOT_PYTHON_COMPILE_SWEEP",
        f"{len(compile_failures)} arquivos",
    )

else:

    ok(
        "ROOT_PYTHON_COMPILE_SWEEP"
    )


# ============================================================
# 13. ROOT SHELL SYNTAX SWEEP
# ============================================================

section(
    "13. ROOT SHELL SYNTAX SWEEP"
)


shell_files = sorted(
    ROOT.glob(
        "*.sh"
    )
)


shell_failures = []


for path in shell_files:

    result = run(
        [
            "bash",
            "-n",
            str(path),
        ]
    )

    if result.returncode != 0:

        shell_failures.append(
            (
                path.name,
                result.stderr.strip(),
            )
        )


print(
    f"ROOT_SH_FILES={len(shell_files)}"
)

print(
    f"ROOT_SH_FAILURES="
    f"{len(shell_failures)}"
)


for name, detail in shell_failures:

    print(
        f"SHELL_FAIL={name} | {detail}"
    )


if shell_failures:

    bad(
        "ROOT_SHELL_SYNTAX_SWEEP",
        f"{len(shell_failures)} arquivos",
    )

else:

    ok(
        "ROOT_SHELL_SYNTAX_SWEEP"
    )


# ============================================================
# 14. CORE DUPLICATE DEFINITIONS
# ============================================================

section(
    "14. CORE DUPLICATE DEFINITION AUDIT"
)


for path in (
    MIDIA,
    VSE4,
    GUARD,
):

    source = path.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        source
    )

    names = {}

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            names.setdefault(
                node.name,
                [],
            ).append(
                node.lineno
            )


    duplicates = {
        name:
            lines
        for name, lines
        in names.items()
        if len(
            lines
        ) > 1
    }


    print(
        f"{path.name}_DUPLICATE_TOP_LEVEL="
        f"{len(duplicates)}"
    )


    for name, lines in duplicates.items():

        print(
            f"DUPLICATE={path.name}:"
            f"{name}:"
            f"{lines}"
        )


    if duplicates:

        warn(
            f"DUPLICATE_DEFS_{path.name}",
            str(
                duplicates
            )[:1000],
        )

    else:

        ok(
            f"DUPLICATE_DEFS_{path.name}"
        )


# ============================================================
# 15. DANGEROUS PATTERN AUDIT
# ============================================================

section(
    "15. CORE RISK PATTERN AUDIT"
)


risk_patterns = {
    "SHELL_TRUE":
        r"shell\s*=\s*True",

    "OS_SYSTEM":
        r"\bos\.system\s*\(",

    "RM_RF":
        r"\brm\s+-rf\b",

    "BARE_EXCEPT":
        r"except\s*:",
}


for path in (
    MIDIA,
    VSE4,
    GUARD,
):

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for label, pattern in risk_patterns.items():

        matches = list(
            re.finditer(
                pattern,
                source,
                flags=re.IGNORECASE,
            )
        )


        print(
            f"{path.name}_{label}="
            f"{len(matches)}"
        )


        if matches:

            warn(
                f"{path.name}_{label}",
                f"{len(matches)} ocorrência(s)",
            )


# ============================================================
# 16. CURRENT MEDIA INTEGRITY
# ============================================================

section(
    "16. CURRENT 12-SCENE MEDIA AUDIT"
)


media_dir = (
    ROOT
    /
    "imagens"
    /
    f"short_{SHORT_ID}"
)


print(
    f"MEDIA_DIR={media_dir}"
)


media_total = 0
bad_scene_count = 0
scene_hashes = {}


if not media_dir.is_dir():

    warn(
        "MEDIA_DIR",
        "short atual não encontrado",
    )

else:

    for number in range(
        1,
        13,
    ):

        prefix = (
            f"scene_{number:02d}."
        )


        matches = [
            path
            for path in media_dir.iterdir()
            if (
                path.is_file()
                and
                path.name.startswith(
                    prefix
                )
            )
        ]


        media_total += len(
            matches
        )


        print()
        print(
            f"SCENE_{number:02d}_COUNT="
            f"{len(matches)}"
        )


        if len(
            matches
        ) != 1:

            bad_scene_count += 1


        for path in matches:

            file_hash = sha256(
                path
            )

            scene_hashes[
                str(path)
            ] = file_hash


            print(
                f"SCENE_FILE="
                f"{path.name}"
            )

            print(
                f"SCENE_BYTES="
                f"{path.stat().st_size}"
            )

            print(
                f"SCENE_SHA256="
                f"{file_hash}"
            )


    print()
    print(
        f"MEDIA_TOTAL={media_total}"
    )

    print(
        f"INVALID_SCENE_COUNT="
        f"{bad_scene_count}"
    )


    duplicate_hashes = {}


    for path, h in scene_hashes.items():

        duplicate_hashes.setdefault(
            h,
            [],
        ).append(
            path
        )


    exact_duplicates = {
        h:
            paths
        for h, paths
        in duplicate_hashes.items()
        if (
            h
            and
            len(paths) > 1
        )
    }


    print(
        f"EXACT_MEDIA_DUPLICATE_GROUPS="
        f"{len(exact_duplicates)}"
    )


    for h, paths in exact_duplicates.items():

        print(
            f"DUPLICATE_HASH={h}"
        )

        for path in paths:
            print(
                f"  {path}"
            )


    if (
        media_total == 12
        and
        bad_scene_count == 0
    ):

        ok(
            "MEDIA_12_SCENE_STRUCTURE"
        )

    else:

        warn(
            "MEDIA_12_SCENE_STRUCTURE",
            f"total={media_total}, "
            f"bad={bad_scene_count}",
        )


    if exact_duplicates:

        warn(
            "EXACT_MEDIA_DUPLICATES",
            str(
                len(exact_duplicates)
            ),
        )

    else:

        ok(
            "EXACT_MEDIA_DUPLICATES"
        )


# ============================================================
# 17. PIPELINE INPUTS
# ============================================================

section(
    "17. PIPELINE INPUT AUDIT"
)


expected_inputs = {

    "SCRIPT":
        ROOT
        /
        "roteiros"
        /
        f"short_{SHORT_ID}.txt",

    "SCENE_MAP":
        ROOT
        /
        "roteiros"
        /
        f"scene_map_{SHORT_ID}.json",

    "AUDIO":
        ROOT
        /
        "audios"
        /
        f"short_{SHORT_ID}.mp3",

    "ASS":
        ROOT
        /
        "videos"
        /
        f"short_{SHORT_ID}.ass",

    "VIDEO_BASE":
        ROOT
        /
        "temp"
        /
        SHORT_ID
        /
        "video_sem_audio.mp4",

    "FINAL":
        ROOT
        /
        "videos"
        /
        f"short_v6_{SHORT_ID}.mp4",
}


for label, path in expected_inputs.items():

    if (
        path.is_file()
        and
        path.stat().st_size > 0
    ):

        print(
            f"{label}=PASS | "
            f"{path.stat().st_size} | "
            f"{path}"
        )

    else:

        if label in (
            "FINAL",
            "VIDEO_BASE",
        ):

            warn(
                label,
                "artefato de render ausente",
            )

        else:

            warn(
                label,
                f"ausente: {path}",
            )


# ============================================================
# 18. JSON VALIDATION
# ============================================================

section(
    "18. CURRENT JSON VALIDATION"
)


json_patterns = (
    ROOT
    /
    "roteiros"
)


json_failures = []


if json_patterns.is_dir():

    relevant_json = sorted(
        json_patterns.glob(
            f"*{SHORT_ID}*.json"
        )
    )


    print(
        f"CURRENT_JSON_FILES="
        f"{len(relevant_json)}"
    )


    for path in relevant_json:

        try:

            json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            print(
                f"JSON_PASS={path.name}"
            )

        except Exception as exc:

            json_failures.append(
                (
                    path.name,
                    str(exc),
                )
            )

            print(
                f"JSON_FAIL={path.name} | "
                f"{exc}"
            )


if json_failures:

    bad(
        "CURRENT_JSON_VALIDATION",
        str(
            json_failures
        )[:1200],
    )

else:

    ok(
        "CURRENT_JSON_VALIDATION"
    )


# ============================================================
# 19. RENDER GUARD SAFETY
# ============================================================

section(
    "19. FRESH RENDER GUARD SAFETY"
)


fresh_guard = (
    ROOT
    /
    "fresh_render_guard_v1.py"
)


if fresh_guard.is_file():

    try:

        source = fresh_guard.read_text(
            encoding="utf-8"
        )


        protected_ass = (
            '".ass"'
            in source
            or
            "'.ass'"
            in source
        )


        protected_audio = any(
            token in source
            for token in (
                '".mp3"',
                "'.mp3'",
                '".wav"',
                "'.wav'",
            )
        )


        print(
            f"FRESH_GUARD_ASS_PROTECTION="
            f"{protected_ass}"
        )

        print(
            f"FRESH_GUARD_AUDIO_PROTECTION="
            f"{protected_audio}"
        )


        if protected_ass:

            ok(
                "FRESH_GUARD_ASS_PROTECTION"
            )

        else:

            warn(
                "FRESH_GUARD_ASS_PROTECTION",
                ".ass não encontrado "
                "na proteção",
            )


        if protected_audio:

            ok(
                "FRESH_GUARD_AUDIO_PROTECTION"
            )

        else:

            warn(
                "FRESH_GUARD_AUDIO_PROTECTION",
                "áudio não encontrado "
                "na proteção",
            )


    except Exception as exc:

        warn(
            "FRESH_RENDER_GUARD_AUDIT",
            str(exc),
        )

else:

    warn(
        "FRESH_RENDER_GUARD",
        "arquivo ausente",
    )


# ============================================================
# 20. FINAL CORE HASHES
# ============================================================

section(
    "20. FINAL CORE HASHES"
)


for path in (
    MIDIA,
    VSE4,
    GUARD,
    GERAR,
    ROOT / "video.py",
    ROOT / "v6.py",
):

    if path.is_file():

        print(
            f"SHA256 {path.name} "
            f"{sha256(path)}"
        )


# ============================================================
# 21. CERTIFICATION DECISION
# ============================================================

section(
    "21. CERTIFICATION DECISION"
)


critical_fail_labels = {
    name
    for name, _detail
    in FAILURES
}


if critical_fail_labels:

    print(
        "VSE42_INTEGRATION_CERTIFIED=FAIL"
    )

else:

    print(
        "VSE42_INTEGRATION_CERTIFIED=PASS"
    )


if not FAILURES:

    print(
        "CORE_SAFE_TO_CANARY=YES"
    )

else:

    print(
        "CORE_SAFE_TO_CANARY=NO"
    )


final_summary()
