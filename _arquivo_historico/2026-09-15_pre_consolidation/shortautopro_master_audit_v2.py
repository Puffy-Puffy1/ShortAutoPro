#!/usr/bin/env python3

from pathlib import Path
from collections import Counter

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time


ROOT = Path.home() / "ShortAutoPro"

SID = os.environ.get(
    "SHORT_ID",
    "2026-09-02_2358",
).strip()

REPORT_TXT = (
    ROOT
    / "temp"
    / f"MASTER_AUDIT_V2_{SID}.txt"
)

REPORT_JSON = (
    ROOT
    / "temp"
    / f"MASTER_AUDIT_V2_{SID}.json"
)


lines = []
results = []


def out(value=""):

    value = str(value)

    print(value)

    lines.append(value)


def section(title):

    out()
    out("=" * 70)
    out(title)
    out("=" * 70)


def result(status, test, detail=""):

    item = {
        "status": status,
        "test": test,
        "detail": str(detail),
    }

    results.append(item)

    message = (
        f"{status}: {test}"
    )

    if detail:
        message += (
            f" | {detail}"
        )

    out(message)


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda:
                f.read(1024 * 1024),
            b"",
        ):

            h.update(chunk)

    return h.hexdigest()


def run(args, timeout=90):

    try:

        p = subprocess.run(
            args,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
        )

        return (
            p.returncode,
            (p.stdout or "")
            +
            (p.stderr or ""),
        )

    except Exception as exc:

        return (
            99,
            f"{type(exc).__name__}: {exc}",
        )


if not ROOT.is_dir():

    print(
        f"PROJETO_NAO_ENCONTRADO={ROOT}"
    )

    raise SystemExit(2)


os.chdir(ROOT)

REPORT_TXT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


out(
    "SHORTAUTOPRO MASTER GENERAL AUDIT V2"
)

out(
    "DATE="
    +
    time.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)

out(
    f"ROOT={ROOT}"
)

out(
    f"SHORT_ID={SID}"
)

out(
    "MODE=READ_ONLY_EXCEPT_REPORTS"
)


# ============================================================
# 1. PROJECT STRUCTURE
# ============================================================

section(
    "1. PROJECT STRUCTURE"
)

required_files = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "fresh_render_guard_v1.py",
]


for name in required_files:

    path = ROOT / name

    result(
        "PASS" if path.is_file() else "FAIL",
        f"FILE_{name}",
        "present"
        if path.is_file()
        else "missing",
    )


for name in [
    "imagens",
    "audios",
    "videos",
    "roteiros",
    "temp",
    "logs",
]:

    path = ROOT / name

    result(
        "PASS"
        if path.is_dir()
        else "WARN",
        f"DIR_{name}",
        "present"
        if path.is_dir()
        else "missing",
    )


# ============================================================
# 2. PYTHON SYNTAX
# ============================================================

section(
    "2. PYTHON TOP-LEVEL SYNTAX"
)

python_files = sorted(
    ROOT.glob("*.py")
)

syntax_failures = []


for path in python_files:

    try:

        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        compile(
            source,
            str(path),
            "exec",
        )

    except Exception as exc:

        syntax_failures.append(
            (
                path.name,
                f"{type(exc).__name__}: {exc}",
            )
        )


if syntax_failures:

    for name, detail in syntax_failures:

        result(
            "FAIL",
            f"PY_SYNTAX_{name}",
            detail,
        )

else:

    result(
        "PASS",
        "PYTHON_TOPLEVEL_SYNTAX",
        f"files={len(python_files)}",
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL TOP-LEVEL SYNTAX"
)


for path in sorted(
    ROOT.glob("*.sh")
):

    rc, text = run(
        [
            "bash",
            "-n",
            str(path),
        ],
        20,
    )

    result(
        "PASS"
        if rc == 0
        else "FAIL",
        f"SH_SYNTAX_{path.name}",
        "ok"
        if rc == 0
        else text.strip()[-500:],
    )


# ============================================================
# 4. DUPLICATE DEFINITIONS
# ============================================================

section(
    "4. DUPLICATE TOP-LEVEL DEFINITIONS"
)


for name in [
    "midia.py",
    "video.py",
    "v6.py",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
]:

    path = ROOT / name

    if not path.is_file():
        continue

    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

        names = Counter(
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
        )

        duplicates = {
            key: value
            for key, value in names.items()
            if value > 1
        }

        result(
            "WARN"
            if duplicates
            else "PASS",
            f"DUPLICATE_DEFS_{name}",
            duplicates
            if duplicates
            else "none",
        )

    except Exception as exc:

        result(
            "FAIL",
            f"AST_PARSE_{name}",
            exc,
        )


# ============================================================
# 5. HASHES
# ============================================================

section(
    "5. CORE HASHES"
)


for name in [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
]:

    path = ROOT / name

    if not path.is_file():
        continue

    digest = sha256(path)

    out(
        f"SHA256 {name} {digest}"
    )

    result(
        "INFO",
        f"HASH_{name}",
        digest,
    )


# ============================================================
# 6. VSE4 STRUCTURE
# ============================================================

section(
    "6. VSE4 STRUCTURE"
)

vse = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if vse.is_file():

    vse_source = vse.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(
        vse_source
    )

    definitions = {
        node.name
        for node in tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }

    assignments = {
        target.id
        for node in tree.body
        if isinstance(
            node,
            ast.Assign,
        )
        for target in node.targets
        if isinstance(
            target,
            ast.Name,
        )
    }


    required_functions = {
        "candidate_text",
        "tokens",
        "score_candidate",
        "geo_hits",
        "concept_hits",
        "objget",
        "provider",
        "media_type",
        "must_tier",
        "base_score",
    }


    required_globals = {
        "CONCEPTS",
        "GEO_GROUPS",
        "GENERIC_LIFESTYLE",
        "MEDICINE_TERMS",
        "STOP",
        "ROOT",
    }


    missing_functions = sorted(
        required_functions
        -
        definitions
    )

    missing_globals = sorted(
        required_globals
        -
        assignments
    )


    result(
        "PASS"
        if not missing_functions
        else "FAIL",
        "VSE4_REQUIRED_FUNCTIONS",
        missing_functions
        if missing_functions
        else "all present",
    )


    result(
        "PASS"
        if not missing_globals
        else "FAIL",
        "VSE4_REQUIRED_GLOBALS",
        missing_globals
        if missing_globals
        else "all present",
    )


else:

    result(
        "FAIL",
        "VSE4_STRUCTURE",
        "file missing",
    )


# ============================================================
# 7. VSE4 SELF TEST
# ============================================================

section(
    "7. VSE4 SELF TEST"
)


if vse.is_file():

    rc, text = run(
        [
            sys.executable,
            str(vse),
        ],
        90,
    )

    tail = "\n".join(
        text.strip().splitlines()[-20:]
    )

    result(
        "PASS"
        if rc == 0
        else "FAIL",
        "VSE4_SELF_TEST",
        f"rc={rc}\n{tail}",
    )


# ============================================================
# 8. DIRECT GEO CONTRADICTION
# ============================================================

section(
    "8. VSE4 DIRECT GEO/HARD-MISMATCH TEST"
)


direct_code = r'''
import json
import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="audit_vse4",
)

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

state = {
    "providers": [
        "pixabay",
        "pixabay",
    ],
    "groups": [],
    "types": [],
    "keys": [],
}

a = ns["score_candidate"](
    wrong,
    scene,
    state,
)

b = ns["score_candidate"](
    correct,
    scene,
    state,
)

payload = {
    "scene_geo":
        sorted(
            ns["geo_hits"](
                scene
            )
        ),

    "wrong_geo":
        sorted(
            ns["geo_hits"](
                ns["candidate_text"](
                    wrong
                )
            )
        ),

    "correct_geo":
        sorted(
            ns["geo_hits"](
                ns["candidate_text"](
                    correct
                )
            )
        ),

    "wrong_hard":
        a.get(
            "hard_mismatch"
        ),

    "correct_hard":
        b.get(
            "hard_mismatch"
        ),

    "wrong_effective":
        a.get(
            "effective"
        ),

    "correct_effective":
        b.get(
            "effective"
        ),
}

print(
    json.dumps(
        payload,
        ensure_ascii=False,
    )
)
'''


rc, text = run(
    [
        sys.executable,
        "-c",
        direct_code,
    ],
    60,
)


if rc == 0:

    try:

        data = json.loads(
            text.strip().splitlines()[-1]
        )

        out(
            "VSE4_DIRECT="
            +
            json.dumps(
                data,
                ensure_ascii=False,
            )
        )

        effective_ok = (
            (
                data.get(
                    "correct_effective"
                )
                or -1
            )
            >
            (
                data.get(
                    "wrong_effective"
                )
                or -1
            )
        )


        passed = (
            data.get(
                "wrong_hard"
            )
            is True
            and
            data.get(
                "correct_hard"
            )
            is False
            and
            effective_ok
        )


        result(
            "PASS"
            if passed
            else "FAIL",
            "VSE4_GEO_HARD_MISMATCH",
            data,
        )


    except Exception as exc:

        result(
            "FAIL",
            "VSE4_DIRECT_PARSE",
            (
                f"{exc} | "
                f"{text[-1000:]}"
            ),
        )


else:

    result(
        "FAIL",
        "VSE4_DIRECT_RUNTIME",
        text[-1500:],
    )


# ============================================================
# 9. PROVIDER ACQUISITION
# ============================================================

section(
    "9. PROVIDER ACQUISITION STATIC MAP"
)

midia = ROOT / "midia.py"


provider_functions = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
]


if midia.is_file():

    tree = ast.parse(
        midia.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )

    function_map = {
        node.name: node
        for node in tree.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
    }


    for name in provider_functions:

        result(
            "PASS"
            if name in function_map
            else "FAIL",
            f"PROVIDER_DEF_{name}",
            "present"
            if name in function_map
            else "missing",
        )


    function = function_map.get(
        "buscar_todos_candidatos"
    )


    if function:

        calls = []

        for node in ast.walk(
            function
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

                calls.append(
                    node.func.id
                )


            elif isinstance(
                node.func,
                ast.Attribute,
            ):

                calls.append(
                    node.func.attr
                )


        for name in [
            "pexels_video",
            "pexels_foto",
            "pixabay_video",
            "pixabay_foto",
            "coverr_video",
        ]:

            result(
                "PASS"
                if name in calls
                else "FAIL",
                f"PROVIDER_CALL_{name}",
                "called"
                if name in calls
                else "not called",
            )


# ============================================================
# 10. ACTIVE VISUAL PATH
# ============================================================

section(
    "10. ACTIVE VISUAL ENGINE PATH"
)

active_text = ""


for name in [
    "midia.py",
    "media_diversity_guard_v1.py",
]:

    path = ROOT / name

    if path.is_file():

        active_text += (
            "\n"
            +
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )


result(
    "PASS"
    if "visual_selection_engine_v4"
    in active_text
    else "WARN",
    "VSE4_ACTIVE_PATH",
    "referenced"
    if "visual_selection_engine_v4"
    in active_text
    else "not referenced in active media path",
)


result(
    "PASS"
    if "visual_selection_final_gate_v3"
    in active_text
    else "INFO",
    "VSE3_ACTIVE_PATH",
    "referenced"
    if "visual_selection_final_gate_v3"
    in active_text
    else "not referenced",
)


# ============================================================
# 11. MEDIA INTEGRITY
# ============================================================

section(
    "11. CURRENT 12-SCENE MEDIA INTEGRITY"
)

media_dir = (
    ROOT
    / "imagens"
    / f"short_{SID}"
)


media_items = []


if not media_dir.is_dir():

    result(
        "WARN",
        "MEDIA_DIR",
        f"missing {media_dir}",
    )


else:

    bad = []


    for number in range(
        1,
        13,
    ):

        files = sorted(
            media_dir.glob(
                f"scene_{number:02d}.*"
            )
        )


        if len(files) != 1:

            bad.append(
                (
                    number,
                    len(files),
                    [
                        item.name
                        for item in files
                    ],
                )
            )


        for path in files:

            media_items.append(
                (
                    path.name,
                    path.stat().st_size,
                    sha256(path),
                )
            )


    result(
        "PASS"
        if not bad
        else "FAIL",
        "SCENE_FILE_CARDINALITY",
        "12 scenes, exactly one file each"
        if not bad
        else bad,
    )


    payload = "\n".join(
        f"{name}|{size}|{digest}"
        for name, size, digest
        in sorted(media_items)
    )


    fingerprint = hashlib.sha256(
        payload.encode()
    ).hexdigest()


    out(
        f"MEDIA_FINGERPRINT={fingerprint}"
    )


    result(
        "INFO",
        "MEDIA_FINGERPRINT",
        fingerprint,
    )


# ============================================================
# 12. RENDER STATE
# ============================================================

section(
    "12. RENDER INPUT/OUTPUT STATE"
)


render_files = {

    "AUDIO":
        ROOT
        / "audios"
        / f"short_{SID}.mp3",

    "ASS":
        ROOT
        / "videos"
        / f"short_{SID}.ass",

    "VIDEO_BASE":
        ROOT
        / "temp"
        / SID
        / "video_sem_audio.mp4",

    "FINAL":
        ROOT
        / "videos"
        / f"short_v6_{SID}.mp4",
}


for name, path in render_files.items():

    valid = (
        path.is_file()
        and
        path.stat().st_size > 0
    )

    status = (
        "PASS"
        if valid
        else
        (
            "WARN"
            if name == "FINAL"
            else "FAIL"
        )
    )


    result(
        status,
        f"RENDER_{name}",
        (
            f"{path} | "
            f"bytes="
            f"{path.stat().st_size if path.exists() else 0}"
        ),
    )


final = render_files[
    "FINAL"
]


if final.is_file():

    rc, text = run(
        [
            "ffprobe",
            "-v",
            "error",

            "-show_entries",
            (
                "format="
                "duration,size,bit_rate"
            ),

            "-show_entries",
            (
                "stream="
                "codec_name,codec_type,"
                "width,height,r_frame_rate"
            ),

            "-of",
            "default=noprint_wrappers=1",

            str(final),
        ],
        30,
    )


    result(
        "PASS"
        if rc == 0
        else "FAIL",
        "FINAL_FFPROBE",
        text.strip()[-1200:],
    )


# ============================================================
# 13. FRESH RENDER GUARD
# ============================================================

section(
    "13. FRESH RENDER GUARD SAFETY"
)

guard = (
    ROOT
    / "fresh_render_guard_v1.py"
)


if guard.is_file():

    source = guard.read_text(
        encoding="utf-8",
        errors="replace",
    )


    ass_protected = (
        ".ass" in source
        and
        "PROTECTED" in source
    )


    result(
        "PASS"
        if ass_protected
        else "WARN",
        "FRESH_GUARD_ASS_PROTECTION",
        "detected"
        if ass_protected
        else "not obvious",
    )


    temp_video = (
        "video_sem_audio.mp4"
        in source
    )


    result(
        "PASS"
        if temp_video
        else "WARN",
        "FRESH_GUARD_TEMP_VIDEO_TARGET",
        "detected"
        if temp_video
        else "not obvious",
    )


# ============================================================
# 14. PROVIDER DIVERSITY EVIDENCE
# ============================================================

section(
    "14. RECENT PROVIDER SELECTION EVIDENCE"
)

production_logs = (
    ROOT
    / "logs"
    / "producao"
)


if production_logs.is_dir():

    logs = sorted(
        production_logs.glob(
            f"*{SID}*.log"
        )
    )

else:

    logs = []


chosen = Counter()
pools = Counter()


for path in logs:

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for match in re.finditer(
        r"ESCOLHIDO:\s*([^/\n]+)\s*/",
        text,
    ):

        chosen[
            match.group(1)
            .strip()
            .lower()
        ] += 1


    for match in re.finditer(
        r"VSE3_POOL_PROVIDERS=([^\n]+)",
        text,
    ):

        pools[
            match.group(1).strip()
        ] += 1


out(
    "CHOSEN_PROVIDER_COUNTS="
    +
    str(dict(chosen))
)

out(
    "VSE3_POOL_SAMPLES="
    +
    str(dict(pools))
)


if chosen:

    total = sum(
        chosen.values()
    )

    provider_name, amount = (
        chosen.most_common(1)[0]
    )


    result(
        "WARN"
        if (
            amount == total
            and total >= 6
        )
        else "PASS",
        "PROVIDER_DIVERSITY_EVIDENCE",
        (
            f"{provider_name}="
            f"{amount}/{total}"
        ),
    )


else:

    result(
        "INFO",
        "PROVIDER_DIVERSITY_EVIDENCE",
        "no provider-selection evidence found",
    )


# ============================================================
# 15. SUMMARY
# ============================================================

section(
    "15. MASTER SUMMARY"
)

counts = Counter(
    item["status"]
    for item in results
)


if counts[
    "FAIL"
]:

    overall = "FAIL"


elif counts[
    "WARN"
]:

    overall = "WARN"


else:

    overall = "PASS"


out(
    f"AUDIT_PASS={counts['PASS']}"
)

out(
    f"AUDIT_WARN={counts['WARN']}"
)

out(
    f"AUDIT_FAIL={counts['FAIL']}"
)

out(
    f"AUDIT_INFO={counts['INFO']}"
)

out(
    f"OVERALL_STATUS={overall}"
)


failures = [
    item
    for item in results
    if item[
        "status"
    ] == "FAIL"
]


if failures:

    out()
    out(
        "===== CRITICAL FAILURES ====="
    )

    for index, item in enumerate(
        failures,
        start=1,
    ):

        out(
            f"FAIL_{index}="
            f"{item['test']} | "
            f"{item['detail']}"
        )


out()
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
    "PIPELINE_EXECUTED=NO"
)

out(
    "PROJECT_CODE_MODIFIED=NO"
)

out(
    "AUDIT_COMPLETE=YES"
)


REPORT_TXT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)


REPORT_JSON.write_text(
    json.dumps(
        {
            "short_id": SID,
            "overall": overall,
            "counts": dict(counts),
            "results": results,
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print(
    f"REPORT_TXT="
    f"{REPORT_TXT.relative_to(ROOT)}"
)

print(
    f"REPORT_JSON="
    f"{REPORT_JSON.relative_to(ROOT)}"
)


raise SystemExit(
    2
    if counts["FAIL"]
    else 0
)
