#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1

BASE="$HOME/ShortAutoPro"
SHORT_ID="2026-09-01_1433"

MANIFEST="$BASE/temp/vi720_canary/portfolio_manifest.json"
REPORT="$BASE/logs/producao/vi720_00_case_context_repair_latest.json"

WORK="$BASE/temp/vi720_full_canary"
TRACE="$WORK/command_trace.jsonl"
RENDER_LOG="$WORK/render.log"

SILENT_SRC="$BASE/temp/$SHORT_ID/video_sem_audio.mp4"
SILENT_COPY="$WORK/VI720_visual_canary.mp4"

ORIGINAL_FINAL="$BASE/videos/short_v6_${SHORT_ID}.mp4"
FULL_CANARY="$WORK/ShortAutoPro_VI720_Full_Canary.mp4"

DOWNLOADS="$HOME/storage/downloads"
DOWNLOAD_VISUAL="$DOWNLOADS/ShortAutoPro_VI720_Visual.mp4"
DOWNLOAD_FULL="$DOWNLOADS/ShortAutoPro_VI720_Full.mp4"

SITE="$BASE/sitecustomize.py"
SITE_BAK="$WORK/sitecustomize.backup.py"
SITE_FLAG="$WORK/sitecustomize.existed"

OLD_SILENT="$WORK/old_video_sem_audio.bak.mp4"

mkdir -p "$WORK"

echo
echo "=============================================="
echo " VI720 FULL CANARY"
echo "=============================================="

[ -f "$MANIFEST" ] || {
    echo "ERRO: VI720 manifest ausente"
    exit 2
}

[ -f "$REPORT" ] || {
    echo "ERRO: VI720 report ausente"
    exit 3
}

[ -f "$BASE/vi710_1_command_hook.py" ] || {
    echo "ERRO: hook VI710.1 ausente"
    exit 4
}


READY="$(
python - <<'PY'
import json
from pathlib import Path

p = Path(
    "logs/producao/vi720_00_case_context_repair_latest.json"
)

data = json.loads(
    p.read_text(
        encoding="utf-8"
    )
).get("gate", {})

print(
    data.get(
        "canary_ready",
        False
    )
)
PY
)"

if [ "$READY" != "True" ]; then
    echo "ERRO: VI720 ainda não está pronto."
    exit 5
fi


VIDEO0="$(sha256sum video.py | awk '{print $1}')"
EXEC0="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
GERAR0="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO0="$(sha256sum roteiro.py | awk '{print $1}')"

MEDIA0="$(
find imagens -type f -printf '%p|%s|%T@\n' 2>/dev/null |
sort | sha256sum | awk '{print $1}'
)"


echo
echo "===== DYNAMIC PREFLIGHT ====="

export PYTHONPATH="$BASE${PYTHONPATH:+:$PYTHONPATH}"

export VI700_CANARY_MODE="ON"
export VI700_PORTFOLIO_CANARY="ON"
export VI700_PORTFOLIO_MANIFEST="$MANIFEST"

export VI710_CANARY_MODE="OFF"
export VI730_CANARY_MODE="OFF"

export VI710_1_TRACE="$TRACE"

python - <<'PY'
import json
import os

import vi710_1_command_hook as hook

manifest = json.loads(
    open(
        os.environ[
            "VI700_PORTFOLIO_MANIFEST"
        ],
        encoding="utf-8"
    ).read()
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
        "VI720 PREFLIGHT: active manifest mismatch"
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

    hit = sorted(
        item["scene"]
        for item in matches
    )

    print(
        "SCENE",
        scene,
        "| REWRITE=",
        hit
    )

    if hit != [scene]:
        raise SystemExit(
            f"rewrite failed scene {scene}"
        )

print(
    "DYNAMIC PREFLIGHT: PASS"
)
PY

if [ "$?" -ne 0 ]; then
    exit 6
fi


if [ -f "$SILENT_SRC" ]; then
    cp -f \
    "$SILENT_SRC" \
    "$OLD_SILENT"

    rm -f \
    "$SILENT_SRC"
fi


if [ -f "$SITE" ]; then
    cp -f \
    "$SITE" \
    "$SITE_BAK"

    echo "1" > "$SITE_FLAG"
else
    echo "0" > "$SITE_FLAG"
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
        from vi710_1_command_hook import activate
        activate()

    except BaseException as exc:
        print(
            "VI720 HOOK ERROR:",
            type(exc).__name__,
            str(exc)[:500],
            file=sys.stderr
        )
PY


rm -f "$TRACE"

export SHORT_ID="$SHORT_ID"
export SHORTAUTO_SHORT_ID="$SHORT_ID"
export SHORTAUTO_FORCE_SHORT_ID="$SHORT_ID"
export PYTHONUNBUFFERED=1


echo
echo "===== VI720 VISUAL RENDER ====="
echo

python video.py 2>&1 |
tee "$RENDER_LOG"

RENDER_STATUS=${PIPESTATUS[0]}

restore_site
trap - EXIT

echo
echo "RENDER STATUS=$RENDER_STATUS"

if [ "$RENDER_STATUS" -ne 0 ]; then

    if [ -f "$OLD_SILENT" ]; then
        cp -f \
        "$OLD_SILENT" \
        "$SILENT_SRC"
    fi

    exit "$RENDER_STATUS"
fi


[ -f "$SILENT_SRC" ] || {
    echo "ERRO: novo video_sem_audio não encontrado."
    exit 7
}

cp -f \
"$SILENT_SRC" \
"$SILENT_COPY"

mkdir -p \
"$DOWNLOADS"

cp -f \
"$SILENT_COPY" \
"$DOWNLOAD_VISUAL"


echo
echo "===== REAL OVERRIDE AUDIT ====="

export VI720_MANIFEST="$MANIFEST"
export VI720_TRACE="$TRACE"

python - <<'PY'
import json
import os
from pathlib import Path

manifest = json.loads(
    Path(
        os.environ[
            "VI720_MANIFEST"
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
        "VI720_TRACE"
    ]
)

if trace.exists():
    for line in trace.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines():

        try:
            events.append(
                json.loads(line)
            )
        except Exception:
            pass

changed = sorted({
    int(scene)

    for event in events

    if (
        event.get("changed")
        and event.get("status") == "SUCCESS"
    )

    for scene in (
        event.get(
            "matched_scenes"
        )
        or []
    )
})

print(
    "EXPECTED:",
    expected
)

print(
    "CHANGED:",
    changed
)

print(
    "ALL ACTIVE CORRECT:",
    changed == expected
)

print(
    "HOOK EVENTS:",
    len(events)
)

if changed != expected:
    raise SystemExit(
        "REAL OVERRIDE AUDIT FAILED"
    )
PY

if [ "$?" -ne 0 ]; then
    exit 8
fi


echo
echo "===== FULL AUDIO + SUBTITLE CANARY ====="

export VI720_SILENT="$SILENT_COPY"
export VI720_ORIGINAL="$ORIGINAL_FINAL"
export VI720_FULL="$FULL_CANARY"
export VI720_DOWNLOAD_FULL="$DOWNLOAD_FULL"
export VI720_SHORT_ID="$SHORT_ID"

python - <<'PY'
import json
import os
import shutil
import subprocess
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

SILENT = Path(
    os.environ[
        "VI720_SILENT"
    ]
)

ORIGINAL = Path(
    os.environ[
        "VI720_ORIGINAL"
    ]
)

FULL = Path(
    os.environ[
        "VI720_FULL"
    ]
)

DOWNLOAD = Path(
    os.environ[
        "VI720_DOWNLOAD_FULL"
    ]
)

SHORT_ID = os.environ[
    "VI720_SHORT_ID"
]


def run(cmd):
    p = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    return p


def subtitle_candidates():
    candidates = []

    roots = [
        BASE / "temp" / SHORT_ID,
        BASE / "legendas",
        BASE / "roteiros",
        BASE / "temp",
    ]

    seen = set()

    for root in roots:
        if not root.exists():
            continue

        try:
            iterator = root.rglob("*")
        except Exception:
            continue

        for path in iterator:
            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".ass",
                ".srt",
            }:
                continue

            resolved = str(path.resolve())

            if resolved in seen:
                continue

            seen.add(
                resolved
            )

            within_short_dir = (
                BASE /
                "temp" /
                SHORT_ID
            ) in path.parents

            mentions_id = (
                SHORT_ID
                in str(path)
            )

            if not (
                within_short_dir
                or mentions_id
            ):
                continue

            score = 0

            if within_short_dir:
                score += 100

            if mentions_id:
                score += 50

            if path.suffix.lower() == ".ass":
                score += 20

            score += min(
                20,
                int(
                    path.stat().st_size
                    / 5000
                )
            )

            candidates.append(
                (
                    score,
                    path
                )
            )

    candidates.sort(
        key=lambda item:
            item[0],
        reverse=True
    )

    return [
        path
        for _, path
        in candidates
    ]


def probe(path):
    p = subprocess.run([
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

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
        "silent canary missing"
    )

if not ORIGINAL.exists():
    raise SystemExit(
        "original final video missing; cannot reuse audio"
    )


subs = subtitle_candidates()

subtitle = (
    subs[0]
    if subs
    else None
)

FULL.parent.mkdir(
    parents=True,
    exist_ok=True
)

FULL.unlink(
    missing_ok=True
)


subtitle_mode = "NONE"
subtitle_error = None


if subtitle:
    escaped = str(
        subtitle
    ).replace(
        "\\",
        "\\\\"
    ).replace(
        "'",
        "\\'"
    ).replace(
        ":",
        "\\:"
    )

    vf = (
        "subtitles="
        f"filename='{escaped}'"
    )

    cmd = [
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
    ]

    result = run(
        cmd
    )

    if (
        result.returncode == 0
        and FULL.exists()
    ):
        subtitle_mode = (
            "FILE_BURNIN"
        )

    else:
        subtitle_error = (
            result.stderr[-2000:]
        )

        FULL.unlink(
            missing_ok=True
        )


if not FULL.exists():
    cmd = [
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
    ]

    result = run(
        cmd
    )

    if result.returncode != 0:
        raise SystemExit(
            "audio mux failed:\n"
            + result.stderr[-2000:]
        )

    if subtitle:
        subtitle_mode = (
            "SUBTITLE_BURNIN_FAILED_AUDIO_ONLY"
        )
    else:
        subtitle_mode = (
            "SUBTITLE_FILE_NOT_FOUND_AUDIO_ONLY"
        )


DOWNLOAD.parent.mkdir(
    parents=True,
    exist_ok=True
)

shutil.copy2(
    FULL,
    DOWNLOAD
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

    if (
        stream.get(
            "codec_type"
        )
        == "audio"
        and audio is None
    ):
        audio = stream


summary = {
    "full_canary":
        str(FULL),

    "downloads":
        str(DOWNLOAD),

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

    "duration":
        info.get(
            "format",
            {}
        ).get(
            "duration"
        ),

    "resolution":
        (
            [
                video.get("width"),
                video.get("height"),
            ]
            if video
            else None
        ),

    "fps":
        (
            video.get(
                "avg_frame_rate"
            )
            if video
            else None
        ),

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
}


summary_path = (
    BASE /
    "temp/vi720_full_canary/"
    "full_summary.json"
)

summary_path.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


print()
print(
    "===== VI720 FULL CANARY SUMMARY ====="
)

for key, value in (
    summary.items()
):
    print(
        key.upper(),
        "=",
        value
    )
PY


VIDEO1="$(sha256sum video.py | awk '{print $1}')"
EXEC1="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
GERAR1="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO1="$(sha256sum roteiro.py | awk '{print $1}')"

MEDIA1="$(
find imagens -type f -printf '%p|%s|%T@\n' 2>/dev/null |
sort | sha256sum | awk '{print $1}'
)"


echo
echo "===== VI720 FINAL INTEGRITY ====="

echo "VIDEO=$([ "$VIDEO0" = "$VIDEO1" ] && echo PASS || echo FAIL)"
echo "EXECUTOR=$([ "$EXEC0" = "$EXEC1" ] && echo PASS || echo FAIL)"
echo "GERAR=$([ "$GERAR0" = "$GERAR1" ] && echo PASS || echo FAIL)"
echo "ROTEIRO=$([ "$ROTEIRO0" = "$ROTEIRO1" ] && echo PASS || echo FAIL)"
echo "PRODUCTION_MEDIA=$([ "$MEDIA0" = "$MEDIA1" ] && echo PASS || echo FAIL)"


echo
echo "===== DOWNLOADS ====="

ls -lh \
"$DOWNLOAD_VISUAL" \
"$DOWNLOAD_FULL" \
2>/dev/null


echo
echo "VI720 RESULT: CANARY_RENDER_COMPLETE"
