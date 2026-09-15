#!/usr/bin/env python3

from pathlib import Path
import ast
import hashlib
import subprocess
import os
import re
import json

ROOT = Path.home() / "ShortAutoPro"

CRITICAL_FILES = {
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "visual_scene_commit_lock_v1.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "fresh_render_guard_v1.py",
    "vi6_47_renderer_switch.py",
}

IMPORTANT_NAMES = {
    "evaluate",
    "resolve",
    "collect",
    "adapt_scene_command",
    "extract_candidates",
    "find_inventory_lists",
    "collect_paths",
    "collect_hashes",
}

PASS = []
WARN = []
FAIL = []


def section(name):
    print()
    print("=" * 78)
    print(name)
    print("=" * 78)


def result(name, ok, detail="", warning=False):

    if ok:
        PASS.append((name, detail))
        print(
            f"PASS | {name}"
            + (f" | {detail}" if detail else "")
        )
        return

    if warning:
        WARN.append((name, detail))
        print(
            f"WARN | {name}"
            + (f" | {detail}" if detail else "")
        )
    else:
        FAIL.append((name, detail))
        print(
            f"FAIL | {name}"
            + (f" | {detail}" if detail else "")
        )


def source(path):
    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def body_hash(node):

    dumped = ast.dump(
        node,
        annotate_fields=True,
        include_attributes=False,
    )

    return hashlib.sha256(
        dumped.encode("utf-8")
    ).hexdigest()


def signature(node):

    try:
        args = ast.unparse(
            node.args
        )
    except Exception:
        args = "?"

    return (
        f"{node.name}({args})"
    )


def snippet(lines, start, end, limit=14):

    data = lines[
        max(0, start - 1):
        min(len(lines), end)
    ]

    if len(data) > limit:
        data = (
            data[:limit]
            +
            ["    ... <truncated> ...\n"]
        )

    return "".join(data)


# ============================================================
# 1. PRIOR GENERAL AUDIT SUMMARY
# ============================================================

section("1. PREVIOUS GENERAL AUDIT SUMMARY")

previous = (
    ROOT
    / "temp"
    / "AUDIT_GERAL_SHORTAUTOPRO_V1.txt"
)

if previous.is_file():

    text = source(previous)

    patterns = (
        "PYTHON_FILES_CHECKED=",
        "ALL_TOPLEVEL_PYTHON_COMPILE=",
        "SHELL_FILES_CHECKED=",
        "ALL_TOPLEVEL_SHELL_SYNTAX=",
        "PASS_COUNT=",
        "WARN_COUNT=",
        "FAIL_COUNT=",
        "QUALITY_POINTS=",
        "GENERAL_AUDIT_STATUS=",
    )

    for line in text.splitlines():

        if line.startswith(patterns):
            print(line)

else:
    print(
        "PREVIOUS_AUDIT=NOT_FOUND"
    )


# ============================================================
# 2. DUPLICATE PYTHON DEFINITIONS
# ============================================================

section("2. DUPLICATE PYTHON DEFINITIONS")

duplicate_records = []

for path in sorted(
    ROOT.glob("*.py")
):

    try:
        src = source(path)
        tree = ast.parse(src)
    except Exception:
        continue

    defs = {}

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):

            defs.setdefault(
                node.name,
                [],
            ).append(node)

    for name, nodes in defs.items():

        if len(nodes) < 2:
            continue

        hashes = [
            body_hash(node)
            for node in nodes
        ]

        identical = (
            len(set(hashes))
            == 1
        )

        record = {
            "file": path.name,
            "name": name,
            "count": len(nodes),
            "lines": [
                node.lineno
                for node in nodes
            ],
            "end_lines": [
                getattr(
                    node,
                    "end_lineno",
                    node.lineno,
                )
                for node in nodes
            ],
            "hashes": hashes,
            "identical": identical,
        }

        duplicate_records.append(
            record
        )

        severity = (
            "LOW_IDENTICAL"
            if identical
            else "DIFFERENT_IMPLEMENTATIONS"
        )

        print(
            f"DUPLICATE "
            f"file={path.name} "
            f"name={name} "
            f"count={len(nodes)} "
            f"lines={record['lines']} "
            f"class={severity}"
        )


print(
    f"DUPLICATE_GROUPS={len(duplicate_records)}"
)

different = [
    r
    for r in duplicate_records
    if not r["identical"]
]

print(
    f"DUPLICATE_DIFFERENT={len(different)}"
)

result(
    "NO_DIFFERENT_DUPLICATE_DEFS",
    not different,
    (
        "none"
        if not different
        else f"{len(different)} groups"
    ),
    warning=bool(different),
)


# ============================================================
# 3. HIGH-RISK DUPLICATES
# ============================================================

section("3. HIGH-RISK DUPLICATES")

high_risk = []

for record in different:

    if (
        record["file"]
        in CRITICAL_FILES
        or
        record["name"]
        in IMPORTANT_NAMES
    ):

        high_risk.append(
            record
        )

        print(
            "HIGH_RISK_DUPLICATE "
            f"file={record['file']} "
            f"name={record['name']} "
            f"lines={record['lines']}"
        )


result(
    "NO_HIGH_RISK_DUPLICATES",
    not high_risk,
    (
        "none"
        if not high_risk
        else f"{len(high_risk)} high-risk groups"
    ),
    warning=bool(high_risk),
)


# ============================================================
# 4. ACTIVE OVERRIDE ANALYSIS
# ============================================================

section("4. ACTIVE OVERRIDE ANALYSIS")

for record in high_risk:

    path = ROOT / record["file"]

    src = source(path)
    tree = ast.parse(src)

    nodes = [
        node
        for node in tree.body
        if (
            isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            )
            and
            node.name == record["name"]
        )
    ]

    print()
    print(
        "-" * 70
    )

    print(
        f"FILE={record['file']}"
    )

    print(
        f"NAME={record['name']}"
    )

    print(
        f"DEFINITION_COUNT={len(nodes)}"
    )

    for index, node in enumerate(
        nodes,
        start=1,
    ):

        active = (
            index == len(nodes)
        )

        print()
        print(
            f"VERSION_{index}_LINE="
            f"{node.lineno}"
        )

        print(
            f"VERSION_{index}_ACTIVE="
            f"{'YES' if active else 'NO'}"
        )

        print(
            f"VERSION_{index}_HASH="
            f"{body_hash(node)}"
        )

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            print(
                f"VERSION_{index}_SIGNATURE="
                f"{signature(node)}"
            )

    print(
        "ACTIVE_IMPLEMENTATION_LINE="
        f"{nodes[-1].lineno}"
    )


# ============================================================
# 5. CALL-SITE ANALYSIS
# ============================================================

section("5. DUPLICATE FUNCTION CALL-SITES")

for record in high_risk:

    path = ROOT / record["file"]

    try:
        tree = ast.parse(
            source(path)
        )
    except Exception:
        continue

    direct_calls = []

    for node in ast.walk(tree):

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        fn = node.func

        if (
            isinstance(fn, ast.Name)
            and
            fn.id == record["name"]
        ):

            direct_calls.append(
                node.lineno
            )

    print(
        f"CALLS "
        f"{record['file']}::{record['name']} "
        f"count={len(direct_calls)} "
        f"lines={direct_calls[:40]}"
    )


# ============================================================
# 6. CROSS-PROJECT IMPORT/CALL SEARCH
# ============================================================

section("6. CROSS-PROJECT HIGH-RISK REFERENCES")

for record in high_risk:

    needle = record["name"]

    references = []

    for path in ROOT.glob("*.py"):

        try:
            src = source(path)
        except Exception:
            continue

        if needle not in src:
            continue

        for lineno, line in enumerate(
            src.splitlines(),
            start=1,
        ):

            if re.search(
                rf"\b{re.escape(needle)}\b",
                line,
            ):

                references.append(
                    (
                        path.name,
                        lineno,
                        line.strip()[:180],
                    )
                )

    print()
    print(
        f"REFERENCE_TARGET={record['file']}::{needle}"
    )

    print(
        f"REFERENCE_COUNT={len(references)}"
    )

    for item in references[:30]:

        print(
            f"REF {item[0]}:{item[1]} "
            f"{item[2]}"
        )


# ============================================================
# 7. SPECIFIC RENDER SWITCH FORENSICS
# ============================================================

section("7. RENDER SWITCH FORENSICS")

renderer = (
    ROOT
    / "vi6_47_renderer_switch.py"
)

if renderer.is_file():

    src = source(renderer)

    tree = ast.parse(src)

    matches = [
        node
        for node in tree.body
        if (
            isinstance(node, ast.FunctionDef)
            and
            node.name
            == "adapt_scene_command"
        )
    ]

    print(
        f"ADAPT_SCENE_COMMAND_DEFS={len(matches)}"
    )

    for idx, node in enumerate(
        matches,
        start=1,
    ):

        print(
            f"ADAPT_VERSION_{idx}_LINE="
            f"{node.lineno}"
        )

        print(
            f"ADAPT_VERSION_{idx}_END="
            f"{node.end_lineno}"
        )

        print(
            f"ADAPT_VERSION_{idx}_HASH="
            f"{body_hash(node)}"
        )

        print(
            f"ADAPT_VERSION_{idx}_ACTIVE="
            f"{'YES' if idx == len(matches) else 'NO'}"
        )

else:

    result(
        "RENDER_SWITCH_EXISTS",
        False,
        warning=True,
    )


# ============================================================
# 8. VSE4 CURRENT STATE
# ============================================================

section("8. VSE4 CURRENT STATE")

vse = (
    ROOT
    / "visual_selection_engine_v4.py"
)

if vse.is_file():

    vse_src = source(vse)

    required = (
        "score_candidate",
        "candidate_text",
        "tokens",
        "geo_hits",
        "concept_hits",
        "objget",
    )

    for name in required:

        present = bool(
            re.search(
                rf"^def\s+{name}\s*\(",
                vse_src,
                re.MULTILINE,
            )
        )

        result(
            f"VSE4_{name}",
            present,
        )

    proc = subprocess.run(
        [
            "python",
            str(vse),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "SAP_NO_PUBLISH": "1",
        },
    )

    print(
        f"VSE4_SELF_TEST_STATUS={proc.returncode}"
    )

    if proc.stdout.strip():

        print(
            "===== VSE4 STDOUT ====="
        )

        print(
            "\n".join(
                proc.stdout.splitlines()[-40:]
            )
        )

    if proc.stderr.strip():

        print(
            "===== VSE4 STDERR ====="
        )

        print(
            "\n".join(
                proc.stderr.splitlines()[-40:]
            )
        )

    result(
        "VSE4_SELF_TEST",
        proc.returncode == 0,
        (
            "status=0"
            if proc.returncode == 0
            else f"status={proc.returncode}"
        ),
        warning=proc.returncode != 0,
    )


# ============================================================
# 9. MIDIA -> VSE4 INTEGRATION
# ============================================================

section("9. MIDIA -> VSE4 INTEGRATION")

midia = ROOT / "midia.py"

if midia.is_file():

    msrc = source(midia)

    markers = (
        "visual_selection_engine_v4",
        "score_candidate",
        "VSE4",
        "vse4",
    )

    found = []

    for marker in markers:

        if marker in msrc:
            found.append(marker)

    print(
        "MIDIA_VSE4_MARKERS="
        +
        (
            ",".join(found)
            if found
            else "NONE"
        )
    )

    for lineno, line in enumerate(
        msrc.splitlines(),
        start=1,
    ):

        if any(
            marker in line
            for marker in markers
        ):

            print(
                f"MIDIA_VSE4_REF "
                f"line={lineno} "
                f"{line.strip()[:200]}"
            )

    result(
        "MIDIA_HAS_VSE4_INTEGRATION",
        bool(found),
        warning=not bool(found),
    )


# ============================================================
# 10. CORE HASH SNAPSHOT
# ============================================================

section("10. CORE HASH SNAPSHOT")

for name in (
    "visual_selection_engine_v4.py",
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "vi6_47_renderer_switch.py",
):

    path = ROOT / name

    if not path.is_file():
        continue

    digest = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

    print(
        f"SHA256 {name} {digest}"
    )


# ============================================================
# 11. DUPLICATE REPORT JSON
# ============================================================

section("11. MACHINE-READABLE REPORT")

report_path = (
    ROOT
    / "temp"
    / "SEMANTIC_AUDIT_V2_DUPLICATES.json"
)

report_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

report_path.write_text(
    json.dumps(
        {
            "duplicate_groups":
                duplicate_records,

            "different_groups":
                different,

            "high_risk_groups":
                high_risk,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(
    f"REPORT_JSON={report_path}"
)


# ============================================================
# 12. FINAL SUMMARY
# ============================================================

section("12. SEMANTIC AUDIT SUMMARY")

print(
    f"PASS_COUNT={len(PASS)}"
)

print(
    f"WARN_COUNT={len(WARN)}"
)

print(
    f"FAIL_COUNT={len(FAIL)}"
)

print(
    f"DUPLICATE_GROUPS={len(duplicate_records)}"
)

print(
    f"DIFFERENT_DUPLICATE_GROUPS={len(different)}"
)

print(
    f"HIGH_RISK_DUPLICATE_GROUPS={len(high_risk)}"
)


if FAIL:

    print()
    print("===== FAILURES =====")

    for name, detail in FAIL:

        print(
            f"FAIL | {name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )


if WARN:

    print()
    print("===== WARNINGS =====")

    for name, detail in WARN:

        print(
            f"WARN | {name}"
            +
            (
                f" | {detail}"
                if detail
                else ""
            )
        )


if FAIL:

    status = "FAIL"

elif WARN:

    status = "PASS_WITH_WARNINGS"

else:

    status = "PASS"


print()
print(
    f"SEMANTIC_AUDIT_STATUS={status}"
)

print(
    "PROJECT_FILES_MODIFIED=NO"
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
    "TERMUX_CONTINUA_ABERTO=SIM"
)
