#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict
import ast
import builtins
import hashlib
import json
import os
import py_compile
import re
import runpy
import shutil
import subprocess
import symtable
import traceback


# ============================================================
# SHORTAUTOPRO GENERAL AUDIT V3
#
# Objetivos:
# - não usar rede
# - não baixar mídia
# - não renderizar
# - não alterar pipeline
# - testar estrutura geral
# - testar VSE4
# - testar mídia ativa
# - testar inputs de render
# - procurar bugs e regressões
# ============================================================


ROOT = (
    Path.home()
    / "ShortAutoPro"
)

os.chdir(
    ROOT
)


PASS = []
WARN = []
FAIL = []


def header(title):

    print()
    print(
        "=" * 72
    )
    print(
        title
    )
    print(
        "=" * 72
    )


def out(*args):

    print(
        *args,
        flush=True,
    )


def good(name, detail="PASS"):

    PASS.append(
        (
            name,
            str(detail),
        )
    )

    out(
        f"PASS | {name} | {detail}"
    )


def warning(name, detail):

    WARN.append(
        (
            name,
            str(detail),
        )
    )

    out(
        f"WARN | {name} | {detail}"
    )


def bad(name, detail):

    FAIL.append(
        (
            name,
            str(detail),
        )
    )

    out(
        f"FAIL | {name} | {detail}"
    )


def sha(path):

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


def subprocess_safe(
    cmd,
    timeout=90,
):

    try:

        return subprocess.run(
            cmd,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )

    except Exception as exc:

        return None


def ffprobe(path):

    proc = subprocess_safe(
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
            str(path),
        ],
        timeout=60,
    )

    if (
        proc is None
        or proc.returncode != 0
    ):

        return None

    try:

        return json.loads(
            proc.stdout
        )

    except Exception:

        return None


def resolve_short_id():

    env = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if env:
        return (
            env,
            "ENV",
        )


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

            sid = path.name[
                len("short_"):
            ]

            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0

            candidates.append(
                (
                    mtime,
                    sid,
                )
            )


    if candidates:

        candidates.sort(
            reverse=True
        )

        return (
            candidates[0][1],
            "LATEST_MEDIA_DIR",
        )


    audio_root = (
        ROOT
        / "audios"
    )

    if audio_root.is_dir():

        audio_candidates = []

        for path in audio_root.glob(
            "short_*.mp3"
        ):

            sid = path.stem[
                len("short_"):
            ]

            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0

            audio_candidates.append(
                (
                    mtime,
                    sid,
                )
            )


        if audio_candidates:

            audio_candidates.sort(
                reverse=True
            )

            return (
                audio_candidates[0][1],
                "LATEST_AUDIO",
            )


    return (
        "",
        "NOT_FOUND",
    )


SHORT_ID, SHORT_ID_SOURCE = resolve_short_id()


# ============================================================
# 0. ENVIRONMENT
# ============================================================

header(
    "0. ENVIRONMENT"
)

out(
    "ROOT=",
    ROOT,
)

out(
    "SHORT_ID=",
    SHORT_ID,
)

out(
    "SHORT_ID_SOURCE=",
    SHORT_ID_SOURCE,
)


if ROOT.is_dir():

    good(
        "PROJECT_ROOT",
        ROOT,
    )

else:

    bad(
        "PROJECT_ROOT",
        "directory missing",
    )


python_version = subprocess_safe(
    [
        "python",
        "--version",
    ]
)

if (
    python_version
    and
    python_version.returncode == 0
):

    good(
        "PYTHON_RUNTIME",
        (
            python_version.stdout
            or
            python_version.stderr
        ).strip(),
    )

else:

    bad(
        "PYTHON_RUNTIME",
        "python unavailable",
    )


for executable in (
    "ffmpeg",
    "ffprobe",
):

    path = shutil.which(
        executable
    )

    if path:

        good(
            executable.upper(),
            path,
        )

    else:

        bad(
            executable.upper(),
            "not found",
        )


try:

    usage = shutil.disk_usage(
        ROOT
    )

    free_gb = (
        usage.free
        /
        1024
        /
        1024
        /
        1024
    )

    out(
        f"DISK_FREE_GB={free_gb:.2f}"
    )

    if free_gb >= 1.0:

        good(
            "DISK_SPACE",
            f"{free_gb:.2f} GB free",
        )

    else:

        warning(
            "DISK_SPACE",
            f"only {free_gb:.2f} GB free",
        )

except Exception as exc:

    warning(
        "DISK_SPACE",
        exc,
    )


# ============================================================
# 1. CRITICAL FILES
# ============================================================

header(
    "1. CRITICAL FILES"
)


critical_files = [

    "gerar_short.sh",

    "roteiro.py",
    "midia.py",
    "video.py",
    "v6.py",

    "legenda_dinamica.py",

    "visual_selection_engine_v4.py",

    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",

    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


for name in critical_files:

    path = (
        ROOT
        / name
    )

    if path.is_file():

        size = path.stat().st_size

        good(
            "FILE_" + name,
            f"{size} bytes",
        )

        try:

            out(
                f"HASH {name}={sha(path)}"
            )

        except Exception as exc:

            warning(
                "HASH_" + name,
                exc,
            )

    else:

        # Alguns módulos auxiliares podem não existir
        # em instalações anteriores.
        if name in {
            "visual_selection_engine_v4.py",
            "media_diversity_guard_v1.py",
            "media_provenance_capture_v1.py",
        }:

            warning(
                "FILE_" + name,
                "missing",
            )

        else:

            bad(
                "FILE_" + name,
                "missing",
            )


# ============================================================
# 2. PYTHON COMPILE - ALL TOP LEVEL
# ============================================================

header(
    "2. PYTHON COMPILE"
)


python_files = sorted(
    ROOT.glob(
        "*.py"
    )
)


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
                path.name,
                str(exc),
            )
        )

        bad(
            "PY_COMPILE_" + path.name,
            str(exc)[
                :400
            ],
        )


out(
    "PYTHON_FILES_CHECKED=",
    len(
        python_files
    ),
)

out(
    "PYTHON_COMPILE_FAILURES=",
    len(
        compile_failures
    ),
)


if not compile_failures:

    good(
        "PYTHON_COMPILE_ALL",
        f"{len(python_files)} files",
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

header(
    "3. SHELL SYNTAX"
)


shell_files = sorted(
    ROOT.glob(
        "*.sh"
    )
)

shell_failures = []


for path in shell_files:

    proc = subprocess_safe(
        [
            "bash",
            "-n",
            str(path),
        ]
    )

    if (
        proc is None
        or proc.returncode != 0
    ):

        shell_failures.append(
            path.name
        )

        bad(
            "SHELL_" + path.name,
            (
                proc.stderr[:500]
                if proc
                else
                "execution failure"
            ),
        )


out(
    "SHELL_FILES_CHECKED=",
    len(
        shell_files
    ),
)


if not shell_failures:

    good(
        "SHELL_SYNTAX_ALL",
        f"{len(shell_files)} files",
    )


# ============================================================
# 4. AST / DUPLICATE DEFINITIONS
# ============================================================

header(
    "4. PYTHON STRUCTURE"
)


for filename in (
    "midia.py",
    "video.py",
    "v6.py",
    "visual_selection_engine_v4.py",
):

    path = (
        ROOT
        / filename
    )

    if not path.is_file():
        continue


    try:

        src = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            src
        )


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
            for name, lines in defs.items()
            if len(lines) > 1
        }


        if duplicates:

            for name, lines in duplicates.items():

                warning(
                    f"DUPLICATE_DEF_{filename}_{name}",
                    lines,
                )

        else:

            good(
                "NO_DUPLICATE_TOP_LEVEL_" + filename,
                "PASS",
            )


    except Exception as exc:

        bad(
            "AST_" + filename,
            exc,
        )


# ============================================================
# 5. ACTIVE MEDIA INVENTORY
# ============================================================

header(
    "5. ACTIVE MEDIA INVENTORY"
)


chosen_files = []


if SHORT_ID:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{SHORT_ID}"
    )


    out(
        "MEDIA_DIR=",
        media_dir,
    )


    if media_dir.is_dir():

        valid_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
        }


        invalid_scene_count = 0


        for number in range(
            1,
            13,
        ):

            prefix = (
                f"scene_{number:02d}"
            )


            matches = [
                p
                for p in media_dir.glob(
                    prefix + ".*"
                )
                if (
                    p.is_file()
                    and
                    p.suffix.casefold()
                    in
                    valid_extensions
                )
            ]


            out(
                f"SCENE_{number:02d}_COUNT="
                f"{len(matches)}"
            )


            for path in matches:

                out(
                    f"SCENE_{number:02d}_FILE="
                    f"{path.name}"
                )


            if len(matches) != 1:

                invalid_scene_count += 1

                bad(
                    f"SCENE_{number:02d}_COUNT",
                    len(matches),
                )

            else:

                chosen_files.append(
                    matches[0]
                )


        out(
            "MEDIA_TOTAL=",
            len(
                chosen_files
            ),
        )

        out(
            "INVALID_SCENE_COUNT=",
            invalid_scene_count,
        )


        if (
            invalid_scene_count == 0
            and
            len(chosen_files) == 12
        ):

            good(
                "MEDIA_12_SCENES",
                "12/12",
            )

    else:

        warning(
            "MEDIA_DIR",
            "active media directory missing",
        )

else:

    warning(
        "SHORT_ID",
        "could not resolve active short",
    )


# ============================================================
# 6. MEDIA TECHNICAL VALIDATION
# ============================================================

header(
    "6. MEDIA TECHNICAL VALIDATION"
)


technical_ok = 0
technical_fail = 0


for path in chosen_files:

    data = ffprobe(
        path
    )


    if data is None:

        technical_fail += 1

        bad(
            "MEDIA_TECH_" + path.name,
            "ffprobe failed",
        )

        continue


    streams = data.get(
        "streams",
        [],
    )

    file_format = data.get(
        "format",
        {},
    )


    if not streams:

        technical_fail += 1

        bad(
            "MEDIA_TECH_" + path.name,
            "no streams",
        )

        continue


    technical_ok += 1


    out(
        f"TECH_{path.name}="
        f"PASS size={file_format.get('size')}"
    )


out(
    "MEDIA_TECHNICAL_OK=",
    technical_ok,
)

out(
    "MEDIA_TECHNICAL_FAILURES=",
    technical_fail,
)


if chosen_files:

    if technical_fail == 0:

        good(
            "MEDIA_TECHNICAL_TEST",
            f"{technical_ok}/12",
        )

    else:

        bad(
            "MEDIA_TECHNICAL_TEST",
            f"{technical_fail} failure(s)",
        )

else:

    warning(
        "MEDIA_TECHNICAL_TEST",
        "not run because active media was unavailable",
    )


# ============================================================
# 7. EXACT MEDIA DUPLICATES
# ============================================================

header(
    "7. MEDIA EXACT-DUPLICATE AUDIT"
)


hash_groups = defaultdict(
    list
)


for path in chosen_files:

    try:

        digest = sha(
            path
        )

        hash_groups[
            digest
        ].append(
            path.name
        )

    except Exception as exc:

        bad(
            "MEDIA_HASH_" + path.name,
            exc,
        )


duplicates = {
    digest: names
    for digest, names in hash_groups.items()
    if len(names) > 1
}


if duplicates:

    for digest, names in duplicates.items():

        warning(
            "EXACT_MEDIA_DUPLICATE",
            (
                f"{names} "
                f"sha={digest[:20]}"
            ),
        )

else:

    if chosen_files:

        good(
            "MEDIA_EXACT_DUPLICATE",
            "none",
        )


# ============================================================
# 8. RENDER INPUTS
# ============================================================

header(
    "8. RENDER INPUTS"
)


if SHORT_ID:

    render_inputs = {

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
    }


    for name, path in render_inputs.items():

        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            good(
                "RENDER_" + name,
                (
                    f"{path.stat().st_size} bytes "
                    f"{path}"
                ),
            )

        else:

            if name == "FINAL":

                warning(
                    "RENDER_FINAL",
                    "final video absent",
                )

            else:

                warning(
                    "RENDER_" + name,
                    f"missing: {path}",
                )


    ass = render_inputs[
        "ASS"
    ]


    if ass.is_file():

        text = ass.read_text(
            encoding="utf-8",
            errors="replace",
        )

        dialogue_count = len(
            re.findall(
                r"^Dialogue:",
                text,
                re.MULTILINE,
            )
        )


        out(
            "ASS_DIALOGUE_COUNT=",
            dialogue_count,
        )


        if (
            "[Events]" in text
            and
            dialogue_count > 0
        ):

            good(
                "ASS_STRUCTURE",
                (
                    f"{dialogue_count} "
                    "Dialogue events"
                ),
            )

        else:

            bad(
                "ASS_STRUCTURE",
                "invalid or empty ASS",
            )


    for name in (
        "AUDIO",
        "VIDEO_BASE",
        "FINAL",
    ):

        path = render_inputs[
            name
        ]

        if not path.is_file():
            continue


        info = ffprobe(
            path
        )


        if info is None:

            bad(
                "FFPROBE_" + name,
                "failed",
            )

        else:

            duration = (
                info
                .get(
                    "format",
                    {},
                )
                .get(
                    "duration"
                )
            )

            out(
                f"{name}_DURATION="
                f"{duration}"
            )

            good(
                "FFPROBE_" + name,
                "PASS",
            )


# ============================================================
# 9. VSE4 MODULE + SELF TEST
# ============================================================

header(
    "9. VSE4 RUNTIME CERTIFICATION"
)


vse_path = (
    ROOT
    / "visual_selection_engine_v4.py"
)

vse_ns = None


if vse_path.is_file():

    try:

        vse_ns = runpy.run_path(
            str(vse_path),
            run_name=(
                "shortautopro_"
                "general_audit_v3"
            ),
        )

        good(
            "VSE4_MODULE_LOAD",
            "PASS",
        )

    except Exception:

        bad(
            "VSE4_MODULE_LOAD",
            traceback.format_exc()[
                -2500:
            ],
        )


if vse_ns:

    self_test = vse_ns.get(
        "self_test"
    )


    if callable(
        self_test
    ):

        try:

            self_test()

            good(
                "VSE4_SELF_TEST",
                "PASS",
            )

        except Exception:

            bad(
                "VSE4_SELF_TEST",
                traceback.format_exc()[
                    -2200:
                ],
            )

    else:

        warning(
            "VSE4_SELF_TEST",
            "function absent",
        )


# ============================================================
# 10. VSE4 GLOBAL SYMBOL AUDIT
# ============================================================

header(
    "10. VSE4 GLOBAL SYMBOL AUDIT"
)


if vse_path.is_file():

    try:

        source = vse_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        table = symtable.symtable(
            source,
            str(vse_path),
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


        builtins_set = set(
            dir(
                builtins
            )
        )

        unresolved = set()


        def walk(scope):

            for child in scope.get_children():

                for symbol in child.get_symbols():

                    name = (
                        symbol
                        .get_name()
                    )

                    if not symbol.is_referenced():
                        continue

                    if not symbol.is_global():
                        continue

                    if name in defined:
                        continue

                    if name in builtins_set:
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


        if unresolved:

            bad(
                "VSE4_UNRESOLVED_GLOBALS",
                sorted(
                    unresolved
                ),
            )

        else:

            good(
                "VSE4_UNRESOLVED_GLOBALS",
                "NONE",
            )


    except Exception as exc:

        bad(
            "VSE4_GLOBAL_AUDIT",
            exc,
        )


# ============================================================
# 11. VSE4 DIRECT GEO REGRESSION
# ============================================================

header(
    "11. VSE4 GEO / SEMANTIC REGRESSION"
)


if vse_ns:

    score_candidate = vse_ns.get(
        "score_candidate"
    )

    geo_hits = vse_ns.get(
        "geo_hits"
    )


    if callable(
        score_candidate
    ):

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
                (
                    "Empire State Building "
                    "Manhattan New York"
                ),

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
                (
                    "Apartment building "
                    "Sao Paulo Brazil"
                ),

            "must":
                "1/2",

            "score":
                120,

            "width":
                1920,

            "height":
                1080,
        }


        try:

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
                "WRONG_HARD_MISMATCH=",
                a.get(
                    "hard_mismatch"
                ),
            )

            out(
                "WRONG_EFFECTIVE=",
                a.get(
                    "effective"
                ),
            )

            out(
                "CORRECT_HARD_MISMATCH=",
                b.get(
                    "hard_mismatch"
                ),
            )

            out(
                "CORRECT_EFFECTIVE=",
                b.get(
                    "effective"
                ),
            )


            if a.get(
                "hard_mismatch"
            ) is True:

                good(
                    "VSE4_GEO_HARD_MISMATCH",
                    (
                        "São Paulo rejects "
                        "New York"
                    ),
                )

            else:

                bad(
                    "VSE4_GEO_HARD_MISMATCH",
                    (
                        "New York candidate "
                        "was not hard rejected"
                    ),
                )


            if b.get(
                "hard_mismatch"
            ) is False:

                good(
                    "VSE4_CORRECT_GEO_ACCEPT",
                    "São Paulo accepted",
                )

            else:

                bad(
                    "VSE4_CORRECT_GEO_ACCEPT",
                    b,
                )


            try:

                wrong_effective = float(
                    a.get(
                        "effective",
                        0,
                    )
                )

                correct_effective = float(
                    b.get(
                        "effective",
                        0,
                    )
                )


                if (
                    correct_effective
                    >
                    wrong_effective
                ):

                    good(
                        "VSE4_SEMANTIC_RANKING",
                        (
                            f"correct={correct_effective} "
                            f"> wrong={wrong_effective}"
                        ),
                    )

                else:

                    bad(
                        "VSE4_SEMANTIC_RANKING",
                        (
                            f"correct={correct_effective} "
                            f"wrong={wrong_effective}"
                        ),
                    )

            except Exception as exc:

                bad(
                    "VSE4_EFFECTIVE_SCORE",
                    exc,
                )


        except Exception:

            bad(
                "VSE4_DIRECT_REGRESSION",
                traceback.format_exc()[
                    -2500:
                ],
            )


    if callable(
        geo_hits
    ):

        try:

            sp = set(
                geo_hits(
                    "São Paulo Brasil"
                )
            )

            ny = set(
                geo_hits(
                    (
                        "Empire State Building "
                        "Manhattan New York"
                    )
                )
            )


            out(
                "SP_GEO=",
                sorted(
                    sp
                ),
            )

            out(
                "NY_GEO=",
                sorted(
                    ny
                ),
            )


            if (
                sp
                and
                ny
                and
                sp != ny
            ):

                good(
                    "VSE4_GEO_DISTINCT",
                    "PASS",
                )

            else:

                bad(
                    "VSE4_GEO_DISTINCT",
                    (
                        f"SP={sp} "
                        f"NY={ny}"
                    ),
                )


        except Exception as exc:

            bad(
                "VSE4_GEO_RUNTIME",
                exc,
            )


# ============================================================
# 12. PROVIDER ACQUISITION STATIC AUDIT
# ============================================================

header(
    "12. PROVIDER ACQUISITION"
)


midia_path = (
    ROOT
    / "midia.py"
)


if midia_path.is_file():

    try:

        source = midia_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            source
        )


        functions = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        providers = {

            "PEXELS_VIDEO":
                "pexels_video",

            "PEXELS_PHOTO":
                "pexels_foto",

            "PIXABAY_VIDEO":
                "pixabay_video",

            "PIXABAY_PHOTO":
                "pixabay_foto",

            "COVERR_VIDEO":
                "coverr_video",

            "WIKIMEDIA":
                "buscar_wikimedia_fotos",
        }


        for label, name in providers.items():

            if name in functions:

                good(
                    "PROVIDER_FUNC_" + label,
                    (
                        f"line="
                        f"{functions[name].lineno}"
                    ),
                )

            else:

                warning(
                    "PROVIDER_FUNC_" + label,
                    "function absent",
                )


        buscar = functions.get(
            "buscar_todos_candidatos"
        )


        if buscar:

            calls = set()


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


            out(
                "BUSCAR_TODOS_CALLS=",
                sorted(
                    calls
                ),
            )


            for label, name in providers.items():

                # Wikimedia pode ser chamado
                # através de rota própria.
                if name in calls:

                    good(
                        "PROVIDER_ACTIVE_" + label,
                        name,
                    )

                elif label != "WIKIMEDIA":

                    warning(
                        "PROVIDER_ACTIVE_" + label,
                        (
                            "defined but not called "
                            "inside buscar_todos_candidatos"
                        ),
                    )


        else:

            bad(
                "BUSCAR_TODOS_CANDIDATOS",
                "function absent",
            )


    except Exception:

        bad(
            "PROVIDER_STATIC_AUDIT",
            traceback.format_exc()[
                -2000:
            ],
        )


# ============================================================
# 13. PIPELINE HOOK INTEGRATION
# ============================================================

header(
    "13. PIPELINE HOOK INTEGRATION"
)


if midia_path.is_file():

    text = midia_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    hook_checks = {

        "VSE4":
            (
                "visual_selection_engine_v4"
                in text
            ),

        "VSE3":
            (
                "visual_selection_final_gate_v3"
                in text
            ),

        "DIVERSITY":
            (
                "media_diversity_guard_v1"
                in text
            ),

        "PROVENANCE":
            (
                "media_provenance_capture_v1"
                in text
            ),

        "COMMIT_LOCK":
            (
                "visual_scene_commit_lock_v1"
                in text
            ),
    }


    for name, active in hook_checks.items():

        out(
            f"HOOK_{name}="
            f"{'YES' if active else 'NO'}"
        )


    if hook_checks[
        "PROVENANCE"
    ]:

        good(
            "HOOK_PROVENANCE",
            "present",
        )

    else:

        warning(
            "HOOK_PROVENANCE",
            "not detected in midia.py",
        )


    if hook_checks[
        "DIVERSITY"
    ]:

        good(
            "HOOK_DIVERSITY",
            "present",
        )

    else:

        warning(
            "HOOK_DIVERSITY",
            "not detected",
        )


    if hook_checks[
        "VSE4"
    ]:

        good(
            "HOOK_VSE4",
            "present",
        )

    else:

        warning(
            "HOOK_VSE4",
            (
                "VSE4 not yet integrated "
                "into active midia.py"
            ),
        )


# ============================================================
# 14. FRESH RENDER GUARD SAFETY
# ============================================================

header(
    "14. FRESH RENDER GUARD SAFETY"
)


guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    source = guard.read_text(
        encoding="utf-8",
        errors="replace",
    )


    if (
        ".ass" in source
        and
        "PROTECTED_SUFFIXES"
        in source
    ):

        good(
            "RENDER_GUARD_ASS_PROTECTION",
            "detected",
        )

    else:

        warning(
            "RENDER_GUARD_ASS_PROTECTION",
            (
                "could not prove .ass "
                "protection statically"
            ),
        )


    if (
        "video_sem_audio.mp4"
        in source
    ):

        good(
            "RENDER_GUARD_TEMP_VIDEO",
            "explicit disposable asset",
        )


# ============================================================
# 15. RECENT LOG ERROR SCAN
# ============================================================

header(
    "15. RECENT LOG ERROR SCAN"
)


logs_root = (
    ROOT
    / "logs"
    / "producao"
)


error_pattern = re.compile(
    (
        r"traceback|"
        r"nameerror|"
        r"typeerror|"
        r"assertionerror|"
        r"syntaxerror|"
        r"\berro\b|"
        r"\berror\b|"
        r"\bfail(?:ed|ure)?\b"
    ),
    re.IGNORECASE,
)


if logs_root.is_dir():

    recent_logs = sorted(
        [
            p
            for p in logs_root.glob(
                "*.log"
            )
            if p.is_file()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[
        :25
    ]


    logs_with_errors = []


    for path in recent_logs:

        try:

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except Exception:
            continue


        matches = error_pattern.findall(
            text
        )


        if matches:

            logs_with_errors.append(
                (
                    path,
                    len(matches),
                )
            )


    out(
        "RECENT_LOGS_SCANNED=",
        len(
            recent_logs
        ),
    )

    out(
        "RECENT_LOGS_WITH_ERROR_WORDS=",
        len(
            logs_with_errors
        ),
    )


    for path, count in logs_with_errors[
        :10
    ]:

        warning(
            "LOG_ERROR_MARKERS",
            (
                f"{path.name}: "
                f"{count} marker(s)"
            ),
        )


else:

    warning(
        "LOG_DIRECTORY",
        "logs/producao absent",
    )


# ============================================================
# 16. DANGEROUS / STALE PATTERN AUDIT
# ============================================================

header(
    "16. CODE RISK PATTERNS"
)


risk_patterns = {

    "RM_RF":
        r"\brm\s+-rf\b",

    "SHUTIL_RMTREE":
        r"shutil\.rmtree",

    "BARE_EXCEPT":
        r"except\s*:",

    "HARDCODED_TEST_SHORT":
        r"2026-09-02_2358",
}


risk_files = [

    ROOT
    / "gerar_short.sh",

    ROOT
    / "midia.py",

    ROOT
    / "video.py",

    ROOT
    / "v6.py",

    ROOT
    / "fresh_render_guard_v1.py",

    ROOT
    / "visual_selection_engine_v4.py",
]


for label, pattern in risk_patterns.items():

    locations = []


    compiled = re.compile(
        pattern,
        re.IGNORECASE,
    )


    for path in risk_files:

        if not path.is_file():
            continue


        try:

            lines = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()

        except Exception:
            continue


        for line_number, line in enumerate(
            lines,
            start=1,
        ):

            if compiled.search(
                line
            ):

                locations.append(
                    (
                        path.name,
                        line_number,
                    )
                )


    if locations:

        warning(
            "RISK_" + label,
            locations[
                :20
            ],
        )

    else:

        good(
            "RISK_" + label,
            "none",
        )


# ============================================================
# 17. SHORT ASSET CONSISTENCY
# ============================================================

header(
    "17. SHORT ASSET CONSISTENCY"
)


if SHORT_ID:

    expected_assets = {

        "ROTEIRO":
            ROOT
            / "roteiros"
            / f"short_{SHORT_ID}.txt",

        "SCENE_MAP":
            ROOT
            / "roteiros"
            / f"scene_map_{SHORT_ID}.json",

        "MOTION_PLAN":
            ROOT
            / "roteiros"
            / f"motion_plan_{SHORT_ID}.json",

        "AUDIO":
            ROOT
            / "audios"
            / f"short_{SHORT_ID}.mp3",
    }


    for name, path in expected_assets.items():

        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            good(
                "ASSET_" + name,
                path.name,
            )

        else:

            warning(
                "ASSET_" + name,
                f"missing: {path}",
            )


    scene_map = expected_assets[
        "SCENE_MAP"
    ]


    if scene_map.is_file():

        try:

            data = json.loads(
                scene_map.read_text(
                    encoding="utf-8"
                )
            )

            out(
                "SCENE_MAP_TYPE=",
                type(data).__name__,
            )

            good(
                "SCENE_MAP_JSON",
                "valid JSON",
            )

        except Exception as exc:

            bad(
                "SCENE_MAP_JSON",
                exc,
            )


# ============================================================
# 18. BACKUP AVAILABILITY
# ============================================================

header(
    "18. BACKUP HEALTH"
)


backup_root = (
    ROOT
    / "backups"
)


if backup_root.is_dir():

    backup_files = [
        p
        for p in backup_root.rglob(
            "*"
        )
        if p.is_file()
    ]


    out(
        "BACKUP_FILE_COUNT=",
        len(
            backup_files
        ),
    )


    if backup_files:

        good(
            "BACKUPS_PRESENT",
            len(
                backup_files
            ),
        )

    else:

        warning(
            "BACKUPS_PRESENT",
            "folder empty",
        )

else:

    warning(
        "BACKUP_DIRECTORY",
        "missing",
    )


# ============================================================
# 19. FINAL SUMMARY
# ============================================================

header(
    "19. FINAL SUMMARY"
)


out(
    "SHORT_ID=",
    SHORT_ID,
)

out(
    "PASS_COUNT=",
    len(
        PASS
    ),
)

out(
    "WARN_COUNT=",
    len(
        WARN
    ),
)

out(
    "FAIL_COUNT=",
    len(
        FAIL
    ),
)


if FAIL:

    print()
    print(
        "===== FAILURES ====="
    )

    for name, detail in FAIL:

        print(
            f"FAIL | {name} | {detail}"
        )


if WARN:

    print()
    print(
        "===== WARNINGS ====="
    )

    for name, detail in WARN[
        :50
    ]:

        print(
            f"WARN | {name} | {detail}"
        )


print()
print(
    "=" * 72
)


if not FAIL:

    print(
        "GENERAL_AUDIT_STATUS=PASS"
    )

elif len(
    FAIL
) <= 3:

    print(
        "GENERAL_AUDIT_STATUS=FAIL_LOCALIZED"
    )

else:

    print(
        "GENERAL_AUDIT_STATUS=FAIL_MULTIPLE"
    )


print(
    f"TOTAL_PASS={len(PASS)}"
)

print(
    f"TOTAL_WARN={len(WARN)}"
)

print(
    f"TOTAL_FAIL={len(FAIL)}"
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
    "PIPELINE_FILES_MODIFIED=NO"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)

print(
    "=" * 72
)


# Nonzero apenas para indicar falhas ao shell.
# Não fecha o Termux.
if FAIL:
    raise SystemExit(1)
