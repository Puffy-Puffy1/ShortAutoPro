#!/usr/bin/env python3

from pathlib import Path
import ast
import re
import hashlib
from collections import defaultdict

ROOT = Path.home() / "ShortAutoPro"

OUT = (
    ROOT
    / "temp"
    / "VISUAL_ARCHITECTURE_AUDIT_V1.txt"
)

OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

lines_out = []


def emit(*parts):

    text = " ".join(
        str(x)
        for x in parts
    )

    print(text)

    lines_out.append(
        text
    )


def section(title):

    emit()
    emit("=" * 74)
    emit(title)
    emit("=" * 74)


def read(path):

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except Exception:
        return ""


def sha(path):

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


section(
    "0. SHORTAUTOPRO VISUAL ARCHITECTURE AUDIT V1"
)

emit(
    "ROOT=",
    ROOT,
)

emit(
    "MODE=STATIC_ONLY"
)

emit(
    "NETWORK_EXECUTED=NO"
)

emit(
    "MIDIA_EXECUTED=NO"
)

emit(
    "VIDEO_RENDERED=NO"
)


# ============================================================
# 1. CRITICAL FILES
# ============================================================

section(
    "1. CRITICAL FILE STATUS"
)

critical = [

    "midia.py",
    "gerar_short.sh",

    "visual_selection_engine_v4.py",
    "visual_selection_engine_v2.py",
    "visual_selection_final_gate_v3.py",

    "visual_pipeline_bridge_v42.py",
    "visual_selection_bridge_v42.py",
    "visual_selection_runtime_v42.py",
    "visual_runtime_v42.py",
    "visual_runtime_bridge_v4.py",

    "visual_quality_engine_v5.py",
    "visual_quality_runtime_v5.py",

    "visual_engine_unified.py",
    "sap_visual_consolidation_v5.py",

    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
    "visual_must_rescue_v1.py",
]


for name in critical:

    p = ROOT / name

    if p.is_file():

        emit(
            f"FILE={name}",
            f"BYTES={p.stat().st_size}",
            f"SHA256={sha(p)}",
        )

    else:

        emit(
            f"FILE={name}",
            "MISSING",
        )


# ============================================================
# 2. VSE4 DEFINITIONS
# ============================================================

section(
    "2. VSE4 TOP-LEVEL DEFINITION RESOLUTION"
)

vse4 = (
    ROOT
    / "visual_selection_engine_v4.py"
)

src = read(vse4)


try:

    tree = ast.parse(src)

except Exception as exc:

    emit(
        "VSE4_PARSE=FAIL",
        type(exc).__name__,
        exc,
    )

    tree = None


defs = defaultdict(list)


if tree:

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            defs[
                node.name
            ].append(
                (
                    node.lineno,
                    getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                )
            )


duplicates = {
    name: places
    for name, places
    in defs.items()
    if len(places) > 1
}


for name in sorted(
    duplicates
):

    places = duplicates[
        name
    ]

    emit(
        "DUPLICATE=",
        name,
        "DEFINITIONS=",
        ",".join(
            str(x[0])
            for x in places
        ),
        "ACTIVE_LAST_DEFINITION=",
        places[-1][0],
    )


if not duplicates:

    emit(
        "DUPLICATE_TOPLEVEL=NONE"
    )


if "score_candidate" in defs:

    emit()

    emit(
        "SCORE_CANDIDATE_COUNT=",
        len(
            defs[
                "score_candidate"
            ]
        ),
    )

    emit(
        "SCORE_CANDIDATE_ACTIVE_LINE=",
        defs[
            "score_candidate"
        ][-1][0],
    )


# ============================================================
# 3. SCORE_CANDIDATE SOURCE SUMMARIES
# ============================================================

section(
    "3. ALL SCORE_CANDIDATE VERSIONS"
)


if tree:

    source_lines = src.splitlines()

    versions = defs.get(
        "score_candidate",
        [],
    )


    for index, (
        start,
        end,
    ) in enumerate(
        versions,
        start=1,
    ):

        body = "\n".join(
            source_lines[
                start - 1:
                min(
                    end,
                    start + 44,
                )
            ]
        )

        emit()
        emit(
            f"VERSION={index}",
            f"START={start}",
            f"END={end}",
            (
                "ACTIVE=YES"
                if index == len(versions)
                else
                "ACTIVE=NO"
            ),
        )

        for line in body.splitlines():

            emit(
                "    " + line
            )


# ============================================================
# 4. WHO CALLS VSE4?
# ============================================================

section(
    "4. VSE4 REFERENCES ACROSS PROJECT"
)


patterns = (

    "visual_selection_engine_v4",
    "SAP_VSE4",
    "SAP_VSE_V4",
    "score_candidate",
)


project_files = list(
    ROOT.glob("*.py")
)


for p in sorted(
    project_files
):

    text = read(p)

    hits = []

    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        if any(
            pattern in line
            for pattern in patterns
        ):

            hits.append(
                (
                    number,
                    line.strip(),
                )
            )


    if hits:

        emit()
        emit(
            f"FILE={p.name}"
        )

        for number, line in hits[:80]:

            emit(
                f"  L{number}:",
                line[:220],
            )


# ============================================================
# 5. MIDIA VISUAL WIRING
# ============================================================

section(
    "5. MIDIA.PY ACTIVE VISUAL WIRING"
)


midia = read(
    ROOT / "midia.py"
)


visual_terms = (

    "visual_",
    "VSE",
    "SAP_VSE",
    "diversity",
    "commit",
    "rescue",
)


for number, line in enumerate(
    midia.splitlines(),
    start=1,
):

    if any(
        term.casefold()
        in
        line.casefold()
        for term in visual_terms
    ):

        emit(
            f"L{number}:",
            line.strip()[:250],
        )


# ============================================================
# 6. MIDIA IMPORT GRAPH
# ============================================================

section(
    "6. MIDIA.PY IMPORT GRAPH"
)


try:

    midia_tree = ast.parse(
        midia
    )

except Exception:

    midia_tree = None


if midia_tree:

    imports = []

    for node in ast.walk(
        midia_tree
    ):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                imports.append(
                    (
                        node.lineno,
                        alias.name,
                    )
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            mod = (
                node.module
                or ""
            )

            imports.append(
                (
                    node.lineno,
                    mod,
                )
            )


    for line_no, name in sorted(
        imports
    ):

        if any(
            x in name.casefold()
            for x in (
                "visual",
                "media",
                "vse",
            )
        ):

            emit(
                f"L{line_no}:",
                name,
            )


# ============================================================
# 7. VISUAL MODULE IMPORT DEPENDENCY GRAPH
# ============================================================

section(
    "7. VISUAL MODULE DEPENDENCY GRAPH"
)


visual_files = sorted(
    p
    for p in ROOT.glob("*.py")
    if (
        "visual" in p.name.casefold()
        or
        "media_diversity" in p.name.casefold()
    )
)


for p in visual_files:

    text = read(p)

    try:

        t = ast.parse(
            text
        )

    except Exception:

        continue


    deps = set()


    for node in ast.walk(t):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                if (
                    "visual"
                    in
                    alias.name.casefold()
                ):

                    deps.add(
                        alias.name
                    )


        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            mod = (
                node.module
                or ""
            )

            if (
                "visual"
                in
                mod.casefold()
            ):

                deps.add(mod)


    if deps:

        emit(
            f"{p.name} -> "
            +
            ", ".join(
                sorted(deps)
            )
        )


# ============================================================
# 8. FEATURE FLAG COLLISIONS
# ============================================================

section(
    "8. FEATURE FLAG COLLISION MAP"
)


flag_re = re.compile(
    r"""(?:getenv|environ\.get)\s*\(\s*["'](SAP_[A-Z0-9_]+)["']"""
)


flags = defaultdict(
    list
)


for p in project_files:

    text = read(p)

    for number, line in enumerate(
        text.splitlines(),
        start=1,
    ):

        for match in flag_re.finditer(
            line
        ):

            flags[
                match.group(1)
            ].append(
                (
                    p.name,
                    number,
                    line.strip(),
                )
            )


for flag in sorted(flags):

    if (
        "VSE"
        in flag
        or
        "VISUAL"
        in flag
        or
        "SCENE_COMMIT"
        in flag
    ):

        emit()
        emit(
            f"FLAG={flag}",
            f"REFERENCES={len(flags[flag])}",
        )

        for filename, number, line in flags[
            flag
        ][:25]:

            emit(
                f"  {filename}:{number}",
                line[:220],
            )


# ============================================================
# 9. ACTIVE DEFAULT VALUES
# ============================================================

section(
    "9. VISUAL FLAG DEFAULT VALUES"
)


default_re = re.compile(
    r"""os\.getenv\(\s*["'](SAP_[A-Z0-9_]+)["']\s*,\s*["']([^"']*)["']"""
)


for p in project_files:

    text = read(p)

    matches = list(
        default_re.finditer(
            text
        )
    )


    for m in matches:

        flag = m.group(1)

        if (
            "VSE"
            in flag
            or
            "VISUAL"
            in flag
            or
            "SCENE_COMMIT"
            in flag
        ):

            emit(
                f"{p.name}:",
                flag,
                "DEFAULT=",
                repr(
                    m.group(2)
                ),
            )


# ============================================================
# 10. MULTIPLE IMPLEMENTATION RESOLUTION
# ============================================================

section(
    "10. MULTIPLE VISUAL IMPLEMENTATION RESOLUTION"
)


interesting_functions = (

    "enabled",
    "install",
    "note_success",
    "reset_state",
    "score_candidate",
    "rank",
    "rerank",
    "select",
    "choose",
)


owners = defaultdict(
    list
)


for p in visual_files:

    try:

        t = ast.parse(
            read(p)
        )

    except Exception:

        continue


    for node in t.body:

        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name
            in
            interesting_functions
        ):

            owners[
                node.name
            ].append(
                (
                    p.name,
                    node.lineno,
                )
            )


for name in sorted(
    owners
):

    if len(
        owners[name]
    ) > 1:

        emit(
            f"FUNCTION={name}"
        )

        for filename, line_no in owners[
            name
        ]:

            emit(
                f"  {filename}:{line_no}"
            )


# ============================================================
# 11. EXCEPT PASS IN ACTIVE VISUAL STACK
# ============================================================

section(
    "11. ACTIVE VISUAL SILENT-EXCEPTION CONTEXT"
)


active_candidates = {

    "midia.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v4.py",
    "visual_pipeline_bridge_v42.py",
    "visual_selection_bridge_v42.py",
    "visual_runtime_v42.py",
    "visual_quality_engine_v5.py",
    "visual_quality_runtime_v5.py",
    "visual_scene_commit_lock_v1.py",
}


for name in sorted(
    active_candidates
):

    p = ROOT / name

    if not p.is_file():
        continue


    text = read(p)
    text_lines = text.splitlines()


    try:

        t = ast.parse(
            text
        )

    except Exception:

        continue


    findings = []


    for node in ast.walk(t):

        if not isinstance(
            node,
            ast.ExceptHandler,
        ):
            continue


        if (
            len(node.body) == 1
            and
            isinstance(
                node.body[0],
                ast.Pass,
            )
        ):

            findings.append(
                node.lineno
            )


    if findings:

        emit()
        emit(
            f"FILE={name}",
            f"SILENT_EXCEPTIONS={len(findings)}",
        )


        for line_no in findings:

            start = max(
                0,
                line_no - 3,
            )

            end = min(
                len(text_lines),
                line_no + 3,
            )

            emit(
                f"  --- around L{line_no} ---"
            )

            for idx in range(
                start,
                end,
            ):

                emit(
                    f"  {idx + 1:05d}:",
                    text_lines[idx][
                        :220
                    ],
                )


# ============================================================
# 12. DESTRUCTIVE OPS IN ACTIVE PATH
# ============================================================

section(
    "12. DESTRUCTIVE OPERATIONS IN ACTIVE VISUAL FILES"
)


destructive_terms = (

    ".unlink(",
    "os.remove(",
    "os.unlink(",
    "shutil.rmtree(",
)


for name in sorted(
    active_candidates
):

    p = ROOT / name

    if not p.is_file():
        continue


    for number, line in enumerate(
        read(p).splitlines(),
        start=1,
    ):

        if any(
            x in line
            for x in destructive_terms
        ):

            emit(
                f"{name}:{number}:",
                line.strip()[:240],
            )


# ============================================================
# 13. buscar_todos_candidatos ACTIVE BODY
# ============================================================

section(
    "13. ACTIVE buscar_todos_candidatos"
)


if midia_tree:

    functions = [
        node
        for node in midia_tree.body
        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name
            ==
            "buscar_todos_candidatos"
        )
    ]


    emit(
        "DEFINITION_COUNT=",
        len(functions),
    )


    if functions:

        active = functions[-1]

        emit(
            "ACTIVE_START=",
            active.lineno,
        )

        emit(
            "ACTIVE_END=",
            active.end_lineno,
        )


        source_lines = midia.splitlines()


        for number in range(
            active.lineno,
            active.end_lineno + 1,
        ):

            emit(
                f"{number:05d}:",
                source_lines[
                    number - 1
                ][:240],
            )


# ============================================================
# 14. PROVIDER FUNCTION DUPLICATES
# ============================================================

section(
    "14. PROVIDER FUNCTION RESOLUTION"
)


provider_names = (

    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
    "baixar_candidato_5_2",
    "ordenar_failover_5_2",
)


if midia_tree:

    midia_defs = defaultdict(
        list
    )


    for node in midia_tree.body:

        if isinstance(
            node,
            ast.FunctionDef,
        ):

            midia_defs[
                node.name
            ].append(
                node.lineno
            )


    for name in provider_names:

        places = midia_defs.get(
            name,
            [],
        )

        emit(
            f"{name}:",
            (
                ",".join(
                    map(
                        str,
                        places,
                    )
                )
                or
                "NOT_FOUND"
            ),
        )

        if len(places) > 1:

            emit(
                "  WARNING=DUPLICATE_PROVIDER_FUNCTION",
                "ACTIVE_LAST=",
                places[-1],
            )


# ============================================================
# 15. CRITICAL CLASSIFICATION
# ============================================================

section(
    "15. AUTOMATIC RISK CLASSIFICATION"
)


risks = []


score_count = len(
    defs.get(
        "score_candidate",
        [],
    )
)


if score_count > 1:

    risks.append(
        (
            "CRITICAL",
            (
                "visual_selection_engine_v4.py possui "
                f"{score_count} definições de score_candidate; "
                "somente a última normalmente fica ativa."
            ),
        )
    )


vse_flags = {
    flag
    for flag in flags
    if (
        "VSE"
        in flag
    )
}


if len(vse_flags) >= 3:

    risks.append(
        (
            "HIGH",
            (
                "Existem múltiplas famílias de feature flags VSE: "
                +
                ", ".join(
                    sorted(
                        vse_flags
                    )
                )
            ),
        )
    )


if len(
    owners.get(
        "install",
        [],
    )
) > 1:

    risks.append(
        (
            "HIGH",
            (
                "Mais de um módulo visual exporta install(); "
                "é necessário provar qual hook está ativo."
            ),
        )
    )


if len(
    owners.get(
        "note_success",
        [],
    )
) > 1:

    risks.append(
        (
            "MEDIUM",
            (
                "Múltiplos módulos mantêm estado de sucesso visual; "
                "risco de estados independentes."
            ),
        )
    )


if not risks:

    emit(
        "RISK=NONE_DETECTED"
    )

else:

    for severity, description in risks:

        emit(
            f"RISK={severity}:",
            description,
        )


# ============================================================
# 16. SUMMARY
# ============================================================

section(
    "16. SUMMARY"
)


emit(
    "VSE4_SCORE_CANDIDATE_DEFINITIONS=",
    score_count,
)

if score_count:

    emit(
        "VSE4_ACTIVE_SCORE_CANDIDATE_LINE=",
        defs[
            "score_candidate"
        ][-1][0],
    )


emit(
    "VISUAL_FLAG_FAMILIES=",
    ",".join(
        sorted(
            vse_flags
        )
    )
    or
    "NONE",
)

emit(
    "DUPLICATE_VSE4_TOPLEVEL_NAMES=",
    len(duplicates),
)

emit(
    "AUDIT_COMPLETE=YES"
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


OUT.write_text(
    "\n".join(
        lines_out
    )
    +
    "\n",
    encoding="utf-8",
)

print()
print(
    "REPORT=",
    OUT,
)
