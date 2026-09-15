#!/usr/bin/env python3

from pathlib import Path
from collections import Counter

import ast
import builtins
import hashlib
import json
import os
import re
import runpy
import shutil
import subprocess
import symtable
import sys
import time
import traceback


ROOT = Path.home() / "ShortAutoPro"

REPORT = (
    ROOT
    / "temp"
    / "SHORTAUTOPRO_MASTER_AUDIT_V1.txt"
)

NOW = time.time()

CRITICAL = []
WARNINGS = []
PASSES = []


def out(*args):

    print(
        " ".join(
            str(x)
            for x in args
        )
    )


def section(name):

    print()
    print(
        "=" * 72
    )
    print(name)
    print(
        "=" * 72
    )


def critical(code, detail=""):

    CRITICAL.append(
        (
            code,
            str(detail),
        )
    )

    out(
        "CRITICAL",
        code,
        detail,
    )


def warning(code, detail=""):

    WARNINGS.append(
        (
            code,
            str(detail),
        )
    )

    out(
        "WARNING",
        code,
        detail,
    )


def passed(code, detail=""):

    PASSES.append(
        (
            code,
            str(detail),
        )
    )

    out(
        "PASS",
        code,
        detail,
    )


def read_text(path):

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def file_sha256(path):

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


def media_signature_ok(path):

    try:

        with path.open(
            "rb"
        ) as f:

            head = f.read(
                32
            )

    except Exception:

        return False


    suffix = path.suffix.casefold()


    if suffix in {
        ".jpg",
        ".jpeg",
    }:

        return head.startswith(
            b"\xff\xd8"
        )


    if suffix == ".png":

        return head.startswith(
            b"\x89PNG\r\n\x1a\n"
        )


    if suffix == ".webp":

        return (
            len(head) >= 12
            and
            head[:4] == b"RIFF"
            and
            head[8:12] == b"WEBP"
        )


    if suffix in {
        ".mp4",
        ".mov",
        ".m4v",
    }:

        return (
            b"ftyp"
            in
            head[:24]
        )


    return True


def scene_count_from_json(obj):

    if isinstance(
        obj,
        list,
    ):

        return len(obj)


    if isinstance(
        obj,
        dict,
    ):

        for key in (
            "scenes",
            "cenas",
            "scene_map",
        ):

            value = obj.get(
                key
            )

            if isinstance(
                value,
                (
                    list,
                    dict,
                ),
            ):

                return len(value)


        scene_keys = [
            key
            for key in obj
            if re.fullmatch(
                r"(?:scene|cena)_?\d+",
                str(key),
                re.I,
            )
        ]

        if scene_keys:

            return len(
                scene_keys
            )


    return 0


class Tee:

    def __init__(
        self,
        *streams,
    ):

        self.streams = streams


    def write(
        self,
        data,
    ):

        for stream in self.streams:

            stream.write(
                data
            )

            stream.flush()

        return len(data)


    def flush(self):

        for stream in self.streams:

            stream.flush()


if not ROOT.is_dir():

    print(
        "ROOT_NOT_FOUND=",
        ROOT,
    )

    raise SystemExit(2)


REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


report_handle = REPORT.open(
    "w",
    encoding="utf-8",
)

original_stdout = sys.stdout

sys.stdout = Tee(
    original_stdout,
    report_handle,
)


try:

    # ========================================================
    # 1
    # ========================================================

    section(
        "1. SHORTAUTOPRO MASTER AUDIT"
    )

    out(
        "DATE=",
        time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    )

    out(
        "ROOT=",
        ROOT,
    )

    out(
        "PYTHON=",
        sys.version.replace(
            "\n",
            " ",
        ),
    )

    out(
        "NETWORK_ALLOWED=NO"
    )

    out(
        "RENDER_ALLOWED=NO"
    )

    out(
        "MEDIA_DOWNLOAD_ALLOWED=NO"
    )


    # ========================================================
    # 2
    # ========================================================

    section(
        "2. ENVIRONMENT"
    )


    for command in (
        "python",
        "bash",
        "ffmpeg",
        "ffprobe",
    ):

        found = shutil.which(
            command
        )

        if found:

            passed(
                f"TOOL_{command.upper()}",
                found,
            )

        else:

            critical(
                f"TOOL_{command.upper()}_MISSING"
            )


    whisper = (
        Path.home()
        / "whisper.cpp"
        / "build"
        / "bin"
        / "whisper-cli"
    )


    model = (
        Path.home()
        / "whisper.cpp"
        / "models"
        / "ggml-base.bin"
    )


    if whisper.is_file():

        passed(
            "WHISPER_CLI",
            whisper,
        )

    else:

        warning(
            "WHISPER_CLI_MISSING",
            whisper,
        )


    if (
        model.is_file()
        and
        model.stat().st_size
        >
        1_000_000
    ):

        passed(
            "WHISPER_MODEL",
            f"{model.stat().st_size} bytes",
        )

    else:

        warning(
            "WHISPER_MODEL_MISSING",
            model,
        )


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


    out(
        f"DISK_FREE_MB={free_mb:.1f}"
    )


    if free_mb < 300:

        critical(
            "LOW_DISK_SPACE",
            f"{free_mb:.1f} MB",
        )

    elif free_mb < 800:

        warning(
            "DISK_SPACE_LOW",
            f"{free_mb:.1f} MB",
        )

    else:

        passed(
            "DISK_SPACE",
            f"{free_mb:.1f} MB",
        )


    # ========================================================
    # 3
    # ========================================================

    section(
        "3. REQUIRED CORE FILES"
    )


    required = [
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
    ]


    for name in required:

        path = (
            ROOT
            /
            name
        )


        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            passed(
                "CORE_FILE",
                f"{name} "
                f"{path.stat().st_size} bytes",
            )

        else:

            critical(
                "CORE_FILE_MISSING",
                name,
            )


    # ========================================================
    # 4
    # ========================================================

    section(
        "4. PYTHON SYNTAX"
    )


    python_files = sorted(
        ROOT.glob(
            "*.py"
        )
    )


    syntax_failures = []


    for path in python_files:

        try:

            source = read_text(
                path
            )

            compile(
                source,
                str(path),
                "exec",
            )

        except Exception as exc:

            syntax_failures.append(
                (
                    path.name,
                    type(exc).__name__,
                    str(exc),
                )
            )


    out(
        "PYTHON_FILES_SCANNED=",
        len(
            python_files
        ),
    )


    if syntax_failures:

        for item in syntax_failures[:50]:

            out(
                "PYTHON_SYNTAX_FAIL",
                *item,
            )

        critical(
            "PYTHON_SYNTAX_FAILURES",
            len(
                syntax_failures
            ),
        )

    else:

        passed(
            "PYTHON_SYNTAX",
            f"{len(python_files)} files",
        )


    # ========================================================
    # 5
    # ========================================================

    section(
        "5. SHELL SYNTAX"
    )


    shell_files = sorted(
        ROOT.glob(
            "*.sh"
        )
    )


    shell_failures = []


    for path in shell_files:

        process = subprocess.run(
            [
                "bash",
                "-n",
                str(path),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


        if process.returncode != 0:

            shell_failures.append(
                (
                    path.name,
                    process.stderr.strip(),
                )
            )


    out(
        "SHELL_FILES_SCANNED=",
        len(
            shell_files
        ),
    )


    if shell_failures:

        for name, error in shell_failures[:30]:

            out(
                "SHELL_SYNTAX_FAIL",
                name,
                error,
            )

        critical(
            "SHELL_SYNTAX_FAILURES",
            len(
                shell_failures
            ),
        )

    else:

        passed(
            "SHELL_SYNTAX",
            f"{len(shell_files)} files",
        )


    # ========================================================
    # 6
    # ========================================================

    section(
        "6. PIPELINE STAGE REFERENCES"
    )


    gerar = (
        ROOT
        /
        "gerar_short.sh"
    )


    if gerar.is_file():

        text = read_text(
            gerar
        )


        references = sorted(
            set(
                re.findall(
                    r"\bpython(?:3)?\s+"
                    r"['\"]?"
                    r"([A-Za-z0-9_./-]+\.py)",
                    text,
                )
            )
        )


        out(
            "PYTHON_STAGE_REFERENCES=",
            len(
                references
            ),
        )


        missing = []


        for reference in references:

            path = (
                ROOT
                /
                reference
            )


            exists = path.is_file()


            out(
                f"STAGE={reference} "
                f"EXISTS="
                f"{'YES' if exists else 'NO'}"
            )


            if not exists:

                missing.append(
                    reference
                )


        if missing:

            critical(
                "BROKEN_STAGE_REFERENCES",
                ",".join(
                    missing
                ),
            )

        else:

            passed(
                "PIPELINE_STAGE_REFERENCES"
            )


    # ========================================================
    # 7
    # ========================================================

    section(
        "7. SHORT_ID CONSISTENCY"
    )


    for name in (
        "midia.py",
        "video.py",
        "v6.py",
        "legenda_dinamica.py",
    ):

        path = (
            ROOT
            /
            name
        )


        if not path.is_file():

            continue


        text = read_text(
            path
        )


        has_short_id = bool(
            re.search(
                r"os\.(?:getenv|environ\.get)"
                r"\s*\("
                r"\s*['\"]SHORT_ID['\"]",
                text,
            )
        )


        out(
            f"{name}: "
            f"SHORT_ID_ENV="
            f"{'YES' if has_short_id else 'NO'}"
        )


        if (
            name
            in
            {
                "video.py",
                "v6.py",
            }
            and
            not has_short_id
        ):

            critical(
                "SHORT_ID_ENV_NOT_HONORED",
                name,
            )


    # ========================================================
    # 8
    # ========================================================

    section(
        "8. DUPLICATE TOP-LEVEL DEFINITIONS"
    )


    for name in (
        "midia.py",
        "video.py",
        "v6.py",
        "visual_selection_engine_v4.py",
    ):

        path = (
            ROOT
            /
            name
        )


        if not path.is_file():

            continue


        try:

            tree = ast.parse(
                read_text(
                    path
                )
            )

        except Exception:

            continue


        names = [
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
        ]


        duplicates = sorted(
            name
            for name, count
            in Counter(
                names
            ).items()
            if count > 1
        )


        out(
            f"{path.name}: "
            f"DUPLICATE_DEFINITIONS="
            +
            (
                ",".join(
                    duplicates
                )
                if duplicates
                else
                "NONE"
            )
        )


        if duplicates:

            warning(
                "DUPLICATE_TOP_LEVEL_DEFINITION",
                f"{path.name}: "
                f"{','.join(duplicates)}",
            )


    # ========================================================
    # 9
    # ========================================================

    section(
        "9. VSE4 GLOBAL AUDIT"
    )


    vse4 = (
        ROOT
        /
        "visual_selection_engine_v4.py"
    )


    if vse4.is_file():

        try:

            source = read_text(
                vse4
            )


            table = symtable.symtable(
                source,
                str(vse4),
                "exec",
            )


            defined = {
                symbol.get_name()
                for symbol
                in table.get_symbols()
                if (
                    symbol.is_assigned()
                    or
                    symbol.is_imported()
                    or
                    symbol.is_namespace()
                )
            }


            builtin_names = set(
                dir(
                    builtins
                )
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


                        if name in builtin_names:

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


            out(
                "VSE4_UNRESOLVED_GLOBALS="
                +
                (
                    ",".join(
                        sorted(
                            unresolved
                        )
                    )
                    if unresolved
                    else
                    "NONE"
                )
            )


            if unresolved:

                critical(
                    "VSE4_UNRESOLVED_GLOBALS",
                    ",".join(
                        sorted(
                            unresolved
                        )
                    ),
                )

            else:

                passed(
                    "VSE4_GLOBAL_AUDIT"
                )


        except Exception as exc:

            critical(
                "VSE4_GLOBAL_AUDIT_EXCEPTION",
                f"{type(exc).__name__}: "
                f"{exc}",
            )


    # ========================================================
    # 10
    # ========================================================

    section(
        "10. VSE4 SELF TEST"
    )


    if vse4.is_file():

        try:

            env = os.environ.copy()

            env[
                "SAP_NO_PUBLISH"
            ] = "1"


            process = subprocess.run(
                [
                    sys.executable,
                    str(vse4),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=90,
            )


            out(
                "VSE4_SELF_TEST_STATUS=",
                process.returncode,
            )


            for line in (
                process.stdout
                .splitlines()
                [-60:]
            ):

                out(
                    "VSE4_TEST>",
                    line,
                )


            if process.returncode == 0:

                passed(
                    "VSE4_SELF_TEST"
                )

            else:

                critical(
                    "VSE4_SELF_TEST_FAILED",
                    f"status="
                    f"{process.returncode}",
                )


        except subprocess.TimeoutExpired:

            critical(
                "VSE4_SELF_TEST_TIMEOUT"
            )


        except Exception as exc:

            critical(
                "VSE4_SELF_TEST_EXCEPTION",
                f"{type(exc).__name__}: "
                f"{exc}",
            )


    # ========================================================
    # 11
    # ========================================================

    section(
        "11. VSE4 GEO / HARD-MISMATCH TEST"
    )


    if vse4.is_file():

        try:

            namespace = runpy.run_path(
                str(vse4),
                run_name="vse4_master_audit",
            )


            score_candidate = namespace.get(
                "score_candidate"
            )


            geo_hits = namespace.get(
                "geo_hits"
            )


            if not callable(
                score_candidate
            ):

                critical(
                    "VSE4_SCORE_CANDIDATE_MISSING"
                )

            else:

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


                if callable(
                    geo_hits
                ):

                    out(
                        "SCENE_GEO=",
                        sorted(
                            geo_hits(
                                scene
                            )
                        ),
                    )

                    out(
                        "WRONG_GEO=",
                        sorted(
                            geo_hits(
                                wrong[
                                    "title"
                                ]
                            )
                        ),
                    )

                    out(
                        "CORRECT_GEO=",
                        sorted(
                            geo_hits(
                                correct[
                                    "title"
                                ]
                            )
                        ),
                    )


                result_wrong = score_candidate(
                    wrong,
                    scene,
                    state,
                )


                result_correct = score_candidate(
                    correct,
                    scene,
                    state,
                )


                if isinstance(
                    result_wrong,
                    dict,
                ):

                    out(
                        "WRONG_HARD_MISMATCH=",
                        repr(
                            result_wrong.get(
                                "hard_mismatch"
                            )
                        ),
                    )

                    out(
                        "WRONG_EFFECTIVE=",
                        result_wrong.get(
                            "effective"
                        ),
                    )

                    out(
                        "WRONG_REASON=",
                        result_wrong.get(
                            "hard_reason"
                        )
                        or
                        result_wrong.get(
                            "reason"
                        ),
                    )


                if isinstance(
                    result_correct,
                    dict,
                ):

                    out(
                        "CORRECT_HARD_MISMATCH=",
                        repr(
                            result_correct.get(
                                "hard_mismatch"
                            )
                        ),
                    )

                    out(
                        "CORRECT_EFFECTIVE=",
                        result_correct.get(
                            "effective"
                        ),
                    )


                wrong_blocked = (
                    isinstance(
                        result_wrong,
                        dict,
                    )
                    and
                    result_wrong.get(
                        "hard_mismatch"
                    )
                    is True
                )


                correct_allowed = (
                    isinstance(
                        result_correct,
                        dict,
                    )
                    and
                    result_correct.get(
                        "hard_mismatch"
                    )
                    is False
                )


                if wrong_blocked:

                    passed(
                        "VSE4_GEO_WRONG_BLOCKED"
                    )

                else:

                    critical(
                        "VSE4_GEO_HARD_MISMATCH_FAIL",
                        "New York não foi bloqueado "
                        "para cena em São Paulo",
                    )


                if correct_allowed:

                    passed(
                        "VSE4_CORRECT_GEO_ALLOWED"
                    )

                else:

                    critical(
                        "VSE4_CORRECT_GEO_FALSE_BLOCK"
                    )


                if (
                    isinstance(
                        result_wrong,
                        dict,
                    )
                    and
                    isinstance(
                        result_correct,
                        dict,
                    )
                ):

                    wrong_score = (
                        result_wrong.get(
                            "effective"
                        )
                    )

                    correct_score = (
                        result_correct.get(
                            "effective"
                        )
                    )


                    if (
                        isinstance(
                            wrong_score,
                            (
                                int,
                                float,
                            ),
                        )
                        and
                        isinstance(
                            correct_score,
                            (
                                int,
                                float,
                            ),
                        )
                    ):

                        if (
                            correct_score
                            >
                            wrong_score
                        ):

                            passed(
                                "VSE4_CORRECT_RANKS_ABOVE_WRONG",
                                f"{correct_score} "
                                f"> {wrong_score}",
                            )

                        else:

                            critical(
                                "VSE4_WRONG_RANKS_TOO_HIGH",
                                f"wrong={wrong_score} "
                                f"correct={correct_score}",
                            )


        except Exception as exc:

            critical(
                "VSE4_DIRECT_TEST_EXCEPTION",
                f"{type(exc).__name__}: "
                f"{exc}",
            )

            out(
                traceback.format_exc()
            )


    # ========================================================
    # 12
    # ========================================================

    section(
        "12. PROVIDER ACQUISITION MAP"
    )


    provider_names = [
        "buscar_wikimedia_fotos",
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
    ]


    midia = (
        ROOT
        /
        "midia.py"
    )


    if midia.is_file():

        try:

            tree = ast.parse(
                read_text(
                    midia
                )
            )


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


            buscar = next(
                (
                    node
                    for node
                    in tree.body
                    if (
                        isinstance(
                            node,
                            (
                                ast.FunctionDef,
                                ast.AsyncFunctionDef,
                            ),
                        )
                        and
                        node.name
                        ==
                        "buscar_todos_candidatos"
                    )
                ),
                None,
            )


            calls = set()


            if buscar is None:

                critical(
                    "BUSCAR_TODOS_CANDIDATOS_MISSING"
                )

            else:

                for node in ast.walk(
                    buscar
                ):

                    if (
                        isinstance(
                            node,
                            ast.Call,
                        )
                        and
                        isinstance(
                            node.func,
                            ast.Name,
                        )
                    ):

                        calls.add(
                            node.func.id
                        )


            for name in provider_names:

                defined = (
                    name
                    in
                    definitions
                )

                called = (
                    name
                    in
                    calls
                )


                out(
                    f"{name}: "
                    f"DEFINED="
                    f"{'YES' if defined else 'NO'} "
                    f"CALLED="
                    f"{'YES' if called else 'NO'}"
                )


                if (
                    called
                    and
                    not defined
                ):

                    critical(
                        "BROKEN_PROVIDER_REFERENCE",
                        name,
                    )


                elif (
                    defined
                    and
                    not called
                ):

                    warning(
                        "PROVIDER_NOT_USED_IN_MAIN_POOL",
                        name,
                    )


        except Exception as exc:

            critical(
                "PROVIDER_AUDIT_EXCEPTION",
                f"{type(exc).__name__}: "
                f"{exc}",
            )


    # ========================================================
    # 13
    # ========================================================

    section(
        "13. VSE4 ACTIVE INTEGRATION"
    )


    if midia.is_file():

        text = read_text(
            midia
        )


        patterns = {
            "VSE4_MODULE":
                r"visual_selection_engine_v4",

            "VSE4_SCORE":
                r"\bscore_candidate\b",

            "COMMIT_LOCK":
                r"SCENE_COMMIT_LOCK"
                r"|visual_scene_commit_lock",

            "MUST_RESCUE":
                r"MUST_RESCUE"
                r"|visual_must_rescue",
        }


        for name, pattern in patterns.items():

            found = bool(
                re.search(
                    pattern,
                    text,
                    re.I,
                )
            )


            out(
                f"{name}="
                f"{'FOUND' if found else 'NOT_FOUND'}"
            )


            if (
                name.startswith(
                    "VSE4"
                )
                and
                not found
            ):

                warning(
                    "VSE4_NOT_ACTIVE_IN_MIDIA",
                    name,
                )


    # ========================================================
    # 14
    # ========================================================

    section(
        "14. RECENT MEDIA SETS"
    )


    image_root = (
        ROOT
        /
        "imagens"
    )


    media_dirs = []


    if image_root.is_dir():

        media_dirs = sorted(
            [
                path
                for path
                in image_root.glob(
                    "short_*"
                )
                if path.is_dir()
            ],
            key=lambda p:
                p.stat().st_mtime,
            reverse=True,
        )[:10]


    out(
        "MEDIA_SETS_SCANNED=",
        len(
            media_dirs
        ),
    )


    complete_ids = []


    for directory in media_dirs:

        short_id = (
            directory.name
            .removeprefix(
                "short_"
            )
        )


        problems = []

        total = 0


        for number in range(
            1,
            13,
        ):

            files = [
                path
                for path
                in directory.glob(
                    f"scene_{number:02d}.*"
                )
                if path.is_file()
            ]


            total += len(
                files
            )


            if len(files) != 1:

                problems.append(
                    f"scene_{number:02d}"
                    f":count={len(files)}"
                )


            for path in files:

                size = path.stat().st_size


                if size == 0:

                    problems.append(
                        f"{path.name}:ZERO"
                    )


                elif not media_signature_ok(
                    path
                ):

                    problems.append(
                        f"{path.name}:BAD_SIGNATURE"
                    )


        out(
            f"MEDIA_SET={short_id} "
            f"TOTAL={total} "
            f"PROBLEMS="
            +
            (
                ";".join(
                    problems
                )
                if problems
                else
                "NONE"
            )
        )


        if (
            total == 12
            and
            not problems
        ):

            complete_ids.append(
                short_id
            )

            passed(
                "MEDIA_12_OF_12",
                short_id,
            )

        else:

            warning(
                "MEDIA_SET_PROBLEM",
                f"{short_id}: "
                f"{problems}",
            )


    # ========================================================
    # 15
    # ========================================================

    section(
        "15. SCENE MAP JSON"
    )


    roteiro_dir = (
        ROOT
        /
        "roteiros"
    )


    scene_maps = []


    if roteiro_dir.is_dir():

        scene_maps = sorted(
            roteiro_dir.glob(
                "scene_map_*.json"
            ),
            key=lambda p:
                p.stat().st_mtime,
            reverse=True,
        )[:20]


    out(
        "SCENE_MAPS_SCANNED=",
        len(
            scene_maps
        ),
    )


    for path in scene_maps:

        try:

            data = json.loads(
                read_text(
                    path
                )
            )


            count = scene_count_from_json(
                data
            )


            out(
                f"{path.name}: "
                f"JSON=PASS "
                f"COUNT={count}"
            )


            if count not in {
                0,
                12,
            }:

                warning(
                    "SCENE_MAP_UNEXPECTED_COUNT",
                    f"{path.name}: "
                    f"{count}",
                )


        except Exception as exc:

            critical(
                "SCENE_MAP_INVALID_JSON",
                f"{path.name}: "
                f"{type(exc).__name__}: "
                f"{exc}",
            )


    # ========================================================
    # 16
    # ========================================================

    section(
        "16. RENDER INPUT CONSISTENCY"
    )


    for short_id in complete_ids[:5]:

        expected = {
            "AUDIO":
                ROOT
                /
                "audios"
                /
                f"short_{short_id}.mp3",

            "SCRIPT":
                ROOT
                /
                "roteiros"
                /
                f"short_{short_id}.txt",

            "ASS":
                ROOT
                /
                "videos"
                /
                f"short_{short_id}.ass",

            "VIDEO_BASE":
                ROOT
                /
                "temp"
                /
                short_id
                /
                "video_sem_audio.mp4",

            "FINAL":
                ROOT
                /
                "videos"
                /
                f"short_v6_{short_id}.mp4",
        }


        out(
            f"SHORT_ID={short_id}"
        )


        for label, path in expected.items():

            exists = (
                path.is_file()
                and
                path.stat().st_size > 0
            )


            out(
                f"  {label}="
                f"{'PASS' if exists else 'MISSING'} "
                f"{path}"
            )


            if (
                label
                in
                {
                    "AUDIO",
                    "SCRIPT",
                }
                and
                not exists
            ):

                warning(
                    "CORE_RENDER_INPUT_MISSING",
                    f"{short_id}:"
                    f"{label}",
                )


    # ========================================================
    # 17
    # ========================================================

    section(
        "17. RENDER GUARD SAFETY"
    )


    guard = (
        ROOT
        /
        "fresh_render_guard_v1.py"
    )


    if guard.is_file():

        text = read_text(
            guard
        )


        ass_protection = (
            ".ass" in text
            and
            "PROTECTED"
            in
            text.upper()
        )


        broad_rglob = (
            'rglob("*")'
            in
            text
            or
            "rglob('*')"
            in
            text
        )


        out(
            "ASS_PROTECTION_MARKER=",
            "YES"
            if ass_protection
            else
            "NO",
        )


        out(
            "BROAD_RGLOB=",
            "YES"
            if broad_rglob
            else
            "NO",
        )


        if ass_protection:

            passed(
                "RENDER_GUARD_ASS_PROTECTION"
            )

        else:

            warning(
                "RENDER_GUARD_ASS_PROTECTION_NOT_FOUND"
            )


        if broad_rglob:

            warning(
                "RENDER_GUARD_BROAD_RECURSION"
            )


    # ========================================================
    # 18
    # ========================================================

    section(
        "18. RECENT LOG ERRORS"
    )


    log_root = (
        ROOT
        /
        "logs"
        /
        "producao"
    )


    error_pattern = re.compile(
        r"Traceback"
        r"|NameError"
        r"|TypeError"
        r"|SyntaxError"
        r"|FileNotFoundError"
        r"|PermissionError"
        r"|RuntimeError"
        r"|AssertionError"
        r"|FATAL"
        r"|ERRO:"
        r"|ERROR:",
        re.I,
    )


    recent_logs = []


    if log_root.is_dir():

        for path in log_root.glob(
            "*"
        ):

            if not path.is_file():

                continue


            age_hours = (
                NOW
                -
                path.stat().st_mtime
            ) / 3600


            if age_hours <= 48:

                recent_logs.append(
                    path
                )


    recent_logs.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


    error_logs = []


    for path in recent_logs[:120]:

        try:

            text = read_text(
                path
            )

        except Exception:

            continue


        matches = error_pattern.findall(
            text
        )


        if matches:

            error_logs.append(
                (
                    path,
                    len(matches),
                )
            )


    for path, count in error_logs[:40]:

        out(
            f"ERROR_LOG "
            f"matches={count} "
            f"file={path.name}"
        )


    out(
        "RECENT_LOGS_SCANNED=",
        min(
            len(recent_logs),
            120,
        ),
    )


    out(
        "RECENT_LOGS_WITH_ERRORS=",
        len(
            error_logs
        ),
    )


    if error_logs:

        warning(
            "RECENT_ERROR_LOGS",
            len(
                error_logs
            ),
        )

    else:

        passed(
            "RECENT_LOG_SCAN"
        )


    # ========================================================
    # 19
    # ========================================================

    section(
        "19. ZERO-BYTE / TINY FILES"
    )


    scan_dirs = [
        ROOT / "imagens",
        ROOT / "audios",
        ROOT / "videos",
        ROOT / "roteiros",
        ROOT / "manifests",
    ]


    extensions = {
        ".mp4",
        ".mp3",
        ".wav",
        ".ass",
        ".srt",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".json",
        ".txt",
    }


    zero_files = []

    tiny_media = []


    for base in scan_dirs:

        if not base.is_dir():

            continue


        for path in base.rglob(
            "*"
        ):

            if not path.is_file():

                continue


            if (
                path.suffix.casefold()
                not in
                extensions
            ):

                continue


            try:

                size = path.stat().st_size

            except OSError:

                continue


            if size == 0:

                zero_files.append(
                    path
                )


            elif (
                path.suffix.casefold()
                in
                {
                    ".mp4",
                    ".mp3",
                    ".wav",
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp",
                }
                and
                size < 128
            ):

                tiny_media.append(
                    (
                        path,
                        size,
                    )
                )


    for path in zero_files[:50]:

        out(
            "ZERO_BYTE=",
            path.relative_to(
                ROOT
            ),
        )


    for path, size in tiny_media[:50]:

        out(
            "TINY_MEDIA=",
            size,
            path.relative_to(
                ROOT
            ),
        )


    out(
        "ZERO_BYTE_COUNT=",
        len(
            zero_files
        ),
    )


    out(
        "TINY_MEDIA_COUNT=",
        len(
            tiny_media
        ),
    )


    if zero_files:

        warning(
            "ZERO_BYTE_FILES",
            len(
                zero_files
            ),
        )


    if tiny_media:

        warning(
            "TINY_MEDIA_FILES",
            len(
                tiny_media
            ),
        )


    if (
        not zero_files
        and
        not tiny_media
    ):

        passed(
            "PRODUCTION_FILE_SIZE_SANITY"
        )


    # ========================================================
    # 20
    # ========================================================

    section(
        "20. RECENT JSON VALIDITY"
    )


    json_files = []


    for base in (
        ROOT / "roteiros",
        ROOT / "manifests",
        ROOT / "temp",
    ):

        if base.is_dir():

            json_files.extend(
                path
                for path
                in base.rglob(
                    "*.json"
                )
                if path.is_file()
            )


    json_files.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


    invalid_json = []


    for path in json_files[:150]:

        try:

            json.loads(
                read_text(
                    path
                )
            )

        except Exception as exc:

            invalid_json.append(
                (
                    path,
                    type(exc).__name__,
                    str(exc),
                )
            )


    out(
        "JSON_FILES_SCANNED=",
        min(
            len(json_files),
            150,
        ),
    )


    for path, error_type, error in invalid_json[:30]:

        out(
            "INVALID_JSON=",
            path.relative_to(
                ROOT
            ),
            error_type,
            error,
        )


    if invalid_json:

        warning(
            "INVALID_RECENT_JSON",
            len(
                invalid_json
            ),
        )

    else:

        passed(
            "RECENT_JSON_VALIDITY"
        )


    # ========================================================
    # 21
    # ========================================================

    section(
        "21. CORE HASHES"
    )


    for name in required:

        path = (
            ROOT
            /
            name
        )


        if not path.is_file():

            continue


        try:

            out(
                "SHA256",
                name,
                file_sha256(
                    path
                ),
            )

        except Exception as exc:

            warning(
                "HASH_FAILURE",
                f"{name}: {exc}",
            )


    # ========================================================
    # 22
    # ========================================================

    section(
        "22. FINAL SUMMARY"
    )


    out(
        "PASS_COUNT=",
        len(
            PASSES
        ),
    )


    out(
        "WARNING_COUNT=",
        len(
            WARNINGS
        ),
    )


    out(
        "CRITICAL_COUNT=",
        len(
            CRITICAL
        ),
    )


    if WARNINGS:

        print()
        print(
            "===== WARNINGS ====="
        )

        for code, detail in WARNINGS:

            out(
                "WARNING_ITEM=",
                code,
                detail,
            )


    if CRITICAL:

        print()
        print(
            "===== CRITICALS ====="
        )

        for code, detail in CRITICAL:

            out(
                "CRITICAL_ITEM=",
                code,
                detail,
            )


    if CRITICAL:

        status = "FAIL"

    elif WARNINGS:

        status = "WARN"

    else:

        status = "PASS"


    print()
    out(
        "MASTER_AUDIT_STATUS=",
        status,
    )

    out(
        "REPORT=",
        REPORT,
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
        "CORE_FILES_MODIFIED=NO"
    )

    out(
        "TERMUX_CONTINUA_ABERTO=SIM"
    )


finally:

    sys.stdout = original_stdout

    report_handle.close()


if CRITICAL:

    raise SystemExit(2)

raise SystemExit(0)
