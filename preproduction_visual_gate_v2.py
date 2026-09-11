#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import os
import py_compile
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

FAILURES = []
WARNINGS = []
PASSES = []


def section(title):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def ok(name, detail=""):
    PASSES.append(name)

    if detail:
        print(f"{name}=PASS | {detail}")
    else:
        print(f"{name}=PASS")


def fail(name, detail=""):
    FAILURES.append(
        (name, detail)
    )

    if detail:
        print(f"{name}=FAIL | {detail}")
    else:
        print(f"{name}=FAIL")


def warn(name, detail=""):
    WARNINGS.append(
        (name, detail)
    )

    if detail:
        print(f"{name}=WARN | {detail}")
    else:
        print(f"{name}=WARN")


def sha256(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


# ============================================================
# 1. REQUIRED FILES
# ============================================================

section("1. REQUIRED FILES")

required = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
]

for name in required:

    path = ROOT / name

    if path.is_file():
        print(f"FOUND={name}")
    else:
        fail(
            "REQUIRED_FILE",
            name,
        )


if not any(
    item[0] == "REQUIRED_FILE"
    for item in FAILURES
):
    ok("REQUIRED_FILES")


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section("2. PYTHON COMPILE")

python_files = [
    "midia.py",
    "video.py",
    "v6.py",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
]

optional_python = [
    "visual_selection_bridge_v42.py",
    "visual_selection_final_gate_v3.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
]

compile_bad = []


for name in python_files + optional_python:

    path = ROOT / name

    if not path.is_file():

        if name in python_files:
            compile_bad.append(name)

        continue

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        print(
            f"COMPILE {name}=PASS"
        )

    except Exception as exc:

        print(
            f"COMPILE {name}=FAIL | "
            f"{type(exc).__name__}: {exc}"
        )

        compile_bad.append(name)


if compile_bad:
    fail(
        "PYTHON_COMPILE",
        ",".join(compile_bad),
    )
else:
    ok("PYTHON_COMPILE")


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section("3. SHELL SYNTAX")

shell = ROOT / "gerar_short.sh"

if shell.is_file():

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(shell),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode == 0:
        ok("SHELL_SYNTAX")
    else:
        fail(
            "SHELL_SYNTAX",
            result.stderr.strip(),
        )

else:
    fail("SHELL_SYNTAX", "gerar_short.sh ausente")


# ============================================================
# 4. VSE4 SELF TEST
# ============================================================

section("4. VSE4 RUNTIME SELF TEST")

vse = ROOT / "visual_selection_engine_v4.py"

if vse.is_file():

    result = subprocess.run(
        [
            sys.executable,
            str(vse),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(result.stdout.rstrip())

    if result.returncode == 0:
        ok("VSE4_SELF_TEST")
    else:
        fail(
            "VSE4_SELF_TEST",
            f"rc={result.returncode}",
        )

else:
    fail("VSE4_SELF_TEST", "arquivo ausente")


# ============================================================
# 5. VSE4 STATIC SYMBOLS
# ============================================================

section("5. VSE4 REQUIRED SYMBOLS")

symbols = [
    "candidate_text",
    "concept_hits",
    "geo_hits",
    "score_candidate",
    "tokens",
]

symbol_bad = []


if vse.is_file():

    source = vse.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(source)

    definitions = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }


    for symbol in symbols:

        exists = symbol in definitions

        print(
            f"VSE4_FUNCTION_{symbol}="
            f"{'YES' if exists else 'NO'}"
        )

        if not exists:
            symbol_bad.append(symbol)


if symbol_bad:
    fail(
        "VSE4_REQUIRED_SYMBOLS",
        ",".join(symbol_bad),
    )
else:
    ok("VSE4_REQUIRED_SYMBOLS")


# ============================================================
# 6. MIDIA PROVIDER ACQUISITION
# ============================================================

section("6. PROVIDER ACQUISITION")

midia = ROOT / "midia.py"

provider_functions = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
]

required_calls = [
    "buscar_wikimedia_fotos",
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
]


provider_fail = []


if midia.is_file():

    src = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(src)

    funcs = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }


    for name in provider_functions:

        exists = name in funcs

        print(
            f"PROVIDER_FUNCTION_{name}="
            f"{'YES' if exists else 'NO'}"
        )

        if not exists:
            provider_fail.append(
                f"function:{name}"
            )


    search_fn = funcs.get(
        "buscar_todos_candidatos"
    )


    calls = set()

    if search_fn:

        for node in ast.walk(
            search_fn
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


    for name in required_calls:

        exists = name in calls

        print(
            f"PROVIDER_CALL_{name}="
            f"{'YES' if exists else 'NO'}"
        )

        if not exists:
            provider_fail.append(
                f"call:{name}"
            )


if provider_fail:
    fail(
        "PROVIDER_COVERAGE",
        ",".join(provider_fail),
    )
else:
    ok("PROVIDER_COVERAGE")


# ============================================================
# 7. VSE ACTIVE-PATH INTEGRATION
# ============================================================

section("7. VSE4 ACTIVE-PATH INTEGRATION")

integration_patterns = {
    "IMPORT":
        r"visual_selection_engine_v4",

    "FINAL_GATE":
        r"VSE42 FINAL GATE|VSE4\.2.*FINAL",

    "PRIMARY_RANK":
        r"VSE42 PRIMARY RANK|rank_pool",

    "FINAL_POOL":
        r"VSE42 FINAL POOL|finalize_pool",

    "COMMIT":
        r"VSE42.*COMMIT|commit_candidate|note_commit",
}


integration_bad = []


if midia.is_file():

    src = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for name, pattern in integration_patterns.items():

        hit = bool(
            re.search(
                pattern,
                src,
                re.IGNORECASE,
            )
        )

        print(
            f"VSE42_INTEGRATION_{name}="
            f"{'YES' if hit else 'NO'}"
        )

        if not hit:
            integration_bad.append(name)


if integration_bad:

    fail(
        "VSE4_IN_MIDIA",
        ",".join(integration_bad),
    )

else:

    ok("VSE4_IN_MIDIA")


# ============================================================
# 8. DUPLICATE / LEGACY VISUAL HOOK AUDIT
# ============================================================

section("8. VISUAL HOOK COLLISION AUDIT")

if midia.is_file():

    src = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )

    patterns = {
        "VSE417_FINAL_GATE":
            r"SHORTAUTOPRO VSE4\.17 FINAL GATE",

        "VSE42_FINAL_GATE":
            r"SHORTAUTOPRO VSE42 FINAL GATE",

        "VSE42_PRIMARY_RANK":
            r"SHORTAUTOPRO VSE42 PRIMARY RANK",

        "VSE42_SCENE_COMMIT":
            r"SHORTAUTOPRO VSE42 SCENE COMMIT",

        "VSE421_FINALIZER":
            r"SHORTAUTOPRO VSE421 SCENE SUCCESS FINALIZER",
    }


    for name, pattern in patterns.items():

        count = len(
            re.findall(
                pattern,
                src,
                re.IGNORECASE,
            )
        )

        print(
            f"{name}_COUNT={count}"
        )


        if count > 1:

            warn(
                "DUPLICATE_VISUAL_HOOK",
                f"{name}:{count}",
            )


    # VSE4.17 + VSE4.2 coexistindo não significa necessariamente erro,
    # mas merece atenção porque dois final gates podem disputar escolha.
    has_417 = bool(
        re.search(
            patterns[
                "VSE417_FINAL_GATE"
            ],
            src,
            re.IGNORECASE,
        )
    )

    has_42 = bool(
        re.search(
            patterns[
                "VSE42_FINAL_GATE"
            ],
            src,
            re.IGNORECASE,
        )
    )


    if has_417 and has_42:

        warn(
            "MULTIPLE_FINAL_GATES",
            "VSE4.17 + VSE4.2 coexistem",
        )

    else:

        ok(
            "FINAL_GATE_COLLISION_CHECK"
        )


# ============================================================
# 9. FRESH RENDER GUARD SYNTHETIC TEST
# ============================================================

section("9. FRESH RENDER GUARD")

guard_path = ROOT / "fresh_render_guard_v1.py"

guard_fail = []


if guard_path.is_file():

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "fresh_guard_test",
        guard_path,
    )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )


    sid = (
        "AUDIT_GUARD_"
        + str(os.getpid())
        + "_"
        + str(int(time.time()))
    )


    temp_dir = ROOT / "temp" / sid
    videos_dir = ROOT / "videos"

    temp_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    videos_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    protected_ass = (
        videos_dir
        / f"short_{sid}.ass"
    )

    protected_audio = (
        temp_dir
        / "test.mp3"
    )

    protected_image = (
        temp_dir
        / "scene_01.jpg"
    )

    disposable_base = (
        temp_dir
        / "video_sem_audio.mp4"
    )

    disposable_scene = (
        temp_dir
        / "v63_cena_00.mp4"
    )

    disposable_final = (
        videos_dir
        / f"short_v6_{sid}.mp4"
    )


    for path in (
        protected_ass,
        protected_audio,
        protected_image,
        disposable_base,
        disposable_scene,
        disposable_final,
    ):

        path.write_bytes(
            b"SHORTAUTOPRO_AUDIT"
        )


    try:

        removed = module.clean(
            sid
        )

        print(
            f"GUARD_REMOVED_COUNT={len(removed)}"
        )


        checks = {

            "PROTECTED_ASS":
                protected_ass.exists(),

            "PROTECTED_AUDIO":
                protected_audio.exists(),

            "PROTECTED_IMAGE":
                protected_image.exists(),

            "DISPOSABLE_BASE":
                not disposable_base.exists(),

            "DISPOSABLE_SCENE":
                not disposable_scene.exists(),

            "DISPOSABLE_FINAL":
                not disposable_final.exists(),
        }


        for name, passed in checks.items():

            print(
                f"{name}="
                f"{'PASS' if passed else 'FAIL'}"
            )

            if not passed:
                guard_fail.append(name)


    except Exception as exc:

        guard_fail.append(
            type(exc).__name__
        )

        print(
            "GUARD_EXCEPTION="
            f"{type(exc).__name__}: {exc}"
        )


    finally:

        try:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )
        except Exception:
            pass

        for path in (
            protected_ass,
            disposable_final,
        ):

            try:
                path.unlink()
            except FileNotFoundError:
                pass


if guard_fail:
    fail(
        "FRESH_GUARD",
        ",".join(guard_fail),
    )
else:
    ok("FRESH_GUARD")


# ============================================================
# 10. REAL MEDIA DISCOVERY
# ============================================================

section("10. REAL MEDIA DISCOVERY")

images_root = ROOT / "imagens"

explicit_sid = os.environ.get(
    "SHORT_ID",
    "",
).strip()


media_dirs = []


if images_root.is_dir():

    for path in images_root.glob(
        "short_*"
    ):

        if path.is_dir():
            media_dirs.append(
                path
            )


media_dirs.sort(
    key=lambda p: p.stat().st_mtime,
    reverse=True,
)


selected = None
selection_mode = None


if explicit_sid:

    candidate = (
        images_root
        / f"short_{explicit_sid}"
    )

    selection_mode = "EXPLICIT_SHORT_ID"

    if candidate.is_dir():
        selected = candidate

    else:
        fail(
            "REAL_MEDIA_STRUCTURE",
            f"SHORT_ID explícito não encontrado: {explicit_sid}",
        )


else:

    # Primeiro diretório recente que realmente possui scene_*.
    for path in media_dirs:

        if any(
            path.glob(
                "scene_*"
            )
        ):
            selected = path
            selection_mode = "LATEST_WITH_SCENES"
            break


if selected is None and not explicit_sid:

    print(
        "REAL_MEDIA_SET=NONE"
    )

    print(
        "REAL_MEDIA_STRUCTURE=SKIP_NO_MEDIA"
    )

    print(
        "REAL_MEDIA_REASON="
        "nenhum conjunto scene_* disponível; "
        "isto não é falha da fundação"
    )

else:

    if selected is not None:

        print(
            f"REAL_MEDIA_SELECTION_MODE={selection_mode}"
        )

        print(
            f"REAL_MEDIA_DIR={selected}"
        )


        allowed_suffixes = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
            ".mkv",
        }


        total = 0
        bad = []
        duplicates = []


        for number in range(
            1,
            13,
        ):

            prefix = (
                f"scene_{number:02d}"
            )

            matches = [
                p
                for p in selected.glob(
                    prefix + ".*"
                )
                if (
                    p.is_file()
                    and
                    p.suffix.casefold()
                    in allowed_suffixes
                )
            ]


            count = len(matches)

            total += count


            print(
                f"REAL_SCENE_{number:02d}_COUNT={count}"
            )


            for path in matches:

                print(
                    "  "
                    f"{path.name} "
                    f"bytes={path.stat().st_size} "
                    f"sha256={sha256(path)}"
                )


            if count != 1:
                bad.append(number)

            if count > 1:
                duplicates.append(
                    number
                )


        if total == 12 and not bad:

            ok(
                "REAL_MEDIA_STRUCTURE",
                f"total={total}",
            )

        else:

            fail(
                "REAL_MEDIA_STRUCTURE",
                f"total={total} bad={bad}",
            )


        if duplicates:

            fail(
                "SCENE_SIBLING_DUPLICATES",
                str(duplicates),
            )

        else:

            ok(
                "SCENE_SIBLING_DUPLICATES"
            )


# ============================================================
# 11. CURRENT MEDIA SETS
# ============================================================

section("11. MEDIA SET INVENTORY")

print(
    f"MEDIA_DIRECTORY_COUNT={len(media_dirs)}"
)


for path in media_dirs[:15]:

    scene_count = len(
        [
            p
            for p in path.glob("scene_*")
            if p.is_file()
        ]
    )

    print(
        f"MEDIA_SET={path.name} "
        f"scene_files={scene_count} "
        f"mtime={int(path.stat().st_mtime)}"
    )


# ============================================================
# 12. CORE HASHES
# ============================================================

section("12. CORE HASHES")

hash_files = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
]


for name in hash_files:

    path = ROOT / name

    if path.is_file():

        print(
            f"SHA256 {name}="
            f"{sha256(path)}"
        )


# ============================================================
# 13. FINAL DECISION
# ============================================================

section("13. FINAL DECISION")


hard_failure_names = {
    name
    for name, detail
    in FAILURES
}


foundation_checks = {
    "REQUIRED_FILES",
    "PYTHON_COMPILE",
    "SHELL_SYNTAX",
    "VSE4_SELF_TEST",
    "VSE4_REQUIRED_SYMBOLS",
    "PROVIDER_COVERAGE",
    "VSE4_IN_MIDIA",
    "FRESH_GUARD",
}


foundation_pass = all(
    check in PASSES
    for check in foundation_checks
)


print(
    "FOUNDATION_CHECKS_REQUIRED="
    +
    ",".join(
        sorted(
            foundation_checks
        )
    )
)


for check in sorted(
    foundation_checks
):

    print(
        f"FOUNDATION_{check}="
        f"{'PASS' if check in PASSES else 'FAIL'}"
    )


print()


if foundation_pass:

    print(
        "VSE42_PREPRODUCTION_FOUNDATION=PASS"
    )

else:

    print(
        "VSE42_PREPRODUCTION_FOUNDATION=FAIL"
    )


media_failed = (
    "REAL_MEDIA_STRUCTURE"
    in hard_failure_names
)


if foundation_pass and not media_failed:

    print(
        "READY_FOR_ACTIVE_PATH_CANARY=YES"
    )

    print(
        "NEXT_STAGE=ACTIVE_PATH_CANARY"
    )

else:

    print(
        "READY_FOR_ACTIVE_PATH_CANARY=NO"
    )

    print(
        "NEXT_STAGE=FIX_DETECTED_FAILURES"
    )


print()
print(
    f"HARD_FAILURE_COUNT={len(FAILURES)}"
)

print(
    f"WARNING_COUNT={len(WARNINGS)}"
)


if FAILURES:

    print()
    print("===== HARD FAILURES =====")

    for name, detail in FAILURES:

        print(
            f"FAIL={name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )


if WARNINGS:

    print()
    print("===== WARNINGS =====")

    for name, detail in WARNINGS:

        print(
            f"WARN={name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )


print()
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
    "REAL_MEDIA_MODIFIED=NO"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
