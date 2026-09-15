#!/usr/bin/env python3

from pathlib import Path
from collections import Counter, defaultdict
import ast
import hashlib
import os
import re
import runpy
import subprocess
import time


ROOT = Path.home() / "ShortAutoPro"

REPORT = (
    ROOT
    / "temp"
    / "SAP_ACTIVE_RUNTIME_AUDIT_V2.txt"
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


out = []


def emit(*parts):

    text = " ".join(
        str(x)
        for x in parts
    )

    print(text)

    out.append(text)


def section(title):

    emit()
    emit("=" * 72)
    emit(title)
    emit("=" * 72)


def sha(path):

    path = Path(path)

    if not path.is_file():
        return "MISSING"

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


def scene_files(directory):

    result = {}

    if not directory.is_dir():
        return result

    for n in range(1, 13):

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
                    f"scene_{n:02d}{ext}"
                )
            )

        result[n] = sorted(
            matches
        )

    return result


def valid_media_set(directory):

    scenes = scene_files(
        directory
    )

    return (
        len(scenes) == 12
        and
        all(
            len(v) == 1
            for v in scenes.values()
        )
    )


# ============================================================
# 1. DISCOVER REAL ACTIVE MEDIA SET
# ============================================================

section(
    "1. ACTIVE SHORT DISCOVERY"
)

images_root = (
    ROOT
    / "imagens"
)

directories = []

if images_root.is_dir():

    directories = sorted(
        [
            p
            for p in images_root.glob(
                "short_*"
            )
            if p.is_dir()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


valid = []

for directory in directories:

    files = scene_files(
        directory
    )

    count = sum(
        len(x)
        for x in files.values()
    )

    errors = sum(
        1
        for x in files.values()
        if len(x) != 1
    )

    sid = directory.name.removeprefix(
        "short_"
    )

    emit(
        f"MEDIA_SET sid={sid} "
        f"files={count} "
        f"errors={errors}"
    )

    if valid_media_set(
        directory
    ):
        valid.append(
            directory
        )


requested_sid = (
    os.environ.get(
        "SHORT_ID",
        ""
    ).strip()
)


chosen = None


if requested_sid:

    candidate = (
        images_root
        / f"short_{requested_sid}"
    )

    if valid_media_set(
        candidate
    ):

        chosen = candidate

        emit(
            "SHORT_SELECTION="
            "ENV_VALID"
        )


if chosen is None and valid:

    chosen = valid[0]

    emit(
        "SHORT_SELECTION="
        "LATEST_VALID"
    )


if chosen is not None:

    sid = chosen.name.removeprefix(
        "short_"
    )

    emit(
        f"ACTIVE_SHORT_ID={sid}"
    )

    emit(
        f"ACTIVE_MEDIA_DIR={chosen}"
    )

else:

    sid = ""

    emit(
        "ACTIVE_SHORT_ID=NONE"
    )

    emit(
        "ACTIVE_MEDIA_SET=WARN_NO_12_SCENE_SET"
    )


# ============================================================
# 2. ACTIVE MEDIA STRUCTURE
# ============================================================

section(
    "2. ACTIVE MEDIA STRUCTURE"
)

media_errors = 0
media_total = 0
types = Counter()


if chosen is not None:

    scenes = scene_files(
        chosen
    )

    for number in range(
        1,
        13,
    ):

        matches = scenes[
            number
        ]

        media_total += len(
            matches
        )

        if len(matches) != 1:

            media_errors += 1

            emit(
                f"SCENE_{number:02d}=FAIL "
                f"count={len(matches)}"
            )

            continue


        path = matches[0]

        suffix = (
            path.suffix
            .lower()
        )


        if suffix in (
            ".mp4",
            ".mov",
            ".webm",
        ):

            kind = "video"

        else:

            kind = "photo"


        types[kind] += 1


        emit(
            f"SCENE_{number:02d}=PASS "
            f"type={kind} "
            f"bytes={path.stat().st_size} "
            f"sha256={sha(path)[:16]} "
            f"file={path.name}"
        )


emit(
    f"MEDIA_TOTAL={media_total}"
)

emit(
    f"MEDIA_STRUCTURE_ERRORS={media_errors}"
)

emit(
    f"MEDIA_TYPES={dict(types)}"
)


# ============================================================
# 3. CORE COMPILE
# ============================================================

section(
    "3. CORE COMPILE"
)

core_python = [

    "midia.py",
    "video.py",
    "v6.py",

    "visual_selection_engine_v4.py",

    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",

    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",

    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


compile_fail = []


for name in core_python:

    path = (
        ROOT
        / name
    )

    if not path.is_file():

        emit(
            f"COMPILE_{name}=MISSING"
        )

        continue


    result = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


    emit(
        f"COMPILE_{name}="
        f"{result.returncode}"
    )


    if result.returncode != 0:

        compile_fail.append(
            name
        )

        if result.stderr:

            emit(
                result.stderr.strip()
            )


shell = (
    ROOT
    / "gerar_short.sh"
)

if shell.is_file():

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(shell),
        ],
        cwd=ROOT,
    )

    shell_status = (
        result.returncode
    )

else:

    shell_status = -1


emit(
    f"GERAR_SHORT_SYNTAX="
    f"{shell_status}"
)


# ============================================================
# 4. CORE HASHES
# ============================================================

section(
    "4. CORE HASHES"
)


for name in (

    "midia.py",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_scene_commit_lock_v1.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",

):

    emit(
        f"HASH_{name}="
        f"{sha(ROOT / name)}"
    )


# ============================================================
# 5. TOP-LEVEL DUPLICATE DEFINITIONS
# ============================================================

section(
    "5. TOP-LEVEL DEFINITION SHADOWING"
)


important_files = (

    "visual_selection_engine_v4.py",
    "midia.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_scene_commit_lock_v1.py",

)


duplicate_risk = []


for name in important_files:

    path = (
        ROOT
        / name
    )

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

        emit(
            f"AST_{name}=FAIL {exc}"
        )

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
            ),
        ):

            defs[
                node.name
            ].append(
                node.lineno
            )


    duplicates = {
        key: value
        for key, value in defs.items()
        if len(value) > 1
    }


    if not duplicates:

        emit(
            f"DUPLICATE_DEFS_{name}=NONE"
        )

        continue


    emit(
        f"DUPLICATE_DEFS_{name}="
        f"{duplicates}"
    )


    for function, lines in sorted(
        duplicates.items()
    ):

        active = lines[-1]

        emit(
            f"ACTIVE_DEF "
            f"file={name} "
            f"function={function} "
            f"line={active} "
            f"shadowed={lines[:-1]}"
        )


        if (
            name
            ==
            "visual_selection_engine_v4.py"
            and
            function
            in {
                "score_candidate",
                "candidate_text",
                "_vse414_lifestyle_penalty",
            }
        ):

            duplicate_risk.append(
                (
                    name,
                    function,
                    lines,
                )
            )


# ============================================================
# 6. ACTIVE VSE4 FUNCTION HASHES
# ============================================================

section(
    "6. ACTIVE VSE4 DEFINITIONS"
)

vse_path = (
    ROOT
    / "visual_selection_engine_v4.py"
)

active_function_hashes = {}


if vse_path.is_file():

    src = vse_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(
        src
    )

    lines = src.splitlines(
        keepends=True
    )


    for wanted in (
        "candidate_text",
        "tokens",
        "geo_hits",
        "score_candidate",
        "_vse414_lifestyle_penalty",
        "choose_candidate",
        "rerank",
    ):

        defs = [
            node
            for node in tree.body
            if (
                isinstance(
                    node,
                    ast.FunctionDef,
                )
                and
                node.name == wanted
            )
        ]


        if not defs:

            emit(
                f"ACTIVE_{wanted}=MISSING"
            )

            continue


        node = defs[-1]


        text = "".join(
            lines[
                node.lineno - 1:
                node.end_lineno
            ]
        )


        digest = hashlib.sha256(
            text.encode(
                "utf-8"
            )
        ).hexdigest()


        active_function_hashes[
            wanted
        ] = digest


        emit(
            f"ACTIVE_{wanted}_LINE="
            f"{node.lineno}"
        )

        emit(
            f"ACTIVE_{wanted}_SHA256="
            f"{digest}"
        )


# ============================================================
# 7. VSE4 RUNTIME SELF TEST
# ============================================================

section(
    "7. VSE4 RUNTIME"
)

vse_script_status = -1


if vse_path.is_file():

    result = subprocess.run(
        [
            "python",
            str(vse_path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
    )

    vse_script_status = (
        result.returncode
    )


    emit(
        f"VSE4_SCRIPT_STATUS="
        f"{vse_script_status}"
    )


    tail = (
        result.stdout
        or ""
    ).splitlines()[-30:]


    for line in tail:

        emit(
            "VSE4_OUTPUT="
            + line
        )


# ============================================================
# 8. DIRECT GEOGRAPHY / SEMANTIC TEST
# ============================================================

section(
    "8. VSE4 DIRECT SEMANTIC TEST"
)

semantic_ok = False


try:

    ns = runpy.run_path(
        str(vse_path),
        run_name="sap_active_audit_v2",
    )


    score_candidate = ns[
        "score_candidate"
    ]


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
            "Empire State Building "
            "Manhattan New York",

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


    emit(
        "WRONG_HARD_MISMATCH=",
        a.get(
            "hard_mismatch"
        )
    )

    emit(
        "CORRECT_HARD_MISMATCH=",
        b.get(
            "hard_mismatch"
        )
    )

    emit(
        "WRONG_EFFECTIVE=",
        a.get(
            "effective"
        )
    )

    emit(
        "CORRECT_EFFECTIVE=",
        b.get(
            "effective"
        )
    )


    semantic_ok = (
        a.get(
            "hard_mismatch"
        ) is True

        and

        b.get(
            "hard_mismatch"
        ) is False

        and

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


    emit(
        "SEMANTIC_GEO_RUNTIME="
        +
        (
            "PASS"
            if semantic_ok
            else
            "FAIL"
        )
    )


except Exception as exc:

    emit(
        "SEMANTIC_GEO_RUNTIME=FAIL"
    )

    emit(
        f"SEMANTIC_EXCEPTION="
        f"{type(exc).__name__}: "
        f"{exc}"
    )


# ============================================================
# 9. MIDIA INTEGRATION
# ============================================================

section(
    "9. MIDIA INTEGRATION"
)

midia_path = (
    ROOT
    / "midia.py"
)

midia_text = ""

if midia_path.is_file():

    midia_text = midia_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


markers = {

    "VSE4":
        (
            "visual_selection_engine_v4"
            in midia_text
            or
            "VSE4"
            in midia_text
        ),

    "VSE3":
        (
            "visual_selection_final_gate_v3"
            in midia_text
            or
            "VSE3"
            in midia_text
        ),

    "DIVERSITY":
        "media_diversity_guard_v1"
        in midia_text,

    "PROVENANCE":
        "media_provenance_capture_v1"
        in midia_text,

    "COMMIT_LOCK_DIRECT":
        (
            "visual_scene_commit_lock_v1"
            in midia_text
            or
            "SCENE_COMMIT_LOCK"
            in midia_text
        ),
}


for key, value in markers.items():

    emit(
        f"MIDIA_MARKER_{key}="
        f"{'YES' if value else 'NO'}"
    )


# ============================================================
# 10. COMMIT LOCK EFFECTIVE PATH
# ============================================================

section(
    "10. COMMIT LOCK EFFECTIVE PATH"
)


lock_files = (

    "midia.py",
    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
    "visual_selection_engine_v4.py",

)


lock_hits = []


for name in lock_files:

    path = (
        ROOT
        / name
    )

    if not path.is_file():
        continue


    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for pattern in (

        "SCENE_COMMIT_LOCK",
        "visual_scene_commit_lock",
        "commit_lock",
        "install(",

    ):

        if pattern.casefold() in text.casefold():

            lock_hits.append(
                (
                    name,
                    pattern,
                )
            )

            emit(
                f"COMMIT_LOCK_REFERENCE "
                f"file={name} "
                f"pattern={pattern}"
            )


emit(
    f"COMMIT_LOCK_REFERENCE_COUNT="
    f"{len(lock_hits)}"
)


# ============================================================
# 11. DOWNLOAD CALL GRAPH
# ============================================================

section(
    "11. MEDIA DOWNLOAD CALL GRAPH"
)


if midia_path.is_file():

    tree = ast.parse(
        midia_text
    )


    functions = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }


    for wanted in (

        "buscar_todos_candidatos",
        "baixar_candidato_5_2",

    ):

        node = functions.get(
            wanted
        )


        if node is None:

            emit(
                f"FUNCTION_{wanted}=MISSING"
            )

            continue


        calls = []


        for child in ast.walk(
            node
        ):

            if not isinstance(
                child,
                ast.Call,
            ):
                continue


            if isinstance(
                child.func,
                ast.Name,
            ):

                calls.append(
                    child.func.id
                )


            elif isinstance(
                child.func,
                ast.Attribute,
            ):

                calls.append(
                    child.func.attr
                )


        emit(
            f"{wanted.upper()}_CALLS="
            +
            ",".join(
                sorted(
                    set(calls)
                )
            )
        )


# ============================================================
# 12. PROVIDER ACQUISITION
# ============================================================

section(
    "12. PROVIDER ACQUISITION"
)


provider_names = (

    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",

)


for provider_fn in provider_names:

    present = bool(
        re.search(
            rf"^def\s+"
            rf"{re.escape(provider_fn)}"
            rf"\s*\(",
            midia_text,
            re.MULTILINE,
        )
    )


    emit(
        f"PROVIDER_FUNCTION_{provider_fn}="
        f"{'YES' if present else 'NO'}"
    )


# ============================================================
# 13. ACTIVE LOG PROVIDER DISTRIBUTION
# ============================================================

section(
    "13. ACTIVE LOG PROVIDER DISTRIBUTION"
)


provider_counter = Counter()
log_matches = []


logs_root = (
    ROOT
    / "logs"
    / "producao"
)


if logs_root.is_dir():

    candidates = sorted(
        logs_root.glob(
            "*.log"
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:50]


    for log in candidates:

        try:

            text = log.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except Exception:

            continue


        if sid and sid not in text and sid not in log.name:
            continue


        log_matches.append(
            log
        )


        for provider_name in (
            "Pixabay",
            "Pexels",
            "Wikimedia",
            "Coverr",
        ):

            count = len(
                re.findall(
                    provider_name,
                    text,
                    re.IGNORECASE,
                )
            )

            provider_counter[
                provider_name
            ] += count


emit(
    f"ACTIVE_LOG_COUNT="
    f"{len(log_matches)}"
)

emit(
    f"PROVIDER_LOG_MENTIONS="
    f"{dict(provider_counter)}"
)


# ============================================================
# 14. HISTORICAL LOG ERRORS — INFORMATIONAL ONLY
# ============================================================

section(
    "14. RECENT LOG ERROR SCAN"
)


recent_error_logs = []


if logs_root.is_dir():

    for log in sorted(
        logs_root.glob(
            "*.log"
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:30]:

        try:

            text = log.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except Exception:

            continue


        matches = re.findall(
            r"\b(?:ERRO|ERROR|FAIL|Traceback)\b",
            text,
            re.IGNORECASE,
        )


        if matches:

            recent_error_logs.append(
                (
                    log.name,
                    len(matches),
                )
            )


for name, count in recent_error_logs:

    emit(
        f"HISTORICAL_LOG_ERRORS "
        f"file={name} "
        f"matches={count}"
    )


emit(
    "HISTORICAL_LOG_ERRORS_ARE_NOT_"
    "CURRENT_RUNTIME_FAILURES=YES"
)


# ============================================================
# 15. FINAL CLASSIFICATION
# ============================================================

section(
    "15. FINAL CLASSIFICATION"
)


blockers = []
warnings = []


if compile_fail:

    blockers.append(
        "PYTHON_COMPILE_FAILURE"
    )


if shell_status != 0:

    blockers.append(
        "GERAR_SHORT_SYNTAX"
    )


if vse_script_status != 0:

    blockers.append(
        "VSE4_SELF_TEST"
    )


if not semantic_ok:

    blockers.append(
        "VSE4_SEMANTIC_GEO"
    )


if not markers[
    "VSE4"
]:

    blockers.append(
        "VSE4_NOT_IN_MIDIA"
    )


if chosen is None:

    warnings.append(
        "NO_VALID_12_SCENE_MEDIA_SET"
    )


if chosen is not None and media_errors:

    blockers.append(
        "ACTIVE_MEDIA_STRUCTURE"
    )


if duplicate_risk:

    warnings.append(
        "VSE4_SHADOWED_DEFINITIONS"
    )


if not markers[
    "COMMIT_LOCK_DIRECT"
]:

    warnings.append(
        "COMMIT_LOCK_NOT_DIRECT_IN_MIDIA"
    )


if len(lock_hits) == 0:

    blockers.append(
        "COMMIT_LOCK_NO_REFERENCE_ANYWHERE"
    )


if (
    types
    and
    (
        types.get(
            "video",
            0,
        )
        == 0

        or

        types.get(
            "photo",
            0,
        )
        == 0
    )
):

    warnings.append(
        "MEDIA_TYPE_MONOCULTURE"
    )


emit(
    f"BLOCKER_COUNT="
    f"{len(blockers)}"
)

for item in blockers:

    emit(
        f"BLOCKER={item}"
    )


emit(
    f"WARNING_COUNT="
    f"{len(warnings)}"
)

for item in warnings:

    emit(
        f"WARNING={item}"
    )


if blockers:

    status = "BLOCKED"

elif warnings:

    status = "PASS_WITH_WARNINGS"

else:

    status = "PASS"


emit(
    f"ACTIVE_RUNTIME_AUDIT_STATUS="
    f"{status}"
)


emit(
    f"ACTIVE_SHORT_ID="
    f"{sid or 'NONE'}"
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
    "FILES_MODIFIED="
    "REPORT_ONLY"
)


REPORT.write_text(
    "\n".join(out)
    + "\n",
    encoding="utf-8",
)


emit()
emit(
    f"REPORT={REPORT}"
)

emit(
    "AUDIT_V2_COMPLETE=YES"
)
