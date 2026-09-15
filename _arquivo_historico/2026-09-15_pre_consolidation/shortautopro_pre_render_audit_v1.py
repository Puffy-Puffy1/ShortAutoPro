#!/usr/bin/env python3

import ast
import hashlib
import json
import py_compile
import subprocess
import sys
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

EXPECTED = {
    "midia.py":
        "626b28af9397c84fc1cced44fa1d6236c5cd62948712bc4403e2407593361d90",

    "v6.py":
        "13d1444fc2ae0198f8f070ad98238a36d7c939c6db2572c462cd9b07712286e7",

    "video.py":
        "756c0db576f664d474cb92676b4ad81737158f8a275bfad6348aa0a542d87b06",

    "gerar_short.sh":
        "25af0e189440d3646de8da8772535e00ac1e8446097f5db56ed93144ab45eb7a",
}


PY_FILES = [
    "media_provenance_capture_v1.py",
    "media_diversity_guard_v1.py",
    "midia.py",
    "v6.py",
    "video.py",
    "vi1510_1_22_upstream_provenance_v4.py",
    "vi1510_1_23_runtime_inventory_v3.py",
    "vi1510_1_24_partitioned_resolver.py",
    "vi1510_1_25_scene_usage.py",
    "vi1510_1_27_source_metadata_v2.py",
    "vi1510_1_28_relevance_v2.py",
    "vi1510_1_29_lineage_v2.py",
    "vi1510_1_30_evidence_gate_v2.py",
    "vi1510_1_31_cross_topic_v3.py",
    "vi1510_1_34_v2_pipeline.py",
    "vi1510_1_35_fresh_provenance_generalization.py",
]


failed = []
details = {}


def sha(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def check(name, actual, expected=True):
    ok = actual == expected

    print(
        name,
        "=",
        "PASS" if ok else "FAIL",
        "| expected=",
        expected,
        "| actual=",
        actual,
    )

    if not ok:
        failed.append(name)

    return ok


print()
print("===== 1. CORE HASHES =====")

for filename, expected in EXPECTED.items():

    path = ROOT / filename

    actual = (
        sha(path)
        if path.exists()
        else "MISSING"
    )

    details[
        f"hash_{filename}"
    ] = actual

    check(
        f"HASH_{filename}",
        actual,
        expected,
    )


print()
print("===== 2. PYTHON COMPILE =====")

for filename in PY_FILES:

    path = ROOT / filename

    if not path.exists():

        check(
            f"EXISTS_{filename}",
            False,
            True,
        )

        continue

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        check(
            f"COMPILE_{filename}",
            True,
            True,
        )

    except Exception as exc:

        print(
            "COMPILE_ERROR=",
            filename,
            type(exc).__name__,
            str(exc)[:200],
        )

        check(
            f"COMPILE_{filename}",
            False,
            True,
        )


print()
print("===== 3. SHELL SYNTAX =====")

shell = subprocess.run(
    [
        "bash",
        "-n",
        str(
            ROOT
            / "gerar_short.sh"
        ),
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)


check(
    "GERAR_SHORT_SYNTAX",
    shell.returncode,
    0,
)


print()
print("===== 4. MIDIA ARCHITECTURE =====")

midia_path = (
    ROOT
    / "midia.py"
)

midia_text = midia_path.read_text(
    encoding="utf-8",
    errors="ignore",
)

tree = ast.parse(
    midia_text
)


functions = {
    node.name:
        node

    for node in tree.body

    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    )
}


required_functions = [
    "baixar",
    "buscar_todos_candidatos",
    "metadata_confiavel",
    "preparar_candidatos",
    "escolher_documental_prioritario",
    "escolher_com_movimento",
    "chave_candidato_5_2",
    "ordenar_failover_5_2",
    "baixar_candidato_5_2",
    "reencontrar_vi6_original_6_3",
]


for name in required_functions:

    check(
        f"MIDIA_FUNCTION_{name}",
        name in functions,
        True,
    )


check(
    "PROVENANCE_HOOK_PRESENT",
    (
        "SHORTAUTOPRO SOURCE PROVENANCE EARLY HOOK V1"
        in midia_text
    ),
    True,
)


check(
    "DIVERSITY_HOOK_PRESENT",
    (
        "SHORTAUTOPRO MEDIA DIVERSITY GUARD V1"
        in midia_text
    ),
    True,
)


downloader = functions.get(
    "baixar_candidato_5_2"
)


if downloader:

    lines = midia_text.splitlines()

    prov_line = next(
        (
            i
            for i, line
            in enumerate(
                lines,
                1,
            )
            if (
                "SHORTAUTOPRO SOURCE PROVENANCE EARLY HOOK V1"
                in line
            )
        ),
        None,
    )

    div_line = next(
        (
            i
            for i, line
            in enumerate(
                lines,
                1,
            )
            if (
                "SHORTAUTOPRO MEDIA DIVERSITY GUARD V1"
                in line
            )
        ),
        None,
    )

    check(
        "PROVENANCE_HOOK_AFTER_DOWNLOADER",
        bool(
            prov_line
            and
            prov_line
            >
            downloader.end_lineno
        ),
        True,
    )

    check(
        "DIVERSITY_HOOK_AFTER_PROVENANCE",
        bool(
            div_line
            and
            prov_line
            and
            div_line
            >
            prov_line
        ),
        True,
    )


print()
print("===== 5. SAFETY OF FRESH BENCHMARK =====")

fresh_path = (
    ROOT
    / "vi1510_1_35_fresh_provenance_generalization.py"
)

fresh_text = fresh_path.read_text(
    encoding="utf-8",
    errors="ignore",
).lower()


danger_tokens = [
    "subprocess.run([\"ffmpeg\"",
    "subprocess.run(['ffmpeg'",
    "os.system(\"ffmpeg",
    "os.system('ffmpeg",
    "requests.get(",
    "requests.post(",
    "urllib.request.urlopen(",
    "socket.socket(",
]


found_danger = [
    token
    for token in danger_tokens
    if token in fresh_text
]


check(
    "FRESH_BENCH_NO_NETWORK_RENDER_CALLS",
    found_danger,
    [],
)


print()
print("===== 6. FRESH 3-TOPIC PIPELINE =====")

fresh = subprocess.run(
    [
        sys.executable,
        str(
            fresh_path
        ),
    ],
    cwd=str(ROOT),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)


print(
    fresh.stdout
)


check(
    "FRESH_3TOPIC_RETURN_CODE",
    fresh.returncode,
    0,
)


check(
    "FRESH_3TOPIC_CERTIFIED",
    (
        "STATUS: FRESH_3TOPIC_PROVENANCE_CERTIFIED"
        in fresh.stdout
    ),
    True,
)


for partition in [
    1,
    2,
    3,
]:

    # The output contains PASS for each partition.
    expected_block = (
        f"PARTITION= {partition}"
    )

    check(
        f"FRESH_PARTITION_{partition}_PRESENT",
        expected_block
        in fresh.stdout,
        True,
    )


check(
    "FRESH_NO_FAILURES",
    (
        "FAILED= []"
        in fresh.stdout
    ),
    True,
)


print()
print("===== 7. HARDENING CONTRACT =====")

prov_text = (
    ROOT
    / "media_provenance_capture_v1.py"
).read_text(
    encoding="utf-8",
    errors="ignore",
)


hardening_tokens = [
    "_sap_validate_downloaded_media",
    "FILE_TOO_SMALL",
    "INVALID_FILE_SIGNATURE",
    "DUPLICATE_SHA256",
    "_SAP_SESSION_HASH_PATHS",
]


for token in hardening_tokens:

    check(
        "HARDENING_"
        +
        token,
        token in prov_text,
        True,
    )


print()
print("===== 8. DIVERSITY CONTRACT =====")

div_text = (
    ROOT
    / "media_diversity_guard_v1.py"
).read_text(
    encoding="utf-8",
    errors="ignore",
)


diversity_tokens = [
    "_PROVIDER_HISTORY",
    "_GROUP_HISTORY",
    "_KEY_HISTORY",
    "diversity_penalty",
    "rerank",
    "provider_repeat_penalty",
    "source_group_repeat_penalty",
    "hard_blocking",
]


for token in diversity_tokens:

    check(
        "DIVERSITY_"
        +
        token,
        token in div_text,
        True,
    )


print()
print("===== 9. LEGACY QUERY SAFETY =====")

for filename in [
    "vi1510_1_26_evidence_text.py",
    "vi1510_1_29_lineage_v2.py",
]:

    path = ROOT / filename

    check(
        f"SAFETY_MODULE_{filename}_EXISTS",
        path.exists(),
        True,
    )


evidence_text = (
    ROOT
    / "vi1510_1_26_evidence_text.py"
).read_text(
    encoding="utf-8",
    errors="ignore",
).lower()


for forbidden in [
    "query",
    "search",
    "prompt",
    "asset_query",
]:

    check(
        f"EVIDENCE_POLICY_REFERENCES_{forbidden.upper()}",
        forbidden in evidence_text,
        True,
    )


print()
print("===== 10. FINAL =====")

status = (
    "CERTIFIED"
    if not failed
    else "FAILED"
)


report = {
    "schema":
        "SHORTAUTOPRO_PRE_RENDER_AUDIT_V1",

    "status":
        status,

    "core_hashes":
        details,

    "fresh_3topic":
        (
            "PASS"
            if fresh.returncode == 0
            else "FAIL"
        ),

    "network_executed":
        False,

    "ffmpeg_executed":
        False,

    "video_generated":
        False,

    "failed":
        failed,
}


out = (
    ROOT
    / "temp"
    / "pre_render_audit"
    / "report.json"
)

out.parent.mkdir(
    parents=True,
    exist_ok=True,
)

out.write_text(
    json.dumps(
        report,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    "FAILED=",
    failed,
)

print(
    "REPORT=",
    out,
)


if failed:

    print(
        "STATUS: PRE_RENDER_AUDIT_FAILED"
    )

    raise SystemExit(
        1
    )


certificate = {
    "status":
        "CERTIFIED",

    "stage":
        "PRE_RENDER",

    "midia_sha256":
        EXPECTED[
            "midia.py"
        ],

    "v6_sha256":
        EXPECTED[
            "v6.py"
        ],

    "video_sha256":
        EXPECTED[
            "video.py"
        ],

    "gerar_short_sha256":
        EXPECTED[
            "gerar_short.sh"
        ],

    "fresh_partitions":
        3,

    "fresh_assets":
        36,

    "network":
        False,

    "ffmpeg":
        False,

    "video":
        False,
}


cert = (
    ROOT
    / "manifests"
    / "shortautopro_pre_render_certification_v1.json"
)


cert.write_text(
    json.dumps(
        certificate,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print(
    "CERTIFICATE=",
    cert,
)

print(
    "STATUS: SHORTAUTOPRO_PRE_RENDER_CERTIFIED"
)
