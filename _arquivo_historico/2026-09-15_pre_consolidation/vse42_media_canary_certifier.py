#!/usr/bin/env python3

import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

SID = os.environ.get(
    "SHORT_ID",
    "",
).strip()

if not SID:
    raise RuntimeError(
        "SHORT_ID ausente"
    )


MEDIA_DIR = (
    ROOT
    / "imagens"
    / f"short_{SID}"
)

LOG = (
    ROOT
    / "logs"
    / "producao"
    / f"vse42_real_media_{SID}.log"
)


OLD_HASHES = {
    1: "5110b63489b633ffe1d764f25c983c88c8cd1dfd1b79f47ef0d9eee9abd43b64",
    2: "3fa8558e78de27b30ea829807553c9311b79d0f61e36eebcb15ba42e7ce858db",
    3: "2b553d3d784bc4a6e86f3fbb08fe0771a98075b81f9e0e2c69dc164d679ff27c",
    4: "ecc56485c146a8de60232dadbfd050caeb9ec877702384459deb731f6a268179",
    5: "683d9ff5782e7b4838a01752ad368152293981e99f9645df4c9d51fd0ed4a2f9",
    6: "0f399ea3a559d0122e07002bc1ef65b116143e2c09511f98444162f9a3a02cbd",
    7: "a29e659fa85c2a310aa5e995657b86ae2d48adfd60c7cafc99ec96e88a2f2f93",
    8: "5293b8d2fa4bdd9e6cb59c8d03012b4034fdbbe7c470d2db9e265bfd24ec3900",
    9: "60364bac313db45332b09e0de4e6085f59b2108368e8031a1265158c16d1c422",
    10: "5958b06bf52002d07d745942ed5bf22bc29670523343ed019cf06b753c84aeb7",
    11: "c7062946ed1610ea24f88e1155661b2b5b3b6c8fd3ca7cb1cc0b2fb65fed5fce",
    12: "343646d8ae767a933085ffdfc198e61920bd8ebf245df8f84c16d253927dc573",
}


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def valid_signature(path):

    with path.open("rb") as f:
        head = f.read(32)

    ext = path.suffix.lower()

    if ext in {".jpg", ".jpeg"}:
        return head.startswith(
            b"\xff\xd8\xff"
        )

    if ext == ".png":
        return head.startswith(
            b"\x89PNG\r\n\x1a\n"
        )

    if ext == ".webp":
        return (
            head[:4] == b"RIFF"
            and
            head[8:12] == b"WEBP"
        )

    if ext in {".mp4", ".mov"}:
        return (
            len(head) >= 12
            and
            b"ftyp" in head[:16]
        )

    if ext == ".webm":
        return head.startswith(
            b"\x1a\x45\xdf\xa3"
        )

    return False


def probe(path):

    try:

        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,codec_name",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return {}

        return json.loads(
            result.stdout
        )

    except Exception:
        return {}


scene_files = {}

duplicates = []
missing = []
invalid = []
changed = []
unchanged = []

types = Counter()


for n in range(1, 13):

    matches = []

    for ext in (
        "jpg",
        "jpeg",
        "png",
        "webp",
        "mp4",
        "mov",
        "webm",
    ):

        matches.extend(
            MEDIA_DIR.glob(
                f"scene_{n:02d}.{ext}"
            )
        )


    if len(matches) == 0:

        missing.append(n)
        continue


    if len(matches) > 1:

        duplicates.append(n)
        continue


    path = matches[0]

    scene_files[n] = path

    digest = sha256(path)

    if digest == OLD_HASHES.get(n):
        unchanged.append(n)
    else:
        changed.append(n)


    if path.suffix.lower() in {
        ".mp4",
        ".mov",
        ".webm",
    }:
        types["video"] += 1
    else:
        types["photo"] += 1


    size = path.stat().st_size

    signature = valid_signature(
        path
    )

    metadata = probe(
        path
    )


    streams = metadata.get(
        "streams",
        [],
    )

    width = 0
    height = 0

    if streams:

        width = int(
            streams[0].get(
                "width",
                0,
            )
            or 0
        )

        height = int(
            streams[0].get(
                "height",
                0,
            )
            or 0
        )


    min_size = (
        100_000
        if path.suffix.lower()
        in {
            ".mp4",
            ".mov",
            ".webm",
        }
        else
        4_096
    )


    ok = (
        size >= min_size
        and
        signature
        and
        width > 0
        and
        height > 0
    )


    if not ok:

        invalid.append(n)


    print(
        f"SCENE_{n:02d} "
        f"FILE={path.name} "
        f"BYTES={size} "
        f"WIDTH={width} "
        f"HEIGHT={height} "
        f"SHA256={digest} "
        f"OLD={'YES' if n in unchanged else 'NO'} "
        f"HEALTH={'PASS' if ok else 'FAIL'}"
    )


log_text = ""

if LOG.is_file():

    log_text = LOG.read_text(
        encoding="utf-8",
        errors="replace",
    )


providers = Counter()

for match in re.finditer(
    r"ESCOLHIDO:\s*([^/\n]+)\s*/\s*([^\n]+)",
    log_text,
    re.I,
):

    providers[
        match.group(1).strip()
    ] += 1


must_values = []

for match in re.finditer(
    r"MUST\s+COVERAGE:\s*(\d+)\s*/\s*(\d+)",
    log_text,
    re.I,
):

    must_values.append(
        (
            int(match.group(1)),
            int(match.group(2)),
        )
    )


must_full = sum(
    1
    for a, b in must_values
    if b > 0 and a >= b
)

must_weak = sum(
    1
    for a, b in must_values
    if b > 0 and a < b
)


fail_open = len(
    re.findall(
        r"VSE\d*.*FAIL_OPEN",
        log_text,
        re.I,
    )
)

overrides = len(
    re.findall(
        r"(?:OVERRIDE(?:_ACTIVE)?|REAL_OVERRIDE)=YES",
        log_text,
        re.I,
    )
)

commits = len(
    re.findall(
        r"(?:FIRST_SUCCESS_LOCK|SCENE_COMMIT).*COMMITTED",
        log_text,
        re.I,
    )
)


tracebacks = log_text.count(
    "Traceback"
)

errors = len(
    re.findall(
        r"\b(?:ERRO|ERROR)\b",
        log_text,
        re.I,
    )
)


print()
print("=" * 68)
print("VSE4.2 MEDIA CANARY SUMMARY")
print("=" * 68)

print(
    f"MEDIA_DIR={MEDIA_DIR}"
)

print(
    f"VALID_SCENES={len(scene_files)}"
)

print(
    "MISSING_SCENES="
    +
    (
        ",".join(
            f"{n:02d}"
            for n in missing
        )
        or
        "NONE"
    )
)

print(
    "DUPLICATE_SCENES="
    +
    (
        ",".join(
            f"{n:02d}"
            for n in duplicates
        )
        or
        "NONE"
    )
)

print(
    "INVALID_SCENES="
    +
    (
        ",".join(
            f"{n:02d}"
            for n in invalid
        )
        or
        "NONE"
    )
)

print(
    "CHANGED_VS_OLD="
    +
    (
        ",".join(
            f"{n:02d}"
            for n in changed
        )
        or
        "NONE"
    )
)

print(
    "UNCHANGED_VS_OLD="
    +
    (
        ",".join(
            f"{n:02d}"
            for n in unchanged
        )
        or
        "NONE"
    )
)

print(
    f"CHANGED_COUNT={len(changed)}"
)

print(
    f"PHOTO_COUNT={types['photo']}"
)

print(
    f"VIDEO_COUNT={types['video']}"
)

print(
    "PROVIDERS="
    +
    (
        ",".join(
            f"{k}:{v}"
            for k, v
            in providers.items()
        )
        or
        "UNKNOWN"
    )
)

print(
    f"MUST_RECORDS={len(must_values)}"
)

print(
    f"MUST_FULL={must_full}"
)

print(
    f"MUST_WEAK={must_weak}"
)

print(
    f"VSE_OVERRIDES={overrides}"
)

print(
    f"VSE_COMMITS={commits}"
)

print(
    f"VSE_FAIL_OPEN={fail_open}"
)

print(
    f"TRACEBACKS={tracebacks}"
)

print(
    f"ERROR_TOKENS={errors}"
)


structure_ok = (
    len(scene_files) == 12
    and
    not missing
    and
    not duplicates
    and
    not invalid
)


runtime_ok = (
    tracebacks == 0
    and
    fail_open == 0
)


if structure_ok:
    print(
        "MEDIA_STRUCTURE_GATE=PASS"
    )
else:
    print(
        "MEDIA_STRUCTURE_GATE=FAIL"
    )


if runtime_ok:
    print(
        "VSE_RUNTIME_GATE=PASS"
    )
else:
    print(
        "VSE_RUNTIME_GATE=FAIL"
    )


if (
    structure_ok
    and
    runtime_ok
):

    print(
        "VSE42_REAL_MEDIA_CANARY=PASS"
    )

else:

    print(
        "VSE42_REAL_MEDIA_CANARY=FAIL"
    )


manifest = {
    "short_id": SID,
    "valid_scenes": len(scene_files),
    "missing": missing,
    "duplicates": duplicates,
    "invalid": invalid,
    "changed_vs_old": changed,
    "unchanged_vs_old": unchanged,
    "photo_count": types["photo"],
    "video_count": types["video"],
    "providers": dict(providers),
    "must_records": len(must_values),
    "must_full": must_full,
    "must_weak": must_weak,
    "overrides": overrides,
    "commits": commits,
    "fail_open": fail_open,
    "tracebacks": tracebacks,
    "structure_ok": structure_ok,
    "runtime_ok": runtime_ok,
}


manifest_path = (
    ROOT
    / "manifests"
    / f"vse42_media_canary_{SID}.json"
)

manifest_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

manifest_path.write_text(
    json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(
    f"MANIFEST={manifest_path}"
)
