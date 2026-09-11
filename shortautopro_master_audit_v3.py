#!/usr/bin/env python3

from pathlib import Path
from collections import defaultdict, Counter
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import symtable
import sys
import time


ROOT = Path.home() / "ShortAutoPro"
REPORT = ROOT / "temp" / "SHORTAUTOPRO_MASTER_AUDIT_V3.txt"
JSON_REPORT = ROOT / "temp" / "SHORTAUTOPRO_MASTER_AUDIT_V3.json"

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


PASS = []
WARN = []
FAIL = []
INFO = []


def emit(text=""):
    print(text)


def section(title):
    emit()
    emit("=" * 76)
    emit(title)
    emit("=" * 76)


def status(kind, key, detail=""):

    line = f"{kind} | {key}"

    if detail:
        line += f" | {detail}"

    emit(line)

    bucket = {
        "PASS": PASS,
        "WARN": WARN,
        "FAIL": FAIL,
        "INFO": INFO,
    }.get(kind)

    if bucket is not None:
        bucket.append(
            {
                "key": key,
                "detail": detail,
            }
        )


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
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


def parse(path):

    try:
        return ast.parse(
            text(path),
            filename=str(path),
        )
    except Exception:
        return None


def shell_check(path):

    try:
        r = subprocess.run(
            [
                "bash",
                "-n",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

        return (
            r.returncode,
            r.stderr.strip(),
        )

    except Exception as exc:

        return (
            999,
            f"{type(exc).__name__}: {exc}",
        )


def command_exists(name):
    return shutil.which(name) is not None


def ffprobe_ok(path):

    if not command_exists("ffprobe"):
        return None

    try:

        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration,size",
                "-of",
                "json",
                str(path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )

        return r.returncode == 0

    except Exception:
        return False


def numbered_scene(name):

    m = re.match(
        r"^scene_(\d{2})\.",
        name,
        re.I,
    )

    if not m:
        return None

    return int(
        m.group(1)
    )


# ============================================================
# START
# ============================================================

original_stdout = sys.stdout

REPORT_HANDLE = REPORT.open(
    "w",
    encoding="utf-8",
)


class Tee:

    def write(self, data):

        original_stdout.write(data)
        REPORT_HANDLE.write(data)

    def flush(self):

        original_stdout.flush()
        REPORT_HANDLE.flush()


sys.stdout = Tee()


section(
    "SHORTAUTOPRO MASTER AUDIT V3"
)

emit(
    f"DATE={time.strftime('%Y-%m-%d %H:%M:%S')}"
)

emit(
    f"ROOT={ROOT}"
)

emit(
    f"PYTHON={sys.version.split()[0]}"
)

emit(
    "MODE=READ_ONLY_DIAGNOSTIC"
)


# ============================================================
# 1 ENVIRONMENT
# ============================================================

section(
    "1. ENVIRONMENT / BINARIES"
)

for binary in (
    "python",
    "ffmpeg",
    "ffprobe",
    "bash",
):

    if command_exists(binary):
        status(
            "PASS",
            f"BINARY_{binary.upper()}",
            shutil.which(binary) or "",
        )
    else:
        status(
            "FAIL",
            f"BINARY_{binary.upper()}",
            "not found",
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

    emit(
        f"DISK_FREE_MB={free_mb:.1f}"
    )

    if free_mb < 500:

        status(
            "WARN",
            "LOW_DISK_SPACE",
            f"{free_mb:.1f} MB free",
        )

    else:

        status(
            "PASS",
            "DISK_SPACE",
            f"{free_mb:.1f} MB free",
        )

except Exception as exc:

    status(
        "WARN",
        "DISK_CHECK",
        str(exc),
    )


# ============================================================
# 2 CORE FILES
# ============================================================

section(
    "2. CORE FILE PRESENCE + HASHES"
)

core_files = (
    "gerar_short.sh",
    "roteiro.py",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
    "visual_scene_commit_lock_v1.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
)

for name in core_files:

    path = ROOT / name

    if path.is_file():

        status(
            "PASS",
            f"CORE_{name}",
            f"sha256={sha256(path)}",
        )

    else:

        # Nem todos os auxiliares são obrigatórios.
        severity = (
            "FAIL"
            if name in {
                "gerar_short.sh",
                "midia.py",
                "video.py",
                "v6.py",
            }
            else
            "WARN"
        )

        status(
            severity,
            f"CORE_{name}",
            "missing",
        )


# ============================================================
# 3 ALL PYTHON SYNTAX
# ============================================================

section(
    "3. PYTHON SYNTAX — TOP LEVEL"
)

python_files = sorted(
    p
    for p in ROOT.glob("*.py")
    if p.is_file()
)

syntax_fail = []

for path in python_files:

    try:

        compile(
            text(path),
            str(path),
            "exec",
            flags=ast.PyCF_ONLY_AST,
        )

    except Exception as exc:

        syntax_fail.append(
            (
                path.name,
                f"{type(exc).__name__}: {exc}",
            )
        )


emit(
    f"TOP_LEVEL_PY_FILES={len(python_files)}"
)

if syntax_fail:

    for name, err in syntax_fail:

        status(
            "FAIL",
            f"PYTHON_SYNTAX_{name}",
            err,
        )

else:

    status(
        "PASS",
        "ALL_TOP_LEVEL_PYTHON_SYNTAX",
        f"{len(python_files)} files",
    )


# ============================================================
# 4 SHELL SYNTAX
# ============================================================

section(
    "4. SHELL SYNTAX — TOP LEVEL"
)

shell_files = sorted(
    p
    for p in ROOT.glob("*.sh")
    if p.is_file()
)

shell_fail = []

for path in shell_files:

    code, err = shell_check(
        path
    )

    if code != 0:

        shell_fail.append(
            (
                path.name,
                err,
            )
        )


emit(
    f"TOP_LEVEL_SH_FILES={len(shell_files)}"
)

if shell_fail:

    for name, err in shell_fail:

        status(
            "FAIL",
            f"SHELL_SYNTAX_{name}",
            err,
        )

else:

    status(
        "PASS",
        "ALL_TOP_LEVEL_SHELL_SYNTAX",
        f"{len(shell_files)} files",
    )


# ============================================================
# 5 DUPLICATE DEFINITIONS
# ============================================================

section(
    "5. DUPLICATE TOP-LEVEL DEFINITIONS"
)

important_py = (
    "visual_selection_engine_v4.py",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_diversity_guard_v1.py",
    "visual_scene_commit_lock_v1.py",
)

duplicate_total = 0


for filename in important_py:

    path = ROOT / filename

    if not path.is_file():
        continue

    tree = parse(path)

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
                ast.ClassDef,
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


    if not duplicates:

        status(
            "PASS",
            f"DUPLICATE_DEFS_{filename}",
            "none",
        )

        continue


    duplicate_total += len(
        duplicates
    )


    for name, lines in sorted(
        duplicates.items()
    ):

        status(
            "WARN",
            f"DUPLICATE_DEF_{filename}:{name}",
            "lines="
            +
            ",".join(
                map(str, lines)
            )
            +
            f" active={lines[-1]}",
        )


emit(
    f"DUPLICATE_FUNCTION_NAMES_TOTAL={duplicate_total}"
)


# ============================================================
# 6 VSE4 SPECIFIC DEFINITIONS
# ============================================================

section(
    "6. VSE4 ACTIVE DEFINITION MAP"
)

vse = ROOT / "visual_selection_engine_v4.py"

if vse.is_file():

    tree = parse(vse)

    names = (
        "candidate_text",
        "tokens",
        "geo_hits",
        "concept_hits",
        "score_candidate",
        "must_tier",
        "provider",
        "source_group",
        "media_type",
        "objget",
        "self_test",
    )

    if tree:

        defs = defaultdict(
            list
        )

        for node in tree.body:

            if isinstance(
                node,
                ast.FunctionDef,
            ):

                defs[
                    node.name
                ].append(
                    node.lineno
                )


        for name in names:

            lines = defs.get(
                name,
                [],
            )

            if not lines:

                status(
                    "FAIL",
                    f"VSE4_DEF_{name}",
                    "missing",
                )

            elif len(lines) == 1:

                status(
                    "PASS",
                    f"VSE4_DEF_{name}",
                    f"line={lines[0]}",
                )

            else:

                status(
                    "WARN",
                    f"VSE4_DEF_{name}",
                    f"count={len(lines)} lines={lines} active={lines[-1]}",
                )


# ============================================================
# 7 VSE4 UNRESOLVED GLOBALS
# ============================================================

section(
    "7. VSE4 GLOBAL SYMBOL AUDIT"
)

if vse.is_file():

    try:

        src = text(vse)

        table = symtable.symtable(
            src,
            str(vse),
            "exec",
        )

        import builtins

        builtin_names = set(
            dir(builtins)
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

                    unresolved.add(
                        name
                    )

                walk(child)


        walk(table)


        if unresolved:

            status(
                "FAIL",
                "VSE4_UNRESOLVED_GLOBALS",
                ",".join(
                    sorted(
                        unresolved
                    )
                ),
            )

        else:

            status(
                "PASS",
                "VSE4_UNRESOLVED_GLOBALS",
                "none",
            )


    except Exception as exc:

        status(
            "WARN",
            "VSE4_GLOBAL_AUDIT",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 8 VSE4 SELF TEST
# ============================================================

section(
    "8. VSE4 SELF TEST"
)

if vse.is_file():

    try:

        r = subprocess.run(
            [
                sys.executable,
                str(vse),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )

        emit(
            r.stdout[-4000:]
        )

        if r.stderr:
            emit(
                r.stderr[-4000:]
            )

        if r.returncode == 0:

            status(
                "PASS",
                "VSE4_SELF_TEST",
                "status=0",
            )

        else:

            status(
                "FAIL",
                "VSE4_SELF_TEST",
                f"status={r.returncode}",
            )


    except Exception as exc:

        status(
            "FAIL",
            "VSE4_SELF_TEST",
            f"{type(exc).__name__}: {exc}",
        )


# ============================================================
# 9 MIDIA VISUAL STACK
# ============================================================

section(
    "9. MIDIA.PY VISUAL STACK INTEGRATION"
)

midia = ROOT / "midia.py"

if midia.is_file():

    src = text(
        midia
    )

    markers = {

        "VSE4":
            (
                "visual_selection_engine_v4",
                "VSE4",
            ),

        "COMMIT_LOCK":
            (
                "visual_scene_commit_lock",
                "SCENE_COMMIT_LOCK",
            ),

        "DIVERSITY":
            (
                "media_diversity_guard",
                "DIVERSITY",
            ),

        "PROVENANCE":
            (
                "media_provenance_capture",
                "PROVENANCE",
            ),

        "VSE3":
            (
                "visual_selection_final_gate_v3",
                "VSE3",
            ),
    }


    for name, terms in markers.items():

        count = sum(
            src.count(term)
            for term in terms
        )

        emit(
            f"{name}_REFERENCE_COUNT={count}"
        )

        if count:

            status(
                "PASS",
                f"MIDIA_STACK_{name}",
                f"references={count}",
            )

        else:

            severity = (
                "WARN"
                if name == "VSE3"
                else
                "FAIL"
            )

            status(
                severity,
                f"MIDIA_STACK_{name}",
                "no reference found",
            )


# ============================================================
# 10 PROVIDER FUNCTIONS
# ============================================================

section(
    "10. PROVIDER ACQUISITION STATIC AUDIT"
)

provider_functions = (
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
)

if midia.is_file():

    tree = parse(
        midia
    )

    function_nodes = {}

    if tree:

        for node in tree.body:

            if isinstance(
                node,
                ast.FunctionDef,
            ):

                function_nodes[
                    node.name
                ] = node


    for fn in provider_functions:

        node = function_nodes.get(
            fn
        )

        if node is None:

            status(
                "FAIL",
                f"PROVIDER_FUNCTION_{fn}",
                "missing",
            )

            continue


        calls = []

        names = set()


        for child in ast.walk(
            node
        ):

            if isinstance(
                child,
                ast.Call,
            ):

                try:
                    calls.append(
                        ast.unparse(
                            child.func
                        )
                    )
                except Exception:
                    pass

            if isinstance(
                child,
                ast.Name,
            ):

                names.add(
                    child.id
                )


        networkish = sorted(
            {
                call
                for call in calls
                if any(
                    word in call.casefold()
                    for word in (
                        "request",
                        "http",
                        "get",
                        "urlopen",
                        "download",
                    )
                )
            }
        )


        secretish_names = sorted(
            name
            for name in names
            if any(
                token in name.upper()
                for token in (
                    "KEY",
                    "TOKEN",
                    "API",
                    "PEXELS",
                    "PIXABAY",
                    "COVERR",
                )
            )
        )


        status(
            "PASS",
            f"PROVIDER_FUNCTION_{fn}",
            f"line={node.lineno}",
        )

        emit(
            f"{fn}_NETWORK_CALL_NAMES={networkish or ['NONE']}"
        )

        emit(
            f"{fn}_CONFIG_SYMBOL_NAMES={secretish_names or ['NONE']}"
        )


# ============================================================
# 11 CONFIG NAMES ONLY
# ============================================================

section(
    "11. PROVIDER CONFIG NAME DISCOVERY — NO VALUES"
)

config_name_hits = set()

patterns = (
    "PEXELS",
    "PIXABAY",
    "COVERR",
)

candidate_config_files = [
    ROOT / "config.env",
    ROOT / ".env",
    ROOT / "config.py",
]

for path in candidate_config_files:

    if not path.is_file():
        continue

    for line in text(path).splitlines():

        line = line.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key = line.split(
            "=",
            1,
        )[0].strip()

        if any(
            p in key.upper()
            for p in patterns
        ):
            config_name_hits.add(
                key
            )


if config_name_hits:

    for name in sorted(
        config_name_hits
    ):

        emit(
            f"PROVIDER_CONFIG_NAME={name}"
        )

    status(
        "PASS",
        "PROVIDER_CONFIG_NAMES",
        f"count={len(config_name_hits)}",
    )

else:

    status(
        "WARN",
        "PROVIDER_CONFIG_NAMES",
        "none found in config.env/.env/config.py",
    )


emit(
    "SECRET_VALUES_PRINTED=NO"
)


# ============================================================
# 12 SEARCH CONFIG FLOW
# ============================================================

section(
    "12. PROVIDER CONFIG FLOW ACROSS CODE"
)

provider_terms = re.compile(
    r"PEXELS|PIXABAY|COVERR",
    re.I,
)

config_refs = []

for path in python_files:

    src = text(path)

    if not provider_terms.search(
        src
    ):
        continue

    for lineno, line in enumerate(
        src.splitlines(),
        start=1,
    ):

        if provider_terms.search(
            line
        ):

            sanitized = re.sub(
                r"(=.*)$",
                "=<hidden>",
                line.strip(),
            )

            # Não imprime strings longas.
            sanitized = sanitized[:220]

            config_refs.append(
                (
                    path.name,
                    lineno,
                    sanitized,
                )
            )


for filename, lineno, line in config_refs[:200]:

    emit(
        f"CONFIG_REF={filename}:{lineno}:{line}"
    )


emit(
    f"CONFIG_REFERENCE_COUNT={len(config_refs)}"
)


# ============================================================
# 13 PIPELINE CALL MAP
# ============================================================

section(
    "13. GERAR_SHORT PIPELINE CALL MAP"
)

gerar = ROOT / "gerar_short.sh"

if gerar.is_file():

    src = text(
        gerar
    )

    script_calls = []

    for lineno, line in enumerate(
        src.splitlines(),
        start=1,
    ):

        if re.search(
            r"\bpython(?:3)?\s+[^ ]+\.py",
            line,
        ):

            script_calls.append(
                (
                    lineno,
                    line.strip(),
                )
            )


    for lineno, line in script_calls:

        emit(
            f"PIPELINE_CALL={lineno}:{line}"
        )


    emit(
        f"PIPELINE_PYTHON_CALL_COUNT={len(script_calls)}"
    )


    called_names = []

    for _, line in script_calls:

        m = re.search(
            r"\bpython(?:3)?\s+([^\s]+\.py)",
            line,
        )

        if m:
            called_names.append(
                Path(
                    m.group(1)
                ).name
            )


    counts = Counter(
        called_names
    )


    for name, count in sorted(
        counts.items()
    ):

        if count > 1:

            status(
                "WARN",
                f"PIPELINE_DUPLICATE_CALL_{name}",
                f"count={count}",
            )


    renderers = {
        name: counts.get(
            name,
            0,
        )
        for name in (
            "video.py",
            "v4.py",
            "v5.py",
            "v6.py",
        )
    }


    emit(
        "RENDERER_CALL_COUNTS="
        +
        json.dumps(
            renderers,
            ensure_ascii=False,
        )
    )


# ============================================================
# 14 SHORT_ID RESOLUTION
# ============================================================

section(
    "14. SHORT_ID RESOLUTION AUDIT"
)

for filename in (
    "gerar_short.sh",
    "roteiro.py",
    "midia.py",
    "legenda_dinamica.py",
    "video.py",
    "v6.py",
):

    path = ROOT / filename

    if not path.is_file():
        continue

    src = text(
        path
    )

    env_count = len(
        re.findall(
            r"SHORT_ID",
            src,
        )
    )

    suspicious_latest = len(
        re.findall(
            r"latest|newest|mtime|glob\(|sorted\(",
            src,
            re.I,
        )
    )


    emit(
        f"SHORT_ID_FILE={filename} refs={env_count} "
        f"latest_like={suspicious_latest}"
    )


    if filename in {
        "midia.py",
        "video.py",
        "v6.py",
    } and env_count == 0:

        status(
            "FAIL",
            f"SHORT_ID_{filename}",
            "no SHORT_ID reference",
        )


    if suspicious_latest:

        status(
            "WARN",
            f"LATEST_RESOLUTION_{filename}",
            f"patterns={suspicious_latest}",
        )


# ============================================================
# 15 CLEANUP / DELETE RISKS
# ============================================================

section(
    "15. DELETION / CLEANUP RISK AUDIT"
)

danger_patterns = (
    r"rm\s+-rf",
    r"rmtree\(",
    r"\.unlink\(",
    r"os\.remove\(",
    r"shutil\.rmtree",
    r"glob\(.*\*",
    r"rglob\(",
)

for filename in (
    "gerar_short.sh",
    "midia.py",
    "fresh_render_guard_v1.py",
    "render_transaction_v1.py",
):

    path = ROOT / filename

    if not path.is_file():
        continue

    src = text(
        path
    )

    hits = []

    for pattern in danger_patterns:

        for match in re.finditer(
            pattern,
            src,
            re.I,
        ):

            lineno = (
                src[:match.start()].count("\n")
                +
                1
            )

            hits.append(
                (
                    lineno,
                    pattern,
                )
            )


    if hits:

        for lineno, pattern in hits[:100]:

            status(
                "WARN",
                f"DELETE_PATTERN_{filename}",
                f"line={lineno} pattern={pattern}",
            )

    else:

        status(
            "PASS",
            f"DELETE_PATTERN_{filename}",
            "none",
        )


# ============================================================
# 16 MEDIA DIRECTORY INTEGRITY
# ============================================================

section(
    "16. MEDIA DIRECTORY INTEGRITY"
)

images_root = ROOT / "imagens"

media_dirs = []

if images_root.is_dir():

    media_dirs = sorted(
        (
            p
            for p in images_root.glob(
                "short_*"
            )
            if p.is_dir()
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


for directory in media_dirs[:30]:

    scene_files = [
        p
        for p in directory.iterdir()
        if (
            p.is_file()
            and
            numbered_scene(
                p.name
            )
            is not None
        )
    ]


    numbers = [
        numbered_scene(
            p.name
        )
        for p in scene_files
    ]


    counter = Counter(
        numbers
    )


    unique = sorted(
        set(numbers)
    )


    duplicates = sorted(
        number
        for number, count
        in counter.items()
        if count > 1
    )


    missing = [
        n
        for n in range(
            1,
            13,
        )
        if n not in unique
    ]


    zero = [
        p.name
        for p in scene_files
        if p.stat().st_size == 0
    ]


    emit(
        f"MEDIA_DIR={directory.name} "
        f"FILES={len(scene_files)} "
        f"UNIQUE={len(unique)} "
        f"MISSING={missing} "
        f"DUPLICATES={duplicates} "
        f"ZERO={zero}"
    )


    if len(unique) == 12 and not duplicates and not zero:

        status(
            "PASS",
            f"MEDIA_INTEGRITY_{directory.name}",
            "12/12",
        )

    elif len(unique) == 0:

        status(
            "WARN",
            f"MEDIA_INTEGRITY_{directory.name}",
            "empty directory",
        )

    elif len(unique) < 12:

        status(
            "WARN",
            f"MEDIA_INTEGRITY_{directory.name}",
            f"incomplete {len(unique)}/12",
        )

    else:

        status(
            "WARN",
            f"MEDIA_INTEGRITY_{directory.name}",
            "unexpected structure",
        )


# ============================================================
# 17 LATEST SHORT ARTIFACT ALIGNMENT
# ============================================================

section(
    "17. SHORT ARTIFACT ALIGNMENT"
)

patterns = {

    "ROTEIRO":
        ROOT
        /
        "roteiros",

    "AUDIO":
        ROOT
        /
        "audios",

    "VIDEOS":
        ROOT
        /
        "videos",

    "TEMP":
        ROOT
        /
        "temp",

}


id_pattern = re.compile(
    r"\d{4}-\d{2}-\d{2}_\d{4}"
)


artifact_ids = defaultdict(
    set
)


for category, base in patterns.items():

    if not base.exists():
        continue

    count = 0

    for path in base.rglob("*"):

        if count > 5000:
            break

        count += 1

        m = id_pattern.search(
            path.name
        )

        if m:
            artifact_ids[
                category
            ].add(
                m.group(0)
            )


    newest = sorted(
        artifact_ids[
            category
        ]
    )[-10:]

    emit(
        f"{category}_RECENT_IDS={newest}"
    )


all_ids = set()

for ids in artifact_ids.values():
    all_ids.update(ids)


for sid in sorted(
    all_ids
)[-20:]:

    presence = {
        category:
            sid in ids
        for category, ids
        in artifact_ids.items()
    }

    emit(
        f"SHORT_ID_ALIGNMENT={sid} "
        +
        json.dumps(
            presence,
            sort_keys=True,
        )
    )


# ============================================================
# 18 FINAL VIDEO TECHNICAL VALIDATION
# ============================================================

section(
    "18. RECENT FINAL VIDEO VALIDATION"
)

videos_root = ROOT / "videos"

finals = []

if videos_root.is_dir():

    finals = sorted(
        videos_root.glob(
            "short_v6_*.mp4"
        ),
        key=lambda p:
            p.stat().st_mtime,
        reverse=True,
    )


for path in finals[:10]:

    size = path.stat().st_size

    probe = ffprobe_ok(
        path
    )

    emit(
        f"FINAL_VIDEO={path.name} "
        f"BYTES={size} "
        f"FFPROBE={probe}"
    )


    if size <= 10000:

        status(
            "FAIL",
            f"FINAL_VIDEO_{path.name}",
            "file too small",
        )

    elif probe is False:

        status(
            "FAIL",
            f"FINAL_VIDEO_{path.name}",
            "ffprobe failed",
        )

    else:

        status(
            "PASS",
            f"FINAL_VIDEO_{path.name}",
            f"bytes={size}",
        )


# ============================================================
# 19 COMMIT LOCK
# ============================================================

section(
    "19. SCENE COMMIT LOCK AUDIT"
)

commit = ROOT / "visual_scene_commit_lock_v1.py"

if commit.is_file():

    src = text(
        commit
    )

    checks = {

        "READY":
            "SCENE_COMMIT_LOCK" in src,

        "BLOCKED":
            "BLOCKED" in src,

        "COMMITTED":
            "COMMITTED" in src,

        "DISABLE_FLAG":
            "SAP_SCENE_COMMIT_LOCK" in src,
    }


    for key, ok in checks.items():

        status(
            "PASS" if ok else "WARN",
            f"COMMIT_LOCK_{key}",
            str(ok),
        )


# ============================================================
# 20 PROVENANCE
# ============================================================

section(
    "20. PROVENANCE / MANIFEST AUDIT"
)

manifest_root = ROOT / "manifests"

if manifest_root.is_dir():

    json_files = list(
        manifest_root.rglob(
            "*.json"
        )
    )

    emit(
        f"MANIFEST_JSON_COUNT={len(json_files)}"
    )

    broken_json = []

    for path in json_files[:3000]:

        try:
            json.loads(
                text(path)
            )
        except Exception:
            broken_json.append(
                str(
                    path.relative_to(
                        ROOT
                    )
                )
            )


    if broken_json:

        for name in broken_json[:100]:

            status(
                "WARN",
                "BROKEN_MANIFEST_JSON",
                name,
            )

    else:

        status(
            "PASS",
            "MANIFEST_JSON_PARSE",
            "all scanned files valid",
        )


# ============================================================
# 21 BACKUP DUPLICATION / CLUTTER
# ============================================================

section(
    "21. BACKUP CLUTTER"
)

backups_root = ROOT / "backups"

if backups_root.is_dir():

    backup_dirs = [
        p
        for p in backups_root.iterdir()
        if p.is_dir()
    ]

    emit(
        f"BACKUP_DIRECTORY_COUNT={len(backup_dirs)}"
    )

    if len(
        backup_dirs
    ) > 100:

        status(
            "WARN",
            "BACKUP_DIRECTORY_COUNT",
            str(
                len(
                    backup_dirs
                )
            ),
        )

    else:

        status(
            "PASS",
            "BACKUP_DIRECTORY_COUNT",
            str(
                len(
                    backup_dirs
                )
            ),
        )


# ============================================================
# 22 VSE4 HARD MISMATCH REGRESSION
# ============================================================

section(
    "22. VSE4 GEO / HARD-MISMATCH REGRESSION"
)

if vse.is_file():

    code = r'''
import runpy

ns = runpy.run_path(
    "visual_selection_engine_v4.py",
    run_name="audit_vse4",
)

score = ns["score_candidate"]

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

a = score(
    wrong,
    scene,
    state,
)

b = score(
    correct,
    scene,
    state,
)

print(
    "WRONG_HARD_MISMATCH=",
    a.get("hard_mismatch"),
)

print(
    "CORRECT_HARD_MISMATCH=",
    b.get("hard_mismatch"),
)

print(
    "WRONG_EFFECTIVE=",
    a.get("effective"),
)

print(
    "CORRECT_EFFECTIVE=",
    b.get("effective"),
)

if (
    a.get("hard_mismatch") is True
    and
    b.get("hard_mismatch") is False
    and
    b.get("effective", -999999)
    >
    a.get("effective", 999999)
):
    print("VSE4_GEO_REGRESSION=PASS")
else:
    print("VSE4_GEO_REGRESSION=FAIL")
    raise SystemExit(1)
'''

    try:

        r = subprocess.run(
            [
                sys.executable,
                "-c",
                code,
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )


        emit(
            r.stdout
        )

        if r.stderr:
            emit(
                r.stderr
            )


        if r.returncode == 0:

            status(
                "PASS",
                "VSE4_GEO_REGRESSION",
                "São Paulo != New York",
            )

        else:

            status(
                "FAIL",
                "VSE4_GEO_REGRESSION",
                f"status={r.returncode}",
            )


    except Exception as exc:

        status(
            "FAIL",
            "VSE4_GEO_REGRESSION",
            str(exc),
        )


# ============================================================
# 23 SUSPICIOUS PASS / EMPTY HASH BUGS
# ============================================================

section(
    "23. CERTIFICATION LOGIC RISKS"
)

cert_files = (
    "render_output_certifier_v1.py",
    "render_transaction_v1.py",
    "fresh_render_guard_v1.py",
)

for filename in cert_files:

    path = ROOT / filename

    if not path.is_file():
        continue

    src = text(
        path
    )


    empty_compare = bool(
        re.search(
            r'==\s*["\']{2}',
            src,
        )
    )


    if empty_compare:

        status(
            "WARN",
            f"EMPTY_VALUE_LOGIC_{filename}",
            "manual review recommended",
        )

    else:

        status(
            "PASS",
            f"EMPTY_VALUE_LOGIC_{filename}",
            "no obvious empty-string compare",
        )


# ============================================================
# 24 FILE SIZE OUTLIERS
# ============================================================

section(
    "24. CORE FILE SIZE OUTLIERS"
)

for filename in (
    "midia.py",
    "visual_selection_engine_v4.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
):

    path = ROOT / filename

    if not path.is_file():
        continue

    size = path.stat().st_size

    lines = len(
        text(path).splitlines()
    )

    emit(
        f"CORE_SIZE={filename} "
        f"BYTES={size} "
        f"LINES={lines}"
    )


    if filename.endswith(
        ".py"
    ) and lines > 7000:

        status(
            "WARN",
            f"LARGE_CORE_FILE_{filename}",
            f"{lines} lines",
        )


# ============================================================
# SUMMARY
# ============================================================

section(
    "MASTER AUDIT SUMMARY"
)

emit(
    f"PASS_COUNT={len(PASS)}"
)

emit(
    f"WARN_COUNT={len(WARN)}"
)

emit(
    f"FAIL_COUNT={len(FAIL)}"
)


if FAIL:

    emit(
        "OVERALL_STATUS=FAIL"
    )

elif WARN:

    emit(
        "OVERALL_STATUS=PASS_WITH_WARNINGS"
    )

else:

    emit(
        "OVERALL_STATUS=PASS"
    )


emit()
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
    "PIPELINE_EXECUTED=NO"
)

emit(
    "SECRETS_PRINTED=NO"
)

emit(
    "SOURCE_FILES_MODIFIED=NO"
)


section(
    "FAILURES"
)

if FAIL:

    for item in FAIL:

        emit(
            f"FAIL={item['key']} | "
            f"{item['detail']}"
        )

else:

    emit(
        "FAILURES=NONE"
    )


section(
    "WARNINGS"
)

if WARN:

    for item in WARN:

        emit(
            f"WARN={item['key']} | "
            f"{item['detail']}"
        )

else:

    emit(
        "WARNINGS=NONE"
    )


payload = {

    "generated_at":
        time.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

    "pass":
        PASS,

    "warn":
        WARN,

    "fail":
        FAIL,

    "info":
        INFO,
}


JSON_REPORT.write_text(
    json.dumps(
        payload,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


emit()
emit(
    f"REPORT={REPORT}"
)

emit(
    f"JSON_REPORT={JSON_REPORT}"
)

emit(
    "MASTER_AUDIT_COMPLETE=YES"
)

emit(
    "TERMUX_CONTINUA_ABERTO=SIM"
)


REPORT_HANDLE.flush()
REPORT_HANDLE.close()

sys.stdout = original_stdout
