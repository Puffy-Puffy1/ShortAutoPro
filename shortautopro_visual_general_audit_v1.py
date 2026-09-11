#!/usr/bin/env python3

from pathlib import Path
import ast
import builtins
import hashlib
import inspect
import json
import os
import re
import runpy
import subprocess
import symtable
import traceback


ROOT = Path.home() / "ShortAutoPro"
REPORT = ROOT / "temp" / "VISUAL_GENERAL_AUDIT_V1.txt"

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


PASS = []
FAIL = []
WARN = []


def log(*args):

    text = " ".join(
        str(x)
        for x in args
    )

    print(text)

    with REPORT.open(
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            text + "\n"
        )


def section(name):

    log()
    log("=" * 78)
    log(name)
    log("=" * 78)


def result(name, ok, detail=""):

    status = (
        "PASS"
        if ok
        else
        "FAIL"
    )

    log(
        f"{name}={status}",
        detail,
    )

    if ok:
        PASS.append(name)
    else:
        FAIL.append(name)


def warning(name, detail=""):

    WARN.append(name)

    log(
        f"{name}=WARN",
        detail,
    )


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(chunk)

    return h.hexdigest()


def compile_python(path):

    p = subprocess.run(
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

    return (
        p.returncode,
        p.stderr.strip(),
    )


def shell_syntax(path):

    p = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return (
        p.returncode,
        p.stderr.strip(),
    )


def load_module(filename, run_name):

    return runpy.run_path(
        str(
            ROOT / filename
        ),
        run_name=run_name,
    )


REPORT.write_text(
    "",
    encoding="utf-8",
)


section(
    "SHORTAUTOPRO VISUAL GENERAL AUDIT V1"
)

log(
    "ROOT=",
    ROOT,
)

log(
    "NETWORK_ALLOWED=NO"
)

log(
    "MIDIA_EXECUTION=NO"
)

log(
    "VIDEO_RENDER=NO"
)


# ============================================================
# 1. CRITICAL FILE INVENTORY
# ============================================================

section(
    "1. CRITICAL FILE INVENTORY"
)


critical = [

    "midia.py",
    "gerar_short.sh",

    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",

    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",

    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",

    "video.py",
    "v6.py",

    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


for name in critical:

    path = ROOT / name

    exists = path.is_file()

    result(
        f"FILE_{name}",
        exists,
    )

    if exists:

        log(
            f"HASH_{name}="
            f"{sha256(path)}"
        )


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section(
    "2. PYTHON CORE COMPILE"
)


python_core = [

    "midia.py",

    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",

    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",

    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",

    "video.py",
    "v6.py",

    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


for name in python_core:

    path = ROOT / name

    if not path.is_file():
        continue

    code, stderr = compile_python(
        path
    )

    result(
        f"COMPILE_{name}",
        code == 0,
        stderr,
    )


# ============================================================
# 3. ALL TOP-LEVEL PYTHON AST
# ============================================================

section(
    "3. TOP-LEVEL PYTHON AST AUDIT"
)


ast_failures = []


for path in sorted(
    ROOT.glob("*.py")
):

    try:

        ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception as exc:

        ast_failures.append(
            (
                path.name,
                type(exc).__name__,
                str(exc),
            )
        )


if ast_failures:

    for item in ast_failures:

        log(
            "AST_FAILURE=",
            item,
        )


result(
    "TOP_LEVEL_AST",
    not ast_failures,
    f"files={len(list(ROOT.glob('*.py')))} "
    f"failures={len(ast_failures)}",
)


# ============================================================
# 4. SHELL SYNTAX
# ============================================================

section(
    "4. SHELL SYNTAX"
)


shell_fail = []


for path in sorted(
    ROOT.glob("*.sh")
):

    code, stderr = shell_syntax(
        path
    )

    if code != 0:

        shell_fail.append(
            (
                path.name,
                stderr,
            )
        )

        log(
            f"SHELL_FAIL={path.name}",
            stderr,
        )


result(
    "TOP_LEVEL_SHELL_SYNTAX",
    not shell_fail,
    f"scripts={len(list(ROOT.glob('*.sh')))} "
    f"failures={len(shell_fail)}",
)


# ============================================================
# 5. VSE4 GLOBAL SYMBOL AUDIT
# ============================================================

section(
    "5. VSE4 GLOBAL SYMBOL AUDIT"
)


vse_path = (
    ROOT
    /
    "visual_selection_engine_v4.py"
)


if vse_path.is_file():

    try:

        src = vse_path.read_text(
            encoding="utf-8"
        )

        table = symtable.symtable(
            src,
            str(vse_path),
            "exec",
        )


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


        unresolved = set()

        builtin_names = set(
            dir(builtins)
        )


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

                    if name in module_defined:
                        continue

                    if name in builtin_names:
                        continue

                    unresolved.add(
                        name
                    )

                walk(child)


        walk(table)


        log(
            "VSE4_MODULE_DEFINED=",
            len(module_defined),
        )


        if unresolved:

            log(
                "VSE4_UNRESOLVED_GLOBALS="
                +
                ",".join(
                    sorted(unresolved)
                )
            )

        else:

            log(
                "VSE4_UNRESOLVED_GLOBALS=NONE"
            )


        result(
            "VSE4_GLOBAL_AUDIT",
            not unresolved,
        )


    except Exception as exc:

        result(
            "VSE4_GLOBAL_AUDIT",
            False,
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 6. VSE4 LOAD + API
# ============================================================

section(
    "6. VSE4 RUNTIME/API"
)


vse = None


try:

    vse = load_module(
        "visual_selection_engine_v4.py",
        "visual_general_audit_vse4",
    )

    result(
        "VSE4_LOAD",
        True,
    )


    required_vse = [

        "score_candidate",
        "candidate_text",
        "tokens",
        "geo_hits",
        "concept_hits",
        "objget",
        "provider",
        "source_group",
        "media_type",
        "candidate_key",
        "base_score",
        "must_tier",
        "flatten_candidates",
    ]


    for name in required_vse:

        result(
            f"VSE4_API_{name}",
            callable(
                vse.get(name)
            ),
        )


except Exception as exc:

    result(
        "VSE4_LOAD",
        False,
        f"{type(exc).__name__}: {exc}",
    )

    log(
        traceback.format_exc()
    )


# ============================================================
# 7. VSE4 SELF TEST
# ============================================================

section(
    "7. VSE4 SELF TEST"
)


if vse is not None:

    self_test = vse.get(
        "self_test"
    )

    if callable(self_test):

        try:

            self_test()

            result(
                "VSE4_SELF_TEST",
                True,
            )

        except Exception as exc:

            result(
                "VSE4_SELF_TEST",
                False,
                f"{type(exc).__name__}: {exc}",
            )

            log(
                traceback.format_exc()
            )

    else:

        result(
            "VSE4_SELF_TEST",
            False,
            "self_test missing",
        )


# ============================================================
# 8. DIRECT GEO SAFETY
# ============================================================

section(
    "8. GEOGRAPHIC SAFETY"
)


if vse is not None:

    geo_hits = vse.get(
        "geo_hits"
    )

    score_candidate = vse.get(
        "score_candidate"
    )


    if callable(geo_hits):

        sp = set(
            geo_hits(
                "São Paulo Brazil"
            )
        )

        ny = set(
            geo_hits(
                "Empire State Building Manhattan New York"
            )
        )


        log(
            "SP_GEO=",
            sorted(sp),
        )

        log(
            "NY_GEO=",
            sorted(ny),
        )


        result(
            "GEO_SP_DETECTED",
            bool(sp),
        )

        result(
            "GEO_NY_DETECTED",
            bool(ny),
        )

        result(
            "GEO_SP_NY_DISTINCT",
            sp != ny,
        )


    if callable(score_candidate):

        scene = {
            "texto":
                "Investigação em apartamento "
                "na cidade de São Paulo",

            "visual_query":
                "police investigation apartment "
                "Sao Paulo Brazil",

            "must_have": [
                "investigação",
                "apartamento",
            ],

            "location":
                "São Paulo Brazil",
        }


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


        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        }


        try:

            bad_score = score_candidate(
                wrong,
                scene,
                state,
            )

            good_score = score_candidate(
                correct,
                scene,
                state,
            )


            log(
                "GEO_BAD_RESULT=",
                json.dumps(
                    bad_score,
                    ensure_ascii=False,
                    default=str,
                ),
            )

            log(
                "GEO_GOOD_RESULT=",
                json.dumps(
                    good_score,
                    ensure_ascii=False,
                    default=str,
                ),
            )


            result(
                "GEO_BAD_HARD_MISMATCH",
                bad_score.get(
                    "hard_mismatch"
                )
                is True,
            )


            result(
                "GEO_GOOD_NOT_HARD_MISMATCH",
                good_score.get(
                    "hard_mismatch"
                )
                is False,
            )


            bad_effective = (
                bad_score.get(
                    "effective",
                    bad_score.get(
                        "effective_score",
                        0,
                    ),
                )
            )

            good_effective = (
                good_score.get(
                    "effective",
                    good_score.get(
                        "effective_score",
                        0,
                    ),
                )
            )


            result(
                "GEO_GOOD_BEATS_WRONG",
                good_effective
                >
                bad_effective,
                f"good={good_effective} "
                f"bad={bad_effective}",
            )


        except Exception as exc:

            result(
                "GEO_SCORE_RUNTIME",
                False,
                f"{type(exc).__name__}: {exc}",
            )

            log(
                traceback.format_exc()
            )


# ============================================================
# 9. FALSE ASSOCIATION TESTS
# ============================================================

section(
    "9. FALSE ASSOCIATION / GENERIC STOCK"
)


if vse is not None:

    score_candidate = vse.get(
        "score_candidate"
    )


    if callable(score_candidate):

        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        }


        scenarios = [

            (
                "FORENSIC_VS_PILLS",

                {
                    "texto":
                        "O laudo pericial revelou "
                        "novos indícios na investigação.",

                    "visual_query":
                        "forensic evidence laboratory report",

                    "must_have": [
                        "laudo",
                        "indícios",
                    ],
                },

                {
                    "provider":
                        "Pixabay",

                    "tipo":
                        "foto",

                    "title":
                        "Medication pills tablets on desk",

                    "must":
                        "1/2",

                    "score":
                        220,

                    "width":
                        1920,

                    "height":
                        1080,
                },

                {
                    "provider":
                        "Pexels",

                    "tipo":
                        "video",

                    "title":
                        "Forensic evidence "
                        "laboratory investigation",

                    "must":
                        "2/2",

                    "score":
                        170,

                    "width":
                        1920,

                    "height":
                        1080,
                },
            ),


            (
                "INVESTIGATION_VS_LIFESTYLE",

                {
                    "texto":
                        "A polícia iniciou a investigação "
                        "no apartamento.",

                    "visual_query":
                        "police investigation apartment",

                    "must_have": [
                        "polícia",
                        "investigação",
                    ],
                },

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
                        230,

                    "width":
                        1920,

                    "height":
                        1080,
                },

                {
                    "provider":
                        "Pixabay",

                    "tipo":
                        "video",

                    "title":
                        "Police detective "
                        "investigation apartment",

                    "must":
                        "2/2",

                    "score":
                        175,

                    "width":
                        1920,

                    "height":
                        1080,
                },
            ),
        ]


        for (
            name,
            scene,
            bad,
            good,
        ) in scenarios:

            try:

                bad_result = score_candidate(
                    bad,
                    scene,
                    state,
                )

                good_result = score_candidate(
                    good,
                    scene,
                    state,
                )


                bad_eff = bad_result.get(
                    "effective",
                    bad_result.get(
                        "effective_score",
                        0,
                    ),
                )

                good_eff = good_result.get(
                    "effective",
                    good_result.get(
                        "effective_score",
                        0,
                    ),
                )


                log(
                    f"{name}_BAD=",
                    json.dumps(
                        bad_result,
                        ensure_ascii=False,
                        default=str,
                    ),
                )

                log(
                    f"{name}_GOOD=",
                    json.dumps(
                        good_result,
                        ensure_ascii=False,
                        default=str,
                    ),
                )


                result(
                    f"{name}_GOOD_WINS",
                    good_eff > bad_eff,
                    f"good={good_eff} "
                    f"bad={bad_eff}",
                )


            except Exception as exc:

                result(
                    f"{name}_RUNTIME",
                    False,
                    f"{type(exc).__name__}: {exc}",
                )


# ============================================================
# 10. V42 BRIDGE API
# ============================================================

section(
    "10. V42 BRIDGE COMPLETE API"
)


bridge = None


bridge_path = (
    ROOT
    /
    "visual_selection_bridge_v42.py"
)


if bridge_path.is_file():

    try:

        bridge = load_module(
            "visual_selection_bridge_v42.py",
            "visual_general_audit_bridge",
        )

        result(
            "V42_BRIDGE_LOAD",
            True,
        )


        required = (

            "rank_pool",
            "reset_state",
            "commit_candidate",
        )


        for name in required:

            value = bridge.get(
                name
            )

            result(
                f"V42_API_{name}",
                callable(value),
                (
                    f"signature="
                    f"{inspect.signature(value)}"
                    if callable(value)
                    else
                    ""
                ),
            )


    except Exception as exc:

        result(
            "V42_BRIDGE_LOAD",
            False,
            f"{type(exc).__name__}: {exc}",
        )

        log(
            traceback.format_exc()
        )


# ============================================================
# 11. V42 OFFLINE RANK TEST
# ============================================================

section(
    "11. V42 OFFLINE GENERAL RANK TEST"
)


if bridge is not None:

    rank_pool = bridge.get(
        "rank_pool"
    )

    reset_state = bridge.get(
        "reset_state"
    )


    if (
        callable(rank_pool)
        and
        callable(reset_state)
    ):

        try:

            reset_state()


            scene = {

                "texto":
                    "A polícia iniciou a investigação "
                    "no apartamento em São Paulo.",

                "visual_query":
                    "police investigation apartment "
                    "Sao Paulo Brazil",

                "must_have": [
                    "investigação",
                    "apartamento",
                ],

                "location":
                    "São Paulo Brazil",
            }


            pool = [

                {
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
                },


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
                        210,

                    "width":
                        1920,

                    "height":
                        1080,
                },


                {
                    "provider":
                        "Pixabay",

                    "tipo":
                        "foto",

                    "title":
                        "Medication pills tablets on desk",

                    "must":
                        "1/2",

                    "score":
                        215,

                    "width":
                        1920,

                    "height":
                        1080,
                },


                {
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
                },


                {
                    "provider":
                        "Pexels",

                    "tipo":
                        "video",

                    "title":
                        "Police investigation "
                        "apartment crime scene "
                        "Sao Paulo Brazil",

                    "must":
                        "2/2",

                    "score":
                        180,

                    "width":
                        1920,

                    "height":
                        1080,
                },
            ]


            ranked, chosen, meta = rank_pool(

                pool,

                escolhido=pool[0],

                context=scene,
            )


            log(
                "V42_RANKED_COUNT=",
                len(ranked),
            )

            log(
                "V42_CHOSEN=",
                chosen,
            )

            log(
                "V42_META=",
                meta,
            )


            for index, item in enumerate(
                ranked,
                start=1,
            ):

                log(
                    f"V42_RANK_{index}="
                    f"{item.get('provider')} | "
                    f"{item.get('tipo')} | "
                    f"{item.get('title')}"
                )


            chosen_title = str(
                chosen.get(
                    "title",
                    "",
                )
            ).casefold()


            forbidden = (

                "empire state",
                "new york",
                "relaxing",
                "pills",
                "medication",
            )


            result(
                "V42_BAD_MEDIA_NOT_CHOSEN",
                not any(
                    term in chosen_title
                    for term in forbidden
                ),
                chosen_title,
            )


            result(
                "V42_GENERAL_RANK_TEST",
                bool(chosen),
            )


        except Exception as exc:

            result(
                "V42_GENERAL_RANK_TEST",
                False,
                f"{type(exc).__name__}: {exc}",
            )

            log(
                traceback.format_exc()
            )


# ============================================================
# 12. BRIDGE DIVERSITY / COMMIT STATE
# ============================================================

section(
    "12. V42 DIVERSITY + COMMIT STATE"
)


if bridge is not None:

    rank_pool = bridge.get(
        "rank_pool"
    )

    reset_state = bridge.get(
        "reset_state"
    )

    commit_candidate = bridge.get(
        "commit_candidate"
    )


    if all(
        callable(x)
        for x in (
            rank_pool,
            reset_state,
            commit_candidate,
        )
    ):

        try:

            reset_state()


            context = {

                "texto":
                    "Police investigation documents",

                "visual_query":
                    "police investigation documents",

                "must_have": [
                    "police",
                    "investigation",
                ],
            }


            first = {

                "provider":
                    "Pixabay",

                "tipo":
                    "foto",

                "title":
                    "Police investigation documents",

                "must":
                    "2/2",

                "score":
                    190,

                "id":
                    "pix_1",
            }


            alternate = {

                "provider":
                    "Pexels",

                "tipo":
                    "video",

                "title":
                    "Police investigation documents",

                "must":
                    "2/2",

                "score":
                    187,

                "id":
                    "pex_1",
            }


            commit_candidate(
                first
            )


            ranked, chosen, meta = rank_pool(

                [
                    first,
                    alternate,
                ],

                escolhido=first,

                context=context,
            )


            log(
                "DIVERSITY_CHOSEN=",
                chosen,
            )

            log(
                "DIVERSITY_META=",
                meta,
            )


            result(
                "V42_DIVERSITY_RUNTIME",
                bool(chosen),
            )


        except Exception as exc:

            result(
                "V42_DIVERSITY_RUNTIME",
                False,
                f"{type(exc).__name__}: {exc}",
            )


# ============================================================
# 13. MIDIA STRUCTURAL MARKERS
# ============================================================

section(
    "13. MIDIA V42 STRUCTURAL AUDIT"
)


midia_path = (
    ROOT
    /
    "midia.py"
)


if midia_path.is_file():

    midia_text = midia_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    midia_lines = (
        midia_text.splitlines()
    )


    markers = {

        "IMPORT":
            r"SHORTAUTOPRO VSE42 IMPORT",

        "SEARCH_RESCUE":
            r"SHORTAUTOPRO VSE42 SEARCH RESCUE",

        "FINAL_GATE":
            r"SHORTAUTOPRO VSE42 FINAL GATE",

        "PRIMARY_RANK":
            r"SHORTAUTOPRO VSE42 PRIMARY RANK",

        "FINAL_POOL":
            r"SHORTAUTOPRO VSE42 FINAL POOL",

        "SINGLE_FINALIZER":
            r"SHORTAUTOPRO VSE42 SINGLE FINALIZER",

        "SCENE_COMMIT":
            r"SHORTAUTOPRO VSE42 SCENE COMMIT",

        "SUCCESS_COMMIT":
            r"SHORTAUTOPRO VSE42 SUCCESS COMMIT",

        "ALT_RANK":
            r"SHORTAUTOPRO VSE42 ALT RANK",
    }


    marker_locations = {}


    for name, pattern in markers.items():

        regex = re.compile(
            pattern,
            re.I,
        )

        hits = [

            number

            for number, line
            in enumerate(
                midia_lines,
                start=1,
            )

            if regex.search(
                line
            )
        ]


        marker_locations[
            name
        ] = hits


        log(
            f"{name}_LINES="
            f"{hits}"
        )


        result(
            f"MIDIA_MARKER_{name}",
            len(hits) >= 1,
        )


    duplicate_markers = [

        name

        for name, hits
        in marker_locations.items()

        if len(hits) > 1
    ]


    if duplicate_markers:

        warning(
            "MIDIA_DUPLICATE_V42_MARKERS",
            ",".join(
                duplicate_markers
            ),
        )

    else:

        result(
            "MIDIA_NO_DUPLICATE_V42_MARKERS",
            True,
        )


# ============================================================
# 14. PROVIDER ACQUISITION MAP
# ============================================================

section(
    "14. PROVIDER ACQUISITION MAP"
)


if midia_path.is_file():

    try:

        tree = ast.parse(
            midia_text
        )


        functions = {

            node.name:
                node

            for node in tree.body

            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        provider_functions = (

            "pexels_video",
            "pexels_foto",

            "pixabay_video",
            "pixabay_foto",

            "coverr_video",

            "buscar_todos_candidatos",
        )


        for name in provider_functions:

            node = functions.get(
                name
            )

            result(
                f"PROVIDER_FUNCTION_{name}",
                node is not None,
                (
                    f"line={node.lineno}"
                    if node
                    else
                    ""
                ),
            )


        buscador = functions.get(
            "buscar_todos_candidatos"
        )


        calls = set()


        if buscador:

            for node in ast.walk(
                buscador
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


        expected_calls = (

            "pexels_video",
            "pexels_foto",

            "pixabay_video",
            "pixabay_foto",

            "coverr_video",
        )


        for name in expected_calls:

            result(
                f"BUSCADOR_CALLS_{name}",
                name in calls,
            )


    except Exception as exc:

        result(
            "PROVIDER_AST_AUDIT",
            False,
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 15. PROVIDER CONFIG PRESENCE - NAMES ONLY
# ============================================================

section(
    "15. PROVIDER CONFIG VARIABLE AUDIT"
)


if midia_path.is_file():

    env_refs = sorted(
        set(
            re.findall(
                r'os\.getenv\(\s*["\']([^"\']+)["\']',
                midia_text,
            )
        )
    )


    provider_envs = [

        name

        for name in env_refs

        if any(
            term in name.upper()
            for term in (
                "PEXELS",
                "PIXABAY",
                "COVERR",
                "WIKIMEDIA",
                "VSE",
            )
        )
    ]


    for name in provider_envs:

        log(
            f"ENV_REF={name}"
        )


    result(
        "PROVIDER_ENV_REFERENCE_SCAN",
        True,
        f"count={len(provider_envs)}",
    )


# ============================================================
# 16. HARD-CODED SHORT ID AUDIT
# ============================================================

section(
    "16. HARD-CODED SHORT ID AUDIT"
)


pattern_sid = re.compile(
    r"20\d{2}-\d{2}-\d{2}_\d{4}"
)


hardcoded = []


for path in [

    ROOT / "midia.py",
    ROOT / "video.py",
    ROOT / "v6.py",
    ROOT / "gerar_short.sh",
    ROOT / "visual_selection_engine_v4.py",
    ROOT / "visual_selection_bridge_v42.py",
]:

    if not path.is_file():
        continue

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    hits = sorted(
        set(
            pattern_sid.findall(
                text
            )
        )
    )


    if hits:

        hardcoded.append(
            (
                path.name,
                hits,
            )
        )


for item in hardcoded:

    log(
        "HARDCODED_SHORT_ID=",
        item,
    )


if hardcoded:

    warning(
        "HARDCODED_SHORT_ID",
        str(hardcoded),
    )

else:

    result(
        "NO_HARDCODED_SHORT_ID",
        True,
    )


# ============================================================
# 17. DANGEROUS CLEANUP AUDIT
# ============================================================

section(
    "17. DESTRUCTIVE / CLEANUP AUDIT"
)


danger_patterns = (

    r"rm\s+-rf\s+~/ShortAutoPro",
    r"rm\s+-rf\s+\$HOME/ShortAutoPro",
    r"shutil\.rmtree\(\s*ROOT",
    r"shutil\.rmtree\(\s*BASE",
)


danger_hits = []


for path in list(
    ROOT.glob("*.py")
) + list(
    ROOT.glob("*.sh")
):

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for pattern in danger_patterns:

        if re.search(
            pattern,
            text,
            re.I,
        ):

            danger_hits.append(
                (
                    path.name,
                    pattern,
                )
            )


for item in danger_hits:

    log(
        "DANGEROUS_PATTERN=",
        item,
    )


if danger_hits:

    warning(
        "DESTRUCTIVE_PATTERN_AUDIT",
        str(danger_hits),
    )

else:

    result(
        "DESTRUCTIVE_PATTERN_AUDIT",
        True,
    )


# ============================================================
# 18. FRESH RENDER GUARD SAFETY
# ============================================================

section(
    "18. FRESH RENDER GUARD STATIC SAFETY"
)


guard_path = (
    ROOT
    /
    "fresh_render_guard_v1.py"
)


if guard_path.is_file():

    text = guard_path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    result(
        "GUARD_PROTECTS_ASS",
        ".ass" in text,
    )

    result(
        "GUARD_PROTECTS_AUDIO",
        (
            ".mp3" in text
            or
            ".wav" in text
        ),
    )

    result(
        "GUARD_MP4_SCOPED",
        ".mp4" in text,
    )


# ============================================================
# 19. PIPELINE ORDER
# ============================================================

section(
    "19. GERAR_SHORT PIPELINE ORDER"
)


gerar = (
    ROOT
    /
    "gerar_short.sh"
)


if gerar.is_file():

    text = gerar.read_text(
        encoding="utf-8",
        errors="replace",
    )


    stages = {

        "MIDIA":
            "midia.py",

        "LEGENDA":
            "legenda_dinamica.py",

        "VIDEO":
            "video.py",

        "V6":
            "v6.py",
    }


    positions = {}


    for name, needle in stages.items():

        positions[
            name
        ] = text.find(
            needle
        )


        log(
            f"PIPELINE_{name}_POSITION="
            f"{positions[name]}"
        )


    found_all = all(
        value >= 0
        for value in positions.values()
    )


    result(
        "PIPELINE_CORE_STAGES_PRESENT",
        found_all,
    )


    if found_all:

        order_ok = (

            positions["MIDIA"]
            <
            positions["LEGENDA"]
            <
            positions["VIDEO"]
            <
            positions["V6"]
        )


        result(
            "PIPELINE_CORE_ORDER",
            order_ok,
        )


# ============================================================
# 20. V42 FEATURE FLAGS
# ============================================================

section(
    "20. FEATURE FLAG AUDIT"
)


texts = ""


for path in (

    ROOT / "midia.py",
    ROOT / "visual_selection_bridge_v42.py",
    ROOT / "visual_selection_engine_v4.py",
):

    if path.is_file():

        texts += (
            "\n"
            +
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )


for flag in (

    "SAP_VSE_V4",
    "SAP_VSE42",
):

    result(
        f"FEATURE_FLAG_{flag}",
        flag in texts,
    )


# ============================================================
# 21. POSSIBLE LEGACY ENGINE COLLISION
# ============================================================

section(
    "21. LEGACY VISUAL ENGINE COLLISION"
)


legacy_names = (

    "visual_selection_engine_v2",
    "visual_selection_final_gate_v3",
    "visual_must_rescue_v1",
    "visual_scene_commit_lock_v1",
)


if midia_path.is_file():

    for name in legacy_names:

        count = midia_text.count(
            name
        )

        log(
            f"LEGACY_REF_{name}="
            f"{count}"
        )


        if count > 0:

            warning(
                f"LEGACY_ENGINE_ACTIVE_{name}",
                f"references={count}",
            )


# ============================================================
# 22. DUPLICATE FUNCTION DEFINITIONS IN MIDIA
# ============================================================

section(
    "22. MIDIA DUPLICATE FUNCTION DEFINITIONS"
)


if midia_path.is_file():

    try:

        tree = ast.parse(
            midia_text
        )


        names = {}


        for node in tree.body:

            if isinstance(
                node,
                ast.FunctionDef,
            ):

                names.setdefault(
                    node.name,
                    []
                ).append(
                    node.lineno
                )


        duplicates = {

            name:
                lines

            for name, lines
            in names.items()

            if len(lines) > 1
        }


        important_duplicates = {

            name:
                lines

            for name, lines
            in duplicates.items()

            if any(
                key in name.casefold()
                for key in (
                    "buscar",
                    "baixar",
                    "candidato",
                    "selector",
                    "failover",
                    "pexels",
                    "pixabay",
                    "coverr",
                )
            )
        }


        if important_duplicates:

            for name, lines in sorted(
                important_duplicates.items()
            ):

                log(
                    f"DUPLICATE_FUNCTION_{name}="
                    f"{lines}"
                )


            warning(
                "MIDIA_IMPORTANT_DUPLICATE_FUNCTIONS",
                str(
                    important_duplicates
                ),
            )

        else:

            result(
                "MIDIA_NO_IMPORTANT_DUPLICATE_FUNCTIONS",
                True,
            )


    except Exception as exc:

        result(
            "MIDIA_DUPLICATE_FUNCTION_AUDIT",
            False,
            str(exc),
        )


# ============================================================
# 23. SUMMARY
# ============================================================

section(
    "23. FINAL SUMMARY"
)


log(
    "PASS_COUNT=",
    len(PASS),
)

log(
    "FAIL_COUNT=",
    len(FAIL),
)

log(
    "WARN_COUNT=",
    len(WARN),
)


if PASS:

    log()
    log(
        "===== PASS ====="
    )

    for name in PASS:

        log(
            name
        )


if FAIL:

    log()
    log(
        "===== FAIL ====="
    )

    for name in FAIL:

        log(
            name
        )


if WARN:

    log()
    log(
        "===== WARN ====="
    )

    for name in WARN:

        log(
            name
        )


log()


if not FAIL:

    if WARN:

        log(
            "GENERAL_STATUS=PASS_WITH_WARNINGS"
        )

    else:

        log(
            "GENERAL_STATUS=PASS"
        )

else:

    log(
        "GENERAL_STATUS=FAIL"
    )


log(
    "REPORT=",
    REPORT,
)

log(
    "NETWORK_EXECUTED=NO"
)

log(
    "MEDIA_DOWNLOADED=NO"
)

log(
    "MIDIA_PY_EXECUTED=NO"
)

log(
    "VIDEO_RENDERED=NO"
)

log(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
