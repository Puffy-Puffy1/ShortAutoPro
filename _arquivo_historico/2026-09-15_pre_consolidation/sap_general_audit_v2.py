#!/usr/bin/env python3

from pathlib import Path
from collections import Counter
import ast
import builtins
import datetime
import hashlib
import os
import re
import shutil
import subprocess
import symtable
import sys
import traceback


ROOT = Path.cwd()
TEMP = ROOT / "temp"
TEMP.mkdir(parents=True, exist_ok=True)

STAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
REPORT = TEMP / f"GENERAL_AUDIT_V2_{STAMP}.txt"

PASS_COUNT = 0
WARN_COUNT = 0
FAIL_COUNT = 0

WARNINGS = []
FAILURES = []


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)
            stream.flush()

    def flush(self):
        for stream in self.streams:
            stream.flush()


report_handle = REPORT.open(
    "w",
    encoding="utf-8",
)

sys.stdout = Tee(
    sys.__stdout__,
    report_handle,
)

sys.stderr = Tee(
    sys.__stderr__,
    report_handle,
)


def section(title):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def passed(message):
    global PASS_COUNT
    PASS_COUNT += 1
    print(f"PASS | {message}")


def warn(message):
    global WARN_COUNT
    WARN_COUNT += 1
    WARNINGS.append(message)
    print(f"WARN | {message}")


def fail(message):
    global FAIL_COUNT
    FAIL_COUNT += 1
    FAILURES.append(message)
    print(f"FAIL | {message}")


def sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def run(cmd, timeout=30):
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )

        return (
            result.returncode,
            result.stdout or "",
        )

    except subprocess.TimeoutExpired as exc:
        return (
            124,
            f"TIMEOUT: {exc}",
        )

    except Exception as exc:
        return (
            125,
            f"{type(exc).__name__}: {exc}",
        )


def project_files(suffix):
    ignored = (
        "/backups/",
        "/temp/",
        "/.git/",
        "/__pycache__/",
    )

    result = []

    for path in ROOT.rglob(f"*{suffix}"):

        text = "/" + str(
            path.relative_to(ROOT)
        ).replace("\\", "/")

        if any(
            marker in text
            for marker in ignored
        ):
            continue

        if path.is_file():
            result.append(path)

    return sorted(result)


def find_active_short_id():

    env_id = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if env_id:
        return env_id, "ENV"

    base = ROOT / "imagens"

    if not base.exists():
        return "", "NONE"

    dirs = [
        p
        for p in base.glob("short_*")
        if p.is_dir()
    ]

    if not dirs:
        return "", "NONE"

    latest = max(
        dirs,
        key=lambda p: p.stat().st_mtime,
    )

    return (
        latest.name.removeprefix("short_"),
        "LATEST_MEDIA_DIR",
    )


section("0. GENERAL AUDIT START")

print(
    "DATE=",
    datetime.datetime.now().isoformat(
        timespec="seconds"
    ),
)

print(f"ROOT={ROOT}")
print(f"REPORT={REPORT}")

if ROOT.name == "ShortAutoPro":
    passed("diretório do projeto reconhecido")
else:
    warn(
        "diretório atual não se chama ShortAutoPro"
    )


# ============================================================
# 1. CORE FILES
# ============================================================

section("1. CORE FILE PRESENCE")

core_files = [
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_selection_engine_v4.py",
]

for name in core_files:

    path = ROOT / name

    if path.is_file() and path.stat().st_size > 0:
        print(
            f"CORE=PASS "
            f"bytes={path.stat().st_size} "
            f"file={name}"
        )
    else:
        fail(
            f"arquivo core ausente/vazio: {name}"
        )

if all(
    (ROOT / name).is_file()
    for name in core_files
):
    passed("arquivos core principais presentes")


# ============================================================
# 2. PYTHON AST
# ============================================================

section("2. PYTHON SYNTAX - ENTIRE ACTIVE TREE")

py_files = project_files(".py")

py_bad = []

for path in py_files:

    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        ast.parse(
            source,
            filename=str(path),
        )

    except SyntaxError as exc:

        py_bad.append(
            (
                path,
                exc.lineno,
                exc.msg,
            )
        )

    except Exception as exc:

        py_bad.append(
            (
                path,
                0,
                f"{type(exc).__name__}: {exc}",
            )
        )


print(
    f"PYTHON_FILES_CHECKED={len(py_files)}"
)

print(
    f"PYTHON_SYNTAX_FAILURES={len(py_bad)}"
)

for path, line, msg in py_bad[:100]:

    print(
        f"PYTHON_FAIL "
        f"file={path.relative_to(ROOT)} "
        f"line={line} "
        f"error={msg}"
    )


if py_bad:
    fail(
        f"{len(py_bad)} arquivo(s) Python com erro de sintaxe"
    )
else:
    passed(
        f"{len(py_files)} arquivos Python passaram no AST"
    )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section("3. SHELL SCRIPT SYNTAX")

sh_files = project_files(".sh")

shell_bad = []

for path in sh_files:

    status, output = run(
        [
            "bash",
            "-n",
            str(path),
        ],
        timeout=15,
    )

    if status != 0:
        shell_bad.append(
            (
                path,
                output.strip(),
            )
        )


print(
    f"SHELL_FILES_CHECKED={len(sh_files)}"
)

print(
    f"SHELL_SYNTAX_FAILURES={len(shell_bad)}"
)


for path, output in shell_bad[:100]:

    print(
        f"SHELL_FAIL "
        f"file={path.relative_to(ROOT)}"
    )

    print(
        output[:1500]
    )


if shell_bad:
    fail(
        f"{len(shell_bad)} script(s) shell inválidos"
    )
else:
    passed(
        f"{len(sh_files)} scripts shell passaram no bash -n"
    )


# ============================================================
# 4. DUPLICATE DEFINITIONS
# ============================================================

section("4. DUPLICATE TOP-LEVEL DEFINITIONS")

duplicate_targets = [
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
]

duplicate_total = 0


for filename in duplicate_targets:

    path = ROOT / filename

    if not path.is_file():
        continue

    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception:
        continue


    names = []

    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            names.append(
                node.name
            )


    duplicates = {
        name: count
        for name, count in Counter(
            names
        ).items()
        if count > 1
    }


    if duplicates:

        duplicate_total += len(
            duplicates
        )

        print(
            f"DUPLICATES file={filename} "
            f"values={duplicates}"
        )

    else:

        print(
            f"DUPLICATES file={filename} NONE"
        )


if duplicate_total:
    warn(
        f"{duplicate_total} definição(ões) top-level duplicadas; revisar shadowing"
    )
else:
    passed(
        "sem funções/classes top-level duplicadas nos cores"
    )


# ============================================================
# 5. VSE4 STATIC HEALTH
# ============================================================

section("5. VSE4 STATIC HEALTH")

vse = ROOT / "visual_selection_engine_v4.py"

if vse.is_file():

    vse_source = vse.read_text(
        encoding="utf-8",
        errors="replace",
    )

    try:

        table = symtable.symtable(
            vse_source,
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

                    if name in defined:
                        continue

                    if name in builtins_set:
                        continue

                    unresolved.add(name)

                walk(child)


        walk(table)


        if unresolved:

            print(
                "VSE4_UNRESOLVED_GLOBALS="
                +
                ",".join(
                    sorted(unresolved)
                )
            )

            fail(
                "VSE4 possui globals não resolvidos"
            )

        else:

            print(
                "VSE4_UNRESOLVED_GLOBALS=NONE"
            )

            passed(
                "VSE4 sem globals não resolvidos"
            )

    except Exception as exc:

        fail(
            "auditoria symtable do VSE4 falhou: "
            f"{type(exc).__name__}: {exc}"
        )


    required_vse_names = [
        "score_candidate",
        "candidate_text",
        "tokens",
        "geo_hits",
        "concept_hits",
        "objget",
        "provider",
        "source_group",
        "media_type",
        "must_tier",
    ]


    try:

        tree = ast.parse(
            vse_source
        )

        defined_functions = {
            node.name
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        missing = [
            name
            for name in required_vse_names
            if name not in defined_functions
        ]


        if missing:

            print(
                "VSE4_REQUIRED_MISSING="
                +
                ",".join(missing)
            )

            fail(
                "VSE4 está sem funções fundamentais"
            )

        else:

            print(
                "VSE4_REQUIRED_MISSING=NONE"
            )

            passed(
                "funções fundamentais do VSE4 presentes"
            )

    except Exception as exc:

        fail(
            f"não foi possível auditar definições VSE4: {exc}"
        )

else:

    fail(
        "visual_selection_engine_v4.py ausente"
    )


# ============================================================
# 6. VSE4 RUNTIME SELF TEST
# ============================================================

section("6. VSE4 RUNTIME SELF TEST")

if vse.is_file():

    status, output = run(
        [
            sys.executable,
            "visual_selection_engine_v4.py",
        ],
        timeout=30,
    )

    print(
        f"VSE4_SELF_TEST_STATUS={status}"
    )

    if output:

        print(
            "----- VSE4 OUTPUT -----"
        )

        print(
            output[-6000:]
        )


    if status == 0:

        passed(
            "VSE4 self-test runtime passou"
        )

    else:

        fail(
            "VSE4 self-test runtime falhou"
        )


# ============================================================
# 7. VSE4 / MIDIA INTEGRATION
# ============================================================

section("7. ACTIVE MIDIA ↔ VSE4 INTEGRATION")

midia = ROOT / "midia.py"

if midia.is_file():

    text = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )

    markers = [
        "visual_selection_engine_v4",
        "VSE4",
        "SAP_VSE4",
        "score_candidate",
    ]


    found = [
        marker
        for marker in markers
        if marker in text
    ]


    print(
        "MIDIA_VSE4_MARKERS="
        +
        (
            ",".join(found)
            if found
            else "NONE"
        )
    )


    if found:

        passed(
            "há integração/referência VSE4 em midia.py"
        )

    else:

        warn(
            "VSE4 ainda não aparenta estar integrado no midia.py ativo"
        )


# ============================================================
# 8. PROVIDER ACQUISITION
# ============================================================

section("8. PROVIDER ACQUISITION MAP")

provider_expected = [
    "pexels_video",
    "pexels_foto",
    "pixabay_video",
    "pixabay_foto",
    "coverr_video",
    "buscar_todos_candidatos",
]


if midia.is_file():

    try:

        tree = ast.parse(
            midia.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

        functions = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.FunctionDef,
            )
        }


        for name in provider_expected:

            if name in functions:

                node = functions[name]

                print(
                    f"PROVIDER_FUNCTION=PASS "
                    f"name={name} "
                    f"lines={node.lineno}-{node.end_lineno}"
                )

            else:

                print(
                    f"PROVIDER_FUNCTION=FAIL "
                    f"name={name}"
                )


        missing_providers = [
            name
            for name in provider_expected
            if name not in functions
        ]


        if missing_providers:

            warn(
                "funções de provider ausentes: "
                +
                ",".join(
                    missing_providers
                )
            )

        else:

            passed(
                "funções principais de aquisição presentes"
            )


        search_fn = functions.get(
            "buscar_todos_candidatos"
        )


        if search_fn:

            calls = set()

            for node in ast.walk(
                search_fn
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
                    calls.add(
                        node.func.id
                    )


            provider_calls = [
                name
                for name in (
                    "pexels_video",
                    "pexels_foto",
                    "pixabay_video",
                    "pixabay_foto",
                    "coverr_video",
                    "buscar_wikimedia_fotos",
                )
                if name in calls
            ]


            print(
                "SEARCH_PROVIDER_CALLS="
                +
                ",".join(
                    provider_calls
                )
            )


            if (
                "pexels_video" in calls
                and
                "pixabay_video" in calls
            ):
                passed(
                    "buscar_todos_candidatos chama múltiplos providers"
                )
            else:
                warn(
                    "aquisição multi-provider parece incompleta"
                )

    except Exception as exc:

        fail(
            f"auditoria de providers falhou: {exc}"
        )


# ============================================================
# 9. ACTIVE SHORT
# ============================================================

section("9. ACTIVE SHORT DISCOVERY")

SHORT_ID, short_source = (
    find_active_short_id()
)

print(
    f"ACTIVE_SHORT_ID={SHORT_ID or 'NONE'}"
)

print(
    f"ACTIVE_SHORT_SOURCE={short_source}"
)


if SHORT_ID:
    passed(
        f"Short ativo identificado: {SHORT_ID}"
    )
else:
    warn(
        "nenhum Short ativo identificado"
    )


# ============================================================
# 10. MEDIA SCENE INTEGRITY
# ============================================================

section("10. ACTIVE MEDIA SCENE INTEGRITY")

media_dir = (
    ROOT
    / "imagens"
    / f"short_{SHORT_ID}"
    if SHORT_ID
    else None
)

scene_files = {}


if (
    media_dir
    and
    media_dir.is_dir()
):

    invalid_scene_count = 0
    total_media = 0


    for i in range(
        1,
        13,
    ):

        prefix = f"scene_{i:02d}"

        matches = sorted(
            p
            for p in media_dir.glob(
                prefix + ".*"
            )
            if p.is_file()
        )


        scene_files[i] = matches

        total_media += len(
            matches
        )


        print(
            f"SCENE_{i:02d}_COUNT="
            f"{len(matches)}"
        )


        for path in matches:

            print(
                f"  MEDIA "
                f"bytes={path.stat().st_size} "
                f"file={path.relative_to(ROOT)}"
            )


        if len(matches) != 1:

            invalid_scene_count += 1


    print(
        f"MEDIA_TOTAL={total_media}"
    )

    print(
        f"INVALID_SCENE_COUNT={invalid_scene_count}"
    )


    if (
        total_media == 12
        and
        invalid_scene_count == 0
    ):

        passed(
            "12/12 cenas com exatamente uma mídia"
        )

    else:

        fail(
            "estrutura das 12 cenas está inconsistente"
        )

else:

    warn(
        "diretório de mídia do Short ativo não existe"
    )


# ============================================================
# 11. MEDIA TECHNICAL VALIDITY
# ============================================================

section("11. MEDIA TECHNICAL VALIDITY")

ffprobe_bin = shutil.which(
    "ffprobe"
)

media_bad = 0
media_checked = 0


if ffprobe_bin and scene_files:

    for index, matches in scene_files.items():

        if len(matches) != 1:
            continue


        path = matches[0]

        media_checked += 1


        status, output = run(
            [
                ffprobe_bin,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_name,width,height",
                "-of",
                "default=noprint_wrappers=1",
                str(path),
            ],
            timeout=15,
        )


        if (
            status == 0
            and output.strip()
        ):

            print(
                f"MEDIA_PROBE=PASS "
                f"scene={index:02d} "
                f"file={path.name}"
            )

        else:

            media_bad += 1

            print(
                f"MEDIA_PROBE=FAIL "
                f"scene={index:02d} "
                f"file={path.name} "
                f"output={output[:500]!r}"
            )


    print(
        f"MEDIA_PROBE_CHECKED={media_checked}"
    )

    print(
        f"MEDIA_PROBE_FAILURES={media_bad}"
    )


    if media_bad == 0 and media_checked == 12:

        passed(
            "12/12 mídias passam no ffprobe"
        )

    elif media_bad:

        fail(
            f"{media_bad} mídia(s) inválidas/corrompidas"
        )

    else:

        warn(
            "não foi possível verificar todas as 12 mídias"
        )

else:

    warn(
        "ffprobe ou conjunto de mídias indisponível"
    )


# ============================================================
# 12. AUDIO
# ============================================================

section("12. AUDIO HEALTH")

if SHORT_ID:

    audio = (
        ROOT
        / "audios"
        / f"short_{SHORT_ID}.mp3"
    )


    if audio.is_file() and audio.stat().st_size > 0:

        print(
            f"AUDIO_BYTES={audio.stat().st_size}"
        )


        if ffprobe_bin:

            status, output = run(
                [
                    ffprobe_bin,
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration,size",
                    "-of",
                    "default=noprint_wrappers=1",
                    str(audio),
                ],
                timeout=15,
            )

            print(output.strip())

            if status == 0:
                passed(
                    "áudio principal válido"
                )
            else:
                fail(
                    "ffprobe falhou no áudio principal"
                )

        else:

            warn(
                "ffprobe ausente para validar áudio"
            )

    else:

        warn(
            "áudio principal do Short ativo ausente"
        )


# ============================================================
# 13. ASS SUBTITLE
# ============================================================

section("13. SUBTITLE HEALTH")

if SHORT_ID:

    ass = (
        ROOT
        / "videos"
        / f"short_{SHORT_ID}.ass"
    )


    if ass.is_file() and ass.stat().st_size > 0:

        text = ass.read_text(
            encoding="utf-8",
            errors="replace",
        )

        events = sum(
            1
            for line in text.splitlines()
            if line.startswith(
                "Dialogue:"
            )
        )


        print(
            f"ASS_BYTES={ass.stat().st_size}"
        )

        print(
            f"ASS_DIALOGUE_EVENTS={events}"
        )


        if (
            "[Events]" in text
            and
            events > 0
        ):

            passed(
                "legenda ASS estruturalmente válida"
            )

        else:

            fail(
                "legenda ASS existe mas está estruturalmente inválida"
            )

    else:

        warn(
            "legenda ASS do Short ativo ausente"
        )


# ============================================================
# 14. RENDER ARTIFACTS
# ============================================================

section("14. RENDER ARTIFACTS")

if SHORT_ID:

    render_paths = [
        ROOT
        / "temp"
        / SHORT_ID
        / "video_sem_audio.mp4",

        ROOT
        / "videos"
        / f"short_v6_{SHORT_ID}.mp4",
    ]


    for path in render_paths:

        if path.is_file() and path.stat().st_size > 0:

            print(
                f"RENDER_FILE=FOUND "
                f"bytes={path.stat().st_size} "
                f"path={path.relative_to(ROOT)}"
            )


            if ffprobe_bin:

                status, output = run(
                    [
                        ffprobe_bin,
                        "-v",
                        "error",
                        "-show_entries",
                        "format=duration,size,bit_rate",
                        "-of",
                        "default=noprint_wrappers=1",
                        str(path),
                    ],
                    timeout=15,
                )

                if status != 0:
                    fail(
                        f"render inválido: {path.name}"
                    )

                else:
                    print(
                        output.strip()
                    )

        else:

            print(
                f"RENDER_FILE=ABSENT "
                f"path={path.relative_to(ROOT)}"
            )


# ============================================================
# 15. ZERO/TINY FILES
# ============================================================

section("15. ZERO / SUSPICIOUSLY TINY ACTIVE FILES")

zero_files = []
tiny_media = []


search_roots = [
    ROOT / "imagens",
    ROOT / "audios",
    ROOT / "videos",
]


for base in search_roots:

    if not base.exists():
        continue


    for path in base.rglob("*"):

        if not path.is_file():
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue


        if size == 0:

            zero_files.append(
                path
            )


        if (
            path.suffix.lower()
            in {
                ".jpg",
                ".jpeg",
                ".png",
                ".webp",
                ".mp4",
                ".mp3",
                ".wav",
            }
            and
            size < 1024
        ):

            tiny_media.append(
                path
            )


print(
    f"ZERO_FILES={len(zero_files)}"
)

print(
    f"TINY_MEDIA_FILES={len(tiny_media)}"
)


for path in zero_files[:50]:

    print(
        f"ZERO_FILE={path.relative_to(ROOT)}"
    )


for path in tiny_media[:50]:

    print(
        f"TINY_MEDIA={path.relative_to(ROOT)}"
    )


if zero_files:
    warn(
        f"{len(zero_files)} arquivo(s) vazios encontrados"
    )

if tiny_media:
    warn(
        f"{len(tiny_media)} mídia(s) suspeitamente pequenas"
    )

if (
    not zero_files
    and
    not tiny_media
):
    passed(
        "sem arquivos ativos vazios/tiny"
    )


# ============================================================
# 16. RENDER GUARD SAFETY
# ============================================================

section("16. FRESH RENDER GUARD SAFETY")

guard = ROOT / "fresh_render_guard_v1.py"


if guard.is_file():

    text = guard.read_text(
        encoding="utf-8",
        errors="replace",
    )


    ass_protection = (
        '".ass"' in text
        or
        "'.ass'" in text
    )

    audio_protection = (
        '".mp3"' in text
        or
        "'.mp3'" in text
    )


    print(
        f"GUARD_ASS_PROTECTION="
        f"{'YES' if ass_protection else 'NO'}"
    )

    print(
        f"GUARD_AUDIO_PROTECTION="
        f"{'YES' if audio_protection else 'NO'}"
    )


    if (
        ass_protection
        and
        audio_protection
    ):

        passed(
            "Fresh Render Guard aparenta proteger ASS e áudio"
        )

    else:

        warn(
            "Fresh Render Guard merece revisão de proteção"
        )

else:

    warn(
        "fresh_render_guard_v1.py ausente"
    )


# ============================================================
# 17. RECENT LOG ALERTS
# ============================================================

section("17. RECENT PRODUCTION LOG ALERTS")

log_dir = (
    ROOT
    / "logs"
    / "producao"
)

alerts = []

pattern = re.compile(
    r"\b("
    r"traceback|"
    r"exception|"
    r"error|"
    r"erro|"
    r"failed|"
    r"fail"
    r")\b",
    re.IGNORECASE,
)


if log_dir.exists():

    now = datetime.datetime.now().timestamp()


    logs = sorted(
        (
            p
            for p in log_dir.glob("*")
            if p.is_file()
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:40]


    for path in logs:

        try:

            age_days = (
                now
                -
                path.stat().st_mtime
            ) / 86400


            if age_days > 14:
                continue


            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )


            lines = text.splitlines()


            for index, line in enumerate(
                lines,
                start=1,
            ):

                if pattern.search(
                    line
                ):

                    alerts.append(
                        (
                            path,
                            index,
                            line[:350],
                        )
                    )

        except Exception:
            continue


print(
    f"RECENT_LOG_ALERTS={len(alerts)}"
)


for path, line, text in alerts[-80:]:

    print(
        f"LOG_ALERT "
        f"file={path.name} "
        f"line={line} "
        f"text={text}"
    )


if alerts:
    warn(
        "logs recentes contêm alertas; podem incluir falhas históricas de testes"
    )
else:
    passed(
        "nenhum erro explícito nos logs recentes inspecionados"
    )


# ============================================================
# 18. STALE TEMP
# ============================================================

section("18. STALE TEMP ARTIFACTS")

stale = []

if TEMP.exists():

    now = datetime.datetime.now().timestamp()


    for path in TEMP.iterdir():

        if path == REPORT:
            continue

        try:

            age = (
                now
                -
                path.stat().st_mtime
            ) / 86400

        except OSError:
            continue


        if age >= 14:

            stale.append(
                (
                    age,
                    path,
                )
            )


print(
    f"STALE_TEMP_COUNT={len(stale)}"
)


for age, path in sorted(
    stale,
    reverse=True,
)[:100]:

    print(
        f"STALE_TEMP "
        f"age_days={age:.1f} "
        f"path={path.relative_to(ROOT)}"
    )


if stale:
    warn(
        f"{len(stale)} artefato(s) temp com 14+ dias"
    )
else:
    passed(
        "sem temp antigo relevante"
    )


# ============================================================
# 19. REQUIRED BINARIES
# ============================================================

section("19. REQUIRED EXTERNAL BINARIES")

binaries = [
    "python",
    "ffmpeg",
    "ffprobe",
    "git",
]

binary_bad = []


for name in binaries:

    location = shutil.which(
        name
    )

    if location:

        print(
            f"BINARY=PASS "
            f"name={name} "
            f"path={location}"
        )

    else:

        binary_bad.append(
            name
        )

        print(
            f"BINARY=FAIL "
            f"name={name}"
        )


whisper = (
    Path.home()
    / "whisper.cpp"
    / "build"
    / "bin"
    / "whisper-cli"
)


if (
    whisper.is_file()
    and
    os.access(
        whisper,
        os.X_OK,
    )
):

    print(
        f"BINARY=PASS "
        f"name=whisper-cli "
        f"path={whisper}"
    )

else:

    binary_bad.append(
        "whisper-cli"
    )

    print(
        f"BINARY=FAIL "
        f"name=whisper-cli "
        f"path={whisper}"
    )


if binary_bad:

    fail(
        "binários essenciais ausentes: "
        +
        ",".join(binary_bad)
    )

else:

    passed(
        "todos os binários essenciais disponíveis"
    )


# ============================================================
# 20. STORAGE
# ============================================================

section("20. STORAGE HEALTH")

usage = shutil.disk_usage(
    ROOT
)

print(
    f"DISK_TOTAL_BYTES={usage.total}"
)

print(
    f"DISK_USED_BYTES={usage.used}"
)

print(
    f"DISK_FREE_BYTES={usage.free}"
)

print(
    f"DISK_FREE_MB={usage.free / 1024 / 1024:.1f}"
)


if usage.free < 512 * 1024 * 1024:

    warn(
        "menos de ~512 MB livres; renders podem falhar"
    )

else:

    passed(
        "espaço livre acima do limite crítico"
    )


# ============================================================
# 21. GIT
# ============================================================

section("21. GIT WORKTREE")

if (
    ROOT
    / ".git"
).is_dir():

    status, output = run(
        [
            "git",
            "status",
            "--short",
        ],
        timeout=20,
    )


    if status == 0:

        lines = output.splitlines()

        print(
            f"GIT_CHANGED_ITEMS={len(lines)}"
        )

        for line in lines[:200]:
            print(line)

        if lines:
            warn(
                "Git possui alterações não commitadas"
            )
        else:
            passed(
                "Git worktree limpo"
            )

    else:

        warn(
            "git status falhou"
        )


    status, branch = run(
        [
            "git",
            "branch",
            "--show-current",
        ],
        timeout=10,
    )

    if status == 0:

        print(
            f"GIT_BRANCH={branch.strip()}"
        )

else:

    warn(
        "projeto não possui .git ativo"
    )


# ============================================================
# 22. CORE HASHES
# ============================================================

section("22. CORE HASH SNAPSHOT")

hash_targets = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
]


for name in hash_targets:

    path = ROOT / name

    if path.is_file():

        try:

            print(
                f"SHA256 "
                f"{sha256(path)} "
                f"{name}"
            )

        except Exception as exc:

            print(
                f"HASH_FAIL "
                f"file={name} "
                f"error={exc}"
            )


# ============================================================
# 23. FINAL SUMMARY
# ============================================================

section("23. FINAL AUDIT SUMMARY")

print(
    f"PASS_COUNT={PASS_COUNT}"
)

print(
    f"WARN_COUNT={WARN_COUNT}"
)

print(
    f"FAIL_COUNT={FAIL_COUNT}"
)

print(
    f"ACTIVE_SHORT_ID={SHORT_ID or 'NONE'}"
)


print()
print(
    "----- FAILURES -----"
)

if FAILURES:

    for index, item in enumerate(
        FAILURES,
        start=1,
    ):

        print(
            f"FAILURE_{index}={item}"
        )

else:

    print(
        "FAILURES=NONE"
    )


print()
print(
    "----- WARNINGS -----"
)

if WARNINGS:

    for index, item in enumerate(
        WARNINGS,
        start=1,
    ):

        print(
            f"WARNING_{index}={item}"
        )

else:

    print(
        "WARNINGS=NONE"
    )


print()
print("=" * 78)

if FAIL_COUNT == 0:

    if WARN_COUNT == 0:

        print(
            "GENERAL_AUDIT_STATUS=CLEAN"
        )

    else:

        print(
            "GENERAL_AUDIT_STATUS=PASS_WITH_WARNINGS"
        )

else:

    print(
        "GENERAL_AUDIT_STATUS=FAIL"
    )

print("=" * 78)

print(
    f"REPORT={REPORT}"
)

print(
    "AUDIT_NETWORK_EXECUTED=NO"
)

print(
    "AUDIT_MEDIA_DOWNLOADED=NO"
)

print(
    "AUDIT_VIDEO_RENDERED=NO"
)

print(
    "AUDIT_PROJECT_FILES_DELETED=NO"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)

report_handle.flush()
