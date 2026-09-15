#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import ast
import hashlib
import json
import os
import re
import subprocess
import symtable
import time
import builtins


ROOT = Path.home() / "ShortAutoPro"

TEMP = ROOT / "temp"
LOGS = ROOT / "logs" / "producao"
VIDEOS = ROOT / "videos"
AUDIOS = ROOT / "audios"
IMAGENS = ROOT / "imagens"
ROTEIROS = ROOT / "roteiros"
MANIFESTS = ROOT / "manifests"

TEMP.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT = TEMP / "SAP_GENERAL_AUDIT_V3.txt"
JSON_REPORT = TEMP / "SAP_GENERAL_AUDIT_V3.json"


LINES = []

RESULTS = {
    "errors": [],
    "warnings": [],
    "passes": [],
    "info": [],
}


def emit(*parts):

    text = " ".join(
        str(x)
        for x in parts
    )

    print(text)
    LINES.append(text)


def section(title):

    emit()
    emit("=" * 72)
    emit(title)
    emit("=" * 72)


def add_pass(code, detail=""):

    RESULTS["passes"].append(
        {
            "code": code,
            "detail": detail,
        }
    )

    emit(
        f"PASS | {code}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def add_warn(code, detail=""):

    RESULTS["warnings"].append(
        {
            "code": code,
            "detail": detail,
        }
    )

    emit(
        f"WARN | {code}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def add_error(code, detail=""):

    RESULTS["errors"].append(
        {
            "code": code,
            "detail": detail,
        }
    )

    emit(
        f"ERROR | {code}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def add_info(code, detail=""):

    RESULTS["info"].append(
        {
            "code": code,
            "detail": detail,
        }
    )

    emit(
        f"INFO | {code}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def sha256(path):

    path = Path(path)

    if not path.is_file():
        return None

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def read_text(path):

    try:
        return Path(path).read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def parse_python(path):

    try:

        source = read_text(path)

        tree = ast.parse(
            source,
            filename=str(path),
        )

        return source, tree, None

    except Exception as exc:

        return "", None, exc


def compile_source(path):

    try:

        source = Path(path).read_text(
            encoding="utf-8",
            errors="replace",
        )

        compile(
            source,
            str(path),
            "exec",
        )

        return True, ""

    except Exception as exc:

        return (
            False,
            f"{type(exc).__name__}: {exc}",
        )


def shell_syntax(path):

    try:

        r = subprocess.run(
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

        return (
            r.returncode == 0,
            (
                r.stderr.strip()
                or
                r.stdout.strip()
            ),
        )

    except Exception as exc:

        return (
            False,
            f"{type(exc).__name__}: {exc}",
        )


def scene_files(directory):

    result = {}

    for number in range(1, 13):

        matches = []

        for ext in (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
        ):

            matches.extend(
                directory.glob(
                    f"scene_{number:02d}{ext}"
                )
            )

        result[number] = sorted(
            matches
        )

    return result


def valid_media_set(directory):

    if not directory.is_dir():
        return False

    scenes = scene_files(
        directory
    )

    return (
        len(scenes) == 12
        and
        all(
            len(files) == 1
            for files in scenes.values()
        )
    )


def discover_short():

    requested = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if requested:

        candidate = (
            IMAGENS
            /
            f"short_{requested}"
        )

        if valid_media_set(
            candidate
        ):
            return (
                requested,
                candidate,
                "ENV",
            )

    candidates = []

    if IMAGENS.is_dir():

        for path in IMAGENS.glob(
            "short_*"
        ):

            if not path.is_dir():
                continue

            if not valid_media_set(
                path
            ):
                continue

            try:
                mtime = path.stat().st_mtime
            except Exception:
                mtime = 0

            candidates.append(
                (
                    mtime,
                    path,
                )
            )

    if not candidates:
        return (
            "",
            None,
            "NONE",
        )

    candidates.sort(
        reverse=True,
        key=lambda x: x[0],
    )

    directory = candidates[0][1]

    sid = directory.name.removeprefix(
        "short_"
    )

    return (
        sid,
        directory,
        "LATEST_VALID",
    )


def duplicate_defs(tree):

    counter = Counter()

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            counter[node.name] += 1

    return {
        name: count
        for name, count in counter.items()
        if count > 1
    }


def unresolved_globals(path):

    source = read_text(path)

    try:

        table = symtable.symtable(
            source,
            str(path),
            "exec",
        )

    except Exception as exc:

        return {
            f"SYMTABLE_ERROR:{exc}"
        }

    module_defined = set()

    for symbol in table.get_symbols():

        if (
            symbol.is_assigned()
            or
            symbol.is_imported()
            or
            symbol.is_namespace()
        ):
            module_defined.add(
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

                if name in module_defined:
                    continue

                if name in builtin_names:
                    continue

                unresolved.add(
                    name
                )

            walk(child)

    walk(table)

    return unresolved


def run_safe_python(script, timeout=30):

    try:

        r = subprocess.run(
            [
                "python",
                str(script),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "SAP_NO_PUBLISH": "1",
            },
        )

        return (
            r.returncode,
            r.stdout,
        )

    except subprocess.TimeoutExpired:

        return (
            124,
            "TIMEOUT",
        )

    except Exception as exc:

        return (
            125,
            f"{type(exc).__name__}: {exc}",
        )


def grep_count(text, pattern):

    return len(
        re.findall(
            pattern,
            text,
            flags=re.I | re.M,
        )
    )


# ============================================================
# BEFORE-HASH
# ============================================================

core_files = [
    ROOT / "midia.py",
    ROOT / "video.py",
    ROOT / "v6.py",
    ROOT / "gerar_short.sh",
]

before_hashes = {
    str(path.relative_to(ROOT)):
        sha256(path)
    for path in core_files
}


section(
    "1. PROJECT / ACTIVE SHORT"
)

emit(
    f"ROOT={ROOT}"
)

emit(
    f"DATE={time.strftime('%Y-%m-%d %H:%M:%S')}"
)

sid, media_dir, selection = discover_short()

emit(
    f"ACTIVE_SHORT_ID={sid or 'NONE'}"
)

emit(
    f"ACTIVE_SHORT_SELECTION={selection}"
)

if media_dir:

    emit(
        f"ACTIVE_MEDIA_DIR={media_dir}"
    )

    add_pass(
        "ACTIVE_MEDIA_SET_FOUND"
    )

else:

    add_warn(
        "ACTIVE_MEDIA_SET_NOT_FOUND",
        "Nenhum conjunto completo de 12 cenas.",
    )


# ============================================================
# MEDIA
# ============================================================

section(
    "2. MEDIA STRUCTURE"
)

if media_dir:

    scenes = scene_files(
        media_dir
    )

    type_counter = Counter()
    total = 0
    bad = 0

    hashes = Counter()

    for number in range(
        1,
        13,
    ):

        files = scenes[
            number
        ]

        total += len(files)

        if len(files) != 1:

            bad += 1

            add_error(
                f"SCENE_{number:02d}_COUNT",
                f"count={len(files)}",
            )

            continue

        path = files[0]

        kind = (
            "video"
            if path.suffix.lower()
            in (
                ".mp4",
                ".mov",
                ".webm",
            )
            else
            "photo"
        )

        type_counter[kind] += 1

        digest = sha256(
            path
        )

        if digest:
            hashes[digest] += 1

        emit(
            f"SCENE_{number:02d}=PASS "
            f"type={kind} "
            f"bytes={path.stat().st_size} "
            f"sha256={digest[:16] if digest else 'NA'} "
            f"file={path.name}"
        )

    emit(
        f"MEDIA_TOTAL={total}"
    )

    emit(
        f"MEDIA_TYPES={dict(type_counter)}"
    )

    if bad == 0 and total == 12:

        add_pass(
            "MEDIA_STRUCTURE",
            "12/12 cenas, exatamente um arquivo por cena.",
        )

    else:

        add_error(
            "MEDIA_STRUCTURE",
            f"total={total} invalid_scenes={bad}",
        )

    duplicate_media = [
        digest
        for digest, count in hashes.items()
        if count > 1
    ]

    if duplicate_media:

        add_warn(
            "DUPLICATE_MEDIA_HASHES",
            f"duplicate_hash_groups={len(duplicate_media)}",
        )

    else:

        add_pass(
            "NO_EXACT_MEDIA_DUPLICATES"
        )


# ============================================================
# ROOT PYTHON COMPILE
# ============================================================

section(
    "3. ACTIVE ROOT PYTHON SYNTAX"
)

python_files = sorted(
    ROOT.glob("*.py")
)

compile_failures = []

for path in python_files:

    ok, detail = compile_source(
        path
    )

    if ok:

        emit(
            f"PY_COMPILE=PASS | {path.name}"
        )

    else:

        compile_failures.append(
            path.name
        )

        add_error(
            "PY_COMPILE_FAIL",
            f"{path.name} | {detail}",
        )

emit(
    f"ROOT_PYTHON_FILES={len(python_files)}"
)

emit(
    f"ROOT_PYTHON_COMPILE_FAILURES={len(compile_failures)}"
)

if not compile_failures:

    add_pass(
        "ALL_ROOT_PYTHON_COMPILE"
    )


# ============================================================
# SHELL
# ============================================================

section(
    "4. SHELL SYNTAX"
)

shell_files = sorted(
    ROOT.glob("*.sh")
)

shell_failures = []

for path in shell_files:

    ok, detail = shell_syntax(
        path
    )

    if ok:

        emit(
            f"SHELL_SYNTAX=PASS | {path.name}"
        )

    else:

        shell_failures.append(
            path.name
        )

        add_error(
            "SHELL_SYNTAX_FAIL",
            f"{path.name} | {detail}",
        )

if not shell_failures:

    add_pass(
        "ALL_ROOT_SHELL_SYNTAX"
    )


# ============================================================
# CRITICAL FILES
# ============================================================

section(
    "5. CRITICAL FILES"
)

critical = [
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "visual_selection_engine_v2.py",
    "visual_selection_final_gate_v3.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]

for name in critical:

    path = ROOT / name

    if path.is_file():

        emit(
            f"CRITICAL=FOUND | {name} | sha256={sha256(path)}"
        )

    else:

        add_warn(
            "CRITICAL_FILE_MISSING",
            name,
        )


# ============================================================
# DUPLICATE DEFINITIONS
# ============================================================

section(
    "6. DUPLICATE TOP-LEVEL DEFINITIONS"
)

dup_total = 0

for path in python_files:

    source, tree, error = parse_python(
        path
    )

    if tree is None:
        continue

    duplicates = duplicate_defs(
        tree
    )

    if not duplicates:
        continue

    dup_total += len(
        duplicates
    )

    for name, count in duplicates.items():

        add_warn(
            "DUPLICATE_DEFINITION",
            f"{path.name}: {name} x{count}",
        )

if dup_total == 0:

    add_pass(
        "NO_DUPLICATE_TOP_LEVEL_DEFINITIONS"
    )


# ============================================================
# VSE4 STATIC FOUNDATION
# ============================================================

section(
    "7. VSE4 STATIC AUDIT"
)

vse4 = ROOT / "visual_selection_engine_v4.py"

if vse4.is_file():

    unresolved = unresolved_globals(
        vse4
    )

    if unresolved:

        add_error(
            "VSE4_UNRESOLVED_GLOBALS",
            ",".join(
                sorted(unresolved)
            ),
        )

    else:

        add_pass(
            "VSE4_UNRESOLVED_GLOBALS_NONE"
        )

    vse4_text = read_text(
        vse4
    )

    required_symbols = [
        "CONCEPTS",
        "GEO_GROUPS",
        "GENERIC_LIFESTYLE",
        "MEDICINE_TERMS",
        "candidate_text",
        "tokens",
        "geo_hits",
        "score_candidate",
        "self_test",
    ]

    for symbol in required_symbols:

        if re.search(
            rf"\b{re.escape(symbol)}\b",
            vse4_text,
        ):

            emit(
                f"VSE4_SYMBOL=PASS | {symbol}"
            )

        else:

            add_error(
                "VSE4_SYMBOL_MISSING",
                symbol,
            )

else:

    add_error(
        "VSE4_MISSING"
    )


# ============================================================
# VSE4 SELF TEST
# ============================================================

section(
    "8. VSE4 RUNTIME SELF TEST"
)

if vse4.is_file():

    status, output = run_safe_python(
        vse4,
        timeout=30,
    )

    emit(
        f"VSE4_SELF_TEST_STATUS={status}"
    )

    tail = "\n".join(
        output.splitlines()[-30:]
    )

    emit(
        "----- VSE4 SELF TEST TAIL -----"
    )

    emit(
        tail
    )

    if status == 0:

        add_pass(
            "VSE4_RUNTIME_SELF_TEST"
        )

    else:

        if "AssertionError" in output:

            add_error(
                "VSE4_ASSERTION_FAILURE"
            )

        elif "NameError" in output:

            add_error(
                "VSE4_NAMEERROR"
            )

        elif "TypeError" in output:

            add_error(
                "VSE4_TYPEERROR"
            )

        else:

            add_error(
                "VSE4_RUNTIME_FAILURE",
                f"status={status}",
            )


# ============================================================
# MIDIA INTEGRATION
# ============================================================

section(
    "9. MIDIA / VISUAL ENGINE INTEGRATION"
)

midia = ROOT / "midia.py"

if midia.is_file():

    text = read_text(
        midia
    )

    integration_checks = {
        "VSE4_REFERENCE":
            "visual_selection_engine_v4"
            in text,

        "VSE3_REFERENCE":
            "visual_selection_final_gate_v3"
            in text,

        "DIVERSITY_GUARD":
            "media_diversity_guard_v1"
            in text,

        "PROVENANCE":
            "media_provenance_capture_v1"
            in text,

        "MUST_RESCUE":
            (
                "visual_must_rescue_v1"
                in text
                or
                "VSE3_MUST_RESCUE"
                in text
            ),
    }

    for name, ok in integration_checks.items():

        if ok:

            emit(
                f"{name}=PRESENT"
            )

        else:

            emit(
                f"{name}=ABSENT"
            )

    if integration_checks[
        "VSE4_REFERENCE"
    ]:

        add_pass(
            "VSE4_REFERENCED_BY_MIDIA"
        )

    else:

        add_warn(
            "VSE4_NOT_YET_IN_ACTIVE_MIDIA",
            "Motor existe, mas referência direta não foi detectada.",
        )


# ============================================================
# PROVIDER ACQUISITION
# ============================================================

section(
    "10. PROVIDER ACQUISITION STATIC AUDIT"
)

if midia.is_file():

    text = read_text(
        midia
    )

    providers = {
        "PEXELS_VIDEO":
            r"\bpexels_video\s*\(",

        "PEXELS_PHOTO":
            r"\bpexels_foto\s*\(",

        "PIXABAY_VIDEO":
            r"\bpixabay_video\s*\(",

        "PIXABAY_PHOTO":
            r"\bpixabay_foto\s*\(",

        "COVERR_VIDEO":
            r"\bcoverr_video\s*\(",

        "WIKIMEDIA":
            r"\bbuscar_wikimedia_fotos\s*\(",
    }

    for name, pattern in providers.items():

        count = grep_count(
            text,
            pattern,
        )

        emit(
            f"{name}_REFERENCES={count}"
        )

        if count == 0:

            add_warn(
                "PROVIDER_NOT_REFERENCED",
                name,
            )

    if "buscar_todos_candidatos" in text:

        add_pass(
            "CANDIDATE_AGGREGATOR_PRESENT"
        )

    else:

        add_error(
            "CANDIDATE_AGGREGATOR_MISSING"
        )


# ============================================================
# SECRETS / PROVIDER CONFIG
# ============================================================

section(
    "11. PROVIDER CONFIG NAMES"
)

if midia.is_file():

    text = read_text(
        midia
    )

    env_names = sorted(
        set(
            re.findall(
                r'os\.getenv\(\s*["\']([^"\']+)["\']',
                text,
            )
        )
    )

    safe_provider_envs = [
        name
        for name in env_names
        if any(
            word in name.upper()
            for word in (
                "PEXELS",
                "PIXABAY",
                "COVERR",
                "WIKI",
                "MEDIA",
            )
        )
    ]

    for name in safe_provider_envs:

        configured = bool(
            os.environ.get(
                name,
                ""
            ).strip()
        )

        emit(
            f"ENV_NAME={name} "
            f"configured={'YES' if configured else 'NO'}"
        )

    emit(
        "SECRET_VALUES_PRINTED=NO"
    )


# ============================================================
# RENDER INPUTS
# ============================================================

section(
    "12. ACTIVE RENDER INPUT READINESS"
)

if sid:

    checks = {
        "AUDIO":
            AUDIOS
            /
            f"short_{sid}.mp3",

        "ASS":
            VIDEOS
            /
            f"short_{sid}.ass",

        "VIDEO_BASE":
            TEMP
            /
            sid
            /
            "video_sem_audio.mp4",

        "FINAL":
            VIDEOS
            /
            f"short_v6_{sid}.mp4",
    }

    for label, path in checks.items():

        if path.is_file() and path.stat().st_size > 0:

            emit(
                f"{label}=PASS "
                f"bytes={path.stat().st_size} "
                f"path={path}"
            )

        else:

            emit(
                f"{label}=MISSING "
                f"path={path}"
            )

    required = [
        checks["AUDIO"],
        checks["ASS"],
        checks["VIDEO_BASE"],
    ]

    if all(
        path.is_file()
        and path.stat().st_size > 0
        for path in required
    ):

        add_pass(
            "V6_INPUT_READINESS"
        )

    else:

        add_warn(
            "V6_INPUT_READINESS_INCOMPLETE"
        )


# ============================================================
# FRESH RENDER GUARD SAFETY
# ============================================================

section(
    "13. FRESH RENDER GUARD STATIC SAFETY"
)

guard = ROOT / "fresh_render_guard_v1.py"

if guard.is_file():

    text = read_text(
        guard
    )

    if ".ass" in text:

        emit(
            "GUARD_ASS_AWARE=YES"
        )

    else:

        add_warn(
            "GUARD_ASS_AWARE=NO"
        )

    if "PROTECTED_SUFFIXES" in text:

        add_pass(
            "GUARD_PROTECTED_SUFFIXES_PRESENT"
        )

    else:

        add_warn(
            "GUARD_NO_PROTECTED_SUFFIXES"
        )

    dangerous = (
        'rglob("*")' in text
        and
        "unlink" in text
        and
        "PROTECTED_SUFFIXES" not in text
    )

    if dangerous:

        add_error(
            "GUARD_BROAD_DELETE_PATTERN"
        )

    else:

        add_pass(
            "GUARD_NO_OBVIOUS_BROAD_DELETE"
        )


# ============================================================
# PROVENANCE
# ============================================================

section(
    "14. PROVENANCE / MANIFESTS"
)

prov = ROOT / "media_provenance_capture_v1.py"

if prov.is_file():

    add_pass(
        "PROVENANCE_MODULE_PRESENT"
    )

else:

    add_warn(
        "PROVENANCE_MODULE_MISSING"
    )

live_dirs = []

if MANIFESTS.is_dir():

    for path in MANIFESTS.iterdir():

        if "provenance" in path.name.lower():

            live_dirs.append(
                path
            )

emit(
    f"PROVENANCE_PATHS={len(live_dirs)}"
)

for path in live_dirs[:20]:

    emit(
        f"PROVENANCE_PATH={path}"
    )


# ============================================================
# SCENE COMMIT LOCK
# ============================================================

section(
    "15. SCENE COMMIT LOCK"
)

commit = ROOT / "visual_scene_commit_lock_v1.py"
diversity = ROOT / "media_diversity_guard_v1.py"

if commit.is_file():

    ctext = read_text(
        commit
    )

    required = [
        "COMMITTED",
        "BLOCKED",
        "SAP_SCENE_COMMIT_LOCK",
    ]

    missing = [
        item
        for item in required
        if item not in ctext
    ]

    if missing:

        add_warn(
            "COMMIT_LOCK_INCOMPLETE",
            ",".join(missing),
        )

    else:

        add_pass(
            "COMMIT_LOCK_STRUCTURE"
        )

else:

    add_warn(
        "COMMIT_LOCK_MODULE_MISSING"
    )

if diversity.is_file():

    dtext = read_text(
        diversity
    )

    if (
        "visual_scene_commit_lock_v1"
        in dtext
    ):

        add_pass(
            "COMMIT_LOCK_BRIDGE_PRESENT"
        )

    else:

        add_warn(
            "COMMIT_LOCK_BRIDGE_NOT_FOUND"
        )


# ============================================================
# LOG ERROR SCAN
# ============================================================

section(
    "16. RECENT LOG ERROR SCAN"
)

patterns = re.compile(
    r"Traceback|"
    r"NameError|"
    r"TypeError|"
    r"AssertionError|"
    r"SyntaxError|"
    r"ERRO:|"
    r"\bFAIL\b|"
    r"CRITICAL",
    re.I,
)

recent_logs = []

if LOGS.is_dir():

    recent_logs = sorted(
        [
            path
            for path in LOGS.glob("*")
            if path.is_file()
        ],
        key=lambda path:
            path.stat().st_mtime,
        reverse=True,
    )[:30]

historical_hits = []

for path in recent_logs:

    text = read_text(
        path
    )

    matches = patterns.findall(
        text
    )

    if matches:

        historical_hits.append(
            (
                path.name,
                len(matches),
            )
        )

        emit(
            f"LOG_ERRORS "
            f"file={path.name} "
            f"hits={len(matches)}"
        )

emit(
    f"RECENT_LOGS_SCANNED={len(recent_logs)}"
)

emit(
    f"LOGS_WITH_ERROR_MARKERS={len(historical_hits)}"
)

if historical_hits:

    add_warn(
        "HISTORICAL_LOG_ERRORS_FOUND",
        "Não significa necessariamente erro ativo.",
    )

else:

    add_pass(
        "NO_ERROR_MARKERS_RECENT_LOGS"
    )


# ============================================================
# SUSPICIOUS EMPTY / GIANT ROOT FILES
# ============================================================

section(
    "17. FILE ANOMALIES"
)

for path in sorted(
    list(
        ROOT.glob("*.py")
    )
    +
    list(
        ROOT.glob("*.sh")
    )
):

    size = path.stat().st_size

    if size == 0:

        add_error(
            "EMPTY_ACTIVE_FILE",
            path.name,
        )

    elif size > 2_000_000:

        add_warn(
            "VERY_LARGE_ACTIVE_SOURCE",
            f"{path.name} bytes={size}",
        )


# ============================================================
# HARD-MISMATCH SPECIAL TEST
# ============================================================

section(
    "18. VSE4 GEO HARD-MISMATCH TARGET TEST"
)

if vse4.is_file():

    test_code = r'''
import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="sap_general_geo_test",
)

score = ns["score_candidate"]

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
    "CORRECT_HARD_MISMATCH=",
    b.get("hard_mismatch"),
)

print(
    "WRONG_EFFECTIVE=",
    a.get("effective"),
)

print(
    "CORRECT_EFFECTIVE=",
    b.get("effective"),
)

if (
    a.get("hard_mismatch") is True
    and
    b.get("hard_mismatch") is False
    and
    b.get("effective", -10**9)
    >
    a.get("effective", 10**9)
):
    print(
        "GEO_HARD_MISMATCH_TEST=PASS"
    )
else:
    print(
        "GEO_HARD_MISMATCH_TEST=FAIL"
    )
    raise SystemExit(1)
'''

    try:

        r = subprocess.run(
            [
                "python",
                "-c",
                test_code,
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=20,
        )

        emit(
            r.stdout.strip()
        )

        if r.returncode == 0:

            add_pass(
                "GEO_HARD_MISMATCH_RUNTIME"
            )

        else:

            add_error(
                "GEO_HARD_MISMATCH_RUNTIME",
                "São Paulo x New York ainda não está protegido.",
            )

    except Exception as exc:

        add_error(
            "GEO_HARD_MISMATCH_TEST_EXCEPTION",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# CORE HASH INTEGRITY
# ============================================================

section(
    "19. AUDIT NON-MUTATION CHECK"
)

after_hashes = {
    str(path.relative_to(ROOT)):
        sha256(path)
    for path in core_files
}

for name in before_hashes:

    before = before_hashes[
        name
    ]

    after = after_hashes[
        name
    ]

    emit(
        f"CORE_HASH "
        f"{name} "
        f"before={before} "
        f"after={after}"
    )

    if before != after:

        add_error(
            "CORE_CHANGED_DURING_AUDIT",
            name,
        )

if before_hashes == after_hashes:

    add_pass(
        "AUDIT_DID_NOT_MODIFY_CORE"
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

section(
    "20. GENERAL CERTIFICATION"
)

errors = len(
    RESULTS["errors"]
)

warnings = len(
    RESULTS["warnings"]
)

passes = len(
    RESULTS["passes"]
)

emit(
    f"PASS_COUNT={passes}"
)

emit(
    f"WARNING_COUNT={warnings}"
)

emit(
    f"ERROR_COUNT={errors}"
)


if errors == 0:

    if warnings == 0:

        status = (
            "CERTIFIED"
        )

    else:

        status = (
            "PASS_WITH_WARNINGS"
        )

else:

    status = (
        "FAIL"
    )


emit(
    f"GENERAL_STATUS={status}"
)


if RESULTS["errors"]:

    emit()
    emit(
        "===== ACTIVE ERRORS ====="
    )

    for item in RESULTS[
        "errors"
    ]:

        emit(
            f"- {item['code']}: "
            f"{item['detail']}"
        )


if RESULTS["warnings"]:

    emit()
    emit(
        "===== WARNINGS ====="
    )

    for item in RESULTS[
        "warnings"
    ]:

        emit(
            f"- {item['code']}: "
            f"{item['detail']}"
        )


emit()
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
    "MIDIA_PIPELINE_EXECUTED=NO"
)

emit(
    "CORE_MUTATION_INTENDED=NO"
)

emit(
    "AUDIT_COMPLETE=YES"
)

emit(
    "TERMUX_CONTINUA_ABERTO=SIM"
)


REPORT.write_text(
    "\n".join(LINES)
    + "\n",
    encoding="utf-8",
)


JSON_REPORT.write_text(
    json.dumps(
        {
            "timestamp":
                time.time(),

            "active_short_id":
                sid,

            "status":
                status,

            "summary": {
                "passes":
                    passes,

                "warnings":
                    warnings,

                "errors":
                    errors,
            },

            "results":
                RESULTS,

            "core_hashes_before":
                before_hashes,

            "core_hashes_after":
                after_hashes,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    f"REPORT={REPORT}"
)

print(
    f"JSON_REPORT={JSON_REPORT}"
)
