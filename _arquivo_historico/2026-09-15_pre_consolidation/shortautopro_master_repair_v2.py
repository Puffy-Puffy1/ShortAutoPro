#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time


ROOT = Path.home() / "ShortAutoPro"
STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

BACKUP = (
    ROOT
    / "backups"
    / f"MASTER_REPAIR_V2_{STAMP}"
)

REPORT = (
    ROOT
    / "temp"
    / f"MASTER_REPAIR_V2_{STAMP}.txt"
)

BACKUP.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


APPLY = (
    "--audit-only"
    not in sys.argv
)


MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
    ".mkv",
}


EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    "backups",
    "temp",
    "logs",
    ".venv",
    "venv",
    "node_modules",
}


NON_RUNTIME_NAME_PARTS = {
    "audit",
    "repair",
    "regression",
    "backup",
    "forensic",
    "diagnostic",
    "benchmark",
    "probe",
}


rows = []
failures = []
warnings = []
repairs = []


def log(*parts):

    text = " ".join(
        str(x)
        for x in parts
    )

    print(
        text,
        flush=True,
    )

    rows.append(
        text
    )


def pass_item(name, detail=""):

    log(
        "PASS |",
        name,
        "|",
        detail,
    )


def warn_item(name, detail=""):

    warnings.append(
        (
            name,
            detail,
        )
    )

    log(
        "WARN |",
        name,
        "|",
        detail,
    )


def fail_item(name, detail=""):

    failures.append(
        (
            name,
            detail,
        )
    )

    log(
        "FAIL |",
        name,
        "|",
        detail,
    )


def repair_item(name, detail=""):

    repairs.append(
        (
            name,
            detail,
        )
    )

    log(
        "REPAIR |",
        name,
        "|",
        detail,
    )


def sha256(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


def runtime_file(path):

    try:
        rel = path.relative_to(
            ROOT
        )
    except ValueError:
        return False

    if any(
        part in EXCLUDED_DIRS
        for part in rel.parts
    ):
        return False

    lower = path.name.casefold()

    if any(
        token in lower
        for token in NON_RUNTIME_NAME_PARTS
    ):
        return False

    return True


def command(
    args,
    timeout=120,
):

    try:

        result = subprocess.run(
            args,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return (
            result.returncode,
            result.stdout,
            result.stderr,
        )

    except Exception as exc:

        return (
            999,
            "",
            f"{type(exc).__name__}: {exc}",
        )


def scene_number(path):

    match = re.fullmatch(
        r"scene_(\d{1,2})"
        r"\.(jpg|jpeg|png|webp|mp4|mov|webm|mkv)",
        path.name,
        re.I,
    )

    if not match:
        return None

    n = int(
        match.group(1)
    )

    if 1 <= n <= 12:
        return n

    return None


def media_map(sid):

    directory = (
        ROOT
        / "imagens"
        / f"short_{sid}"
    )

    result = {
        n: []
        for n in range(
            1,
            13,
        )
    }

    if not directory.is_dir():
        return result

    for path in directory.iterdir():

        if not path.is_file():
            continue

        if (
            path.suffix.casefold()
            not in MEDIA_EXTENSIONS
        ):
            continue

        n = scene_number(
            path
        )

        if n is None:
            continue

        result[
            n
        ].append(
            path
        )

    return result


def media_score(sid):

    mapping = media_map(
        sid
    )

    exact = sum(
        len(v) == 1
        for v in mapping.values()
    )

    total = sum(
        len(v)
        for v in mapping.values()
    )

    complete = (
        exact == 12
        and
        total == 12
    )

    directory = (
        ROOT
        / "imagens"
        / f"short_{sid}"
    )

    try:
        mtime = directory.stat().st_mtime
    except Exception:
        mtime = 0

    return (
        complete,
        exact,
        total,
        mtime,
    )


def discover_short_ids():

    ids = set()

    images = (
        ROOT
        / "imagens"
    )

    if images.is_dir():

        for directory in images.glob(
            "short_*"
        ):

            if directory.is_dir():

                sid = directory.name[
                    len("short_"):
                ]

                if sid:
                    ids.add(
                        sid
                    )

    for folder, pattern, prefix in (
        (
            ROOT / "videos",
            "short_v6_*.mp4",
            "short_v6_",
        ),
        (
            ROOT / "audios",
            "short_*.mp3",
            "short_",
        ),
        (
            ROOT / "roteiros",
            "short_*.txt",
            "short_",
        ),
    ):

        if not folder.is_dir():
            continue

        for path in folder.glob(
            pattern
        ):

            name = path.stem

            if name.startswith(
                prefix
            ):

                ids.add(
                    name[
                        len(prefix):
                    ]
                )

    return sorted(
        ids
    )


def resolve_short_id():

    env_sid = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    ids = discover_short_ids()

    if env_sid:

        score = media_score(
            env_sid
        )

        if score[0]:

            return (
                env_sid,
                "ENV_COMPLETE",
            )

    ranked = []

    for sid in ids:

        complete, exact, total, mtime = media_score(
            sid
        )

        ranked.append(
            (
                int(complete),
                exact,
                -abs(
                    total - 12
                ),
                mtime,
                sid,
            )
        )

    if ranked:

        ranked.sort(
            reverse=True
        )

        return (
            ranked[0][-1],
            "AUTO_RESOLVED",
        )

    if env_sid:

        return (
            env_sid,
            "ENV_FALLBACK",
        )

    return (
        "",
        "NOT_FOUND",
    )


def backup_file(path):

    if not path.exists():
        return

    try:
        rel = path.relative_to(
            ROOT
        )
    except Exception:
        return

    dest = (
        BACKUP
        / "files"
        / rel
    )

    dest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        dest,
    )


def choose_scene_winner(paths):

    # O arquivo mais recentemente gravado normalmente
    # representa a última decisão do pipeline.
    # O tamanho serve apenas como desempate.

    return max(
        paths,
        key=lambda p: (
            p.stat().st_mtime,
            p.stat().st_size,
        ),
    )


def repair_cardinality(sid):

    directory = (
        ROOT
        / "imagens"
        / f"short_{sid}"
    )

    if not directory.is_dir():

        fail_item(
            "MEDIA_DIRECTORY",
            str(directory),
        )

        return False


    quarantine = (
        BACKUP
        / "media_quarantine"
        / f"short_{sid}"
    )

    mapping = media_map(
        sid
    )


    for n in range(
        1,
        13,
    ):

        paths = mapping[
            n
        ]

        if not paths:

            fail_item(
                "SCENE_MISSING",
                f"scene_{n:02d}",
            )

            continue


        winner = choose_scene_winner(
            paths
        )


        # --------------------------------------------
        # DUPLICATES
        # --------------------------------------------

        if len(paths) > 1:

            if APPLY:

                quarantine.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                for path in paths:

                    if path == winner:
                        continue

                    dest = (
                        quarantine
                        / path.name
                    )

                    index = 1

                    while dest.exists():

                        dest = (
                            quarantine
                            /
                            f"{path.stem}"
                            f"_dup{index}"
                            f"{path.suffix}"
                        )

                        index += 1

                    shutil.move(
                        str(path),
                        str(dest),
                    )

                    repair_item(
                        "MEDIA_DUPLICATE_QUARANTINED",
                        f"{path.name} -> {dest.name}",
                    )

            else:

                warn_item(
                    "MEDIA_DUPLICATE",
                    ", ".join(
                        p.name
                        for p in paths
                    ),
                )


        # --------------------------------------------
        # NORMALIZE PADDED NAME
        # --------------------------------------------

        canonical = (
            directory
            /
            f"scene_{n:02d}"
            f"{winner.suffix.casefold()}"
        )

        if winner.name != canonical.name:

            if APPLY:

                backup_file(
                    winner
                )

                if canonical.exists():

                    quarantine.mkdir(
                        parents=True,
                        exist_ok=True,
                    )

                    displaced = (
                        quarantine
                        /
                        (
                            canonical.stem
                            +
                            "_preexisting"
                            +
                            canonical.suffix
                        )
                    )

                    shutil.move(
                        str(canonical),
                        str(displaced),
                    )

                winner.rename(
                    canonical
                )

                repair_item(
                    "MEDIA_NAME_NORMALIZED",
                    f"{winner.name} -> {canonical.name}",
                )


    # Recheck.
    after = media_map(
        sid
    )

    invalid = [
        n
        for n, paths in after.items()
        if len(paths) != 1
    ]

    total = sum(
        len(x)
        for x in after.values()
    )

    if not invalid and total == 12:

        pass_item(
            "MEDIA_SCENE_CARDINALITY",
            "12/12 exatamente uma mídia por cena",
        )

        return True


    fail_item(
        "MEDIA_SCENE_CARDINALITY",
        "invalid="
        +
        ",".join(
            f"{x:02d}"
            for x in invalid
        )
        +
        f" total={total}",
    )

    return False


def archive_old_error_logs():

    source = (
        ROOT
        / "logs"
        / "producao"
    )

    if not source.is_dir():
        return


    archive = (
        source
        / "archive_old_errors"
        / STAMP
    )

    now = time.time()

    archived = 0


    for path in source.glob(
        "*.log"
    ):

        try:

            age_hours = (
                now
                -
                path.stat().st_mtime
            ) / 3600

        except Exception:
            continue


        # Somente histórico antigo.
        if age_hours < 48:
            continue


        try:

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).casefold()

        except Exception:
            continue


        indicators = (
            "traceback",
            "error:",
            "erro:",
            "exception",
            "failed",
            "falhou",
        )


        if not any(
            x in text
            for x in indicators
        ):
            continue


        if APPLY:

            archive.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.move(
                str(path),
                str(
                    archive
                    / path.name
                ),
            )

        archived += 1


    if archived:

        repair_item(
            "OLD_ERROR_LOGS_ARCHIVED",
            archived,
        )

    else:

        pass_item(
            "OLD_ERROR_LOGS",
            "nenhum para arquivar",
        )


def compile_python():

    failed = []
    checked = 0


    for path in sorted(
        ROOT.glob(
            "*.py"
        )
    ):

        if not runtime_file(
            path
        ):
            continue

        checked += 1

        code, out, err = command(
            [
                sys.executable,
                "-m",
                "py_compile",
                str(path),
            ],
            timeout=60,
        )

        if code != 0:

            failed.append(
                (
                    path.name,
                    (
                        err.strip()
                        or
                        out.strip()
                    )[-1000:],
                )
            )


    if failed:

        for name, detail in failed:

            fail_item(
                "PYTHON_COMPILE",
                f"{name}: {detail}",
            )

    else:

        pass_item(
            "PYTHON_COMPILE",
            f"{checked} arquivos",
        )


def shell_syntax():

    failed = []
    checked = 0


    for path in sorted(
        ROOT.glob(
            "*.sh"
        )
    ):

        if not runtime_file(
            path
        ):
            continue

        checked += 1

        code, out, err = command(
            [
                "bash",
                "-n",
                str(path),
            ]
        )

        if code != 0:

            failed.append(
                (
                    path.name,
                    err.strip(),
                )
            )


    if failed:

        for name, detail in failed:

            fail_item(
                "SHELL_SYNTAX",
                f"{name}: {detail}",
            )

    else:

        pass_item(
            "SHELL_SYNTAX",
            f"{checked} scripts",
        )


def duplicate_top_level_defs():

    problems = []


    for path in sorted(
        ROOT.glob(
            "*.py"
        )
    ):

        if not runtime_file(
            path
        ):
            continue


        try:

            tree = ast.parse(
                path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )

        except Exception:
            continue


        names = {}


        for node in tree.body:

            if isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):

                names.setdefault(
                    node.name,
                    [],
                ).append(
                    node.lineno
                )


        for name, lines in names.items():

            if len(lines) > 1:

                problems.append(
                    (
                        path.name,
                        name,
                        lines,
                    )
                )


    if problems:

        for file, name, lines in problems:

            warn_item(
                "TOPLEVEL_DUPLICATE_DEFINITION",
                f"{file}:{name} lines={lines}",
            )

    else:

        pass_item(
            "TOPLEVEL_DUPLICATE_DEFINITIONS",
            "0",
        )


def hardcoded_ids():

    regex = re.compile(
        r"\b20\d{2}-\d{2}-\d{2}_\d{4}\b"
    )

    hits = []


    for path in list(
        ROOT.glob(
            "*.py"
        )
    ) + list(
        ROOT.glob(
            "*.sh"
        )
    ):

        if not runtime_file(
            path
        ):
            continue


        try:

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

        except Exception:
            continue


        for i, line in enumerate(
            text.splitlines(),
            start=1,
        ):

            if regex.search(
                line
            ):

                hits.append(
                    (
                        path.name,
                        i,
                        line.strip()[:180],
                    )
                )


    if hits:

        for file, line, source in hits:

            warn_item(
                "RUNTIME_HARDCODED_SHORT_ID",
                f"{file}:{line}: {source}",
            )

    else:

        pass_item(
            "RUNTIME_HARDCODED_SHORT_IDS",
            "0",
        )


def network_timeout_audit():

    actual = []


    for path in sorted(
        ROOT.glob(
            "*.py"
        )
    ):

        if not runtime_file(
            path
        ):
            continue


        try:

            source = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            tree = ast.parse(
                source
            )

        except Exception:
            continue


        requests_names = set()
        session_names = set()


        for node in tree.body:

            if isinstance(
                node,
                ast.Import,
            ):

                for alias in node.names:

                    if alias.name == "requests":

                        requests_names.add(
                            alias.asname
                            or
                            "requests"
                        )


            elif isinstance(
                node,
                ast.Assign,
            ):

                if not isinstance(
                    node.value,
                    ast.Call,
                ):
                    continue


                func = node.value.func


                if (
                    isinstance(
                        func,
                        ast.Attribute,
                    )
                    and
                    func.attr == "Session"
                    and
                    isinstance(
                        func.value,
                        ast.Name,
                    )
                    and
                    func.value.id
                    in requests_names
                ):

                    for target in node.targets:

                        if isinstance(
                            target,
                            ast.Name,
                        ):

                            session_names.add(
                                target.id
                            )


        for node in ast.walk(
            tree
        ):

            if not isinstance(
                node,
                ast.Call,
            ):
                continue

            if not isinstance(
                node.func,
                ast.Attribute,
            ):
                continue


            method = node.func.attr


            if method not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "request",
                "head",
            }:
                continue


            owner = node.func.value

            is_network = False


            if (
                isinstance(
                    owner,
                    ast.Name,
                )
                and
                owner.id
                in requests_names
            ):

                is_network = True


            if (
                isinstance(
                    owner,
                    ast.Name,
                )
                and
                owner.id
                in session_names
            ):

                is_network = True


            if not is_network:
                continue


            has_timeout = any(
                kw.arg == "timeout"
                for kw in node.keywords
            )


            if not has_timeout:

                actual.append(
                    (
                        path.name,
                        node.lineno,
                        method,
                    )
                )


    if actual:

        for item in actual:

            warn_item(
                "REAL_NETWORK_CALL_WITHOUT_TIMEOUT",
                f"{item[0]}:{item[1]} .{item[2]}()",
            )

    else:

        pass_item(
            "NETWORK_TIMEOUT_AUDIT",
            "0 chamadas reais sem timeout",
        )


def dangerous_runtime_patterns():

    results = []


    patterns = (
        (
            "RM_RF_ROOT",
            re.compile(
                r"rm\s+-rf\s+[/\"']*(?:\s|$)"
            ),
        ),
        (
            "SHUTIL_RMTREE_ROOT",
            re.compile(
                r"shutil\.rmtree\(\s*[\"']/[\"']"
            ),
        ),
        (
            "OS_REMOVE_ROOT",
            re.compile(
                r"os\.remove\(\s*[\"']/[\"']"
            ),
        ),
    )


    for path in list(
        ROOT.glob(
            "*.py"
        )
    ) + list(
        ROOT.glob(
            "*.sh"
        )
    ):

        if not runtime_file(
            path
        ):
            continue


        try:

            lines = path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()

        except Exception:
            continue


        for lineno, line in enumerate(
            lines,
            start=1,
        ):

            for name, regex in patterns:

                if regex.search(
                    line
                ):

                    results.append(
                        (
                            name,
                            path.name,
                            lineno,
                            line.strip()[:180],
                        )
                    )


    if results:

        for x in results:

            fail_item(
                x[0],
                f"{x[1]}:{x[2]} {x[3]}",
            )

    else:

        pass_item(
            "DANGEROUS_ROOT_DELETE_PATTERNS",
            "0",
        )


def vse4_test():

    path = (
        ROOT
        / "visual_selection_engine_v4.py"
    )

    if not path.is_file():

        warn_item(
            "VSE4_SELF_TEST",
            "arquivo ausente",
        )

        return


    code, out, err = command(
        [
            sys.executable,
            str(path),
        ],
        timeout=120,
    )


    output = (
        out
        +
        "\n"
        +
        err
    )


    if code == 0:

        pass_item(
            "VSE4_SELF_TEST",
            "status=0",
        )

    else:

        fail_item(
            "VSE4_SELF_TEST",
            output[-2500:],
        )


def final_video_health():

    videos = (
        ROOT
        / "videos"
    )

    finals = list(
        videos.glob(
            "short_v6_*.mp4"
        )
    ) if videos.is_dir() else []


    if not finals:

        warn_item(
            "FINAL_VIDEO_HEALTH",
            "nenhum short_v6 encontrado",
        )

        return


    latest = max(
        finals,
        key=lambda p:
            p.stat().st_mtime,
    )


    code, out, err = command(
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
            str(latest),
        ],
        timeout=60,
    )


    if code != 0:

        fail_item(
            "FINAL_VIDEO_HEALTH",
            err[-1000:],
        )

        return


    try:

        data = json.loads(
            out
        )

        duration = float(
            data[
                "format"
            ][
                "duration"
            ]
        )

        video_stream = next(
            x
            for x in data[
                "streams"
            ]
            if x.get(
                "codec_type"
            )
            ==
            "video"
        )

        width = int(
            video_stream.get(
                "width",
                0,
            )
        )

        height = int(
            video_stream.get(
                "height",
                0,
            )
        )

    except Exception as exc:

        fail_item(
            "FINAL_VIDEO_HEALTH",
            f"parse: {exc}",
        )

        return


    digest = sha256(
        latest
    )


    if (
        width == 1080
        and
        height == 1920
        and
        duration > 1
    ):

        pass_item(
            "FINAL_VIDEO_HEALTH",
            (
                f"{latest.name} "
                f"{width}x{height} "
                f"{duration:.2f}s "
                f"sha256={digest}"
            ),
        )

    else:

        fail_item(
            "FINAL_VIDEO_HEALTH",
            (
                f"{width}x{height} "
                f"{duration:.2f}s"
            ),
        )


def recent_runtime_errors():

    directory = (
        ROOT
        / "logs"
        / "producao"
    )

    if not directory.is_dir():

        pass_item(
            "RECENT_RUNTIME_ERRORS",
            "sem logs",
        )

        return


    now = time.time()

    hits = []


    for path in directory.glob(
        "*.log"
    ):

        try:

            age = (
                now
                -
                path.stat().st_mtime
            ) / 3600

        except Exception:
            continue


        # Só consideramos realmente recente.
        if age > 24:
            continue


        try:

            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

        except Exception:
            continue


        matched = []

        for line in text.splitlines():

            lower = line.casefold()

            if any(
                token in lower
                for token in (
                    "traceback",
                    "erro:",
                    "error:",
                    "exception",
                    "failed",
                    "falhou",
                )
            ):

                matched.append(
                    line.strip()[:200]
                )


        if matched:

            hits.append(
                (
                    path.name,
                    matched[-3:],
                )
            )


    if hits:

        for name, lines in hits:

            warn_item(
                "RECENT_RUNTIME_LOG_ERROR",
                f"{name}: {' | '.join(lines)}",
            )

    else:

        pass_item(
            "RECENT_RUNTIME_ERRORS",
            "0 nas últimas 24h",
        )


def save_report():

    REPORT.write_text(
        "\n".join(
            rows
        )
        +
        "\n",
        encoding="utf-8",
    )


def main():

    log(
        "=" * 72
    )

    log(
        " SHORTAUTOPRO MASTER REPAIR + AUDIT V2"
    )

    log(
        "=" * 72
    )

    log(
        f"MODE={'APPLY' if APPLY else 'AUDIT_ONLY'}"
    )

    log(
        f"BACKUP={BACKUP}"
    )

    log()


    # --------------------------------------------------------
    # CORE BACKUPS
    # --------------------------------------------------------

    for name in (
        "midia.py",
        "video.py",
        "v6.py",
        "gerar_short.sh",
        "visual_selection_engine_v4.py",
        "visual_engine_unified.py",
        "visual_pipeline_bridge_v42.py",
        "visual_quality_runtime_v5.py",
        "visual_scene_commit_lock_v1.py",
    ):

        backup_file(
            ROOT
            / name
        )


    sid, source = resolve_short_id()

    log(
        f"ACTIVE_SHORT_ID={sid or 'NONE'}"
    )

    log(
        f"SHORT_ID_SOURCE={source}"
    )


    if sid:

        active_file = (
            ROOT
            / "temp"
            / "active_short_id.txt"
        )

        if APPLY:

            active_file.write_text(
                sid + "\n",
                encoding="utf-8",
            )

        repair_cardinality(
            sid
        )

    else:

        fail_item(
            "SHORT_ID_RESOLUTION",
            "nenhum ID encontrado",
        )


    archive_old_error_logs()


    log()
    log(
        "=" * 72
    )
    log(
        " STATIC + RUNTIME SAFETY"
    )
    log(
        "=" * 72
    )


    compile_python()
    shell_syntax()
    duplicate_top_level_defs()
    hardcoded_ids()
    network_timeout_audit()
    dangerous_runtime_patterns()


    log()
    log(
        "=" * 72
    )
    log(
        " ENGINE + OUTPUT"
    )
    log(
        "=" * 72
    )


    vse4_test()
    recent_runtime_errors()
    final_video_health()


    log()
    log(
        "=" * 72
    )
    log(
        " CORE HASHES"
    )
    log(
        "=" * 72
    )


    for name in (
        "midia.py",
        "video.py",
        "v6.py",
        "gerar_short.sh",
        "visual_selection_engine_v4.py",
    ):

        path = (
            ROOT
            / name
        )

        if path.is_file():

            log(
                f"SHA256_{name}="
                f"{sha256(path)}"
            )


    log()
    log(
        "=" * 72
    )
    log(
        " FINAL SUMMARY"
    )
    log(
        "=" * 72
    )


    log(
        f"TOTAL_REPAIRS={len(repairs)}"
    )

    log(
        f"TOTAL_WARN={len(warnings)}"
    )

    log(
        f"TOTAL_FAIL={len(failures)}"
    )


    if failures:

        log()
        log(
            "----- REAL FAILURES -----"
        )

        for name, detail in failures:

            log(
                "FAIL |",
                name,
                "|",
                detail,
            )


    if warnings:

        log()
        log(
            "----- WARNINGS / REVIEW -----"
        )

        for name, detail in warnings:

            log(
                "WARN |",
                name,
                "|",
                detail,
            )


    if failures:

        status = "FAIL"

    elif warnings:

        status = "PASS_WITH_WARNINGS"

    else:

        status = "PASS"


    log()
    log(
        f"MASTER_STATUS={status}"
    )

    log(
        "NETWORK_DOWNLOAD_EXECUTED=NO"
    )

    log(
        "MEDIA_SELECTION_EXECUTED=NO"
    )

    log(
        "VIDEO_RENDER_EXECUTED=NO"
    )

    log(
        f"PROJECT_REPAIR_APPLIED={'YES' if APPLY else 'NO'}"
    )

    log(
        "TERMUX_CONTINUA_ABERTO=SIM"
    )


    save_report()

    print()
    print(
        f"REPORT={REPORT}"
    )


if __name__ == "__main__":
    main()
