#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import re
import subprocess
import symtable
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

REPORT = (
    ROOT
    / "temp"
    / "VSE42_MASTER_AUDIT.txt"
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


VISUAL_FILES = [
    "visual_selection_engine_v4.py",
    "visual_selection_runtime_v42.py",
    "visual_selection_bridge_v42.py",
    "visual_pipeline_bridge_v42.py",
    "visual_runtime_v42.py",
    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
]


CORE_FILES = [
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "gerar_short.sh",
]


REQUIRED_PROVIDER_FUNCTIONS = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
]


PROVIDER_NAMES = {
    "pexels",
    "pixabay",
    "coverr",
    "wikimedia",
}


BUILTINS = set(
    dir(builtins)
)


errors = []
warnings = []
passes = []


def out(*args):

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

    out()
    out("=" * 72)
    out(title)
    out("=" * 72)


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

            h.update(chunk)

    return h.hexdigest()


def read(path):

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def parse(path):

    return ast.parse(
        read(path),
        filename=str(path),
    )


def add_pass(name):

    passes.append(name)

    out(
        f"PASS={name}"
    )


def add_warning(name):

    warnings.append(name)

    out(
        f"WARNING={name}"
    )


def add_error(name):

    errors.append(name)

    out(
        f"ERROR={name}"
    )


REPORT.write_text(
    "",
    encoding="utf-8",
)


section(
    "1. FILE INVENTORY"
)


all_files = (
    VISUAL_FILES
    +
    CORE_FILES
)


for name in all_files:

    path = ROOT / name

    if path.is_file():

        out(
            f"FOUND={name}"
        )

        out(
            f"SHA256={sha256(path)}"
        )

    else:

        out(
            f"MISSING={name}"
        )

        if (
            name
            in (
                "midia.py",
                "visual_selection_engine_v4.py",
            )
        ):

            add_error(
                f"CRITICAL_FILE_MISSING:{name}"
            )

        else:

            add_warning(
                f"OPTIONAL_OR_EXPECTED_FILE_MISSING:{name}"
            )


section(
    "2. PYTHON SYNTAX"
)


python_files = []

for name in all_files:

    path = ROOT / name

    if (
        path.is_file()
        and
        path.suffix == ".py"
    ):

        python_files.append(path)


for path in python_files:

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode == 0:

        out(
            f"COMPILE_PASS={path.name}"
        )

    else:

        add_error(
            f"COMPILE_FAIL:{path.name}"
        )

        out(
            result.stderr.strip()
        )


shell = ROOT / "gerar_short.sh"

if shell.is_file():

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(shell),
        ],
        cwd=ROOT,
    )

    if result.returncode == 0:

        add_pass(
            "GERAR_SHORT_SYNTAX"
        )

    else:

        add_error(
            "GERAR_SHORT_SYNTAX"
        )


section(
    "3. UNRESOLVED GLOBALS"
)


def unresolved_globals(path):

    src = read(path)

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

                if name in BUILTINS:
                    continue

                unresolved.add(name)

            walk(child)


    walk(table)

    return sorted(unresolved)


for path in python_files:

    try:

        unresolved = unresolved_globals(
            path
        )

    except Exception as exc:

        add_warning(
            f"GLOBAL_AUDIT_EXCEPTION:{path.name}:{type(exc).__name__}"
        )

        continue


    if unresolved:

        out(
            f"UNRESOLVED_GLOBALS={path.name}:"
            +
            ",".join(unresolved)
        )

        if path.name == "visual_selection_engine_v4.py":

            add_error(
                "VSE4_UNRESOLVED_GLOBALS"
            )

        else:

            add_warning(
                f"UNRESOLVED_GLOBALS:{path.name}"
            )

    else:

        out(
            f"UNRESOLVED_GLOBALS={path.name}:NONE"
        )


section(
    "4. DUPLICATE DEFINITIONS INSIDE FILES"
)


for path in python_files:

    try:
        tree = parse(path)
    except Exception:
        continue


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


    counts = Counter(names)

    duplicates = {
        name: count
        for name, count
        in counts.items()
        if count > 1
    }


    if duplicates:

        out(
            f"DUPLICATE_DEFINITIONS={path.name}:{duplicates}"
        )

        add_warning(
            f"DUPLICATE_DEFINITIONS:{path.name}"
        )

    else:

        out(
            f"DUPLICATE_DEFINITIONS={path.name}:NONE"
        )


section(
    "5. OVERLAPPING VISUAL API"
)


exports = defaultdict(list)


for name in VISUAL_FILES:

    path = ROOT / name

    if not path.is_file():
        continue

    try:
        tree = parse(path)
    except Exception:
        continue


    for node in tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            exports[
                node.name
            ].append(
                name
            )


interesting_overlap = {
    name: files
    for name, files
    in exports.items()
    if len(files) > 1
}


for name, files in sorted(
    interesting_overlap.items()
):

    out(
        f"OVERLAP={name}:"
        +
        ",".join(files)
    )


dangerous_overlap = {
    "enabled",
    "reset_state",
    "finalize_pool",
    "note_success",
    "commit_media",
    "install_search_rescue",
}


for name in dangerous_overlap:

    files = exports.get(
        name,
        [],
    )

    if len(files) > 1:

        add_warning(
            f"MULTIPLE_IMPLEMENTATIONS:{name}:{','.join(files)}"
        )


section(
    "6. FEATURE FLAG CONSISTENCY"
)


flags_by_file = defaultdict(set)

flag_regex = re.compile(
    r"""SAP_[A-Z0-9_]+"""
)


for name in VISUAL_FILES + ["midia.py"]:

    path = ROOT / name

    if not path.is_file():
        continue


    for match in flag_regex.findall(
        read(path)
    ):

        flags_by_file[
            name
        ].add(match)


all_flags = set()


for name, flags in flags_by_file.items():

    all_flags.update(flags)

    out(
        f"FLAGS={name}:"
        +
        ",".join(
            sorted(flags)
        )
    )


v42_flags = sorted(
    x
    for x in all_flags
    if "V42" in x
)


out(
    "V42_FLAGS="
    +
    ",".join(v42_flags)
)


if len(v42_flags) > 1:

    add_warning(
        "MULTIPLE_V42_KILL_SWITCH_NAMES:"
        +
        ",".join(v42_flags)
    )


section(
    "7. EXCEPTION SWALLOWING"
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


        body = node.body


        if (
            len(body) == 1
            and
            isinstance(
                body[0],
                ast.Pass,
            )
        ):

            silent.append(
                node.lineno
            )


    out(
        f"SILENT_EXCEPT_PASS={path.name}:"
        +
        (
            ",".join(
                map(str, silent)
            )
            if silent
            else
            "NONE"
        )
    )


    if len(silent) >= 5:

        add_warning(
            f"MANY_SILENT_EXCEPTIONS:{path.name}:{len(silent)}"
        )


section(
    "8. FILE DELETION / DESTRUCTIVE OPERATIONS"
)


danger_patterns = (
    "os.remove",
    "os.unlink",
    "shutil.rmtree",
    ".unlink",
    "rmtree",
)


for name in VISUAL_FILES + ["midia.py"]:

    path = ROOT / name

    if not path.is_file():
        continue


    lines = read(path).splitlines()

    hits = []


    for index, line in enumerate(
        lines,
        start=1,
    ):

        if any(
            pattern in line
            for pattern in danger_patterns
        ):

            hits.append(
                (
                    index,
                    line.strip(),
                )
            )


    if not hits:

        out(
            f"DESTRUCTIVE_OPS={name}:NONE"
        )

        continue


    out(
        f"DESTRUCTIVE_OPS={name}:{len(hits)}"
    )

    for line_no, text in hits:

        out(
            f"  {line_no}: {text}"
        )


section(
    "9. MIDIA.PY V42 INTEGRATION"
)


midia = ROOT / "midia.py"


if midia.is_file():

    src = read(midia)


    bridge_names = (
        "visual_selection_bridge_v42",
        "visual_pipeline_bridge_v42",
        "visual_selection_runtime_v42",
        "visual_runtime_v42",
        "visual_selection_engine_v4",
    )


    integration_count = 0


    for name in bridge_names:

        count = src.count(name)

        out(
            f"MIDIA_REFERENCE={name}:{count}"
        )

        integration_count += count


    out(
        f"MIDIA_V42_TOTAL_REFERENCES={integration_count}"
    )


    if integration_count == 0:

        add_error(
            "MIDIA_HAS_NO_V42_REFERENCE"
        )

    elif integration_count > 8:

        add_warning(
            "MIDIA_HAS_MANY_V42_REFERENCES_POSSIBLE_DOUBLE_HOOK"
        )


section(
    "10. PROVIDER ACQUISITION"
)


if midia.is_file():

    tree = parse(midia)


    definitions = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }


    for name in REQUIRED_PROVIDER_FUNCTIONS:

        if name in definitions:

            out(
                f"PROVIDER_FUNCTION={name}:PASS"
            )

        else:

            add_warning(
                f"PROVIDER_FUNCTION_MISSING:{name}"
            )


    buscar = definitions.get(
        "buscar_todos_candidatos"
    )


    if buscar:

        calls = []


        for node in ast.walk(
            buscar
        ):

            if isinstance(
                node,
                ast.Call,
            ):

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

            found = provider_name in calls

            out(
                f"PROVIDER_CALL={provider_name}:"
                f"{'YES' if found else 'NO'}"
            )


section(
    "11. DOWNLOAD SUCCESS / COMMIT FLOW"
)


if midia.is_file():

    src = read(midia)


    patterns = {
        "baixar_candidato_5_2":
            r"baixar_candidato_5_2",

        "FAILOVER_QUALIDADE":
            r"FAILOVER:\s*QUALIDADE",

        "SCENE_COMMIT_LOCK":
            r"SCENE_COMMIT_LOCK",

        "commit_media":
            r"commit_media",

        "note_success":
            r"note_success",
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
            f"MIDIA_FLOW={name}:{count}"
        )


section(
    "12. VSE4 ENGINE RUNTIME"
)


engine = ROOT / "visual_selection_engine_v4.py"


if engine.is_file():

    try:

        import runpy

        ns = runpy.run_path(
            str(engine),
            run_name="vse42_master_audit",
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
            "must_tier",
        )


        for name in required_functions:

            if callable(
                ns.get(name)
            ):

                out(
                    f"VSE4_FUNCTION={name}:PASS"
                )

            else:

                add_error(
                    f"VSE4_FUNCTION_MISSING:{name}"
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
            "WRONG_RESULT="
            +
            json.dumps(
                a,
                ensure_ascii=False,
                default=str,
            )
        )

        out(
            "CORRECT_RESULT="
            +
            json.dumps(
                b,
                ensure_ascii=False,
                default=str,
            )
        )


        hard_wrong = bool(
            a.get(
                "hard_mismatch",
                False,
            )
        )


        hard_correct = bool(
            b.get(
                "hard_mismatch",
                False,
            )
        )


        out(
            f"GEO_WRONG_HARD_MISMATCH={hard_wrong}"
        )

        out(
            f"GEO_CORRECT_HARD_MISMATCH={hard_correct}"
        )


        if hard_wrong:

            add_pass(
                "GEO_CONTRADICTION_BLOCK"
            )

        else:

            add_error(
                "GEO_CONTRADICTION_NOT_BLOCKED"
            )


        if not hard_correct:

            add_pass(
                "CORRECT_GEOGRAPHY_ALLOWED"
            )

        else:

            add_error(
                "CORRECT_GEOGRAPHY_FALSE_POSITIVE"
            )


        ae = float(
            a.get(
                "effective",
                a.get(
                    "score",
                    0,
                ),
            )
            or 0
        )


        be = float(
            b.get(
                "effective",
                b.get(
                    "score",
                    0,
                ),
            )
            or 0
        )


        out(
            f"WRONG_EFFECTIVE={ae}"
        )

        out(
            f"CORRECT_EFFECTIVE={be}"
        )


        if be > ae:

            add_pass(
                "CORRECT_BEATS_WRONG"
            )

        else:

            add_error(
                "WRONG_MEDIA_OUTRANKS_CORRECT_MEDIA"
            )


    except Exception as exc:

        add_error(
            "VSE4_RUNTIME_EXCEPTION:"
            f"{type(exc).__name__}:{exc}"
        )

        out(
            traceback.format_exc()
        )


section(
    "13. GENERAL SEMANTIC REGRESSION"
)


if engine.is_file():

    try:

        import runpy

        ns = runpy.run_path(
            str(engine),
            run_name="vse42_semantic_regression",
        )

        score = ns[
            "score_candidate"
        ]


        cases = [
            {
                "name":
                    "FORENSIC_VS_PILLS",

                "scene":
                    "Laudo pericial encontrou evidências importantes",

                "bad":
                    {
                        "provider": "Pixabay",
                        "title": "Pills medication pharmacy",
                        "score": 220,
                        "must": "2/2",
                    },

                "good":
                    {
                        "provider": "Wikimedia",
                        "title": "Forensic evidence laboratory report",
                        "score": 130,
                        "must": "1/2",
                    },
            },

            {
                "name":
                    "POLICE_VS_LIFESTYLE",

                "scene":
                    "Polícia iniciou investigação criminal no apartamento",

                "bad":
                    {
                        "provider": "Pixabay",
                        "title": "Happy woman relaxing bedroom lifestyle",
                        "score": 230,
                        "must": "2/2",
                    },

                "good":
                    {
                        "provider": "Wikimedia",
                        "title": "Police investigation residential building",
                        "score": 120,
                        "must": "1/2",
                    },
            },

            {
                "name":
                    "COURT",

                "scene":
                    "O julgamento terminou com condenação no tribunal",

                "bad":
                    {
                        "provider": "Pixabay",
                        "title": "Coffee office desk lifestyle",
                        "score": 210,
                        "must": "2/2",
                    },

                "good":
                    {
                        "provider": "Pixabay",
                        "title": "Courtroom judge gavel justice trial",
                        "score": 125,
                        "must": "1/2",
                    },
            },
        ]


        for case in cases:

            state = {
                "providers": [],
                "groups": [],
                "types": [],
                "keys": [],
            }


            bad = score(
                case[
                    "bad"
                ],
                case[
                    "scene"
                ],
                state,
            )


            good = score(
                case[
                    "good"
                ],
                case[
                    "scene"
                ],
                state,
            )


            bad_effective = float(
                bad.get(
                    "effective",
                    0,
                )
                or 0
            )

            good_effective = float(
                good.get(
                    "effective",
                    0,
                )
                or 0
            )


            out(
                f"SEMANTIC_CASE={case['name']}"
            )

            out(
                f"  BAD_EFFECTIVE={bad_effective}"
            )

            out(
                f"  GOOD_EFFECTIVE={good_effective}"
            )

            out(
                f"  BAD_HARD={bad.get('hard_mismatch')}"
            )

            out(
                f"  BAD_REASONS={bad.get('safety_reasons')}"
            )


            if good_effective > bad_effective:

                add_pass(
                    f"SEMANTIC:{case['name']}"
                )

            else:

                add_error(
                    f"SEMANTIC_FAILURE:{case['name']}"
                )


    except Exception as exc:

        add_error(
            f"SEMANTIC_TEST_EXCEPTION:{type(exc).__name__}:{exc}"
        )


section(
    "14. PROVIDER / TYPE DIVERSITY STATIC CHECK"
)


diversity_terms = (
    "providers",
    "source_group",
    "groups",
    "types",
    "provider_repeat",
    "diversity",
)


for name in VISUAL_FILES:

    path = ROOT / name

    if not path.is_file():
        continue


    src = read(
        path
    ).casefold()


    hits = [
        term
        for term
        in diversity_terms
        if term.casefold()
        in src
    ]


    out(
        f"DIVERSITY_FEATURES={name}:"
        +
        ",".join(hits)
    )


section(
    "15. V42 MULTIPLE STATE STORES"
)


state_files = []


for name in VISUAL_FILES:

    path = ROOT / name

    if not path.is_file():
        continue


    src = read(path)


    if re.search(
        r"\bSTATE\s*=\s*\{",
        src,
    ):

        state_files.append(
            name
        )


    if re.search(
        r"_VSE\d*_STATE\s*=\s*\{",
        src,
    ):

        state_files.append(
            name
        )


out(
    "STATE_STORE_FILES="
    +
    ",".join(
        state_files
    )
)


if len(
    set(state_files)
) > 1:

    add_warning(
        "MULTIPLE_VISUAL_STATE_STORES"
    )


section(
    "16. TOP-LEVEL EXECUTION RISK"
)


for path in python_files:

    try:
        tree = parse(path)
    except Exception:
        continue


    risky = []


    for node in tree.body:

        if isinstance(
            node,
            ast.Expr,
        ) and isinstance(
            node.value,
            ast.Call,
        ):

            try:
                name = ast.unparse(
                    node.value.func
                )
            except Exception:
                name = "unknown"

            if name not in {
                "print",
            }:

                risky.append(
                    (
                        node.lineno,
                        name,
                    )
                )


    if risky:

        out(
            f"TOP_LEVEL_CALLS={path.name}:"
            +
            ",".join(
                f"{line}:{name}"
                for line, name
                in risky
            )
        )


section(
    "17. CORE HASHES"
)


for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
):

    path = ROOT / name

    if path.is_file():

        out(
            f"CORE_HASH={name}:{sha256(path)}"
        )


section(
    "18. FINAL VERDICT"
)


out(
    f"PASS_COUNT={len(passes)}"
)

out(
    f"WARNING_COUNT={len(warnings)}"
)

out(
    f"ERROR_COUNT={len(errors)}"
)


if warnings:

    out()
    out(
        "WARNINGS:"
    )

    for item in warnings:

        out(
            f" - {item}"
        )


if errors:

    out()
    out(
        "ERRORS:"
    )

    for item in errors:

        out(
            f" - {item}"
        )


out()


if not errors:

    if warnings:

        out(
            "AUDIT_STATUS=PASS_WITH_WARNINGS"
        )

    else:

        out(
            "AUDIT_STATUS=PASS"
        )

else:

    out(
        "AUDIT_STATUS=FAIL"
    )


out(
    f"REPORT={REPORT}"
)

out(
    "MIDIA_PY_MODIFIED=NO"
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
    "AUDIT_COMPLETE=YES"
)
