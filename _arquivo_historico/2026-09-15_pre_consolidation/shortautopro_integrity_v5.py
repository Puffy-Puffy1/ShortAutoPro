#!/usr/bin/env python3

import ast
import os
import py_compile
import subprocess

from pathlib import Path


ROOT = (
    Path.home()
    /
    "ShortAutoPro"
)


errors = []
warnings = []


print(
    "=" * 70
)

print(
    "SHORTAUTOPRO INTEGRITY AUDIT V5"
)

print(
    "=" * 70
)


# ============================================================
# PYTHON COMPILE
# ============================================================

python_files = []

for path in ROOT.glob(
    "*.py"
):

    python_files.append(
        path
    )


compile_fail = []


for path in sorted(
    python_files
):

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
    "PYTHON_FILES=",
    len(
        python_files
    )
)

print(
    "PYTHON_COMPILE_FAILS=",
    len(
        compile_fail
    )
)


for name, error in compile_fail:

    print(
        "PYTHON_FAIL=",
        name,
        error,
    )


if compile_fail:

    errors.append(
        "PYTHON_COMPILE"
    )


# ============================================================
# SHELL
# ============================================================

shell_files = list(
    ROOT.glob(
        "*.sh"
    )
)


shell_fail = []


for path in shell_files:

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode:

        shell_fail.append(
            path.name
        )


print(
    "SHELL_FILES=",
    len(
        shell_files
    )
)

print(
    "SHELL_SYNTAX_FAILS=",
    len(
        shell_fail
    )
)


if shell_fail:

    errors.append(
        "SHELL_SYNTAX"
    )


# ============================================================
# VQE5
# ============================================================

required = {

    "visual_quality_engine_v5.py":
        [
            "score_candidate",
            "rerank",
            "choose_best",
            "rescue_queries",
        ],

    "visual_quality_runtime_v5.py":
        [
            "install",
            "runtime_choose",
            "clean_scene_siblings",
        ],
}


for filename, functions in required.items():

    path = ROOT / filename

    if not path.is_file():

        errors.append(
            "MISSING:"
            +
            filename
        )

        continue


    tree = ast.parse(
        path.read_text(
            encoding="utf-8"
        )
    )


    names = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }


    for function in functions:

        if function not in names:

            errors.append(
                f"MISSING_FUNCTION:"
                f"{filename}:"
                f"{function}"
            )


# ============================================================
# MIDIA INTEGRATION
# ============================================================

midia = (
    ROOT
    /
    "midia.py"
).read_text(
    encoding="utf-8",
    errors="replace",
)


if (
    "# SHORTAUTOPRO VQE5 RUNTIME INSTALL"
    not in midia
):

    errors.append(
        "VQE5_RUNTIME_NOT_IN_MIDIA"
    )


if (
    "# SHORTAUTOPRO VQE5 FINAL WINNER GATE"
    not in midia
):

    errors.append(
        "VQE5_FINAL_GATE_NOT_IN_MIDIA"
    )


# ============================================================
# CURRENT SHORT MEDIA
# ============================================================

sid = os.getenv(
    "SHORT_ID",
    ""
).strip()


if sid:

    folder = (
        ROOT
        /
        "imagens"
        /
        f"short_{sid}"
    )


    if folder.is_dir():

        total = 0
        bad = 0
        hashes = {}


        import hashlib


        for number in range(
            1,
            13,
        ):

            matches = list(
                folder.glob(
                    f"scene_{number:02d}.*"
                )
            )


            total += len(
                matches
            )


            if len(
                matches
            ) != 1:

                bad += 1


            for path in matches:

                digest = hashlib.sha256(
                    path.read_bytes()
                ).hexdigest()


                hashes.setdefault(
                    digest,
                    []
                ).append(
                    path.name
                )


        duplicate_groups = [
            files
            for files in hashes.values()
            if len(files) > 1
        ]


        print(
            "MEDIA_TOTAL=",
            total
        )

        print(
            "MEDIA_BAD_SCENES=",
            bad
        )

        print(
            "DUPLICATE_MEDIA_GROUPS=",
            duplicate_groups
        )


        if bad:

            errors.append(
                "MEDIA_SCENE_COUNT"
            )


        if duplicate_groups:

            warnings.append(
                "EXACT_MEDIA_REUSE"
            )


# ============================================================
# SUMMARY
# ============================================================

print(
    "ERRORS=",
    errors
)

print(
    "WARNINGS=",
    warnings
)


if errors:

    print(
        "PROJECT_INTEGRITY=FAIL"
    )

    raise SystemExit(1)


print(
    "PROJECT_INTEGRITY=PASS"
)
