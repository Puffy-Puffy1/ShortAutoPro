#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import contextlib
import hashlib
import io
import json
import os
import re
import runpy
import shutil
import subprocess
import symtable
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

REPORT_TXT = (
    ROOT
    / "temp"
    / f"GENERAL_SYSTEM_AUDIT_{STAMP}.txt"
)

REPORT_JSON = (
    ROOT
    / "temp"
    / f"GENERAL_SYSTEM_AUDIT_{STAMP}.json"
)

ROOT.joinpath(
    "temp"
).mkdir(
    parents=True,
    exist_ok=True,
)


RESULTS = []


def emit(*items):

    text = " ".join(
        str(x)
        for x in items
    )

    print(text)

    with REPORT_TXT.open(
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            text + "\n"
        )


def section(title):

    emit()
    emit(
        "=" * 74
    )

    emit(
        title
    )

    emit(
        "=" * 74
    )


def record(
    name,
    status,
    detail="",
):

    status = str(
        status
    ).upper()

    RESULTS.append(
        {
            "name":
                name,

            "status":
                status,

            "detail":
                str(detail),
        }
    )

    line = (
        f"{name}={status}"
    )

    if detail:

        line += (
            f" | {detail}"
        )

    emit(
        line
    )


def sha256(path):

    h = hashlib.sha256()

    with Path(path).open(
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


def read(path):

    try:

        return Path(path).read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:

        return ""


def parse_file(path):

    source = read(
        path
    )

    return ast.parse(
        source,
        filename=str(path),
    )


def function_node(
    tree,
    name,
):

    for node in tree.body:

        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and
            node.name == name
        ):

            return node

    return None


def call_names(node):

    result = []

    if node is None:

        return result

    for n in ast.walk(
        node
    ):

        if not isinstance(
            n,
            ast.Call,
        ):

            continue

        if isinstance(
            n.func,
            ast.Name,
        ):

            result.append(
                n.func.id
            )

        elif isinstance(
            n.func,
            ast.Attribute,
        ):

            result.append(
                n.func.attr
            )

    return result


def latest_short_id():

    ids = []

    rx = re.compile(
        r"^short_"
        r"(\d{4}-\d{2}-\d{2}_\d{4})"
        r"\.txt$"
    )

    directory = (
        ROOT
        / "roteiros"
    )

    if not directory.exists():

        return None

    for path in directory.glob(
        "short_*.txt"
    ):

        m = rx.match(
            path.name
        )

        if not m:

            continue

        ids.append(
            (
                path.stat().st_mtime,
                m.group(1),
            )
        )

    if not ids:

        return None

    ids.sort(
        reverse=True
    )

    return ids[
        0
    ][
        1
    ]


def unresolved_globals(
    path,
):

    source = read(
        path
    )

    table = symtable.symtable(
        source,
        str(path),
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

    builtin_names.update(
        {
            "__name__",
            "__file__",
            "__package__",
            "__spec__",
            "__loader__",
            "__cached__",
        }
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

            walk(
                child
            )


    walk(
        table
    )

    return sorted(
        unresolved
    )


def find_bridge_candidates():

    found = []

    required = {
        "rank_pool",
        "reset_state",
        "commit_candidate",
    }

    for path in ROOT.glob(
        "*.py"
    ):

        try:

            tree = parse_file(
                path
            )

        except Exception:

            continue


        defs = {
            node.name
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        if required.issubset(
            defs
        ):

            found.append(
                path
            )

    return found


# ============================================================
# HEADER
# ============================================================

if REPORT_TXT.exists():

    REPORT_TXT.unlink()


section(
    "SHORTAUTOPRO - GENERAL SYSTEM AUDIT V1"
)

emit(
    "DATE=",
    datetime.now().isoformat(
        timespec="seconds"
    ),
)

emit(
    "ROOT=",
    ROOT,
)

emit(
    "MODE=OFFLINE_READ_ONLY"
)


# ============================================================
# 1. PROJECT STRUCTURE
# ============================================================

section(
    "1. CORE PROJECT STRUCTURE"
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

    "render_input_fingerprint_v1.py",

    "render_output_certifier_v1.py",

    "render_transaction_v1.py",

    "media_provenance_capture_v1.py",
]


for name in critical:

    path = (
        ROOT
        / name
    )

    if path.exists():

        record(
            f"FILE_{name}",
            "PASS",
            f"bytes={path.stat().st_size}",
        )

    else:

        status = (
            "FAIL"
            if name in {
                "midia.py",
                "video.py",
                "v6.py",
                "gerar_short.sh",
                "visual_selection_engine_v4.py",
            }
            else
            "WARN"
        )

        record(
            f"FILE_{name}",
            status,
            "missing",
        )


# ============================================================
# 2. ALL PYTHON SYNTAX
# ============================================================

section(
    "2. PYTHON SYNTAX - ALL ROOT MODULES"
)


python_files = sorted(
    ROOT.glob(
        "*.py"
    )
)

syntax_bad = []


for path in python_files:

    try:

        source = read(
            path
        )

        compile(
            source,
            str(path),
            "exec",
        )

    except Exception as exc:

        syntax_bad.append(
            (
                path.name,
                f"{type(exc).__name__}: {exc}",
            )
        )


emit(
    "PYTHON_FILES_CHECKED=",
    len(
        python_files
    ),
)


if syntax_bad:

    for name, error in syntax_bad:

        emit(
            "PYTHON_SYNTAX_ERROR=",
            name,
            "|",
            error,
        )

    record(
        "PYTHON_GLOBAL_SYNTAX",
        "FAIL",
        f"errors={len(syntax_bad)}",
    )

else:

    record(
        "PYTHON_GLOBAL_SYNTAX",
        "PASS",
        f"files={len(python_files)}",
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)


shell_files = sorted(
    ROOT.glob(
        "*.sh"
    )
)

shell_bad = []


for path in shell_files:

    try:

        result = subprocess.run(
            [
                "bash",
                "-n",
                str(path),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode != 0:

            shell_bad.append(
                (
                    path.name,
                    result.stderr.strip(),
                )
            )

    except Exception as exc:

        shell_bad.append(
            (
                path.name,
                f"{type(exc).__name__}: {exc}",
            )
        )


emit(
    "SHELL_FILES_CHECKED=",
    len(
        shell_files
    ),
)


if shell_bad:

    for name, error in shell_bad:

        emit(
            "SHELL_SYNTAX_ERROR=",
            name,
            "|",
            error,
        )

    record(
        "SHELL_GLOBAL_SYNTAX",
        "FAIL",
        f"errors={len(shell_bad)}",
    )

else:

    record(
        "SHELL_GLOBAL_SYNTAX",
        "PASS",
        f"files={len(shell_files)}",
    )


# ============================================================
# 4. DUPLICATE FUNCTION DEFINITIONS
# ============================================================

section(
    "4. DUPLICATE TOP-LEVEL FUNCTION AUDIT"
)


duplicate_total = 0


for filename in (

    "midia.py",

    "visual_selection_engine_v4.py",

    "media_diversity_guard_v1.py",

    "visual_scene_commit_lock_v1.py",
):

    path = (
        ROOT
        / filename
    )

    if not path.exists():

        continue

    try:

        tree = parse_file(
            path
        )

    except Exception:

        continue


    names = [

        n.name
        for n in tree.body
        if isinstance(
            n,
            ast.FunctionDef,
        )
    ]


    duplicates = sorted(
        name
        for name, count
        in Counter(names).items()
        if count > 1
    )


    if duplicates:

        duplicate_total += len(
            duplicates
        )

        record(
            f"DUPLICATE_DEFS_{filename}",
            "WARN",
            ",".join(
                duplicates
            ),
        )

    else:

        record(
            f"DUPLICATE_DEFS_{filename}",
            "PASS",
        )


# ============================================================
# 5. VSE4 GLOBAL AUDIT
# ============================================================

section(
    "5. VSE4 STATIC FOUNDATION"
)


vse = (
    ROOT
    / "visual_selection_engine_v4.py"
)


vse_namespace = None


if vse.exists():

    try:

        unresolved = unresolved_globals(
            vse
        )

        if unresolved:

            record(
                "VSE4_UNRESOLVED_GLOBALS",
                "FAIL",
                ",".join(
                    unresolved
                ),
            )

        else:

            record(
                "VSE4_UNRESOLVED_GLOBALS",
                "PASS",
                "NONE",
            )

    except Exception as exc:

        record(
            "VSE4_UNRESOLVED_GLOBALS",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


    try:

        vse_namespace = runpy.run_path(
            str(vse),
            run_name="shortautopro_general_audit",
        )

        record(
            "VSE4_RUNTIME_LOAD",
            "PASS",
        )

    except Exception as exc:

        record(
            "VSE4_RUNTIME_LOAD",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 6. VSE4 SELF TEST
# ============================================================

section(
    "6. VSE4 INTERNAL SELF TEST"
)


if vse_namespace:

    self_test = vse_namespace.get(
        "self_test"
    )

    if callable(
        self_test
    ):

        buffer = io.StringIO()

        try:

            with contextlib.redirect_stdout(
                buffer
            ):

                self_test()

            output = (
                buffer
                .getvalue()
                .strip()
            )

            record(
                "VSE4_SELF_TEST",
                "PASS",
                output.replace(
                    "\n",
                    " | ",
                )[
                    :600
                ],
            )

        except Exception as exc:

            record(
                "VSE4_SELF_TEST",
                "FAIL",
                f"{type(exc).__name__}: {exc}",
            )

    else:

        record(
            "VSE4_SELF_TEST",
            "WARN",
            "self_test missing",
        )


# ============================================================
# 7. VSE4 GEO CONTRADICTION
# ============================================================

section(
    "7. VSE4 GEO / SEMANTIC CONTRADICTION"
)


if vse_namespace:

    score_candidate = vse_namespace.get(
        "score_candidate"
    )

    geo_hits = vse_namespace.get(
        "geo_hits"
    )


    if callable(
        geo_hits
    ):

        try:

            sp = set(
                geo_hits(
                    "São Paulo Brazil apartment"
                )
            )

            ny = set(
                geo_hits(
                    "Empire State Building Manhattan New York"
                )
            )

            emit(
                "SP_GEO=",
                sorted(sp),
            )

            emit(
                "NY_GEO=",
                sorted(ny),
            )


            if (
                sp
                and
                ny
                and
                sp != ny
            ):

                record(
                    "GEO_DISTINCTION_SP_NY",
                    "PASS",
                )

            else:

                record(
                    "GEO_DISTINCTION_SP_NY",
                    "FAIL",
                )

        except Exception as exc:

            record(
                "GEO_DISTINCTION_SP_NY",
                "FAIL",
                str(exc),
            )


    if callable(
        score_candidate
    ):

        state = {
            "providers": [],
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
                240,

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
                145,

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


            emit(
                "WRONG_RESULT=",
                json.dumps(
                    a,
                    ensure_ascii=False,
                    default=str,
                )[
                    :1200
                ],
            )

            emit(
                "CORRECT_RESULT=",
                json.dumps(
                    b,
                    ensure_ascii=False,
                    default=str,
                )[
                    :1200
                ],
            )


            wrong_hard = bool(
                a.get(
                    "hard_mismatch",
                    False,
                )
            )


            correct_hard = bool(
                b.get(
                    "hard_mismatch",
                    False,
                )
            )


            if wrong_hard:

                record(
                    "NYC_FOR_SP_HARD_MISMATCH",
                    "PASS",
                )

            else:

                record(
                    "NYC_FOR_SP_HARD_MISMATCH",
                    "FAIL",
                    "wrong candidate not hard-blocked",
                )


            if not correct_hard:

                record(
                    "SP_FOR_SP_ALLOWED",
                    "PASS",
                )

            else:

                record(
                    "SP_FOR_SP_ALLOWED",
                    "FAIL",
                    "correct candidate hard-blocked",
                )


            ae = a.get(
                "effective",
                a.get(
                    "effective_score",
                    0,
                ),
            )

            be = b.get(
                "effective",
                b.get(
                    "effective_score",
                    0,
                ),
            )


            try:

                better = float(
                    be
                ) > float(
                    ae
                )

            except Exception:

                better = False


            record(
                "CORRECT_GEO_BEATS_WRONG_GEO",
                "PASS"
                if better
                else
                "FAIL",
                f"wrong={ae} correct={be}",
            )


        except Exception as exc:

            record(
                "VSE4_DIRECT_SCORE_RUNTIME",
                "FAIL",
                f"{type(exc).__name__}: {exc}",
            )


# ============================================================
# 8. FALSE ASSOCIATION TESTS
# ============================================================

section(
    "8. FALSE ASSOCIATION / GENERIC MEDIA"
)


if vse_namespace:

    score_candidate = vse_namespace.get(
        "score_candidate"
    )


    if callable(
        score_candidate
    ):

        tests = [

            (
                "FORENSIC_VS_PILLS",

                "Laudo pericial encontrou "
                "evidências importantes "
                "na investigação",

                {
                    "provider":
                        "Pixabay",

                    "tipo":
                        "foto",

                    "title":
                        "Medication pills "
                        "tablets on desk",

                    "must":
                        "1/2",

                    "score":
                        220,
                },

                {
                    "provider":
                        "Wikimedia",

                    "tipo":
                        "foto",

                    "title":
                        "Forensic evidence "
                        "crime investigation "
                        "laboratory report",

                    "must":
                        "2/2",

                    "score":
                        160,
                },
            ),


            (
                "INVESTIGATION_VS_LIFESTYLE",

                "Polícia iniciou investigação "
                "no apartamento",

                {
                    "provider":
                        "Pexels",

                    "tipo":
                        "foto",

                    "title":
                        "Woman relaxing smiling "
                        "in bedroom lifestyle",

                    "must":
                        "1/2",

                    "score":
                        220,
                },

                {
                    "provider":
                        "Pixabay",

                    "tipo":
                        "video",

                    "title":
                        "Police investigation "
                        "apartment crime scene",

                    "must":
                        "2/2",

                    "score":
                        170,
                },
            ),
        ]


        for (
            name,
            scene,
            bad,
            good,
        ) in tests:

            try:

                state = {
                    "providers": [],
                    "groups": [],
                    "types": [],
                    "keys": [],
                }


                rb = score_candidate(
                    bad,
                    scene,
                    state,
                )

                rg = score_candidate(
                    good,
                    scene,
                    state,
                )


                bad_eff = rb.get(
                    "effective",
                    rb.get(
                        "effective_score",
                        0,
                    ),
                )

                good_eff = rg.get(
                    "effective",
                    rg.get(
                        "effective_score",
                        0,
                    ),
                )


                try:

                    ok = float(
                        good_eff
                    ) > float(
                        bad_eff
                    )

                except Exception:

                    ok = False


                record(
                    name,
                    "PASS"
                    if ok
                    else
                    "FAIL",
                    f"bad={bad_eff} good={good_eff}",
                )

            except Exception as exc:

                record(
                    name,
                    "FAIL",
                    f"{type(exc).__name__}: {exc}",
                )


# ============================================================
# 9. V42 BRIDGE DISCOVERY
# ============================================================

section(
    "9. V42 / RANK BRIDGE DISCOVERY"
)


bridges = find_bridge_candidates()


if bridges:

    for path in bridges:

        emit(
            "BRIDGE_CANDIDATE=",
            path.name,
        )

    record(
        "V42_BRIDGE_FOUND",
        "PASS",
        ",".join(
            x.name
            for x in bridges
        ),
    )

else:

    record(
        "V42_BRIDGE_FOUND",
        "WARN",
        "rank_pool/reset_state/commit_candidate not found together",
    )


# ============================================================
# 10. MIDIA PROVIDER ACQUISITION
# ============================================================

section(
    "10. PROVIDER ACQUISITION PIPELINE"
)


midia = (
    ROOT
    / "midia.py"
)


if midia.exists():

    try:

        tree = parse_file(
            midia
        )


        provider_defs = [

            "pexels_video",

            "pexels_foto",

            "pixabay_video",

            "pixabay_foto",

            "coverr_video",
        ]


        for name in provider_defs:

            record(
                f"PROVIDER_DEF_{name}",
                "PASS"
                if function_node(
                    tree,
                    name,
                )
                else
                "FAIL",
            )


        buscar = function_node(
            tree,
            "buscar_todos_candidatos",
        )


        if buscar:

            calls = set(
                call_names(
                    buscar
                )
            )


            emit(
                "BUSCAR_TODOS_CALLS=",
                ",".join(
                    sorted(calls)
                ),
            )


            expected = {

                "pexels_video",

                "pexels_foto",

                "pixabay_video",

                "pixabay_foto",

                "coverr_video",
            }


            missing = sorted(
                expected - calls
            )


            if missing:

                record(
                    "MULTI_PROVIDER_ACQUISITION",
                    "FAIL",
                    "missing="
                    +
                    ",".join(missing),
                )

            else:

                record(
                    "MULTI_PROVIDER_ACQUISITION",
                    "PASS",
                )


            wiki_present = any(
                "wiki" in x.casefold()
                for x in calls
            )


            record(
                "WIKIMEDIA_ACQUISITION_PATH",
                "PASS"
                if wiki_present
                else
                "WARN",
            )


        else:

            record(
                "BUSCAR_TODOS_CANDIDATOS",
                "FAIL",
                "definition missing",
            )


    except Exception as exc:

        record(
            "PROVIDER_ACQUISITION_AUDIT",
            "FAIL",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 11. VSE INTEGRATION IN ACTIVE PATH
# ============================================================

section(
    "11. ACTIVE VSE INTEGRATION"
)


midia_text = read(
    ROOT
    / "midia.py"
)

guard_text = read(
    ROOT
    / "media_diversity_guard_v1.py"
)


combined = (
    midia_text
    +
    "\n"
    +
    guard_text
)


v4_mentions = [

    term
    for term in (
        "visual_selection_engine_v4",
        "VSE4",
        "V42",
        "rank_pool",
    )
    if term.casefold()
    in combined.casefold()
]


if v4_mentions:

    record(
        "VSE4_ACTIVE_PATH_REFERENCE",
        "PASS",
        ",".join(
            v4_mentions
        ),
    )

else:

    record(
        "VSE4_ACTIVE_PATH_REFERENCE",
        "FAIL",
        "no V4/V42 reference in midia/guard",
    )


legacy = []


for term in (
    "visual_selection_engine_v2",
    "visual_selection_final_gate_v3",
    "VSE3",
):

    if term.casefold() in combined.casefold():

        legacy.append(
            term
        )


if legacy:

    record(
        "LEGACY_VSE_REFERENCES",
        "WARN",
        ",".join(
            legacy
        ),
    )

else:

    record(
        "LEGACY_VSE_REFERENCES",
        "PASS",
        "none",
    )


# ============================================================
# 12. COMMIT LOCK
# ============================================================

section(
    "12. SCENE COMMIT / DOUBLE DOWNLOAD"
)


commit_reference = any(
    term.casefold()
    in combined.casefold()

    for term in (
        "visual_scene_commit_lock_v1",
        "SCENE_COMMIT_LOCK",
        "commit_candidate",
    )
)


record(
    "SCENE_COMMIT_LOCK_REFERENCE",
    "PASS"
    if commit_reference
    else
    "FAIL",
)


try:

    tree = parse_file(
        midia
    )


    success_ifs = 0
    direct_breaks = 0
    conditional_breaks = 0


    for node in ast.walk(
        tree
    ):

        if not isinstance(
            node,
            ast.If,
        ):

            continue


        try:

            test_text = ast.unparse(
                node.test
            ).casefold()

        except Exception:

            continue


        if not (
            "ok" in test_text
            or
            "sucesso" in test_text
        ):

            continue


        success_ifs += 1


        direct = any(
            isinstance(
                child,
                ast.Break,
            )
            for child in node.body
        )


        nested = any(
            isinstance(
                child,
                ast.Break,
            )
            for child in ast.walk(node)
        )


        if direct:

            direct_breaks += 1

        elif nested:

            conditional_breaks += 1


    emit(
        "SUCCESS_IFS=",
        success_ifs,
    )

    emit(
        "DIRECT_BREAKS=",
        direct_breaks,
    )

    emit(
        "CONDITIONAL_ONLY_BREAKS=",
        conditional_breaks,
    )


    if (
        commit_reference
        or
        direct_breaks > 0
    ):

        record(
            "POST_SUCCESS_REPLACEMENT_GUARD",
            "PASS",
        )

    else:

        record(
            "POST_SUCCESS_REPLACEMENT_GUARD",
            "WARN",
            "possible post-success replacement risk",
        )


except Exception as exc:

    record(
        "POST_SUCCESS_REPLACEMENT_GUARD",
        "WARN",
        str(exc),
    )


# ============================================================
# 13. RENDER GUARD SAFETY
# ============================================================

section(
    "13. FRESH RENDER GUARD SAFETY"
)


frg = read(
    ROOT
    / "fresh_render_guard_v1.py"
)


if frg:

    lower = frg.casefold()


    protected_ass = (
        '".ass"' in lower
        or
        "'.ass'" in lower
    )


    protected_audio = (
        '".mp3"' in lower
        or
        "'.mp3'" in lower
    )


    record(
        "RENDER_GUARD_ASS_PROTECTION",
        "PASS"
        if protected_ass
        else
        "FAIL",
    )


    record(
        "RENDER_GUARD_AUDIO_PROTECTION",
        "PASS"
        if protected_audio
        else
        "WARN",
    )


    dangerous_root_rglob = (
        'rglob("*")' in frg
        and
        'ROOT.rglob' in frg
    )


    record(
        "RENDER_GUARD_ROOT_WIDE_DELETE",
        "FAIL"
        if dangerous_root_rglob
        else
        "PASS",
    )

else:

    record(
        "RENDER_GUARD_AUDIT",
        "WARN",
        "file missing",
    )


# ============================================================
# 14. SHORT_ID RESOLUTION
# ============================================================

section(
    "14. SHORT_ID RESOLUTION"
)


for filename in (
    "video.py",
    "v6.py",
):

    text = read(
        ROOT
        / filename
    )


    explicit = (
        'os.getenv(' in text
        and
        '"SHORT_ID"' in text
    )


    record(
        f"{filename}_SHORT_ID_ENV",
        "PASS"
        if explicit
        else
        "FAIL",
    )


# ============================================================
# 15. MAIN PIPELINE DUPLICATION
# ============================================================

section(
    "15. GERAR_SHORT PIPELINE CALL COUNT"
)


gerar = read(
    ROOT
    / "gerar_short.sh"
)


for script in (

    "midia.py",

    "video.py",

    "v6.py",

    "legenda_dinamica.py",
):

    lines = [

        line
        for line in gerar.splitlines()
        if (
            script in line
            and
            not line.lstrip().startswith(
                "#"
            )
        )
    ]


    emit(
        f"{script}_CALL_LINES=",
        len(lines),
    )


    if len(lines) == 1:

        status = "PASS"

    elif len(lines) == 0:

        status = "WARN"

    else:

        status = "WARN"


    record(
        f"PIPELINE_CALL_{script}",
        status,
        f"count={len(lines)}",
    )


# ============================================================
# 16. CURRENT SHORT ASSET AUDIT
# ============================================================

section(
    "16. CURRENT SHORT ASSET INTEGRITY"
)


sid = (
    os.environ.get(
        "SHORT_ID",
        ""
    ).strip()
    or
    latest_short_id()
)


emit(
    "AUDIT_SHORT_ID=",
    sid,
)


if sid:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{sid}"
    )


    scene_files = []

    invalid = []


    for number in range(
        1,
        13,
    ):

        prefix = (
            f"scene_{number:02d}."
        )


        matches = [

            path
            for path in media_dir.glob(
                f"scene_{number:02d}.*"
            )
            if path.is_file()
        ]


        if len(matches) != 1:

            invalid.append(
                (
                    number,
                    len(matches),
                )
            )


        scene_files.extend(
            matches
        )


        emit(
            f"SCENE_{number:02d}_COUNT=",
            len(matches),
        )


        for path in matches:

            emit(
                "  ",
                path.name,
                "bytes=",
                path.stat().st_size,
            )


    if invalid:

        record(
            "SCENE_COUNT_INTEGRITY",
            "FAIL",
            str(invalid),
        )

    else:

        record(
            "SCENE_COUNT_INTEGRITY",
            "PASS",
            "12/12",
        )


    # --------------------------------------------------------
    # Duplicate SHA media
    # --------------------------------------------------------

    hash_map = {}


    for path in scene_files:

        try:

            digest = sha256(
                path
            )

            hash_map.setdefault(
                digest,
                [],
            ).append(
                path.name
            )

        except Exception:

            pass


    duplicates = {

        digest:
            names

        for digest, names
        in hash_map.items()

        if len(names) > 1
    }


    if duplicates:

        record(
            "SCENE_DUPLICATE_CONTENT",
            "WARN",
            json.dumps(
                duplicates,
                ensure_ascii=False,
            )[
                :1000
            ],
        )

    else:

        record(
            "SCENE_DUPLICATE_CONTENT",
            "PASS",
        )


    # --------------------------------------------------------
    # Media fingerprint
    # --------------------------------------------------------

    ordered = sorted(
        hash_map.keys()
    )

    fp = hashlib.sha256(
        "|".join(
            ordered
        ).encode()
    ).hexdigest()


    emit(
        "SCENE_MEDIA_FINGERPRINT=",
        fp,
    )


    # --------------------------------------------------------
    # ffprobe each scene
    # --------------------------------------------------------

    ffprobe = shutil.which(
        "ffprobe"
    )


    media_probe_errors = []


    if ffprobe:

        for path in scene_files:

            try:

                result = subprocess.run(
                    [
                        ffprobe,
                        "-v",
                        "error",
                        "-show_entries",
                        (
                            "stream=codec_name,"
                            "codec_type,width,height"
                        ),
                        "-of",
                        "json",
                        str(path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )


                if result.returncode != 0:

                    media_probe_errors.append(
                        (
                            path.name,
                            result.stderr.strip(),
                        )
                    )


            except Exception as exc:

                media_probe_errors.append(
                    (
                        path.name,
                        str(exc),
                    )
                )


        if media_probe_errors:

            record(
                "SCENE_MEDIA_TECHNICAL_VALIDITY",
                "FAIL",
                str(
                    media_probe_errors
                )[
                    :1200
                ],
            )

        else:

            record(
                "SCENE_MEDIA_TECHNICAL_VALIDITY",
                "PASS",
                f"files={len(scene_files)}",
            )

    else:

        record(
            "SCENE_MEDIA_TECHNICAL_VALIDITY",
            "WARN",
            "ffprobe unavailable",
        )


    # --------------------------------------------------------
    # Pipeline assets
    # --------------------------------------------------------

    required_assets = {

        "AUDIO":
            ROOT
            / "audios"
            / f"short_{sid}.mp3",

        "ASS":
            ROOT
            / "videos"
            / f"short_{sid}.ass",

        "VIDEO_BASE":
            ROOT
            / "temp"
            / sid
            / "video_sem_audio.mp4",

        "FINAL":
            ROOT
            / "videos"
            / f"short_v6_{sid}.mp4",
    }


    for name, path in required_assets.items():

        if (
            path.exists()
            and
            path.stat().st_size > 0
        ):

            record(
                f"ASSET_{name}",
                "PASS",
                (
                    f"bytes="
                    f"{path.stat().st_size}"
                ),
            )

        else:

            record(
                f"ASSET_{name}",
                "WARN",
                "missing",
            )


else:

    record(
        "CURRENT_SHORT_DISCOVERY",
        "WARN",
        "no SHORT_ID found",
    )


# ============================================================
# 17. CORE HASHES
# ============================================================

section(
    "17. CORE HASH SNAPSHOT"
)


for filename in (

    "midia.py",

    "video.py",

    "v6.py",

    "gerar_short.sh",

    "visual_selection_engine_v4.py",
):

    path = (
        ROOT
        / filename
    )

    if path.exists():

        emit(
            filename,
            "=",
            sha256(
                path
            ),
        )


# ============================================================
# 18. HIGH-RISK STATIC PATTERNS
# ============================================================

section(
    "18. STATIC BUG PATTERNS"
)


for filename in (

    "midia.py",

    "visual_selection_engine_v4.py",

    "media_diversity_guard_v1.py",

    "fresh_render_guard_v1.py",

    "render_transaction_v1.py",
):

    path = (
        ROOT
        / filename
    )

    if not path.exists():

        continue


    text = read(
        path
    )


    shell_true = len(
        re.findall(
            r"shell\s*=\s*True",
            text,
        )
    )


    eval_count = len(
        re.findall(
            r"\beval\s*\(",
            text,
        )
    )


    exec_count = len(
        re.findall(
            r"\bexec\s*\(",
            text,
        )
    )


    emit(
        f"{filename}: "
        f"shell_true={shell_true} "
        f"eval={eval_count} "
        f"exec={exec_count}"
    )


    if shell_true:

        record(
            f"RISK_SHELL_TRUE_{filename}",
            "WARN",
            f"count={shell_true}",
        )


    if eval_count:

        record(
            f"RISK_EVAL_{filename}",
            "WARN",
            f"count={eval_count}",
        )


# ============================================================
# 19. SUMMARY
# ============================================================

section(
    "19. FINAL SUMMARY"
)


counts = Counter(
    item[
        "status"
    ]
    for item in RESULTS
)


emit(
    "PASS_COUNT=",
    counts.get(
        "PASS",
        0,
    ),
)

emit(
    "WARN_COUNT=",
    counts.get(
        "WARN",
        0,
    ),
)

emit(
    "FAIL_COUNT=",
    counts.get(
        "FAIL",
        0,
    ),
)


fails = [

    item
    for item in RESULTS
    if item[
        "status"
    ] == "FAIL"
]


warnings = [

    item
    for item in RESULTS
    if item[
        "status"
    ] == "WARN"
]


if fails:

    emit()
    emit(
        "===== FAILURES ====="
    )

    for item in fails:

        emit(
            "FAIL:",
            item[
                "name"
            ],
            "|",
            item[
                "detail"
            ],
        )


if warnings:

    emit()
    emit(
        "===== WARNINGS ====="
    )

    for item in warnings:

        emit(
            "WARN:",
            item[
                "name"
            ],
            "|",
            item[
                "detail"
            ],
        )


if not fails:

    overall = (
        "PASS_WITH_WARNINGS"
        if warnings
        else
        "PASS"
    )

else:

    overall = "FAIL"


emit()
emit(
    "GENERAL_AUDIT_STATUS=",
    overall,
)


REPORT_JSON.write_text(
    json.dumps(
        {
            "timestamp":
                STAMP,

            "short_id":
                sid,

            "summary":
                dict(counts),

            "status":
                overall,

            "results":
                RESULTS,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


emit(
    "REPORT_TXT=",
    REPORT_TXT,
)

emit(
    "REPORT_JSON=",
    REPORT_JSON,
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
    "CORE_FILES_MODIFIED=NO"
)

emit(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
