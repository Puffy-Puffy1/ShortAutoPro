#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import inspect
import json
import os
import py_compile
import re
import runpy
import subprocess
import symtable
import sys
import traceback
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"
SID = os.environ.get(
    "SHORT_ID",
    "2026-09-02_2358",
).strip()


def section(name):

    print()
    print("=" * 78)
    print(name)
    print("=" * 78)


def sha256(path: Path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def file_status(path: Path):

    if not path.is_file():
        return "MISSING"

    try:
        size = path.stat().st_size
    except Exception:
        size = -1

    return f"PASS bytes={size}"


def get_effective(result):

    if not isinstance(result, dict):
        return None

    for key in (
        "effective",
        "effective_score",
        "final_score",
        "score_final",
        "score",
    ):

        value = result.get(key)

        if isinstance(
            value,
            (int, float),
        ):
            return float(value)

    return None


core_files = [
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
    "render_output_certifier_v1.py",
    "render_transaction_v1.py",
]


summary = {
    "core_missing": [],
    "compile_failures": [],
    "shell_failures": [],
    "vse_load": None,
    "vse_self_test": None,
    "score_candidate_definitions": None,
    "active_score_candidate_line": None,
    "unresolved_globals": [],
    "wrong_geo_hard": None,
    "correct_geo_hard": None,
    "geo_behavior": None,
    "media_count": None,
    "invalid_scene_count": None,
    "scene_map_count": None,
    "provider_exact_missing": [],
    "pipeline_script_missing": [],
}


# ============================================================
# 1. CORE
# ============================================================

section("1. CORE FILES + HASHES")


for name in core_files:

    path = ROOT / name

    if path.is_file():

        print(
            f"CORE=PASS | {name} | "
            f"{path.stat().st_size} bytes | "
            f"{sha256(path)}"
        )

    else:

        print(
            f"CORE=FAIL | {name}"
        )

        summary[
            "core_missing"
        ].append(name)


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section("2. PYTHON COMPILE - CORE")


for name in core_files:

    if not name.endswith(".py"):
        continue

    path = ROOT / name

    if not path.is_file():
        continue

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        print(
            f"COMPILE=PASS | {name}"
        )

    except Exception as exc:

        print(
            f"COMPILE=FAIL | {name} | "
            f"{type(exc).__name__}: {exc}"
        )

        summary[
            "compile_failures"
        ].append(name)


# ============================================================
# 3. ALL ACTIVE ROOT PYTHON
# ============================================================

section("3. ALL ROOT PYTHON SYNTAX")


root_py_fail = []

root_py_count = 0


for path in sorted(
    ROOT.glob("*.py")
):

    # Backups soltos não representam necessariamente código ativo.
    lower = path.name.casefold()

    if (
        "backup" in lower
        or lower.endswith("_old.py")
    ):
        continue

    root_py_count += 1

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        root_py_fail.append(
            (
                path.name,
                str(exc),
            )
        )


print(
    f"ROOT_PY_FILES_TESTED={root_py_count}"
)

print(
    f"ROOT_PY_COMPILE_FAILURES={len(root_py_fail)}"
)


for name, error in root_py_fail[:50]:

    print(
        f"ROOT_COMPILE_FAIL={name} | {error}"
    )


# ============================================================
# 4. SHELL
# ============================================================

section("4. SHELL SYNTAX")


for name in (
    "gerar_short.sh",
):

    path = ROOT / name

    if not path.is_file():

        print(
            f"SHELL=MISSING | {name}"
        )

        summary[
            "shell_failures"
        ].append(name)

        continue


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


    if result.returncode == 0:

        print(
            f"SHELL=PASS | {name}"
        )

    else:

        print(
            f"SHELL=FAIL | {name}"
        )

        print(
            result.stderr
        )

        summary[
            "shell_failures"
        ].append(name)


# ============================================================
# 5. VSE4 AST
# ============================================================

section("5. VSE4 STRUCTURAL AST AUDIT")


vse_path = (
    ROOT
    / "visual_selection_engine_v4.py"
)


vse_tree = None
vse_src = ""


if vse_path.is_file():

    vse_src = vse_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    vse_tree = ast.parse(
        vse_src
    )


    top_functions = [
        node
        for node in vse_tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]


    by_name = defaultdict(list)


    for node in top_functions:

        by_name[
            node.name
        ].append(node)


    duplicates = {
        name: nodes
        for name, nodes
        in by_name.items()
        if len(nodes) > 1
    }


    print(
        f"TOP_LEVEL_FUNCTIONS={len(top_functions)}"
    )

    print(
        f"DUPLICATE_FUNCTION_NAMES={len(duplicates)}"
    )


    for name, nodes in sorted(
        duplicates.items()
    ):

        locations = [
            f"{n.lineno}-{n.end_lineno}"
            for n in nodes
        ]

        print(
            f"DUPLICATE={name} "
            f"COUNT={len(nodes)} "
            f"LINES={','.join(locations)}"
        )


    score_nodes = by_name.get(
        "score_candidate",
        [],
    )


    summary[
        "score_candidate_definitions"
    ] = len(score_nodes)


    print()
    print(
        "SCORE_CANDIDATE_DEFINITION_COUNT="
        f"{len(score_nodes)}"
    )


    for index, node in enumerate(
        score_nodes,
        start=1,
    ):

        segment = ast.get_source_segment(
            vse_src,
            node,
        ) or ""

        digest = hashlib.sha256(
            segment.encode("utf-8")
        ).hexdigest()[:16]

        print(
            f"SCORE_DEF_{index}="
            f"lines:{node.lineno}-{node.end_lineno} "
            f"sha:{digest}"
        )


else:

    print(
        "VSE4_AST=FAIL_FILE_MISSING"
    )


# ============================================================
# 6. VSE4 TRUE GLOBALS
# ============================================================

section("6. VSE4 GLOBAL SYMBOL AUDIT")


if vse_src:

    try:

        table = symtable.symtable(
            vse_src,
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


        builtins_set = set(
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

                    if name in builtins_set:
                        continue

                    unresolved.add(name)

                walk(child)


        walk(table)


        summary[
            "unresolved_globals"
        ] = sorted(unresolved)


        if unresolved:

            print(
                "TRUE_UNRESOLVED_GLOBALS="
                +
                ",".join(
                    sorted(unresolved)
                )
            )

        else:

            print(
                "TRUE_UNRESOLVED_GLOBALS=NONE"
            )


    except Exception as exc:

        print(
            "GLOBAL_AUDIT_EXCEPTION="
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# 7. VSE4 RUNTIME
# ============================================================

section("7. VSE4 RUNTIME + ACTIVE FUNCTION")


vse_ns = None


try:

    vse_ns = runpy.run_path(
        str(vse_path),
        run_name="shortautopro_general_audit_v7",
    )


    summary[
        "vse_load"
    ] = True


    print(
        "VSE4_LOAD=PASS"
    )


    score_fn = vse_ns.get(
        "score_candidate"
    )


    if callable(score_fn):

        print(
            "ACTIVE_SCORE_CANDIDATE=YES"
        )

        print(
            "ACTIVE_SCORE_SIGNATURE="
            f"{inspect.signature(score_fn)}"
        )

        print(
            "ACTIVE_SCORE_FIRSTLINE="
            f"{score_fn.__code__.co_firstlineno}"
        )


        summary[
            "active_score_candidate_line"
        ] = (
            score_fn.__code__.co_firstlineno
        )


        expected_last = None

        if vse_tree is not None:

            nodes = [
                n
                for n in vse_tree.body
                if isinstance(
                    n,
                    ast.FunctionDef,
                )
                and n.name == "score_candidate"
            ]

            if nodes:
                expected_last = nodes[-1].lineno


        print(
            "LAST_STATIC_SCORE_LINE="
            f"{expected_last}"
        )


        if (
            expected_last
            ==
            score_fn.__code__.co_firstlineno
        ):

            print(
                "ACTIVE_SCORE_MATCHES_LAST_DEFINITION=PASS"
            )

        else:

            print(
                "ACTIVE_SCORE_MATCHES_LAST_DEFINITION=FAIL"
            )


    else:

        print(
            "ACTIVE_SCORE_CANDIDATE=NO"
        )


except Exception as exc:

    summary[
        "vse_load"
    ] = False

    print(
        "VSE4_LOAD=FAIL"
    )

    print(
        f"{type(exc).__name__}: {exc}"
    )

    traceback.print_exc()


# ============================================================
# 8. ORIGINAL SELF TEST
# ============================================================

section("8. VSE4 ORIGINAL SELF TEST")


if vse_ns is not None:

    fn = vse_ns.get(
        "self_test"
    )

    if callable(fn):

        try:

            fn()

            summary[
                "vse_self_test"
            ] = True

            print(
                "ORIGINAL_SELF_TEST=PASS"
            )

        except Exception:

            summary[
                "vse_self_test"
            ] = False

            print(
                "ORIGINAL_SELF_TEST=FAIL"
            )

            traceback.print_exc()

    else:

        print(
            "ORIGINAL_SELF_TEST=MISSING"
        )


# ============================================================
# 9. SEMANTIC BEHAVIOR
# ============================================================

section("9. SEMANTIC / GEO BEHAVIOR")


if vse_ns is not None:

    score = vse_ns.get(
        "score_candidate"
    )

    geo_hits = vse_ns.get(
        "geo_hits"
    )


    state = {
        "providers": [
            "pixabay",
            "pixabay",
        ],
        "groups": [],
        "types": [],
        "keys": [],
    }


    scene_geo = (
        "Investigação em apartamento "
        "na cidade de São Paulo Brasil"
    )


    candidates = {

        "WRONG_GEO": {
            "provider": "Pixabay",
            "tipo": "foto",
            "title":
                "Empire State Building Manhattan New York",
            "must": "2/2",
            "score": 220,
            "width": 1920,
            "height": 1080,
        },

        "CORRECT_GEO": {
            "provider": "Wikimedia",
            "tipo": "foto",
            "title":
                "Apartment building Sao Paulo Brazil",
            "must": "1/2",
            "score": 120,
            "width": 1920,
            "height": 1080,
        },

        "GENERIC": {
            "provider": "Pixabay",
            "tipo": "foto",
            "title":
                "Happy woman relaxing on bed lifestyle",
            "must": "1/2",
            "score": 180,
            "width": 1920,
            "height": 1080,
        },

        "MEDICINE": {
            "provider": "Pixabay",
            "tipo": "foto",
            "title":
                "Pills medication tablets on desk",
            "must": "1/2",
            "score": 180,
            "width": 1920,
            "height": 1080,
        },

        "NEUTRAL": {
            "provider": "Pexels",
            "tipo": "foto",
            "title":
                "Police investigation documents evidence",
            "must": "1/2",
            "score": 140,
            "width": 1920,
            "height": 1080,
        },
    }


    results = {}


    for name, candidate in candidates.items():

        try:

            result = score(
                candidate,
                scene_geo,
                state,
            )

            results[name] = result


            print()
            print(
                f"CANDIDATE={name}"
            )

            print(
                "RESULT_KEYS="
                +
                (
                    ",".join(
                        sorted(result.keys())
                    )
                    if isinstance(result, dict)
                    else "NON_DICT"
                )
            )


            if isinstance(result, dict):

                for key in (
                    "hard_mismatch",
                    "hard_reason",
                    "effective",
                    "effective_score",
                    "base",
                    "base_score",
                    "geo_conflict",
                    "geo_penalty",
                    "scene_geo",
                    "candidate_geo",
                    "generic_penalty",
                    "medicine_penalty",
                    "mismatch",
                    "mismatch_penalty",
                    "must",
                    "must_tier",
                ):

                    if key in result:

                        print(
                            f"{name}_{key.upper()}="
                            f"{result[key]!r}"
                        )


                print(
                    f"{name}_EFFECTIVE="
                    f"{get_effective(result)}"
                )


        except Exception as exc:

            print(
                f"{name}_SCORE=EXCEPTION | "
                f"{type(exc).__name__}: {exc}"
            )

            traceback.print_exc()


    wrong = results.get(
        "WRONG_GEO",
        {},
    )

    correct = results.get(
        "CORRECT_GEO",
        {},
    )


    if isinstance(wrong, dict):

        summary[
            "wrong_geo_hard"
        ] = wrong.get(
            "hard_mismatch"
        )


    if isinstance(correct, dict):

        summary[
            "correct_geo_hard"
        ] = correct.get(
            "hard_mismatch"
        )


    wrong_eff = get_effective(wrong)
    correct_eff = get_effective(correct)


    behavior_ok = (
        isinstance(wrong, dict)
        and
        wrong.get("hard_mismatch") is True
        and
        isinstance(correct, dict)
        and
        correct.get("hard_mismatch") is False
        and
        wrong_eff is not None
        and
        correct_eff is not None
        and
        correct_eff > wrong_eff
    )


    summary[
        "geo_behavior"
    ] = behavior_ok


    print()
    print(
        "GEO_BEHAVIOR_TEST="
        +
        (
            "PASS"
            if behavior_ok
            else "FAIL"
        )
    )


    if callable(geo_hits):

        for text in (
            "São Paulo Brasil",
            "Empire State Building Manhattan New York",
            "Rio de Janeiro Brazil",
            "London United Kingdom",
        ):

            try:

                print(
                    f"GEO_HITS[{text}]="
                    f"{sorted(geo_hits(text))}"
                )

            except Exception as exc:

                print(
                    f"GEO_HITS_EXCEPTION={exc}"
                )


# ============================================================
# 10. MIDIA STRUCTURE
# ============================================================

section("10. MIDIA.PY STRUCTURE + VSE INTEGRATION")


midia_path = ROOT / "midia.py"


if midia_path.is_file():

    midia_src = midia_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    midia_tree = ast.parse(
        midia_src
    )


    defs_all = [
        node
        for node in ast.walk(
            midia_tree
        )
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]


    defs_top = [
        node
        for node in midia_tree.body
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    ]


    print(
        f"MIDIA_TOP_LEVEL_FUNCTIONS={len(defs_top)}"
    )

    print(
        f"MIDIA_ALL_FUNCTION_DEFS={len(defs_all)}"
    )


    markers = (
        "visual_selection_engine_v4",
        "vse42",
        "vse4",
        "score_candidate",
        "hard_mismatch",
        "must_rescue",
        "commit_lock",
    )


    for marker in markers:

        count = midia_src.casefold().count(
            marker.casefold()
        )

        print(
            f"MIDIA_MARKER[{marker}]={count}"
        )


    print()
    print(
        "===== VSE-RELATED MIDIA LINES ====="
    )


    for index, line in enumerate(
        midia_src.splitlines(),
        start=1,
    ):

        low = line.casefold()

        if any(
            marker.casefold() in low
            for marker in markers
        ):

            print(
                f"{index:05d}: "
                f"{line[:240]}"
            )


# ============================================================
# 11. PROVIDERS
# ============================================================

section("11. PROVIDER DISCOVERY")


if midia_path.is_file():

    provider_terms = (
        "wiki",
        "wikimedia",
        "pexels",
        "pixabay",
        "coverr",
        "unsplash",
    )


    provider_defs = []


    for node in defs_all:

        if any(
            term in node.name.casefold()
            for term in provider_terms
        ):

            provider_defs.append(
                (
                    node.name,
                    node.lineno,
                    node.end_lineno,
                )
            )


    for name, start, end in sorted(
        provider_defs,
        key=lambda x: x[1],
    ):

        print(
            f"PROVIDER_FUNCTION="
            f"{name} lines={start}-{end}"
        )


    exact_required = (
        "buscar_wikimedia_fotos",
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
    )


    top_names = {
        node.name
        for node in defs_top
    }


    for name in exact_required:

        ok = name in top_names

        print(
            f"EXACT_PROVIDER_{name}="
            f"{'PASS' if ok else 'MISSING'}"
        )

        if not ok:

            summary[
                "provider_exact_missing"
            ].append(name)


    # Call sites inside buscar_todos_candidatos.
    target = None


    for node in defs_all:

        if node.name == "buscar_todos_candidatos":

            target = node

            break


    if target:

        print()
        print(
            f"BUSCAR_TODOS_CANDIDATOS="
            f"{target.lineno}-{target.end_lineno}"
        )


        calls = []


        for node in ast.walk(target):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue


            try:

                call_name = ast.unparse(
                    node.func
                )

            except Exception:

                call_name = "?"


            if any(
                term in call_name.casefold()
                for term in provider_terms
            ):

                calls.append(
                    (
                        node.lineno,
                        call_name,
                    )
                )


        for line, call_name in sorted(calls):

            print(
                f"PROVIDER_CALL="
                f"line:{line} name:{call_name}"
            )


    else:

        print(
            "BUSCAR_TODOS_CANDIDATOS=MISSING"
        )


# ============================================================
# 12. ACTIVE MEDIA
# ============================================================

section("12. ACTIVE MEDIA SET")


media_dir = (
    ROOT
    / "imagens"
    / f"short_{SID}"
)


print(
    f"EXPECTED_MEDIA_DIR={media_dir}"
)


invalid = []
total = 0


for number in range(
    1,
    13,
):

    files = []


    if media_dir.is_dir():

        files = sorted(
            [
                p
                for p in media_dir.glob(
                    f"scene_{number:02d}.*"
                )
                if p.is_file()
            ]
        )


    total += len(files)


    print(
        f"SCENE_{number:02d}_COUNT="
        f"{len(files)}"
    )


    for path in files:

        print(
            f"  {path.name} | "
            f"{path.stat().st_size} | "
            f"{sha256(path)[:20]}"
        )


    if len(files) != 1:

        invalid.append(
            number
        )


summary[
    "media_count"
] = total

summary[
    "invalid_scene_count"
] = len(invalid)


print(
    f"ACTIVE_MEDIA_TOTAL={total}"
)

print(
    f"ACTIVE_MEDIA_INVALID_SCENES="
    f"{len(invalid)}"
)


if invalid:

    print(
        "INVALID_SCENE_IDS="
        +
        ",".join(
            f"{x:02d}"
            for x in invalid
        )
    )


# ============================================================
# 13. FIND OTHER MEDIA SETS
# ============================================================

section("13. OTHER MEDIA DIRECTORIES")


images_root = ROOT / "imagens"


candidates = []


if images_root.is_dir():

    for directory in sorted(
        images_root.glob(
            "short_*"
        )
    ):

        if not directory.is_dir():
            continue


        scene_files = [
            p
            for p in directory.glob(
                "scene_*.*"
            )
            if p.is_file()
        ]


        candidates.append(
            (
                directory.stat().st_mtime,
                directory,
                len(scene_files),
            )
        )


for _, directory, count in sorted(
    candidates,
    reverse=True,
)[:30]:

    print(
        f"MEDIA_DIR={directory.name} "
        f"SCENE_FILES={count}"
    )


if total == 0:

    print()
    print(
        "ACTIVE_MEDIA_MISSING_FOR_REQUESTED_SHORT_ID=YES"
    )

    print(
        "NOTE=This canary cannot be rerendered "
        "without restoring/regenerating its scene media."
    )


# ============================================================
# 14. BACKUP MEDIA SEARCH
# ============================================================

section("14. BACKUP MEDIA RECOVERY CANDIDATES")


backup_hits = []


backups_root = ROOT / "backups"


if backups_root.is_dir():

    try:

        for path in backups_root.rglob(
            f"short_{SID}"
        ):

            if not path.is_dir():
                continue


            scene_files = [
                p
                for p in path.glob(
                    "scene_*.*"
                )
                if p.is_file()
            ]


            if scene_files:

                backup_hits.append(
                    (
                        path,
                        len(scene_files),
                    )
                )

    except Exception as exc:

        print(
            f"BACKUP_SEARCH_EXCEPTION={exc}"
        )


if backup_hits:

    for path, count in backup_hits[:30]:

        print(
            f"BACKUP_MEDIA="
            f"{path} "
            f"SCENE_FILES={count}"
        )

else:

    print(
        "BACKUP_MEDIA_FOR_SHORT_ID=NONE_FOUND"
    )


# ============================================================
# 15. SCENE MAP
# ============================================================

section("15. SCENE MAP")


scene_map = (
    ROOT
    / "roteiros"
    / f"scene_map_{SID}.json"
)


if scene_map.is_file():

    print(
        f"SCENE_MAP_FILE=PASS | "
        f"{scene_map}"
    )


    try:

        data = json.loads(
            scene_map.read_text(
                encoding="utf-8"
            )
        )


        if isinstance(data, list):

            scenes = data

        elif isinstance(data, dict):

            scenes = (
                data.get("scenes")
                or
                data.get("cenas")
                or
                data.get("scene_map")
                or
                []
            )

        else:

            scenes = []


        summary[
            "scene_map_count"
        ] = len(scenes)


        print(
            f"SCENE_MAP_COUNT={len(scenes)}"
        )


        for index, scene in enumerate(
            scenes[:12],
            start=1,
        ):

            if isinstance(scene, dict):

                print(
                    f"SCENE_MAP_{index:02d}_KEYS="
                    +
                    ",".join(
                        sorted(
                            scene.keys()
                        )
                    )
                )


    except Exception as exc:

        print(
            "SCENE_MAP_PARSE=FAIL | "
            f"{type(exc).__name__}: {exc}"
        )


else:

    print(
        "SCENE_MAP_FILE=MISSING"
    )


# ============================================================
# 16. RENDER ASSETS
# ============================================================

section("16. RENDER ASSETS")


render_assets = [
    ROOT
    / "audios"
    / f"short_{SID}.mp3",

    ROOT
    / "videos"
    / f"short_{SID}.ass",

    ROOT
    / "temp"
    / SID
    / "video_sem_audio.mp4",

    ROOT
    / "videos"
    / f"short_v6_{SID}.mp4",
]


for path in render_assets:

    print(
        f"RENDER_ASSET="
        f"{file_status(path)} | "
        f"{path.relative_to(ROOT)}"
    )


# ============================================================
# 17. GERAR_SHORT PIPELINE REFERENCES
# ============================================================

section("17. GERAR_SHORT PIPELINE DEPENDENCIES")


gerar = ROOT / "gerar_short.sh"


if gerar.is_file():

    shell_src = gerar.read_text(
        encoding="utf-8",
        errors="replace",
    )


    refs = sorted(
        set(
            re.findall(
                r"(?<![/\w])"
                r"([A-Za-z0-9_][A-Za-z0-9_.-]*"
                r"\.(?:py|sh))",
                shell_src,
            )
        )
    )


    print(
        f"PIPELINE_SCRIPT_REFERENCES={len(refs)}"
    )


    for ref in refs:

        path = ROOT / ref

        if path.is_file():

            print(
                f"PIPELINE_SCRIPT=PASS | {ref}"
            )

        else:

            print(
                f"PIPELINE_SCRIPT=MISSING | {ref}"
            )

            summary[
                "pipeline_script_missing"
            ].append(ref)


# ============================================================
# 18. FRESH RENDER GUARD STATIC SAFETY
# ============================================================

section("18. FRESH RENDER GUARD")


guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    text = guard.read_text(
        encoding="utf-8",
        errors="replace",
    )


    checks = {
        "PROTECTED_SUFFIXES":
            "PROTECTED_SUFFIXES" in text,

        "ASS_PROTECTION_REFERENCE":
            ".ass" in text,

        "MP3_PROTECTION_REFERENCE":
            ".mp3" in text,

        "SHORT_ID_SCOPE":
            "short_id" in text.casefold(),

        "TEMP_SCOPE":
            '"temp"' in text
            or "'temp'" in text,
    }


    for name, ok in checks.items():

        print(
            f"GUARD_{name}="
            f"{'PASS' if ok else 'REVIEW'}"
        )


else:

    print(
        "FRESH_RENDER_GUARD=MISSING"
    )


# ============================================================
# 19. SCORE CANDIDATE CALL SITES
# ============================================================

section("19. SCORE_CANDIDATE CALL SITES")


for filename in (
    "visual_selection_engine_v4.py",
    "midia.py",
    "media_diversity_guard_v1.py",
    "visual_selection_final_gate_v3.py",
):

    path = ROOT / filename

    if not path.is_file():
        continue


    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    print()
    print(
        f"FILE={filename}"
    )


    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        if "score_candidate" in line:

            print(
                f"{number:05d}: "
                f"{line[:240]}"
            )


# ============================================================
# 20. MASTER CLASSIFICATION
# ============================================================

section("20. MASTER CLASSIFICATION")


critical = []
warnings = []


if summary["core_missing"]:

    critical.append(
        "CORE_FILES_MISSING"
    )


if summary["compile_failures"]:

    critical.append(
        "CORE_COMPILE_FAILURE"
    )


if summary["shell_failures"]:

    critical.append(
        "SHELL_SYNTAX_FAILURE"
    )


if summary["vse_load"] is False:

    critical.append(
        "VSE4_RUNTIME_LOAD_FAILURE"
    )


if summary["vse_self_test"] is False:

    critical.append(
        "VSE4_SELF_TEST_FAILURE"
    )


score_defs = (
    summary[
        "score_candidate_definitions"
    ]
    or 0
)


if score_defs > 1:

    critical.append(
        "DUPLICATE_SCORE_CANDIDATE_DEFINITIONS"
    )


if summary["unresolved_globals"]:

    critical.append(
        "VSE4_UNRESOLVED_GLOBALS"
    )


if summary["geo_behavior"] is False:

    critical.append(
        "GEO_BEHAVIOR_FAILURE"
    )


if (
    summary["media_count"]
    != 12
    or
    summary["invalid_scene_count"]
    != 0
):

    warnings.append(
        "CURRENT_CANARY_MEDIA_INCOMPLETE"
    )


if summary["scene_map_count"] != 12:

    warnings.append(
        "SCENE_MAP_NOT_12"
    )


if summary["provider_exact_missing"]:

    warnings.append(
        "EXPECTED_PROVIDER_FUNCTION_NAME_MISSING"
    )


if summary["pipeline_script_missing"]:

    critical.append(
        "PIPELINE_REFERENCES_MISSING_FILES"
    )


print(
    "CRITICAL_COUNT="
    f"{len(critical)}"
)

for item in critical:

    print(
        f"CRITICAL={item}"
    )


print(
    "WARNING_COUNT="
    f"{len(warnings)}"
)

for item in warnings:

    print(
        f"WARNING={item}"
    )


print()
print(
    "SCORE_CANDIDATE_DEFINITIONS="
    f"{score_defs}"
)

print(
    "ACTIVE_SCORE_CANDIDATE_LINE="
    f"{summary['active_score_candidate_line']}"
)

print(
    "VSE4_LOAD="
    f"{summary['vse_load']}"
)

print(
    "VSE4_SELF_TEST="
    f"{summary['vse_self_test']}"
)

print(
    "WRONG_GEO_HARD="
    f"{summary['wrong_geo_hard']}"
)

print(
    "CORRECT_GEO_HARD="
    f"{summary['correct_geo_hard']}"
)

print(
    "GEO_BEHAVIOR="
    f"{summary['geo_behavior']}"
)

print(
    "ACTIVE_MEDIA_COUNT="
    f"{summary['media_count']}"
)

print(
    "INVALID_SCENES="
    f"{summary['invalid_scene_count']}"
)

print(
    "SCENE_MAP_COUNT="
    f"{summary['scene_map_count']}"
)


if not critical:

    print()
    print(
        "PROJECT_CORE_CERTIFICATION=PASS"
    )

else:

    print()
    print(
        "PROJECT_CORE_CERTIFICATION=FAIL"
    )


if (
    summary["vse_load"] is True
    and
    summary["vse_self_test"] is True
    and
    summary["geo_behavior"] is True
):

    print(
        "VSE_RUNTIME_BEHAVIOR=PASS"
    )

else:

    print(
        "VSE_RUNTIME_BEHAVIOR=FAIL"
    )


if (
    summary["media_count"] == 12
    and
    summary["invalid_scene_count"] == 0
):

    print(
        "CANARY_MEDIA_SET=PASS"
    )

else:

    print(
        "CANARY_MEDIA_SET=FAIL"
    )


print()
print(
    "AUDIT_MODE=READ_ONLY"
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
