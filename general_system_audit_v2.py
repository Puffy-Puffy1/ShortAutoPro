#!/usr/bin/env python3

from pathlib import Path
from collections import Counter, defaultdict
import ast
import hashlib
import json
import os
import re
import runpy
import subprocess
import sys
import time
import traceback


ROOT = Path.home() / "ShortAutoPro"

REPORT = (
    ROOT
    / "temp"
    / "GENERAL_SYSTEM_AUDIT_V2.txt"
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


PASS = []
WARN = []
FAIL = []


def out(*args):

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


def header(title):

    out()
    out("=" * 72)
    out(title)
    out("=" * 72)


def good(name, detail=""):

    PASS.append(name)

    out(
        "PASS |",
        name,
        "|",
        detail,
    )


def warning(name, detail=""):

    WARN.append(name)

    out(
        "WARN |",
        name,
        "|",
        detail,
    )


def bad(name, detail=""):

    FAIL.append(name)

    out(
        "FAIL |",
        name,
        "|",
        detail,
    )


def sha(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for block in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):
            h.update(block)

    return h.hexdigest()


REPORT.write_text(
    "",
    encoding="utf-8",
)


header(
    "SHORTAUTOPRO - GENERAL SYSTEM AUDIT V2"
)

out(
    "TIME=",
    time.strftime(
        "%Y-%m-%d %H:%M:%S"
    ),
)

out(
    "ROOT=",
    ROOT,
)


# ============================================================
# 1. CORE FILES
# ============================================================

header(
    "1. CORE FILE PRESENCE + HASH"
)

core = [
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v4.py",
    "fresh_render_guard_v1.py",
]


for name in core:

    path = ROOT / name

    if path.is_file():

        good(
            "CORE_" + name,
            sha(path)[:16],
        )

    else:

        bad(
            "CORE_" + name,
            "missing",
        )


# ============================================================
# 2. ALL ROOT PYTHON SYNTAX
# ============================================================

header(
    "2. ROOT PYTHON SYNTAX AUDIT"
)

py_files = sorted(
    ROOT.glob("*.py")
)

syntax_bad = []


for path in py_files:

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

        syntax_bad.append(
            (
                path.name,
                f"{type(exc).__name__}: {exc}",
            )
        )


out(
    "ROOT_PYTHON_FILES=",
    len(py_files),
)


if not syntax_bad:

    good(
        "ROOT_PYTHON_SYNTAX",
        f"{len(py_files)} files",
    )

else:

    for name, err in syntax_bad:

        bad(
            "PYTHON_SYNTAX_" + name,
            err,
        )


# ============================================================
# 3. ROOT SHELL SYNTAX
# ============================================================

header(
    "3. ROOT SHELL SYNTAX AUDIT"
)

shell_files = sorted(
    ROOT.glob("*.sh")
)

shell_bad = []


for path in shell_files:

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

    if result.returncode:

        shell_bad.append(
            (
                path.name,
                result.stderr.strip(),
            )
        )


out(
    "ROOT_SHELL_FILES=",
    len(shell_files),
)


if not shell_bad:

    good(
        "ROOT_SHELL_SYNTAX",
        f"{len(shell_files)} files",
    )

else:

    for name, err in shell_bad:

        bad(
            "SHELL_SYNTAX_" + name,
            err,
        )


# ============================================================
# 4. RUN ID INVENTORY
# ============================================================

header(
    "4. RUN ID INVENTORY"
)


def ids_from_media():

    result = []

    base = ROOT / "imagens"

    if not base.is_dir():
        return result

    for d in base.glob(
        "short_*"
    ):

        if not d.is_dir():
            continue

        sid = d.name[
            len("short_"):
        ]

        files = [
            p
            for p in d.glob(
                "scene_*.*"
            )
            if p.is_file()
        ]

        mtime = max(
            [
                p.stat().st_mtime
                for p in files
            ]
            or
            [
                d.stat().st_mtime
            ]
        )

        result.append(
            (
                sid,
                len(files),
                mtime,
                d,
            )
        )

    return result


media_runs = ids_from_media()


for sid, count, mt, path in sorted(
    media_runs,
    key=lambda x: x[2],
    reverse=True,
)[:20]:

    out(
        f"MEDIA_RUN={sid} "
        f"scenes={count} "
        f"mtime={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mt))}"
    )


valid_12 = [
    x
    for x in media_runs
    if x[1] == 12
]


if valid_12:

    active_media = max(
        valid_12,
        key=lambda x: x[2],
    )

    ACTIVE_MEDIA_ID = active_media[0]

    good(
        "ACTIVE_12_SCENE_RUN",
        ACTIVE_MEDIA_ID,
    )

else:

    ACTIVE_MEDIA_ID = None

    warning(
        "ACTIVE_12_SCENE_RUN",
        "none currently retained",
    )


def latest_id_from_pattern(
    directory,
    regex,
):

    directory = ROOT / directory

    matches = []

    if directory.is_dir():

        for path in directory.iterdir():

            if not path.is_file():
                continue

            m = re.fullmatch(
                regex,
                path.name,
            )

            if m:

                matches.append(
                    (
                        m.group(1),
                        path.stat().st_mtime,
                        path,
                    )
                )

    if not matches:
        return None

    return max(
        matches,
        key=lambda x: x[1],
    )


latest_audio = latest_id_from_pattern(
    "audios",
    r"short_(.+)\.mp3",
)

latest_ass = latest_id_from_pattern(
    "videos",
    r"short_(?!v6_)(.+)\.ass",
)

latest_final = latest_id_from_pattern(
    "videos",
    r"short_v6_(.+)\.mp4",
)


for label, item in (
    (
        "LATEST_AUDIO",
        latest_audio,
    ),
    (
        "LATEST_ASS",
        latest_ass,
    ),
    (
        "LATEST_FINAL",
        latest_final,
    ),
):

    if item:

        out(
            f"{label}_ID={item[0]}"
        )

        out(
            f"{label}_FILE={item[2]}"
        )

    else:

        out(
            f"{label}=NONE"
        )


# ============================================================
# 5. MEDIA STRUCTURE — DYNAMIC, NOT HARDCODED
# ============================================================

header(
    "5. ACTIVE MEDIA STRUCTURE"
)


if ACTIVE_MEDIA_ID:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{ACTIVE_MEDIA_ID}"
    )

    total = 0
    invalid = 0
    chosen_files = []


    for n in range(
        1,
        13,
    ):

        scene_files = list(
            media_dir.glob(
                f"scene_{n:02d}.*"
            )
        )

        scene_files = [
            x
            for x in scene_files
            if x.is_file()
        ]

        total += len(
            scene_files
        )

        if len(
            scene_files
        ) != 1:

            invalid += 1

            bad(
                f"SCENE_{n:02d}_COUNT",
                str(
                    len(scene_files)
                ),
            )

        else:

            chosen_files.append(
                scene_files[0]
            )


    out(
        "ACTIVE_MEDIA_ID=",
        ACTIVE_MEDIA_ID,
    )

    out(
        "MEDIA_TOTAL=",
        total,
    )

    out(
        "INVALID_SCENE_COUNT=",
        invalid,
    )


    if (
        total == 12
        and
        invalid == 0
    ):

        good(
            "MEDIA_SCENE_STRUCTURE",
            "12/12",
        )


else:

    warning(
        "MEDIA_SCENE_STRUCTURE",
        "no retained 12-scene run; not treated as pipeline failure",
    )

    chosen_files = []


# ============================================================
# 6. MEDIA TECHNICAL VALIDATION
# ============================================================

header(
    "6. MEDIA TECHNICAL VALIDATION"
)

technical_ok = 0
technical_fail = 0


for path in chosen_files:

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=codec_name,width,height",
        "-show_entries",
        "format=duration,size",
        "-of",
        "json",
        str(path),
    ]

    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if proc.returncode == 0:

        try:

            data = json.loads(
                proc.stdout
            )

            if (
                data.get("streams")
                or
                data.get("format")
            ):

                technical_ok += 1

                continue

        except Exception:
            pass


    technical_fail += 1

    bad(
        "MEDIA_TECH_" + path.name,
        proc.stderr.strip()[:200],
    )


out(
    "MEDIA_TECHNICAL_OK=",
    technical_ok,
)

out(
    "MEDIA_TECHNICAL_FAILURES=",
    technical_fail,
)


if chosen_files:

    if technical_fail == 0:

        good(
            "MEDIA_TECHNICAL_TEST",
            f"{technical_ok}/12",
        )

else:

    warning(
        "MEDIA_TECHNICAL_TEST",
        "skipped because no retained active media",
    )


# ============================================================
# 7. EXACT DUPLICATE MEDIA HASH
# ============================================================

header(
    "7. MEDIA EXACT-DUPLICATE AUDIT"
)

hash_groups = defaultdict(
    list
)


for path in chosen_files:

    try:

        hash_groups[
            sha(path)
        ].append(
            path.name
        )

    except Exception as exc:

        bad(
            "MEDIA_HASH_" + path.name,
            str(exc),
        )


duplicates = {
    h: names
    for h, names in hash_groups.items()
    if len(names) > 1
}


if duplicates:

    for h, names in duplicates.items():

        warning(
            "EXACT_MEDIA_DUPLICATE",
            f"{names} sha={h[:16]}",
        )

else:

    if chosen_files:

        good(
            "MEDIA_EXACT_DUPLICATE",
            "none",
        )


# ============================================================
# 8. VSE4 MODULE LOAD + SELF TEST
# ============================================================

header(
    "8. VSE4 RUNTIME CERTIFICATION"
)

vse_path = (
    ROOT
    / "visual_selection_engine_v4.py"
)


vse_ns = None


if vse_path.is_file():

    try:

        vse_ns = runpy.run_path(
            str(vse_path),
            run_name="shortautopro_general_audit_v2",
        )

        good(
            "VSE4_MODULE_LOAD",
            "PASS",
        )

    except Exception:

        bad(
            "VSE4_MODULE_LOAD",
            traceback.format_exc()[-2000:],
        )


if vse_ns:

    self_test = vse_ns.get(
        "self_test"
    )

    if callable(
        self_test
    ):

        try:

            self_test()

            good(
                "VSE4_SELF_TEST",
                "PASS",
            )

        except Exception:

            bad(
                "VSE4_SELF_TEST",
                traceback.format_exc()[-1800:],
            )

    else:

        warning(
            "VSE4_SELF_TEST",
            "function absent",
        )


# ============================================================
# 9. VSE4 DIRECT SEMANTIC REGRESSION
# ============================================================

header(
    "9. VSE4 DIRECT SEMANTIC REGRESSION"
)


if vse_ns:

    score_candidate = vse_ns.get(
        "score_candidate"
    )


    if callable(
        score_candidate
    ):

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
                "Empire State Building Manhattan New York",
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


            out(
                "WRONG_HARD_MISMATCH=",
                a.get(
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
                "CORRECT_HARD_MISMATCH=",
                b.get(
                    "hard_mismatch"
                ),
            )

            out(
                "CORRECT_EFFECTIVE=",
                b.get(
                    "effective"
                ),
            )


            if a.get(
                "hard_mismatch"
            ) is True:

                good(
                    "VSE4_GEO_HARD_MISMATCH",
                    "São Paulo rejects New York",
                )

            else:

                bad(
                    "VSE4_GEO_HARD_MISMATCH",
                    "New York candidate was not hard rejected",
                )


            if b.get(
                "hard_mismatch"
            ) is False:

                good(
                    "VSE4_GEO_CORRECT_MEDIA",
                    "São Paulo candidate accepted",
                )

            else:

                bad(
                    "VSE4_GEO_CORRECT_MEDIA",
                    "correct candidate hard rejected",
                )


            try:

                if (
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
                ):

                    good(
                        "VSE4_GEO_RANK_ORDER",
                        "correct > wrong",
                    )

                else:

                    bad(
                        "VSE4_GEO_RANK_ORDER",
                        "wrong candidate ranks too high",
                    )

            except Exception as exc:

                bad(
                    "VSE4_GEO_RANK_ORDER",
                    str(exc),
                )


        except Exception:

            bad(
                "VSE4_DIRECT_SCORING",
                traceback.format_exc()[-2000:],
            )


# ============================================================
# 10. PROVIDER GLOBAL BINDINGS IN MIDIA.PY
# ============================================================

header(
    "10. PROVIDER BINDING AUDIT"
)

midia_path = (
    ROOT
    / "midia.py"
)


provider_names = [
    "buscar_wikimedia_fotos",
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
]


if midia_path.is_file():

    source = midia_path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    tree = ast.parse(
        source
    )


    defs = set()
    imports = set()
    assigns = set()
    wildcard_imports = []


    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            defs.add(
                node.name
            )


        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            for alias in node.names:

                if alias.name == "*":

                    wildcard_imports.append(
                        node.module
                    )

                else:

                    imports.add(
                        alias.asname
                        or
                        alias.name
                    )


        elif isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                imports.add(
                    alias.asname
                    or
                    alias.name.split(".")[0]
                )


        elif isinstance(
            node,
            ast.Assign,
        ):

            for target in node.targets:

                if isinstance(
                    target,
                    ast.Name,
                ):

                    assigns.add(
                        target.id
                    )


    globals_known = (
        defs
        |
        imports
        |
        assigns
    )


    for name in provider_names:

        if name in globals_known:

            source_type = (
                "def"
                if name in defs
                else
                "import"
                if name in imports
                else
                "assignment"
            )

            good(
                "PROVIDER_BINDING_" + name,
                source_type,
            )

        else:

            call_lines = []

            for node in ast.walk(
                tree
            ):

                if (
                    isinstance(
                        node,
                        ast.Call,
                    )
                    and
                    isinstance(
                        node.func,
                        ast.Name,
                    )
                    and
                    node.func.id == name
                ):

                    call_lines.append(
                        node.lineno
                    )


            if call_lines:

                if wildcard_imports:

                    warning(
                        "PROVIDER_BINDING_" + name,
                        "not statically defined; wildcard imports="
                        +
                        ",".join(
                            str(x)
                            for x in wildcard_imports
                        ),
                    )

                else:

                    bad(
                        "PROVIDER_BINDING_" + name,
                        "called at lines "
                        +
                        ",".join(
                            map(
                                str,
                                call_lines,
                            )
                        )
                        +
                        " but no global binding found",
                    )

            else:

                warning(
                    "PROVIDER_BINDING_" + name,
                    "not bound and not directly called",
                )


# ============================================================
# 11. PROVIDER CALL MAP
# ============================================================

header(
    "11. PROVIDER ACQUISITION CALL MAP"
)


if midia_path.is_file():

    tree = ast.parse(
        midia_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    )


    search_fn = None


    for node in tree.body:

        if (
            isinstance(
                node,
                ast.FunctionDef,
            )
            and
            node.name
            ==
            "buscar_todos_candidatos"
        ):

            search_fn = node


    if search_fn:

        calls = []


        for node in ast.walk(
            search_fn
        ):

            if isinstance(
                node,
                ast.Call,
            ):

                try:

                    calls.append(
                        (
                            node.lineno,
                            ast.unparse(
                                node.func
                            ),
                        )
                    )

                except Exception:
                    pass


        for provider_name in [
            "buscar_wikimedia_fotos",
            "pexels_video",
            "pexels_foto",
            "pixabay_video",
            "pixabay_foto",
            "coverr_video",
        ]:

            hit = [
                x
                for x in calls
                if x[1]
                ==
                provider_name
            ]


            if hit:

                good(
                    "ACQUISITION_CALL_" + provider_name,
                    "lines="
                    +
                    ",".join(
                        str(x[0])
                        for x in hit
                    ),
                )

            else:

                warning(
                    "ACQUISITION_CALL_" + provider_name,
                    "not called by active buscar_todos_candidatos",
                )

    else:

        bad(
            "BUSCAR_TODOS_CANDIDATOS",
            "definition absent",
        )


# ============================================================
# 12. VSE4 PATH INTEGRATION
# ============================================================

header(
    "12. VSE4 / DIVERSITY INTEGRATION"
)

files_to_scan = {
    "midia.py":
        ROOT / "midia.py",

    "media_diversity_guard_v1.py":
        ROOT
        / "media_diversity_guard_v1.py",
}


for name, path in files_to_scan.items():

    if not path.is_file():
        continue

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )


    count = text.count(
        "visual_selection_engine_v4"
    )


    out(
        f"{name}_VSE4_REFERENCES={count}"
    )


    if count:

        good(
            "VSE4_REFERENCE_" + name,
            str(count),
        )

    else:

        warning(
            "VSE4_REFERENCE_" + name,
            "none",
        )


# ============================================================
# 13. INSTALL / DOUBLE-WRAP AUDIT
# ============================================================

header(
    "13. RUNTIME INSTALL / DOUBLE-WRAP AUDIT"
)


diversity = (
    ROOT
    / "media_diversity_guard_v1.py"
)

provenance = (
    ROOT
    / "media_provenance_capture_v1.py"
)


if diversity.is_file():

    text = diversity.read_text(
        encoding="utf-8",
        errors="replace",
    )


    install_guards = re.findall(
        r"_SAP_[A-Z0-9_]*INSTALLED",
        text,
    )


    out(
        "DIVERSITY_INSTALL_GUARDS=",
        sorted(
            set(
                install_guards
            )
        ),
    )


    if install_guards:

        good(
            "DIVERSITY_IDEMPOTENCY_GUARD",
            str(
                len(
                    set(
                        install_guards
                    )
                )
            ),
        )

    else:

        warning(
            "DIVERSITY_IDEMPOTENCY_GUARD",
            "none detected",
        )


if provenance.is_file():

    text = provenance.read_text(
        encoding="utf-8",
        errors="replace",
    )


    if (
        "_SAP_PROVENANCE_CAPTURE_V1_INSTALLED"
        in text
    ):

        good(
            "PROVENANCE_IDEMPOTENCY_GUARD",
            "present",
        )

    else:

        warning(
            "PROVENANCE_IDEMPOTENCY_GUARD",
            "not detected",
        )


# ============================================================
# 14. GERAR_SHORT STAGE REFERENCES
# ============================================================

header(
    "14. PIPELINE STAGE REFERENCE AUDIT"
)

gerar = (
    ROOT
    / "gerar_short.sh"
)


stages = [
    "roteiro.py",
    "midia.py",
    "legenda_dinamica.py",
    "video.py",
    "v6.py",
    "v5.py",
    "quality_check.py",
    "publish_pack.py",
]


if gerar.is_file():

    text = gerar.read_text(
        encoding="utf-8",
        errors="replace",
    )


    for stage in stages:

        matches = list(
            re.finditer(
                re.escape(
                    stage
                ),
                text,
            )
        )


        count = len(
            matches
        )


        out(
            f"PIPELINE_REFERENCE_COUNT | "
            f"{stage} | {count}"
        )


        if count:

            good(
                "PIPELINE_STAGE_" + stage,
                f"references={count}",
            )

        else:

            warning(
                "PIPELINE_STAGE_" + stage,
                "no literal reference",
            )


# ============================================================
# 15. PROVENANCE LIVE DATA
# ============================================================

header(
    "15. PROVENANCE LIVE DATA"
)

prov_dir = (
    ROOT
    / "manifests"
    / "source_provenance_live"
)


if prov_dir.is_dir():

    prov_files = sorted(
        prov_dir.glob("*.json"),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


    out(
        "PROVENANCE_FILES=",
        len(prov_files),
    )


    valid = 0
    invalid = 0


    for path in prov_files[:100]:

        try:

            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )

            if (
                data.get(
                    "sha256"
                )
                and
                data.get(
                    "provider"
                )
                and
                data.get(
                    "source_url"
                )
            ):

                valid += 1

            else:

                invalid += 1

        except Exception:

            invalid += 1


    out(
        "PROVENANCE_RECENT_VALID=",
        valid,
    )

    out(
        "PROVENANCE_RECENT_INVALID=",
        invalid,
    )


    if valid:

        good(
            "PROVENANCE_LIVE_DATA",
            f"valid={valid} invalid={invalid}",
        )

    else:

        warning(
            "PROVENANCE_LIVE_DATA",
            "no recent complete records",
        )


else:

    warning(
        "PROVENANCE_LIVE_DATA",
        "directory absent",
    )


# ============================================================
# 16. JSON INTEGRITY
# ============================================================

header(
    "16. RECENT JSON INTEGRITY"
)

json_candidates = []


for folder in [
    ROOT / "roteiros",
    ROOT / "manifests",
    ROOT / "temp",
]:

    if folder.is_dir():

        json_candidates.extend(
            [
                p
                for p in folder.rglob(
                    "*.json"
                )
                if p.is_file()
            ]
        )


json_candidates = sorted(
    json_candidates,
    key=lambda p:
        p.stat().st_mtime,
    reverse=True,
)[:200]


json_bad = []


for path in json_candidates:

    try:

        json.loads(
            path.read_text(
                encoding="utf-8",
                errors="strict",
            )
        )

    except Exception as exc:

        json_bad.append(
            (
                path,
                str(exc),
            )
        )


out(
    "RECENT_JSON_CHECKED=",
    len(
        json_candidates
    ),
)


if not json_bad:

    good(
        "RECENT_JSON_INTEGRITY",
        "PASS",
    )

else:

    for path, err in json_bad[:20]:

        bad(
            "JSON_INVALID",
            f"{path.relative_to(ROOT)} | {err}",
        )


# ============================================================
# 17. TODO/FIXME AUDIT — WORD BOUNDARIES
# ============================================================

header(
    "17. REAL TODO / FIXME / HACK AUDIT"
)

pattern = re.compile(
    r"\b(TODO|FIXME|XXX|HACK)\b",
    re.IGNORECASE,
)

todo_hits = []


for path in list(
    ROOT.glob("*.py")
) + list(
    ROOT.glob("*.sh")
):

    try:

        for num, line in enumerate(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines(),
            start=1,
        ):

            if pattern.search(
                line
            ):

                todo_hits.append(
                    (
                        path.name,
                        num,
                        line.strip(),
                    )
                )

    except Exception:
        pass


out(
    "REAL_TODO_FIXME_COUNT=",
    len(todo_hits),
)


for item in todo_hits[:50]:

    out(
        "TODO_MARKER |",
        f"{item[0]}:{item[1]}",
        "|",
        item[2],
    )


if not todo_hits:

    good(
        "TODO_FIXME_AUDIT",
        "none",
    )

else:

    warning(
        "TODO_FIXME_AUDIT",
        str(
            len(todo_hits)
        ),
    )


# ============================================================
# 18. RECENT LOG ERROR MARKERS
# ============================================================

header(
    "18. RECENT PRODUCTION LOG ERRORS"
)

log_dir = (
    ROOT
    / "logs"
    / "producao"
)

error_logs = []


if log_dir.is_dir():

    logs = sorted(
        [
            p
            for p in log_dir.glob(
                "*.log"
            )
            if p.is_file()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )[:50]


    error_re = re.compile(
        r"(^|\b)(TRACEBACK|ERROR|ERRO:|FAIL(?:ED)?)(\b|:)",
        re.IGNORECASE,
    )


    for path in logs:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )


        hits = [
            line.strip()
            for line in text.splitlines()
            if error_re.search(
                line
            )
        ]


        if hits:

            error_logs.append(
                (
                    path,
                    hits[-5:],
                )
            )


out(
    "RECENT_LOGS_WITH_ERROR_MARKERS=",
    len(
        error_logs
    ),
)


for path, lines in error_logs[:10]:

    warning(
        "RECENT_LOG_ERROR_" + path.name,
        " || ".join(lines),
    )


if not error_logs:

    good(
        "RECENT_LOG_ERROR_AUDIT",
        "none",
    )


# ============================================================
# 19. FINAL VIDEO VALIDITY
# ============================================================

header(
    "19. LATEST FINAL VIDEO"
)


if latest_final:

    sid = latest_final[0]
    path = latest_final[2]


    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,codec_type,width,height,r_frame_rate",
            "-show_entries",
            "format=duration,size,bit_rate",
            "-of",
            "json",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


    if proc.returncode == 0:

        try:

            data = json.loads(
                proc.stdout
            )

            out(
                json.dumps(
                    data,
                    indent=2,
                    ensure_ascii=False,
                )
            )

            good(
                "LATEST_FINAL_FFPROBE",
                sid,
            )

        except Exception as exc:

            bad(
                "LATEST_FINAL_FFPROBE",
                str(exc),
            )

    else:

        bad(
            "LATEST_FINAL_FFPROBE",
            proc.stderr.strip(),
        )


# ============================================================
# 20. CERTIFICATION FRESHNESS
# ============================================================

header(
    "20. CERTIFICATION FRESHNESS"
)

core_times = [
    p.stat().st_mtime
    for p in [
        ROOT / "midia.py",
        ROOT
        / "media_diversity_guard_v1.py",
        ROOT
        / "visual_selection_engine_v4.py",
        ROOT
        / "media_provenance_capture_v1.py",
    ]
    if p.exists()
]


newest_core = max(
    core_times
    or
    [0]
)


certs = [
    p
    for p in (
        ROOT
        / "temp"
    ).rglob(
        "*CERTIF*.json"
    )
    if p.is_file()
]


certs += [
    p
    for p in (
        ROOT
        / "temp"
    ).rglob(
        "CERTIFIED.json"
    )
    if p.is_file()
]


certs = list(
    dict.fromkeys(
        certs
    )
)


stale = [
    p
    for p in certs
    if p.stat().st_mtime
    <
    newest_core
]


out(
    "CERTIFICATES_FOUND=",
    len(certs),
)

out(
    "STALE_CERTIFICATES=",
    len(stale),
)


if stale:

    warning(
        "CERTIFICATION_FRESHNESS",
        "old certificates cannot certify current core",
    )

else:

    good(
        "CERTIFICATION_FRESHNESS",
        "no stale certificates",
    )


# ============================================================
# 21. FINAL SUMMARY
# ============================================================

header(
    "21. FINAL AUDIT SUMMARY"
)

out(
    "PASS_COUNT=",
    len(PASS),
)

out(
    "WARN_COUNT=",
    len(WARN),
)

out(
    "FAIL_COUNT=",
    len(FAIL),
)


if FAIL:

    out()
    out(
        "===== BLOCKERS ====="
    )

    for item in FAIL:

        out(
            "BLOCKER=",
            item,
        )


if WARN:

    out()
    out(
        "===== WARNINGS ====="
    )

    for item in WARN:

        out(
            "WARNING=",
            item,
        )


out()

if not FAIL:

    out(
        "GENERAL_AUDIT_V2=PASS"
    )

else:

    out(
        "GENERAL_AUDIT_V2=FAIL"
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
    "SOURCE_FILES_MODIFIED=NO"
)

out(
    "REPORT=",
    REPORT,
)

out(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
