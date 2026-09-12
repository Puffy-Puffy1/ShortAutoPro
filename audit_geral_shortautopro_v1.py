#!/usr/bin/env python3

from pathlib import Path
import ast
import builtins
import hashlib
import json
import os
import re
import runpy
import subprocess
import symtable
import traceback
from collections import Counter, defaultdict


ROOT = Path.home() / "ShortAutoPro"

VSE = ROOT / "visual_selection_engine_v4.py"
MIDIA = ROOT / "midia.py"
VIDEO = ROOT / "video.py"
V6 = ROOT / "v6.py"
GERAR = ROOT / "gerar_short.sh"
GUARD = ROOT / "fresh_render_guard_v1.py"
COMMIT = ROOT / "visual_scene_commit_lock_v1.py"


PASS = []
WARN = []
FAIL = []


def section(title):
    print()
    print("=" * 76)
    print(f" {title}")
    print("=" * 76)


def result(name, ok, detail="", warning=False):

    text = (
        f"{name}="
        f"{'PASS' if ok else ('WARN' if warning else 'FAIL')}"
    )

    if detail:
        text += f" | {detail}"

    print(text)

    if ok:
        PASS.append(name)
    elif warning:
        WARN.append((name, detail))
    else:
        FAIL.append((name, detail))


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def load_text(path):

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def compile_python(path):

    p = subprocess.run(
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

    return (
        p.returncode == 0,
        p.stderr.strip(),
    )


def shell_syntax(path):

    p = subprocess.run(
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

    return (
        p.returncode == 0,
        p.stderr.strip(),
    )


def latest_media_dir():

    base = ROOT / "imagens"

    if not base.is_dir():
        return None

    dirs = [
        p
        for p in base.glob("short_*")
        if p.is_dir()
    ]

    if not dirs:
        return None

    return max(
        dirs,
        key=lambda p: p.stat().st_mtime,
    )


# ============================================================
# 1. CRITICAL FILES
# ============================================================

section("1. CRITICAL FILES")

critical = [
    VSE,
    MIDIA,
    VIDEO,
    V6,
    GERAR,
    GUARD,
    COMMIT,
    ROOT / "media_diversity_guard_v1.py",
    ROOT / "media_provenance_capture_v1.py",
    ROOT / "render_input_fingerprint_v1.py",
]

for path in critical:

    exists = path.is_file()

    result(
        f"FILE_{path.name}",
        exists,
        (
            f"{path.stat().st_size} bytes"
            if exists
            else "missing"
        ),
    )


# ============================================================
# 2. CRITICAL HASHES
# ============================================================

section("2. CRITICAL HASHES")

for path in [
    VSE,
    MIDIA,
    VIDEO,
    V6,
    GERAR,
]:

    if path.is_file():
        print(
            f"SHA256 {path.name} "
            f"{sha256(path)}"
        )


# ============================================================
# 3. ALL PYTHON SYNTAX
# ============================================================

section("3. PYTHON SYNTAX - WHOLE PROJECT")

python_files = sorted(
    ROOT.glob("*.py")
)

py_failures = []

for path in python_files:

    ok, err = compile_python(path)

    if not ok:
        py_failures.append(
            (
                path.name,
                err,
            )
        )

print(
    f"PYTHON_FILES_CHECKED={len(python_files)}"
)

result(
    "ALL_TOPLEVEL_PYTHON_COMPILE",
    not py_failures,
    (
        "0 failures"
        if not py_failures
        else f"{len(py_failures)} failures"
    ),
)

for name, error in py_failures[:20]:

    print()
    print(
        f"PYTHON_COMPILE_FAILURE={name}"
    )

    print(
        error[-1200:]
    )


# ============================================================
# 4. SHELL SYNTAX
# ============================================================

section("4. SHELL SYNTAX")

shell_files = sorted(
    ROOT.glob("*.sh")
)

shell_failures = []

for path in shell_files:

    ok, err = shell_syntax(path)

    if not ok:

        shell_failures.append(
            (
                path.name,
                err,
            )
        )

print(
    f"SHELL_FILES_CHECKED={len(shell_files)}"
)

result(
    "ALL_TOPLEVEL_SHELL_SYNTAX",
    not shell_failures,
    (
        "0 failures"
        if not shell_failures
        else f"{len(shell_failures)} failures"
    ),
)

for name, error in shell_failures[:20]:

    print(
        f"SHELL_FAILURE={name} | {error}"
    )


# ============================================================
# 5. DUPLICATE TOP-LEVEL DEFINITIONS
# ============================================================

section("5. DUPLICATE TOP-LEVEL DEFINITIONS")

duplicate_records = []

for path in python_files:

    try:

        tree = ast.parse(
            load_text(path),
            filename=str(path),
        )

    except Exception:
        continue

    definitions = defaultdict(
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

            definitions[
                node.name
            ].append(
                node.lineno
            )

    for name, lines in definitions.items():

        if len(lines) > 1:

            duplicate_records.append(
                (
                    path.name,
                    name,
                    lines,
                )
            )


if duplicate_records:

    for filename, name, lines in duplicate_records[:50]:

        print(
            f"DUPLICATE_DEF "
            f"file={filename} "
            f"name={name} "
            f"lines={lines}"
        )


result(
    "TOPLEVEL_DUPLICATE_DEFS",
    not duplicate_records,
    (
        "none"
        if not duplicate_records
        else f"{len(duplicate_records)} duplicate definitions"
    ),
    warning=bool(
        duplicate_records
    ),
)


# ============================================================
# 6. VSE4 TRUE GLOBAL AUDIT
# ============================================================

section("6. VSE4 TRUE GLOBAL AUDIT")

vse_unresolved = set()

if VSE.is_file():

    vse_src = load_text(
        VSE
    )

    try:

        table = symtable.symtable(
            vse_src,
            str(VSE),
            "exec",
        )

        defined = set()

        for symbol in table.get_symbols():

            if (
                symbol.is_assigned()
                or symbol.is_imported()
                or symbol.is_namespace()
            ):

                defined.add(
                    symbol.get_name()
                )

        builtin_names = set(
            dir(builtins)
        )

        def walk_scope(scope):

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

                    vse_unresolved.add(
                        name
                    )

                walk_scope(
                    child
                )

        walk_scope(
            table
        )

    except Exception as exc:

        FAIL.append(
            (
                "VSE4_GLOBAL_AUDIT_RUNTIME",
                repr(exc),
            )
        )

        print(
            "GLOBAL_AUDIT_EXCEPTION="
            f"{type(exc).__name__}: {exc}"
        )


print(
    "TRUE_UNRESOLVED_GLOBALS="
    +
    (
        "NONE"
        if not vse_unresolved
        else ",".join(
            sorted(
                vse_unresolved
            )
        )
    )
)

result(
    "VSE4_GLOBAL_AUDIT",
    not vse_unresolved,
)


# ============================================================
# 7. VSE4 REQUIRED SYMBOLS
# ============================================================

section("7. VSE4 REQUIRED SYMBOLS")

vse_ns = None

try:

    vse_ns = runpy.run_path(
        str(VSE),
        run_name="shortautopro_general_audit",
    )

    result(
        "VSE4_MODULE_LOAD",
        True,
    )

except Exception as exc:

    result(
        "VSE4_MODULE_LOAD",
        False,
        f"{type(exc).__name__}: {exc}",
    )


required_symbols = [
    "score_candidate",
    "candidate_text",
    "tokens",
    "concept_hits",
    "geo_hits",
    "objget",
    "provider",
    "source_group",
    "media_type",
    "candidate_key",
    "base_score",
    "must_tier",
    "flatten_candidates",
    "resolution_bonus",
]


missing_symbols = []

if vse_ns is not None:

    for name in required_symbols:

        if name not in vse_ns:
            missing_symbols.append(
                name
            )


print(
    "MISSING_VSE4_SYMBOLS="
    +
    (
        "NONE"
        if not missing_symbols
        else ",".join(
            missing_symbols
        )
    )
)

result(
    "VSE4_REQUIRED_SYMBOLS",
    not missing_symbols,
)


# ============================================================
# 8. VSE4 SELF TEST
# ============================================================

section("8. VSE4 BUILT-IN SELF TEST")

self_test_ok = False

if vse_ns is not None:

    fn = vse_ns.get(
        "self_test"
    )

    if callable(fn):

        try:

            fn()

            self_test_ok = True

        except Exception as exc:

            print(
                "SELF_TEST_EXCEPTION="
                f"{type(exc).__name__}: {exc}"
            )

            traceback.print_exc(
                limit=4
            )

    else:

        print(
            "SELF_TEST_FUNCTION=MISSING"
        )


result(
    "VSE4_SELF_TEST",
    self_test_ok,
)


# ============================================================
# 9. VSE4 BEHAVIORAL QUALITY SUITE
# ============================================================

section("9. VSE4 BEHAVIORAL QUALITY SUITE")

behavior_results = {}

if (
    vse_ns is not None
    and
    callable(
        vse_ns.get(
            "score_candidate"
        )
    )
):

    score_candidate = vse_ns[
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

    scenarios = {

        "GEO_WRONG": (
            "Investigação em apartamento na cidade de São Paulo",
            {
                "provider": "Pixabay",
                "tipo": "foto",
                "title":
                    "Empire State Building Manhattan New York",
                "must": "2/2",
                "score": 240,
                "width": 1920,
                "height": 1080,
            },
        ),

        "GEO_CORRECT": (
            "Investigação em apartamento na cidade de São Paulo",
            {
                "provider": "Wikimedia",
                "tipo": "foto",
                "title":
                    "Apartment building Sao Paulo Brazil",
                "must": "1/2",
                "score": 120,
                "width": 1920,
                "height": 1080,
            },
        ),

        "MEDICINE_WRONG": (
            "Laudo pericial revelou evidências na cena do crime",
            {
                "provider": "Pixabay",
                "tipo": "foto",
                "title":
                    "Pills medication pharmacy tablets",
                "must": "1/2",
                "score": 200,
                "width": 1920,
                "height": 1080,
            },
        ),

        "FORENSIC_CORRECT": (
            "Laudo pericial revelou evidências na cena do crime",
            {
                "provider": "Pexels",
                "tipo": "video",
                "title":
                    "Forensic investigation evidence laboratory",
                "must": "2/2",
                "score": 150,
                "width": 1920,
                "height": 1080,
            },
        ),

        "LIFESTYLE_WRONG": (
            "Polícia iniciou investigação do crime",
            {
                "provider": "Pixabay",
                "tipo": "foto",
                "title":
                    "Happy woman relaxing in bedroom lifestyle",
                "must": "1/2",
                "score": 210,
                "width": 1920,
                "height": 1080,
            },
        ),

        "POLICE_CORRECT": (
            "Polícia iniciou investigação do crime",
            {
                "provider": "Pexels",
                "tipo": "video",
                "title":
                    "Police detective investigation crime scene",
                "must": "2/2",
                "score": 150,
                "width": 1920,
                "height": 1080,
            },
        ),

        "NEUTRAL_CITY": (
            "Movimento intenso no centro da cidade",
            {
                "provider": "Pixabay",
                "tipo": "video",
                "title":
                    "Generic urban city traffic street",
                "must": "1/2",
                "score": 130,
                "width": 1920,
                "height": 1080,
            },
        ),
    }


    for name, (
        scene,
        candidate,
    ) in scenarios.items():

        try:

            r = score_candidate(
                candidate,
                scene,
                state,
            )

            behavior_results[
                name
            ] = r

            print()
            print(
                f"SCENARIO={name}"
            )

            print(
                "hard_mismatch="
                f"{r.get('hard_mismatch')}"
            )

            print(
                "effective="
                f"{r.get('effective')}"
            )

            for key in (
                "hard_reason",
                "geo_hits",
                "geo_conflict",
                "mismatch",
                "semantic",
                "must",
                "must_tier",
            ):

                if key in r:

                    print(
                        f"{key}="
                        f"{r[key]}"
                    )

        except Exception as exc:

            behavior_results[
                name
            ] = {
                "_exception":
                    f"{type(exc).__name__}: {exc}"
            }

            print(
                f"SCENARIO={name} "
                f"EXCEPTION="
                f"{type(exc).__name__}: {exc}"
            )


def hard(name):

    return bool(
        behavior_results.get(
            name,
            {},
        ).get(
            "hard_mismatch",
            False,
        )
    )


def effective(name):

    try:

        return float(
            behavior_results.get(
                name,
                {},
            ).get(
                "effective",
                0,
            )
        )

    except Exception:
        return 0.0


quality_checks = {

    "GEO_WRONG_BLOCKED":
        hard(
            "GEO_WRONG"
        ),

    "GEO_CORRECT_SAFE":
        not hard(
            "GEO_CORRECT"
        ),

    "GEO_CORRECT_RANKS_ABOVE_WRONG":
        (
            effective(
                "GEO_CORRECT"
            )
            >
            effective(
                "GEO_WRONG"
            )
        ),

    "MEDICINE_FALSE_ASSOC_BLOCKED":
        hard(
            "MEDICINE_WRONG"
        ),

    "FORENSIC_CORRECT_SAFE":
        not hard(
            "FORENSIC_CORRECT"
        ),

    "GENERIC_LIFESTYLE_BLOCKED":
        hard(
            "LIFESTYLE_WRONG"
        ),

    "POLICE_CORRECT_SAFE":
        not hard(
            "POLICE_CORRECT"
        ),

    "NEUTRAL_CITY_SAFE":
        not hard(
            "NEUTRAL_CITY"
        ),
}


print()

for name, ok in quality_checks.items():

    result(
        name,
        ok,
    )


quality_points = sum(
    bool(v)
    for v in quality_checks.values()
)

print(
    f"QUALITY_POINTS="
    f"{quality_points}/"
    f"{len(quality_checks)}"
)


# ============================================================
# 10. GEO DIRECT TEST
# ============================================================

section("10. GEOGRAPHY DIRECT TEST")

if vse_ns is not None:

    geo_hits = vse_ns.get(
        "geo_hits"
    )

    if callable(
        geo_hits
    ):

        sp = set(
            geo_hits(
                "São Paulo Brazil"
            )
        )

        ny = set(
            geo_hits(
                "Empire State Building Manhattan New York"
            )
        )

        print(
            f"SAO_PAULO_GEO={sorted(sp)}"
        )

        print(
            f"NEW_YORK_GEO={sorted(ny)}"
        )

        result(
            "GEO_DISTINCT_SP_NY",
            bool(sp)
            and bool(ny)
            and sp != ny,
        )


# ============================================================
# 11. MEDIA PROVIDER ACQUISITION
# ============================================================

section("11. MEDIA PROVIDER ACQUISITION")

provider_functions = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
]


defs_map = {}

if MIDIA.is_file():

    try:

        mtree = ast.parse(
            load_text(
                MIDIA
            )
        )

        defs_map = {
            node.name: node
            for node in mtree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }

    except Exception as exc:

        print(
            "MIDIA_AST_ERROR="
            f"{type(exc).__name__}: {exc}"
        )


for name in provider_functions:

    result(
        f"PROVIDER_FUNCTION_{name}",
        name in defs_map,
    )


buscar = defs_map.get(
    "buscar_todos_candidatos"
)

expected_calls = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
}

calls = set()

if buscar:

    for node in ast.walk(
        buscar
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

        elif isinstance(
            node.func,
            ast.Attribute,
        ):

            calls.add(
                node.func.attr
            )


for name in sorted(
    expected_calls
):

    result(
        f"BUSCAR_CALL_{name}",
        name in calls,
        warning=(
            name not in calls
        ),
    )


print(
    "BUSCAR_TODOS_CALLS="
    +
    ",".join(
        sorted(calls)
    )
)


# ============================================================
# 12. PROVIDER CONFIG PRESENCE
# ============================================================

section("12. PROVIDER CONFIG / API KEY NAMES")

midia_src = load_text(
    MIDIA
)

possible_provider_envs = sorted(
    set(
        re.findall(
            r'["\']([A-Z][A-Z0-9_]*(?:PEXELS|PIXABAY|COVERR)[A-Z0-9_]*)["\']',
            midia_src,
        )
    )
)

if possible_provider_envs:

    for name in possible_provider_envs:

        value = os.getenv(
            name
        )

        print(
            f"{name}="
            f"{'SET' if value else 'NOT_SET'}"
        )

else:

    print(
        "PROVIDER_ENV_NAMES=NOT_DETECTED"
    )


# ============================================================
# 13. VSE4 ACTIVE IN MIDIA.PY
# ============================================================

section("13. VSE4 PIPELINE INTEGRATION")

integration_patterns = {

    "VSE4_IMPORT":
        r"visual_selection_engine_v4",

    "VSE4_SCORE_CALL":
        r"score_candidate",

    "VSE4_MARKER":
        r"VSE4",

    "FINAL_GATE_V3":
        r"visual_selection_final_gate_v3",

    "DIVERSITY_GUARD":
        r"media_diversity_guard_v1",

    "PROVENANCE":
        r"media_provenance_capture_v1",
}


for name, pattern in integration_patterns.items():

    found = bool(
        re.search(
            pattern,
            midia_src,
            flags=re.IGNORECASE,
        )
    )

    result(
        name,
        found,
        warning=not found,
    )


# ============================================================
# 14. SCENE COMMIT LOCK
# ============================================================

section("14. SCENE COMMIT LOCK")

commit_src = load_text(
    COMMIT
)

commit_checks = {

    "COMMIT_LOCK_MODULE":
        COMMIT.is_file(),

    "COMMIT_LOCK_COMMITTED_LOG":
        "COMMITTED" in commit_src,

    "COMMIT_LOCK_BLOCKED_LOG":
        "BLOCKED" in commit_src,

    "COMMIT_LOCK_KILL_SWITCH":
        "SAP_SCENE_COMMIT_LOCK"
        in commit_src,
}


for name, ok in commit_checks.items():

    result(
        name,
        ok,
    )


# ============================================================
# 15. FRESH RENDER GUARD SAFETY
# ============================================================

section("15. FRESH RENDER GUARD SAFETY")

guard_src = load_text(
    GUARD
)

guard_checks = {

    "GUARD_EXISTS":
        GUARD.is_file(),

    "ASS_PROTECTED":
        ".ass" in guard_src,

    "AUDIO_PROTECTED":
        (
            ".mp3" in guard_src
            and
            ".wav" in guard_src
        ),

    "VIDEO_CLEAN_TARGET":
        ".mp4" in guard_src,

    "NO_BLIND_RM_RF":
        "shutil.rmtree"
        not in guard_src,
}


for name, ok in guard_checks.items():

    result(
        name,
        ok,
        warning=not ok,
    )


# ============================================================
# 16. LATEST MEDIA DIRECTORY
# ============================================================

section("16. LATEST MEDIA SET")

media_dir = latest_media_dir()

if media_dir is None:

    result(
        "LATEST_MEDIA_DIR",
        False,
        "no imagens/short_* directory",
    )

else:

    sid = media_dir.name.removeprefix(
        "short_"
    )

    print(
        f"LATEST_SHORT_ID={sid}"
    )

    print(
        f"MEDIA_DIR={media_dir}"
    )

    scene_bad = []
    scene_files = []

    for i in range(
        1,
        13,
    ):

        prefix = f"scene_{i:02d}."

        files = [
            p
            for p in media_dir.iterdir()
            if (
                p.is_file()
                and
                p.name.startswith(
                    prefix
                )
            )
        ]

        print(
            f"SCENE_{i:02d}_COUNT="
            f"{len(files)}"
        )

        for p in files:

            scene_files.append(
                p
            )

            print(
                f"  {p.name} "
                f"{p.stat().st_size} bytes"
            )

        if len(files) != 1:

            scene_bad.append(
                i
            )


    result(
        "MEDIA_12_SCENES_UNIQUE",
        not scene_bad,
        (
            "12/12 exactly one media"
            if not scene_bad
            else f"bad scenes={scene_bad}"
        ),
    )


    # --------------------------------------------------------
    # DUPLICATE CONTENT HASH
    # --------------------------------------------------------

    hash_map = defaultdict(
        list
    )

    for path in scene_files:

        try:

            hash_map[
                sha256(path)
            ].append(
                path.name
            )

        except Exception:
            pass


    duplicates = {
        h: names
        for h, names in hash_map.items()
        if len(names) > 1
    }


    if duplicates:

        for h, names in duplicates.items():

            print(
                f"DUPLICATE_MEDIA_SHA "
                f"{h[:16]} "
                f"{names}"
            )


    result(
        "MEDIA_NO_EXACT_DUPLICATE_CONTENT",
        not duplicates,
        (
            "none"
            if not duplicates
            else f"{len(duplicates)} duplicate hashes"
        ),
        warning=bool(
            duplicates
        ),
    )


# ============================================================
# 17. V6 INPUT/OUTPUT PATH CONSISTENCY
# ============================================================

section("17. RENDER PIPELINE STATIC PATH CHECK")

video_src = load_text(
    VIDEO
)

v6_src = load_text(
    V6
)

render_checks = {

    "VIDEO_USES_SHORT_ID":
        "SHORT_ID" in video_src,

    "V6_USES_SHORT_ID":
        "SHORT_ID" in v6_src,

    "V6_EXPECTS_VIDEO_SEM_AUDIO":
        "video_sem_audio.mp4"
        in v6_src,

    "V6_EXPECTS_ASS":
        ".ass"
        in v6_src,

    "V6_EXPECTS_AUDIO":
        ".mp3"
        in v6_src,

    "V6_NAMESPACED_TEMP":
        (
            '"temp"' in v6_src
            or
            "'temp'" in v6_src
        )
        and
        "SHORT_ID" in v6_src,
}


for name, ok in render_checks.items():

    result(
        name,
        ok,
    )


# ============================================================
# 18. DANGEROUS EMPTY-HASH CERTIFICATION PATTERN
# ============================================================

section("18. CERTIFICATION SAFETY")

certification_files = [
    ROOT / "render_output_certifier_v1.py",
    ROOT / "render_transaction_v1.py",
]

for path in certification_files:

    if not path.is_file():

        result(
            f"{path.name}_EXISTS",
            False,
            warning=True,
        )

        continue

    src = load_text(
        path
    )

    result(
        f"{path.name}_COMPILES",
        compile_python(
            path
        )[0],
    )

    suspicious = (
        '== ""' in src
        or "== ''" in src
    )

    print(
        f"{path.name}_EMPTY_VALUE_CHECK_PRESENT="
        f"{'YES' if suspicious else 'UNKNOWN'}"
    )


# ============================================================
# 19. LARGE FILE / ACCIDENTAL CORRUPTION INDICATORS
# ============================================================

section("19. FILE SIZE SANITY")

for path in [
    VSE,
    MIDIA,
    VIDEO,
    V6,
]:

    if not path.is_file():
        continue

    size = path.stat().st_size

    print(
        f"{path.name}_BYTES={size}"
    )

    # Não é erro absoluto, apenas sinal de possível patch
    # duplicado quando cresce demais.
    if (
        path.name
        == "visual_selection_engine_v4.py"
        and
        size > 250_000
    ):

        result(
            "VSE4_SIZE_SANITY",
            False,
            f"{size} bytes - review for duplicated patch blocks",
            warning=True,
        )


# ============================================================
# 20. TODO / FIXME / BROKEN MARKERS
# ============================================================

section("20. SUSPICIOUS DEVELOPMENT MARKERS")

markers = []

for path in [
    VSE,
    MIDIA,
    VIDEO,
    V6,
]:

    src = load_text(
        path
    )

    for lineno, line in enumerate(
        src.splitlines(),
        start=1,
    ):

        if re.search(
            r"\b(TODO|FIXME|BROKEN|HACK)\b",
            line,
            re.IGNORECASE,
        ):

            markers.append(
                (
                    path.name,
                    lineno,
                    line.strip()[:180],
                )
            )


for item in markers[:50]:

    print(
        "MARKER "
        f"{item[0]}:{item[1]} "
        f"{item[2]}"
    )


result(
    "NO_SUSPICIOUS_DEV_MARKERS",
    not markers,
    (
        "none"
        if not markers
        else f"{len(markers)} markers"
    ),
    warning=bool(
        markers
    ),
)


# ============================================================
# 21. FINAL SCORE
# ============================================================

section("21. GENERAL AUDIT SUMMARY")

total = (
    len(PASS)
    +
    len(WARN)
    +
    len(FAIL)
)

print(
    f"TOTAL_CHECKS={total}"
)

print(
    f"PASS_COUNT={len(PASS)}"
)

print(
    f"WARN_COUNT={len(WARN)}"
)

print(
    f"FAIL_COUNT={len(FAIL)}"
)


if FAIL:

    print()
    print("===== FAILURES =====")

    for name, detail in FAIL:

        print(
            f"FAIL | {name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )


if WARN:

    print()
    print("===== WARNINGS =====")

    for name, detail in WARN:

        print(
            f"WARN | {name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )


print()
print(
    "QUALITY_POINTS="
    f"{quality_points}/"
    f"{len(quality_checks)}"
)


if not FAIL:

    if WARN:

        status = (
            "PASS_WITH_WARNINGS"
        )

    else:

        status = (
            "PASS"
        )

else:

    status = (
        "FAIL"
    )


print(
    f"GENERAL_AUDIT_STATUS={status}"
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
    "PROJECT_FILES_MODIFIED=NO"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
