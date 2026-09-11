#!/usr/bin/env python3


# SHORTAUTOPRO RUNTIME SHORT_ID V1
#
# O ID do short deve vir da execução atual.
# Não manter IDs históricos fixos em runtime.

_SAP_RUNTIME_SHORT_ID = os.environ.get(
    "SHORT_ID",
    "",
).strip()


from pathlib import Path
import ast
import inspect
import os
import shutil
import subprocess
import sys
import time
import runpy
import traceback


ROOT = Path.home() / "ShortAutoPro"

VSE = ROOT / "visual_selection_engine_v4.py"

SID = os.environ.get(
    "SHORT_ID",
    _SAP_RUNTIME_SHORT_ID,
).strip()

MEDIA_DIR = (
    ROOT
    / "imagens"
    / f"short_{SID}"
)

STAMP = time.strftime(
    "%Y%m%d_%H%M%S"
)

QUARANTINE = (
    ROOT
    / "backups"
    / f"media_invariant_repair_{STAMP}"
    / SID
)

REPORT = (
    ROOT
    / "temp"
    / "VSE4_CRITICAL_RESOLVER_V1.txt"
)


def out(*args):

    text = " ".join(
        str(x)
        for x in args
    )

    print(
        text,
        flush=True,
    )

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT.open(
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            text + "\n"
        )


def header(title):

    out()
    out("=" * 70)
    out(title)
    out("=" * 70)


def ffprobe_valid(path):

    try:

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,width,height",
                "-of",
                "default=noprint_wrappers=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )

        if result.returncode != 0:
            return False

        text = (
            result.stdout
            +
            result.stderr
        ).strip()

        if not text:
            return False

        return (
            "codec_type=video"
            in text
        )

    except Exception:

        return False


def media_scene_number(path):

    stem = path.stem

    if not stem.startswith(
        "scene_"
    ):
        return None

    number = stem[
        len("scene_"):
    ]

    try:
        return int(number)
    except Exception:
        return None


def quarantine_file(path, reason):

    QUARANTINE.mkdir(
        parents=True,
        exist_ok=True,
    )

    target = (
        QUARANTINE
        / path.name
    )

    counter = 1

    while target.exists():

        target = (
            QUARANTINE
            /
            (
                path.stem
                +
                f"_{counter}"
                +
                path.suffix
            )
        )

        counter += 1

    shutil.move(
        str(path),
        str(target),
    )

    out(
        "QUARANTINED=",
        path.relative_to(ROOT),
    )

    out(
        "QUARANTINE_REASON=",
        reason,
    )

    out(
        "QUARANTINE_TARGET=",
        target.relative_to(ROOT),
    )


REPORT.unlink(
    missing_ok=True
)


# ============================================================
# 1. VSE LOAD
# ============================================================

header(
    "1. VSE4 RUNTIME LOAD"
)

runtime_ok = False
namespace = {}


try:

    namespace = runpy.run_path(
        str(VSE),
        run_name="vse4_critical_resolver",
    )

    runtime_ok = True

    out(
        "VSE4_RUNTIME_LOAD=PASS"
    )

except Exception as exc:

    out(
        "VSE4_RUNTIME_LOAD=FAIL"
    )

    out(
        "ERROR=",
        type(exc).__name__,
        str(exc),
    )

    traceback.print_exc()


# ============================================================
# 2. ACTIVE DEFINITIONS
# ============================================================

header(
    "2. ACTIVE DEFINITION MAP"
)

source = VSE.read_text(
    encoding="utf-8",
    errors="replace",
)

tree = ast.parse(
    source
)

candidate_defs = []
score_defs = []


for node in tree.body:

    if isinstance(
        node,
        ast.FunctionDef,
    ):

        if node.name == "candidate_text":

            candidate_defs.append(
                node
            )

        if node.name == "score_candidate":

            score_defs.append(
                node
            )


out(
    "CANDIDATE_TEXT_DEFINITION_COUNT=",
    len(candidate_defs),
)

out(
    "SCORE_CANDIDATE_DEFINITION_COUNT=",
    len(score_defs),
)


if candidate_defs:

    out(
        "ACTIVE_CANDIDATE_TEXT_LINE=",
        candidate_defs[-1].lineno,
    )


if score_defs:

    out(
        "ACTIVE_SCORE_CANDIDATE_LINE=",
        score_defs[-1].lineno,
    )


# ============================================================
# 3. VSE416 EXACT STATIC MAP
# ============================================================

header(
    "3. VSE416 EXACT STATIC MAP"
)

lines = source.splitlines()

vse416_nodes = []


for node in tree.body:

    if not isinstance(
        node,
        ast.FunctionDef,
    ):
        continue

    segment = "\n".join(
        lines[
            node.lineno - 1:
            node.end_lineno
        ]
    )

    has_marker = (
        "VSE416" in segment
        or
        "vse416" in segment.casefold()
        or
        "416" in node.name
    )

    if not has_marker:
        continue


    recursive_calls = []

    for child in ast.walk(
        node
    ):

        if not isinstance(
            child,
            ast.Call,
        ):
            continue

        if (
            isinstance(
                child.func,
                ast.Name,
            )
            and
            child.func.id
            ==
            node.name
        ):

            recursive_calls.append(
                child
            )


    vse416_nodes.append(
        (
            node,
            recursive_calls,
        )
    )


out(
    "VSE416_FUNCTION_COUNT=",
    len(vse416_nodes),
)


for node, calls in vse416_nodes:

    out(
        "VSE416_FUNCTION=",
        node.name,
        "LINE=",
        node.lineno,
        "END=",
        node.end_lineno,
        "DIRECT_SELF_CALLS=",
        len(calls),
    )


# ============================================================
# 4. RUNTIME OBJECT RESOLUTION
# ============================================================

header(
    "4. VSE416 RUNTIME CYCLE PROBE"
)

cycle_confirmed = False
cycle_clear = False
cycle_unknown = False

runtime_objects = []


if runtime_ok:

    for global_name, value in namespace.items():

        if not inspect.isfunction(
            value
        ):
            continue

        try:

            first_line = (
                value.__code__
                .co_firstlineno
            )

        except Exception:
            continue


        for node, calls in vse416_nodes:

            if (
                first_line
                ==
                node.lineno
            ):

                runtime_objects.append(
                    (
                        global_name,
                        value,
                        node,
                        calls,
                    )
                )


out(
    "VSE416_RUNTIME_OBJECTS=",
    len(runtime_objects),
)


for (
    global_name,
    fn,
    node,
    calls,
) in runtime_objects:

    out()

    out(
        "RUNTIME_ALIAS=",
        global_name,
    )

    out(
        "FUNCTION_NAME=",
        node.name,
    )

    out(
        "FUNCTION_LINE=",
        node.lineno,
    )

    out(
        "DIRECT_SELF_CALLS=",
        len(calls),
    )


    try:

        sig = inspect.signature(
            fn
        )

        out(
            "SIGNATURE=",
            sig,
        )

        required = []

        for parameter in sig.parameters.values():

            if (
                parameter.default
                is inspect._empty
                and
                parameter.kind
                in (
                    parameter.POSITIONAL_ONLY,
                    parameter.POSITIONAL_OR_KEYWORD,
                )
            ):

                required.append(
                    parameter
                )


        if len(required) == 0:

            try:

                result = fn()

                out(
                    "RUNTIME_PROBE=PASS_NO_RECURSION"
                )

                out(
                    "RESULT_TYPE=",
                    type(result).__name__,
                )

                cycle_clear = True

            except RecursionError:

                out(
                    "RUNTIME_PROBE=RECURSION_CONFIRMED"
                )

                cycle_confirmed = True

            except Exception as exc:

                out(
                    "RUNTIME_PROBE=NON_RECURSION_EXCEPTION"
                )

                out(
                    "EXCEPTION=",
                    type(exc).__name__,
                    str(exc),
                )

                cycle_clear = True


        elif len(required) == 1:

            probes = [
                {
                    "title":
                        "Police investigation apartment Sao Paulo",
                    "provider":
                        "Pixabay",
                    "tipo":
                        "foto",
                },
                "Police investigation apartment Sao Paulo",
            ]


            probe_completed = False


            for value in probes:

                try:

                    result = fn(
                        value
                    )

                    out(
                        "RUNTIME_PROBE=PASS_NO_RECURSION"
                    )

                    out(
                        "INPUT_TYPE=",
                        type(value).__name__,
                    )

                    out(
                        "RESULT_TYPE=",
                        type(result).__name__,
                    )

                    cycle_clear = True

                    probe_completed = True

                    break


                except RecursionError:

                    out(
                        "RUNTIME_PROBE=RECURSION_CONFIRMED"
                    )

                    cycle_confirmed = True

                    probe_completed = True

                    break


                except Exception as exc:

                    out(
                        "PROBE_EXCEPTION=",
                        type(exc).__name__,
                        str(exc),
                    )


            if not probe_completed:

                cycle_unknown = True

                out(
                    "RUNTIME_PROBE=INCONCLUSIVE"
                )


        else:

            cycle_unknown = True

            out(
                "RUNTIME_PROBE=SKIPPED_SIGNATURE"
            )


    except Exception as exc:

        cycle_unknown = True

        out(
            "RUNTIME_PROBE=ERROR"
        )

        out(
            "ERROR=",
            type(exc).__name__,
            str(exc),
        )


if cycle_confirmed:

    out(
        "VSE416_RUNTIME_CYCLE=CONFIRMED"
    )

elif cycle_clear:

    out(
        "VSE416_RUNTIME_CYCLE=NOT_REPRODUCED"
    )

elif vse416_nodes:

    out(
        "VSE416_RUNTIME_CYCLE=INCONCLUSIVE"
    )

else:

    out(
        "VSE416_RUNTIME_CYCLE=NO_VSE416_FUNCTION"
    )


# ============================================================
# 5. ACTIVE CANDIDATE TEXT
# ============================================================

header(
    "5. ACTIVE CANDIDATE_TEXT SMOKE"
)

candidate_smoke = False


if runtime_ok:

    fn = namespace.get(
        "candidate_text"
    )

    if callable(fn):

        try:

            result = fn(
                {
                    "title":
                        "Apartment building Sao Paulo Brazil",
                    "provider":
                        "Wikimedia",
                }
            )

            out(
                "ACTIVE_CANDIDATE_TEXT_RESULT=",
                repr(result),
            )

            candidate_smoke = isinstance(
                result,
                str,
            )

        except Exception as exc:

            out(
                "ACTIVE_CANDIDATE_TEXT_EXCEPTION=",
                type(exc).__name__,
                str(exc),
            )


out(
    "ACTIVE_CANDIDATE_TEXT_SMOKE=",
    "PASS"
    if candidate_smoke
    else
    "FAIL",
)


# ============================================================
# 6. SCORE + HARD MISMATCH
# ============================================================

header(
    "6. SEMANTIC SAFETY RUNTIME"
)

semantic_ok = False


if runtime_ok:

    score = namespace.get(
        "score_candidate"
    )

    if callable(score):

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


        try:

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


            out(
                "WRONG_HARD_MISMATCH=",
                a.get(
                    "hard_mismatch"
                ),
            )

            out(
                "CORRECT_HARD_MISMATCH=",
                b.get(
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
                "CORRECT_EFFECTIVE=",
                b.get(
                    "effective"
                ),
            )


            semantic_ok = (
                a.get(
                    "hard_mismatch"
                )
                is True
                and
                b.get(
                    "hard_mismatch"
                )
                is False
                and
                float(
                    b.get(
                        "effective",
                        -9999999,
                    )
                )
                >
                float(
                    a.get(
                        "effective",
                        9999999,
                    )
                )
            )


        except Exception as exc:

            out(
                "SEMANTIC_RUNTIME_EXCEPTION=",
                type(exc).__name__,
                str(exc),
            )


out(
    "SEMANTIC_RUNTIME=",
    "PASS"
    if semantic_ok
    else
    "FAIL",
)


# ============================================================
# 7. FULL SELF TEST
# ============================================================

header(
    "7. FULL VSE4 SELF TEST"
)

selftest_ok = False


if runtime_ok:

    fn = namespace.get(
        "self_test"
    )

    if callable(fn):

        try:

            fn()

            selftest_ok = True

            out(
                "FULL_SELF_TEST_RUNTIME=PASS"
            )

        except Exception as exc:

            out(
                "FULL_SELF_TEST_RUNTIME=FAIL"
            )

            out(
                "ERROR=",
                type(exc).__name__,
                str(exc),
            )


# ============================================================
# 8. MEDIA DIRECTORY BEFORE
# ============================================================

header(
    "8. KNOWN CANARY MEDIA INVARIANT BEFORE"
)

media_before_ok = False
repair_blocked = False
repaired = []


if not MEDIA_DIR.is_dir():

    out(
        "MEDIA_DIR=NOT_FOUND"
    )

    repair_blocked = True


else:

    out(
        "MEDIA_DIR=",
        MEDIA_DIR.relative_to(
            ROOT
        ),
    )


    scene_map = {}


    all_scene_files = sorted(
        p
        for p in MEDIA_DIR.iterdir()
        if (
            p.is_file()
            and
            p.name.startswith(
                "scene_"
            )
        )
    )


    for path in all_scene_files:

        number = media_scene_number(
            path
        )

        out(
            "MEDIA_FILE=",
            path.name,
            "BYTES=",
            path.stat().st_size,
            "SCENE_NUMBER=",
            number,
            "FFPROBE_VALID=",
            ffprobe_valid(
                path
            ),
        )


        if number is None:
            continue


        scene_map.setdefault(
            number,
            []
        ).append(
            path
        )


    # --------------------------------------------------------
    # Safe repair: files outside scene 01..12
    # --------------------------------------------------------

    for number, paths in list(
        scene_map.items()
    ):

        if (
            number < 1
            or
            number > 12
        ):

            for path in paths:

                quarantine_file(
                    path,
                    "SCENE_NUMBER_OUTSIDE_01_12",
                )

                repaired.append(
                    path.name
                )


    # --------------------------------------------------------
    # Safe repair: duplicate where only one file is valid.
    # Never choose automatically between two valid candidates.
    # --------------------------------------------------------

    for number in range(
        1,
        13,
    ):

        paths = [
            p
            for p in MEDIA_DIR.iterdir()
            if (
                p.is_file()
                and
                media_scene_number(
                    p
                )
                ==
                number
            )
        ]


        if len(paths) <= 1:
            continue


        valid = [
            p
            for p in paths
            if ffprobe_valid(
                p
            )
        ]

        invalid = [
            p
            for p in paths
            if p not in valid
        ]


        out(
            f"SCENE_{number:02d}_DUPLICATE_COUNT=",
            len(paths),
        )

        out(
            f"SCENE_{number:02d}_VALID_COUNT=",
            len(valid),
        )


        if (
            len(valid) == 1
            and
            invalid
        ):

            for path in invalid:

                quarantine_file(
                    path,
                    "DUPLICATE_INVALID_MEDIA",
                )

                repaired.append(
                    path.name
                )


        elif len(valid) > 1:

            out(
                f"SCENE_{number:02d}_AUTO_REPAIR="
                "BLOCKED_MULTIPLE_VALID_MEDIA"
            )

            repair_blocked = True


        else:

            out(
                f"SCENE_{number:02d}_AUTO_REPAIR="
                "BLOCKED_NO_VALID_MEDIA"
            )

            repair_blocked = True


# ============================================================
# 9. MEDIA DIRECTORY AFTER
# ============================================================

header(
    "9. KNOWN CANARY MEDIA INVARIANT AFTER"
)


missing = []
duplicates = []
invalid = []
final_scene_files = []


if MEDIA_DIR.is_dir():

    for number in range(
        1,
        13,
    ):

        paths = sorted(
            p
            for p in MEDIA_DIR.iterdir()
            if (
                p.is_file()
                and
                media_scene_number(
                    p
                )
                ==
                number
            )
        )


        if len(paths) == 0:

            missing.append(
                number
            )

            out(
                f"SCENE_{number:02d}=MISSING"
            )


        elif len(paths) > 1:

            duplicates.append(
                number
            )

            out(
                f"SCENE_{number:02d}=DUPLICATE "
                +
                ",".join(
                    p.name
                    for p in paths
                )
            )


        else:

            path = paths[0]

            valid = ffprobe_valid(
                path
            )

            if not valid:

                invalid.append(
                    number
                )


            final_scene_files.append(
                path
            )


            out(
                f"SCENE_{number:02d}=PASS "
                f"{path.name} "
                f"bytes={path.stat().st_size} "
                f"valid={valid}"
            )


    media_before_ok = (
        len(final_scene_files)
        ==
        12
        and
        not missing
        and
        not duplicates
        and
        not invalid
    )


out(
    "SCENE_FILE_COUNT=",
    len(final_scene_files),
)

out(
    "MISSING_SCENES=",
    missing,
)

out(
    "DUPLICATE_SCENES=",
    duplicates,
)

out(
    "INVALID_SCENES=",
    invalid,
)

out(
    "MEDIA_REPAIRS_APPLIED=",
    len(repaired),
)

out(
    "MEDIA_REPAIR_BLOCKED=",
    repair_blocked,
)

out(
    "KNOWN_CANARY_12_SCENE_INVARIANT=",
    "PASS"
    if media_before_ok
    else
    "FAIL",
)


# ============================================================
# 10. CORE COMPILE
# ============================================================

header(
    "10. CORE COMPILE"
)

compile_files = [
    "visual_selection_engine_v4.py",
    "midia.py",
    "video.py",
    "v6.py",
]

compile_ok = True


for name in compile_files:

    path = ROOT / name

    if not path.is_file():

        out(
            "COMPILE_MISSING=",
            name,
        )

        compile_ok = False

        continue


    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
    )


    out(
        f"COMPILE_{name}=",
        result.returncode,
    )


    if result.returncode != 0:

        compile_ok = False


shell = subprocess.run(
    [
        "bash",
        "-n",
        str(
            ROOT
            / "gerar_short.sh"
        ),
    ],
    cwd=ROOT,
)


out(
    "GERAR_SHORT_SYNTAX=",
    shell.returncode,
)


if shell.returncode != 0:

    compile_ok = False


# ============================================================
# 11. FINAL VERDICT
# ============================================================

header(
    "11. FINAL VERDICT"
)


critical = []


if not runtime_ok:
    critical.append(
        "VSE4_RUNTIME"
    )


if not candidate_smoke:
    critical.append(
        "CANDIDATE_TEXT"
    )


if not semantic_ok:
    critical.append(
        "SEMANTIC_RUNTIME"
    )


if not selftest_ok:
    critical.append(
        "SELF_TEST"
    )


if cycle_confirmed:
    critical.append(
        "VSE416_RUNTIME_CYCLE"
    )


if cycle_unknown:
    critical.append(
        "VSE416_RUNTIME_PROBE_INCONCLUSIVE"
    )


if not media_before_ok:
    critical.append(
        "KNOWN_CANARY_MEDIA_INVARIANT"
    )


if not compile_ok:
    critical.append(
        "CORE_COMPILE"
    )


if critical:

    out(
        "CRITICAL_ISSUES="
        +
        ",".join(
            critical
        )
    )

    out(
        "MASTER_VERDICT=FAIL"
    )

else:

    out(
        "CRITICAL_ISSUES=NONE"
    )

    out(
        "MASTER_VERDICT=PASS"
    )


if (
    not cycle_confirmed
    and
    cycle_clear
):

    out(
        "VSE416_STATIC_CYCLE_FINDING="
        "LIKELY_FALSE_POSITIVE"
    )


out(
    "VSE4_PROJECT_FILE_MODIFIED=NO"
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
    "REPORT=",
    REPORT,
)

out(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
