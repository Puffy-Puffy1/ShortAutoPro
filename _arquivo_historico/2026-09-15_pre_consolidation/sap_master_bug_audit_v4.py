#!/usr/bin/env python3

from pathlib import Path
import ast
import hashlib
import json
import os
import re
import subprocess
import time
import py_compile


ROOT = Path.home() / "ShortAutoPro"

SID = os.environ.get(
    "SHORT_ID",
    "2026-09-02_2358",
).strip()

MEDIA_DIR = ROOT / "imagens" / f"short_{SID}"

SCENE_MAP = (
    ROOT
    / "roteiros"
    / f"scene_map_{SID}.json"
)

AUDIO = (
    ROOT
    / "audios"
    / f"short_{SID}.mp3"
)

ASS = (
    ROOT
    / "videos"
    / f"short_{SID}.ass"
)

VIDEO_BASE = (
    ROOT
    / "temp"
    / SID
    / "video_sem_audio.mp4"
)

FINAL = (
    ROOT
    / "videos"
    / f"short_v6_{SID}.mp4"
)

TXT = (
    ROOT
    / "temp"
    / f"MASTER_BUG_AUDIT_V4_{SID}.txt"
)

JSON_OUT = (
    ROOT
    / "temp"
    / f"MASTER_BUG_AUDIT_V4_{SID}.json"
)


results = {
    "short_id": SID,
    "errors": [],
    "warnings": [],
    "passes": [],
    "media": {},
}


def out(*args):

    text = " ".join(
        str(x)
        for x in args
    )

    print(text)

    LOG.append(text)


LOG = []


def section(title):

    out()
    out("=" * 72)
    out(title)
    out("=" * 72)


def add_pass(name):

    results["passes"].append(
        name
    )

    out(
        f"PASS | {name}"
    )


def add_warning(name):

    results["warnings"].append(
        name
    )

    out(
        f"WARNING | {name}"
    )


def add_error(name):

    results["errors"].append(
        name
    )

    out(
        f"ERROR | {name}"
    )


def sha256(path):

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


def ffprobe(path):

    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        (
            "format=duration,size:"
            "stream=codec_name,codec_type,"
            "width,height,r_frame_rate"
        ),
        "-of",
        "json",
        str(path),
    ]

    try:

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
        }


    if p.returncode != 0:

        return {
            "ok": False,
            "error": p.stderr.strip(),
        }


    try:

        data = json.loads(
            p.stdout
        )

    except Exception as exc:

        return {
            "ok": False,
            "error":
                f"JSON: {exc}",
        }


    data["ok"] = True

    return data


def signature_ok(path):

    try:

        data = path.read_bytes()[
            :32
        ]

    except Exception:

        return False


    suffix = path.suffix.lower()


    if suffix in {
        ".jpg",
        ".jpeg",
    }:

        return data.startswith(
            b"\xff\xd8\xff"
        )


    if suffix == ".png":

        return data.startswith(
            b"\x89PNG\r\n\x1a\n"
        )


    if suffix == ".webp":

        return (
            data.startswith(
                b"RIFF"
            )
            and
            b"WEBP" in data[
                :16
            ]
        )


    if suffix in {
        ".mp4",
        ".mov",
        ".m4v",
    }:

        return (
            b"ftyp" in data
        )


    return True


def scene_number(path):

    match = re.match(
        r"scene_(\d+)",
        path.stem,
        re.I,
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


section(
    "SHORTAUTOPRO MASTER BUG AUDIT V4"
)

out(
    f"DATE={time.strftime('%Y-%m-%d %H:%M:%S')}"
)

out(
    f"ROOT={ROOT}"
)

out(
    f"SHORT_ID={SID}"
)


# ============================================================
# 1. CORE
# ============================================================

section(
    "1. CORE FILES"
)

critical = [
    "gerar_short.sh",
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
]


for name in critical:

    p = ROOT / name

    if p.is_file():

        out(
            f"FOUND | {name} | "
            f"{p.stat().st_size} bytes | "
            f"{sha256(p)}"
        )

    else:

        add_error(
            f"CORE_MISSING:{name}"
        )


# ============================================================
# 2. COMPILE ALL ACTIVE ROOT PYTHON
# ============================================================

section(
    "2. PYTHON COMPILE"
)

python_files = sorted(
    ROOT.glob("*.py")
)

compile_failures = []


for p in python_files:

    try:

        py_compile.compile(
            str(p),
            doraise=True,
        )

    except Exception as exc:

        compile_failures.append(
            (
                p.name,
                str(exc),
            )
        )


out(
    f"PYTHON_FILES_TESTED={len(python_files)}"
)


if not compile_failures:

    add_pass(
        "ALL_ROOT_PYTHON_COMPILE"
    )

else:

    for name, error in compile_failures:

        add_error(
            f"PY_COMPILE:{name}"
        )

        out(
            error
        )


# ============================================================
# 3. SHELL SYNTAX
# ============================================================

section(
    "3. SHELL SYNTAX"
)

shell_files = sorted(
    ROOT.glob("*.sh")
)

shell_failures = []


for p in shell_files:

    r = subprocess.run(
        [
            "bash",
            "-n",
            str(p),
        ],
        capture_output=True,
        text=True,
    )

    if r.returncode != 0:

        shell_failures.append(
            (
                p.name,
                r.stderr.strip(),
            )
        )


out(
    f"SHELL_FILES_TESTED={len(shell_files)}"
)


if not shell_failures:

    add_pass(
        "ALL_ROOT_SHELL_SYNTAX"
    )

else:

    for name, error in shell_failures:

        add_error(
            f"SHELL_SYNTAX:{name}"
        )

        out(
            error
        )


# ============================================================
# 4. EXACT TARGET MEDIA
# ============================================================

section(
    "4. EXACT TARGET MEDIA INVENTORY"
)

media_extensions = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".mov",
    ".webm",
}


scene_files = []


if not MEDIA_DIR.is_dir():

    add_error(
        "TARGET_MEDIA_DIR_MISSING"
    )

else:

    for p in sorted(
        MEDIA_DIR.iterdir()
    ):

        if not p.is_file():
            continue

        if p.suffix.lower() not in media_extensions:
            continue

        if scene_number(p) is None:
            continue

        scene_files.append(
            p
        )


out(
    f"TARGET_MEDIA_DIR={MEDIA_DIR}"
)

out(
    f"TARGET_MEDIA_COUNT={len(scene_files)}"
)


by_scene = {}


for p in scene_files:

    n = scene_number(p)

    by_scene.setdefault(
        n,
        [],
    ).append(
        p
    )


for n in range(
    1,
    13,
):

    files = by_scene.get(
        n,
        [],
    )

    out()
    out(
        f"SCENE_{n:02d}_COUNT={len(files)}"
    )


    if not files:

        add_error(
            f"SCENE_{n:02d}_MISSING"
        )

        continue


    if len(files) > 1:

        add_error(
            f"SCENE_{n:02d}_DUPLICATE_FILES"
        )


    for p in files:

        size = p.stat().st_size

        digest = sha256(
            p
        )

        sig = signature_ok(
            p
        )

        probe = ffprobe(
            p
        )


        out(
            f"FILE={p.relative_to(ROOT)}"
        )

        out(
            f"BYTES={size}"
        )

        out(
            f"SHA256={digest}"
        )

        out(
            f"SIGNATURE_OK={sig}"
        )

        out(
            f"FFPROBE_OK={probe.get('ok')}"
        )


        if size < 10_000:

            add_error(
                f"SCENE_{n:02d}_TOO_SMALL"
            )


        if not sig:

            add_error(
                f"SCENE_{n:02d}_BAD_SIGNATURE"
            )


        if not probe.get(
            "ok"
        ):

            add_error(
                f"SCENE_{n:02d}_FFPROBE_FAIL"
            )

            out(
                probe.get(
                    "error",
                    "",
                )
            )


        results["media"][
            f"{n:02d}"
        ] = {
            "path":
                str(
                    p.relative_to(
                        ROOT
                    )
                ),

            "bytes":
                size,

            "sha256":
                digest,

            "mtime":
                p.stat().st_mtime,

            "ffprobe_ok":
                bool(
                    probe.get(
                        "ok"
                    )
                ),
        }


if (
    len(scene_files) == 12
    and
    all(
        len(
            by_scene.get(
                n,
                [],
            )
        )
        == 1
        for n in range(
            1,
            13,
        )
    )
):

    add_pass(
        "EXACTLY_12_UNIQUE_SCENES"
    )


# ============================================================
# 5. DUPLICATE MEDIA HASHES
# ============================================================

section(
    "5. INTRA-SHORT DUPLICATE HASH AUDIT"
)

hash_to_scenes = {}


for scene, item in results[
    "media"
].items():

    digest = item[
        "sha256"
    ]

    hash_to_scenes.setdefault(
        digest,
        [],
    ).append(
        scene
    )


duplicates = {
    digest: scenes
    for digest, scenes
    in hash_to_scenes.items()
    if len(scenes) > 1
}


if duplicates:

    for digest, scenes in duplicates.items():

        add_warning(
            "DUPLICATE_MEDIA:"
            +
            ",".join(
                scenes
            )
        )

        out(
            f"HASH={digest}"
        )

else:

    add_pass(
        "NO_EXACT_DUPLICATE_MEDIA"
    )


# ============================================================
# 6. SCENE MAP
# ============================================================

section(
    "6. SCENE MAP CONSISTENCY"
)


if not SCENE_MAP.is_file():

    add_error(
        "SCENE_MAP_MISSING"
    )

else:

    try:

        data = json.loads(
            SCENE_MAP.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(
            data,
            list,
        ):

            scenes = data

        elif isinstance(
            data,
            dict,
        ):

            scenes = (
                data.get(
                    "scenes"
                )
                or
                data.get(
                    "cenas"
                )
                or
                []
            )

        else:

            scenes = []


        out(
            f"SCENE_MAP_COUNT={len(scenes)}"
        )


        if len(
            scenes
        ) == 12:

            add_pass(
                "SCENE_MAP_12"
            )

        else:

            add_warning(
                f"SCENE_MAP_COUNT:{len(scenes)}"
            )


    except Exception as exc:

        add_error(
            "SCENE_MAP_JSON_INVALID"
        )

        out(
            repr(
                exc
            )
        )


# ============================================================
# 7. REQUIRED PIPELINE ASSETS
# ============================================================

section(
    "7. PIPELINE ASSET READINESS"
)

required_assets = {
    "AUDIO": AUDIO,
    "ASS": ASS,
    "VIDEO_BASE": VIDEO_BASE,
    "FINAL": FINAL,
    "SCENE_MAP": SCENE_MAP,
}


for name, p in required_assets.items():

    if p.is_file() and p.stat().st_size > 0:

        out(
            f"{name}=PASS | "
            f"{p.stat().st_size} | "
            f"{p.relative_to(ROOT)}"
        )

    else:

        out(
            f"{name}=MISSING"
        )


# ============================================================
# 8. RENDER FRESHNESS
# ============================================================

section(
    "8. RENDER FRESHNESS"
)


media_mtimes = [
    p.stat().st_mtime
    for p in scene_files
]


if FINAL.is_file() and media_mtimes:

    newest_media = max(
        media_mtimes
    )

    final_time = FINAL.stat().st_mtime


    out(
        "NEWEST_MEDIA_MTIME="
        +
        time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(
                newest_media
            ),
        )
    )

    out(
        "FINAL_MTIME="
        +
        time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(
                final_time
            ),
        )
    )


    if final_time >= newest_media:

        add_pass(
            "FINAL_NEWER_THAN_MEDIA"
        )

    else:

        add_warning(
            "STALE_FINAL_RENDER_MEDIA_NEWER_THAN_VIDEO"
        )


if VIDEO_BASE.is_file() and media_mtimes:

    base_time = VIDEO_BASE.stat().st_mtime

    newest_media = max(
        media_mtimes
    )


    if base_time >= newest_media:

        add_pass(
            "VIDEO_BASE_NEWER_THAN_MEDIA"
        )

    else:

        add_warning(
            "STALE_VIDEO_BASE_MEDIA_NEWER"
        )


# ============================================================
# 9. ASS VALIDITY
# ============================================================

section(
    "9. SUBTITLE AUDIT"
)


if ASS.is_file():

    text = ASS.read_text(
        encoding="utf-8",
        errors="replace",
    )

    dialogues = len(
        re.findall(
            r"^Dialogue:",
            text,
            flags=re.M,
        )
    )


    out(
        f"ASS_DIALOGUES={dialogues}"
    )


    if (
        "[Events]" in text
        and
        dialogues > 0
    ):

        add_pass(
            "ASS_VALID"
        )

    else:

        add_error(
            "ASS_INVALID"
        )


# ============================================================
# 10. AUDIO / VIDEO PROBE
# ============================================================

section(
    "10. AUDIO / RENDER MEDIA VALIDITY"
)


for label, p in (
    (
        "AUDIO",
        AUDIO,
    ),
    (
        "VIDEO_BASE",
        VIDEO_BASE,
    ),
    (
        "FINAL",
        FINAL,
    ),
):

    if not p.is_file():

        continue


    probe = ffprobe(
        p
    )


    if probe.get(
        "ok"
    ):

        add_pass(
            f"{label}_FFPROBE"
        )

        fmt = probe.get(
            "format",
            {},
        )

        out(
            f"{label}_DURATION="
            f"{fmt.get('duration')}"
        )

        out(
            f"{label}_SIZE="
            f"{fmt.get('size')}"
        )

    else:

        add_error(
            f"{label}_FFPROBE_FAIL"
        )


# ============================================================
# 11. MIDIA PIPELINE STRUCTURE
# ============================================================

section(
    "11. MIDIA.PY STRUCTURAL AUDIT"
)


midia = ROOT / "midia.py"


if midia.is_file():

    src = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )


    required_functions = [
        "buscar_todos_candidatos",
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
    ]


    for name in required_functions:

        exists = bool(
            re.search(
                rf"^def\s+{re.escape(name)}\s*\(",
                src,
                re.M,
            )
        )


        out(
            f"{name}="
            f"{'FOUND' if exists else 'MISSING'}"
        )


        if not exists:

            add_error(
                f"MIDIA_FUNCTION_MISSING:{name}"
            )


    markers = [
        "VSE4",
        "VSE42",
        "VSE4.2",
        "visual_selection_engine_v4",
        "SCENE_COMMIT",
        "MUST_RESCUE",
        "media_diversity_guard",
        "media_provenance_capture",
    ]


    out()
    out(
        "===== ACTIVE MARKERS ====="
    )


    for marker in markers:

        count = src.casefold().count(
            marker.casefold()
        )

        out(
            f"{marker}={count}"
        )


# ============================================================
# 12. PROVIDER CALL MAP
# ============================================================

section(
    "12. PROVIDER CALL MAP"
)


try:

    src = midia.read_text(
        encoding="utf-8"
    )

    tree = ast.parse(
        src
    )


    target = None


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

            target = node

            break


    provider_calls = []


    if target:

        for node in ast.walk(
            target
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

                name = node.func.id


                if name in {
                    "pexels_video",
                    "pexels_foto",
                    "pixabay_video",
                    "pixabay_foto",
                    "coverr_video",
                    "buscar_wikimedia_fotos",
                }:

                    provider_calls.append(
                        name
                    )


    out(
        "PROVIDER_CALLS="
        +
        ",".join(
            provider_calls
        )
    )


    expected = {
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
    }


    missing_calls = (
        expected
        -
        set(
            provider_calls
        )
    )


    if missing_calls:

        add_warning(
            "PROVIDERS_NOT_CALLED:"
            +
            ",".join(
                sorted(
                    missing_calls
                )
            )
        )

    else:

        add_pass(
            "ALL_MAIN_PROVIDERS_CALLED"
        )


except Exception as exc:

    add_warning(
        "PROVIDER_AST_AUDIT_FAILED"
    )

    out(
        repr(
            exc
        )
    )


# ============================================================
# 13. VSE4 STATIC HEALTH
# ============================================================

section(
    "13. VSE4 HEALTH"
)


vse = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if vse.is_file():

    vse_src = vse.read_text(
        encoding="utf-8",
        errors="replace",
    )


    checks = {
        "candidate_text":
            "def candidate_text(",

        "tokens":
            "def tokens(",

        "score_candidate":
            "def score_candidate(",

        "geo_hits":
            "def geo_hits(",

        "GEO_GROUPS":
            "GEO_GROUPS",

        "CONCEPTS":
            "CONCEPTS",

        "GENERIC_LIFESTYLE":
            "GENERIC_LIFESTYLE",

        "MEDICINE_TERMS":
            "MEDICINE_TERMS",
    }


    for name, needle in checks.items():

        ok = needle in vse_src

        out(
            f"{name}="
            f"{'PASS' if ok else 'FAIL'}"
        )


        if not ok:

            add_error(
                f"VSE4_MISSING:{name}"
            )


# ============================================================
# 14. DANGEROUS CACHE / LATEST-FILE LOGIC
# ============================================================

section(
    "14. CACHE / PATH RISK AUDIT"
)


for filename in (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
):

    p = ROOT / filename

    if not p.is_file():
        continue


    text = p.read_text(
        encoding="utf-8",
        errors="replace",
    )


    patterns = {
        "LATEST_GLOB":
            r"(latest|mais_recente|sorted\s*\(\s*glob|max\s*\(.*mtime)",

        "GENERIC_TEMP":
            r"temp/(video|final|output)\.mp4",

        "HARD_CODED_SHORT":
            r"2026-\d\d-\d\d_\d\d\d\d",

        "UNSCOPED_SCENE_GLOB":
            r"glob\([^)]*scene_\*",
    }


    for label, pattern in patterns.items():

        hits = len(
            re.findall(
                pattern,
                text,
                flags=re.I | re.S,
            )
        )


        out(
            f"{filename}:{label}={hits}"
        )


        if hits:

            add_warning(
                f"{filename}:{label}:{hits}"
            )


# ============================================================
# 15. OTHER SHORT HASH LEAKAGE
# ============================================================

section(
    "15. CROSS-SHORT EXACT HASH REUSE"
)


target_hashes = {
    item[
        "sha256"
    ]: scene
    for scene, item
    in results[
        "media"
    ].items()
}


cross_matches = []


imagens_root = (
    ROOT
    / "imagens"
)


if imagens_root.is_dir():

    for short_dir in imagens_root.glob(
        "short_*"
    ):

        if (
            short_dir.resolve()
            ==
            MEDIA_DIR.resolve()
        ):

            continue


        for p in short_dir.glob(
            "scene_*"
        ):

            if not p.is_file():
                continue

            if p.suffix.lower() not in media_extensions:
                continue


            try:

                digest = sha256(
                    p
                )

            except Exception:

                continue


            if digest in target_hashes:

                cross_matches.append(
                    {
                        "target_scene":
                            target_hashes[
                                digest
                            ],

                        "other":
                            str(
                                p.relative_to(
                                    ROOT
                                )
                            ),

                        "hash":
                            digest,
                    }
                )


if cross_matches:

    for item in cross_matches:

        out(
            "MATCH | "
            f"scene={item['target_scene']} | "
            f"{item['other']}"
        )


    add_warning(
        f"CROSS_SHORT_HASH_REUSE:{len(cross_matches)}"
    )

else:

    add_pass(
        "NO_CROSS_SHORT_EXACT_REUSE"
    )


results[
    "cross_short_matches"
] = cross_matches


# ============================================================
# 16. FINAL SUMMARY
# ============================================================

section(
    "16. MASTER SUMMARY"
)


results[
    "error_count"
] = len(
    results[
        "errors"
    ]
)

results[
    "warning_count"
] = len(
    results[
        "warnings"
    ]
)

results[
    "pass_count"
] = len(
    results[
        "passes"
    ]
)


out(
    f"PASS_COUNT={results['pass_count']}"
)

out(
    f"WARNING_COUNT={results['warning_count']}"
)

out(
    f"ERROR_COUNT={results['error_count']}"
)


if results[
    "errors"
]:

    out()
    out(
        "===== ERRORS ====="
    )

    for item in results[
        "errors"
    ]:

        out(
            f"ERROR={item}"
        )


if results[
    "warnings"
]:

    out()
    out(
        "===== WARNINGS ====="
    )

    for item in results[
        "warnings"
    ]:

        out(
            f"WARNING={item}"
        )


if results[
    "error_count"
] == 0:

    if results[
        "warning_count"
    ] == 0:

        status = (
            "CLEAN"
        )

    else:

        status = (
            "PASS_WITH_WARNINGS"
        )

else:

    status = (
        "FAIL"
    )


results[
    "status"
] = status


out()
out(
    f"MASTER_AUDIT_STATUS={status}"
)

out(
    "FILES_MODIFIED=NO"
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


TXT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


TXT.write_text(
    "\n".join(
        LOG
    )
    +
    "\n",
    encoding="utf-8",
)


JSON_OUT.write_text(
    json.dumps(
        results,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    f"REPORT_TXT={TXT.relative_to(ROOT)}"
)

print(
    f"REPORT_JSON={JSON_OUT.relative_to(ROOT)}"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
