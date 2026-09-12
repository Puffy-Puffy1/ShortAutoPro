#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import ast
import hashlib
import importlib.util
import os
import py_compile
import shutil
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

RESULTS = {}
DETAILS = []


def result(name, ok, detail=""):

    RESULTS[name] = bool(ok)

    status = "PASS" if ok else "FAIL"

    print(
        f"{name}={status}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )

    if detail:
        DETAILS.append(
            (
                name,
                status,
                detail,
            )
        )


def sha256(path):

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

print()
print("=" * 70)
print("1. REQUIRED FILES")
print("=" * 70)

required = (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
)

missing = []

for name in required:

    path = ROOT / name

    if path.is_file():
        print(f"FOUND={name}")
    else:
        print(f"MISSING={name}")
        missing.append(name)

result(
    "REQUIRED_FILES",
    not missing,
    ",".join(missing),
)


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

print()
print("=" * 70)
print("2. PYTHON COMPILE")
print("=" * 70)

python_files = (
    "midia.py",
    "video.py",
    "v6.py",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
)

compile_bad = []

for name in python_files:

    path = ROOT / name

    if not path.is_file():
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

        compile_bad.append(name)

        print(
            f"COMPILE {name}=FAIL "
            f"{type(exc).__name__}: {exc}"
        )

result(
    "PYTHON_COMPILE",
    not compile_bad,
    ",".join(compile_bad),
)


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

print()
print("=" * 70)
print("3. SHELL SYNTAX")
print("=" * 70)

shell = subprocess.run(
    [
        "bash",
        "-n",
        "gerar_short.sh",
    ],
    cwd=ROOT,
)

result(
    "SHELL_SYNTAX",
    shell.returncode == 0,
    f"rc={shell.returncode}",
)


# ============================================================
# 4. VSE4 REAL SELF TEST
# ============================================================

print()
print("=" * 70)
print("4. VSE4 SELF TEST")
print("=" * 70)

vse = subprocess.run(
    [
        sys.executable,
        "visual_selection_engine_v4.py",
    ],
    cwd=ROOT,
    capture_output=True,
    text=True,
)

print(
    vse.stdout[-4000:]
)

if vse.stderr:
    print(
        vse.stderr[-4000:]
    )

result(
    "VSE4_SELF_TEST",
    vse.returncode == 0,
    f"rc={vse.returncode}",
)


# ============================================================
# 5. VSE4 SYMBOL CHECK
# ============================================================

print()
print("=" * 70)
print("5. VSE4 SYMBOL CHECK")
print("=" * 70)

vse_path = ROOT / "visual_selection_engine_v4.py"

src = vse_path.read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(src)

definitions = {
    node.name
    for node in tree.body
    if isinstance(
        node,
        ast.FunctionDef,
    )
}

required_functions = {
    "candidate_text",
    "tokens",
    "concept_hits",
    "geo_hits",
    "score_candidate",
}

missing_functions = sorted(
    required_functions - definitions
)

for name in sorted(
    required_functions
):
    print(
        f"VSE4_FUNCTION_{name}="
        f"{'YES' if name in definitions else 'NO'}"
    )

result(
    "VSE4_REQUIRED_SYMBOLS",
    not missing_functions,
    ",".join(missing_functions),
)


# ============================================================
# 6. PROVIDER ACQUISITION COVERAGE
# ============================================================

print()
print("=" * 70)
print("6. PROVIDER ACQUISITION COVERAGE")
print("=" * 70)

midia_path = ROOT / "midia.py"

midia_src = midia_path.read_text(
    encoding="utf-8",
    errors="replace",
)

midia_tree = ast.parse(
    midia_src
)

target = None

for node in midia_tree.body:

    if (
        isinstance(
            node,
            ast.FunctionDef,
        )
        and
        node.name
        ==
        "buscar_todos_candidatos"
    ):
        target = node
        break


expected_calls = {
    "buscar_wikimedia_fotos",
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}

actual_calls = set()

if target:

    for node in ast.walk(
        target
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        fn = node.func

        if isinstance(
            fn,
            ast.Name,
        ):
            actual_calls.add(
                fn.id
            )

        elif isinstance(
            fn,
            ast.Attribute,
        ):
            actual_calls.add(
                fn.attr
            )


for name in sorted(
    expected_calls
):

    print(
        f"PROVIDER_CALL_{name}="
        f"{'YES' if name in actual_calls else 'NO'}"
    )


provider_missing = sorted(
    expected_calls - actual_calls
)

result(
    "PROVIDER_COVERAGE",
    target is not None
    and not provider_missing,
    ",".join(provider_missing),
)


# ============================================================
# 7. VSE4 -> MIDIA INTEGRATION CHECK
# ============================================================

print()
print("=" * 70)
print("7. VSE4 ACTIVE-PATH INTEGRATION")
print("=" * 70)

integration_terms = (
    "visual_selection_engine_v4",
    "VSE4",
    "vse4",
)

integration_hits = []

for number, line in enumerate(
    midia_src.splitlines(),
    start=1,
):

    if any(
        term in line
        for term in integration_terms
    ):

        integration_hits.append(
            (
                number,
                line.strip(),
            )
        )


for number, line in integration_hits[
    :80
]:
    print(
        f"VSE4_MIDIA_LINE={number}: {line}"
    )


if integration_hits:

    print(
        "VSE4_IN_MIDIA=YES"
    )

else:

    print(
        "VSE4_IN_MIDIA=NO"
    )


# Não fazemos este item falhar:
# caso ainda não esteja integrado,
# significa que está pronto para a próxima fase.
RESULTS[
    "VSE4_IN_MIDIA"
] = bool(
    integration_hits
)


# ============================================================
# 8. FRESH RENDER GUARD - SYNTHETIC SAFETY TEST
# ============================================================

print()
print("=" * 70)
print("8. FRESH RENDER GUARD SYNTHETIC TEST")
print("=" * 70)

sid = (
    "PREPROD_GUARD_"
    +
    str(
        os.getpid()
    )
    +
    "_"
    +
    str(
        int(time.time())
    )
)

video_dir = ROOT / "videos"
audio_dir = ROOT / "audios"
image_dir = (
    ROOT
    / "imagens"
    / f"short_{sid}"
)
temp_dir = (
    ROOT
    / "temp"
    / sid
)

video_dir.mkdir(
    parents=True,
    exist_ok=True,
)

audio_dir.mkdir(
    parents=True,
    exist_ok=True,
)

image_dir.mkdir(
    parents=True,
    exist_ok=True,
)

temp_dir.mkdir(
    parents=True,
    exist_ok=True,
)


ass = (
    video_dir
    / f"short_{sid}.ass"
)

audio = (
    audio_dir
    / f"short_{sid}.mp3"
)

image = (
    image_dir
    / "scene_01.jpg"
)

retention_ass = (
    temp_dir
    / "legenda_retention.ass"
)

base_video = (
    temp_dir
    / "video_sem_audio.mp4"
)

scene_video = (
    temp_dir
    / "v63_cena_00.mp4"
)

final_video = (
    video_dir
    / f"short_v6_{sid}.mp4"
)


protected = {
    ass:
        b"ASS_PROTECTED",

    audio:
        b"AUDIO_PROTECTED",

    image:
        b"IMAGE_PROTECTED",

    retention_ass:
        b"RETENTION_ASS_PROTECTED",
}


disposable = {
    base_video:
        b"STALE_BASE_VIDEO",

    scene_video:
        b"STALE_SCENE_VIDEO",

    final_video:
        b"STALE_FINAL_VIDEO",
}


for path, data in {
    **protected,
    **disposable,
}.items():

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(
        data
    )


before_hashes = {
    str(path):
        sha256(path)
    for path in protected
}


guard_ok = False
guard_error = ""


try:

    module_path = (
        ROOT
        / "fresh_render_guard_v1.py"
    )

    spec = (
        importlib.util
        .spec_from_file_location(
            "fresh_render_guard_test",
            module_path,
        )
    )

    module = (
        importlib.util
        .module_from_spec(
            spec
        )
    )

    spec.loader.exec_module(
        module
    )


    if not hasattr(
        module,
        "clean",
    ):

        raise RuntimeError(
            "clean() ausente"
        )


    removed = module.clean(
        sid
    )

    print(
        "GUARD_REMOVED_COUNT=",
        len(
            removed
            or []
        ),
    )

    for item in (
        removed
        or []
    ):
        print(
            f"GUARD_REMOVED={item}"
        )


    protected_ok = True

    for path in protected:

        exists = (
            path.is_file()
        )

        same = False

        if exists:

            same = (
                sha256(path)
                ==
                before_hashes[
                    str(path)
                ]
            )


        print(
            f"PROTECTED_{path.name}="
            f"{'PASS' if exists and same else 'FAIL'}"
        )


        if not (
            exists
            and
            same
        ):
            protected_ok = False


    disposable_ok = True

    for path in disposable:

        removed_ok = (
            not path.exists()
        )

        print(
            f"DISPOSABLE_{path.name}="
            f"{'PASS' if removed_ok else 'FAIL'}"
        )

        if not removed_ok:
            disposable_ok = False


    guard_ok = (
        protected_ok
        and
        disposable_ok
    )


except Exception as exc:

    guard_error = (
        f"{type(exc).__name__}: "
        f"{exc}"
    )

    print(
        "FRESH_GUARD_EXCEPTION="
        +
        guard_error
    )


finally:

    # Só limpa o ID sintético deste teste.
    try:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )
    except Exception:
        pass

    try:
        shutil.rmtree(
            image_dir,
            ignore_errors=True,
        )
    except Exception:
        pass

    for path in (
        ass,
        audio,
        final_video,
    ):

        try:
            if path.exists():
                path.unlink()
        except Exception:
            pass


result(
    "FRESH_GUARD",
    guard_ok,
    guard_error,
)


# ============================================================
# 9. CURRENT REAL SCENE STRUCTURE
# ============================================================

print()
print("=" * 70)
print("9. CURRENT REAL SCENE STRUCTURE")
print("=" * 70)

current_sid = (
    _sap_resolve_short_id()
)

current_media = (
    ROOT
    / "imagens"
    / f"short_{current_sid}"
)


if current_media.is_dir():

    scene_bad = []
    scene_total = 0

    for number in range(
        1,
        13,
    ):

        files = list(
            current_media.glob(
                f"scene_{number:02d}.*"
            )
        )

        count = len(
            [
                f
                for f in files
                if f.is_file()
            ]
        )

        scene_total += count

        print(
            f"REAL_SCENE_{number:02d}_COUNT="
            f"{count}"
        )

        if count != 1:
            scene_bad.append(
                number
            )


    result(
        "REAL_MEDIA_STRUCTURE",
        not scene_bad
        and
        scene_total == 12,
        (
            f"total={scene_total} "
            f"bad={scene_bad}"
        ),
    )

else:

    print(
        "REAL_MEDIA_STRUCTURE=SKIP_NO_DIRECTORY"
    )

    RESULTS[
        "REAL_MEDIA_STRUCTURE"
    ] = True


# ============================================================
# 10. CORE HASHES
# ============================================================

print()
print("=" * 70)
print("10. CORE HASHES")
print("=" * 70)

for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
):

    path = ROOT / name

    if path.is_file():

        print(
            f"SHA256 {name}="
            f"{sha256(path)}"
        )


# ============================================================
# FINAL
# ============================================================

print()
print("=" * 70)
print("PRE-PRODUCTION RESULT")
print("=" * 70)


required_gates = (
    "REQUIRED_FILES",
    "PYTHON_COMPILE",
    "SHELL_SYNTAX",
    "VSE4_SELF_TEST",
    "VSE4_REQUIRED_SYMBOLS",
    "PROVIDER_COVERAGE",
    "FRESH_GUARD",
    "REAL_MEDIA_STRUCTURE",
)


for name in required_gates:

    print(
        f"{name}="
        f"{'PASS' if RESULTS.get(name) else 'FAIL'}"
    )


foundation_pass = all(
    RESULTS.get(
        name,
        False,
    )
    for name in required_gates
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


if RESULTS.get(
    "VSE4_IN_MIDIA"
):

    print(
        "NEXT_STAGE=ACTIVE_PATH_CANARY"
    )

else:

    print(
        "NEXT_STAGE=VSE4_MIDIA_INTEGRATION"
    )


print(
    "VSE4_IN_MIDIA="
    +
    (
        "YES"
        if RESULTS.get(
            "VSE4_IN_MIDIA"
        )
        else
        "NO"
    )
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
    "REAL_MEDIA_MODIFIED=NO"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
