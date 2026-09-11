#!/usr/bin/env python3


# SHORTAUTOPRO RUNTIME SHORT_ID V1
#
# O ID do short deve vir da execução atual.
# Não manter IDs históricos fixos em runtime.

_SAP_RUNTIME_SHORT_ID = os.environ.get(
    "SHORT_ID",
    "",
).strip()


from pathlib import Path
from collections import Counter
import ast
import hashlib
import os
import py_compile
import re
import subprocess
import symtable
import builtins
import json


ROOT = Path.home() / "ShortAutoPro"
os.chdir(ROOT)

SHORT_ID = os.environ.get(
    "SHORT_ID",
    _SAP_RUNTIME_SHORT_ID,
).strip()

REPORT = {
    "pass": [],
    "warn": [],
    "fail": [],
}


def ok(msg):
    REPORT["pass"].append(msg)
    print(f"PASS | {msg}")


def warn(msg):
    REPORT["warn"].append(msg)
    print(f"WARN | {msg}")


def fail(msg):
    REPORT["fail"].append(msg)
    print(f"FAIL | {msg}")


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def section(title):

    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# ============================================================
# 1. PROJECT
# ============================================================

section("1. PROJECT / CORE FILES")

critical = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
]

for name in critical:

    path = ROOT / name

    if path.is_file():

        ok(f"CORE_FOUND {name}")

        try:
            print(
                f"HASH | {name} | "
                f"{sha256(path)}"
            )
        except Exception as exc:
            warn(
                f"HASH_ERROR {name}: {exc}"
            )

    else:

        fail(f"CORE_MISSING {name}")


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section("2. PYTHON COMPILE - ACTIVE ROOT")

py_files = sorted(
    ROOT.glob("*.py")
)

compile_fail = []

for path in py_files:

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        compile_fail.append(
            (
                path.name,
                str(exc),
            )
        )

        fail(
            f"PY_COMPILE {path.name}: {exc}"
        )


print(
    f"PY_FILES_TESTED={len(py_files)}"
)

print(
    f"PY_COMPILE_FAILURES={len(compile_fail)}"
)

if not compile_fail:
    ok("ALL_ACTIVE_PYTHON_COMPILE")


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section("3. SHELL SYNTAX - ACTIVE ROOT")

sh_files = sorted(
    ROOT.glob("*.sh")
)

shell_fail = []

for path in sh_files:

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:

        shell_fail.append(
            path.name
        )

        fail(
            f"SHELL_SYNTAX {path.name}: "
            f"{result.stderr.strip()}"
        )


print(
    f"SHELL_FILES_TESTED={len(sh_files)}"
)

print(
    f"SHELL_FAILURES={len(shell_fail)}"
)

if not shell_fail:
    ok("ALL_ACTIVE_SHELL_SYNTAX")


# ============================================================
# 4. DUPLICATE TOP-LEVEL DEFINITIONS
# ============================================================

section("4. DUPLICATE FUNCTION / CLASS DEFINITIONS")

duplicate_total = 0

for path in py_files:

    try:

        src = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(src)

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
            names.append(node.name)

    counts = Counter(names)

    duplicates = {
        name: count
        for name, count in counts.items()
        if count > 1
    }

    if duplicates:

        duplicate_total += len(
            duplicates
        )

        warn(
            f"DUPLICATE_DEFS {path.name}: "
            f"{duplicates}"
        )


if duplicate_total == 0:
    ok("NO_DUPLICATE_TOPLEVEL_DEFINITIONS")

print(
    f"DUPLICATE_DEFINITION_GROUPS="
    f"{duplicate_total}"
)


# ============================================================
# 5. VSE4 REQUIRED DEFINITIONS
# ============================================================

section("5. VSE4 STRUCTURE")

vse = ROOT / "visual_selection_engine_v4.py"

required_vse = [
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
]

if vse.is_file():

    src = vse.read_text(
        encoding="utf-8",
        errors="replace",
    )

    try:

        tree = ast.parse(src)

        defs = {
            node.name
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            )
        }

        missing = [
            name
            for name in required_vse
            if name not in defs
        ]

        if missing:

            fail(
                "VSE4_MISSING_DEFINITIONS="
                + ",".join(missing)
            )

        else:

            ok(
                "VSE4_REQUIRED_DEFINITIONS"
            )

    except Exception as exc:

        fail(
            f"VSE4_AST_ERROR={exc}"
        )


# ============================================================
# 6. VSE4 GLOBALS
# ============================================================

section("6. VSE4 UNRESOLVED GLOBALS")

if vse.is_file():

    try:

        src = vse.read_text(
            encoding="utf-8",
            errors="replace",
        )

        table = symtable.symtable(
            src,
            str(vse),
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

        builtins_set = set(
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

                    if name in builtins_set:
                        continue

                    unresolved.add(name)

                walk(child)

        walk(table)

        if unresolved:

            fail(
                "VSE4_UNRESOLVED_GLOBALS="
                + ",".join(
                    sorted(unresolved)
                )
            )

        else:

            ok(
                "VSE4_UNRESOLVED_GLOBALS=NONE"
            )

    except Exception as exc:

        fail(
            f"VSE4_GLOBAL_AUDIT_ERROR={exc}"
        )


# ============================================================
# 7. VSE4 SELF TEST
# ============================================================

section("7. VSE4 RUNTIME SELF TEST")

if vse.is_file():

    result = subprocess.run(
        [
            "python",
            str(vse),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    print(
        f"VSE4_SELF_TEST_STATUS="
        f"{result.returncode}"
    )

    output = (
        result.stdout
        +
        "\n"
        +
        result.stderr
    ).strip()

    if output:

        print(
            "----- VSE4 SELF TEST TAIL -----"
        )

        print(
            "\n".join(
                output.splitlines()[-50:]
            )
        )

    if result.returncode == 0:

        ok("VSE4_RUNTIME_SELF_TEST")

    else:

        fail("VSE4_RUNTIME_SELF_TEST")


# ============================================================
# 8. LEGACY VSE REFERENCES
# ============================================================

section("8. LEGACY / MIXED VISUAL ENGINE REFERENCES")

needles = [
    "visual_selection_engine_v2",
    "visual_selection_final_gate_v3",
    "visual_scene_commit_lock_v1",
    "visual_must_rescue_v1",
    "SAP_VSE_V2",
    "SAP_VSE_V3",
    "VSE3_",
]

legacy_hits = []

for path in (
    list(ROOT.glob("*.py"))
    +
    list(ROOT.glob("*.sh"))
):

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        continue

    for needle in needles:

        if needle in text:

            legacy_hits.append(
                (
                    path.name,
                    needle,
                )
            )


for file_name, needle in legacy_hits:

    print(
        f"REFERENCE={file_name} | "
        f"{needle}"
    )


print(
    f"LEGACY_REFERENCE_COUNT="
    f"{len(legacy_hits)}"
)

if legacy_hits:

    warn(
        "LEGACY_VISUAL_REFERENCES_PRESENT"
    )

else:

    ok(
        "NO_LEGACY_VISUAL_REFERENCES"
    )


# ============================================================
# 9. MIDIA VISUAL HOOKS
# ============================================================

section("9. MIDIA.PY VISUAL ENGINE HOOKS")

midia = ROOT / "midia.py"

if midia.is_file():

    text = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )

    markers = [
        "visual_selection_engine_v4",
        "VSE4",
        "visual_selection_engine_v2",
        "VSE3",
        "SCENE_COMMIT_LOCK",
        "MUST_RESCUE",
        "media_diversity_guard",
        "media_provenance_capture",
    ]

    found = []

    for marker in markers:

        count = text.count(marker)

        if count:

            found.append(
                (
                    marker,
                    count,
                )
            )

            print(
                f"MIDIA_REFERENCE={marker} "
                f"COUNT={count}"
            )

    if found:

        ok(
            "MIDIA_VISUAL_HOOK_REFERENCES_FOUND"
        )

    else:

        warn(
            "MIDIA_NO_VISUAL_HOOK_REFERENCE_FOUND"
        )


# ============================================================
# 10. PROVIDER ACQUISITION
# ============================================================

section("10. PROVIDER ACQUISITION STRUCTURE")

provider_functions = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
]

if midia.is_file():

    try:

        tree = ast.parse(
            midia.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

        functions = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }

        for name in provider_functions:

            if name in functions:

                ok(
                    f"PROVIDER_FUNCTION {name}"
                )

            else:

                fail(
                    f"PROVIDER_FUNCTION_MISSING {name}"
                )


        buscar = functions.get(
            "buscar_todos_candidatos"
        )

        if buscar:

            calls = []

            for node in ast.walk(buscar):

                if isinstance(
                    node,
                    ast.Call,
                ):

                    try:
                        call_name = ast.unparse(
                            node.func
                        )
                    except Exception:
                        continue

                    calls.append(
                        call_name
                    )


            for wanted in [
                "pexels_video",
                "pexels_foto",
                "pixabay_video",
                "pixabay_foto",
                "coverr_video",
            ]:

                if any(
                    wanted in call
                    for call in calls
                ):

                    ok(
                        f"ACQUISITION_CALL {wanted}"
                    )

                else:

                    warn(
                        f"ACQUISITION_CALL_MISSING "
                        f"{wanted}"
                    )

    except Exception as exc:

        fail(
            f"PROVIDER_AST_ERROR={exc}"
        )


# ============================================================
# 11. CURRENT SHORT MEDIA
# ============================================================

section("11. CURRENT SHORT MEDIA INTEGRITY")

media_dir = (
    ROOT
    / "imagens"
    / f"short_{SHORT_ID}"
)

media_hashes = []

bad_scenes = []

for number in range(1, 13):

    stem = f"scene_{number:02d}"

    files = sorted(
        media_dir.glob(
            f"{stem}.*"
        )
    ) if media_dir.is_dir() else []

    print(
        f"{stem.upper()}_COUNT="
        f"{len(files)}"
    )

    if len(files) != 1:

        bad_scenes.append(
            (
                number,
                len(files),
            )
        )

    for path in files:

        try:

            digest = sha256(path)

            media_hashes.append(
                (
                    path.name,
                    digest,
                )
            )

            print(
                f"MEDIA={path.name} | "
                f"{path.stat().st_size} bytes | "
                f"{digest}"
            )

        except Exception as exc:

            fail(
                f"MEDIA_HASH_ERROR "
                f"{path.name}: {exc}"
            )


print(
    f"MEDIA_TOTAL="
    f"{len(media_hashes)}"
)

if (
    len(media_hashes) == 12
    and
    not bad_scenes
):

    ok(
        "MEDIA_12_OF_12_EXACTLY_ONE_PER_SCENE"
    )

else:

    fail(
        f"MEDIA_STRUCTURE_BAD={bad_scenes}"
    )


if media_hashes:

    combined = hashlib.sha256()

    for name, digest in media_hashes:

        combined.update(
            name.encode()
        )

        combined.update(
            digest.encode()
        )

    print(
        "MEDIA_FINGERPRINT="
        +
        combined.hexdigest()
    )


# ============================================================
# 12. DUPLICATE MEDIA CONTENT
# ============================================================

section("12. DUPLICATE MEDIA CONTENT")

digest_map = {}

for name, digest in media_hashes:

    digest_map.setdefault(
        digest,
        [],
    ).append(name)


duplicates = {
    digest: names
    for digest, names in digest_map.items()
    if len(names) > 1
}


if duplicates:

    for digest, names in duplicates.items():

        warn(
            "DUPLICATE_MEDIA_SHA "
            f"{digest} -> {names}"
        )

else:

    ok(
        "NO_EXACT_MEDIA_DUPLICATES"
    )


# ============================================================
# 13. RENDER CHAIN
# ============================================================

section("13. RENDER INPUT CHAIN")

render_inputs = [
    ROOT
    / "audios"
    / f"short_{SHORT_ID}.mp3",

    ROOT
    / "videos"
    / f"short_{SHORT_ID}.ass",

    ROOT
    / "temp"
    / SHORT_ID
    / "video_sem_audio.mp4",
]

for path in render_inputs:

    if (
        path.is_file()
        and
        path.stat().st_size > 0
    ):

        ok(
            f"RENDER_INPUT {path.relative_to(ROOT)} "
            f"{path.stat().st_size} bytes"
        )

    else:

        warn(
            f"RENDER_INPUT_MISSING "
            f"{path.relative_to(ROOT)}"
        )


final = (
    ROOT
    / "videos"
    / f"short_v6_{SHORT_ID}.mp4"
)

if final.is_file():

    ok(
        f"FINAL_VIDEO_EXISTS "
        f"{final.stat().st_size} bytes"
    )

    print(
        "FINAL_SHA256="
        +
        sha256(final)
    )

else:

    warn(
        "FINAL_VIDEO_NOT_PRESENT"
    )


# ============================================================
# 14. FRESH RENDER GUARD SAFETY
# ============================================================

section("14. FRESH RENDER GUARD")

guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)

if guard.is_file():

    text = guard.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if ".ass" in text:

        ok(
            "RENDER_GUARD_ASS_PROTECTION_REFERENCE"
        )

    else:

        warn(
            "RENDER_GUARD_ASS_PROTECTION_NOT_VISIBLE"
        )

    if "video_sem_audio.mp4" in text:

        ok(
            "RENDER_GUARD_TEMP_VIDEO_RULE"
        )

else:

    warn(
        "FRESH_RENDER_GUARD_MISSING"
    )


# ============================================================
# 15. HARDCODED CURRENT/OLD SHORT IDs
# ============================================================

section("15. HARDCODED SHORT-ID / DATE AUDIT")

date_pattern = re.compile(
    r"20\d{2}-\d{2}-\d{2}_\d{4}"
)

hardcoded = []

for path in py_files + sh_files:

    if path.name.startswith(
        "audit_geral_"
    ):
        continue

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        continue

    values = sorted(
        set(
            date_pattern.findall(text)
        )
    )

    if values:

        hardcoded.append(
            (
                path.name,
                values,
            )
        )


for name, values in hardcoded:

    warn(
        f"HARDCODED_SHORT_ID "
        f"{name}: {values}"
    )


if not hardcoded:

    ok(
        "NO_HARDCODED_TIMESTAMP_SHORT_IDS"
    )


# ============================================================
# 16. CONFIG KEY AUDIT - NO SECRET VALUES
# ============================================================

section("16. CONFIG KEYS")

for config_name in [
    "config.env",
    ".env",
]:

    path = ROOT / config_name

    if not path.is_file():
        continue

    keys = []

    for line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():

        line = line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key = line.split(
            "=",
            1,
        )[0].strip()

        if key:
            keys.append(key)

    print(
        f"{config_name}_KEY_COUNT="
        f"{len(keys)}"
    )

    for key in sorted(
        set(keys)
    ):
        print(
            f"CONFIG_KEY={key}"
        )

    ok(
        f"CONFIG_KEYS_READ {config_name}"
    )


# ============================================================
# 17. SUSPICIOUS BROAD DELETE PATTERNS
# ============================================================

section("17. DESTRUCTIVE PATTERN AUDIT")

danger_patterns = [
    "rm -rf /",
    "rm -rf $HOME",
    "shutil.rmtree(ROOT",
    "shutil.rmtree(BASE",
]

danger_hits = []

for path in py_files + sh_files:

    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        continue

    for needle in danger_patterns:

        if needle in text:

            danger_hits.append(
                (
                    path.name,
                    needle,
                )
            )


if danger_hits:

    for hit in danger_hits:

        fail(
            f"DANGEROUS_PATTERN "
            f"{hit[0]} | {hit[1]}"
        )

else:

    ok(
        "NO_OBVIOUS_BROAD_DELETE_PATTERN"
    )


# ============================================================
# 18. SUMMARY
# ============================================================

section("18. FINAL GENERAL AUDIT SUMMARY")

print(
    f"SHORT_ID={SHORT_ID}"
)

print(
    f"PASS_COUNT={len(REPORT['pass'])}"
)

print(
    f"WARN_COUNT={len(REPORT['warn'])}"
)

print(
    f"FAIL_COUNT={len(REPORT['fail'])}"
)


if REPORT["fail"]:

    status = "FAIL"

elif REPORT["warn"]:

    status = "WARN"

else:

    status = "PASS"


print(
    f"GENERAL_AUDIT_STATUS={status}"
)


print()
print("===== FAILURES =====")

if REPORT["fail"]:

    for item in REPORT["fail"]:
        print(f"FAIL={item}")

else:

    print("FAIL=NONE")


print()
print("===== WARNINGS =====")

if REPORT["warn"]:

    for item in REPORT["warn"]:
        print(f"WARN={item}")

else:

    print("WARN=NONE")


print()
print(
    "CORE_FILES_MODIFIED=NO"
)

print(
    "NETWORK_EXECUTED=NO"
)

print(
    "MEDIA_DOWNLOADED=NO"
)

print(
    "MIDIA_PY_EXECUTED=NO"
)

print(
    "VIDEO_RENDERED=NO"
)

print(
    "AUDIT_COMPLETE=YES"
)
