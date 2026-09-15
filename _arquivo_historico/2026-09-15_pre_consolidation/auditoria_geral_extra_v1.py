#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict
import ast
import builtins
import hashlib
import json
import os
import re
import shutil
import subprocess
import symtable
import time
import traceback


ROOT = Path.home() / "ShortAutoPro"

PASS_COUNT = 0
WARN_COUNT = 0
FAIL_COUNT = 0


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def PASS(name, detail=""):
    global PASS_COUNT
    PASS_COUNT += 1
    print(
        f"PASS | {name}"
        + (
            f" | {detail}"
            if detail != ""
            else ""
        )
    )


def WARN(name, detail=""):
    global WARN_COUNT
    WARN_COUNT += 1
    print(
        f"WARN | {name}"
        + (
            f" | {detail}"
            if detail != ""
            else ""
        )
    )


def FAIL(name, detail=""):
    global FAIL_COUNT
    FAIL_COUNT += 1
    print(
        f"FAIL | {name}"
        + (
            f" | {detail}"
            if detail != ""
            else ""
        )
    )


def INFO(name, detail=""):
    print(
        f"INFO | {name}"
        + (
            f" | {detail}"
            if detail != ""
            else ""
        )
    )


def source_text(path):
    try:
        return Path(path).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def sha256(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def run(
    cmd,
    timeout=60,
):

    try:

        result = subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )

        return (
            result.returncode,
            result.stdout,
        )

    except subprocess.TimeoutExpired as exc:

        return (
            124,
            "TIMEOUT\n"
            + (
                exc.stdout
                if isinstance(
                    exc.stdout,
                    str,
                )
                else ""
            ),
        )

    except Exception as exc:

        return (
            125,
            f"{type(exc).__name__}: {exc}",
        )


def detect_short_id():

    env = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if env:
        return env


    media_root = (
        ROOT
        / "imagens"
    )

    candidates = []

    if media_root.is_dir():

        for path in media_root.glob(
            "short_*"
        ):

            if not path.is_dir():
                continue

            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0

            candidates.append(
                (
                    mtime,
                    path.name[
                        len("short_"):
                    ],
                )
            )


    if candidates:

        candidates.sort(
            reverse=True
        )

        return candidates[0][1]


    return ""


SID = detect_short_id()


section(
    "SHORTAUTOPRO GENERAL DEEP AUDIT V1"
)

INFO(
    "DATE",
    time.strftime(
        "%Y-%m-%d %H:%M:%S"
    ),
)

INFO(
    "ROOT",
    ROOT,
)

INFO(
    "SHORT_ID",
    SID or "NOT_DETECTED",
)


# ============================================================
# 1. BASIC STRUCTURE
# ============================================================

section(
    "1. PROJECT STRUCTURE"
)

required_dirs = (
    "roteiros",
    "imagens",
    "audios",
    "videos",
    "temp",
    "logs",
    "manifests",
    "backups",
)


for name in required_dirs:

    path = ROOT / name

    if path.is_dir():
        PASS(
            f"DIR_{name}",
            path,
        )
    else:
        WARN(
            f"DIR_{name}",
            "missing",
        )


# ============================================================
# 2. CORE FILES
# ============================================================

section(
    "2. CORE FILES"
)

core_files = (
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_provenance_capture_v1.py",
    "media_diversity_guard_v1.py",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
)


for name in core_files:

    path = ROOT / name

    if path.is_file():

        PASS(
            f"CORE_{name}",
            f"{path.stat().st_size} bytes",
        )

        try:

            INFO(
                f"HASH_{name}",
                sha256(path),
            )

        except Exception as exc:

            WARN(
                f"HASH_{name}",
                exc,
            )

    else:

        WARN(
            f"CORE_{name}",
            "missing",
        )


# ============================================================
# 3. ALL ROOT PYTHON COMPILE
# ============================================================

section(
    "3. ROOT PYTHON COMPILE"
)

root_python = sorted(
    ROOT.glob("*.py")
)

compile_failures = []


for path in root_python:

    status, output = run(
        [
            "python",
            "-m",
            "py_compile",
            str(path),
        ],
        timeout=30,
    )

    if status == 0:

        PASS(
            f"COMPILE_{path.name}",
        )

    else:

        FAIL(
            f"COMPILE_{path.name}",
            output.strip()[-1000:],
        )

        compile_failures.append(
            path.name
        )


INFO(
    "PY_FILES_TESTED",
    len(root_python),
)


# ============================================================
# 4. SHELL SYNTAX
# ============================================================

section(
    "4. SHELL SYNTAX"
)

shell_files = sorted(
    ROOT.glob("*.sh")
)


for path in shell_files:

    status, output = run(
        [
            "bash",
            "-n",
            str(path),
        ],
        timeout=15,
    )

    if status == 0:

        PASS(
            f"SHELL_{path.name}",
        )

    else:

        FAIL(
            f"SHELL_{path.name}",
            output.strip(),
        )


# ============================================================
# 5. DUPLICATE FUNCTION DEFINITIONS
# ============================================================

section(
    "5. DUPLICATE FUNCTION DEFINITIONS"
)

duplicate_defs = {}


for path in root_python:

    try:

        tree = ast.parse(
            source_text(path)
        )

    except Exception:
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

            defs[
                node.name
            ].append(
                node.lineno
            )


    duplicates = {
        name: lines
        for name, lines
        in defs.items()
        if len(lines) > 1
    }


    if duplicates:

        duplicate_defs[
            path.name
        ] = duplicates

        WARN(
            f"DUPLICATE_DEFS_{path.name}",
            duplicates,
        )


if not duplicate_defs:

    PASS(
        "DUPLICATE_TOP_LEVEL_DEFS",
        "none",
    )


# ============================================================
# 6. VSE4 COMPILE
# ============================================================

section(
    "6. VSE4 STATIC HEALTH"
)

vse = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if vse.is_file():

    status, output = run(
        [
            "python",
            "-m",
            "py_compile",
            str(vse),
        ],
        timeout=30,
    )

    if status == 0:
        PASS(
            "VSE4_COMPILE",
        )
    else:
        FAIL(
            "VSE4_COMPILE",
            output[-1500:],
        )


    try:

        src = source_text(vse)

        table = symtable.symtable(
            src,
            str(vse),
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


        def walk_scope(scope):

            for child in scope.get_children():

                for symbol in child.get_symbols():

                    name = (
                        symbol.get_name()
                    )

                    if (
                        symbol.is_referenced()
                        and
                        symbol.is_global()
                        and
                        name not in defined
                        and
                        name not in builtin_names
                    ):

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

            FAIL(
                "VSE4_UNRESOLVED_GLOBALS",
                sorted(unresolved),
            )

        else:

            PASS(
                "VSE4_UNRESOLVED_GLOBALS",
                "none",
            )

    except Exception as exc:

        FAIL(
            "VSE4_GLOBAL_AUDIT",
            exc,
        )

else:

    FAIL(
        "VSE4",
        "missing",
    )


# ============================================================
# 7. VSE4 OFFICIAL SELF TEST
# ============================================================

section(
    "7. VSE4 OFFICIAL SELF TEST"
)


if vse.is_file():

    status, output = run(
        [
            "python",
            str(vse),
        ],
        timeout=45,
    )


    INFO(
        "VSE4_SELF_TEST_STATUS",
        status,
    )


    if status == 0:

        PASS(
            "VSE4_SELF_TEST",
            output.strip()[-1500:],
        )

    else:

        FAIL(
            "VSE4_SELF_TEST",
            output.strip()[-3000:],
        )


# ============================================================
# 8. VSE4 GEO + HARD MISMATCH LIVE TEST
# ============================================================

section(
    "8. VSE4 GEO / HARD MISMATCH"
)


if vse.is_file():

    try:

        import runpy

        ns = runpy.run_path(
            str(vse),
            run_name="vse_general_audit",
        )

        geo_hits = ns[
            "geo_hits"
        ]

        score_candidate = ns[
            "score_candidate"
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
                "New York Manhattan",

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


        sp_geo = set(
            geo_hits(
                scene
            )
        )

        ny_geo = set(
            geo_hits(
                wrong["title"]
            )
        )

        correct_geo = set(
            geo_hits(
                correct["title"]
            )
        )


        INFO(
            "SCENE_GEO",
            sorted(sp_geo),
        )

        INFO(
            "WRONG_GEO",
            sorted(ny_geo),
        )

        INFO(
            "CORRECT_GEO",
            sorted(correct_geo),
        )


        if (
            "sao_paulo" in sp_geo
            and
            "new_york" in ny_geo
        ):

            PASS(
                "GEO_IDENTIFICATION",
            )

        else:

            FAIL(
                "GEO_IDENTIFICATION",
            )


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


        INFO(
            "WRONG_RESULT",
            json.dumps(
                a,
                ensure_ascii=False,
                default=str,
            )[:3000],
        )

        INFO(
            "CORRECT_RESULT",
            json.dumps(
                b,
                ensure_ascii=False,
                default=str,
            )[:3000],
        )


        if (
            isinstance(a, dict)
            and
            a.get(
                "hard_mismatch"
            )
            is True
        ):

            PASS(
                "GEO_HARD_MISMATCH",
                "NY rejected for Sao Paulo",
            )

        else:

            FAIL(
                "GEO_HARD_MISMATCH",
                (
                    "Empire State Building "
                    "not marked hard mismatch"
                ),
            )


        if (
            isinstance(a, dict)
            and
            isinstance(b, dict)
            and
            b.get(
                "effective",
                -10**9,
            )
            >
            a.get(
                "effective",
                10**9,
            )
        ):

            PASS(
                "SEMANTIC_RANK_ORDER",
                "correct > wrong",
            )

        else:

            FAIL(
                "SEMANTIC_RANK_ORDER",
                "wrong candidate still too strong",
            )


    except Exception as exc:

        FAIL(
            "VSE4_RUNTIME_TEST",
            (
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )

        traceback.print_exc()


# ============================================================
# 9. MIDIA.PY PROVIDER DEFINITIONS
# ============================================================

section(
    "9. PROVIDER ACQUISITION DEFINITIONS"
)

midia = (
    ROOT
    / "midia.py"
)


provider_names = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
    "buscar_todos_candidatos",
)


if midia.is_file():

    try:

        tree = ast.parse(
            source_text(
                midia
            )
        )


        function_map = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        for name in provider_names:

            node = function_map.get(
                name
            )

            if node:

                PASS(
                    f"PROVIDER_DEF_{name}",
                    (
                        f"lines="
                        f"{node.lineno}-"
                        f"{node.end_lineno}"
                    ),
                )

            else:

                WARN(
                    f"PROVIDER_DEF_{name}",
                    "missing",
                )


        target = function_map.get(
            "buscar_todos_candidatos"
        )


        if target:

            calls = []


            for node in ast.walk(
                target
            ):

                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue


                name = None


                if isinstance(
                    node.func,
                    ast.Name,
                ):

                    name = (
                        node.func.id
                    )

                elif isinstance(
                    node.func,
                    ast.Attribute,
                ):

                    name = (
                        node.func.attr
                    )


                if name:

                    calls.append(
                        (
                            node.lineno,
                            name,
                        )
                    )


            called_names = {
                name
                for _, name
                in calls
            }


            for provider_fn in (
                "pexels_video",
                "pexels_foto",
                "pixabay_video",
                "pixabay_foto",
                "coverr_video",
            ):

                if provider_fn in called_names:

                    PASS(
                        f"ACQUISITION_CALL_{provider_fn}",
                    )

                else:

                    WARN(
                        f"ACQUISITION_CALL_{provider_fn}",
                        "not called by buscar_todos_candidatos",
                    )


            INFO(
                "ACQUISITION_CALLS",
                sorted(calls),
            )


    except Exception as exc:

        FAIL(
            "MIDIA_AST",
            exc,
        )


# ============================================================
# 10. VSE4 INTEGRATION INTO MIDIA
# ============================================================

section(
    "10. VSE4 REAL PIPELINE INTEGRATION"
)


if midia.is_file():

    text = source_text(
        midia
    )


    integration_patterns = (
        "visual_selection_engine_v4",
        "VSE4",
        "vse4",
    )


    matches = [
        pattern
        for pattern in integration_patterns
        if pattern in text
    ]


    if matches:

        PASS(
            "MIDIA_VSE4_REFERENCE",
            matches,
        )

    else:

        WARN(
            "MIDIA_VSE4_REFERENCE",
            (
                "VSE4 exists but no direct "
                "reference found in midia.py"
            ),
        )


    if (
        "visual_selection_final_gate_v3"
        in text
        or
        "VSE3"
        in text
    ):

        INFO(
            "MIDIA_VSE3_REFERENCE",
            "present",
        )


# ============================================================
# 11. PROVENANCE MODULE
# ============================================================

section(
    "11. PROVENANCE SYSTEM"
)

prov_module = (
    ROOT
    / "media_provenance_capture_v1.py"
)


if prov_module.is_file():

    PASS(
        "PROVENANCE_MODULE",
        prov_module,
    )


    status, output = run(
        [
            "python",
            "-m",
            "py_compile",
            str(prov_module),
        ],
        timeout=20,
    )


    if status == 0:

        PASS(
            "PROVENANCE_COMPILE",
        )

    else:

        FAIL(
            "PROVENANCE_COMPILE",
            output,
        )

else:

    FAIL(
        "PROVENANCE_MODULE",
        "missing",
    )


prov_root = (
    ROOT
    / "manifests"
    / "source_provenance_live"
)


if prov_root.is_dir():

    files = list(
        prov_root.rglob(
            "*.json"
        )
    )

    INFO(
        "PROVENANCE_JSON_COUNT",
        len(files),
    )


    invalid = 0


    for path in files[-100:]:

        try:

            json.loads(
                source_text(
                    path
                )
            )

        except Exception as exc:

            invalid += 1

            FAIL(
                f"PROVENANCE_JSON_{path.name}",
                exc,
            )


    if invalid == 0:

        PASS(
            "PROVENANCE_JSON_VALIDITY",
        )

else:

    WARN(
        "PROVENANCE_LIVE_DIR",
        "missing",
    )


# ============================================================
# 12. CURRENT MEDIA
# ============================================================

section(
    "12. CURRENT 12-SCENE MEDIA"
)


if SID:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{SID}"
    )


    INFO(
        "MEDIA_DIR",
        media_dir,
    )


    scene_files = defaultdict(
        list
    )


    if media_dir.is_dir():

        for path in media_dir.iterdir():

            if not path.is_file():
                continue


            match = re.match(
                r"scene_(\d+)\.",
                path.name,
                re.I,
            )


            if match:

                scene_files[
                    int(
                        match.group(1)
                    )
                ].append(
                    path
                )


        exact = True
        media_hashes = defaultdict(
            list
        )


        for n in range(
            1,
            13,
        ):

            items = scene_files.get(
                n,
                [],
            )


            if len(items) == 1:

                path = items[0]

                size = (
                    path.stat().st_size
                )


                if size > 0:

                    PASS(
                        f"SCENE_{n:02d}",
                        (
                            f"{path.name} "
                            f"{size} bytes"
                        ),
                    )

                else:

                    FAIL(
                        f"SCENE_{n:02d}",
                        "zero bytes",
                    )

                    exact = False


                try:

                    media_hashes[
                        sha256(path)
                    ].append(
                        path.name
                    )

                except Exception as exc:

                    WARN(
                        f"SCENE_HASH_{n:02d}",
                        exc,
                    )


            elif len(items) == 0:

                FAIL(
                    f"SCENE_{n:02d}",
                    "missing",
                )

                exact = False


            else:

                FAIL(
                    f"SCENE_{n:02d}",
                    [
                        x.name
                        for x in items
                    ],
                )

                exact = False


        if exact:

            PASS(
                "MEDIA_STRUCTURE",
                "12 scenes / exactly one file each",
            )


        duplicates = {
            key: value
            for key, value
            in media_hashes.items()
            if len(value) > 1
        }


        if duplicates:

            WARN(
                "MEDIA_EXACT_DUPLICATES",
                duplicates,
            )

        else:

            PASS(
                "MEDIA_EXACT_DUPLICATES",
                "none",
            )


    else:

        FAIL(
            "MEDIA_DIR",
            "missing",
        )

else:

    WARN(
        "CURRENT_MEDIA",
        "SHORT_ID unavailable",
    )


# ============================================================
# 13. RENDER INPUTS
# ============================================================

section(
    "13. CURRENT RENDER CHAIN"
)


if SID:

    files = {
        "AUDIO":
            ROOT
            / "audios"
            / f"short_{SID}.mp3",

        "ASS":
            ROOT
            / "videos"
            / f"short_{SID}.ass",

        "VIDEO_BASE":
            ROOT
            / "temp"
            / SID
            / "video_sem_audio.mp4",

        "FINAL":
            ROOT
            / "videos"
            / f"short_v6_{SID}.mp4",
    }


    for name, path in files.items():

        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            PASS(
                name,
                (
                    f"{path.stat().st_size} "
                    f"bytes"
                ),
            )

        else:

            if name == "FINAL":

                WARN(
                    name,
                    "not present",
                )

            else:

                WARN(
                    name,
                    "missing",
                )


    final = files[
        "FINAL"
    ]


    if final.is_file():

        INFO(
            "FINAL_SHA256",
            sha256(final),
        )


        status, output = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                (
                    "format=duration,size,"
                    "bit_rate"
                ),
                "-show_entries",
                (
                    "stream=codec_name,"
                    "codec_type,width,height,"
                    "r_frame_rate"
                ),
                "-of",
                "default=noprint_wrappers=1",
                str(final),
            ],
            timeout=30,
        )


        if status == 0:

            PASS(
                "FINAL_FFPROBE",
                output.strip(),
            )

        else:

            FAIL(
                "FINAL_FFPROBE",
                output.strip(),
            )


# ============================================================
# 14. CURRENT JSON VALIDITY
# ============================================================

section(
    "14. CURRENT SHORT JSON VALIDITY"
)


if SID:

    candidates = []


    for folder in (
        ROOT / "roteiros",
        ROOT / "manifests",
    ):

        if folder.is_dir():

            candidates.extend(
                folder.glob(
                    f"*{SID}*.json"
                )
            )


    invalid = []


    for path in sorted(
        set(candidates)
    ):

        try:

            json.loads(
                source_text(
                    path
                )
            )

        except Exception as exc:

            invalid.append(
                path.name
            )

            FAIL(
                f"JSON_{path.name}",
                exc,
            )


    if not invalid:

        PASS(
            "CURRENT_JSON_VALIDITY",
            (
                f"{len(candidates)} "
                f"files"
            ),
        )


# ============================================================
# 15. RENDER GUARD SAFETY
# ============================================================

section(
    "15. FRESH RENDER GUARD SAFETY"
)

guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    text = source_text(
        guard
    )


    if (
        ".ass"
        in text
        and
        "PROTECTED"
        in text
    ):

        PASS(
            "RENDER_GUARD_ASS_PROTECTION",
        )

    else:

        WARN(
            "RENDER_GUARD_ASS_PROTECTION",
            "not explicitly detected",
        )


    if (
        'rglob("*")'
        in text
        and
        "short_id"
        in text
    ):

        WARN(
            "RENDER_GUARD_BROAD_RGLOB",
            (
                "review broad recursive "
                "deletion logic"
            ),
        )

    else:

        PASS(
            "RENDER_GUARD_BROAD_DELETE",
            "not detected",
        )


# ============================================================
# 16. DEPENDENCIES
# ============================================================

section(
    "16. EXTERNAL DEPENDENCIES"
)


for command in (
    "python",
    "ffmpeg",
    "ffprobe",
    "bash",
):

    path = shutil.which(
        command
    )


    if path:

        PASS(
            f"BIN_{command}",
            path,
        )

    else:

        FAIL(
            f"BIN_{command}",
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


if whisper.is_file():

    PASS(
        "WHISPER_CLI",
        whisper,
    )

else:

    WARN(
        "WHISPER_CLI",
        "missing",
    )


if whisper_model.is_file():

    PASS(
        "WHISPER_MODEL",
        (
            f"{whisper_model.stat().st_size} "
            f"bytes"
        ),
    )

else:

    WARN(
        "WHISPER_MODEL",
        "missing",
    )


# ============================================================
# 17. STORAGE
# ============================================================

section(
    "17. STORAGE"
)


try:

    disk = shutil.disk_usage(
        ROOT
    )

    free_gb = (
        disk.free
        / 1024**3
    )

    total_gb = (
        disk.total
        / 1024**3
    )

    INFO(
        "DISK_TOTAL_GB",
        f"{total_gb:.2f}",
    )

    INFO(
        "DISK_FREE_GB",
        f"{free_gb:.2f}",
    )


    if free_gb >= 2.0:

        PASS(
            "DISK_FREE",
            f"{free_gb:.2f} GB",
        )

    elif free_gb >= 0.75:

        WARN(
            "DISK_FREE",
            f"{free_gb:.2f} GB",
        )

    else:

        FAIL(
            "DISK_FREE",
            f"{free_gb:.2f} GB",
        )


except Exception as exc:

    WARN(
        "DISK_AUDIT",
        exc,
    )


# ============================================================
# 18. RECENT LOG ERRORS
# ============================================================

section(
    "18. RECENT LOG ERROR SCAN"
)

log_root = (
    ROOT
    / "logs"
    / "producao"
)


error_pattern = re.compile(
    r"("
    r"Traceback|"
    r"NameError|"
    r"TypeError|"
    r"SyntaxError|"
    r"ModuleNotFoundError|"
    r"FileNotFoundError|"
    r"\bERROR\b|"
    r"\bERRO\b|"
    r"\bFAIL\b"
    r")",
    re.I,
)


if log_root.is_dir():

    logs = sorted(
        (
            path
            for path
            in log_root.glob("*")
            if path.is_file()
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:15]


    recent_hits = []


    for path in logs:

        text = source_text(
            path
        )


        matches = [
            line.strip()
            for line in text.splitlines()
            if error_pattern.search(
                line
            )
        ]


        if matches:

            recent_hits.append(
                (
                    path.name,
                    matches[-8:],
                )
            )


    if recent_hits:

        WARN(
            "RECENT_LOG_ERRORS",
            (
                f"{len(recent_hits)} "
                f"logs contain error/fail strings"
            ),
        )


        for name, lines in recent_hits:

            print()
            print(
                f"LOG={name}"
            )

            for line in lines:
                print(
                    "  ",
                    line[:500],
                )

    else:

        PASS(
            "RECENT_LOG_ERRORS",
            "none detected",
        )


# ============================================================
# 19. KNOWN CURRENT VISUAL RISK
# ============================================================

section(
    "19. VISUAL ENGINE CURRENT RISK"
)


if vse.is_file():

    vse_text = source_text(
        vse
    )


    for symbol in (
        "GEO_GROUPS",
        "GENERIC_LIFESTYLE",
        "MEDICINE_TERMS",
        "concept_hits",
        "geo_hits",
        "score_candidate",
    ):

        if symbol in vse_text:

            PASS(
                f"VSE4_SYMBOL_{symbol}",
            )

        else:

            FAIL(
                f"VSE4_SYMBOL_{symbol}",
                "missing",
            )


# ============================================================
# 20. SUMMARY
# ============================================================

section(
    "20. FINAL AUDIT SUMMARY"
)


print(
    f"PASS_COUNT={PASS_COUNT}"
)

print(
    f"WARN_COUNT={WARN_COUNT}"
)

print(
    f"FAIL_COUNT={FAIL_COUNT}"
)


if FAIL_COUNT == 0:

    if WARN_COUNT == 0:

        print(
            "AUDIT_RESULT=PASS"
        )

    else:

        print(
            "AUDIT_RESULT=PASS_WITH_WARNINGS"
        )

else:

    print(
        "AUDIT_RESULT=FAIL"
    )


print()
print(
    "SHORT_ID="
    + (
        SID
        or
        "NOT_DETECTED"
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
    "MIDIA_PY_MODIFIED=NO"
)

print(
    "PROJECT_FILES_MODIFIED=NO"
)

print(
    "GENERAL_AUDIT_COMPLETE=YES"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
