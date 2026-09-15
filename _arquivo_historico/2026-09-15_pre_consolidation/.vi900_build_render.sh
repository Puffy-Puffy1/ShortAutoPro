#!/data/data/com.termux/files/usr/bin/bash

set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1


BASE="$HOME/ShortAutoPro"
SHORT_ID="2026-09-01_1433"

WORK="$BASE/temp/vi900_publish"

REPORT="$BASE/logs/producao/vi900_00_global_visual_director_latest.json"
MANIFEST="$WORK/portfolio_manifest.json"
CREDITS="$WORK/credits_vi900.txt"

TRACE="$WORK/command_trace.jsonl"
RENDER_LOG="$WORK/render.log"

TEMP_RENDER="$BASE/temp/$SHORT_ID/video_sem_audio.mp4"

VISUAL="$WORK/ShortAutoPro_VI900_Visual.mp4"

FULL="$WORK/ShortAutoPro_VI900_Publish_Candidate.mp4"

CONTACT="$WORK/ShortAutoPro_VI900_Contact.jpg"

QC="$WORK/final_qc.json"

ORIGINAL_FINAL="$BASE/videos/short_v6_${SHORT_ID}.mp4"

DOWNLOADS="$HOME/storage/downloads"

DL_FULL="$DOWNLOADS/ShortAutoPro_VI900_Publish_Candidate.mp4"

DL_VISUAL="$DOWNLOADS/ShortAutoPro_VI900_Visual.mp4"

DL_CONTACT="$DOWNLOADS/ShortAutoPro_VI900_Contact.jpg"

DL_CREDITS="$DOWNLOADS/ShortAutoPro_VI900_Credits.txt"


SITE="$BASE/sitecustomize.py"

SITE_BACKUP="$WORK/sitecustomize.previous.py"

SITE_FLAG="$WORK/sitecustomize.existed"


mkdir -p \
"$WORK" \
"$DOWNLOADS"


echo
echo "=============================================="
echo " VI900 BUILD + GLOBAL DIRECTOR CANARY"
echo "=============================================="


VIDEO0="$(sha256sum video.py | awk '{print $1}')"

EXEC0="$(
sha256sum vi6_95_scene_executor.py |
awk '{print $1}'
)"

GERAR0="$(
sha256sum gerar_short.sh |
awk '{print $1}'
)"

ROTEIRO0="$(
sha256sum roteiro.py |
awk '{print $1}'
)"


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


echo
echo "===== VI900 BUILD ====="

python \
vi900_00_global_visual_director.py || exit 10


READY="$(
python - <<'PY'
import json
from pathlib import Path

p = Path(
    "logs/producao/"
    "vi900_00_global_visual_director_latest.json"
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
    echo "VI900 GLOBAL DIVERSITY GATE: HOLD"
    echo "Nenhum render será iniciado."

    exit 11

fi


export PYTHONPATH="$BASE${PYTHONPATH:+:$PYTHONPATH}"

export VI700_CANARY_MODE="ON"

export VI700_PORTFOLIO_CANARY="ON"

export VI700_PORTFOLIO_MANIFEST="$MANIFEST"

export VI710_CANARY_MODE="OFF"

export VI730_CANARY_MODE="OFF"

export VI710_1_TRACE="$TRACE"

export SHORT_ID="$SHORT_ID"

export SHORTAUTO_SHORT_ID="$SHORT_ID"

export SHORTAUTO_FORCE_SHORT_ID="$SHORT_ID"

export PYTHONUNBUFFERED=1


echo
echo "===== DYNAMIC OVERRIDE PREFLIGHT ====="

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
    "EXPECTED ACTIVE:",
    expected
)

print(
    "VALID ACTIVE:",
    valid
)

print(
    "INVALID:",
    invalid
)


if expected != valid:
    raise SystemExit(
        "VI900 PREFLIGHT MANIFEST MISMATCH"
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

    print(
        "SCENE",
        scene,
        "=>",
        matched
    )

    if matched != [
        scene
    ]:
        raise SystemExit(
            f"VI900 REWRITE FAILED SCENE {scene}"
        )


print(
    "DYNAMIC PREFLIGHT: PASS"
)
PY


[ "$?" -eq 0 ] || exit 12


if [ -f "$SITE" ]; then

    cp -f \
    "$SITE" \
    "$SITE_BACKUP"

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
    [ -f "$SITE_BACKUP" ]; then

        cp -f \
        "$SITE_BACKUP" \
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
            "VI900 HOOK ERROR:",
            type(exc).__name__,
            str(exc)[:500],
            file=sys.stderr
        )
PY


rm -f \
"$TRACE"


echo
echo "===== VI900 REAL VISUAL RENDER ====="

python video.py 2>&1 |
tee "$RENDER_LOG"

RENDER_STATUS=${PIPESTATUS[0]}


restore_site

trap - EXIT


echo
echo "RENDER STATUS=$RENDER_STATUS"


[ "$RENDER_STATUS" -eq 0 ] || \
exit "$RENDER_STATUS"


[ -f "$TEMP_RENDER" ] || {
    echo "ERRO: video_sem_audio não encontrado"
    exit 13
}


cp -f \
"$TEMP_RENDER" \
"$VISUAL"


echo
echo "===== VI900 REAL OVERRIDE AUDIT ====="


export VI900_TRACE="$TRACE"

export VI900_MANIFEST="$MANIFEST"


python - <<'PY'
import json
import os

from pathlib import Path


manifest = json.loads(
    Path(
        os.environ[
            "VI900_MANIFEST"
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
        "VI900_TRACE"
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
            "status"
        )
        == "SUCCESS"
        and
        event.get(
            "changed"
        )
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
    len(
        events
    )
)

print(
    "HOOK ERRORS:",
    len(
        errors
    )
)


if changed != expected:
    raise SystemExit(
        "VI900 REAL OVERRIDE MISMATCH"
    )


if errors:
    raise SystemExit(
        "VI900 EXECUTOR ERROR"
    )
PY


[ "$?" -eq 0 ] || exit 14


echo
echo "===== VI900 AUDIO + LEGENDAS ====="


export VI900_VISUAL="$VISUAL"

export VI900_ORIGINAL="$ORIGINAL_FINAL"

export VI900_FULL="$FULL"

export VI900_QC="$QC"

export VI900_SHORT_ID="$SHORT_ID"


python - <<'PY'
import json
import os
import subprocess

from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

VISUAL = Path(
    os.environ[
        "VI900_VISUAL"
    ]
)

ORIGINAL = Path(
    os.environ[
        "VI900_ORIGINAL"
    ]
)

FULL = Path(
    os.environ[
        "VI900_FULL"
    ]
)

QC = Path(
    os.environ[
        "VI900_QC"
    ]
)

SHORT_ID = os.environ[
    "VI900_SHORT_ID"
]


def run(cmd):
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )


def subtitle_candidates():

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

            resolved = str(
                path.resolve()
            )

            if resolved in seen:
                continue

            seen.add(
                resolved
            )

            score = 0

            if (
                BASE /
                "temp" /
                SHORT_ID
            ) in path.parents:

                score += 100

            if SHORT_ID in str(
                path
            ):
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
        item[1]
        for item in found
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


if not VISUAL.exists():
    raise SystemExit(
        "VI900 visual missing"
    )


if not ORIGINAL.exists():
    raise SystemExit(
        "original audio source missing"
    )


subs = subtitle_candidates()


subtitle = (
    subs[0]
    if subs
    else None
)


FULL.unlink(
    missing_ok=True
)


subtitle_mode = "NONE"

subtitle_error = None


if subtitle:

    escaped = (
        str(
            subtitle
        )
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
        str(VISUAL),
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
        str(VISUAL),
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
            "VI900 AUDIO MUX FAILED\n"
            + p.stderr[-2000:]
        )


    subtitle_mode = (
        "AUDIO_ONLY"
    )


info = probe(
    FULL
)


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
    duration = None


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
    and
    resolution
    == [
        1080,
        1920,
    ]
    and
    audio is not None
    and
    duration is not None
    and
    40 <= duration <= 44
)


subtitle_pass = (
    subtitle_mode
    == "FILE_BURNIN"
)


report = json.loads(
    (
        BASE /
        "logs/producao/"
        "vi900_00_global_visual_director_latest.json"
    ).read_text(
        encoding="utf-8"
    )
).get(
    "gate",
    {}
)


diversity = (
    report.get(
        "global_diversity",
        {}
    )
)


global_visual_pass = (
    report.get(
        "canary_ready"
    )
    is True
    and
    diversity.get(
        "unique_source_count",
        0
    )
    >= 8
    and
    diversity.get(
        "facade_count",
        99
    )
    <= 2
    and
    diversity.get(
        "maximum_consecutive_same_source",
        99
    )
    <= 2
)


publish_ready = (
    technical_pass
    and
    subtitle_pass
    and
    global_visual_pass
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

    "unique_source_count":
        diversity.get(
            "unique_source_count"
        ),

    "diversity_score":
        diversity.get(
            "diversity_score"
        ),

    "hotel_cecil_facade_count":
        diversity.get(
            "facade_count"
        ),

    "authentic_case_archive_count":
        diversity.get(
            "case_archive_count"
        ),

    "maximum_consecutive_same_source":
        diversity.get(
            "maximum_consecutive_same_source"
        ),

    "technical_pass":
        technical_pass,

    "subtitle_pass":
        subtitle_pass,

    "global_visual_pass":
        global_visual_pass,

    "publish_ready":
        publish_ready,
}


QC.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


print()
print(
    "===== VI900 FINAL QC ====="
)

print(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    )
)
PY


echo
echo "===== VI900 CONTACT SHEET ====="


ffmpeg \
-y \
-loglevel error \
-i "$FULL" \
-vf \
"fps=1/3.49,scale=270:-2,tile=3x4:padding=4:margin=4" \
-frames:v 1 \
"$CONTACT" || true


cp -f \
"$FULL" \
"$DL_FULL"


cp -f \
"$VISUAL" \
"$DL_VISUAL"


cp -f \
"$CREDITS" \
"$DL_CREDITS"


if [ -f "$CONTACT" ]; then

    cp -f \
    "$CONTACT" \
    "$DL_CONTACT"

fi


VIDEO1="$(
sha256sum video.py |
awk '{print $1}'
)"

EXEC1="$(
sha256sum vi6_95_scene_executor.py |
awk '{print $1}'
)"

GERAR1="$(
sha256sum gerar_short.sh |
awk '{print $1}'
)"

ROTEIRO1="$(
sha256sum roteiro.py |
awk '{print $1}'
)"

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
echo " VI900 CORE INTEGRITY"
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


PUBLISH_READY="$(
python - <<'PY'
import json

from pathlib import Path

data = json.loads(
    Path(
        "temp/vi900_publish/"
        "final_qc.json"
    ).read_text(
        encoding="utf-8"
    )
)

print(
    data.get(
        "publish_ready",
        False
    )
)
PY
)"


CORE_READY="True"

[ "$VIDEO0" = "$VIDEO1" ] || CORE_READY="False"

[ "$EXEC0" = "$EXEC1" ] || CORE_READY="False"

[ "$GERAR0" = "$GERAR1" ] || CORE_READY="False"

[ "$ROTEIRO0" = "$ROTEIRO1" ] || CORE_READY="False"

[ "$MOTION0" = "$MOTION1" ] || CORE_READY="False"

[ "$MEDIA0" = "$MEDIA1" ] || CORE_READY="False"


echo
echo "===== DOWNLOAD PACKAGE ====="

ls -lh \
"$DL_FULL" \
"$DL_VISUAL" \
"$DL_CREDITS" \
2>/dev/null


if [ -f "$DL_CONTACT" ]; then
    ls -lh \
    "$DL_CONTACT"
fi


echo
echo "=============================================="


if \
[ "$PUBLISH_READY" = "True" ] && \
[ "$CORE_READY" = "True" ]; then

    echo \
"VI900 RESULT: GLOBAL_DIRECTOR_PUBLISH_CANDIDATE"

else

    echo \
"VI900 RESULT: HOLD_FOR_VISUAL_REVIEW"

fi


echo "=============================================="
