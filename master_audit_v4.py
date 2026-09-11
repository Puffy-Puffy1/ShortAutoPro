#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"
REPORT = ROOT / "temp" / "MASTER_AUDIT_V4_REPORT.txt"

SID = os.environ.get(
    "SHORT_ID",
    "2026-09-02_2358",
).strip()

KNOWN_OLD_VIDEO_HASH = (
    "6e9397d9c5debc568f7feb3f44e7c71"
    "aa2b13b024e791ad108d883a2874b9233"
)

KNOWN_CORE_HASHES = {
    "video.py":
        "756c0db576f664d474cb92676b4ad817"
        "37158f8a275bfad6348aa0a542d87b06",

    "v6.py":
        "13d1444fc2ae0198f8f070ad98238a36"
        "d7c939c6db2572c462cd9b07712286e7",

    "gerar_short.sh":
        "25af0e189440d3646de8da8772535e00"
        "ac1e8446097f5db56ed93144ab45eb7a",
}


CRITICAL = []
WARN = []
PASS = []
INFO = []


def out(*args):
    print(*args)


def section(title):
    out()
    out("=" * 72)
    out(title)
    out("=" * 72)


def good(message):
    PASS.append(message)
    out("PASS:", message)


def warning(message):
    WARN.append(message)
    out("WARN:", message)


def critical(message):
    CRITICAL.append(message)
    out("CRITICAL:", message)


def info(message):
    INFO.append(message)
    out("INFO:", message)


def sha256(path: Path) -> str:

    h = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            chunk = f.read(
                1024 * 1024
            )

            if not chunk:
                break

            h.update(chunk)

    return h.hexdigest()


def read(path: Path) -> str:

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def parse(path: Path):

    try:

        return ast.parse(
            read(path),
            filename=str(path),
        )

    except SyntaxError as exc:

        critical(
            f"SYNTAX_ERROR {path.relative_to(ROOT)} "
            f"line={exc.lineno}: {exc.msg}"
        )

        return None


section(
    "SHORTAUTOPRO MASTER AUDIT V4"
)

out(
    f"DATE={time.strftime('%Y-%m-%d %H:%M:%S')}"
)

out(
    f"ROOT={ROOT}"
)

out(
    f"SHORT_ID={SID}"
)

out(
    "MODE=STATIC_SAFE_AUDIT"
)

out(
    "NETWORK=NO"
)

out(
    "RENDER=NO"
)


# ============================================================
# 1. ESSENTIAL FILES
# ============================================================

section(
    "1. ESSENTIAL FILES"
)

essential = [
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


for name in essential:

    path = ROOT / name

    if path.is_file():

        good(
            f"FILE_EXISTS {name} bytes={path.stat().st_size}"
        )

    else:

        if name in {
            "midia.py",
            "video.py",
            "v6.py",
            "gerar_short.sh",
        }:

            critical(
                f"ESSENTIAL_FILE_MISSING {name}"
            )

        else:

            warning(
                f"OPTIONAL_OR_FEATURE_FILE_MISSING {name}"
            )


# ============================================================
# 2. ALL PYTHON SYNTAX
# ============================================================

section(
    "2. ALL PYTHON SYNTAX"
)

python_files = sorted(
    p
    for p in ROOT.glob("*.py")
    if p.is_file()
)

syntax_fail = 0


for path in python_files:

    try:

        ast.parse(
            read(path),
            filename=str(path),
        )

    except SyntaxError as exc:

        syntax_fail += 1

        critical(
            f"PYTHON_SYNTAX {path.name} "
            f"line={exc.lineno} "
            f"{exc.msg}"
        )


out(
    f"PYTHON_FILES_SCANNED={len(python_files)}"
)

out(
    f"PYTHON_SYNTAX_FAILURES={syntax_fail}"
)


if syntax_fail == 0:

    good(
        "ALL_TOPLEVEL_PYTHON_SYNTAX"
    )


# ============================================================
# 3. ALL SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)

shell_files = sorted(
    p
    for p in ROOT.glob("*.sh")
    if p.is_file()
)

shell_fail = 0


for path in shell_files:

    try:

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
            timeout=20,
        )

    except Exception as exc:

        shell_fail += 1

        warning(
            f"SHELL_CHECK_EXCEPTION {path.name}: {exc}"
        )

        continue


    if result.returncode != 0:

        shell_fail += 1

        critical(
            f"SHELL_SYNTAX {path.name}: "
            f"{result.stderr.strip()[:500]}"
        )


out(
    f"SHELL_FILES_SCANNED={len(shell_files)}"
)

out(
    f"SHELL_SYNTAX_FAILURES={shell_fail}"
)


if shell_fail == 0:

    good(
        "ALL_TOPLEVEL_SHELL_SYNTAX"
    )


# ============================================================
# 4. CORE HASHES
# ============================================================

section(
    "4. CORE HASHES"
)


for name in [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
]:

    path = ROOT / name

    if not path.is_file():
        continue

    digest = sha256(path)

    out(
        f"HASH {name}={digest}"
    )


    expected = KNOWN_CORE_HASHES.get(
        name
    )

    if expected:

        if digest == expected:

            good(
                f"KNOWN_CORE_HASH_MATCH {name}"
            )

        else:

            warning(
                f"KNOWN_CORE_HASH_CHANGED {name}"
            )


# ============================================================
# 5. DUPLICATE TOP-LEVEL FUNCTIONS
# ============================================================

section(
    "5. DUPLICATE TOP-LEVEL FUNCTIONS"
)


for filename in [
    "visual_selection_engine_v4.py",
    "midia.py",
    "media_diversity_guard_v1.py",
]:

    path = ROOT / filename

    if not path.is_file():
        continue

    tree = parse(path)

    if tree is None:
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

            defs[node.name].append(
                (
                    node.lineno,
                    getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                )
            )


    duplicates = {
        name: values
        for name, values in defs.items()
        if len(values) > 1
    }


    out()
    out(
        f"FILE={filename}"
    )

    out(
        f"TOP_LEVEL_DEFINITIONS={len(defs)}"
    )

    out(
        f"DUPLICATES={len(duplicates)}"
    )


    if not duplicates:

        good(
            f"NO_TOPLEVEL_DUPLICATES {filename}"
        )

    else:

        for name, values in sorted(
            duplicates.items()
        ):

            warning(
                f"DUPLICATE_DEFINITION "
                f"{filename}:{name} "
                f"{values}"
            )


# ============================================================
# 6. TRUE GLOBAL SYMBOL AUDIT - VSE4
# ============================================================

section(
    "6. VSE4 GLOBAL SYMBOL AUDIT"
)

vse = ROOT / "visual_selection_engine_v4.py"


if vse.is_file():

    import symtable

    source = read(vse)

    try:

        table = symtable.symtable(
            source,
            str(vse),
            "exec",
        )

    except Exception as exc:

        critical(
            f"VSE4_SYMTABLE_FAILED {exc}"
        )

    else:

        module_defined = set()

        for symbol in table.get_symbols():

            if (
                symbol.is_assigned()
                or symbol.is_imported()
                or symbol.is_namespace()
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


        out(
            "TRUE_UNRESOLVED_GLOBALS="
            + (
                ",".join(
                    sorted(unresolved)
                )
                if unresolved
                else
                "NONE"
            )
        )


        if unresolved:

            critical(
                "VSE4_UNRESOLVED_GLOBALS "
                + ",".join(
                    sorted(unresolved)
                )
            )

        else:

            good(
                "VSE4_GLOBALS_RESOLVED"
            )


# ============================================================
# 7. REQUIRED VSE4 SYMBOLS
# ============================================================

section(
    "7. VSE4 REQUIRED DEFINITIONS"
)


if vse.is_file():

    tree = parse(vse)

    names = set()


    if tree:

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

            elif isinstance(
                node,
                ast.Assign,
            ):

                for target in node.targets:

                    if isinstance(
                        target,
                        ast.Name,
                    ):

                        names.add(
                            target.id
                        )


    required = {
        "CONCEPTS",
        "GEO_GROUPS",
        "GENERIC_LIFESTYLE",
        "MEDICINE_TERMS",
        "candidate_text",
        "tokens",
        "geo_hits",
        "concept_hits",
        "objget",
        "provider",
        "source_group",
        "media_type",
        "candidate_key",
        "base_score",
        "must_tier",
        "resolution_bonus",
        "score_candidate",
        "self_test",
    }


    missing = sorted(
        required - names
    )


    out(
        "VSE4_REQUIRED_MISSING="
        + (
            ",".join(missing)
            if missing
            else
            "NONE"
        )
    )


    if missing:

        critical(
            "VSE4_REQUIRED_DEFINITIONS_MISSING "
            + ",".join(missing)
        )

    else:

        good(
            "VSE4_REQUIRED_DEFINITIONS"
        )


# ============================================================
# 8. VSE4 SELF-TEST
# ============================================================

section(
    "8. VSE4 SELF-TEST"
)


if vse.is_file():

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(vse),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            env={
                **os.environ,
                "SAP_VSE_V4_SELFTEST": "1",
            },
        )

        out(
            f"VSE4_SELF_TEST_STATUS={result.returncode}"
        )

        if result.stdout.strip():

            out(
                result.stdout.strip()[-3000:]
            )


        if result.stderr.strip():

            out(
                "VSE4_STDERR:"
            )

            out(
                result.stderr.strip()[-3000:]
            )


        if result.returncode == 0:

            good(
                "VSE4_SELF_TEST"
            )

        else:

            critical(
                "VSE4_SELF_TEST_FAILED"
            )


    except subprocess.TimeoutExpired:

        critical(
            "VSE4_SELF_TEST_TIMEOUT"
        )

    except Exception as exc:

        critical(
            f"VSE4_SELF_TEST_EXCEPTION {exc}"
        )


# ============================================================
# 9. VSE4 HARD-MISMATCH TEST
# ============================================================

section(
    "9. VSE4 GEO HARD-MISMATCH"
)


if vse.is_file():

    test_code = r'''
import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="master_audit_v4",
)

score = ns["score_candidate"]

scene = (
    "Investigação em apartamento "
    "na cidade de São Paulo"
)

wrong = {
    "provider": "Pixabay",
    "tipo": "foto",
    "title": "Empire State Building New York",
    "must": "2/2",
    "score": 220,
    "width": 1920,
    "height": 1080,
}

correct = {
    "provider": "Wikimedia",
    "tipo": "foto",
    "title": "Apartment building Sao Paulo Brazil",
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

a = score(
    wrong,
    scene,
    state,
)

b = score(
    correct,
    scene,
    state,
)

print(
    "WRONG_HARD_MISMATCH=",
    a.get("hard_mismatch"),
)

print(
    "WRONG_EFFECTIVE=",
    a.get("effective"),
)

print(
    "CORRECT_HARD_MISMATCH=",
    b.get("hard_mismatch"),
)

print(
    "CORRECT_EFFECTIVE=",
    b.get("effective"),
)

assert (
    a.get("hard_mismatch")
    is True
)

assert (
    b.get("hard_mismatch")
    is False
)

assert (
    float(
        b.get(
            "effective",
            -10**9,
        )
    )
    >
    float(
        a.get(
            "effective",
            10**9,
        )
    )
)

print(
    "HARD_MISMATCH_TEST=PASS"
)
'''

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                test_code,
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

        out(
            result.stdout.strip()
        )

        if result.returncode == 0:

            good(
                "VSE4_GEO_HARD_MISMATCH"
            )

        else:

            critical(
                "VSE4_GEO_HARD_MISMATCH_FAILED"
            )

            out(
                result.stderr.strip()[-2000:]
            )


    except Exception as exc:

        critical(
            f"VSE4_HARD_MISMATCH_EXCEPTION {exc}"
        )


# ============================================================
# 10. MIDIA INTEGRATION
# ============================================================

section(
    "10. MIDIA ↔ VISUAL ENGINE INTEGRATION"
)

midia = ROOT / "midia.py"


if midia.is_file():

    text = read(midia)


    signals = {
        "VSE4_IMPORT":
            (
                "visual_selection_engine_v4"
                in text
            ),

        "VSE3_IMPORT":
            (
                "visual_selection_final_gate_v3"
                in text
            ),

        "DIVERSITY_GUARD":
            (
                "media_diversity_guard_v1"
                in text
            ),

        "PROVENANCE":
            (
                "media_provenance_capture_v1"
                in text
            ),

        "MUST_RESCUE":
            (
                "visual_must_rescue_v1"
                in text
                or
                "MUST_RESCUE"
                in text
            ),

        "COMMIT_LOCK":
            (
                "visual_scene_commit_lock_v1"
                in text
                or
                "SCENE_COMMIT_LOCK"
                in text
            ),
    }


    for name, present in signals.items():

        out(
            f"{name}="
            f"{'YES' if present else 'NO'}"
        )


    if signals[
        "VSE4_IMPORT"
    ]:

        good(
            "MIDIA_HAS_VSE4_REFERENCE"
        )

    else:

        warning(
            "MIDIA_VSE4_REFERENCE_NOT_FOUND"
        )


    if signals[
        "PROVENANCE"
    ]:

        good(
            "MIDIA_PROVENANCE_PRESENT"
        )

    else:

        warning(
            "MIDIA_PROVENANCE_REFERENCE_NOT_FOUND"
        )


# ============================================================
# 11. MEDIA PROVIDER ACQUISITION
# ============================================================

section(
    "11. PROVIDER ACQUISITION"
)


if midia.is_file():

    tree = parse(
        midia
    )

    defs = {}

    if tree:

        for node in tree.body:

            if isinstance(
                node,
                ast.FunctionDef,
            ):

                defs[
                    node.name
                ] = node


    expected_provider_functions = [
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
        "buscar_todos_candidatos",
    ]


    for name in expected_provider_functions:

        if name in defs:

            good(
                f"PROVIDER_FUNCTION {name}"
            )

        else:

            warning(
                f"PROVIDER_FUNCTION_MISSING {name}"
            )


    finder = defs.get(
        "buscar_todos_candidatos"
    )


    if finder:

        calls = []


        for node in ast.walk(
            finder
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


        for provider_name in [
            "pexels_video",
            "pexels_foto",
            "pixabay_video",
            "pixabay_foto",
            "coverr_video",
        ]:

            active = any(
                call.endswith(
                    provider_name
                )
                for call in calls
            )

            out(
                f"FINDER_CALL_{provider_name}="
                f"{'YES' if active else 'NO'}"
            )


            if active:

                good(
                    f"FINDER_PROVIDER_ACTIVE {provider_name}"
                )

            else:

                warning(
                    f"FINDER_PROVIDER_NOT_CALLED {provider_name}"
                )


# ============================================================
# 12. PROVIDER CONFIG KEYS
# ============================================================

section(
    "12. PROVIDER CONFIGURATION"
)

config_paths = [
    ROOT / "config.env",
    ROOT / ".env",
]


config_text = "\n".join(
    read(p)
    for p in config_paths
    if p.is_file()
)


for provider_name, patterns in {

    "PEXELS": [
        "PEXELS",
    ],

    "PIXABAY": [
        "PIXABAY",
    ],

    "COVERR": [
        "COVERR",
    ],

}.items():

    found = any(
        pattern in config_text.upper()
        for pattern in patterns
    )


    out(
        f"{provider_name}_CONFIG_REFERENCE="
        f"{'YES' if found else 'NO'}"
    )


    if not found:

        warning(
            f"{provider_name}_CONFIG_NOT_VISIBLE"
        )


# ============================================================
# 13. SCENE COMMIT / MULTI-DOWNLOAD RISK
# ============================================================

section(
    "13. SCENE COMMIT / MULTI-DOWNLOAD"
)


if midia.is_file():

    text = read(
        midia
    )


    download_count = text.count(
        "baixar_candidato_5_2("
    )


    out(
        f"BAIXAR_CANDIDATO_CALL_TEXT_COUNT={download_count}"
    )


    if (
        "SCENE_COMMIT_LOCK"
        in text
        or
        "visual_scene_commit_lock"
        in text
    ):

        good(
            "SCENE_COMMIT_LOCK_REFERENCE"
        )

    else:

        warning(
            "SCENE_COMMIT_LOCK_NOT_VISIBLE_IN_MIDIA"
        )


    failover_occurrences = len(
        re.findall(
            r"FAILOVER",
            text,
            re.IGNORECASE,
        )
    )


    out(
        f"FAILOVER_REFERENCES={failover_occurrences}"
    )


# ============================================================
# 14. EXISTING MEDIA SET
# ============================================================

section(
    "14. EXISTING MEDIA SET"
)

media_dir = (
    ROOT
    / "imagens"
    / f"short_{SID}"
)


if media_dir.is_dir():

    total = 0
    invalid = 0


    for n in range(
        1,
        13,
    ):

        candidates = list(
            media_dir.glob(
                f"scene_{n:02d}.*"
            )
        )

        media = [
            p
            for p in candidates
            if p.suffix.lower()
            in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".mp4",
                ".webm",
                ".mov",
            }
        ]


        total += len(media)


        out(
            f"SCENE_{n:02d}_COUNT={len(media)}"
        )


        for path in media:

            out(
                f"  {path.name} "
                f"bytes={path.stat().st_size} "
                f"sha256={sha256(path)}"
            )


        if len(media) != 1:

            invalid += 1

            critical(
                f"SCENE_MEDIA_CARDINALITY "
                f"scene={n:02d} count={len(media)}"
            )


    out(
        f"MEDIA_TOTAL={total}"
    )

    out(
        f"INVALID_SCENES={invalid}"
    )


    if total == 12 and invalid == 0:

        good(
            "MEDIA_12_OF_12_EXACT"
        )


else:

    warning(
        f"MEDIA_DIR_NOT_FOUND {media_dir}"
    )


# ============================================================
# 15. MEDIA FINGERPRINT
# ============================================================

section(
    "15. MEDIA FINGERPRINT"
)


if media_dir.is_dir():

    entries = []


    for path in sorted(
        media_dir.glob(
            "scene_*.*"
        )
    ):

        if not path.is_file():
            continue

        entries.append(
            (
                path.name,
                sha256(path),
            )
        )


    payload = json.dumps(
        entries,
        ensure_ascii=False,
        separators=(
            ",",
            ":",
        ),
    )


    fingerprint = hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()


    out(
        f"MEDIA_FINGERPRINT_AUDIT={fingerprint}"
    )


# ============================================================
# 16. RENDER INPUT SAFETY
# ============================================================

section(
    "16. RENDER INPUT SAFETY"
)

ass = (
    ROOT
    / "videos"
    / f"short_{SID}.ass"
)

audio = (
    ROOT
    / "audios"
    / f"short_{SID}.mp3"
)

video_base = (
    ROOT
    / "temp"
    / SID
    / "video_sem_audio.mp4"
)

final_video = (
    ROOT
    / "videos"
    / f"short_v6_{SID}.mp4"
)


for label, path in [
    (
        "ASS",
        ass,
    ),
    (
        "AUDIO",
        audio,
    ),
    (
        "VIDEO_BASE",
        video_base,
    ),
    (
        "FINAL_VIDEO",
        final_video,
    ),
]:

    if (
        path.is_file()
        and path.stat().st_size > 0
    ):

        good(
            f"{label}_EXISTS "
            f"bytes={path.stat().st_size}"
        )

    else:

        warning(
            f"{label}_MISSING {path.relative_to(ROOT)}"
        )


# ============================================================
# 17. FRESH RENDER GUARD SAFETY
# ============================================================

section(
    "17. FRESH RENDER GUARD"
)

guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    text = read(
        guard
    )


    if ".ass" in text:

        info(
            "FRESH_GUARD_CONTAINS_ASS_REFERENCE"
        )


    protected = (
        "PROTECTED_SUFFIXES"
        in text
        and
        '".ass"'
        in text
    )


    if protected:

        good(
            "FRESH_GUARD_ASS_PROTECTED"
        )

    else:

        critical(
            "FRESH_GUARD_ASS_PROTECTION_NOT_PROVEN"
        )


    if (
        "rglob"
        in text
        and
        "short_id"
        in text.lower()
    ):

        warning(
            "FRESH_GUARD_RECURSIVE_SCAN_PRESENT"
        )


# ============================================================
# 18. SHORT_ID RESOLUTION
# ============================================================

section(
    "18. SHORT_ID RESOLUTION"
)


for filename in [
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "midia.py",
]:

    path = ROOT / filename

    if not path.is_file():
        continue

    text = read(
        path
    )


    env_first = bool(
        re.search(
            r'os\.getenv\s*\(\s*["\']SHORT_ID',
            text,
        )
    )


    out(
        f"{filename}_SHORT_ID_ENV="
        f"{'YES' if env_first else 'NO'}"
    )


    if env_first:

        good(
            f"SHORT_ID_ENV_SUPPORTED {filename}"
        )

    else:

        warning(
            f"SHORT_ID_ENV_NOT_FOUND {filename}"
        )


# ============================================================
# 19. SUSPICIOUS PYTHON PATTERNS
# ============================================================

section(
    "19. SUSPICIOUS PYTHON PATTERNS"
)

patterns = {

    "BARE_EXCEPT":
        re.compile(
            r"^\s*except\s*:\s*$",
            re.MULTILINE,
        ),

    "EXCEPT_EXCEPTION_PASS":
        re.compile(
            r"except\s+Exception(?:\s+as\s+\w+)?\s*:\s*(?:\n\s*)?pass\b",
            re.MULTILINE,
        ),

    "EVAL":
        re.compile(
            r"\beval\s*\("
        ),

    "EXEC":
        re.compile(
            r"\bexec\s*\("
        ),

    "SHELL_TRUE":
        re.compile(
            r"shell\s*=\s*True"
        ),

    "OS_SYSTEM":
        re.compile(
            r"\bos\.system\s*\("
        ),
}


for path in python_files:

    text = read(
        path
    )


    for label, pattern in patterns.items():

        matches = list(
            pattern.finditer(
                text
            )
        )


        if not matches:
            continue


        if label in {
            "EVAL",
            "SHELL_TRUE",
            "OS_SYSTEM",
        }:

            warning(
                f"{label} {path.name} count={len(matches)}"
            )


# ============================================================
# 20. HARDCODED /TMP
# ============================================================

section(
    "20. TEMP PATH SAFETY"
)

tmp_refs = []


for path in python_files + shell_files:

    text = read(
        path
    )

    if "/tmp/" in text:

        tmp_refs.append(
            path.name
        )


if tmp_refs:

    warning(
        "HARDCODED_TMP_REFERENCES "
        + ",".join(
            sorted(
                set(tmp_refs)
            )
        )
    )

else:

    good(
        "NO_HARDCODED_TMP_IN_TOPLEVEL_FILES"
    )


# ============================================================
# 21. NETWORK CALL SURFACE
# ============================================================

section(
    "21. NETWORK CALL SURFACE"
)

network_files = []


for path in python_files:

    text = read(
        path
    )


    if re.search(
        r"\b(requests|httpx|urllib\.request|aiohttp)\b",
        text,
    ):

        network_files.append(
            path.name
        )


out(
    "NETWORK_CAPABLE_FILES="
    +
    (
        ",".join(
            network_files
        )
        if network_files
        else
        "NONE"
    )
)


info(
    "NETWORK_CALLS_NOT_EXECUTED"
)


# ============================================================
# 22. SUBPROCESS / FFMPEG SURFACE
# ============================================================

section(
    "22. RENDER EXECUTION SURFACE"
)

for filename in [
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
]:

    path = ROOT / filename

    if not path.is_file():
        continue

    text = read(
        path
    )


    subprocess_count = len(
        re.findall(
            r"subprocess\.",
            text,
        )
    )

    ffmpeg_count = len(
        re.findall(
            r"ffmpeg",
            text,
            re.IGNORECASE,
        )
    )


    out(
        f"{filename} "
        f"SUBPROCESS={subprocess_count} "
        f"FFMPEG_REF={ffmpeg_count}"
    )


# ============================================================
# 23. PROVIDER MONOPOLY SIGNAL
# ============================================================

section(
    "23. PROVIDER MONOPOLY SIGNAL"
)

candidate_logs = [
    ROOT
    / "logs"
    / "producao"
    / f"vse31_real_media_{SID}.log",

    ROOT
    / "logs"
    / "producao"
    / f"vse3_real_media_{SID}.log",
]


provider_counter = Counter()


for log in candidate_logs:

    if not log.is_file():
        continue

    text = read(
        log
    )


    for provider_name in [
        "Pixabay",
        "Pexels",
        "Coverr",
        "Wikimedia",
    ]:

        provider_counter[
            provider_name
        ] += len(
            re.findall(
                rf"ESCOLHIDO:\s*{provider_name}",
                text,
                re.IGNORECASE,
            )
        )


out(
    "PROVIDER_SELECTION_COUNTS="
    + json.dumps(
        provider_counter,
        ensure_ascii=False,
    )
)


if provider_counter:

    total = sum(
        provider_counter.values()
    )

    top_name, top_count = (
        provider_counter.most_common(
            1
        )[0]
    )


    if (
        total >= 6
        and
        top_count / total >= 0.80
    ):

        warning(
            f"PROVIDER_MONOPOLY "
            f"{top_name}={top_count}/{total}"
        )


# ============================================================
# 24. MUST COVERAGE FROM LOGS
# ============================================================

section(
    "24. MUST COVERAGE HISTORY"
)

must_values = []


for log in candidate_logs:

    if not log.is_file():
        continue

    text = read(
        log
    )


    for match in re.finditer(
        r"MUST COVERAGE:\s*(\d+)\s*/\s*(\d+)",
        text,
        re.IGNORECASE,
    ):

        must_values.append(
            (
                int(
                    match.group(1)
                ),
                int(
                    match.group(2)
                ),
            )
        )


if must_values:

    weak = sum(
        1
        for a, b in must_values
        if b and a < b
    )


    out(
        f"MUST_HISTORY_TOTAL={len(must_values)}"
    )

    out(
        f"MUST_HISTORY_WEAK={weak}"
    )


    if weak:

        warning(
            f"HISTORICAL_WEAK_MUST_SCENES={weak}"
        )

    else:

        good(
            "HISTORICAL_MUST_FULL"
        )

else:

    info(
        "NO_MUST_HISTORY_FOUND"
    )


# ============================================================
# 25. BACKUP STATE
# ============================================================

section(
    "25. BACKUPS"
)

backup_dir = (
    ROOT
    / "backups"
)


if backup_dir.is_dir():

    backup_items = sorted(
        backup_dir.iterdir(),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


    out(
        f"BACKUP_ITEMS={len(backup_items)}"
    )


    for path in backup_items[:10]:

        out(
            f"RECENT_BACKUP={path.name}"
        )


    if backup_items:

        good(
            "BACKUPS_AVAILABLE"
        )

else:

    warning(
        "BACKUP_DIRECTORY_MISSING"
    )


# ============================================================
# 26. GIT CONFLICT MARKERS / ACCIDENTAL PATCH MARKERS
# ============================================================

section(
    "26. SOURCE CORRUPTION MARKERS"
)

conflict_files = []


for path in python_files + shell_files:

    text = read(
        path
    )


    if any(
        marker in text
        for marker in [
            "<<<<<<< HEAD",
            "=======",
            ">>>>>>> ",
        ]
    ):

        # ===== is common in comments/output, so only count
        # if actual git-style left/right markers exist.
        if (
            "<<<<<<< HEAD"
            in text
            or
            ">>>>>>> "
            in text
        ):

            conflict_files.append(
                path.name
            )


if conflict_files:

    critical(
        "GIT_CONFLICT_MARKERS "
        + ",".join(
            sorted(
                conflict_files
            )
        )
    )

else:

    good(
        "NO_GIT_CONFLICT_MARKERS"
    )


# ============================================================
# 27. LARGE FILE / PATCH ACCUMULATION
# ============================================================

section(
    "27. CODE GROWTH"
)


for filename in [
    "midia.py",
    "visual_selection_engine_v4.py",
    "video.py",
    "v6.py",
]:

    path = ROOT / filename

    if not path.is_file():
        continue

    lines = read(
        path
    ).count(
        "\n"
    ) + 1


    out(
        f"{filename}_LINES={lines}"
    )


    if (
        filename
        == "visual_selection_engine_v4.py"
        and
        lines > 3000
    ):

        warning(
            f"VSE4_LARGE_FILE lines={lines}; "
            "recommend consolidation after certification"
        )


# ============================================================
# 28. FINAL VIDEO HASH
# ============================================================

section(
    "28. FINAL VIDEO STATE"
)


if final_video.is_file():

    digest = sha256(
        final_video
    )


    out(
        f"FINAL_VIDEO_SHA256={digest}"
    )


    if digest == KNOWN_OLD_VIDEO_HASH:

        warning(
            "FINAL_VIDEO_EQUALS_KNOWN_OLD_RENDER"
        )

    else:

        good(
            "FINAL_VIDEO_DIFFERS_FROM_OLD_RENDER"
        )


# ============================================================
# 29. FINAL SCORE
# ============================================================

section(
    "29. MASTER AUDIT RESULT"
)

out(
    f"PASS_COUNT={len(PASS)}"
)

out(
    f"WARN_COUNT={len(WARN)}"
)

out(
    f"CRITICAL_COUNT={len(CRITICAL)}"
)


if CRITICAL:

    status = (
        "FAIL_CRITICAL"
    )

elif WARN:

    status = (
        "PASS_WITH_WARNINGS"
    )

else:

    status = (
        "PASS_CLEAN"
    )


out(
    f"MASTER_AUDIT_STATUS={status}"
)


out()
out(
    "----- CRITICAL -----"
)

if CRITICAL:

    for item in CRITICAL:

        out(
            "CRITICAL:",
            item,
        )

else:

    out(
        "NONE"
    )


out()
out(
    "----- WARNINGS -----"
)

if WARN:

    for item in WARN:

        out(
            "WARN:",
            item,
        )

else:

    out(
        "NONE"
    )


out()
out(
    "----- KEY PASSES -----"
)

for item in PASS[-30:]:

    out(
        "PASS:",
        item,
    )


out()
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

out(
    "AUDIT_COMPLETE=YES"
)


# Não usa sys.exit() para não fechar/interromper
# o fluxo do usuário no Termux.
