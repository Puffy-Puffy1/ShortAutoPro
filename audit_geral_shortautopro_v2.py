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
import tempfile
import time
from collections import Counter
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"
REPORT = ROOT / "temp" / "AUDIT_GERAL_SHORTAUTOPRO_V2.txt"
JSON_REPORT = ROOT / "temp" / "AUDIT_GERAL_SHORTAUTOPRO_V2.json"

REPORT.parent.mkdir(parents=True, exist_ok=True)


PASS = []
WARN = []
FAIL = []
INFO = []


CORE_FILES = (
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
)


RUNTIME_PY = (
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
)


VISUAL_PROVIDERS = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
)


MEDIA_SUFFIXES = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
}


def emit(text=""):
    print(text)


def pass_(message):
    PASS.append(message)
    emit(f"PASS | {message}")


def warn(message):
    WARN.append(message)
    emit(f"WARN | {message}")


def fail(message):
    FAIL.append(message)
    emit(f"FAIL | {message}")


def info(message):
    INFO.append(message)
    emit(f"INFO | {message}")


def sha256(path: Path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def section(title):
    emit()
    emit("=" * 72)
    emit(title)
    emit("=" * 72)


# ============================================================
# 1. PROJECT ROOT / CORE FILES
# ============================================================

section("1. PROJECT / CORE FILES")

if ROOT.is_dir():
    pass_(f"PROJECT_ROOT={ROOT}")
else:
    fail(f"PROJECT_ROOT_MISSING={ROOT}")


for name in CORE_FILES:

    path = ROOT / name

    if path.is_file():
        pass_(f"CORE_FILE={name}")
    else:
        warn(f"CORE_FILE_MISSING={name}")


# ============================================================
# 2. CORE HASHES
# ============================================================

section("2. CORE HASHES")

for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
):

    path = ROOT / name

    if path.is_file():
        info(
            f"HASH {name}={sha256(path)}"
        )


# ============================================================
# 3. ROOT PYTHON COMPILE
#
# Não executa módulos.
# ============================================================

section("3. PYTHON COMPILE")

compile_bad = []

for path in sorted(ROOT.glob("*.py")):

    try:
        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        compile_bad.append(
            (
                path.name,
                str(exc),
            )
        )


if not compile_bad:
    pass_("ROOT_PYTHON_COMPILE=PASS")
else:

    for name, exc in compile_bad:
        fail(
            f"PYTHON_COMPILE {name}: {exc}"
        )


# ============================================================
# 4. SHELL SYNTAX
# ============================================================

section("4. SHELL SYNTAX")

shell_bad = []

for path in sorted(ROOT.glob("*.sh")):

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        shell_bad.append(
            (
                path.name,
                result.stderr.strip(),
            )
        )


if not shell_bad:
    pass_("ROOT_SHELL_SYNTAX=PASS")
else:

    for name, err in shell_bad:
        fail(
            f"SHELL_SYNTAX {name}: {err}"
        )


# ============================================================
# 5. SHORT ID RESOLUTION
# ============================================================

section("5. ACTIVE SHORT RESOLUTION")


def scene_files_for(directory: Path):

    result = {}

    for number in range(1, 13):

        matches = []

        for path in directory.glob(
            f"scene_{number:02d}.*"
        ):

            if (
                path.is_file()
                and path.suffix.lower()
                in MEDIA_SUFFIXES
            ):
                matches.append(path)

        result[number] = sorted(matches)

    return result


def media_score(directory: Path):

    scene_map = scene_files_for(directory)

    exact = sum(
        1
        for values in scene_map.values()
        if len(values) == 1
    )

    total = sum(
        len(values)
        for values in scene_map.values()
    )

    return (
        exact,
        total,
        directory.stat().st_mtime,
    )


def resolve_short_id():

    explicit = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if explicit:

        candidate = (
            ROOT
            / "imagens"
            / f"short_{explicit}"
        )

        if candidate.is_dir():

            return (
                explicit,
                "environment",
            )

        warn(
            "ENV_SHORT_ID_HAS_NO_MEDIA_DIR="
            + explicit
        )


    media_root = ROOT / "imagens"

    if not media_root.is_dir():
        return None, "none"


    candidates = [
        p
        for p in media_root.glob("short_*")
        if p.is_dir()
    ]


    if not candidates:
        return None, "none"


    candidates.sort(
        key=media_score,
        reverse=True,
    )


    best = candidates[0]

    return (
        best.name.removeprefix("short_"),
        "best_media_directory",
    )


SHORT_ID, SHORT_SOURCE = resolve_short_id()


if SHORT_ID:

    pass_(
        f"ACTIVE_SHORT_ID={SHORT_ID}"
    )

    info(
        f"SHORT_ID_SOURCE={SHORT_SOURCE}"
    )

else:

    warn("ACTIVE_SHORT_ID=NOT_FOUND")


# ============================================================
# 6. MEDIA STRUCTURE
# ============================================================

section("6. MEDIA STRUCTURE")


MEDIA_FP = None
MEDIA_TOTAL = 0


if SHORT_ID:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{SHORT_ID}"
    )


    scenes = scene_files_for(
        media_dir
    )


    bad = []

    fingerprint_items = []


    for number in range(1, 13):

        files = scenes[number]

        MEDIA_TOTAL += len(files)

        if len(files) != 1:

            bad.append(
                (
                    number,
                    len(files),
                )
            )

            continue


        path = files[0]

        digest = sha256(path)

        fingerprint_items.append(
            (
                number,
                path.name,
                digest,
                path.stat().st_size,
            )
        )

        info(
            f"SCENE_{number:02d}="
            f"{path.name} "
            f"{path.stat().st_size} "
            f"{digest}"
        )


    if not bad and MEDIA_TOTAL == 12:

        pass_("MEDIA_STRUCTURE=12_OF_12")

    else:

        fail(
            f"MEDIA_STRUCTURE_BAD={bad}"
        )


    if fingerprint_items:

        blob = json.dumps(
            fingerprint_items,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        MEDIA_FP = hashlib.sha256(
            blob
        ).hexdigest()

        info(
            f"MEDIA_FINGERPRINT={MEDIA_FP}"
        )


else:

    warn(
        "MEDIA_STRUCTURE=SKIPPED_NO_SHORT_ID"
    )


emit(f"MEDIA_TOTAL={MEDIA_TOTAL}")


# ============================================================
# 7. OUTPUT VIDEO
# ============================================================

section("7. FINAL VIDEO")


FINAL_SHA = None


if SHORT_ID:

    final = (
        ROOT
        / "videos"
        / f"short_v6_{SHORT_ID}.mp4"
    )


    if final.is_file() and final.stat().st_size > 0:

        FINAL_SHA = sha256(final)

        pass_(
            f"FINAL_VIDEO_EXISTS={final.name}"
        )

        info(
            f"FINAL_BYTES={final.stat().st_size}"
        )

        info(
            f"FINAL_SHA256={FINAL_SHA}"
        )


        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size,bit_rate",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,r_frame_rate",
                "-of",
                "json",
                str(final),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


        if probe.returncode == 0:

            try:
                metadata = json.loads(
                    probe.stdout
                )

                streams = metadata.get(
                    "streams",
                    [],
                )

                video_streams = [
                    s
                    for s in streams
                    if s.get("codec_type")
                    == "video"
                ]

                if video_streams:

                    video = video_streams[0]

                    width = video.get(
                        "width"
                    )

                    height = video.get(
                        "height"
                    )

                    if (
                        width == 1080
                        and
                        height == 1920
                    ):

                        pass_(
                            "FINAL_RESOLUTION=1080x1920"
                        )

                    else:

                        warn(
                            f"FINAL_RESOLUTION="
                            f"{width}x{height}"
                        )

                else:

                    fail(
                        "FINAL_VIDEO_STREAM=MISSING"
                    )


            except Exception as exc:

                warn(
                    f"FFPROBE_JSON_ERROR={exc}"
                )

        else:

            warn(
                "FFPROBE_FAILED"
            )


    else:

        warn(
            f"FINAL_VIDEO_NOT_FOUND_FOR={SHORT_ID}"
        )


# ============================================================
# 8. VSE4 STATIC / RUNTIME
# ============================================================

section("8. VISUAL SELECTION ENGINE V4")


vse4 = ROOT / "visual_selection_engine_v4.py"


if vse4.is_file():

    result = subprocess.run(
        [
            "python",
            str(vse4),
        ],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    emit(
        f"VSE4_SELF_TEST_STATUS="
        f"{result.returncode}"
    )


    if result.returncode == 0:

        pass_(
            "VSE4_SELF_TEST=PASS"
        )

    else:

        fail(
            "VSE4_SELF_TEST=FAIL"
        )

        emit(
            result.stderr[-3000:]
        )


    try:

        source = vse4.read_text(
            encoding="utf-8",
        )

        table = symtable.symtable(
            source,
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

                    if name in builtin_names:
                        continue

                    unresolved.add(
                        name
                    )

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

            pass_(
                "VSE4_UNRESOLVED_GLOBALS=NONE"
            )


    except Exception as exc:

        fail(
            f"VSE4_GLOBAL_AUDIT_ERROR={exc}"
        )


else:

    fail(
        "VSE4_FILE=MISSING"
    )


# ============================================================
# 9. TOP-LEVEL DUPLICATE DEFINITIONS
#
# Diferente do V1:
# não conta funções internas.
# ============================================================

section("9. TOP-LEVEL DUPLICATE DEFINITIONS")


for name in RUNTIME_PY:

    path = ROOT / name

    if not path.is_file():
        continue


    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception as exc:

        fail(
            f"AST_PARSE {name}: {exc}"
        )

        continue


    defs = [
        node.name
        for node in tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]


    duplicates = {
        key: count
        for key, count
        in Counter(defs).items()
        if count > 1
    }


    if duplicates:

        warn(
            f"TOP_LEVEL_DUPLICATE_DEFS "
            f"{name}: {duplicates}"
        )

    else:

        pass_(
            f"NO_TOP_LEVEL_DUPLICATES={name}"
        )


# ============================================================
# 10. VSE4 ACTIVE DEFINITION MAP
# ============================================================

section("10. VSE4 ACTIVE DEFINITION MAP")


if vse4.is_file():

    tree = ast.parse(
        vse4.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )


    locations = {}

    for node in tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            locations.setdefault(
                node.name,
                [],
            ).append(
                node.lineno
            )


    for function in (
        "candidate_text",
        "tokens",
        "score_candidate",
        "_vse414_lifestyle_penalty",
        "geo_hits",
    ):

        lines = locations.get(
            function,
            [],
        )

        if lines:

            info(
                f"VSE4_DEF {function}="
                + ",".join(
                    str(x)
                    for x in lines
                )
                +
                f" ACTIVE={lines[-1]}"
            )


# ============================================================
# 11. PROVIDER ACQUISITION STRUCTURE
#
# AST somente; NÃO importa midia.py.
# ============================================================

section("11. PROVIDER ACQUISITION")


midia = ROOT / "midia.py"


if midia.is_file():

    tree = ast.parse(
        midia.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )

    defs = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }


    for function in VISUAL_PROVIDERS:

        if function in defs:

            pass_(
                f"PROVIDER_FUNCTION={function}"
            )

        else:

            warn(
                f"PROVIDER_FUNCTION_MISSING={function}"
            )


# ============================================================
# 12. VISUAL ENGINE REFERENCES
# ============================================================

section("12. VISUAL ENGINE REFERENCES")


legacy_names = (
    "visual_selection_engine_v2",
    "visual_selection_final_gate_v3",
    "visual_scene_commit_lock_v1",
    "visual_must_rescue_v1",
)


active_files = (
    "midia.py",
    "media_diversity_guard_v1.py",
)


legacy_hits = []


for name in active_files:

    path = ROOT / name

    if not path.is_file():
        continue

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for legacy in legacy_names:

        count = text.count(
            legacy
        )

        if count:

            legacy_hits.append(
                (
                    name,
                    legacy,
                    count,
                )
            )

            info(
                f"LEGACY_REFERENCE "
                f"{name} "
                f"{legacy}={count}"
            )


    vse4_count = text.count(
        "visual_selection_engine_v4"
    )

    if vse4_count:

        pass_(
            f"VSE4_REFERENCE "
            f"{name}={vse4_count}"
        )

    else:

        info(
            f"VSE4_REFERENCE "
            f"{name}=0"
        )


emit(
    "LEGACY_REFERENCE_COUNT="
    + str(
        sum(
            item[2]
            for item in legacy_hits
        )
    )
)


if legacy_hits:

    warn(
        "LEGACY_VISUAL_REFERENCES_PRESENT"
    )


# ============================================================
# 13. HARDCODED SHORT IDs
#
# Apenas código runtime ativo.
# Auditorias/canários não entram no WARN.
# ============================================================

section("13. RUNTIME HARDCODED SHORT IDS")


short_pattern = re.compile(
    r"20\d{2}-\d{2}-\d{2}_\d{4}"
)


runtime_hardcoded = []


for name in RUNTIME_PY:

    path = ROOT / name

    if not path.is_file():
        continue

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    ids = sorted(
        set(
            short_pattern.findall(
                text
            )
        )
    )

    if ids:

        runtime_hardcoded.append(
            (
                name,
                ids,
            )
        )

        warn(
            f"RUNTIME_HARDCODED_SHORT_ID "
            f"{name}: {ids}"
        )


if not runtime_hardcoded:

    pass_(
        "RUNTIME_HARDCODED_SHORT_ID=NONE"
    )


# ============================================================
# 14. DANGEROUS DELETE AUDIT
#
# V2 não escaneia arquivos audit_*.
#
# Só literal /, ~ ou $HOME vira FAIL.
# shutil.rmtree(ROOT) não é automaticamente classificado
# como destruição do sistema.
# ============================================================

section("14. DANGEROUS DELETE AUDIT")


dangerous = []


for path in ROOT.glob("*.sh"):

    if path.name.startswith(
        (
            "audit_",
            "general_audit",
        )
    ):
        continue


    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        stripped = line.strip()

        if (
            not stripped
            or stripped.startswith("#")
        ):
            continue


        pattern = re.search(
            r"(^|[;&|]\s*)"
            r"rm\s+"
            r"(?:-[^\s]*r[^\s]*f[^\s]*|"
            r"-[^\s]*f[^\s]*r[^\s]*)"
            r"\s+"
            r"(?:/|\$HOME|~)"
            r"(?:\s|$)",
            stripped,
        )

        if pattern:

            dangerous.append(
                f"{path.name}:{number}: "
                f"{stripped}"
            )


for path in ROOT.glob("*.py"):

    if path.name.startswith(
        (
            "audit_",
            "general_audit",
        )
    ):
        continue


    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception:
        continue


    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue


        fn = ""

        try:
            fn = ast.unparse(
                node.func
            )
        except Exception:
            pass


        if fn not in (
            "shutil.rmtree",
            "os.system",
        ):
            continue


        if not node.args:
            continue


        arg = node.args[0]


        if (
            isinstance(arg, ast.Constant)
            and isinstance(arg.value, str)
            and arg.value.strip()
            in {
                "/",
                "~",
                "$HOME",
            }
        ):

            dangerous.append(
                f"{path.name}:{node.lineno}: "
                f"{fn}({arg.value!r})"
            )


if dangerous:

    for item in dangerous:

        fail(
            "DANGEROUS_DELETE="
            + item
        )

else:

    pass_(
        "DANGEROUS_DELETE_LITERAL_ROOT=NONE"
    )


# ============================================================
# 15. RENDER GUARD FUNCTIONAL TEST
# ============================================================

section("15. RENDER GUARD FUNCTIONAL TEST")


guard_path = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard_path.is_file():

    sid = (
        "AUDIT_GUARD_"
        + str(os.getpid())
        + "_"
        + str(int(time.time()))
    )


    temp_dir = ROOT / "temp" / sid
    video_ass = (
        ROOT
        / "videos"
        / f"short_{sid}.ass"
    )

    final_mp4 = (
        ROOT
        / "videos"
        / f"short_v6_{sid}.mp4"
    )

    temp_mp4 = (
        temp_dir
        / "video_sem_audio.mp4"
    )

    audio_guard = (
        temp_dir
        / "audit_audio.mp3"
    )


    try:

        temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        video_ass.parent.mkdir(
            parents=True,
            exist_ok=True,
        )


        video_ass.write_text(
            "AUDIT_ASS_PROTECTED",
            encoding="utf-8",
        )

        final_mp4.write_bytes(
            b"AUDIT_FINAL"
        )

        temp_mp4.write_bytes(
            b"AUDIT_TEMP_VIDEO"
        )

        audio_guard.write_bytes(
            b"AUDIT_AUDIO_PROTECTED"
        )


        test_code = f"""
import os
os.environ["SHORT_ID"] = {sid!r}
from fresh_render_guard_v1 import clean
clean({sid!r})
"""


        result = subprocess.run(
            [
                "python",
                "-c",
                test_code,
            ],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )


        if result.returncode != 0:

            fail(
                "RENDER_GUARD_EXECUTION=FAIL "
                + result.stderr.strip()
            )

        else:

            ass_preserved = (
                video_ass.is_file()
            )

            audio_preserved = (
                audio_guard.is_file()
            )

            final_removed = (
                not final_mp4.exists()
            )

            temp_removed = (
                not temp_mp4.exists()
            )


            if ass_preserved:
                pass_(
                    "RENDER_GUARD_ASS_PROTECTION=PASS"
                )
            else:
                fail(
                    "RENDER_GUARD_ASS_PROTECTION=FAIL"
                )


            if audio_preserved:
                pass_(
                    "RENDER_GUARD_AUDIO_PROTECTION=PASS"
                )
            else:
                fail(
                    "RENDER_GUARD_AUDIO_PROTECTION=FAIL"
                )


            if (
                final_removed
                and temp_removed
            ):

                pass_(
                    "RENDER_GUARD_VIDEO_CLEAN=PASS"
                )

            else:

                fail(
                    "RENDER_GUARD_VIDEO_CLEAN=FAIL"
                )


    finally:

        try:
            video_ass.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        try:
            final_mp4.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        try:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True,
            )
        except Exception:
            pass


else:

    warn(
        "RENDER_GUARD_FILE=MISSING"
    )


# ============================================================
# 16. PROVENANCE / DIVERSITY FOUNDATION
# ============================================================

section("16. MEDIA FOUNDATION")


for name in (
    "media_provenance_capture_v1.py",
    "media_diversity_guard_v1.py",
):

    if (ROOT / name).is_file():
        pass_(
            f"MEDIA_FOUNDATION={name}"
        )
    else:
        warn(
            f"MEDIA_FOUNDATION_MISSING={name}"
        )


# ============================================================
# 17. AUDIT SCRIPT SELF-SAFETY
#
# Garante que o auditor V2 não classifica suas próprias
# strings de busca como falhas do projeto.
# ============================================================

section("17. AUDITOR SELF-CHECK")


self_name = Path(__file__).name

if not any(
    self_name in item
    for item in dangerous
):

    pass_(
        "AUDITOR_SELF_FALSE_POSITIVE=NONE"
    )

else:

    fail(
        "AUDITOR_SELF_FALSE_POSITIVE=PRESENT"
    )


# ============================================================
# 18. SUMMARY
# ============================================================

section("18. GENERAL SUMMARY")


status = (
    "FAIL"
    if FAIL
    else
    (
        "WARN"
        if WARN
        else
        "PASS"
    )
)


summary = {
    "audit_version":
        "2.0",

    "short_id":
        SHORT_ID,

    "short_id_source":
        SHORT_SOURCE,

    "media_total":
        MEDIA_TOTAL,

    "media_fingerprint":
        MEDIA_FP,

    "final_sha256":
        FINAL_SHA,

    "pass_count":
        len(PASS),

    "warn_count":
        len(WARN),

    "fail_count":
        len(FAIL),

    "status":
        status,

    "passes":
        PASS,

    "warnings":
        WARN,

    "failures":
        FAIL,
}


emit(
    f"ACTIVE_SHORT_ID={SHORT_ID}"
)

emit(
    f"MEDIA_TOTAL={MEDIA_TOTAL}"
)

emit(
    f"MEDIA_FINGERPRINT={MEDIA_FP}"
)

emit(
    f"FINAL_SHA256={FINAL_SHA}"
)

emit(
    f"PASS_COUNT={len(PASS)}"
)

emit(
    f"WARN_COUNT={len(WARN)}"
)

emit(
    f"FAIL_COUNT={len(FAIL)}"
)

emit(
    f"GENERAL_AUDIT_STATUS={status}"
)


for message in FAIL:
    emit(
        f"FAIL={message}"
    )


for message in WARN:
    emit(
        f"WARN={message}"
    )


JSON_REPORT.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


emit()
emit(
    f"JSON_REPORT={JSON_REPORT}"
)

emit(
    "NETWORK_EXECUTED=NO"
)

emit(
    "MEDIA_DOWNLOADED=NO"
)

emit(
    "VIDEO_RENDERED=NO"
)

emit(
    "PRODUCTION_MEDIA_MODIFIED=NO"
)

emit(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
