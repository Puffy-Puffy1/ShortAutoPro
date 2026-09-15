#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import symtable
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"
TEMP = ROOT / "temp"
LOGS = ROOT / "logs" / "producao"

STAMP = time.strftime("%Y%m%d_%H%M%S")

REPORT_TXT = (
    TEMP
    / f"AUDITORIA_GERAL_SHORTAUTOPRO_{STAMP}.txt"
)

REPORT_JSON = (
    TEMP
    / f"AUDITORIA_GERAL_SHORTAUTOPRO_{STAMP}.json"
)


TEMP.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# RESULT ENGINE
# ============================================================

results = []

severity_count = Counter()

SEVERITY_ORDER = {
    "PASS": 0,
    "INFO": 1,
    "WARN": 2,
    "ERROR": 3,
    "CRITICAL": 4,
}


def add(
    test,
    severity,
    message,
    data=None,
):

    severity = severity.upper()

    if severity not in SEVERITY_ORDER:
        severity = "INFO"

    item = {
        "test": test,
        "severity": severity,
        "message": str(message),
    }

    if data is not None:
        item["data"] = data

    results.append(item)

    severity_count[severity] += 1

    print(
        f"[{severity:8}] "
        f"{test}: "
        f"{message}"
    )


def section(title):

    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def sha256(path):

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

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


# ============================================================
# BASIC ENVIRONMENT
# ============================================================

section(
    "1. ENVIRONMENT"
)

add(
    "PROJECT_ROOT",
    "PASS" if ROOT.is_dir() else "CRITICAL",
    ROOT,
)


for command in (
    "python",
    "ffmpeg",
    "ffprobe",
    "bash",
):

    found = shutil.which(command)

    add(
        f"COMMAND_{command.upper()}",
        "PASS" if found else "ERROR",
        found or "NOT_FOUND",
    )


try:

    usage = shutil.disk_usage(ROOT)

    free_mb = (
        usage.free
        / 1024
        / 1024
    )

    if free_mb < 500:
        sev = "CRITICAL"

    elif free_mb < 1000:
        sev = "WARN"

    else:
        sev = "PASS"

    add(
        "FREE_SPACE",
        sev,
        f"{free_mb:.1f} MB free",
    )

except Exception as exc:

    add(
        "FREE_SPACE",
        "WARN",
        repr(exc),
    )


# ============================================================
# CRITICAL FILES
# ============================================================

section(
    "2. CRITICAL FILE INVENTORY"
)


critical_files = (
    "gerar_short.sh",
    "roteiro.py",
    "audio.py",
    "legenda_dinamica.py",
    "midia.py",
    "video.py",
    "v6.py",
    "media_diversity_guard_v1.py",
    "visual_selection_engine_v4.py",
)


for name in critical_files:

    path = ROOT / name

    if path.is_file():

        add(
            f"FILE_{name}",
            "PASS",
            (
                f"{path.stat().st_size} bytes "
                f"sha256={sha256(path)}"
            ),
        )

    else:

        add(
            f"FILE_{name}",
            "ERROR",
            "MISSING",
        )


# ============================================================
# PYTHON AST + COMPILE
# ============================================================

section(
    "3. PYTHON SYNTAX / COMPILE"
)


python_files = sorted(
    p
    for p in ROOT.glob("*.py")
    if p.is_file()
)


compile_fail = []


for path in python_files:

    try:

        source = read_text(path)

        ast.parse(
            source,
            filename=str(path),
        )

        compile(
            source,
            str(path),
            "exec",
        )

    except Exception as exc:

        compile_fail.append(
            (
                path.name,
                f"{type(exc).__name__}: {exc}",
            )
        )


if compile_fail:

    for name, error in compile_fail:

        add(
            f"PYTHON_COMPILE_{name}",
            "ERROR",
            error,
        )

else:

    add(
        "PYTHON_COMPILE_ALL_TOP_LEVEL",
        "PASS",
        (
            f"{len(python_files)} "
            "Python files parsed successfully"
        ),
    )


# ============================================================
# SHELL SYNTAX
# ============================================================

section(
    "4. SHELL SYNTAX"
)


shell_files = sorted(
    p
    for p in ROOT.glob("*.sh")
    if p.is_file()
)


shell_fail = []


for path in shell_files:

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
            (
                path.name,
                (
                    result.stderr.strip()
                    or
                    result.stdout.strip()
                ),
            )
        )


if shell_fail:

    for name, error in shell_fail:

        add(
            f"SHELL_{name}",
            "ERROR",
            error,
        )

else:

    add(
        "SHELL_SYNTAX_ALL_TOP_LEVEL",
        "PASS",
        (
            f"{len(shell_files)} "
            "shell scripts valid"
        ),
    )


# ============================================================
# DUPLICATE PYTHON DEFINITIONS
# ============================================================

section(
    "5. DUPLICATE TOP-LEVEL DEFINITIONS"
)


for path in python_files:

    try:

        tree = ast.parse(
            read_text(path)
        )

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
            names.append(
                node.name
            )


    duplicates = [
        name
        for name, count
        in Counter(names).items()
        if count > 1
    ]


    if duplicates:

        add(
            f"DUPLICATE_DEFINITIONS_{path.name}",
            "WARN",
            ",".join(
                sorted(duplicates)
            ),
        )


# ============================================================
# VISUAL FLAGS
# ============================================================

section(
    "6. VISUAL FEATURE FLAGS"
)


gerar = ROOT / "gerar_short.sh"

gerar_text = (
    read_text(gerar)
    if gerar.is_file()
    else ""
)


visual_flags = (
    "SAP_VSE4",
    "SAP_VSE42",
    "SAP_VSE4_RUNTIME",
    "SAP_SCENE_COMMIT_LOCK",
)


flag_values = {}


for flag in visual_flags:

    matches = re.findall(
        rf'export\s+{re.escape(flag)}\s*=\s*["\']?([^"\'\s]+)',
        gerar_text,
    )

    if matches:

        flag_values[
            flag
        ] = matches

        add(
            f"FLAG_{flag}",
            (
                "WARN"
                if matches[-1] == "0"
                else "PASS"
            ),
            (
                f"assignments={matches}; "
                f"effective_static={matches[-1]}"
            ),
        )

    else:

        add(
            f"FLAG_{flag}",
            "INFO",
            "not explicitly exported in gerar_short.sh",
        )


vse_disabled = all(
    (
        flag_values.get(
            flag,
            [None],
        )[-1]
        ==
        "0"
    )
    for flag in (
        "SAP_VSE4",
        "SAP_VSE42",
        "SAP_VSE4_RUNTIME",
    )
)


if vse_disabled:

    add(
        "VISUAL_ENGINE_PIPELINE_STATE",
        "CRITICAL",
        (
            "VSE4/VSE42/runtime are all explicitly "
            "disabled by gerar_short.sh"
        ),
    )

else:

    add(
        "VISUAL_ENGINE_PIPELINE_STATE",
        "PASS",
        "not all VSE4 flags are disabled",
    )


# ============================================================
# MIDIA VISUAL INTEGRATION ORDER
# ============================================================

section(
    "7. MIDIA VISUAL INTEGRATION ORDER"
)


midia = ROOT / "midia.py"

midia_text = (
    read_text(midia)
    if midia.is_file()
    else ""
)


visual_markers = {
    "VSE417":
        r"VSE4\.17|VSE417",

    "VISUAL_UNIFIED":
        r"VISUAL UNIFIED|visual_engine_unified",

    "VSE42_FINAL_GATE":
        r"VSE42 FINAL GATE",

    "VSE42_PRIMARY_RANK":
        r"VSE42 PRIMARY RANK",

    "VSE42_FINAL_POOL":
        r"VSE42 FINAL POOL",

    "VSE42_FINAL_POOL_GATE":
        r"VSE4\.2 FINAL POOL GATE",

    "VSE42_COMMIT":
        r"VSE42 SCENE COMMIT",

    "VSE42_SUCCESS_COMMIT":
        r"VSE42 SUCCESS COMMIT",
}


marker_locations = {}


for name, pattern in visual_markers.items():

    lines = []

    for number, line in enumerate(
        midia_text.splitlines(),
        start=1,
    ):

        if re.search(
            pattern,
            line,
            re.I,
        ):

            lines.append(number)


    marker_locations[
        name
    ] = lines


    if lines:

        add(
            f"MIDIA_{name}",
            "INFO",
            f"lines={lines}",
        )


decision_layers = sum(
    bool(
        marker_locations.get(name)
    )
    for name in (
        "VSE417",
        "VISUAL_UNIFIED",
        "VSE42_FINAL_GATE",
        "VSE42_PRIMARY_RANK",
        "VSE42_FINAL_POOL_GATE",
    )
)


if decision_layers >= 4:

    add(
        "VISUAL_DECISION_LAYER_COUNT",
        "WARN",
        (
            f"{decision_layers} ranking/selection layers "
            "exist in the same active media path; "
            "possible override conflict"
        ),
    )

else:

    add(
        "VISUAL_DECISION_LAYER_COUNT",
        "PASS",
        f"{decision_layers} layers",
    )


# ============================================================
# LEGACY V3/V2 INTERFERENCE
# ============================================================

section(
    "8. LEGACY VISUAL ENGINE INTERFERENCE"
)


legacy_patterns = {
    "VSE3":
        r"visual_selection_final_gate_v3|VSE3_",

    "VSE2":
        r"visual_selection_engine_v2|VSE2_",

    "OLD_COMMIT_LOCK":
        r"visual_scene_commit_lock_v1",

    "OLD_MUST_RESCUE":
        r"visual_must_rescue_v1",
}


for name, pattern in legacy_patterns.items():

    count = len(
        re.findall(
            pattern,
            midia_text,
            re.I,
        )
    )

    add(
        f"LEGACY_{name}",
        (
            "WARN"
            if count
            else "PASS"
        ),
        f"midia.py references={count}",
    )


# ============================================================
# COMMIT / DOWNLOAD PATHS
# ============================================================

section(
    "9. SCENE COMMIT / DOWNLOAD SAFETY"
)


commit_count = len(
    re.findall(
        r"VSE42_SCENE_COMMIT",
        midia_text,
        re.I,
    )
)


download_calls = len(
    re.findall(
        r"\bbaixar_candidato_5_2\s*\(",
        midia_text,
    )
)


cleanup_count = len(
    re.findall(
        r"_vse42_cleanup_scene_sibling\s*\(",
        midia_text,
    )
)


add(
    "SCENE_COMMIT_MARKERS",
    (
        "WARN"
        if commit_count > 4
        else "INFO"
    ),
    f"count={commit_count}",
)


add(
    "DOWNLOAD_CALLS",
    "INFO",
    f"baixar_candidato_5_2 calls={download_calls}",
)


add(
    "SCENE_SIBLING_CLEANUP",
    (
        "PASS"
        if cleanup_count
        else "WARN"
    ),
    f"calls={cleanup_count}",
)


# ============================================================
# PROVIDER ACQUISITION
# ============================================================

section(
    "10. PROVIDER ACQUISITION"
)


provider_functions = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
)


provider_present = {}


for fn in provider_functions:

    definition = bool(
        re.search(
            rf"^def\s+{re.escape(fn)}\s*\(",
            midia_text,
            re.M,
        )
    )

    call_count = len(
        re.findall(
            rf"\b{re.escape(fn)}\s*\(",
            midia_text,
        )
    )

    provider_present[
        fn
    ] = {
        "defined": definition,
        "calls": call_count,
    }

    add(
        f"PROVIDER_{fn}",
        (
            "PASS"
            if definition and call_count >= 2
            else
            "WARN"
        ),
        (
            f"defined={definition}; "
            f"total_mentions_as_call={call_count}"
        ),
    )


# ============================================================
# VSE4 STRUCTURE
# ============================================================

section(
    "11. VSE4 STRUCTURE"
)


vse4 = ROOT / "visual_selection_engine_v4.py"


required_vse4_functions = (
    "score_candidate",
    "candidate_text",
    "tokens",
    "geo_hits",
    "concept_hits",
    "provider",
    "source_group",
    "media_type",
    "must_tier",
)


required_vse4_globals = (
    "GEO_GROUPS",
    "CONCEPTS",
    "GENERIC_LIFESTYLE",
    "MEDICINE_TERMS",
)


if vse4.is_file():

    source = read_text(vse4)

    tree = ast.parse(source)

    functions = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }

    assignments = set()

    for node in tree.body:

        if isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name,
                ):
                    assignments.add(
                        target.id
                    )


    missing_fn = [
        fn
        for fn in required_vse4_functions
        if fn not in functions
    ]

    missing_global = [
        name
        for name in required_vse4_globals
        if name not in assignments
    ]


    add(
        "VSE4_REQUIRED_FUNCTIONS",
        (
            "PASS"
            if not missing_fn
            else "ERROR"
        ),
        (
            "all present"
            if not missing_fn
            else f"missing={missing_fn}"
        ),
    )


    add(
        "VSE4_REQUIRED_GLOBALS",
        (
            "PASS"
            if not missing_global
            else "ERROR"
        ),
        (
            "all present"
            if not missing_global
            else f"missing={missing_global}"
        ),
    )


# ============================================================
# VSE4 UNRESOLVED GLOBALS
# ============================================================

section(
    "12. VSE4 GLOBAL SYMBOL AUDIT"
)


if vse4.is_file():

    try:

        source = read_text(vse4)

        table = symtable.symtable(
            source,
            str(vse4),
            "exec",
        )

        import builtins

        builtin_names = set(
            dir(builtins)
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


        unresolved = set()


        def walk(scope):

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

                walk(child)


        walk(table)


        add(
            "VSE4_UNRESOLVED_GLOBALS",
            (
                "PASS"
                if not unresolved
                else "ERROR"
            ),
            (
                "NONE"
                if not unresolved
                else ",".join(
                    sorted(unresolved)
                )
            ),
        )

    except Exception as exc:

        add(
            "VSE4_UNRESOLVED_GLOBALS",
            "ERROR",
            repr(exc),
        )


# ============================================================
# VSE4 SELF TEST
# ============================================================

section(
    "13. VSE4 SELF TEST"
)


if vse4.is_file():

    env = os.environ.copy()

    env.update(
        {
            "SAP_NO_NETWORK": "1",
            "SAP_NO_PUBLISH": "1",
            "SAP_AUDIT_MODE": "1",
        }
    )

    try:

        test = subprocess.run(
            [
                sys.executable,
                str(vse4),
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )


        output = (
            test.stdout
            +
            "\n"
            +
            test.stderr
        ).strip()


        add(
            "VSE4_SELF_TEST",
            (
                "PASS"
                if test.returncode == 0
                else "ERROR"
            ),
            (
                f"returncode={test.returncode}; "
                f"tail={output[-1200:]}"
            ),
        )

    except subprocess.TimeoutExpired:

        add(
            "VSE4_SELF_TEST",
            "ERROR",
            "timeout >30s",
        )


# ============================================================
# VISUAL BRIDGE
# ============================================================

section(
    "14. VISUAL BRIDGE"
)


bridge = (
    ROOT
    / "media_diversity_guard_v1.py"
)


if bridge.is_file():

    bridge_text = read_text(
        bridge
    )


    tests = {
        "IMPORTS_VSE4":
            r"visual_selection_engine_v4",

        "USES_SCORE_CANDIDATE":
            r"\bscore_candidate\s*\(",

        "USES_HARD_MISMATCH":
            r"\bhard_mismatch\b",

        "HAS_RERANK_POOL":
            r"^def\s+rerank_pool\s*\(",
    }


    for name, pattern in tests.items():

        present = bool(
            re.search(
                pattern,
                bridge_text,
                re.M,
            )
        )

        add(
            f"BRIDGE_{name}",
            (
                "PASS"
                if present
                else "ERROR"
            ),
            str(present),
        )


# ============================================================
# GERAR_SHORT STEP MAP
# ============================================================

section(
    "15. PIPELINE STEP MAP"
)


step_lines = []


for number, line in enumerate(
    gerar_text.splitlines(),
    start=1,
):

    if re.search(
        r'\b\d+/\d+\b',
        line,
    ):

        step_lines.append(
            (
                number,
                line.strip(),
            )
        )


add(
    "PIPELINE_STEPS",
    (
        "PASS"
        if step_lines
        else "WARN"
    ),
    f"steps_found={len(step_lines)}",
    step_lines,
)


# ============================================================
# LATEST SHORT
# ============================================================

section(
    "16. LATEST SHORT ARTIFACT HEALTH"
)


short_files = sorted(
    (
        ROOT
        / "roteiros"
    ).glob(
        "short_*.txt"
    ),
    key=lambda p:
        p.stat().st_mtime,
    reverse=True,
)


latest_sid = None


for path in short_files:

    name = path.stem

    if (
        "pre_" in name
        or
        name.endswith(
            "_pre"
        )
    ):
        continue

    latest_sid = name.removeprefix(
        "short_"
    )

    break


if latest_sid:

    add(
        "LATEST_SHORT_ID",
        "INFO",
        latest_sid,
    )


    media_dir = (
        ROOT
        / "imagens"
        / f"short_{latest_sid}"
    )


    if media_dir.is_dir():

        scenes = defaultdict(
            list
        )


        for path in media_dir.glob(
            "scene_*.*"
        ):

            match = re.match(
                r"scene_(\d+)\.",
                path.name,
            )

            if match:

                scenes[
                    int(
                        match.group(1)
                    )
                ].append(path)


        duplicates = {
            number: [
                p.name
                for p in paths
            ]
            for number, paths
            in scenes.items()
            if len(paths) > 1
        }


        tiny = [
            p.name
            for paths
            in scenes.values()
            for p in paths
            if (
                p.is_file()
                and
                p.stat().st_size < 4096
            )
        ]


        add(
            "LATEST_MEDIA_COUNT",
            (
                "PASS"
                if len(scenes) == 12
                else "WARN"
            ),
            (
                f"unique_scene_numbers="
                f"{len(scenes)}"
            ),
        )


        add(
            "LATEST_MEDIA_DUPLICATE_SCENE",
            (
                "PASS"
                if not duplicates
                else "ERROR"
            ),
            (
                "NONE"
                if not duplicates
                else json.dumps(
                    duplicates,
                    ensure_ascii=False,
                )
            ),
        )


        add(
            "LATEST_MEDIA_TINY_FILES",
            (
                "PASS"
                if not tiny
                else "WARN"
            ),
            (
                "NONE"
                if not tiny
                else ",".join(tiny)
            ),
        )

    else:

        add(
            "LATEST_MEDIA_DIR",
            "WARN",
            f"missing={media_dir}",
        )


    artifact_paths = {
        "AUDIO":
            ROOT
            / "audios"
            / f"short_{latest_sid}.mp3",

        "ASS":
            ROOT
            / "videos"
            / f"short_{latest_sid}.ass",

        "VIDEO_BASE":
            ROOT
            / "temp"
            / latest_sid
            / "video_sem_audio.mp4",

        "FINAL":
            ROOT
            / "videos"
            / f"short_v6_{latest_sid}.mp4",
    }


    for name, path in artifact_paths.items():

        add(
            f"LATEST_{name}",
            (
                "PASS"
                if path.is_file()
                and path.stat().st_size > 0
                else "INFO"
            ),
            (
                f"{path} "
                +
                (
                    f"{path.stat().st_size} bytes"
                    if path.is_file()
                    else "MISSING"
                )
            ),
        )


else:

    add(
        "LATEST_SHORT_ID",
        "WARN",
        "not found",
    )


# ============================================================
# FRESH RENDER GUARD SAFETY
# ============================================================

section(
    "17. RENDER GUARD SAFETY"
)


guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    guard_text = read_text(
        guard
    )


    ass_protected = (
        ".ass"
        in guard_text
    )


    broad_rglob = bool(
        re.search(
            r'rglob\(\s*["\']\*["\']',
            guard_text,
        )
    )


    add(
        "RENDER_GUARD_ASS_PROTECTED",
        (
            "PASS"
            if ass_protected
            else "ERROR"
        ),
        str(ass_protected),
    )


    add(
        "RENDER_GUARD_BROAD_RGLOB",
        (
            "WARN"
            if broad_rglob
            else "PASS"
        ),
        str(broad_rglob),
    )


# ============================================================
# DANGEROUS SHELL PATTERNS
# ============================================================

section(
    "18. SHELL SAFETY PATTERNS"
)


dangerous = []


for path in shell_files:

    text = read_text(path)

    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        clean = line.strip()

        if re.search(
            r'\brm\s+-rf\s+[/~]?\*',
            clean,
        ):

            dangerous.append(
                (
                    path.name,
                    number,
                    clean,
                )
            )


if dangerous:

    add(
        "DANGEROUS_RM_PATTERNS",
        "CRITICAL",
        dangerous,
    )

else:

    add(
        "DANGEROUS_RM_PATTERNS",
        "PASS",
        "none detected",
    )


# ============================================================
# RECENT LOG ERRORS
# ============================================================

section(
    "19. RECENT LOG ERROR SCAN"
)


log_errors = Counter()

log_examples = []


if LOGS.is_dir():

    recent_logs = sorted(
        (
            p
            for p in LOGS.glob("*")
            if p.is_file()
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:20]


    patterns = {
        "TRACEBACK":
            r"Traceback \(most recent call last\)",

        "NAMEERROR":
            r"\bNameError\b",

        "TYPEERROR":
            r"\bTypeError\b",

        "ASSERTION":
            r"\bAssertionError\b",

        "FILE_NOT_FOUND":
            r"arquivo não encontrado|FileNotFoundError",

        "FAIL_OPEN":
            r"FAIL_OPEN",

        "ERRO":
            r"\bERRO\b|\bERROR\b",
    }


    for path in recent_logs:

        text = read_text(path)

        for name, pattern in patterns.items():

            matches = re.findall(
                pattern,
                text,
                re.I,
            )

            if matches:

                log_errors[
                    name
                ] += len(matches)

                if len(
                    log_examples
                ) < 20:

                    log_examples.append(
                        {
                            "file":
                                path.name,

                            "type":
                                name,

                            "count":
                                len(matches),
                        }
                    )


    add(
        "RECENT_LOG_ERRORS",
        (
            "WARN"
            if log_errors
            else "PASS"
        ),
        dict(log_errors),
        log_examples,
    )


# ============================================================
# STATIC CONTRADICTIONS
# ============================================================

section(
    "20. CONFIGURATION CONTRADICTIONS"
)


if (
    "visual_selection_engine_v4"
    in midia_text
    and
    vse_disabled
):

    add(
        "CONTRADICTION_VSE4_PRESENT_BUT_DISABLED",
        "CRITICAL",
        (
            "midia.py contains VSE4 integration but "
            "gerar_short.sh disables SAP_VSE4, SAP_VSE42 "
            "and SAP_VSE4_RUNTIME"
        ),
    )


if (
    decision_layers >= 4
):

    add(
        "CONTRADICTION_MULTIPLE_RANKERS",
        "WARN",
        (
            "multiple visual ranking systems are chained; "
            "later rankers may override earlier decisions"
        ),
    )


if (
    commit_count >= 3
):

    add(
        "MULTIPLE_COMMIT_PATHS",
        "WARN",
        (
            f"{commit_count} VSE42_SCENE_COMMIT markers "
            "exist; verify each belongs to a distinct "
            "branch and cannot execute twice per scene"
        ),
    )


# ============================================================
# FINAL SUMMARY
# ============================================================

section(
    "21. FINAL SUMMARY"
)


critical = severity_count[
    "CRITICAL"
]

errors = severity_count[
    "ERROR"
]

warnings = severity_count[
    "WARN"
]


if critical:

    overall = "CRITICAL"

elif errors:

    overall = "FAIL"

elif warnings:

    overall = "PASS_WITH_WARNINGS"

else:

    overall = "PASS"


summary = {
    "status":
        overall,

    "critical":
        critical,

    "errors":
        errors,

    "warnings":
        warnings,

    "pass":
        severity_count["PASS"],

    "info":
        severity_count["INFO"],

    "latest_short_id":
        latest_sid,

    "report_txt":
        str(REPORT_TXT),

    "report_json":
        str(REPORT_JSON),
}


print(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    )
)


# ============================================================
# SAVE REPORTS
# ============================================================

payload = {
    "timestamp":
        STAMP,

    "root":
        str(ROOT),

    "summary":
        summary,

    "results":
        results,
}


REPORT_JSON.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


lines = []

lines.append(
    "SHORTAUTOPRO GENERAL AUDIT"
)

lines.append(
    "=" * 72
)

lines.append(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2,
    )
)

lines.append("")


for item in results:

    lines.append(
        f"[{item['severity']}] "
        f"{item['test']}: "
        f"{item['message']}"
    )


REPORT_TXT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)


print()
print(
    f"REPORT_TXT={REPORT_TXT}"
)

print(
    f"REPORT_JSON={REPORT_JSON}"
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
    "CORE_FILES_MODIFIED=NO"
)

print(
    "AUDIT_COMPLETE=YES"
)
