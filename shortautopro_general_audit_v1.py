#!/usr/bin/env python3

from pathlib import Path
import ast
import hashlib
import importlib
import os
import py_compile
import subprocess
import sys
import traceback


ROOT = Path.home() / "ShortAutoPro"

os.chdir(ROOT)


FAILURES = []
WARNINGS = []
PASSES = []


def section(name):

    print()
    print("=" * 72)
    print(name)
    print("=" * 72)


def passed(name):

    PASSES.append(name)

    print(
        f"{name}=PASS"
    )


def failed(name, reason=""):

    FAILURES.append(
        (
            name,
            reason,
        )
    )

    print(
        f"{name}=FAIL"
        +
        (
            f" | {reason}"
            if reason
            else ""
        )
    )


def warning(name, reason=""):

    WARNINGS.append(
        (
            name,
            reason,
        )
    )

    print(
        f"{name}=WARN"
        +
        (
            f" | {reason}"
            if reason
            else ""
        )
    )


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


# ============================================================
# 1. CRITICAL FILES
# ============================================================

section(
    "1. CRITICAL FILES"
)


critical = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
    "fresh_render_guard_v1.py",
]


for name in critical:

    path = ROOT / name

    if path.is_file():

        print(
            f"FOUND={name}"
        )

    else:

        failed(
            "CRITICAL_FILE_" + name,
            "missing",
        )


# ============================================================
# 2. COMPILE
# ============================================================

section(
    "2. PYTHON COMPILE"
)


compile_fail = []

python_files = list(
    ROOT.glob("*.py")
)


for path in python_files:

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        compile_fail.append(
            (
                path.name,
                str(exc),
            )
        )


print(
    "ROOT_PY_TOTAL=",
    len(python_files),
)


if compile_fail:

    for name, err in compile_fail[:30]:

        print(
            f"COMPILE_FAIL={name} | {err}"
        )

    failed(
        "ROOT_PY_COMPILE",
        str(
            len(compile_fail)
        ),
    )

else:

    passed(
        "ROOT_PY_COMPILE"
    )


# ============================================================
# 3. SHELL
# ============================================================

section(
    "3. SHELL SYNTAX"
)


result = subprocess.run(
    [
        "bash",
        "-n",
        "gerar_short.sh",
    ],
    capture_output=True,
    text=True,
)


if result.returncode == 0:

    passed(
        "GERAR_SHORT_SYNTAX"
    )

else:

    failed(
        "GERAR_SHORT_SYNTAX",
        result.stderr.strip(),
    )


# ============================================================
# 4. SAFE IMPORTS
# ============================================================

section(
    "4. CRITICAL IMPORTS"
)


for module in (
    "media_diversity_guard_v1",
    "visual_scene_commit_lock_v1",
    "visual_selection_engine_v4",
):

    try:

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import " + module,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )

    except subprocess.TimeoutExpired:

        failed(
            f"IMPORT_{module}",
            "timeout",
        )

        continue


    if result.returncode == 0:

        passed(
            f"IMPORT_{module}"
        )

    else:

        failed(
            f"IMPORT_{module}",
            (
                result.stderr.strip()
                or
                result.stdout.strip()
            )[-1200:],
        )


# ============================================================
# 5. VSE4 RUNTIME
# ============================================================

section(
    "5. VSE4 RUNTIME"
)


try:

    import runpy

    vse = runpy.run_path(
        "visual_selection_engine_v4.py",
        run_name="sap_general_audit",
    )

    passed(
        "VSE4_LOAD"
    )


    score_candidate = vse.get(
        "score_candidate"
    )

    if callable(
        score_candidate
    ):

        passed(
            "VSE4_SCORE_API"
        )

    else:

        failed(
            "VSE4_SCORE_API",
            "score_candidate unavailable",
        )


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
        score_candidate
    ):

        a = score_candidate(
            wrong,
            scene,
            {
                "providers": [],
                "groups": [],
                "types": [],
                "keys": [],
            },
        )

        b = score_candidate(
            correct,
            scene,
            {
                "providers": [],
                "groups": [],
                "types": [],
                "keys": [],
            },
        )


        print(
            "WRONG_HARD_MISMATCH=",
            a.get(
                "hard_mismatch"
            ),
        )

        print(
            "WRONG_EFFECTIVE=",
            a.get(
                "effective"
            ),
        )

        print(
            "CORRECT_HARD_MISMATCH=",
            b.get(
                "hard_mismatch"
            ),
        )

        print(
            "CORRECT_EFFECTIVE=",
            b.get(
                "effective"
            ),
        )


        if (
            a.get(
                "hard_mismatch"
            )
            is True
        ):

            passed(
                "VSE4_GEO_HARD_MISMATCH"
            )

        else:

            failed(
                "VSE4_GEO_HARD_MISMATCH",
                "São Paulo x New York accepted",
            )


        if (
            b.get(
                "hard_mismatch"
            )
            is False
        ):

            passed(
                "VSE4_CORRECT_GEO_ALLOWED"
            )

        else:

            failed(
                "VSE4_CORRECT_GEO_ALLOWED"
            )


        ae = a.get(
            "effective",
            0,
        )

        be = b.get(
            "effective",
            0,
        )


        if be > ae:

            passed(
                "VSE4_CORRECT_RANKS_ABOVE_WRONG"
            )

        else:

            failed(
                "VSE4_CORRECT_RANKS_ABOVE_WRONG",
                f"wrong={ae} correct={be}",
            )


except Exception as exc:

    failed(
        "VSE4_RUNTIME",
        (
            type(exc).__name__
            +
            ":"
            +
            str(exc)
        ),
    )

    traceback.print_exc()


# ============================================================
# 6. MIDIA AST / VSE42
# ============================================================

section(
    "6. MIDIA / VSE42 CONTRACT"
)


try:

    src = Path(
        "midia.py"
    ).read_text(
        encoding="utf-8",
    )

    tree = ast.parse(src)


    functions = {
        n.name
        for n in tree.body
        if isinstance(
            n,
            ast.FunctionDef,
        )
    }


    required_provider_functions = {
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
        "buscar_todos_candidatos",
    }


    missing_provider = (
        required_provider_functions
        -
        functions
    )


    if not missing_provider:

        passed(
            "PROVIDER_FUNCTIONS_PRESENT"
        )

    else:

        failed(
            "PROVIDER_FUNCTIONS_PRESENT",
            ",".join(
                sorted(
                    missing_provider
                )
            ),
        )


    markers = {
        "VSE42":
            "_vse42_",

        "VSE4":
            "visual_selection_engine_v4",

        "COMMIT":
            "commit",

        "DIVERSITY":
            "divers",
    }


    for label, marker in markers.items():

        count = src.casefold().count(
            marker.casefold()
        )

        print(
            f"{label}_MARKER_COUNT={count}"
        )


    if "_vse42_rank_pool" in src:

        passed(
            "VSE42_RANK_POOL_BRIDGE"
        )

    else:

        failed(
            "VSE42_RANK_POOL_BRIDGE"
        )


    if "_vse42_finalize_pool" in src:

        passed(
            "VSE42_FINAL_POOL_BRIDGE"
        )

    else:

        warning(
            "VSE42_FINAL_POOL_BRIDGE",
            "not found",
        )


except Exception as exc:

    failed(
        "MIDIA_AST",
        str(exc),
    )


# ============================================================
# 7. PROVIDER CALLS
# ============================================================

section(
    "7. PROVIDER ACQUISITION"
)


try:

    fn = next(
        (
            n
            for n in tree.body
            if (
                isinstance(
                    n,
                    ast.FunctionDef,
                )
                and
                n.name
                ==
                "buscar_todos_candidatos"
            )
        ),
        None,
    )


    provider_calls = set()


    if fn:

        for node in ast.walk(
            fn
        ):

            if isinstance(
                node,
                ast.Call,
            ):

                if isinstance(
                    node.func,
                    ast.Name,
                ):

                    provider_calls.add(
                        node.func.id
                    )


    for provider_name in (
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
    ):

        if provider_name in provider_calls:

            passed(
                "CALL_" + provider_name
            )

        else:

            warning(
                "CALL_" + provider_name,
                "not directly called",
            )


except Exception as exc:

    failed(
        "PROVIDER_CALL_AUDIT",
        str(exc),
    )


# ============================================================
# 8. DOWNLOAD SUCCESS LOOP
# ============================================================

section(
    "8. POST-DOWNLOAD FLOW"
)


try:

    text = Path(
        "midia.py"
    ).read_text(
        encoding="utf-8",
    )


    lines = text.splitlines()


    suspicious = []


    for i, line in enumerate(
        lines,
        start=1,
    ):

        if (
            "baixar_candidato_5_2("
            in line
        ):

            snippet = "\n".join(
                lines[
                    max(
                        0,
                        i - 8
                    ):
                    min(
                        len(lines),
                        i + 35,
                    )
                ]
            )

            suspicious.append(
                (
                    i,
                    snippet,
                )
            )


    print(
        "DOWNLOAD_CALL_SITES=",
        len(suspicious),
    )


    unconditional_break_found = False


    for line_no, snippet in suspicious:

        print()
        print(
            f"DOWNLOAD_SITE_LINE={line_no}"
        )

        # Heurística conservadora.
        if "break" in snippet:

            unconditional_break_found = True


    if unconditional_break_found:

        passed(
            "POST_DOWNLOAD_BREAK_PRESENT"
        )

    else:

        warning(
            "POST_DOWNLOAD_BREAK_PRESENT",
            "manual/commit-lock protection required",
        )


except Exception as exc:

    failed(
        "POST_DOWNLOAD_FLOW",
        str(exc),
    )


# ============================================================
# 9. COMMIT LOCK
# ============================================================

section(
    "9. COMMIT LOCK"
)


try:

    src_lock = Path(
        "visual_scene_commit_lock_v1.py"
    ).read_text(
        encoding="utf-8",
    )

    tree_lock = ast.parse(
        src_lock
    )


    lock_functions = {
        n.name
        for n in tree_lock.body
        if isinstance(
            n,
            ast.FunctionDef,
        )
    }


    print(
        "COMMIT_LOCK_FUNCTIONS=",
        sorted(
            lock_functions
        ),
    )


    if "install" in lock_functions:

        passed(
            "COMMIT_LOCK_INSTALL"
        )

    else:

        warning(
            "COMMIT_LOCK_INSTALL",
            "install API absent",
        )


except Exception as exc:

    failed(
        "COMMIT_LOCK_AUDIT",
        str(exc),
    )


# ============================================================
# 10. MEDIA RUNS
# ============================================================

section(
    "10. MEDIA RUN STRUCTURE"
)


media_root = ROOT / "imagens"


runs = sorted(
    (
        p
        for p in media_root.glob(
            "short_*"
        )
        if p.is_dir()
    ),
    key=lambda p:
        p.stat().st_mtime,
    reverse=True,
)


complete_runs = []
incomplete_runs = []


for run in runs[:30]:

    counts = []

    total = 0


    for n in range(
        1,
        13,
    ):

        files = list(
            run.glob(
                f"scene_{n:02d}.*"
            )
        )

        count = len(
            [
                f
                for f in files
                if f.is_file()
            ]
        )

        counts.append(
            count
        )

        total += count


    valid = (
        total == 12
        and
        all(
            x == 1
            for x in counts
        )
    )


    if valid:

        complete_runs.append(
            run
        )

    else:

        incomplete_runs.append(
            (
                run,
                total,
                counts,
            )
        )


if runs:

    print(
        "NEWEST_MEDIA_RUN=",
        runs[0],
    )


if complete_runs:

    print(
        "NEWEST_COMPLETE_MEDIA_RUN=",
        complete_runs[0],
    )

    passed(
        "COMPLETE_MEDIA_RUN_AVAILABLE"
    )

else:

    warning(
        "COMPLETE_MEDIA_RUN_AVAILABLE",
        "none in latest 30",
    )


print(
    "INCOMPLETE_RUN_COUNT=",
    len(incomplete_runs),
)


for run, total, counts in incomplete_runs[:10]:

    print(
        "INCOMPLETE="
        +
        run.name
        +
        f" total={total}"
        +
        f" counts={counts}"
    )


# ============================================================
# 11. DUPLICATE SCENES
# ============================================================

section(
    "11. DUPLICATE SCENE FILES"
)


duplicate_runs = 0


for run in runs[:30]:

    duplicates = []


    for n in range(
        1,
        13,
    ):

        files = [
            f
            for f in run.glob(
                f"scene_{n:02d}.*"
            )
            if f.is_file()
        ]

        if len(files) > 1:

            duplicates.append(
                (
                    n,
                    [
                        f.name
                        for f in files
                    ],
                )
            )


    if duplicates:

        duplicate_runs += 1

        print(
            "DUPLICATE_RUN=",
            run.name,
            duplicates,
        )


if duplicate_runs == 0:

    passed(
        "NO_SCENE_EXTENSION_DUPLICATES"
    )

else:

    warning(
        "NO_SCENE_EXTENSION_DUPLICATES",
        str(
            duplicate_runs
        ),
    )


# ============================================================
# 12. RENDER GUARD
# ============================================================

section(
    "12. RENDER GUARD"
)


try:

    guard_text = Path(
        "fresh_render_guard_v1.py"
    ).read_text(
        encoding="utf-8",
    )


    if ".ass" in guard_text:

        passed(
            "RENDER_GUARD_ASS_AWARE"
        )

    else:

        warning(
            "RENDER_GUARD_ASS_AWARE"
        )


except Exception as exc:

    failed(
        "RENDER_GUARD_AUDIT",
        str(exc),
    )


# ============================================================
# 13. FINAL SUMMARY
# ============================================================

section(
    "GENERAL AUDIT SUMMARY"
)


print(
    "PASS_COUNT=",
    len(PASSES),
)

print(
    "WARNING_COUNT=",
    len(WARNINGS),
)

print(
    "FAIL_COUNT=",
    len(FAILURES),
)


if WARNINGS:

    print()
    print(
        "===== WARNINGS ====="
    )

    for name, reason in WARNINGS:

        print(
            f"WARN={name} | {reason}"
        )


if FAILURES:

    print()
    print(
        "===== FAILURES ====="
    )

    for name, reason in FAILURES:

        print(
            f"FAIL={name} | {reason}"
        )


print()


if not FAILURES:

    print(
        "GENERAL_CERTIFICATION=PASS"
    )

else:

    print(
        "GENERAL_CERTIFICATION=FAIL"
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
    "MIDIA_EXECUTED=NO"
)


if __name__ == "__main__":
    pass
