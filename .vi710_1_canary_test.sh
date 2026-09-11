#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1

BASE="$HOME/ShortAutoPro"
SHORT_ID="2026-09-01_1433"

MANIFEST="$BASE/temp/vi700_canary/portfolio_manifest.json"

WORK="$BASE/temp/vi710_1_canary"
TRACE="$WORK/command_trace.jsonl"
RUN_LOG="$WORK/render.log"
SUMMARY="$WORK/summary.json"

HOOK="$BASE/vi710_1_command_hook.py"
SITE="$BASE/sitecustomize.py"

SITE_BAK="$WORK/sitecustomize.backup.py"
SITE_FLAG="$WORK/sitecustomize.existed"

RENDER="$BASE/temp/$SHORT_ID/video_sem_audio.mp4"

OLD_RENDER="$WORK/pre_vi710_1_video_sem_audio.bak.mp4"

CANARY="$WORK/ShortAutoPro_VI710_1_Canary.mp4"

DOWNLOADS="$HOME/storage/downloads"
DOWNLOAD_FILE="$DOWNLOADS/ShortAutoPro_VI710_1_Canary.mp4"

MOTION="$BASE/roteiros/motion_plan_${SHORT_ID}.json"

mkdir -p "$WORK"

echo
echo "=============================================="
echo " VI710.1 COMMAND-LEVEL CANARY"
echo "=============================================="

[ -f "$MANIFEST" ] || {
    echo "ERRO: manifest não encontrado"
    exit 2
}

[ -f "$MOTION" ] || {
    echo "ERRO: motion plan não encontrado"
    exit 3
}


# ======================================================
# INTEGRITY BEFORE
# ======================================================

VIDEO0="$(sha256sum video.py | awk '{print $1}')"
EXEC0="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
GERAR0="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO0="$(sha256sum roteiro.py | awk '{print $1}')"
MOTION0="$(sha256sum "$MOTION" | awk '{print $1}')"

MEDIA0="$(
find imagens \
-type f \
-printf '%p|%s|%T@\n' \
2>/dev/null |
sort |
sha256sum |
awk '{print $1}'
)"


# ======================================================
# PRESERVE EXISTING TEMP RENDER
# ======================================================

if [ -f "$RENDER" ]; then

    cp -f \
    "$RENDER" \
    "$OLD_RENDER"

    echo
    echo "TEMP RENDER ANTERIOR PRESERVADO:"
    echo "$OLD_RENDER"

    rm -f "$RENDER"

fi


# ======================================================
# COMMAND HOOK
# ======================================================

cat > "$HOOK" <<'PY'
#!/usr/bin/env python3

import hashlib
import importlib
import json
import os
from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

DEFAULT_TRACE = (
    BASE
    / "temp"
    / "vi710_1_canary"
    / "command_trace.jsonl"
)


def sha256(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def trace(payload):

    path = Path(
        os.getenv(
            "VI710_1_TRACE",
            str(DEFAULT_TRACE)
        )
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        path,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(
            json.dumps(
                payload,
                ensure_ascii=False
            )
            + "\n"
        )


def enabled():

    return (
        os.getenv(
            "VI700_CANARY_MODE",
            "OFF"
        ).upper()
        == "ON"
        and
        os.getenv(
            "VI700_PORTFOLIO_CANARY",
            "OFF"
        ).upper()
        == "ON"
    )


def manifest():

    runtime = importlib.import_module(
        "vi700_runtime_override"
    )

    return runtime.load_manifest()


def active_entries():

    data = manifest()

    scenes = (
        data.get(
            "scenes"
        )
        or {}
    )

    result = {}

    for key, entry in (
        scenes.items()
    ):

        if not entry.get(
            "override_active"
        ):
            continue

        try:

            scene = int(key)

        except Exception:

            continue

        original = entry.get(
            "original_path"
        )

        candidate = entry.get(
            "canary_path"
        )

        expected = entry.get(
            "expected_sha256"
        )

        if not original:
            continue

        if not candidate:
            continue

        candidate_path = Path(
            candidate
        )

        if not candidate_path.exists():

            result[scene] = {
                "valid":
                    False,

                "reason":
                    "candidate_missing",

                "original":
                    original,

                "candidate":
                    candidate,
            }

            continue

        actual = sha256(
            candidate_path
        )

        if (
            expected
            and actual != expected
        ):

            result[scene] = {
                "valid":
                    False,

                "reason":
                    "candidate_hash_mismatch",

                "original":
                    original,

                "candidate":
                    candidate,

                "expected":
                    expected,

                "actual":
                    actual,
            }

            continue

        original_path = Path(
            original
        )

        try:

            relative = str(
                original_path.relative_to(
                    BASE
                )
            )

        except Exception:

            relative = os.path.relpath(
                str(original_path),
                str(BASE)
            )

        result[scene] = {
            "valid":
                True,

            "original":
                str(original_path),

            "relative":
                relative,

            "basename":
                original_path.name,

            "candidate":
                str(candidate_path),

            "sha256":
                actual,

            "mode":
                entry.get(
                    "mode"
                ),
        }

    return result


def validate_all():

    entries = active_entries()

    expected = {
        3,
        8,
        9,
        10,
        11,
    }

    actual = {
        scene
        for scene, entry
        in entries.items()
        if entry.get(
            "valid"
        )
    }

    invalid = {
        scene:
            entry
        for scene, entry
        in entries.items()
        if not entry.get(
            "valid"
        )
    }

    return {
        "expected":
            sorted(expected),

        "valid":
            sorted(actual),

        "invalid":
            invalid,

        "all_valid":
            actual == expected
            and not invalid,
    }


def replace_string(
    value,
    previous=None
):

    if not isinstance(
        value,
        (str, Path)
    ):
        return value, []

    original_value = str(
        value
    )

    new_value = original_value

    matches = []

    entries = active_entries()

    for scene, entry in (
        entries.items()
    ):

        if not entry.get(
            "valid"
        ):
            continue

        original = entry[
            "original"
        ]

        relative = entry[
            "relative"
        ]

        basename = entry[
            "basename"
        ]

        candidate = entry[
            "candidate"
        ]

        replaced = False

        # Absolute path.
        if original in new_value:

            new_value = new_value.replace(
                original,
                candidate
            )

            replaced = True

        # Relative project path.
        elif (
            relative
            and relative
            in new_value
        ):

            new_value = new_value.replace(
                relative,
                candidate
            )

            replaced = True

        # Bare basename is accepted ONLY
        # when it is clearly an FFmpeg input.
        elif (
            new_value == basename
            and previous == "-i"
        ):

            new_value = candidate

            replaced = True

        if replaced:

            matches.append({
                "scene":
                    scene,

                "original":
                    original,

                "candidate":
                    candidate,

                "mode":
                    entry.get(
                        "mode"
                    ),
            })

    if isinstance(
        value,
        Path
    ):

        return Path(
            new_value
        ), matches

    return new_value, matches


def rewrite_command(command):

    if isinstance(
        command,
        str
    ):

        rewritten, matches = (
            replace_string(
                command
            )
        )

        return rewritten, matches

    if isinstance(
        command,
        tuple
    ):

        source = list(
            command
        )

        tuple_mode = True

    elif isinstance(
        command,
        list
    ):

        source = list(
            command
        )

        tuple_mode = False

    else:

        return command, []

    output = []

    all_matches = []

    previous = None

    for token in source:

        rewritten, matches = (
            replace_string(
                token,
                previous=previous
            )
        )

        output.append(
            rewritten
        )

        all_matches.extend(
            matches
        )

        previous = str(
            token
        )

    # De-duplicate scene matches.
    unique = {}

    for item in all_matches:

        unique[
            item["scene"]
        ] = item

    matches = [
        unique[key]
        for key in sorted(
            unique
        )
    ]

    if tuple_mode:

        return tuple(
            output
        ), matches

    return output, matches


def command_preview(command):

    if isinstance(
        command,
        (list, tuple)
    ):

        return [
            str(x)[:300]
            for x in command[:40]
        ]

    return str(
        command
    )[:1200]


def self_test():

    validation = validate_all()

    fake = [
        "ffmpeg",
        "-loop",
        "1",
        "-i",
        str(
            BASE
            / "imagens"
            / "short_2026-09-01_1433"
            / "scene_03.jpg"
        ),
        "-f",
        "null",
        "-"
    ]

    rewritten, matches = (
        rewrite_command(
            fake
        )
    )

    return {
        "validation":
            validation,

        "synthetic_before":
            fake,

        "synthetic_after":
            rewritten,

        "synthetic_matches":
            matches,

        "synthetic_pass":
            any(
                item[
                    "scene"
                ] == 3
                for item in matches
            ),
    }


def activate():

    module = importlib.import_module(
        "vi6_95_scene_executor"
    )

    if getattr(
        module,
        "_vi710_1_command_hook",
        False
    ):

        return {
            "patched":
                True,

            "reason":
                "already_patched",
        }

    original_execute = getattr(
        module,
        "execute"
    )

    def patched_execute(
        command,
        **run_kwargs
    ):

        use_canary = enabled()

        rewritten = command

        matches = []

        if use_canary:

            rewritten, matches = (
                rewrite_command(
                    command
                )
            )

        event = {
            "enabled":
                use_canary,

            "matched_scenes":
                [
                    item[
                        "scene"
                    ]
                    for item in matches
                ],

            "changed":
                bool(
                    matches
                ),

            "replacements":
                matches,

            "command_before":
                command_preview(
                    command
                ),

            "command_after":
                command_preview(
                    rewritten
                ),
        }

        try:

            result = original_execute(
                rewritten,
                **run_kwargs
            )

            event[
                "status"
            ] = "SUCCESS"

            trace(
                event
            )

            return result

        except BaseException as exc:

            event[
                "status"
            ] = "ERROR"

            event[
                "error"
            ] = (
                type(exc).__name__
                + ": "
                + str(exc)[:500]
            )

            trace(
                event
            )

            raise

    setattr(
        module,
        "_vi710_1_original_execute",
        original_execute
    )

    setattr(
        module,
        "execute",
        patched_execute
    )

    setattr(
        module,
        "_vi710_1_command_hook",
        True
    )

    return {
        "patched":
            True,

        "validation":
            validate_all(),
    }
PY


# ======================================================
# TEMPORARY SITECUSTOMIZE
# ======================================================

if [ -f "$SITE" ]; then

    cp -f \
    "$SITE" \
    "$SITE_BAK"

    echo "1" > "$SITE_FLAG"

else

    echo "0" > "$SITE_FLAG"

fi


restore_site() {

    if (
        [ -f "$SITE_FLAG" ] &&
        [ "$(cat "$SITE_FLAG")" = "1" ] &&
        [ -f "$SITE_BAK" ]
    ); then

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
            "VI710.1 HOOK ERROR:",
            type(exc).__name__,
            str(exc)[:500],
            file=sys.stderr
        )
PY


# ======================================================
# PREFLIGHT
# ======================================================

echo
echo "===== VI710.1 PREFLIGHT ====="

export PYTHONPATH="$BASE${PYTHONPATH:+:$PYTHONPATH}"

export VI700_CANARY_MODE="ON"

export VI700_PORTFOLIO_CANARY="ON"

export VI700_PORTFOLIO_MANIFEST="$MANIFEST"

# Disable older experimental delegates.
export VI710_CANARY_MODE="OFF"
export VI730_CANARY_MODE="OFF"

export VI710_1_TRACE="$TRACE"

export SHORT_ID="$SHORT_ID"
export SHORTAUTO_SHORT_ID="$SHORT_ID"
export SHORTAUTO_FORCE_SHORT_ID="$SHORT_ID"


python - <<'PY'
import json

import vi710_1_command_hook as hook

result = hook.self_test()

print(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    )
)

if not result[
    "validation"
][
    "all_valid"
]:

    raise SystemExit(
        "VI710.1 PREFLIGHT FAILED: "
        "active assets invalid"
    )

if not result[
    "synthetic_pass"
]:

    raise SystemExit(
        "VI710.1 PREFLIGHT FAILED: "
        "command rewrite failed"
    )
PY

PREFLIGHT_STATUS=$?

if [ "$PREFLIGHT_STATUS" -ne 0 ]; then

    echo
    echo "CANARY CANCELADO ANTES DO RENDER."

    exit "$PREFLIGHT_STATUS"

fi


# ======================================================
# RENDER
# ======================================================

rm -f "$TRACE"

echo
echo "===== VI710.1 REAL CANARY RENDER ====="
echo

python video.py 2>&1 |
tee "$RUN_LOG"

RENDER_STATUS=${PIPESTATUS[0]}


echo
echo "RENDER STATUS=$RENDER_STATUS"


# ======================================================
# ANALYSIS + COPY
# ======================================================

export VI710_1_RENDER="$RENDER"
export VI710_1_CANARY="$CANARY"
export VI710_1_SUMMARY="$SUMMARY"
export VI710_1_DOWNLOAD="$DOWNLOAD_FILE"


python - <<'PY'
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


TRACE = Path(
    os.environ[
        "VI710_1_TRACE"
    ]
)

RENDER = Path(
    os.environ[
        "VI710_1_RENDER"
    ]
)

CANARY = Path(
    os.environ[
        "VI710_1_CANARY"
    ]
)

SUMMARY = Path(
    os.environ[
        "VI710_1_SUMMARY"
    ]
)

DOWNLOAD = Path(
    os.environ[
        "VI710_1_DOWNLOAD"
    ]
)

EXPECTED = [
    3,
    8,
    9,
    10,
    11,
]


def sha256(path):

    h = hashlib.sha256()

    with open(path, "rb") as f:

        while True:

            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


events = []

if TRACE.exists():

    for line in TRACE.read_text(
        encoding="utf-8",
        errors="ignore"
    ).splitlines():

        line = line.strip()

        if not line:
            continue

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
        and event.get(
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


successful_events = [
    event
    for event in events
    if event.get(
        "status"
    )
    == "SUCCESS"
]


error_events = [
    event
    for event in events
    if event.get(
        "status"
    )
    == "ERROR"
]


ffprobe = {}

duration = None
width = None
height = None
fps = None


if RENDER.exists():

    CANARY.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        RENDER,
        CANARY
    )

    try:

        raw = subprocess.check_output([
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(CANARY),
        ])

        ffprobe = json.loads(
            raw.decode(
                "utf-8",
                errors="ignore"
            )
        )

        duration = (
            ffprobe.get(
                "format",
                {}
            ).get(
                "duration"
            )
        )

        for stream in (
            ffprobe.get(
                "streams",
                []
            )
        ):

            if stream.get(
                "codec_type"
            ) != "video":
                continue

            width = stream.get(
                "width"
            )

            height = stream.get(
                "height"
            )

            fps = (
                stream.get(
                    "avg_frame_rate"
                )
                or stream.get(
                    "r_frame_rate"
                )
            )

            break

    except Exception as exc:

        ffprobe = {
            "error":
                type(exc).__name__
                + ":"
                + str(exc)
        }


download_copied = False

download_error = None


if CANARY.exists():

    try:

        DOWNLOAD.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            CANARY,
            DOWNLOAD
        )

        download_copied = True

    except Exception as exc:

        download_error = (
            type(exc).__name__
            + ": "
            + str(exc)
        )


summary = {
    "render_exists":
        RENDER.exists(),

    "render_path":
        str(
            RENDER
        ),

    "canary_copy":
        (
            str(CANARY)
            if CANARY.exists()
            else None
        ),

    "downloads_copy":
        (
            str(DOWNLOAD)
            if download_copied
            else None
        ),

    "download_error":
        download_error,

    "hook_events":
        len(events),

    "successful_hook_events":
        len(
            successful_events
        ),

    "error_hook_events":
        len(
            error_events
        ),

    "changed_scenes":
        changed,

    "expected_active":
        EXPECTED,

    "all_five_correct":
        changed == EXPECTED,

    "duration":
        duration,

    "width":
        width,

    "height":
        height,

    "fps":
        fps,

    "canary_sha256":
        (
            sha256(
                CANARY
            )
            if CANARY.exists()
            else None
        ),
}


SUMMARY.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


print()
print(
    "=============================================="
)

print(
    " VI710.1 CANARY SUMMARY"
)

print(
    "=============================================="
)

print(
    "HOOK EVENTS:",
    len(events)
)

print(
    "SUCCESS EVENTS:",
    len(
        successful_events
    )
)

print(
    "ERROR EVENTS:",
    len(
        error_events
    )
)

print()

print(
    "CHANGED SCENES:",
    changed
)

print(
    "EXPECTED:",
    EXPECTED
)

print(
    "ALL FIVE CORRECT:",
    changed == EXPECTED
)

print()

print(
    "DURATION:",
    duration
)

print(
    "RESOLUTION:",
    width,
    "x",
    height
)

print(
    "FPS:",
    fps
)

print()

print(
    "CANARY:",
    (
        CANARY
        if CANARY.exists()
        else None
    )
)

print(
    "DOWNLOADS:",
    (
        DOWNLOAD
        if download_copied
        else None
    )
)

print()

print(
    "===== REAL COMMAND OVERRIDES ====="
)

for event in events:

    if not event.get(
        "changed"
    ):
        continue

    print(
        "SCENES",
        event.get(
            "matched_scenes"
        ),
        "| status=",
        event.get(
            "status"
        )
    )

    for replacement in (
        event.get(
            "replacements"
        )
        or []
    ):

        print(
            "   SCENE",
            replacement[
                "scene"
            ]
        )

        print(
            "      FROM:",
            replacement[
                "original"
            ]
        )

        print(
            "      TO:",
            replacement[
                "candidate"
            ]
        )


if error_events:

    print()

    print(
        "===== HOOK ERRORS ====="
    )

    for event in error_events:

        print(
            event.get(
                "error"
            )
        )
PY


# ======================================================
# RESTORE OLD TEMP RENDER ON FAILURE ONLY
# ======================================================

if [ "$RENDER_STATUS" -ne 0 ]; then

    echo
    echo "RENDER FALHOU."

    if [ -f "$OLD_RENDER" ]; then

        cp -f \
        "$OLD_RENDER" \
        "$RENDER"

        echo \
        "TEMP RENDER ANTERIOR RESTAURADO."

    fi

fi


# ======================================================
# CORE INTEGRITY
# ======================================================

VIDEO1="$(sha256sum video.py | awk '{print $1}')"
EXEC1="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
GERAR1="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO1="$(sha256sum roteiro.py | awk '{print $1}')"
MOTION1="$(sha256sum "$MOTION" | awk '{print $1}')"

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
echo "===== VI710.1 INTEGRITY ====="

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
echo "===== FILES ====="

ls -lh \
"$CANARY" \
"$SUMMARY" \
"$TRACE" \
2>/dev/null


if [ -f "$DOWNLOAD_FILE" ]; then

    echo
    echo "DOWNLOAD READY:"

    ls -lh \
    "$DOWNLOAD_FILE"

fi


# Restore temporary sitecustomize now,
# instead of waiting only for EXIT trap.
restore_site

trap - EXIT


if [ "$RENDER_STATUS" -ne 0 ]; then

    exit "$RENDER_STATUS"

fi


ALL_CORRECT="$(
python - <<'PY'
import json
from pathlib import Path

p = Path(
    "temp/vi710_1_canary/summary.json"
)

if not p.exists():

    print("False")

else:

    data = json.loads(
        p.read_text(
            encoding="utf-8"
        )
    )

    print(
        data.get(
            "all_five_correct",
            False
        )
    )
PY
)"


echo

if [ "$ALL_CORRECT" = "True" ]; then

    echo \
    "VI710.1 RESULT: FIVE_SCENE_CANARY_CERTIFIED"

else

    echo \
    "VI710.1 RESULT: CANARY_NOT_CERTIFIED"

fi
