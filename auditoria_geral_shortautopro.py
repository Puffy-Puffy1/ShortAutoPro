#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import symtable
import sys
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


# ============================================================
# SHORTAUTOPRO MASTER AUDIT V1
# ============================================================

ROOT = Path.cwd()

if ROOT.name != "ShortAutoPro":
    fallback = Path.home() / "ShortAutoPro"

    if fallback.is_dir():
        ROOT = fallback


STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

REPORT_TXT = (
    ROOT
    / "temp"
    / f"AUDITORIA_GERAL_{STAMP}.txt"
)

REPORT_JSON = (
    ROOT
    / "manifests"
    / f"auditoria_geral_{STAMP}.json"
)


REPORT_TXT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT_JSON.parent.mkdir(
    parents=True,
    exist_ok=True,
)


results = []
log_lines = []


def out(*parts):

    line = " ".join(
        str(x)
        for x in parts
    )

    print(
        line,
        flush=True,
    )

    log_lines.append(
        line
    )


def section(title):

    out()
    out("=" * 72)
    out(title)
    out("=" * 72)


def result(
    section_name,
    test,
    status,
    detail="",
):

    status = status.upper()

    if status not in {
        "PASS",
        "WARN",
        "FAIL",
        "INFO",
    }:
        status = "INFO"

    item = {
        "section": section_name,
        "test": test,
        "status": status,
        "detail": str(detail),
    }

    results.append(
        item
    )

    line = (
        f"[{status}] "
        f"{section_name} :: "
        f"{test}"
    )

    if detail:
        line += (
            f" -> {detail}"
        )

    out(
        line
    )


def sha256(path):

    h = hashlib.sha256()

    try:

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

    except Exception:

        return ""


def run(
    cmd,
    timeout=30,
    env=None,
):

    try:

        p = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )

        return (
            p.returncode,
            p.stdout or "",
        )

    except subprocess.TimeoutExpired as exc:

        text = ""

        if exc.stdout:
            text += (
                exc.stdout
                if isinstance(
                    exc.stdout,
                    str,
                )
                else
                exc.stdout.decode(
                    errors="replace"
                )
            )

        return (
            124,
            text
            + "\nTIMEOUT",
        )

    except Exception as exc:

        return (
            125,
            f"{type(exc).__name__}: {exc}",
        )


def tail(
    text,
    lines=15,
):

    rows = (
        text
        .strip()
        .splitlines()
    )

    return "\n".join(
        rows[-lines:]
    )


# ============================================================
# SHORT ID RESOLVER
# ============================================================

def resolve_short_id():

    explicit = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if explicit:
        return explicit


    media_root = (
        ROOT
        / "imagens"
    )

    if not media_root.is_dir():
        return ""


    candidates = []

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


    if not candidates:
        return ""


    candidates.sort(
        reverse=True
    )

    return candidates[0][1]


SHORT_ID = resolve_short_id()


# ============================================================
# HEADER
# ============================================================

section(
    "0. AUDIT INFORMATION"
)

out(
    f"ROOT={ROOT}"
)

out(
    f"DATE={datetime.now().isoformat()}"
)

out(
    f"PYTHON={sys.version.split()[0]}"
)

out(
    f"SHORT_ID={SHORT_ID or 'NOT_RESOLVED'}"
)

out(
    "MODE=OFFLINE_SAFE"
)

out(
    "NETWORK_ALLOWED=NO"
)

out(
    "MEDIA_DOWNLOAD=NO"
)

out(
    "VIDEO_RENDER=NO"
)


# ============================================================
# 1. PROJECT STRUCTURE
# ============================================================

section(
    "1. PROJECT STRUCTURE"
)

required_dirs = [
    "roteiros",
    "imagens",
    "audios",
    "videos",
    "temp",
    "logs",
    "manifests",
    "backups",
]


for name in required_dirs:

    path = ROOT / name

    result(
        "STRUCTURE",
        name,
        (
            "PASS"
            if path.is_dir()
            else
            "WARN"
        ),
        path,
    )


required_core = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "legenda_dinamica.py",
]


for name in required_core:

    path = ROOT / name

    result(
        "CORE_FILES",
        name,
        (
            "PASS"
            if path.is_file()
            else
            "FAIL"
        ),
        path,
    )


# ============================================================
# 2. CORE HASHES
# ============================================================

section(
    "2. CORE HASHES"
)

core_hash_files = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "fresh_render_guard_v1.py",
]


for name in core_hash_files:

    path = ROOT / name

    if path.is_file():

        result(
            "HASH",
            name,
            "INFO",
            sha256(
                path
            ),
        )

    else:

        result(
            "HASH",
            name,
            "WARN",
            "arquivo ausente",
        )


# ============================================================
# 3. PYTHON SYNTAX — FULL PROJECT
# ============================================================

section(
    "3. PYTHON COMPILE AUDIT"
)

excluded_parts = {
    "backups",
    "temp",
    "__pycache__",
    ".git",
    "storage",
    ".venv",
    "venv",
}


python_files = []

for path in ROOT.rglob(
    "*.py"
):

    relative = path.relative_to(
        ROOT
    )

    if any(
        part in excluded_parts
        for part in relative.parts
    ):
        continue

    python_files.append(
        path
    )


python_files.sort()


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
                path.relative_to(
                    ROOT
                ),
                str(exc),
            )
        )


result(
    "PYTHON",
    "FILES_TESTED",
    "INFO",
    len(
        python_files
    ),
)


if compile_failures:

    result(
        "PYTHON",
        "COMPILE_ALL",
        "FAIL",
        f"{len(compile_failures)} arquivo(s)",
    )

    for path, exc in compile_failures[:30]:

        out(
            f"COMPILE_FAIL={path} :: {exc}"
        )

else:

    result(
        "PYTHON",
        "COMPILE_ALL",
        "PASS",
        f"{len(python_files)} arquivos",
    )


# ============================================================
# 4. SHELL SYNTAX
# ============================================================

section(
    "4. SHELL SYNTAX"
)

shell_files = []

for path in ROOT.rglob(
    "*.sh"
):

    relative = path.relative_to(
        ROOT
    )

    if any(
        part in excluded_parts
        for part in relative.parts
    ):
        continue

    shell_files.append(
        path
    )


shell_failures = []


for path in sorted(
    shell_files
):

    code, text = run(
        [
            "bash",
            "-n",
            str(path),
        ],
        timeout=10,
    )

    if code != 0:

        shell_failures.append(
            (
                path.relative_to(
                    ROOT
                ),
                tail(
                    text,
                    5,
                ),
            )
        )


result(
    "SHELL",
    "FILES_TESTED",
    "INFO",
    len(
        shell_files
    ),
)


if shell_failures:

    result(
        "SHELL",
        "SYNTAX_ALL",
        "FAIL",
        len(
            shell_failures
        ),
    )

    for path, message in shell_failures:

        out(
            f"SHELL_FAIL={path} :: {message}"
        )

else:

    result(
        "SHELL",
        "SYNTAX_ALL",
        "PASS",
    )


# ============================================================
# 5. DUPLICATE DEFINITIONS
# ============================================================

section(
    "5. DUPLICATE FUNCTION / CLASS AUDIT"
)

duplicate_count = 0


for path in python_files:

    try:

        src = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            src
        )

    except Exception:

        continue


    names = Counter()

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            names[
                node.name
            ] += 1


    duplicated = [
        name
        for name, count
        in names.items()
        if count > 1
    ]


    if duplicated:

        duplicate_count += (
            len(
                duplicated
            )
        )

        out(
            "DUPLICATE_DEFINITION="
            f"{path.relative_to(ROOT)} :: "
            f"{','.join(duplicated)}"
        )


if duplicate_count:

    result(
        "AST",
        "DUPLICATE_DEFINITIONS",
        "WARN",
        duplicate_count,
    )

else:

    result(
        "AST",
        "DUPLICATE_DEFINITIONS",
        "PASS",
    )


# ============================================================
# 6. VSE4 GLOBAL AUDIT
# ============================================================

section(
    "6. VSE4 STATIC AUDIT"
)

vse4 = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if not vse4.is_file():

    result(
        "VSE4",
        "FILE",
        "WARN",
        "visual_selection_engine_v4.py ausente",
    )

else:

    try:

        src = vse4.read_text(
            encoding="utf-8",
        )

        table = symtable.symtable(
            src,
            str(vse4),
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
            dir(
                builtins
            )
        )

        unresolved = set()


        def walk_scope(
            scope,
        ):

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

                walk_scope(
                    child
                )


        walk_scope(
            table
        )


        if unresolved:

            result(
                "VSE4",
                "UNRESOLVED_GLOBALS",
                "FAIL",
                ",".join(
                    sorted(
                        unresolved
                    )
                ),
            )

        else:

            result(
                "VSE4",
                "UNRESOLVED_GLOBALS",
                "PASS",
            )


    except Exception as exc:

        result(
            "VSE4",
            "STATIC_AUDIT",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 7. VSE4 SELF TEST
# ============================================================

section(
    "7. VSE4 RUNTIME SELF TEST"
)


if vse4.is_file():

    code, text = run(
        [
            sys.executable,
            str(vse4),
        ],
        timeout=30,
    )


    if code == 0:

        result(
            "VSE4",
            "SELF_TEST",
            "PASS",
        )

    else:

        result(
            "VSE4",
            "SELF_TEST",
            "FAIL",
            f"exit={code}",
        )

        out(
            "VSE4_SELF_TEST_TAIL:"
        )

        out(
            tail(
                text,
                30,
            )
        )


# ============================================================
# 8. VSE4 HARD MISMATCH REGRESSION
# ============================================================

section(
    "8. VSE4 HARD-MISMATCH REGRESSION"
)


if vse4.is_file():

    probe = r'''
import json
import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="sap_master_audit",
)

score_candidate = ns["score_candidate"]

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
    json.dumps(
        {
            "wrong_hard":
                a.get(
                    "hard_mismatch"
                ),

            "correct_hard":
                b.get(
                    "hard_mismatch"
                ),

            "wrong_effective":
                a.get(
                    "effective"
                ),

            "correct_effective":
                b.get(
                    "effective"
                ),

            "wrong":
                a,

            "correct":
                b,
        },
        ensure_ascii=False,
        default=str,
    )
)
'''


    code, text = run(
        [
            sys.executable,
            "-c",
            probe,
        ],
        timeout=30,
    )


    if code != 0:

        result(
            "VSE4",
            "HARD_MISMATCH_RUNTIME",
            "FAIL",
            tail(
                text,
                12,
            ),
        )

    else:

        try:

            data = json.loads(
                text.strip()
                .splitlines()[-1]
            )


            wrong_hard = data.get(
                "wrong_hard"
            )

            correct_hard = data.get(
                "correct_hard"
            )


            wrong_eff = data.get(
                "wrong_effective"
            )

            correct_eff = data.get(
                "correct_effective"
            )


            out(
                f"WRONG_HARD_MISMATCH={wrong_hard}"
            )

            out(
                f"CORRECT_HARD_MISMATCH={correct_hard}"
            )

            out(
                f"WRONG_EFFECTIVE={wrong_eff}"
            )

            out(
                f"CORRECT_EFFECTIVE={correct_eff}"
            )


            if (
                wrong_hard is True
                and
                correct_hard is False
                and
                isinstance(
                    wrong_eff,
                    (
                        int,
                        float,
                    ),
                )
                and
                isinstance(
                    correct_eff,
                    (
                        int,
                        float,
                    ),
                )
                and
                correct_eff
                >
                wrong_eff
            ):

                result(
                    "VSE4",
                    "HARD_MISMATCH",
                    "PASS",
                )

            else:

                result(
                    "VSE4",
                    "HARD_MISMATCH",
                    "FAIL",
                    (
                        "SP x New York não está "
                        "sendo tratado corretamente"
                    ),
                )


        except Exception as exc:

            result(
                "VSE4",
                "HARD_MISMATCH_PARSE",
                "FAIL",
                f"{type(exc).__name__}: {exc}",
            )


# ============================================================
# 9. PROVIDER ACQUISITION MAP
# ============================================================

section(
    "9. PROVIDER ACQUISITION AUDIT"
)

midia = (
    ROOT
    / "midia.py"
)


provider_functions = {
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
}


if not midia.is_file():

    result(
        "MEDIA",
        "MIDIA_PY",
        "FAIL",
        "ausente",
    )

else:

    try:

        src = midia.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            src
        )


        definitions = {
            node.name:
                node
            for node in tree.body
            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
        }


        missing_defs = (
            provider_functions
            -
            set(
                definitions
            )
        )


        if missing_defs:

            result(
                "MEDIA",
                "PROVIDER_DEFINITIONS",
                "FAIL",
                ",".join(
                    sorted(
                        missing_defs
                    )
                ),
            )

        else:

            result(
                "MEDIA",
                "PROVIDER_DEFINITIONS",
                "PASS",
            )


        search_fn = definitions.get(
            "buscar_todos_candidatos"
        )


        if search_fn is None:

            result(
                "MEDIA",
                "BUSCAR_TODOS_CANDIDATOS",
                "FAIL",
                "função ausente",
            )

        else:

            calls = set()

            for node in ast.walk(
                search_fn
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

                    calls.add(
                        fn.id
                    )

                elif isinstance(
                    fn,
                    ast.Attribute,
                ):

                    calls.add(
                        fn.attr
                    )


            for provider_name in sorted(
                provider_functions
            ):

                result(
                    "MEDIA_PROVIDER",
                    provider_name,
                    (
                        "PASS"
                        if provider_name
                        in calls
                        else
                        "FAIL"
                    ),
                    (
                        "chamado em buscar_todos_candidatos"
                        if provider_name
                        in calls
                        else
                        "NÃO chamado"
                    ),
                )


            result(
                "MEDIA_PROVIDER",
                "CALLS_TOTAL",
                "INFO",
                ",".join(
                    sorted(
                        calls
                    )
                ),
            )


    except Exception as exc:

        result(
            "MEDIA",
            "AST_PROVIDER_AUDIT",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 10. EXTERNAL TOOLS
# ============================================================

section(
    "10. EXTERNAL DEPENDENCIES"
)


for command in [
    "ffmpeg",
    "ffprobe",
]:

    binary = shutil.which(
        command
    )

    result(
        "DEPENDENCY",
        command,
        (
            "PASS"
            if binary
            else
            "FAIL"
        ),
        binary or "não encontrado",
    )


whisper_candidates = [
    (
        Path.home()
        / "whisper.cpp"
        / "build"
        / "bin"
        / "whisper-cli"
    ),

    (
        Path.home()
        / "whisper.cpp"
        / "main"
    ),
]


whisper_bin = next(
    (
        p
        for p
        in whisper_candidates
        if p.is_file()
    ),
    None,
)


result(
    "DEPENDENCY",
    "WHISPER",
    (
        "PASS"
        if whisper_bin
        else
        "WARN"
    ),
    whisper_bin or "não encontrado",
)


whisper_model = (
    Path.home()
    / "whisper.cpp"
    / "models"
    / "ggml-base.bin"
)


result(
    "DEPENDENCY",
    "WHISPER_MODEL",
    (
        "PASS"
        if whisper_model.is_file()
        else
        "WARN"
    ),
    whisper_model,
)


piper = (
    shutil.which(
        "piper"
    )
    or
    shutil.which(
        "piper-tts"
    )
    or
    shutil.which(
        "piper-tts-cli"
    )
)


result(
    "DEPENDENCY",
    "PIPER",
    (
        "PASS"
        if piper
        else
        "WARN"
    ),
    piper or "não encontrado",
)


# ============================================================
# 11. FFMPEG FEATURES
# ============================================================

section(
    "11. FFMPEG CAPABILITIES"
)


if shutil.which(
    "ffmpeg"
):

    code, filters = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-filters",
        ],
        timeout=20,
    )


    for name in [
        "ass",
        "subtitles",
        "zoompan",
    ]:

        found = bool(
            re.search(
                rf"\b{name}\b",
                filters,
            )
        )

        result(
            "FFMPEG_FILTER",
            name,
            (
                "PASS"
                if found
                else
                "FAIL"
            ),
        )


    code, encoders = run(
        [
            "ffmpeg",
            "-hide_banner",
            "-encoders",
        ],
        timeout=20,
    )


    result(
        "FFMPEG_ENCODER",
        "libx264",
        (
            "PASS"
            if "libx264"
            in encoders
            else
            "FAIL"
        ),
    )


# ============================================================
# 12. CURRENT MEDIA
# ============================================================

section(
    "12. CURRENT SHORT MEDIA AUDIT"
)


if not SHORT_ID:

    result(
        "MEDIA_CURRENT",
        "SHORT_ID",
        "WARN",
        "nenhum short resolvido",
    )

else:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{SHORT_ID}"
    )


    result(
        "MEDIA_CURRENT",
        "MEDIA_DIR",
        (
            "PASS"
            if media_dir.is_dir()
            else
            "FAIL"
        ),
        media_dir,
    )


    hashes = []
    scene_bad = 0
    scene_total = 0


    for number in range(
        1,
        13,
    ):

        pattern = (
            f"scene_{number:02d}.*"
        )

        files = [
            p
            for p
            in media_dir.glob(
                pattern
            )
            if p.is_file()
        ]


        count = len(
            files
        )


        scene_total += count


        if count != 1:

            scene_bad += 1

            result(
                "MEDIA_SCENE",
                f"scene_{number:02d}",
                "FAIL",
                f"count={count}",
            )

            continue


        path = files[0]


        try:

            size = path.stat().st_size

        except Exception:

            size = 0


        digest = sha256(
            path
        )

        hashes.append(
            (
                number,
                digest,
                path,
            )
        )


        if size < 1024:

            status = "FAIL"

        else:

            status = "PASS"


        result(
            "MEDIA_SCENE",
            f"scene_{number:02d}",
            status,
            (
                f"{path.name} "
                f"bytes={size} "
                f"sha={digest[:12]}"
            ),
        )


        if (
            path.suffix.lower()
            in {
                ".mp4",
                ".mov",
                ".mkv",
                ".webm",
            }
            and
            shutil.which(
                "ffprobe"
            )
        ):

            code, probe = run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default="
                    "noprint_wrappers=1:"
                    "nokey=1",
                    str(path),
                ],
                timeout=15,
            )


            if code != 0:

                result(
                    "MEDIA_TECH",
                    path.name,
                    "FAIL",
                    tail(
                        probe,
                        5,
                    ),
                )


    result(
        "MEDIA_CURRENT",
        "MEDIA_TOTAL",
        (
            "PASS"
            if scene_total == 12
            else
            "FAIL"
        ),
        scene_total,
    )


    result(
        "MEDIA_CURRENT",
        "INVALID_SCENES",
        (
            "PASS"
            if scene_bad == 0
            else
            "FAIL"
        ),
        scene_bad,
    )


    # Duplicate media SHA
    sha_groups = defaultdict(
        list
    )


    for number, digest, path in hashes:

        if digest:

            sha_groups[
                digest
            ].append(
                number
            )


    duplicates = {
        digest:
            scenes
        for digest, scenes
        in sha_groups.items()
        if len(
            scenes
        ) > 1
    }


    if duplicates:

        for digest, scenes in duplicates.items():

            out(
                "DUPLICATE_MEDIA_SHA="
                f"{digest} "
                f"scenes={scenes}"
            )


        result(
            "MEDIA_CURRENT",
            "DUPLICATE_SHA",
            "WARN",
            len(
                duplicates
            ),
        )

    else:

        result(
            "MEDIA_CURRENT",
            "DUPLICATE_SHA",
            "PASS",
        )


    # Overall fingerprint
    fingerprint_source = "\n".join(
        (
            f"{n}:"
            f"{digest}:"
            f"{path.name}"
        )
        for n, digest, path
        in sorted(
            hashes
        )
    )


    fingerprint = hashlib.sha256(
        fingerprint_source.encode(
            "utf-8"
        )
    ).hexdigest()


    result(
        "MEDIA_CURRENT",
        "FINGERPRINT",
        "INFO",
        fingerprint,
    )


# ============================================================
# 13. CURRENT PIPELINE ASSETS
# ============================================================

section(
    "13. PIPELINE ASSET CONSISTENCY"
)


if SHORT_ID:

    assets = {

        "AUDIO":
            ROOT
            / "audios"
            / f"short_{SHORT_ID}.mp3",

        "ASS":
            ROOT
            / "videos"
            / f"short_{SHORT_ID}.ass",

        "VIDEO_BASE":
            ROOT
            / "temp"
            / SHORT_ID
            / "video_sem_audio.mp4",

        "FINAL":
            ROOT
            / "videos"
            / f"short_v6_{SHORT_ID}.mp4",

        "SCENE_MAP":
            ROOT
            / "roteiros"
            / f"scene_map_{SHORT_ID}.json",
    }


    for name, path in assets.items():

        exists = (
            path.is_file()
            and
            path.stat().st_size > 0
        )


        status = (
            "PASS"
            if exists
            else
            "WARN"
        )


        detail = (
            f"{path} "
            f"bytes={path.stat().st_size}"
            if exists
            else
            path
        )


        result(
            "ASSET",
            name,
            status,
            detail,
        )


# ============================================================
# 14. FRESH RENDER GUARD UNIT TEST
# ============================================================

section(
    "14. RENDER CACHE GUARD TEST"
)


guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if not guard.is_file():

    result(
        "RENDER_GUARD",
        "FILE",
        "WARN",
        "ausente",
    )

else:

    test_sid = (
        "AUDIT_GUARD_"
        + str(
            os.getpid()
        )
    )


    test_code = r'''
import os
from pathlib import Path

os.environ["SHORT_ID"] = "__SID__"

from fresh_render_guard_v1 import clean

root = Path.home() / "ShortAutoPro"
sid = "__SID__"

temp = root / "temp" / sid
videos = root / "videos"

temp.mkdir(
    parents=True,
    exist_ok=True,
)

videos.mkdir(
    parents=True,
    exist_ok=True,
)

ass = (
    videos
    / f"short_{sid}.ass"
)

audio = (
    temp
    / "test.mp3"
)

intermediate = (
    temp
    / "video_sem_audio.mp4"
)

final = (
    videos
    / f"short_v6_{sid}.mp4"
)

ass.write_text(
    "ASS_PROTECTED",
    encoding="utf-8",
)

audio.write_bytes(
    b"AUDIO_PROTECTED"
)

intermediate.write_bytes(
    b"VIDEO"
)

final.write_bytes(
    b"VIDEO"
)

removed = clean(
    sid
)

tests = {

    "ass":
        ass.exists(),

    "audio":
        audio.exists(),

    "intermediate_removed":
        not intermediate.exists(),

    "final_removed":
        not final.exists(),
}

print(
    tests
)

try:
    ass.unlink(
        missing_ok=True
    )
    audio.unlink(
        missing_ok=True
    )
    temp.rmdir()
except Exception:
    pass

if not all(
    tests.values()
):
    raise SystemExit(1)
'''.replace(
        "__SID__",
        test_sid,
    )


    code, text = run(
        [
            sys.executable,
            "-c",
            test_code,
        ],
        timeout=20,
    )


    result(
        "RENDER_GUARD",
        "PROTECTED_INPUTS",
        (
            "PASS"
            if code == 0
            else
            "FAIL"
        ),
        tail(
            text,
            5,
        ),
    )


# ============================================================
# 15. PROVENANCE MANIFEST HEALTH
# ============================================================

section(
    "15. PROVENANCE HEALTH"
)


prov_dirs = [
    ROOT
    / "manifests"
    / "source_provenance_live",

    ROOT
    / "manifests",
]


prov_dir = next(
    (
        p
        for p
        in prov_dirs
        if p.is_dir()
    ),
    None,
)


if prov_dir is None:

    result(
        "PROVENANCE",
        "DIRECTORY",
        "WARN",
        "não encontrada",
    )

else:

    json_files = list(
        prov_dir.glob(
            "*.json"
        )
    )


    valid = 0
    invalid = 0


    for path in sorted(
        json_files,
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:100]:

        try:

            json.loads(
                path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )

            valid += 1

        except Exception:

            invalid += 1


    result(
        "PROVENANCE",
        "JSON_VALID",
        (
            "PASS"
            if invalid == 0
            else
            "FAIL"
        ),
        (
            f"valid={valid} "
            f"invalid={invalid}"
        ),
    )


# ============================================================
# 16. STATIC RISK SCAN
# ============================================================

section(
    "16. STATIC BUG-RISK SCAN"
)


risk_patterns = {

    "SHELL_TRUE":
        re.compile(
            r"shell\s*=\s*True"
        ),

    "OS_SYSTEM":
        re.compile(
            r"\bos\.system\s*\("
        ),

    "EVAL":
        re.compile(
            r"(?<![\w.])eval\s*\("
        ),

    "BARE_EXCEPT":
        re.compile(
            r"^\s*except\s*:"
        ),

    "TMP_PATH":
        re.compile(
            r"""["']/tmp/"""
        ),

    "RM_RF":
        re.compile(
            r"\brm\s+-rf\b"
        ),
}


core_scan_files = [
    ROOT / "midia.py",
    ROOT / "video.py",
    ROOT / "v6.py",
    ROOT / "gerar_short.sh",
    ROOT / "roteiro.py",
    ROOT / "legenda_dinamica.py",
    ROOT / "visual_selection_engine_v4.py",
]


risk_total = 0


for path in core_scan_files:

    if not path.is_file():
        continue


    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    lines = text.splitlines()


    for risk_name, pattern in risk_patterns.items():

        matches = []

        for number, line in enumerate(
            lines,
            start=1,
        ):

            if pattern.search(
                line
            ):

                matches.append(
                    (
                        number,
                        line.strip()[:160],
                    )
                )


        if matches:

            risk_total += (
                len(
                    matches
                )
            )


            result(
                "STATIC_RISK",
                (
                    f"{path.name}:"
                    f"{risk_name}"
                ),
                "WARN",
                (
                    f"{len(matches)} ocorrência(s)"
                ),
            )


            for number, line in matches[:8]:

                out(
                    f"RISK={path.name}:"
                    f"{number}:"
                    f"{risk_name}:"
                    f"{line}"
                )


if risk_total == 0:

    result(
        "STATIC_RISK",
        "CORE_SCAN",
        "PASS",
    )

else:

    result(
        "STATIC_RISK",
        "CORE_SCAN",
        "WARN",
        (
            f"{risk_total} ocorrência(s) "
            "para revisão manual"
        ),
    )


# ============================================================
# 17. HARDCODED OLD SHORT IDs
# ============================================================

section(
    "17. HARDCODED SHORT-ID AUDIT"
)


id_pattern = re.compile(
    r"20\d{2}-\d{2}-\d{2}_\d{4}"
)


hardcoded_ids = []


for path in core_scan_files:

    if not path.is_file():
        continue


    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        found = id_pattern.findall(
            line
        )

        for sid in found:

            hardcoded_ids.append(
                (
                    path.name,
                    number,
                    sid,
                )
            )


if hardcoded_ids:

    for path, number, sid in hardcoded_ids:

        out(
            f"HARDCODED_SHORT_ID="
            f"{path}:{number}:{sid}"
        )


    result(
        "CONFIG",
        "HARDCODED_SHORT_IDS",
        "WARN",
        len(
            hardcoded_ids
        ),
    )

else:

    result(
        "CONFIG",
        "HARDCODED_SHORT_IDS",
        "PASS",
    )


# ============================================================
# 18. CONFIG NAMES — NO SECRET VALUES
# ============================================================

section(
    "18. CONFIGURATION AUDIT"
)


config_candidates = [
    ROOT / "config.env",
    ROOT / ".env",
]


for path in config_candidates:

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
            or
            line.startswith(
                "#"
            )
            or
            "=" not in line
        ):
            continue


        key = line.split(
            "=",
            1,
        )[0].strip()


        if re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*",
            key,
        ):

            keys.append(
                key
            )


    result(
        "CONFIG",
        path.name,
        "INFO",
        (
            "VARIABLE_NAMES="
            + ",".join(
                sorted(
                    set(
                        keys
                    )
                )
            )
        ),
    )


# ============================================================
# 19. DISK SPACE
# ============================================================

section(
    "19. STORAGE"
)


try:

    usage = shutil.disk_usage(
        ROOT
    )

    free_mb = (
        usage.free
        /
        1024
        /
        1024
    )


    status = (
        "PASS"
        if free_mb >= 500
        else
        (
            "WARN"
            if free_mb >= 200
            else
            "FAIL"
        )
    )


    result(
        "STORAGE",
        "FREE_SPACE",
        status,
        f"{free_mb:.1f} MB",
    )

except Exception as exc:

    result(
        "STORAGE",
        "FREE_SPACE",
        "WARN",
        exc,
    )


# ============================================================
# 20. FINAL SUMMARY
# ============================================================

section(
    "20. FINAL SUMMARY"
)


counts = Counter(
    item[
        "status"
    ]
    for item
    in results
)


out(
    f"PASS={counts.get('PASS', 0)}"
)

out(
    f"WARN={counts.get('WARN', 0)}"
)

out(
    f"FAIL={counts.get('FAIL', 0)}"
)

out(
    f"INFO={counts.get('INFO', 0)}"
)


fails = [
    item
    for item
    in results
    if item[
        "status"
    ] == "FAIL"
]


warnings = [
    item
    for item
    in results
    if item[
        "status"
    ] == "WARN"
]


if fails:

    overall = (
        "FAIL"
    )

elif warnings:

    overall = (
        "PASS_WITH_WARNINGS"
    )

else:

    overall = (
        "PASS"
    )


out(
    f"OVERALL_STATUS={overall}"
)


if fails:

    out()
    out(
        "===== CRITICAL FAILURES ====="
    )

    for item in fails:

        out(
            "FAIL :: "
            f"{item['section']} :: "
            f"{item['test']} :: "
            f"{item['detail']}"
        )


if warnings:

    out()
    out(
        "===== WARNINGS ====="
    )

    for item in warnings[:50]:

        out(
            "WARN :: "
            f"{item['section']} :: "
            f"{item['test']} :: "
            f"{item['detail']}"
        )


payload = {

    "timestamp":
        datetime.now().isoformat(),

    "root":
        str(
            ROOT
        ),

    "short_id":
        SHORT_ID,

    "overall":
        overall,

    "counts":
        dict(
            counts
        ),

    "results":
        results,
}


try:

    REPORT_JSON.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

except Exception:

    traceback.print_exc()


REPORT_TXT.write_text(
    "\n".join(
        log_lines
    )
    + "\n",
    encoding="utf-8",
)


out()
out(
    f"REPORT_TXT={REPORT_TXT}"
)

out(
    f"REPORT_JSON={REPORT_JSON}"
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
    "MIDIA_PY_EXECUTED=NO"
)

out(
    "TERMUX_CONTINUA_ABERTO=SIM"
)


if fails:

    raise SystemExit(
        1
    )
