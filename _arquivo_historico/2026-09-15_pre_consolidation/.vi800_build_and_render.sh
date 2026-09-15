#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1

BASE="$HOME/ShortAutoPro"
SHORT_ID="2026-09-01_1433"

REPORT="$BASE/logs/producao/vi800_00_production_readiness_latest.json"
MANIFEST="$BASE/temp/vi800_publish/portfolio_manifest.json"
CREDITS="$BASE/temp/vi800_publish/credits_vi800.txt"

WORK="$BASE/temp/vi800_publish"
TRACE="$WORK/command_trace.jsonl"
RENDER_LOG="$WORK/render.log"

SILENT="$BASE/temp/$SHORT_ID/video_sem_audio.mp4"
SILENT_OUT="$WORK/VI800_visual.mp4"

ORIGINAL_FINAL="$BASE/videos/short_v6_${SHORT_ID}.mp4"

FULL="$WORK/ShortAutoPro_VI800_Publish_Candidate.mp4"

CONTACT="$WORK/VI800_contact_sheet.jpg"

QC="$WORK/publish_readiness.json"

DOWNLOADS="$HOME/storage/downloads"

DL_FULL="$DOWNLOADS/ShortAutoPro_VI800_Publish_Candidate.mp4"
DL_VISUAL="$DOWNLOADS/ShortAutoPro_VI800_Visual.mp4"
DL_CREDITS="$DOWNLOADS/ShortAutoPro_VI800_Credits.txt"
DL_CONTACT="$DOWNLOADS/ShortAutoPro_VI800_Contact.jpg"

SITE="$BASE/sitecustomize.py"
SITE_BAK="$WORK/sitecustomize.previous.py"
SITE_FLAG="$WORK/sitecustomize.existed"

mkdir -p "$WORK"

echo
echo "=============================================="
echo " VI800 BUILD + FINAL CANARY"
echo "=============================================="


# ------------------------------------------------------
# CORE SAFETY HASHES
# ------------------------------------------------------

VIDEO0="$(sha256sum video.py | awk '{print $1}')"
EXEC0="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
GERAR0="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO0="$(sha256sum roteiro.py | awk '{print $1}')"

MOTION="$BASE/roteiros/motion_plan_${SHORT_ID}.json"

MOTION0="$(
sha256sum "$MOTION" |
awk '{print $1}'
)"

MEDIA0="$(
find imagens \
-type f \
-printf '%p|%s|%T@\n' \
2>/dev/null |
sort |
sha256sum |
awk '{print $1}'
)"


# ------------------------------------------------------
# BUILD VI800
# ------------------------------------------------------

echo
echo "===== BUILDING VI800 ====="

python \
vi800_00_production_readiness.py || exit 10


READY="$(
python - <<'PY'
import json
from pathlib import Path

p = Path(
    "logs/producao/"
    "vi800_00_production_readiness_latest.json"
)

data = json.loads(
    p.read_text(
        encoding="utf-8"
    )
).get(
    "gate",
    {}
)

print(
    data.get(
        "canary_ready",
        False
    )
)
PY
)"


if [ "$READY" != "True" ]; then

    echo
    echo "VI800 BUILD HOLD."
    echo "Não será renderizado."

    exit 11

fi


# ------------------------------------------------------
# DYNAMIC MANIFEST PREFLIGHT
# ------------------------------------------------------

export PYTHONPATH="$BASE${PYTHONPATH:+:$PYTHONPATH}"

export VI700_CANARY_MODE="ON"
export VI700_PORTFOLIO_CANARY="ON"
export VI700_PORTFOLIO_MANIFEST="$MANIFEST"

export VI710_CANARY_MODE="OFF"
export VI730_CANARY_MODE="OFF"

export VI710_1_TRACE="$TRACE"


echo
echo "===== MANIFEST PREFLIGHT ====="

python - <<'PY'
import json
import os
from pathlib import Path

import vi710_1_command_hook as hook

manifest = json.loads(
    Path(
        os.environ[
            "VI700_PORTFOLIO_MANIFEST"
        ]
    ).read_text(
        encoding="utf-8"
    )
)

expected = sorted(
    int(x)
    for x in (
        manifest.get(
            "active_override_scenes"
        )
        or []
    )
)

entries = hook.active_entries()

valid = sorted(
    int(scene)
    for scene, entry
    in entries.items()
    if entry.get(
        "valid"
    )
)

invalid = {
    scene:
        entry
    for scene, entry
    in entries.items()
    if not entry.get(
        "valid"
    )
}

print(
    "EXPECTED:",
    expected
)

print(
    "VALID:",
    valid
)

print(
    "INVALID:",
    invalid
)

if expected != valid:
    raise SystemExit(
        "MANIFEST VALIDATION FAILED"
    )

for scene in expected:

    original = (
        manifest[
            "scenes"
        ][
            str(scene)
        ][
            "original_path"
        ]
    )

    command = [
        "ffmpeg",
        "-i",
        original,
        "-f",
        "null",
        "-"
    ]

    rewritten, matches = (
        hook.rewrite_command(
            command
        )
    )

    matched = sorted(
        item[
            "scene"
        ]
        for item in matches
    )

    if matched != [
        scene
    ]:
        raise SystemExit(
            f"REWRITE FAILED SCENE {scene}"
        )

print(
    "MANIFEST PREFLIGHT: PASS"
)
PY

[ "$?" -eq 0 ] || exit 12


# ------------------------------------------------------
# TEMP SITECUSTOMIZE
# ------------------------------------------------------

if [ -f "$SITE" ]; then

    cp -f \
    "$SITE" \
    "$SITE_BAK"

    echo "1" > \
    "$SITE_FLAG"

else

    echo "0" > \
    "$SITE_FLAG"

fi


restore_site() {

    if \
    [ -f "$SITE_FLAG" ] && \
    [ "$(cat "$SITE_FLAG")" = "1" ] && \
    [ -f "$SITE_BAK" ]; then

        cp -f \
        "$SITE_BAK" \
        "$SITE"

    else

        rm -f \
        "$SITE"

    fi
}


trap restore_site EXIT


cat > "$SITE" <<'PY'
import os
import sys

if (
    os.getenv(
        "VI700_CANARY_MODE",
        "OFF"
    ).upper()
    == "ON"
):
    try:

        from vi710_1_command_hook import (
            activate
        )

        activate()

    except BaseException as exc:

        print(
            "VI800 HOOK ERROR:",
            type(exc).__name__,
            str(exc)[:500],
            file=sys.stderr
        )
PY


# ------------------------------------------------------
# RENDER
# ------------------------------------------------------

rm -f "$TRACE"

export SHORT_ID="$SHORT_ID"
export SHORTAUTO_SHORT_ID="$SHORT_ID"
export SHORTAUTO_FORCE_SHORT_ID="$SHORT_ID"
export PYTHONUNBUFFERED=1


echo
echo "===== VI800 VISUAL RENDER ====="

python video.py 2>&1 |
tee "$RENDER_LOG"

RENDER_STATUS=${PIPESTATUS[0]}

restore_site
trap - EXIT

echo
echo "RENDER STATUS=$RENDER_STATUS"

[ "$RENDER_STATUS" -eq 0 ] || exit "$RENDER_STATUS"

[ -f "$SILENT" ] || {
    echo "video_sem_audio missing"
    exit 13
}

cp -f \
"$SILENT" \
"$SILENT_OUT"


# ------------------------------------------------------
# REAL EXECUTION AUDIT
# ------------------------------------------------------

echo
echo "===== REAL OVERRIDE AUDIT ====="

export VI800_TRACE="$TRACE"
export VI800_MANIFEST="$MANIFEST"

python - <<'PY'
import json
import os
from pathlib import Path

manifest = json.loads(
    Path(
        os.environ[
            "VI800_MANIFEST"
        ]
    ).read_text(
        encoding="utf-8"
    )
)

expected = sorted(
    int(x)
    for x in (
        manifest.get(
            "active_override_scenes"
        )
        or []
    )
)

events = []

trace = Path(
    os.environ[
        "VI800_TRACE"
    ]
)

if trace.exists():

    for line in trace.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines():

        try:
            events.append(
                json.loads(
                    line
                )
            )

        except Exception:
            pass


changed = sorted({
    int(scene)

    for event in events

    if (
        event.get(
            "changed"
        )
        and
        event.get(
            "status"
        )
        == "SUCCESS"
    )

    for scene in (
        event.get(
            "matched_scenes"
        )
        or []
    )
})


errors = [
    event
    for event in events
    if event.get(
        "status"
    )
    == "ERROR"
]


print(
    "EXPECTED:",
    expected
)

print(
    "CHANGED:",
    changed
)

print(
    "ALL CORRECT:",
    changed == expected
)

print(
    "HOOK EVENTS:",
    len(events)
)

print(
    "HOOK ERRORS:",
    len(errors)
)


if changed != expected:
    raise SystemExit(
        "REAL OVERRIDE MISMATCH"
    )

if errors:
    raise SystemExit(
        "HOOK ERROR DETECTED"
    )
PY

[ "$?" -eq 0 ] || exit 14


# ------------------------------------------------------
# FULL AUDIO + SUBTITLE
# ------------------------------------------------------

echo
echo "===== AUDIO + SUBTITLE ====="

export VI800_SILENT="$SILENT_OUT"
export VI800_ORIGINAL="$ORIGINAL_FINAL"
export VI800_FULL="$FULL"
export VI800_SHORT_ID="$SHORT_ID"
export VI800_QC="$QC"

python - <<'PY'
import json
import os
import subprocess
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

SILENT = Path(
    os.environ[
        "VI800_SILENT"
    ]
)

ORIGINAL = Path(
    os.environ[
        "VI800_ORIGINAL"
    ]
)

FULL = Path(
    os.environ[
        "VI800_FULL"
    ]
)

SHORT_ID = os.environ[
    "VI800_SHORT_ID"
]

QC = Path(
    os.environ[
        "VI800_QC"
    ]
)


def run(cmd):

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def subtitles():

    roots = [
        BASE /
        "temp" /
        SHORT_ID,

        BASE /
        "legendas",

        BASE /
        "roteiros",
    ]

    found = []

    seen = set()

    for root in roots:

        if not root.exists():
            continue

        for path in root.rglob("*"):

            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".ass",
                ".srt",
            }:
                continue

            absolute = str(
                path.resolve()
            )

            if absolute in seen:
                continue

            seen.add(
                absolute
            )

            score = 0

            if (
                BASE /
                "temp" /
                SHORT_ID
            ) in path.parents:
                score += 100

            if SHORT_ID in str(path):
                score += 50

            if (
                path.suffix.lower()
                == ".ass"
            ):
                score += 25

            score += min(
                20,
                int(
                    path.stat().st_size
                    / 4000
                )
            )

            found.append(
                (
                    score,
                    path
                )
            )

    found.sort(
        key=lambda x:
            x[0],
        reverse=True
    )

    return [
        path
        for _, path
        in found
    ]


def probe(path):

    p = run([
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ])

    if p.returncode != 0:
        return {}

    try:
        return json.loads(
            p.stdout
        )

    except Exception:
        return {}


if not SILENT.exists():
    raise SystemExit(
        "silent render missing"
    )

if not ORIGINAL.exists():
    raise SystemExit(
        "original final audio source missing"
    )


subs = subtitles()

subtitle = (
    subs[0]
    if subs
    else None
)

subtitle_mode = "NONE"

subtitle_error = None

FULL.unlink(
    missing_ok=True
)


if subtitle:

    escaped = (
        str(subtitle)
        .replace(
            "\\",
            "\\\\"
        )
        .replace(
            "'",
            "\\'"
        )
        .replace(
            ":",
            "\\:"
        )
    )

    vf = (
        "subtitles="
        f"filename='{escaped}'"
    )

    p = run([
        "ffmpeg",
        "-y",
        "-i",
        str(SILENT),
        "-i",
        str(ORIGINAL),
        "-vf",
        vf,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "18",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(FULL),
    ])

    if (
        p.returncode == 0
        and FULL.exists()
    ):
        subtitle_mode = (
            "FILE_BURNIN"
        )

    else:

        subtitle_error = (
            p.stderr[-2500:]
        )

        FULL.unlink(
            missing_ok=True
        )


if not FULL.exists():

    p = run([
        "ffmpeg",
        "-y",
        "-i",
        str(SILENT),
        "-i",
        str(ORIGINAL),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(FULL),
    ])

    if p.returncode != 0:
        raise SystemExit(
            "audio mux failed\n"
            + p.stderr[-2000:]
        )

    subtitle_mode = (
        "AUDIO_ONLY_NO_BURNIN"
    )


info = probe(
    FULL
)

duration = None

try:
    duration = float(
        info.get(
            "format",
            {}
        ).get(
            "duration"
        )
    )

except Exception:
    pass


video = None
audio = None

for stream in (
    info.get(
        "streams",
        []
    )
):

    if (
        stream.get(
            "codec_type"
        )
        == "video"
        and video is None
    ):
        video = stream

    elif (
        stream.get(
            "codec_type"
        )
        == "audio"
        and audio is None
    ):
        audio = stream


resolution = (
    [
        video.get(
            "width"
        ),
        video.get(
            "height"
        ),
    ]
    if video
    else None
)

fps = (
    video.get(
        "avg_frame_rate"
    )
    if video
    else None
)


technical_pass = (
    FULL.exists()
    and resolution
    == [
        1080,
        1920,
    ]
    and audio is not None
    and (
        duration is not None
        and 40 <= duration <= 44
    )
)


subtitle_pass = (
    subtitle_mode
    == "FILE_BURNIN"
)


summary = {
    "full_video":
        str(FULL),

    "duration":
        duration,

    "resolution":
        resolution,

    "fps":
        fps,

    "audio_present":
        audio is not None,

    "audio_codec":
        (
            audio.get(
                "codec_name"
            )
            if audio
            else None
        ),

    "subtitle_candidate":
        (
            str(subtitle)
            if subtitle
            else None
        ),

    "subtitle_mode":
        subtitle_mode,

    "subtitle_error":
        subtitle_error,

    "technical_pass":
        technical_pass,

    "subtitle_pass":
        subtitle_pass,
}


QC.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


print(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    )
)
PY


# ------------------------------------------------------
# CONTACT SHEET
# ------------------------------------------------------

echo
echo "===== CONTACT SHEET ====="

ffmpeg \
-y \
-loglevel error \
-i "$FULL" \
-vf \
"fps=1/3.49,scale=270:-2,tile=3x4:padding=4:margin=4" \
-frames:v 1 \
"$CONTACT" || true


# ------------------------------------------------------
# COPY PUBLISH PACK
# ------------------------------------------------------

mkdir -p \
"$DOWNLOADS"

cp -f \
"$FULL" \
"$DL_FULL"

cp -f \
"$SILENT_OUT" \
"$DL_VISUAL"

cp -f \
"$CREDITS" \
"$DL_CREDITS"

if [ -f "$CONTACT" ]; then

    cp -f \
    "$CONTACT" \
    "$DL_CONTACT"

fi


# ------------------------------------------------------
# FINAL CORE INTEGRITY
# ------------------------------------------------------

VIDEO1="$(sha256sum video.py | awk '{print $1}')"
EXEC1="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
GERAR1="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO1="$(sha256sum roteiro.py | awk '{print $1}')"

MOTION1="$(
sha256sum "$MOTION" |
awk '{print $1}'
)"

MEDIA1="$(
find imagens \
-type f \
-printf '%p|%s|%T@\n' \
2>/dev/null |
sort |
sha256sum |
awk '{print $1}'
)"


echo
echo "=============================================="
echo " VI800 FINAL INTEGRITY"
echo "=============================================="

echo \
"VIDEO=$(
[ "$VIDEO0" = "$VIDEO1" ] &&
echo PASS ||
echo FAIL
)"

echo \
"EXECUTOR=$(
[ "$EXEC0" = "$EXEC1" ] &&
echo PASS ||
echo FAIL
)"

echo \
"GERAR=$(
[ "$GERAR0" = "$GERAR1" ] &&
echo PASS ||
echo FAIL
)"

echo \
"ROTEIRO=$(
[ "$ROTEIRO0" = "$ROTEIRO1" ] &&
echo PASS ||
echo FAIL
)"

echo \
"MOTION_PLAN=$(
[ "$MOTION0" = "$MOTION1" ] &&
echo PASS ||
echo FAIL
)"

echo \
"PRODUCTION_MEDIA=$(
[ "$MEDIA0" = "$MEDIA1" ] &&
echo PASS ||
echo FAIL
)"


echo
echo "===== PUBLISH QC ====="

cat "$QC"


TECH_OK="$(
python - <<'PY'
import json
from pathlib import Path

data = json.loads(
    Path(
        "temp/vi800_publish/"
        "publish_readiness.json"
    ).read_text(
        encoding="utf-8"
    )
)

print(
    data.get(
        "technical_pass",
        False
    )
    and
    data.get(
        "subtitle_pass",
        False
    )
)
PY
)"


CORE_OK="True"

[ "$VIDEO0" = "$VIDEO1" ] || CORE_OK="False"
[ "$EXEC0" = "$EXEC1" ] || CORE_OK="False"
[ "$GERAR0" = "$GERAR1" ] || CORE_OK="False"
[ "$ROTEIRO0" = "$ROTEIRO1" ] || CORE_OK="False"
[ "$MOTION0" = "$MOTION1" ] || CORE_OK="False"
[ "$MEDIA0" = "$MEDIA1" ] || CORE_OK="False"


echo
echo "===== DOWNLOADS ====="

ls -lh \
"$DL_FULL" \
"$DL_VISUAL" \
"$DL_CREDITS" \
2>/dev/null

[ -f "$DL_CONTACT" ] && \
ls -lh "$DL_CONTACT"


echo

if \
[ "$TECH_OK" = "True" ] && \
[ "$CORE_OK" = "True" ]; then

    echo \
"VI800 RESULT: TECHNICALLY_PUBLISHABLE_CANDIDATE"

else

    echo \
"VI800 RESULT: HOLD_FOR_REVIEW"

fi
