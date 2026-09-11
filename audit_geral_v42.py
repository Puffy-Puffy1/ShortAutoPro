#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import py_compile
import runpy
import subprocess
import symtable
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"
TEMP = ROOT / "temp"

TEMP.mkdir(
    parents=True,
    exist_ok=True,
)

STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

REPORT = (
    TEMP
    / f"MASTER_AUDIT_V42_{STAMP}.txt"
)

JSON_REPORT = (
    TEMP
    / f"MASTER_AUDIT_V42_{STAMP}.json"
)


results = []

COUNTS = Counter()


def out(*parts):

    text = " ".join(
        str(x)
        for x in parts
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

    out()
    out(
        "=" * 72
    )
    out(title)
    out(
        "=" * 72
    )


def record(
    name,
    status,
    detail="",
    severity="critical",
):

    status = str(
        status
    ).upper()

    COUNTS[
        status
    ] += 1

    item = {
        "name": name,
        "status": status,
        "detail": str(detail),
        "severity": severity,
    }

    results.append(
        item
    )

    suffix = (
        f" | {detail}"
        if detail
        else ""
    )

    out(
        f"{name}={status}{suffix}"
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


def compile_file(path):

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        return True, ""

    except Exception as exc:

        return (
            False,
            f"{type(exc).__name__}: {exc}",
        )


def shell_syntax(path):

    try:

        result = subprocess.run(
            [
                "bash",
                "-n",
                str(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

        return (
            result.returncode == 0,
            (
                result.stderr.strip()
                or
                result.stdout.strip()
            ),
        )

    except Exception as exc:

        return (
            False,
            f"{type(exc).__name__}: {exc}",
        )


def line_of(
    text,
    pattern,
):

    for index, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        if pattern in line:
            return index

    return None


def load_source(name):

    path = ROOT / name

    if not path.is_file():
        return ""

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def unresolved_globals(path):

    src = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    table = symtable.symtable(
        src,
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

    builtin_names = set(
        dir(builtins)
    )

    unresolved = set()


    def walk(scope):

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

            walk(
                child
            )


    walk(
        table
    )

    return sorted(
        unresolved
    )


def top_level_defs(path):

    tree = ast.parse(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )

    names = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            names.append(
                node.name
            )

    return names


def function_info(
    path,
    function_name,
):

    tree = ast.parse(
        path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )

    for node in tree.body:

        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name
            ==
            function_name
        ):

            calls = []

            for sub in ast.walk(
                node
            ):

                if not isinstance(
                    sub,
                    ast.Call,
                ):
                    continue

                if isinstance(
                    sub.func,
                    ast.Name,
                ):
                    calls.append(
                        sub.func.id
                    )

                elif isinstance(
                    sub.func,
                    ast.Attribute,
                ):
                    calls.append(
                        sub.func.attr
                    )

            return {
                "start":
                    node.lineno,

                "end":
                    node.end_lineno,

                "calls":
                    calls,
            }

    return None


# ============================================================
# HEADER
# ============================================================

REPORT.write_text(
    "",
    encoding="utf-8",
)

section(
    "SHORTAUTOPRO V4.2 - MASTER AUDIT"
)

out(
    "DATE=",
    datetime.now().isoformat(),
)

out(
    "ROOT=",
    ROOT,
)

out(
    "NETWORK_TESTS=DISABLED"
)

out(
    "VIDEO_RENDER=DISABLED"
)

out(
    "MEDIA_DOWNLOAD=DISABLED"
)


# ============================================================
# 1. REQUIRED FILES
# ============================================================

section(
    "1. REQUIRED FILES"
)

required = [

    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",

    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "visual_selection_runtime_v42.py",

    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
    "media_provenance_capture_v1.py",

    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


for name in required:

    path = ROOT / name

    record(
        f"FILE_{name}",
        "PASS"
        if path.is_file()
        else "FAIL",
        severity="critical",
    )


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section(
    "2. PYTHON COMPILE"
)

python_files = [

    ROOT / name

    for name in required

    if name.endswith(
        ".py"
    )
]


for path in python_files:

    if not path.is_file():
        continue

    ok, detail = compile_file(
        path
    )

    record(
        f"COMPILE_{path.name}",
        "PASS"
        if ok
        else "FAIL",
        detail,
    )


# ============================================================
# 3. ROOT PYTHON SWEEP
# ============================================================

section(
    "3. ROOT PYTHON SWEEP"
)

root_py = sorted(
    ROOT.glob(
        "*.py"
    )
)

compile_failures = []


for path in root_py:

    ok, detail = compile_file(
        path
    )

    if not ok:

        compile_failures.append(
            (
                path.name,
                detail,
            )
        )


out(
    "ROOT_PY_FILES=",
    len(root_py),
)

out(
    "ROOT_PY_COMPILE_FAILURES=",
    len(compile_failures),
)


for name, detail in compile_failures[:30]:

    out(
        "COMPILE_FAIL=",
        name,
        "|",
        detail,
    )


record(
    "ROOT_PYTHON_COMPILE",
    "PASS"
    if not compile_failures
    else "FAIL",
    f"failures={len(compile_failures)}",
)


# ============================================================
# 4. SHELL SYNTAX
# ============================================================

section(
    "4. SHELL SYNTAX"
)

shell_files = sorted(
    ROOT.glob(
        "*.sh"
    )
)


shell_failures = []


for path in shell_files:

    ok, detail = shell_syntax(
        path
    )

    if not ok:

        shell_failures.append(
            (
                path.name,
                detail,
            )
        )


out(
    "ROOT_SH_FILES=",
    len(shell_files),
)

out(
    "ROOT_SH_FAILURES=",
    len(shell_failures),
)


for name, detail in shell_failures:

    out(
        "SHELL_FAIL=",
        name,
        "|",
        detail,
    )


record(
    "SHELL_SYNTAX_ALL",
    "PASS"
    if not shell_failures
    else "FAIL",
)


# ============================================================
# 5. STABLE CORE HASHES
# ============================================================

section(
    "5. CORE HASH REGRESSION"
)


expected_hashes = {

    "video.py":
        "756c0db576f664d474cb92676b4ad81737158f8a275bfad6348aa0a542d87b06",

    "v6.py":
        "13d1444fc2ae0198f8f070ad98238a36d7c939c6db2572c462cd9b07712286e7",

    "gerar_short.sh":
        "25af0e189440d3646de8da8772535e00ac1e8446097f5db56ed93144ab45eb7a",
}


for name, expected in expected_hashes.items():

    path = ROOT / name

    if not path.is_file():

        record(
            f"HASH_{name}",
            "FAIL",
            "arquivo ausente",
        )

        continue


    current = sha256(
        path
    )

    out(
        f"{name}_HASH={current}"
    )


    if current == expected:

        record(
            f"CORE_UNCHANGED_{name}",
            "PASS",
        )

    else:

        record(
            f"CORE_UNCHANGED_{name}",
            "WARN",
            "hash diferente do baseline conhecido",
            severity="warning",
        )


# ============================================================
# 6. TRUE GLOBAL AUDIT
# ============================================================

section(
    "6. UNRESOLVED GLOBALS"
)


global_targets = [

    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "visual_selection_runtime_v42.py",
    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
]


for name in global_targets:

    path = ROOT / name

    if not path.is_file():
        continue

    try:

        unresolved = unresolved_globals(
            path
        )

        if unresolved:

            record(
                f"GLOBALS_{name}",
                "FAIL",
                ",".join(
                    unresolved
                ),
            )

        else:

            record(
                f"GLOBALS_{name}",
                "PASS",
            )

    except Exception as exc:

        record(
            f"GLOBALS_{name}",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 7. DUPLICATE TOP LEVEL DEFINITIONS
# ============================================================

section(
    "7. DUPLICATE DEFINITIONS"
)


duplicate_targets = [

    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "visual_selection_runtime_v42.py",
    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
]


for name in duplicate_targets:

    path = ROOT / name

    if not path.is_file():
        continue

    try:

        defs = top_level_defs(
            path
        )

        dupes = sorted(
            name_
            for name_, count
            in Counter(defs).items()
            if count > 1
        )


        if dupes:

            record(
                f"DUPLICATE_DEFS_{name}",
                "WARN",
                ",".join(
                    dupes
                ),
                severity="warning",
            )

        else:

            record(
                f"DUPLICATE_DEFS_{name}",
                "PASS",
            )

    except Exception as exc:

        record(
            f"DUPLICATE_DEFS_{name}",
            "FAIL",
            str(exc),
        )


# ============================================================
# 8. MIDIA INTEGRATION MAP
# ============================================================

section(
    "8. MIDIA VSE42 INTEGRATION"
)


midia_path = ROOT / "midia.py"

midia = load_source(
    "midia.py"
)


markers = {

    "QUERY_EXPANSION":
        "VSE42_QUERY_EXPANSION_HOOK",

    "VSE417_GATE":
        "VSE4.17 FINAL GATE",

    "VSE42_FINAL_GATE":
        "VSE42 FINAL GATE",

    "VSE42_PRIMARY_RANK":
        "VSE42 PRIMARY RANK",

    "VSE42_ALT_RANK":
        "VSE42 ALT RANK",

    "VSE42_SCENE_COMMIT":
        "VSE42 SCENE COMMIT",

    "VSE42_SUCCESS_COMMIT":
        "VSE42 SUCCESS COMMIT",

    "VSE42_FIRST_SUCCESS":
        "VSE42_FIRST_SUCCESS_LOCK=COMMITTED",
}


marker_lines = {}


for key, marker in markers.items():

    line = line_of(
        midia,
        marker,
    )

    marker_lines[
        key
    ] = line

    out(
        f"{key}_LINE={line}"
    )


for key in (
    "QUERY_EXPANSION",
    "VSE42_FINAL_GATE",
    "VSE42_PRIMARY_RANK",
    "VSE42_SCENE_COMMIT",
):

    record(
        f"MIDIA_{key}",
        "PASS"
        if marker_lines.get(key)
        else "FAIL",
    )


# ============================================================
# 9. DOUBLE GATE RISK
# ============================================================

section(
    "9. GATE CONFLICT AUDIT"
)


has_417 = (
    marker_lines[
        "VSE417_GATE"
    ]
    is not None
)

has_42 = (
    marker_lines[
        "VSE42_FINAL_GATE"
    ]
    is not None
)


if has_417 and has_42:

    record(
        "DOUBLE_FINAL_GATE",
        "WARN",
        (
            "VSE4.17 e VSE4.2 estão ativos "
            "no mesmo fluxo"
        ),
        severity="warning",
    )

else:

    record(
        "DOUBLE_FINAL_GATE",
        "PASS",
    )


# ============================================================
# 10. PROVIDER ACQUISITION
# ============================================================

section(
    "10. PROVIDER ACQUISITION"
)


try:

    info = function_info(
        midia_path,
        "buscar_todos_candidatos",
    )

except Exception:

    info = None


provider_calls = {

    "buscar_wikimedia_fotos",
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}


if info:

    out(
        "BUSCAR_TODOS_START=",
        info["start"],
    )

    out(
        "BUSCAR_TODOS_END=",
        info["end"],
    )


    calls = set(
        info[
            "calls"
        ]
    )


    for call in sorted(
        provider_calls
    ):

        record(
            f"PROVIDER_CALL_{call}",
            "PASS"
            if call in calls
            else "FAIL",
        )

else:

    record(
        "BUSCAR_TODOS_CANDIDATOS",
        "FAIL",
        "função não localizada",
    )


# ============================================================
# 11. QUERY HOOK ORDER
# ============================================================

section(
    "11. QUERY HOOK ORDER"
)


if info:

    query_line = marker_lines[
        "QUERY_EXPANSION"
    ]


    if (
        query_line
        and
        query_line
        >
        info[
            "end"
        ]
    ):

        record(
            "QUERY_HOOK_AFTER_FUNCTION",
            "PASS",
        )

    else:

        record(
            "QUERY_HOOK_AFTER_FUNCTION",
            "FAIL",
            (
                f"function_end={info['end']} "
                f"hook={query_line}"
            ),
        )


# ============================================================
# 12. DOWNLOAD / COMMIT STRUCTURE
# ============================================================

section(
    "12. DOWNLOAD AND COMMIT STRUCTURE"
)


download_calls = midia.count(
    "baixar_candidato_5_2("
)

scene_commit_count = midia.count(
    "VSE42_SCENE_COMMIT=FIRST_SUCCESS"
)

success_commit_count = midia.count(
    "VSE42_FIRST_SUCCESS_LOCK=COMMITTED"
)


out(
    "DOWNLOAD_CALLS=",
    download_calls,
)

out(
    "SCENE_COMMIT_MARKERS=",
    scene_commit_count,
)

out(
    "SUCCESS_COMMIT_MARKERS=",
    success_commit_count,
)


record(
    "DOWNLOAD_FUNCTION_PRESENT",
    "PASS"
    if "def baixar_candidato_5_2(" in midia
    else "FAIL",
)


if scene_commit_count >= 1:

    record(
        "SCENE_COMMIT_PRESENT",
        "PASS",
    )

else:

    record(
        "SCENE_COMMIT_PRESENT",
        "FAIL",
    )


if (
    scene_commit_count > 0
    and
    success_commit_count > 0
):

    record(
        "MULTIPLE_COMMIT_LAYERS",
        "WARN",
        (
            "bridge commit + runtime note_commit "
            "presentes"
        ),
        severity="warning",
    )


# ============================================================
# 13. COMMIT LOCK WRAPPER
# ============================================================

section(
    "13. SCENE COMMIT LOCK"
)


commit_src = load_source(
    "visual_scene_commit_lock_v1.py"
)


checks = {

    "FLAG":
        "SAP_SCENE_COMMIT_LOCK"
        in commit_src,

    "BLOCK":
        "SCENE_COMMIT_LOCK=BLOCKED"
        in commit_src,

    "COMMIT":
        "SCENE_COMMIT_LOCK=COMMITTED"
        in commit_src,

    "DOWNLOAD_WRAP":
        "baixar_candidato_5_2"
        in commit_src,
}


for key, ok in checks.items():

    record(
        f"SCENE_LOCK_{key}",
        "PASS"
        if ok
        else "FAIL",
    )


# ============================================================
# 14. DIVERSITY WRAPPER STACK
# ============================================================

section(
    "14. DIVERSITY WRAPPER STACK"
)


div_src = load_source(
    "media_diversity_guard_v1.py"
)


install_count = div_src.count(
    "\ndef install("
)


out(
    "DIVERSITY_INSTALL_DEFINITIONS=",
    install_count,
)


if install_count > 1:

    record(
        "DIVERSITY_INSTALL_REDEFINED",
        "WARN",
        (
            "install() redefinido "
            f"{install_count} vezes"
        ),
        severity="warning",
    )

else:

    record(
        "DIVERSITY_INSTALL_REDEFINED",
        "PASS",
    )


record(
    "DIVERSITY_SCENE_COMMIT_BRIDGE",
    "PASS"
    if "_SAP_SCENE_COMMIT_LOCK_BRIDGE"
    in div_src
    else "FAIL",
)


# ============================================================
# 15. VSE4 SELF TEST
# ============================================================

section(
    "15. VSE4 SELF TEST"
)


vse_path = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if vse_path.is_file():

    try:

        test = subprocess.run(
            [
                "python",
                str(vse_path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=45,
        )


        output = (
            test.stdout
            +
            "\n"
            +
            test.stderr
        ).strip()


        out(
            "VSE4_SELF_TEST_RC=",
            test.returncode,
        )


        if output:

            for line in output.splitlines()[
                -25:
            ]:
                out(
                    "VSE4>",
                    line,
                )


        record(
            "VSE4_SELF_TEST",
            "PASS"
            if test.returncode == 0
            else "FAIL",
        )

    except Exception as exc:

        record(
            "VSE4_SELF_TEST",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 16. VSE4 SYNTHETIC QUALITY TESTS
# ============================================================

section(
    "16. VSE4 SYNTHETIC QUALITY"
)


try:

    ns = runpy.run_path(
        str(vse_path),
        run_name="sap_master_audit_v42",
    )


    score_candidate = ns[
        "score_candidate"
    ]


    state = {

        "providers": [
            "pixabay",
            "pixabay",
        ],

        "groups": [],

        "types": [],

        "keys": [],
    }


    # --------------------------------------------------------
    # Geography contradiction
    # --------------------------------------------------------

    scene_geo = (
        "Investigação em apartamento "
        "na cidade de São Paulo Brasil"
    )


    wrong_geo = {

        "provider": "Pixabay",

        "tipo": "foto",

        "title":
            "Empire State Building "
            "Manhattan New York",

        "must": "2/2",

        "score": 220,

        "width": 1920,

        "height": 1080,
    }


    correct_geo = {

        "provider": "Wikimedia",

        "tipo": "foto",

        "title":
            "Apartment building "
            "Sao Paulo Brazil",

        "must": "1/2",

        "score": 120,

        "width": 1920,

        "height": 1080,
    }


    geo_bad = score_candidate(
        wrong_geo,
        scene_geo,
        state,
    )


    geo_good = score_candidate(
        correct_geo,
        scene_geo,
        state,
    )


    out(
        "GEO_BAD=",
        json.dumps(
            geo_bad,
            ensure_ascii=False,
            default=str,
        ),
    )


    out(
        "GEO_GOOD=",
        json.dumps(
            geo_good,
            ensure_ascii=False,
            default=str,
        ),
    )


    record(
        "GEO_HARD_MISMATCH",
        "PASS"
        if geo_bad.get(
            "hard_mismatch"
        ) is True
        else "FAIL",
    )


    record(
        "GEO_CORRECT_NOT_MISMATCH",
        "PASS"
        if geo_good.get(
            "hard_mismatch"
        ) is False
        else "FAIL",
    )


    if (
        "effective"
        in geo_good
        and
        "effective"
        in geo_bad
    ):

        record(
            "GEO_CORRECT_RANKS_HIGHER",
            "PASS"
            if (
                geo_good[
                    "effective"
                ]
                >
                geo_bad[
                    "effective"
                ]
            )
            else "FAIL",
        )


    # --------------------------------------------------------
    # Medicine false association
    # --------------------------------------------------------

    scene_forensic = (
        "O laudo pericial encontrou "
        "indícios e evidências "
        "na cena do crime."
    )


    pills = {

        "provider": "Pixabay",

        "tipo": "foto",

        "title":
            "Pills medicine medication "
            "tablets on desk",

        "must": "1/2",

        "score": 180,

        "width": 1920,

        "height": 1080,
    }


    forensic = {

        "provider": "Pexels",

        "tipo": "foto",

        "title":
            "Forensic laboratory evidence "
            "crime investigation",

        "must": "2/2",

        "score": 150,

        "width": 1920,

        "height": 1080,
    }


    p1 = score_candidate(
        pills,
        scene_forensic,
        state,
    )


    p2 = score_candidate(
        forensic,
        scene_forensic,
        state,
    )


    out(
        "MEDICINE_BAD_EFFECTIVE=",
        p1.get(
            "effective"
        ),
    )

    out(
        "FORENSIC_GOOD_EFFECTIVE=",
        p2.get(
            "effective"
        ),
    )


    if (
        p1.get(
            "effective"
        )
        is not None
        and
        p2.get(
            "effective"
        )
        is not None
    ):

        record(
            "FALSE_MEDICINE_ASSOCIATION",
            "PASS"
            if (
                p2[
                    "effective"
                ]
                >
                p1[
                    "effective"
                ]
            )
            else "FAIL",
        )


    # --------------------------------------------------------
    # Generic lifestyle
    # --------------------------------------------------------

    scene_police = (
        "A polícia iniciou "
        "a investigação do caso."
    )


    lifestyle = {

        "provider": "Pixabay",

        "tipo": "foto",

        "title":
            "Happy woman relaxing "
            "in bedroom lifestyle",

        "must": "1/2",

        "score": 190,

        "width": 1920,

        "height": 1080,
    }


    police = {

        "provider": "Wikimedia",

        "tipo": "foto",

        "title":
            "Police officers conducting "
            "investigation",

        "must": "2/2",

        "score": 140,

        "width": 1920,

        "height": 1080,
    }


    l1 = score_candidate(
        lifestyle,
        scene_police,
        state,
    )


    l2 = score_candidate(
        police,
        scene_police,
        state,
    )


    if (
        l1.get(
            "effective"
        )
        is not None
        and
        l2.get(
            "effective"
        )
        is not None
    ):

        record(
            "GENERIC_LIFESTYLE_PENALTY",
            "PASS"
            if (
                l2[
                    "effective"
                ]
                >
                l1[
                    "effective"
                ]
            )
            else "FAIL",
        )


except Exception as exc:

    record(
        "VSE4_SYNTHETIC_RUNTIME",
        "FAIL",
        (
            f"{type(exc).__name__}: "
            f"{exc}"
        ),
    )

    out(
        traceback.format_exc()
    )


# ============================================================
# 17. V42 BRIDGE API
# ============================================================

section(
    "17. V42 BRIDGE API"
)


for module_name, functions in {

    "visual_selection_bridge_v42.py": (
        "rank_pool",
        "commit_candidate",
    ),

    "visual_selection_runtime_v42.py": (
        "enhance_selection",
        "note_commit",
    ),

}.items():

    path = ROOT / module_name

    if not path.is_file():
        continue


    try:

        ns = runpy.run_path(
            str(path),
            run_name=(
                "audit_"
                +
                module_name.replace(
                    ".",
                    "_"
                )
            ),
        )


        for fn_name in functions:

            fn = ns.get(
                fn_name
            )

            record(
                (
                    module_name
                    +
                    "::"
                    +
                    fn_name
                ),
                "PASS"
                if callable(fn)
                else "FAIL",
            )


    except Exception as exc:

        record(
            f"LOAD_{module_name}",
            "FAIL",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


# ============================================================
# 18. PROVIDER CONFIG STATUS
# ============================================================

section(
    "18. PROVIDER CONFIG"
)


config = ROOT / "config.env"


provider_words = (
    "PEXELS",
    "PIXABAY",
    "COVERR",
)


if config.is_file():

    lines = config.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines()


    for provider_name in provider_words:

        matches = []

        for line in lines:

            stripped = line.strip()

            if (
                not stripped
                or
                stripped.startswith(
                    "#"
                )
                or
                "="
                not in stripped
            ):
                continue

            key, value = stripped.split(
                "=",
                1,
            )

            if provider_name in key.upper():

                matches.append(
                    (
                        key.strip(),
                        bool(
                            value.strip()
                        ),
                    )
                )


        if not matches:

            record(
                f"CONFIG_{provider_name}",
                "WARN",
                "nenhuma variável encontrada",
                severity="warning",
            )

        else:

            for key, populated in matches:

                out(
                    f"CONFIG_KEY={key} "
                    f"SET={'YES' if populated else 'NO'}"
                )

else:

    record(
        "CONFIG_ENV",
        "WARN",
        "config.env não encontrado",
        severity="warning",
    )


# ============================================================
# 19. MEDIA DIRECTORY HEALTH
# ============================================================

section(
    "19. MEDIA DIRECTORY HEALTH"
)


images_root = (
    ROOT
    / "imagens"
)


dirs = []


if images_root.is_dir():

    dirs = sorted(
        [
            x
            for x in images_root.iterdir()
            if (
                x.is_dir()
                and
                x.name.startswith(
                    "short_"
                )
            )
        ],
        key=lambda x:
            x.stat().st_mtime,
        reverse=True,
    )


for directory in dirs[:10]:

    scene_files = list(
        directory.glob(
            "scene_*.*"
        )
    )

    stems = Counter(
        p.stem
        for p in scene_files
    )

    duplicates = sorted(
        stem
        for stem, count
        in stems.items()
        if count > 1
    )


    out()
    out(
        "MEDIA_DIR=",
        directory.name,
    )

    out(
        "MEDIA_FILES=",
        len(scene_files),
    )

    out(
        "DUPLICATE_SCENES=",
        duplicates
        if duplicates
        else "NONE",
    )


    if duplicates:

        record(
            (
                "MEDIA_DUPLICATE_"
                +
                directory.name
            ),
            "WARN",
            ",".join(
                duplicates
            ),
            severity="warning",
        )


# ============================================================
# 20. LATEST SHORT INPUT HEALTH
# ============================================================

section(
    "20. LATEST SHORT HEALTH"
)


latest_sid = None


if dirs:

    latest_sid = dirs[
        0
    ].name.replace(
        "short_",
        "",
        1,
    )


if latest_sid:

    out(
        "LATEST_SHORT_ID=",
        latest_sid,
    )


    media_dir = (
        ROOT
        / "imagens"
        / f"short_{latest_sid}"
    )

    audio = (
        ROOT
        / "audios"
        / f"short_{latest_sid}.mp3"
    )

    ass = (
        ROOT
        / "videos"
        / f"short_{latest_sid}.ass"
    )

    video_base = (
        ROOT
        / "temp"
        / latest_sid
        / "video_sem_audio.mp4"
    )

    final = (
        ROOT
        / "videos"
        / f"short_v6_{latest_sid}.mp4"
    )


    media_count = len(
        list(
            media_dir.glob(
                "scene_*.*"
            )
        )
    )


    out(
        "LATEST_MEDIA_COUNT=",
        media_count,
    )


    for label, path in {

        "AUDIO": audio,
        "ASS": ass,
        "VIDEO_BASE": video_base,
        "FINAL": final,

    }.items():

        out(
            f"LATEST_{label}="
            +
            (
                "YES"
                if (
                    path.is_file()
                    and
                    path.stat().st_size > 0
                )
                else "NO"
            )
        )


# ============================================================
# 21. FRESH RENDER GUARD
# ============================================================

section(
    "21. FRESH RENDER GUARD"
)


guard_src = load_source(
    "fresh_render_guard_v1.py"
)


record(
    "RENDER_GUARD_ASS_PROTECTED",
    "PASS"
    if (
        '".ass"'
        in guard_src
        or
        "'.ass'"
        in guard_src
    )
    else "FAIL",
)


record(
    "RENDER_GUARD_MP4_TARGETED",
    "PASS"
    if ".mp4"
    in guard_src
    else "FAIL",
)


# ============================================================
# 22. RECENT LOG ERROR SCAN
# ============================================================

section(
    "22. RECENT LOG ERROR SCAN"
)


log_root = (
    ROOT
    / "logs"
    / "producao"
)


logs = []


if log_root.is_dir():

    logs = sorted(
        [
            p
            for p in log_root.iterdir()
            if p.is_file()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


error_tokens = (

    "Traceback (most recent call last)",
    "NameError:",
    "TypeError:",
    "AssertionError",
    "SyntaxError:",
    "ModuleNotFoundError:",
    "ImportError:",
)


recent_error_files = []


for path in logs[:30]:

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:

        continue


    matched = [
        token
        for token in error_tokens
        if token in text
    ]


    if matched:

        recent_error_files.append(
            (
                path.name,
                matched,
            )
        )


out(
    "RECENT_LOGS_SCANNED=",
    min(
        len(logs),
        30,
    ),
)

out(
    "RECENT_LOG_ERROR_FILES=",
    len(
        recent_error_files
    ),
)


for name, errors in recent_error_files[:20]:

    out(
        "LOG_ERROR=",
        name,
        "|",
        ",".join(
            errors
        ),
    )


if recent_error_files:

    record(
        "RECENT_LOG_ERRORS",
        "WARN",
        (
            f"{len(recent_error_files)} "
            "logs contêm exceções"
        ),
        severity="warning",
    )

else:

    record(
        "RECENT_LOG_ERRORS",
        "PASS",
    )


# ============================================================
# 23. HIGH RISK STATIC PATTERNS
# ============================================================

section(
    "23. HIGH RISK STATIC PATTERNS"
)


patterns = {

    "BARE_EXCEPT":
        "except:",

    "SYSTEM_EXIT":
        "sys.exit(",

    "OS_SYSTEM":
        "os.system(",

}


for label, pattern in patterns.items():

    count = midia.count(
        pattern
    )

    out(
        f"MIDIA_{label}_COUNT={count}"
    )


# ============================================================
# 24. FINAL SUMMARY
# ============================================================

section(
    "24. MASTER AUDIT SUMMARY"
)


critical_failures = [

    item
    for item in results
    if (
        item[
            "status"
        ]
        ==
        "FAIL"
        and
        item[
            "severity"
        ]
        ==
        "critical"
    )
]


warnings = [

    item
    for item in results
    if item[
        "status"
    ]
    ==
    "WARN"
]


passes = [

    item
    for item in results
    if item[
        "status"
    ]
    ==
    "PASS"
]


out(
    "PASS_COUNT=",
    len(
        passes
    ),
)

out(
    "WARNING_COUNT=",
    len(
        warnings
    ),
)

out(
    "CRITICAL_FAIL_COUNT=",
    len(
        critical_failures
    ),
)


if critical_failures:

    out()
    out(
        "===== CRITICAL FAILURES ====="
    )

    for item in critical_failures:

        out(
            "FAIL:",
            item[
                "name"
            ],
            "|",
            item[
                "detail"
            ],
        )


if warnings:

    out()
    out(
        "===== WARNINGS ====="
    )

    for item in warnings:

        out(
            "WARN:",
            item[
                "name"
            ],
            "|",
            item[
                "detail"
            ],
        )


# Important architectural warnings.

architectural_risks = []


if has_417 and has_42:

    architectural_risks.append(
        "DOUBLE_FINAL_GATE"
    )


if (
    scene_commit_count > 0
    and
    success_commit_count > 0
):

    architectural_risks.append(
        "MULTIPLE_COMMIT_LAYERS"
    )


if install_count > 1:

    architectural_risks.append(
        "DIVERSITY_INSTALL_REDEFINED"
    )


out()
out(
    "ARCHITECTURAL_RISKS="
    +
    (
        ",".join(
            architectural_risks
        )
        if architectural_risks
        else "NONE"
    )
)


if not critical_failures:

    out(
        "MASTER_AUDIT_STATUS=PASS"
    )

else:

    out(
        "MASTER_AUDIT_STATUS=FAIL"
    )


payload = {

    "timestamp":
        STAMP,

    "pass_count":
        len(
            passes
        ),

    "warning_count":
        len(
            warnings
        ),

    "critical_fail_count":
        len(
            critical_failures
        ),

    "architectural_risks":
        architectural_risks,

    "results":
        results,
}


JSON_REPORT.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


out(
    "TEXT_REPORT=",
    REPORT,
)

out(
    "JSON_REPORT=",
    JSON_REPORT,
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
    "MIDIA_PY_MODIFIED=NO"
)

out(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
