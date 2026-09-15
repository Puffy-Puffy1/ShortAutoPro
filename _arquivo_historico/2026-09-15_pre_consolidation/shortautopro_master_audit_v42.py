#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import ast
import builtins
import hashlib
import json
import os
import py_compile
import re
import runpy
import subprocess
import symtable
import time
import traceback


ROOT = Path.home() / "ShortAutoPro"

REPORT = (
    ROOT
    / "temp"
    / "SHORTAUTOPRO_MASTER_AUDIT_V42.txt"
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


OUT = []
FAIL = []
WARN = []
PASS = []


def emit(text=""):

    text = str(text)

    print(text)

    OUT.append(text)


def section(title):

    emit()
    emit("=" * 72)
    emit(title)
    emit("=" * 72)


def result(kind, name, detail=""):

    line = f"{kind}: {name}"

    if detail:
        line += f" | {detail}"

    emit(line)

    if kind == "PASS":
        PASS.append(name)

    elif kind == "WARN":
        WARN.append(name)

    elif kind == "FAIL":
        FAIL.append(name)


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


def shell(cmd):

    return subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def source(path):

    try:

        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:

        return ""


def parse_python(path):

    try:

        return ast.parse(
            source(path),
            filename=str(path),
        )

    except Exception:

        return None


def find_latest_short_id():

    requested = (
        os.environ.get(
            "SHORT_ID",
            ""
        )
        .strip()
    )

    if requested:
        return requested


    candidates = []

    patterns = (
        (
            ROOT / "roteiros",
            "short_*.txt",
            "short_",
            ".txt",
        ),
        (
            ROOT / "audios",
            "short_*.mp3",
            "short_",
            ".mp3",
        ),
    )


    for folder, pattern, prefix, suffix in patterns:

        if not folder.exists():
            continue

        for path in folder.glob(pattern):

            name = path.name

            if not (
                name.startswith(prefix)
                and
                name.endswith(suffix)
            ):
                continue

            sid = name[
                len(prefix):
                -len(suffix)
            ]

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
        return None


    candidates.sort(
        reverse=True
    )

    return candidates[0][1]


# ============================================================
# 1. PROJECT / CORE
# ============================================================

section(
    "1. PROJECT / CORE FILES"
)


required_files = (
    "roteiro.py",
    "midia.py",
    "legenda_dinamica.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
    "render_output_certifier_v1.py",
)


for name in required_files:

    path = ROOT / name

    if path.is_file():

        result(
            "PASS",
            f"FILE_{name}",
            f"{path.stat().st_size} bytes",
        )

        emit(
            f"HASH_{name}="
            f"{sha256(path)}"
        )

    else:

        result(
            "FAIL",
            f"FILE_{name}",
            "missing",
        )


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section(
    "2. ROOT PYTHON COMPILE"
)


python_files = sorted(
    ROOT.glob("*.py")
)

compile_errors = []


for path in python_files:

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        compile_errors.append(
            (
                path.name,
                str(exc),
            )
        )


emit(
    f"ROOT_PY_COUNT="
    f"{len(python_files)}"
)


if compile_errors:

    result(
        "FAIL",
        "ROOT_PY_COMPILE",
        f"errors={len(compile_errors)}",
    )

    for name, error in compile_errors:

        emit(
            f"COMPILE_ERROR={name} | "
            f"{error}"
        )

else:

    result(
        "PASS",
        "ROOT_PY_COMPILE",
        "all root Python files",
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)


shell_files = sorted(
    ROOT.glob("*.sh")
)


for path in shell_files:

    check = shell(
        [
            "bash",
            "-n",
            str(path),
        ]
    )

    if check.returncode == 0:

        result(
            "PASS",
            f"SHELL_{path.name}",
        )

    else:

        result(
            "FAIL",
            f"SHELL_{path.name}",
            check.stderr[-500:],
        )


# ============================================================
# 4. DUPLICATE TOP-LEVEL DEFINITIONS
# ============================================================

section(
    "4. DUPLICATE PYTHON DEFINITIONS"
)


critical_python = (
    "visual_selection_engine_v4.py",
    "midia.py",
    "video.py",
    "v6.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
)


for name in critical_python:

    path = ROOT / name

    if not path.is_file():
        continue

    tree = parse_python(path)

    if tree is None:

        result(
            "FAIL",
            f"AST_{name}",
            "parse failed",
        )

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
        for key, count in defs.items()
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

                unresolved.add(name)

            walk_scope(child)


    walk_scope(table)


    if unresolved:

        result(
            "FAIL",
            "VSE4_UNRESOLVED_GLOBALS",
            ",".join(
                sorted(unresolved)
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
        f"{type(exc).__name__}: {exc}",
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
            ast.Assign,
        ):

            for target in node.targets:

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
        ",".join(missing_functions),
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
        ",".join(missing_globals),
    )

else:

    result(
        "PASS",
        "VSE4_REQUIRED_GLOBALS",
        "all",
    )


# ============================================================
# 7. VSE4 RUNTIME
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
            f"{type(exc).__name__}: {exc}",
        )

        emit(
            traceback.format_exc()
        )


except Exception as exc:

    result(
        "FAIL",
        "VSE4_MODULE_LOAD",
        f"{type(exc).__name__}: {exc}",
    )


# ============================================================
# 8. DIRECT STRING SEMANTICS
# ============================================================

section(
    "8. VSE4 DIRECT STRING SEMANTICS"
)


if vse_ns:

    scene_string = (
        "Investigação em apartamento "
        "na cidade de São Paulo"
    )


    try:

        direct_text = vse_ns[
            "candidate_text"
        ](
            scene_string
        )

        direct_tokens = vse_ns[
            "tokens"
        ](
            scene_string
        )

        direct_geo = set(
            vse_ns[
                "geo_hits"
            ](
                scene_string
            )
        )


        emit(
            f"DIRECT_TEXT={direct_text!r}"
        )

        emit(
            "DIRECT_TOKENS="
            +
            json.dumps(
                sorted(direct_tokens),
                ensure_ascii=False,
            )
        )

        emit(
            "DIRECT_GEO="
            +
            json.dumps(
                sorted(direct_geo),
                ensure_ascii=False,
            )
        )


        string_ok = (
            isinstance(
                direct_text,
                str,
            )
            and
            "sao" in direct_text
            and
            "paulo" in direct_text
        )


        if string_ok:

            result(
                "PASS",
                "DIRECT_STRING_SEMANTICS",
            )

        else:

            result(
                "FAIL",
                "DIRECT_STRING_SEMANTICS",
                "candidate_text(string) perdeu conteúdo",
            )


        if (
            "brazil" in direct_geo
            and
            "sao_paulo" in direct_geo
        ):

            result(
                "PASS",
                "DIRECT_GEO_SEMANTICS",
            )

        else:

            result(
                "FAIL",
                "DIRECT_GEO_SEMANTICS",
                str(
                    sorted(direct_geo)
                ),
            )


    except Exception as exc:

        result(
            "FAIL",
            "DIRECT_STRING_RUNTIME",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 9. GEO CONTRADICTION TEST
# ============================================================

section(
    "9. GEO / HARD-MISMATCH TEST"
)


if vse_ns:

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

        wrong_score = vse_ns[
            "score_candidate"
        ](
            wrong,
            scene,
            state,
        )

        correct_score = vse_ns[
            "score_candidate"
        ](
            correct,
            scene,
            state,
        )


        emit(
            "WRONG_RESULT="
            +
            json.dumps(
                wrong_score,
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            )
        )


        emit(
            "CORRECT_RESULT="
            +
            json.dumps(
                correct_score,
                ensure_ascii=False,
                default=str,
                sort_keys=True,
            )
        )


        wrong_hard = (
            wrong_score.get(
                "hard_mismatch"
            )
            is True
        )

        correct_hard = (
            correct_score.get(
                "hard_mismatch"
            )
            is True
        )


        if wrong_hard:

            result(
                "PASS",
                "SP_VS_NEW_YORK_HARD_MISMATCH",
            )

        else:

            result(
                "FAIL",
                "SP_VS_NEW_YORK_HARD_MISMATCH",
                "Empire State Building não foi bloqueado",
            )


        if not correct_hard:

            result(
                "PASS",
                "SAO_PAULO_CORRECT_NOT_BLOCKED",
            )

        else:

            result(
                "FAIL",
                "SAO_PAULO_CORRECT_NOT_BLOCKED",
            )


        wrong_eff = wrong_score.get(
            "effective",
            wrong_score.get(
                "effective_score",
                0,
            ),
        )

        correct_eff = correct_score.get(
            "effective",
            correct_score.get(
                "effective_score",
                0,
            ),
        )


        emit(
            f"WRONG_EFFECTIVE={wrong_eff}"
        )

        emit(
            f"CORRECT_EFFECTIVE={correct_eff}"
        )


        if correct_eff > wrong_eff:

            result(
                "PASS",
                "SEMANTIC_WINNER_CORRECT",
            )

        else:

            result(
                "FAIL",
                "SEMANTIC_WINNER_CORRECT",
                "candidato incorreto ainda vence",
            )


    except Exception as exc:

        result(
            "FAIL",
            "HARD_MISMATCH_RUNTIME",
            f"{type(exc).__name__}: {exc}",
        )

        emit(
            traceback.format_exc()
        )


# ============================================================
# 10. GENERAL SEMANTIC SAFETY
# ============================================================

section(
    "10. GENERAL SEMANTIC SAFETY"
)


if vse_ns:

    tests = (
        (
            "FORENSIC_VS_MEDICINE",
            "Laudo pericial encontrou evidências na cena do crime",
            {
                "provider": "Pixabay",
                "tipo": "foto",
                "title":
                    "Pills medication pharmacy tablets",
                "score": 190,
                "must": "1/2",
                "width": 1920,
                "height": 1080,
            },
        ),
        (
            "INVESTIGATION_VS_LIFESTYLE",
            "Polícia iniciou investigação no apartamento",
            {
                "provider": "Pixabay",
                "tipo": "foto",
                "title":
                    "Happy woman relaxing in bedroom lifestyle",
                "score": 190,
                "must": "1/2",
                "width": 1920,
                "height": 1080,
            },
        ),
    )


    for label, scene, candidate in tests:

        try:

            score = vse_ns[
                "score_candidate"
            ](
                candidate,
                scene,
                {
                    "providers": [],
                    "groups": [],
                    "types": [],
                    "keys": [],
                },
            )


            emit(
                f"{label}_RESULT="
                +
                json.dumps(
                    score,
                    ensure_ascii=False,
                    default=str,
                    sort_keys=True,
                )
            )


            mismatch = bool(
                score.get(
                    "hard_mismatch",
                    False,
                )
            )

            penalty = (
                score.get(
                    "mismatch",
                    0
                )
                or
                score.get(
                    "mismatch_penalty",
                    0
                )
                or
                score.get(
                    "penalty",
                    0
                )
            )


            if mismatch or penalty:

                result(
                    "PASS",
                    label,
                    "penalized",
                )

            else:

                result(
                    "WARN",
                    label,
                    "nenhuma penalização aparente",
                )


        except Exception as exc:

            result(
                "FAIL",
                label,
                f"{type(exc).__name__}: {exc}",
            )


# ============================================================
# 11. PROVIDER ACQUISITION
# ============================================================

section(
    "11. PROVIDER ACQUISITION"
)


midia_path = ROOT / "midia.py"
midia_tree = parse_python(
    midia_path
)

provider_functions = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
}


midia_functions = {}


if midia_tree:

    for node in midia_tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            midia_functions[
                node.name
            ] = node


for name in sorted(
    provider_functions
):

    if name in midia_functions:

        result(
            "PASS",
            f"PROVIDER_FUNCTION_{name}",
            f"line={midia_functions[name].lineno}",
        )

    else:

        result(
            "FAIL",
            f"PROVIDER_FUNCTION_{name}",
            "missing",
        )


buscar = midia_functions.get(
    "buscar_todos_candidatos"
)


if buscar:

    calls = []


    for node in ast.walk(buscar):

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
                node.func.id
            )

        elif isinstance(
            node.func,
            ast.Attribute,
        ):

            calls.append(
                node.func.attr
            )


    acquisition_expected = (
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
    )


    for name in acquisition_expected:

        if name in calls:

            result(
                "PASS",
                f"ACQUISITION_CALL_{name}",
            )

        else:

            result(
                "FAIL",
                f"ACQUISITION_CALL_{name}",
                "não chamado por buscar_todos_candidatos",
            )


# ============================================================
# 12. CONFIG VARIABLE NAMES
# ============================================================

section(
    "12. PROVIDER CONFIG VARIABLE NAMES"
)


config_names = sorted(
    set(
        re.findall(
            r'\b[A-Z][A-Z0-9_]*(?:KEY|TOKEN|API)[A-Z0-9_]*\b',
            source(midia_path),
        )
    )
)


if config_names:

    for name in config_names:

        emit(
            f"CONFIG_NAME={name}"
        )

else:

    result(
        "WARN",
        "PROVIDER_CONFIG_NAMES",
        "nenhum nome detectado",
    )


emit(
    "CONFIG_VALUES_PRINTED=NO"
)


# ============================================================
# 13. VSE4 ACTIVE INTEGRATION
# ============================================================

section(
    "13. VSE4 ACTIVE PIPELINE INTEGRATION"
)


integration_sources = {
    "midia.py":
        source(
            ROOT / "midia.py"
        ),

    "media_diversity_guard_v1.py":
        source(
            ROOT
            / "media_diversity_guard_v1.py"
        ),
}


integration_hits = []


for filename, text in integration_sources.items():

    if (
        "visual_selection_engine_v4"
        in text
        or
        "VSE4"
        in text
        or
        "vse4"
        in text
    ):

        integration_hits.append(
            filename
        )


if integration_hits:

    result(
        "PASS",
        "VSE4_PIPELINE_REFERENCE",
        ",".join(integration_hits),
    )

else:

    result(
        "WARN",
        "VSE4_PIPELINE_REFERENCE",
        "VSE4 existe mas não há referência ativa detectável",
    )


# ============================================================
# 14. PROVENANCE / DIVERSITY / COMMIT LOCK
# ============================================================

section(
    "14. MEDIA SAFETY HOOKS"
)


hook_checks = (
    (
        "PROVENANCE_REFERENCE",
        "media_provenance_capture",
    ),
    (
        "DIVERSITY_REFERENCE",
        "media_diversity_guard",
    ),
    (
        "SCENE_COMMIT_REFERENCE",
        "SCENE_COMMIT",
    ),
)


combined_media_source = (
    source(
        ROOT / "midia.py"
    )
    +
    "\n"
    +
    source(
        ROOT
        / "media_diversity_guard_v1.py"
    )
)


for label, marker in hook_checks:

    if marker.casefold() in (
        combined_media_source.casefold()
    ):

        result(
            "PASS",
            label,
        )

    else:

        result(
            "WARN",
            label,
            "marker not detected",
        )


# ============================================================
# 15. RENDER GUARD STATIC SAFETY
# ============================================================

section(
    "15. FRESH RENDER GUARD SAFETY"
)


guard_path = (
    ROOT
    / "fresh_render_guard_v1.py"
)

guard_src = source(
    guard_path
)


if ".ass" in guard_src:

    result(
        "PASS",
        "RENDER_GUARD_ASS_AWARE",
    )

else:

    result(
        "WARN",
        "RENDER_GUARD_ASS_AWARE",
        ".ass não aparece na proteção",
    )


if (
    "PROTECTED_SUFFIXES"
    in guard_src
):

    result(
        "PASS",
        "RENDER_GUARD_PROTECTED_SUFFIXES",
    )

else:

    result(
        "WARN",
        "RENDER_GUARD_PROTECTED_SUFFIXES",
    )


dangerous_guard = (
    "rglob(\"*\")" in guard_src
    and
    ".unlink(" in guard_src
)


if dangerous_guard:

    result(
        "WARN",
        "RENDER_GUARD_BROAD_DELETE_PATTERN",
        "rglob('*') + unlink detected",
    )

else:

    result(
        "PASS",
        "RENDER_GUARD_BROAD_DELETE_PATTERN",
        "not detected",
    )


# ============================================================
# 16. DANGEROUS DELETE STATIC AUDIT
# ============================================================

section(
    "16. DESTRUCTIVE PATTERN AUDIT"
)


danger_patterns = (
    r"rm\s+-rf",
    r"rmtree\s*\(",
    r"\.unlink\s*\(",
    r"os\.remove\s*\(",
)


for filename in (
    "gerar_short.sh",
    "midia.py",
    "fresh_render_guard_v1.py",
    "render_transaction_v1.py",
):

    path = ROOT / filename

    if not path.exists():
        continue

    text = source(path)

    matches = []


    for pattern in danger_patterns:

        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            line = (
                text.count(
                    "\n",
                    0,
                    match.start(),
                )
                + 1
            )

            matches.append(
                (
                    line,
                    match.group(0),
                )
            )


    if matches:

        result(
            "WARN",
            f"DESTRUCTIVE_PATTERNS_{filename}",
            f"count={len(matches)}",
        )

        for line, value in matches[:20]:

            emit(
                f"DELETE_PATTERN={filename}:{line}:"
                f"{value}"
            )

    else:

        result(
            "PASS",
            f"DESTRUCTIVE_PATTERNS_{filename}",
            "none",
        )


# ============================================================
# 17. PIPELINE STAGE MAP
# ============================================================

section(
    "17. GERAR_SHORT PIPELINE MAP"
)


gerar_src = source(
    ROOT / "gerar_short.sh"
)


expected_stage_files = (
    "roteiro.py",
    "midia.py",
    "legenda_dinamica.py",
    "video.py",
    "v6.py",
)


positions = {}


for name in expected_stage_files:

    pos = gerar_src.find(
        name
    )

    positions[
        name
    ] = pos

    if pos >= 0:

        result(
            "PASS",
            f"PIPELINE_STAGE_{name}",
            f"offset={pos}",
        )

    else:

        result(
            "WARN",
            f"PIPELINE_STAGE_{name}",
            "not directly referenced",
        )


known_positions = [
    positions[name]
    for name in expected_stage_files
    if positions[name] >= 0
]


if (
    len(known_positions) >= 4
    and
    known_positions
    ==
    sorted(known_positions)
):

    result(
        "PASS",
        "PIPELINE_STAGE_ORDER",
    )

else:

    result(
        "WARN",
        "PIPELINE_STAGE_ORDER",
        str(positions),
    )


# ============================================================
# 18. CURRENT SHORT
# ============================================================

section(
    "18. CURRENT SHORT ASSETS"
)


sid = find_latest_short_id()

emit(
    f"AUDIT_SHORT_ID={sid}"
)


if not sid:

    result(
        "WARN",
        "CURRENT_SHORT_ID",
        "not found",
    )

else:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{sid}"
    )


    total = 0
    invalid = 0
    hashes = {}


    for index in range(
        1,
        13,
    ):

        matches = sorted(
            media_dir.glob(
                f"scene_{index:02d}.*"
            )
        ) if media_dir.exists() else []


        count = len(matches)

        total += count


        if count != 1:

            invalid += 1

            result(
                "FAIL",
                f"SCENE_{index:02d}_COUNT",
                f"count={count}",
            )

        else:

            path = matches[0]

            file_hash = sha256(
                path
            )

            hashes[
                path.name
            ] = file_hash


            emit(
                f"SCENE_{index:02d}="
                f"{path.name} | "
                f"{path.stat().st_size} | "
                f"{file_hash}"
            )


    emit(
        f"MEDIA_TOTAL={total}"
    )

    emit(
        f"INVALID_SCENE_COUNT={invalid}"
    )


    if (
        total == 12
        and
        invalid == 0
    ):

        result(
            "PASS",
            "CURRENT_MEDIA_12_OF_12",
        )

    else:

        result(
            "FAIL",
            "CURRENT_MEDIA_12_OF_12",
            f"total={total} invalid={invalid}",
        )


    duplicate_hashes = {}

    by_hash = {}

    for name, digest in hashes.items():

        by_hash.setdefault(
            digest,
            []
        ).append(
            name
        )


    for digest, names in by_hash.items():

        if len(names) > 1:

            duplicate_hashes[
                digest
            ] = names


    if duplicate_hashes:

        result(
            "WARN",
            "EXACT_MEDIA_DUPLICATES",
            json.dumps(
                duplicate_hashes,
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
# 19. CURRENT RENDER INPUTS
# ============================================================

section(
    "19. CURRENT RENDER INPUTS"
)


if sid:

    render_inputs = {
        "AUDIO":
            ROOT
            / "audios"
            / f"short_{sid}.mp3",

        "ASS":
            ROOT
            / "videos"
            / f"short_{sid}.ass",

        "VIDEO_BASE":
            ROOT
            / "temp"
            / sid
            / "video_sem_audio.mp4",

        "FINAL":
            ROOT
            / "videos"
            / f"short_v6_{sid}.mp4",
    }


    for label, path in render_inputs.items():

        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            result(
                "PASS",
                f"RENDER_INPUT_{label}",
                f"{path.stat().st_size} bytes",
            )

        else:

            # FINAL/intermediate podem legitimamente não existir.
            if label in {
                "VIDEO_BASE",
                "FINAL",
            }:

                result(
                    "WARN",
                    f"RENDER_INPUT_{label}",
                    "not present",
                )

            else:

                result(
                    "FAIL",
                    f"RENDER_INPUT_{label}",
                    "missing",
                )


# ============================================================
# 20. FINAL VIDEO TECHNICAL CHECK
# ============================================================

section(
    "20. FINAL VIDEO TECHNICAL CHECK"
)


if sid:

    final_video = (
        ROOT
        / "videos"
        / f"short_v6_{sid}.mp4"
    )


    if final_video.is_file():

        probe = shell(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,r_frame_rate",
                "-show_entries",
                "format=duration,size,bit_rate",
                "-of",
                "json",
                str(final_video),
            ]
        )


        if probe.returncode == 0:

            result(
                "PASS",
                "FINAL_FFPROBE",
            )

            emit(
                "FINAL_FFPROBE_JSON="
                +
                probe.stdout.strip()
            )

        else:

            result(
                "FAIL",
                "FINAL_FFPROBE",
                probe.stderr[-500:],
            )


        emit(
            "FINAL_SHA256="
            +
            sha256(
                final_video
            )
        )


    else:

        result(
            "WARN",
            "FINAL_VIDEO",
            "not present",
        )


# ============================================================
# 21. RECENT LOG ERROR SCAN
# ============================================================

section(
    "21. RECENT LOG ERROR SCAN"
)


log_dir = (
    ROOT
    / "logs"
    / "producao"
)


recent_errors = []


if log_dir.exists():

    log_files = sorted(
        log_dir.glob("*"),
        key=lambda p:
            p.stat().st_mtime
            if p.is_file()
            else 0,
        reverse=True,
    )[:30]


    error_re = re.compile(
        r"Traceback|"
        r"\bERRO\b|"
        r"\bERROR\b|"
        r"\bFAIL(?:ED)?\b|"
        r"AssertionError|"
        r"NameError|"
        r"TypeError",
        re.IGNORECASE,
    )


    for path in log_files:

        if not path.is_file():
            continue

        text = source(path)

        matches = [
            line.strip()
            for line in text.splitlines()
            if error_re.search(line)
        ]


        if matches:

            recent_errors.append(
                (
                    path.name,
                    matches[-5:],
                )
            )


    emit(
        f"RECENT_LOGS_WITH_ERROR_MARKERS="
        f"{len(recent_errors)}"
    )


    for name, matches in recent_errors[:15]:

        emit(
            f"LOG_ERROR_FILE={name}"
        )

        for line in matches:

            emit(
                f"  {line[:300]}"
            )


    if recent_errors:

        result(
            "WARN",
            "RECENT_LOG_ERRORS",
            f"files={len(recent_errors)}",
        )

    else:

        result(
            "PASS",
            "RECENT_LOG_ERRORS",
            "none",
        )


else:

    result(
        "WARN",
        "LOG_DIRECTORY",
        "missing",
    )


# ============================================================
# 22. EMPTY / TINY CORE FILES
# ============================================================

section(
    "22. EMPTY / TINY FILE AUDIT"
)


for name in required_files:

    path = ROOT / name

    if not path.exists():
        continue


    size = path.stat().st_size


    if size == 0:

        result(
            "FAIL",
            f"EMPTY_{name}",
        )

    elif size < 50:

        result(
            "WARN",
            f"TINY_{name}",
            f"{size} bytes",
        )

    else:

        result(
            "PASS",
            f"SIZE_{name}",
            f"{size} bytes",
        )


# ============================================================
# 23. KNOWN CRITICAL ARCHITECTURE CHECKS
# ============================================================

section(
    "23. KNOWN CRITICAL ARCHITECTURE CHECKS"
)


midia_src = source(
    ROOT / "midia.py"
)


# Detecta o padrão que antes permitiu segundo download
# depois de uma seleção bem-sucedida.
if (
    "baixar_candidato_5_2"
    in midia_src
):

    result(
        "PASS",
        "MIDIA_DOWNLOADER_PRESENT",
    )

else:

    result(
        "FAIL",
        "MIDIA_DOWNLOADER_PRESENT",
    )


# Procura possibilidade de .jpg + .mp4 para mesma cena.
if (
    'f"scene_{numero:02d}.mp4"'
    in midia_src
    or
    "scene_{numero:02d}.mp4"
    in midia_src
):

    result(
        "WARN",
        "SCENE_EXTENSION_SWITCH_PATH",
        "verificar commit/cleanup de sibling .jpg/.mp4",
    )


# ============================================================
# 24. MASTER SUMMARY
# ============================================================

section(
    "24. MASTER SUMMARY"
)


emit(
    f"PASS_COUNT={len(PASS)}"
)

emit(
    f"WARN_COUNT={len(WARN)}"
)

emit(
    f"FAIL_COUNT={len(FAIL)}"
)


if FAIL:

    emit()
    emit(
        "===== FAILURES ====="
    )

    for item in FAIL:

        emit(
            f"FAIL_ITEM={item}"
        )


if WARN:

    emit()
    emit(
        "===== WARNINGS ====="
    )

    for item in WARN:

        emit(
            f"WARN_ITEM={item}"
        )


emit()


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
    "NETWORK_EXECUTED=NO"
)

emit(
    "MEDIA_DOWNLOADED=NO"
)

emit(
    "VIDEO_RENDERED=NO"
)

emit(
    "PIPELINE_MODIFIED=NO"
)

emit(
    "AUDIT_COMPLETE=YES"
)


REPORT.write_text(
    "\n".join(OUT) + "\n",
    encoding="utf-8",
)


print()
print(
    f"REPORT={REPORT}"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
