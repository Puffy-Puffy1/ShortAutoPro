#!/usr/bin/env python3

from __future__ import annotations

import ast
import builtins
import hashlib
import os
import re
import shlex
import subprocess
import symtable
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

REPORT = (
    ROOT
    / "temp"
    / "SAP_RUNTIME_TRUTH_AUDIT_V4.txt"
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


CRITICAL_FILES = [
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v4.py",
    "visual_selection_runtime_v42.py",
    "visual_selection_bridge_v42.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
]


VISUAL_FLAGS = [
    "SAP_VSE_V2",
    "SAP_VSE_V3",
    "SAP_VSE_V4",
    "SAP_VSE_V42",
    "SAP_VSE4",
    "SAP_VSE42",
    "SAP_VSE4_RUNTIME",
    "SAP_SCENE_COMMIT_LOCK",
]


SEVERITY = {
    "CRITICAL": 0,
    "HIGH": 0,
    "MEDIUM": 0,
    "LOW": 0,
}


findings = []


def emit(text=""):

    print(text)

    with REPORT.open(
        "a",
        encoding="utf-8",
    ) as f:

        f.write(
            text + "\n"
        )


def section(title):

    emit()
    emit("=" * 78)
    emit(title)
    emit("=" * 78)


def finding(level, code, message):

    SEVERITY[level] += 1

    findings.append(
        (
            level,
            code,
            message,
        )
    )

    emit(
        f"[{level}] {code}: {message}"
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


def text(path):

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        return ""


def parse_python(path):

    try:

        src = text(path)

        return (
            ast.parse(
                src,
                filename=str(path),
            ),
            src,
            None,
        )

    except Exception as exc:

        return (
            None,
            "",
            exc,
        )


# reset report
REPORT.write_text(
    "",
    encoding="utf-8",
)


section(
    "SHORTAUTOPRO MASTER RUNTIME TRUTH AUDIT V4"
)

emit(
    f"ROOT={ROOT}"
)

emit(
    f"PID={os.getpid()}"
)

emit(
    "MODE=OFFLINE_READ_ONLY"
)


# ============================================================
# 1. CORE EXISTENCE + HASHES
# ============================================================

section(
    "1. CORE FILES / HASHES"
)


for name in CRITICAL_FILES:

    path = ROOT / name

    if path.is_file():

        emit(
            f"FOUND {name}"
        )

        emit(
            f"SHA256 {name} "
            f"{sha256(path)}"
        )

    else:

        emit(
            f"MISSING {name}"
        )

        if name in (
            "gerar_short.sh",
            "midia.py",
            "video.py",
            "v6.py",
        ):

            finding(
                "CRITICAL",
                "CORE_FILE_MISSING",
                name,
            )

        else:

            finding(
                "MEDIUM",
                "OPTIONAL_RUNTIME_FILE_MISSING",
                name,
            )


# ============================================================
# 2. PYTHON COMPILE
# ============================================================

section(
    "2. ROOT PYTHON SYNTAX"
)


python_files = sorted(
    p
    for p in ROOT.glob("*.py")
    if p.is_file()
)


compile_fail = []


for path in python_files:

    result = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        compile_fail.append(
            path.name
        )

        emit(
            f"COMPILE_FAIL {path.name}"
        )

        emit(
            result.stderr.strip()
        )


emit(
    f"ROOT_PY_FILES={len(python_files)}"
)

emit(
    f"COMPILE_FAILURES={len(compile_fail)}"
)


if compile_fail:

    finding(
        "CRITICAL",
        "PYTHON_SYNTAX_FAILURE",
        ",".join(
            compile_fail
        ),
    )

else:

    emit(
        "PYTHON_COMPILE=PASS"
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)


shell_files = sorted(
    list(
        ROOT.glob("*.sh")
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
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:

        shell_fail.append(
            path.name
        )

        emit(
            f"SHELL_FAIL {path.name}"
        )

        emit(
            result.stderr.strip()
        )


emit(
    f"ROOT_SH_FILES={len(shell_files)}"
)

emit(
    f"SHELL_FAILURES={len(shell_fail)}"
)


if shell_fail:

    finding(
        "CRITICAL",
        "SHELL_SYNTAX_FAILURE",
        ",".join(
            shell_fail
        ),
    )

else:

    emit(
        "SHELL_SYNTAX=PASS"
    )


# ============================================================
# 4. LAUNCHER FLAGS
# ============================================================

section(
    "4. ACTIVE LAUNCHER FLAGS"
)


launcher = text(
    ROOT / "gerar_short.sh"
)


flag_values = {}


for flag in VISUAL_FLAGS:

    pattern = re.compile(
        rf"^\s*export\s+{re.escape(flag)}\s*=\s*"
        r"""["']?([^"'#\s]+)""",
        re.MULTILINE,
    )

    matches = pattern.findall(
        launcher
    )

    if matches:

        flag_values[
            flag
        ] = matches[-1]

        emit(
            f"{flag}={matches[-1]}"
        )

        if len(matches) > 1:

            finding(
                "MEDIUM",
                "FLAG_REDEFINED",
                f"{flag} aparece "
                f"{len(matches)} vezes",
            )

    else:

        emit(
            f"{flag}=UNSET"
        )


disabled_visual_flags = [
    k
    for k, v in flag_values.items()
    if str(v).strip() == "0"
]


if len(
    disabled_visual_flags
) >= 5:

    finding(
        "HIGH",
        "VISUAL_RUNTIME_DISABLED",
        "launcher desliga: "
        +
        ",".join(
            disabled_visual_flags
        ),
    )


# ============================================================
# 5. FLAG REFERENCES / DEFAULTS
# ============================================================

section(
    "5. VISUAL FLAG REFERENCES"
)


for flag in VISUAL_FLAGS:

    refs = []

    for path in python_files:

        src = text(path)

        for lineno, line in enumerate(
            src.splitlines(),
            1,
        ):

            if flag in line:

                refs.append(
                    (
                        path.name,
                        lineno,
                        line.strip(),
                    )
                )


    emit()
    emit(
        f"FLAG={flag} REFERENCES={len(refs)}"
    )

    for file_name, line, content in refs[:25]:

        emit(
            f"  {file_name}:{line}: "
            f"{content[:180]}"
        )


# ============================================================
# 6. DUPLICATE TOP-LEVEL DEFINITIONS
# ============================================================

section(
    "6. TOP-LEVEL FUNCTION SHADOWING"
)


shadowed_files = {}


for path in python_files:

    tree, src, error = parse_python(
        path
    )

    if tree is None:
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
        name: lines
        for name, lines in defs.items()
        if len(lines) > 1
    }


    if duplicates:

        shadowed_files[
            path.name
        ] = duplicates


        emit()
        emit(
            f"FILE={path.name}"
        )

        for name, lines in sorted(
            duplicates.items()
        ):

            emit(
                f"  SHADOWED {name} "
                f"COUNT={len(lines)} "
                f"LINES={lines}"
            )


            if (
                path.name
                ==
                "visual_selection_engine_v4.py"
                and
                name
                ==
                "score_candidate"
            ):

                finding(
                    "HIGH",
                    "VSE4_SCORE_SHADOWING",
                    f"score_candidate definido "
                    f"{len(lines)} vezes; "
                    f"efetivo=line {lines[-1]}",
                )


emit()
emit(
    f"FILES_WITH_SHADOWED_FUNCTIONS="
    f"{len(shadowed_files)}"
)


# ============================================================
# 7. EFFECTIVE VSE4 FUNCTIONS
# ============================================================

section(
    "7. EFFECTIVE VSE4 FUNCTION MAP"
)


vse_path = (
    ROOT
    /
    "visual_selection_engine_v4.py"
)


vse_tree, vse_src, vse_error = (
    parse_python(
        vse_path
    )
)


if vse_tree:

    defs = defaultdict(
        list
    )

    for node in vse_tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            defs[
                node.name
            ].append(
                (
                    node.lineno,
                    node.end_lineno,
                )
            )


    important = [
        "score_candidate",
        "choose_from_context",
        "geo_hits",
        "concept_hits",
        "must_tier",
        "candidate_text",
        "tokens",
    ]


    for name in important:

        items = defs.get(
            name,
            [],
        )

        if not items:

            emit(
                f"{name}=MISSING"
            )

            finding(
                "HIGH",
                "VSE4_FUNCTION_MISSING",
                name,
            )

            continue


        emit(
            f"{name} "
            f"COUNT={len(items)} "
            f"EFFECTIVE={items[-1]}"
        )


# ============================================================
# 8. UNRESOLVED GLOBALS
# ============================================================

section(
    "8. UNRESOLVED GLOBAL NAMES"
)


audit_targets = [
    "visual_selection_engine_v4.py",
    "visual_selection_runtime_v42.py",
    "visual_selection_bridge_v42.py",
    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
]


builtin_names = set(
    dir(builtins)
)


for name in audit_targets:

    path = ROOT / name

    if not path.is_file():
        continue


    src = text(path)


    try:

        table = symtable.symtable(
            src,
            name,
            "exec",
        )

    except Exception as exc:

        emit(
            f"{name}: SYMBOL_TABLE_FAIL={exc}"
        )

        continue


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


    def walk(scope):

        for child in scope.get_children():

            for symbol in child.get_symbols():

                n = symbol.get_name()

                if not symbol.is_referenced():
                    continue

                if not symbol.is_global():
                    continue

                if n in module_defined:
                    continue

                if n in builtin_names:
                    continue

                unresolved.add(n)

            walk(child)


    walk(table)


    emit(
        f"{name}: "
        f"UNRESOLVED="
        +
        (
            ",".join(
                sorted(unresolved)
            )
            if unresolved
            else
            "NONE"
        )
    )


    if unresolved:

        finding(
            "HIGH",
            "UNRESOLVED_GLOBAL",
            f"{name}: "
            +
            ",".join(
                sorted(unresolved)
            ),
        )


# ============================================================
# 9. LOCAL IMPORT RESOLUTION
# ============================================================

section(
    "9. LOCAL IMPORT RESOLUTION"
)


known_local = {
    p.stem
    for p in python_files
}


missing_local_imports = set()


for path in python_files:

    tree, src, error = parse_python(
        path
    )

    if tree is None:
        continue


    for node in ast.walk(tree):

        module = None

        if isinstance(
            node,
            ast.Import,
        ):

            modules = [
                alias.name
                for alias in node.names
            ]

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            modules = (
                [node.module]
                if node.module
                else []
            )

        else:

            continue


        for module in modules:

            root_module = (
                module.split(".")[0]
            )

            # Focus only likely ShortAutoPro local modules.
            if root_module.startswith(
                (
                    "visual_",
                    "media_",
                    "vi",
                    "vg",
                )
            ):

                if (
                    root_module
                    not in known_local
                ):

                    missing_local_imports.add(
                        (
                            path.name,
                            node.lineno,
                            root_module,
                        )
                    )


for item in sorted(
    missing_local_imports
):

    emit(
        "MISSING_LOCAL_IMPORT "
        f"{item[0]}:{item[1]} "
        f"{item[2]}"
    )


if missing_local_imports:

    finding(
        "HIGH",
        "BROKEN_LOCAL_IMPORTS",
        f"{len(missing_local_imports)} "
        "referências",
    )

else:

    emit(
        "LOCAL_IMPORT_RESOLUTION=PASS"
    )


# ============================================================
# 10. MIDIA PIPELINE ORDER
# ============================================================

section(
    "10. MIDIA ACTIVE VISUAL PIPELINE ORDER"
)


midia_path = (
    ROOT / "midia.py"
)

midia_src = text(
    midia_path
)


markers = [
    "VSE417",
    "VSE42",
    "VG4X",
    "FINAL POOL",
    "PRIMARY RANK",
    "ALT RANK",
    "SCENE COMMIT",
    "FIRST_SUCCESS",
    "cleanup_scene_sibling",
    "baixar_candidato_5_2",
    "ordenar_failover_5_2",
    "fallback_preserva_5_2",
]


events = []


for lineno, line in enumerate(
    midia_src.splitlines(),
    1,
):

    upper = line.upper()

    if any(
        marker.upper() in upper
        for marker in markers
    ):

        events.append(
            (
                lineno,
                line.strip(),
            )
        )


for line, content in events:

    emit(
        f"{line}: {content[:220]}"
    )


# ============================================================
# 11. RANKER / FINALIZER STACK DEPTH
# ============================================================

section(
    "11. MIDIA RANKER STACK"
)


rank_terms = {
    "VSE417": 0,
    "VSE42_RUNTIME": 0,
    "VSE42_BRIDGE": 0,
    "VG4X": 0,
    "DIVERSITY_RERANK": 0,
}


for line in midia_src.splitlines():

    if "VSE417" in line:
        rank_terms[
            "VSE417"
        ] += 1

    if (
        "visual_selection_runtime_v42"
        in line
    ):
        rank_terms[
            "VSE42_RUNTIME"
        ] += 1

    if (
        "visual_selection_bridge_v42"
        in line
    ):
        rank_terms[
            "VSE42_BRIDGE"
        ] += 1

    if "vg4x" in line.casefold():
        rank_terms[
            "VG4X"
        ] += 1

    if "rerank_pool" in line:
        rank_terms[
            "DIVERSITY_RERANK"
        ] += 1


for key, value in rank_terms.items():

    emit(
        f"{key}={value}"
    )


active_rank_systems = sum(
    1
    for value in rank_terms.values()
    if value > 0
)


if active_rank_systems >= 4:

    finding(
        "HIGH",
        "MULTIPLE_VISUAL_AUTHORITIES",
        f"{active_rank_systems} "
        "camadas de ranking/finalização "
        "coexistem em midia.py",
    )


# ============================================================
# 12. COMMIT PATH AUDIT
# ============================================================

section(
    "12. SCENE COMMIT PATHS"
)


commit_patterns = [
    "_vse42_commit_candidate",
    "_vse42_commit_safe",
    "_vse42_note_commit",
    "_vse42_commit_media",
    "SCENE_COMMIT",
    "FIRST_SUCCESS_LOCK",
]


for pattern in commit_patterns:

    hits = []

    for lineno, line in enumerate(
        midia_src.splitlines(),
        1,
    ):

        if pattern in line:

            hits.append(
                lineno
            )


    emit(
        f"{pattern} "
        f"COUNT={len(hits)} "
        f"LINES={hits}"
    )


commit_call_count = len(
    re.findall(
        r"_vse42_commit_candidate\s*\(",
        midia_src,
    )
)


if commit_call_count > 2:

    finding(
        "HIGH",
        "MULTIPLE_COMMIT_PATHS",
        f"_vse42_commit_candidate "
        f"possui {commit_call_count} "
        "pontos de chamada",
    )


# ============================================================
# 13. DOWNLOAD AFTER SUCCESS AUDIT
# ============================================================

section(
    "13. DOWNLOAD / SUCCESS CONTROL FLOW"
)


midia_tree, _, err = parse_python(
    midia_path
)


if midia_tree:

    target = None

    for node in midia_tree.body:

        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name
            ==
            "baixar_candidato_5_2"
        ):

            target = node


    if target:

        emit(
            "baixar_candidato_5_2="
            f"{target.lineno}-{target.end_lineno}"
        )

    else:

        finding(
            "HIGH",
            "DOWNLOAD_FUNCTION_MISSING",
            "baixar_candidato_5_2",
        )


# map every call to downloader
download_calls = []


if midia_tree:

    for node in ast.walk(
        midia_tree
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        fn = node.func

        if (
            isinstance(
                fn,
                ast.Name,
            )
            and
            fn.id
            ==
            "baixar_candidato_5_2"
        ):

            download_calls.append(
                node.lineno
            )


emit(
    "DOWNLOAD_CALLS="
    +
    str(
        download_calls
    )
)


if len(download_calls) >= 3:

    finding(
        "MEDIUM",
        "MULTIPLE_DOWNLOAD_PATHS",
        f"{len(download_calls)} "
        "pontos podem baixar mídia",
    )


# ============================================================
# 14. PROVIDER ACQUISITION
# ============================================================

section(
    "14. PROVIDER ACQUISITION"
)


providers = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_wikimedia_fotos",
]


for provider_name in providers:

    def_match = re.search(
        rf"^def\s+{re.escape(provider_name)}\s*\(",
        midia_src,
        re.MULTILINE,
    )

    call_count = len(
        re.findall(
            rf"\b{re.escape(provider_name)}\s*\(",
            midia_src,
        )
    )


    emit(
        f"{provider_name}: "
        f"DEFINED="
        f"{'YES' if def_match else 'NO'} "
        f"CALLS={call_count}"
    )


    if (
        provider_name
        !=
        "buscar_wikimedia_fotos"
        and
        (
            not def_match
            or call_count < 2
        )
    ):

        finding(
            "MEDIUM",
            "PROVIDER_PATH_WEAK",
            provider_name,
        )


# ============================================================
# 15. API KEY NAME AUDIT
# ============================================================

section(
    "15. PROVIDER CONFIG NAMES"
)


config_names = set()


for line in midia_src.splitlines():

    for match in re.findall(
        r"""(?:getenv|environ\.get)\(\s*["']([^"']+)["']""",
        line,
    ):

        upper = match.upper()

        if any(
            word in upper
            for word in (
                "PEXELS",
                "PIXABAY",
                "COVERR",
                "WIKI",
            )
        ):

            config_names.add(
                match
            )


for name in sorted(
    config_names
):

    # Never print values.
    emit(
        f"CONFIG_NAME={name}"
    )


# ============================================================
# 16. DANGEROUS FILE OPERATIONS
# ============================================================

section(
    "16. FILE DELETION / CLEANUP RISKS"
)


runtime_targets = [
    "midia.py",
    "video.py",
    "v6.py",
    "fresh_render_guard_v1.py",
    "render_transaction_v1.py",
]


danger_patterns = [
    "unlink(",
    "os.remove(",
    "remove(",
    "rmtree(",
    "shutil.rmtree(",
]


for name in runtime_targets:

    path = ROOT / name

    if not path.is_file():
        continue


    src = text(path)


    hits = []

    for lineno, line in enumerate(
        src.splitlines(),
        1,
    ):

        if any(
            pattern in line
            for pattern in danger_patterns
        ):

            hits.append(
                (
                    lineno,
                    line.strip(),
                )
            )


    emit(
        f"{name}: "
        f"DELETION_LINES={len(hits)}"
    )

    for lineno, line in hits[:50]:

        emit(
            f"  {lineno}: "
            f"{line[:180]}"
        )


# ============================================================
# 17. RENDER INPUT CONTRACT
# ============================================================

section(
    "17. RENDER INPUT CONTRACT"
)


render_checks = {
    "video.py": [
        "SHORT_ID",
        "imagens",
        "scene_map",
        "video_sem_audio",
    ],

    "v6.py": [
        "SHORT_ID",
        "video_sem_audio.mp4",
        ".mp3",
        ".ass",
        "short_v6_",
    ],

    "legenda_dinamica.py": [
        "SHORT_ID",
        ".mp3",
        ".ass",
        "whisper",
    ],
}


for name, expected_terms in (
    render_checks.items()
):

    src = text(
        ROOT / name
    )

    missing = [
        term
        for term in expected_terms
        if term.casefold()
        not in src.casefold()
    ]


    if missing:

        finding(
            "HIGH",
            "RENDER_CONTRACT_MISSING",
            f"{name}: {missing}",
        )

    else:

        emit(
            f"{name}: CONTRACT=PASS"
        )


# ============================================================
# 18. SHORT_ID RESOLUTION
# ============================================================

section(
    "18. SHORT_ID RESOLUTION"
)


for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
):

    src = text(
        ROOT / name
    )


    env_first = bool(
        re.search(
            r"""os\.(?:getenv|environ\.get)\(\s*["']SHORT_ID["']""",
            src,
        )
    )


    emit(
        f"{name}: "
        f"SHORT_ID_ENV="
        f"{'YES' if env_first else 'NO'}"
    )


    if not env_first:

        finding(
            "MEDIUM",
            "SHORT_ID_NOT_EXPLICIT",
            name,
        )


# ============================================================
# 19. VSE4 SELF TEST
# ============================================================

section(
    "19. VSE4 SELF TEST"
)


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


    emit(
        f"VSE4_SELF_TEST_STATUS="
        f"{result.returncode}"
    )


    lines = result.stdout.splitlines()


    for line in lines[-40:]:

        emit(
            line
        )


    if result.returncode != 0:

        finding(
            "HIGH",
            "VSE4_SELF_TEST_FAILURE",
            "visual_selection_engine_v4.py",
        )


# ============================================================
# 20. SELECTED MODULE IMPORT SMOKE
# ============================================================

section(
    "20. SAFE IMPORT SMOKE TEST"
)


safe_imports = [
    "visual_selection_engine_v4",
    "visual_selection_runtime_v42",
    "visual_selection_bridge_v42",
    "visual_must_rescue_v1",
]


for module in safe_imports:

    env = os.environ.copy()

    for flag in VISUAL_FLAGS:

        env[
            flag
        ] = "0"


    command = (
        "import "
        + module
        +
        "; print('IMPORT_OK')"
    )


    try:

        result = subprocess.run(
            [
                "python",
                "-c",
                command,
            ],
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=20,
        )


        emit(
            f"{module}: "
            f"STATUS={result.returncode}"
        )


        if result.returncode != 0:

            emit(
                result.stdout[-2000:]
            )

            finding(
                "HIGH",
                "IMPORT_FAILURE",
                module,
            )


    except subprocess.TimeoutExpired:

        finding(
            "HIGH",
            "IMPORT_TIMEOUT",
            module,
        )


# ============================================================
# 21. VISUAL RUNTIME CONTRADICTION
# ============================================================

section(
    "21. RUNTIME ENABLE/DISABLE CONTRADICTION"
)


midia_vse42_present = (
    "visual_selection_runtime_v42"
    in midia_src
)


launcher_disables_vse42 = any(
    flag_values.get(
        name
    )
    ==
    "0"
    for name in (
        "SAP_VSE_V42",
        "SAP_VSE42",
        "SAP_VSE4_RUNTIME",
    )
)


emit(
    "MIDIA_VSE42_PRESENT="
    +
    (
        "YES"
        if midia_vse42_present
        else
        "NO"
    )
)

emit(
    "LAUNCHER_VSE42_DISABLED="
    +
    (
        "YES"
        if launcher_disables_vse42
        else
        "NO"
    )
)


if (
    midia_vse42_present
    and
    launcher_disables_vse42
):

    finding(
        "HIGH",
        "RUNTIME_CONFIGURATION_CONTRADICTION",
        "VSE42 está integrado em midia.py "
        "mas launcher exporta flags = 0",
    )


# ============================================================
# 22. SAME-FILE SCORE AUTHORITY
# ============================================================

section(
    "22. SCORE AUTHORITY"
)


if vse_tree:

    score_defs = [
        node
        for node in vse_tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name
            ==
            "score_candidate"
        )
    ]


    emit(
        f"VSE4_SCORE_DEFS="
        f"{len(score_defs)}"
    )


    if score_defs:

        effective = score_defs[-1]

        emit(
            "VSE4_EFFECTIVE_SCORE="
            f"{effective.lineno}-"
            f"{effective.end_lineno}"
        )


        prior = [
            node.lineno
            for node in score_defs[:-1]
        ]


        emit(
            f"VSE4_SHADOWED_SCORE_LINES="
            f"{prior}"
        )


# ============================================================
# 23. POSSIBLE LEGACY MODULES
# ============================================================

section(
    "23. VISUAL MODULE INVENTORY"
)


visual_files = sorted(
    [
        p.name
        for p in ROOT.glob(
            "visual*.py"
        )
    ]
    +
    [
        p.name
        for p in ROOT.glob(
            "vg*.py"
        )
    ]
)


emit(
    f"VISUAL_MODULE_COUNT="
    f"{len(visual_files)}"
)


for name in visual_files:

    emit(
        f"VISUAL_MODULE={name}"
    )


if len(
    visual_files
) > 15:

    finding(
        "MEDIUM",
        "VISUAL_MODULE_SPRAWL",
        f"{len(visual_files)} "
        "módulos visuais no root",
    )


# ============================================================
# 24. BACKUP / ACTIVE SEPARATION
# ============================================================

section(
    "24. BACKUP SEPARATION"
)


backup_py = list(
    (
        ROOT / "backups"
    ).rglob(
        "*.py"
    )
) if (
    ROOT / "backups"
).exists() else []


emit(
    f"BACKUP_PY_FILES="
    f"{len(backup_py)}"
)


# ensure no import explicitly points into backups/temp
bad_import_strings = []


for path in python_files:

    src = text(path)

    if (
        "backups/"
        in src
        or
        "temp/"
        in src
        and
        "import"
        in src
    ):

        for lineno, line in enumerate(
            src.splitlines(),
            1,
        ):

            if (
                "import"
                in line
                and
                (
                    "backup"
                    in line.casefold()
                    or
                    "temp/"
                    in line
                )
            ):

                bad_import_strings.append(
                    (
                        path.name,
                        lineno,
                        line.strip(),
                    )
                )


for item in bad_import_strings:

    emit(
        "SUSPICIOUS_IMPORT="
        f"{item}"
    )


# ============================================================
# 25. FINAL FINDINGS
# ============================================================

section(
    "25. FINAL FINDINGS"
)


severity_order = [
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
]


for level in severity_order:

    emit(
        f"{level}_COUNT="
        f"{SEVERITY[level]}"
    )


emit()


if not findings:

    emit(
        "NO_FINDINGS=YES"
    )

else:

    for level, code, message in findings:

        emit(
            f"{level} | "
            f"{code} | "
            f"{message}"
        )


# ============================================================
# 26. DECISION
# ============================================================

section(
    "26. AUDIT DECISION"
)


if (
    SEVERITY[
        "CRITICAL"
    ]
    >
    0
):

    decision = (
        "BLOCKED_CRITICAL"
    )


elif (
    SEVERITY[
        "HIGH"
    ]
    >
    0
):

    decision = (
        "HOLD_FIX_HIGH_RISK"
    )


elif (
    SEVERITY[
        "MEDIUM"
    ]
    >
    0
):

    decision = (
        "PASS_WITH_WARNINGS"
    )


else:

    decision = (
        "PASS"
    )


emit(
    f"AUDIT_DECISION={decision}"
)


emit(
    f"REPORT={REPORT}"
)

emit(
    "PROJECT_MODIFIED=NO"
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
    "AUDIT_COMPLETE=YES"
)


print()
print(
    "REPORT:",
    REPORT,
)
