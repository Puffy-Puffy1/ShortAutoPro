#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import ast
import builtins
import hashlib
import importlib.util
import json
import os
import py_compile
import re
import shutil
import subprocess
import symtable
import time
import traceback


ROOT = Path.home() / "ShortAutoPro"
os.chdir(ROOT)

STAMP = time.strftime("%Y%m%d_%H%M%S")

RESULTS = []
PASS = 0
WARN = 0
FAIL = 0


def banner(title):

    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def record(status, name, detail=""):

    global PASS, WARN, FAIL

    status = status.upper()

    if status == "PASS":
        PASS += 1

    elif status == "WARN":
        WARN += 1

    else:
        FAIL += 1
        status = "FAIL"

    RESULTS.append(
        (
            status,
            name,
            str(detail),
        )
    )

    print(
        f"{status:4} | {name}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )


def sha256(path):

    h = hashlib.sha256()

    with Path(path).open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(chunk)

    return h.hexdigest()


def run(
    command,
    timeout=30,
):

    try:

        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
        )

        return (
            result.returncode,
            result.stdout,
            result.stderr,
        )

    except subprocess.TimeoutExpired:

        return (
            124,
            "",
            "TIMEOUT",
        )

    except Exception as exc:

        return (
            125,
            "",
            f"{type(exc).__name__}: {exc}",
        )


def production_python_files():

    files = []

    for path in ROOT.glob("*.py"):

        name = path.name.casefold()

        if "backup" in name:
            continue

        if name.startswith("."):
            continue

        files.append(path)

    return sorted(files)


def discover_short_id():

    env = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if env:
        return env


    candidates = []

    roteiro_dir = ROOT / "roteiros"

    if roteiro_dir.exists():

        pattern = re.compile(
            r"^short_(\d{4}-\d{2}-\d{2}_\d{4})\.txt$"
        )

        for path in roteiro_dir.glob(
            "short_*.txt"
        ):

            match = pattern.match(
                path.name
            )

            if not match:
                continue

            candidates.append(
                (
                    path.stat().st_mtime,
                    match.group(1),
                )
            )


    if candidates:

        candidates.sort(
            reverse=True
        )

        return candidates[0][1]


    return ""


banner(
    "SHORTAUTOPRO - AUDITORIA GERAL"
)

print(
    f"ROOT={ROOT}"
)

print(
    f"DATE={time.ctime()}"
)

SHORT_ID = discover_short_id()

print(
    f"SHORT_ID={SHORT_ID or 'NOT_DETECTED'}"
)


# ================================================================
# 1. STORAGE / ENVIRONMENT
# ================================================================

banner(
    "1. ENVIRONMENT / STORAGE"
)

try:

    usage = shutil.disk_usage(ROOT)

    free_mb = (
        usage.free
        /
        1024
        /
        1024
    )

    total_mb = (
        usage.total
        /
        1024
        /
        1024
    )

    print(
        f"DISK_TOTAL_MB={total_mb:.1f}"
    )

    print(
        f"DISK_FREE_MB={free_mb:.1f}"
    )

    if free_mb >= 1000:
        record(
            "PASS",
            "FREE_STORAGE",
            f"{free_mb:.0f} MB",
        )

    elif free_mb >= 400:
        record(
            "WARN",
            "FREE_STORAGE",
            f"somente {free_mb:.0f} MB",
        )

    else:
        record(
            "FAIL",
            "FREE_STORAGE",
            f"crítico: {free_mb:.0f} MB",
        )

except Exception as exc:

    record(
        "WARN",
        "DISK_CHECK",
        exc,
    )


code, out, err = run(
    [
        "python",
        "--version",
    ]
)

record(
    "PASS"
    if code == 0
    else "FAIL",
    "PYTHON",
    (
        out.strip()
        or
        err.strip()
    ),
)


code, out, err = run(
    [
        "ffmpeg",
        "-version",
    ]
)

record(
    "PASS"
    if code == 0
    else "FAIL",
    "FFMPEG",
    (
        out.splitlines()[0]
        if out
        else err
    ),
)


# ================================================================
# 2. CORE FILES
# ================================================================

banner(
    "2. CORE FILES"
)

core_files = [

    "gerar_short.sh",

    "midia.py",
    "video.py",
    "v6.py",

    "legenda_dinamica.py",

    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",

    "visual_selection_engine_v4.py",
    "visual_selection_final_gate_v3.py",

    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",

    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


for name in core_files:

    path = ROOT / name

    if path.is_file():

        record(
            "PASS",
            f"CORE_{name}",
            sha256(path)[:16],
        )

    else:

        record(
            "FAIL",
            f"CORE_{name}",
            "arquivo ausente",
        )


# ================================================================
# 3. PYTHON SYNTAX
# ================================================================

banner(
    "3. PYTHON COMPILE - PRODUCTION"
)

py_files = production_python_files()

compile_failed = []


for path in py_files:

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        compile_failed.append(
            (
                path.name,
                str(exc),
            )
        )


print(
    f"PYTHON_FILES_CHECKED={len(py_files)}"
)


if compile_failed:

    record(
        "FAIL",
        "PYTHON_COMPILE",
        f"{len(compile_failed)} arquivos",
    )

    for name, error in compile_failed[:50]:

        print(
            f"  COMPILE_FAIL={name}"
        )

        print(
            f"    {error}"
        )

else:

    record(
        "PASS",
        "PYTHON_COMPILE",
        f"{len(py_files)} arquivos",
    )


# ================================================================
# 4. AST PARSE
# ================================================================

banner(
    "4. AST STRUCTURE"
)

ast_failed = []


for path in py_files:

    try:

        ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception as exc:

        ast_failed.append(
            (
                path.name,
                str(exc),
            )
        )


if ast_failed:

    record(
        "FAIL",
        "AST_PARSE",
        len(ast_failed),
    )

    for item in ast_failed:

        print(
            "AST_FAIL=",
            item,
        )

else:

    record(
        "PASS",
        "AST_PARSE",
        f"{len(py_files)} arquivos",
    )


# ================================================================
# 5. SHELL SYNTAX
# ================================================================

banner(
    "5. SHELL SYNTAX"
)

shell_files = sorted(
    ROOT.glob("*.sh")
)

shell_failed = []


for path in shell_files:

    code, out, err = run(
        [
            "bash",
            "-n",
            str(path),
        ]
    )

    if code != 0:

        shell_failed.append(
            (
                path.name,
                err.strip(),
            )
        )


print(
    f"SHELL_FILES_CHECKED={len(shell_files)}"
)


if shell_failed:

    record(
        "FAIL",
        "SHELL_SYNTAX",
        len(shell_failed),
    )

    for item in shell_failed:

        print(
            "SHELL_FAIL=",
            item,
        )

else:

    record(
        "PASS",
        "SHELL_SYNTAX",
        len(shell_files),
    )


# ================================================================
# 6. GERAR_SHORT DEPENDENCIES
# ================================================================

banner(
    "6. MAIN PIPELINE DEPENDENCIES"
)

gerar = ROOT / "gerar_short.sh"

if gerar.is_file():

    text = gerar.read_text(
        encoding="utf-8",
        errors="replace",
    )


    refs = set(
        re.findall(
            r"(?:python|python3)\s+(?:-u\s+)?([A-Za-z0-9_./-]+\.py)",
            text,
        )
    )


    print(
        f"PIPELINE_PYTHON_REFERENCES={len(refs)}"
    )


    missing = []


    for ref in sorted(refs):

        path = ROOT / ref

        if path.exists():

            print(
                f"PIPELINE_SCRIPT=PASS | {ref}"
            )

        else:

            print(
                f"PIPELINE_SCRIPT=MISSING | {ref}"
            )

            missing.append(ref)


    if missing:

        record(
            "FAIL",
            "PIPELINE_DEPENDENCIES",
            ",".join(missing),
        )

    else:

        record(
            "PASS",
            "PIPELINE_DEPENDENCIES",
            len(refs),
        )


else:

    record(
        "FAIL",
        "PIPELINE_DEPENDENCIES",
        "gerar_short.sh ausente",
    )


# ================================================================
# 7. DUPLICATE TOP-LEVEL DEFINITIONS
# ================================================================

banner(
    "7. DUPLICATE DEFINITIONS"
)

duplicate_files = []


for path in py_files:

    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception:
        continue


    names = [

        node.name

        for node in tree.body

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        )
    ]


    counts = Counter(names)

    duplicates = {

        name: count

        for name, count
        in counts.items()

        if count > 1
    }


    if duplicates:

        duplicate_files.append(
            (
                path.name,
                duplicates,
            )
        )


if duplicate_files:

    record(
        "WARN",
        "DUPLICATE_DEFINITIONS",
        len(duplicate_files),
    )

    for name, duplicates in duplicate_files:

        print(
            f"DUPLICATE={name} | {duplicates}"
        )

else:

    record(
        "PASS",
        "DUPLICATE_DEFINITIONS",
        "NONE",
    )


# ================================================================
# 8. VSE4 GLOBAL AUDIT
# ================================================================

banner(
    "8. VSE4 GLOBAL AUDIT"
)

vse = ROOT / "visual_selection_engine_v4.py"

if vse.is_file():

    try:

        source = vse.read_text(
            encoding="utf-8",
            errors="replace",
        )

        table = symtable.symtable(
            source,
            str(vse),
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

        ignored = {
            "__name__",
            "__file__",
            "__package__",
            "__spec__",
        }

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

                    if name in ignored:
                        continue

                    unresolved.add(name)

                walk(child)


        walk(table)


        if unresolved:

            record(
                "FAIL",
                "VSE4_UNRESOLVED_GLOBALS",
                ",".join(
                    sorted(unresolved)
                ),
            )

        else:

            record(
                "PASS",
                "VSE4_UNRESOLVED_GLOBALS",
                "NONE",
            )


    except Exception as exc:

        record(
            "FAIL",
            "VSE4_GLOBAL_AUDIT",
            exc,
        )

else:

    record(
        "FAIL",
        "VSE4_GLOBAL_AUDIT",
        "arquivo ausente",
    )


# ================================================================
# 9. VSE4 SELF TEST
# ================================================================

banner(
    "9. VSE4 RUNTIME SELF TEST"
)

if vse.is_file():

    code, out, err = run(
        [
            "python",
            str(vse),
        ],
        timeout=45,
    )


    combined = (
        out
        +
        "\n"
        +
        err
    ).strip()


    if code == 0:

        record(
            "PASS",
            "VSE4_SELF_TEST",
            "exit=0",
        )

    else:

        record(
            "FAIL",
            "VSE4_SELF_TEST",
            f"exit={code}",
        )


        print()
        print(
            "----- VSE4 SELF TEST TAIL -----"
        )

        for line in combined.splitlines()[-50:]:

            print(line)


else:

    record(
        "FAIL",
        "VSE4_SELF_TEST",
        "arquivo ausente",
    )


# ================================================================
# 10. VSE4 SEMANTIC / GEO TEST
# ================================================================

banner(
    "10. VSE4 SEMANTIC QUALITY TEST"
)

if vse.is_file():

    try:

        import runpy

        ns = runpy.run_path(
            str(vse),
            run_name="shortautopro_general_audit",
        )


        score_candidate = ns.get(
            "score_candidate"
        )

        geo_hits = ns.get(
            "geo_hits"
        )


        if not callable(score_candidate):

            record(
                "FAIL",
                "VSE4_SCORE_FUNCTION",
                "score_candidate ausente",
            )

        else:

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


            geo_ok = False

            if callable(geo_hits):

                sp_geo = set(
                    geo_hits(
                        "São Paulo Brasil"
                    )
                )

                ny_geo = set(
                    geo_hits(
                        "Empire State Building "
                        "Manhattan New York"
                    )
                )

                print(
                    "SAO_PAULO_GEO=",
                    sorted(sp_geo),
                )

                print(
                    "NEW_YORK_GEO=",
                    sorted(ny_geo),
                )


                geo_ok = (
                    bool(sp_geo)
                    and
                    bool(ny_geo)
                    and
                    sp_geo != ny_geo
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
                        -999999,
                    )
                )
                >
                float(
                    a.get(
                        "effective",
                        999999,
                    )
                )
            )


            record(
                "PASS"
                if geo_ok
                else "FAIL",
                "VSE4_GEO_DISTINCTION",
            )


            record(
                "PASS"
                if semantic_ok
                else "FAIL",
                "VSE4_HARD_MISMATCH_LOGIC",
                (
                    "São Paulo vs New York"
                ),
            )


    except Exception as exc:

        record(
            "FAIL",
            "VSE4_SEMANTIC_TEST",
            f"{type(exc).__name__}: {exc}",
        )

        traceback.print_exc()


# ================================================================
# 11. PROVIDER ACQUISITION
# ================================================================

banner(
    "11. PROVIDER ACQUISITION"
)

midia = ROOT / "midia.py"


required_provider_functions = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
)


if midia.is_file():

    try:

        tree = ast.parse(
            midia.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )


        definitions = {

            node.name: node

            for node in tree.body

            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        missing = []


        for name in required_provider_functions:

            node = definitions.get(name)

            if node:

                print(
                    f"PROVIDER_FUNCTION_{name}=PASS "
                    f"lines={node.lineno}-{node.end_lineno}"
                )

            else:

                print(
                    f"PROVIDER_FUNCTION_{name}=MISSING"
                )

                missing.append(name)


        buscar = definitions.get(
            "buscar_todos_candidatos"
        )


        expected_calls = {
            "pexels_video",
            "pexels_foto",
            "pixabay_video",
            "pixabay_foto",
            "coverr_video",
        }


        found_calls = set()


        if buscar:

            for node in ast.walk(buscar):

                if not isinstance(
                    node,
                    ast.Call,
                ):
                    continue

                if isinstance(
                    node.func,
                    ast.Name,
                ):

                    if (
                        node.func.id
                        in expected_calls
                    ):

                        found_calls.add(
                            node.func.id
                        )


        for name in sorted(
            expected_calls
        ):

            print(
                f"ACQUISITION_CALL_{name}="
                +
                (
                    "PASS"
                    if name in found_calls
                    else "MISSING"
                )
            )


        missing_calls = (
            expected_calls
            -
            found_calls
        )


        if missing or missing_calls:

            record(
                "FAIL",
                "PROVIDER_ACQUISITION",
                (
                    f"functions={missing} "
                    f"calls={sorted(missing_calls)}"
                ),
            )

        else:

            record(
                "PASS",
                "PROVIDER_ACQUISITION",
                "estrutura completa",
            )


    except Exception as exc:

        record(
            "FAIL",
            "PROVIDER_ACQUISITION",
            exc,
        )


# ================================================================
# 12. VSE INTEGRATION STATUS
# ================================================================

banner(
    "12. VISUAL ENGINE INTEGRATION"
)

if midia.is_file():

    midia_text = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )


    checks = {

        "VSE4":
            "visual_selection_engine_v4"
            in midia_text,

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
    }


    for name, ok in checks.items():

        print(
            f"MIDIA_{name}="
            f"{'PASS' if ok else 'MISSING'}"
        )


    if checks["VSE4"]:

        record(
            "PASS",
            "VSE4_MIDIA_INTEGRATION",
        )

    else:

        record(
            "WARN",
            "VSE4_MIDIA_INTEGRATION",
            "VSE4 ainda não está ativo em midia.py",
        )


    if checks["DIVERSITY"]:

        record(
            "PASS",
            "DIVERSITY_INTEGRATION",
        )

    else:

        record(
            "WARN",
            "DIVERSITY_INTEGRATION",
            "não encontrado em midia.py",
        )


# ================================================================
# 13. COMMIT LOCK
# ================================================================

banner(
    "13. SCENE COMMIT LOCK"
)

commit_module = (
    ROOT
    /
    "visual_scene_commit_lock_v1.py"
)

if commit_module.is_file():

    text = commit_module.read_text(
        encoding="utf-8",
        errors="replace",
    )


    markers = (
        "SCENE_COMMIT_LOCK=COMMITTED"
        in text
        and
        "SCENE_COMMIT_LOCK=BLOCKED"
        in text
    )


    record(
        "PASS"
        if markers
        else "FAIL",
        "COMMIT_LOCK_MARKERS",
    )


    integration_found = False


    for candidate in (
        ROOT / "midia.py",
        ROOT / "media_diversity_guard_v1.py",
    ):

        if candidate.is_file():

            data = candidate.read_text(
                encoding="utf-8",
                errors="replace",
            )

            if (
                "visual_scene_commit_lock_v1"
                in data
                or
                "SCENE_COMMIT_LOCK"
                in data
            ):

                integration_found = True


    record(
        "PASS"
        if integration_found
        else "WARN",
        "COMMIT_LOCK_INTEGRATION",
        (
            "found"
            if integration_found
            else "módulo existe, integração não detectada"
        ),
    )


else:

    record(
        "FAIL",
        "COMMIT_LOCK_MODULE",
        "ausente",
    )


# ================================================================
# 14. CURRENT MEDIA SET
# ================================================================

banner(
    "14. CURRENT MEDIA SET"
)

if SHORT_ID:

    media_dir = (
        ROOT
        /
        "imagens"
        /
        f"short_{SHORT_ID}"
    )


    if not media_dir.is_dir():

        record(
            "WARN",
            "MEDIA_DIRECTORY",
            str(media_dir),
        )

    else:

        record(
            "PASS",
            "MEDIA_DIRECTORY",
            str(media_dir),
        )


        bad_scene_count = 0
        all_media = []


        for number in range(
            1,
            13,
        ):

            pattern = (
                f"scene_{number:02d}.*"
            )


            matches = [

                p

                for p
                in media_dir.glob(pattern)

                if p.is_file()
            ]


            print(
                f"SCENE_{number:02d}_COUNT="
                f"{len(matches)}"
            )


            if len(matches) != 1:

                bad_scene_count += 1


            all_media.extend(
                matches
            )


        if bad_scene_count:

            record(
                "FAIL",
                "MEDIA_SCENE_CARDINALITY",
                f"{bad_scene_count} cenas inválidas",
            )

        else:

            record(
                "PASS",
                "MEDIA_SCENE_CARDINALITY",
                "12/12",
            )


        # Exact duplicate detection.
        hash_map = {}


        for path in all_media:

            try:

                h = sha256(path)

                hash_map.setdefault(
                    h,
                    [],
                ).append(
                    path.name
                )

            except Exception:
                pass


        duplicate_assets = {

            h: names

            for h, names
            in hash_map.items()

            if len(names) > 1
        }


        if duplicate_assets:

            record(
                "WARN",
                "EXACT_MEDIA_DUPLICATES",
                len(duplicate_assets),
            )

            for h, names in duplicate_assets.items():

                print(
                    f"DUPLICATE_MEDIA={h[:16]} | {names}"
                )

        else:

            record(
                "PASS",
                "EXACT_MEDIA_DUPLICATES",
                "NONE",
            )


        # Technical media health.
        invalid_media = []


        for path in all_media:

            code, out, err = run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=codec_name,width,height",
                    "-of",
                    "json",
                    str(path),
                ],
                timeout=20,
            )


            if code != 0:

                invalid_media.append(
                    (
                        path.name,
                        err.strip(),
                    )
                )

                continue


            try:

                data = json.loads(out)

                streams = data.get(
                    "streams",
                    [],
                )

                if not streams:

                    invalid_media.append(
                        (
                            path.name,
                            "no video/image stream",
                        )
                    )

            except Exception:

                invalid_media.append(
                    (
                        path.name,
                        "ffprobe json invalid",
                    )
                )


        if invalid_media:

            record(
                "FAIL",
                "MEDIA_TECHNICAL_HEALTH",
                len(invalid_media),
            )

            for item in invalid_media:

                print(
                    "INVALID_MEDIA=",
                    item,
                )

        else:

            record(
                "PASS",
                "MEDIA_TECHNICAL_HEALTH",
                len(all_media),
            )


else:

    record(
        "WARN",
        "CURRENT_SHORT_ID",
        "não detectado",
    )


# ================================================================
# 15. CURRENT SHORT RENDER INPUTS
# ================================================================

banner(
    "15. RENDER INPUTS"
)

if SHORT_ID:

    required = {

        "AUDIO":
            ROOT
            /
            "audios"
            /
            f"short_{SHORT_ID}.mp3",

        "ASS":
            ROOT
            /
            "videos"
            /
            f"short_{SHORT_ID}.ass",

        "VIDEO_BASE":
            ROOT
            /
            "temp"
            /
            SHORT_ID
            /
            "video_sem_audio.mp4",

        "FINAL":
            ROOT
            /
            "videos"
            /
            f"short_v6_{SHORT_ID}.mp4",
    }


    for name, path in required.items():

        if (
            path.is_file()
            and
            path.stat().st_size > 0
        ):

            record(
                "PASS",
                f"RENDER_{name}",
                (
                    f"{path.stat().st_size} bytes"
                ),
            )

        else:

            # FINAL / VIDEO_BASE may not exist before render.
            status = (
                "WARN"
                if name in {
                    "FINAL",
                    "VIDEO_BASE",
                }
                else "FAIL"
            )

            record(
                status,
                f"RENDER_{name}",
                "ausente",
            )


# ================================================================
# 16. FRESH RENDER GUARD SYNTHETIC TEST
# ================================================================

banner(
    "16. FRESH RENDER GUARD SAFETY"
)

guard_path = (
    ROOT
    /
    "fresh_render_guard_v1.py"
)

if guard_path.is_file():

    sid = (
        "AUDIT_GUARD_"
        +
        str(os.getpid())
    )


    temp_dir = (
        ROOT
        /
        "temp"
        /
        sid
    )

    videos_dir = (
        ROOT
        /
        "videos"
    )


    ass = (
        videos_dir
        /
        f"short_{sid}.ass"
    )

    final = (
        videos_dir
        /
        f"short_v6_{sid}.mp4"
    )

    audio = (
        temp_dir
        /
        "test.mp3"
    )

    temp_video = (
        temp_dir
        /
        "video_sem_audio.mp4"
    )


    try:

        temp_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        videos_dir.mkdir(
            parents=True,
            exist_ok=True,
        )


        ass.write_text(
            "PROTECTED",
            encoding="utf-8",
        )

        audio.write_bytes(
            b"AUDIO"
        )

        final.write_bytes(
            b"VIDEO"
        )

        temp_video.write_bytes(
            b"VIDEO"
        )


        spec = importlib.util.spec_from_file_location(
            "sap_render_guard_audit",
            guard_path,
        )

        module = importlib.util.module_from_spec(
            spec
        )

        spec.loader.exec_module(
            module
        )


        if not hasattr(
            module,
            "clean",
        ):

            raise RuntimeError(
                "clean() ausente"
            )


        module.clean(
            sid
        )


        ass_ok = ass.exists()
        audio_ok = audio.exists()

        final_removed = (
            not final.exists()
        )

        temp_removed = (
            not temp_video.exists()
        )


        print(
            f"GUARD_ASS_PROTECTED={ass_ok}"
        )

        print(
            f"GUARD_AUDIO_PROTECTED={audio_ok}"
        )

        print(
            f"GUARD_FINAL_REMOVED={final_removed}"
        )

        print(
            f"GUARD_TEMP_REMOVED={temp_removed}"
        )


        if (
            ass_ok
            and
            audio_ok
            and
            final_removed
            and
            temp_removed
        ):

            record(
                "PASS",
                "RENDER_GUARD_SYNTHETIC",
            )

        else:

            record(
                "FAIL",
                "RENDER_GUARD_SYNTHETIC",
            )


    except Exception as exc:

        record(
            "FAIL",
            "RENDER_GUARD_SYNTHETIC",
            f"{type(exc).__name__}: {exc}",
        )


    finally:

        try:
            ass.unlink(
                missing_ok=True
            )
        except Exception:
            pass

        try:
            final.unlink(
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

    record(
        "FAIL",
        "RENDER_GUARD_SYNTHETIC",
        "guard ausente",
    )


# ================================================================
# 17. SHORT_ID CONSISTENCY
# ================================================================

banner(
    "17. SHORT_ID CONSISTENCY"
)

for filename in (
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
):

    path = ROOT / filename

    if not path.is_file():
        continue

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    env_support = (
        'os.getenv("SHORT_ID"'
        in text
        or
        "os.getenv(\n" in text
        and
        '"SHORT_ID"' in text
    )


    record(
        "PASS"
        if env_support
        else "WARN",
        f"SHORT_ID_ENV_{filename}",
        (
            "explicit env support"
            if env_support
            else "não detectado"
        ),
    )


# Hard-coded IDs in production source.
hardcoded = []


id_regex = re.compile(
    r"20\d{2}-\d{2}-\d{2}_\d{4}"
)


for path in py_files:

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    ids = sorted(
        set(
            id_regex.findall(text)
        )
    )


    if ids:

        hardcoded.append(
            (
                path.name,
                ids,
            )
        )


if hardcoded:

    record(
        "WARN",
        "HARDCODED_SHORT_IDS",
        len(hardcoded),
    )

    for item in hardcoded[:30]:

        print(
            "HARDCODED_ID=",
            item,
        )

else:

    record(
        "PASS",
        "HARDCODED_SHORT_IDS",
        "NONE",
    )


# ================================================================
# 18. RISKY CODE PATTERNS
# ================================================================

banner(
    "18. RISKY CODE PATTERNS"
)

patterns = {

    "SHELL_TRUE":
        r"shell\s*=\s*True",

    "EVAL":
        r"\beval\s*\(",

    "EXEC":
        r"\bexec\s*\(",

    "RM_RF":
        r"\brm\s+-rf\b",

    "RMTREE":
        r"shutil\.rmtree\s*\(",

    "UNLINK":
        r"\.unlink\s*\(",

    "OS_REMOVE":
        r"os\.remove\s*\(",

    "TMP_PATH":
        r'["\']/tmp(?:/|["\'])',
}


risk_count = 0


for path in py_files:

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for name, pattern in patterns.items():

        matches = list(
            re.finditer(
                pattern,
                text,
                re.IGNORECASE,
            )
        )


        if matches:

            risk_count += len(
                matches
            )

            lines = text.splitlines()

            for match in matches[:5]:

                line = (
                    text[:match.start()]
                    .count("\n")
                    +
                    1
                )

                content = (
                    lines[line - 1].strip()
                    if line <= len(lines)
                    else ""
                )


                print(
                    f"RISK={name} "
                    f"FILE={path.name} "
                    f"LINE={line} "
                    f"CODE={content[:180]}"
                )


if risk_count:

    record(
        "WARN",
        "RISKY_CODE_PATTERNS",
        risk_count,
    )

else:

    record(
        "PASS",
        "RISKY_CODE_PATTERNS",
        "NONE",
    )


# ================================================================
# 19. NETWORK TIMEOUT AUDIT
# ================================================================

banner(
    "19. NETWORK TIMEOUT AUDIT"
)

network_without_timeout = []


for path in py_files:

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(source)

    except Exception:
        continue


    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue


        func_text = ""

        try:
            func_text = ast.unparse(
                node.func
            )
        except Exception:
            continue


        interesting = any(
            term in func_text
            for term in (
                "requests.get",
                "requests.post",
                "requests.request",
                "session.get",
                "session.post",
                "urlopen",
            )
        )


        if not interesting:
            continue


        has_timeout = any(
            keyword.arg == "timeout"
            for keyword in node.keywords
        )


        if (
            not has_timeout
            and
            "urlopen" not in func_text
        ):

            network_without_timeout.append(
                (
                    path.name,
                    node.lineno,
                    func_text,
                )
            )


if network_without_timeout:

    record(
        "WARN",
        "NETWORK_CALLS_WITHOUT_TIMEOUT",
        len(network_without_timeout),
    )

    for item in network_without_timeout[:50]:

        print(
            "NO_TIMEOUT=",
            item,
        )

else:

    record(
        "PASS",
        "NETWORK_CALLS_WITHOUT_TIMEOUT",
        "NONE",
    )


# ================================================================
# 20. RECENT LOG ERRORS
# ================================================================

banner(
    "20. RECENT LOG ERROR SCAN"
)

log_dir = (
    ROOT
    /
    "logs"
    /
    "producao"
)

error_pattern = re.compile(
    r"Traceback|ERRO|ERROR|FAILED|FAIL\b|Exception",
    re.IGNORECASE,
)


if log_dir.is_dir():

    logs = sorted(
        [
            p
            for p
            in log_dir.iterdir()
            if p.is_file()
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:20]


    logs_with_errors = []


    for path in logs:

        try:

            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        except Exception:
            continue


        matches = error_pattern.findall(
            text
        )


        if matches:

            logs_with_errors.append(
                (
                    path.name,
                    len(matches),
                )
            )


    print(
        f"RECENT_LOGS_CHECKED={len(logs)}"
    )


    if logs_with_errors:

        record(
            "WARN",
            "RECENT_LOG_ERRORS",
            len(logs_with_errors),
        )

        for item in logs_with_errors:

            print(
                "LOG_ERROR=",
                item,
            )

    else:

        record(
            "PASS",
            "RECENT_LOG_ERRORS",
            "NONE",
        )

else:

    record(
        "WARN",
        "RECENT_LOG_ERRORS",
        "logs/producao ausente",
    )


# ================================================================
# 21. FINAL VIDEO HEALTH
# ================================================================

banner(
    "21. FINAL VIDEO HEALTH"
)

if SHORT_ID:

    final = (
        ROOT
        /
        "videos"
        /
        f"short_v6_{SHORT_ID}.mp4"
    )


    if final.is_file():

        code, out, err = run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                (
                    "stream=codec_name,codec_type,"
                    "width,height,r_frame_rate:"
                    "format=duration,size,bit_rate"
                ),
                "-of",
                "json",
                str(final),
            ],
            timeout=20,
        )


        if code == 0:

            try:

                data = json.loads(out)

                duration = float(
                    data.get(
                        "format",
                        {},
                    ).get(
                        "duration",
                        0,
                    )
                )


                streams = data.get(
                    "streams",
                    [],
                )


                video_stream = next(
                    (
                        s
                        for s in streams
                        if s.get(
                            "codec_type"
                        )
                        ==
                        "video"
                    ),
                    None,
                )


                audio_stream = next(
                    (
                        s
                        for s in streams
                        if s.get(
                            "codec_type"
                        )
                        ==
                        "audio"
                    ),
                    None,
                )


                print(
                    f"FINAL_DURATION={duration}"
                )

                print(
                    f"FINAL_SHA256={sha256(final)}"
                )


                if (
                    video_stream
                    and
                    audio_stream
                    and
                    duration > 1
                ):

                    record(
                        "PASS",
                        "FINAL_VIDEO_HEALTH",
                        (
                            f"{video_stream.get('width')}x"
                            f"{video_stream.get('height')} "
                            f"{duration:.2f}s"
                        ),
                    )

                else:

                    record(
                        "FAIL",
                        "FINAL_VIDEO_HEALTH",
                        "stream/duração inválidos",
                    )


            except Exception as exc:

                record(
                    "FAIL",
                    "FINAL_VIDEO_HEALTH",
                    exc,
                )


        else:

            record(
                "FAIL",
                "FINAL_VIDEO_HEALTH",
                err.strip(),
            )


    else:

        record(
            "WARN",
            "FINAL_VIDEO_HEALTH",
            "final não existe",
        )


# ================================================================
# 22. BACKUP HEALTH
# ================================================================

banner(
    "22. BACKUP HEALTH"
)

backup_dir = ROOT / "backups"

if backup_dir.is_dir():

    items = list(
        backup_dir.iterdir()
    )

    record(
        "PASS",
        "BACKUPS",
        f"{len(items)} entradas",
    )


    recent = sorted(
        items,
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:10]


    for path in recent:

        print(
            "RECENT_BACKUP="
            f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(path.stat().st_mtime))}"
            f" | {path.name}"
        )

else:

    record(
        "WARN",
        "BACKUPS",
        "diretório ausente",
    )


# ================================================================
# 23. CORE HASHES
# ================================================================

banner(
    "23. CORE HASHES"
)

for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
):

    path = ROOT / name

    if path.is_file():

        print(
            f"SHA256_{name}="
            f"{sha256(path)}"
        )


# ================================================================
# 24. FINAL SUMMARY
# ================================================================

banner(
    "24. FINAL SUMMARY"
)

print(
    f"TOTAL_PASS={PASS}"
)

print(
    f"TOTAL_WARN={WARN}"
)

print(
    f"TOTAL_FAIL={FAIL}"
)


print()
print(
    "---------------- FAILURES ----------------"
)

failures = [
    item
    for item in RESULTS
    if item[0] == "FAIL"
]


if failures:

    for status, name, detail in failures:

        print(
            f"FAIL | {name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )

else:

    print(
        "FAILURES=NONE"
    )


print()
print(
    "---------------- WARNINGS ----------------"
)

warnings = [
    item
    for item in RESULTS
    if item[0] == "WARN"
]


if warnings:

    for status, name, detail in warnings:

        print(
            f"WARN | {name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )

else:

    print(
        "WARNINGS=NONE"
    )


print()
print(
    "============================================================"
)

if FAIL == 0:

    if WARN == 0:

        print(
            "AUDIT_STATUS=CLEAN"
        )

    else:

        print(
            "AUDIT_STATUS=PASS_WITH_WARNINGS"
        )

else:

    print(
        "AUDIT_STATUS=FAIL"
    )


print(
    "NETWORK_DOWNLOAD_EXECUTED=NO"
)

print(
    "MEDIA_SELECTION_EXECUTED=NO"
)

print(
    "VIDEO_RENDER_EXECUTED=NO"
)

print(
    "PROJECT_FILES_MODIFIED=NO"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)

print(
    "============================================================"
)
