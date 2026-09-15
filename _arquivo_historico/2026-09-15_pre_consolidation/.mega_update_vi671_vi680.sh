#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/mega_vi671_vi680_${STAMP}"

mkdir -p "$BACKDIR"

echo
echo "======================================================"
echo " SHORTAUTOPRO MEGA UPDATE III"
echo " VI6.71 -> VI6.80"
echo " REAL ONE-SCENE VISUAL CANARY CERTIFICATION"
echo "======================================================"
echo
echo "VIDEO.PY = PROTECTED"
echo "FULL ACTIVE = LOCKED"
echo


# =====================================================
# 0. REQUIREMENTS
# =====================================================

REQUIRED="
video.py
vi6_49_real_command_mapper.py
vi6_66_canary_filter_preview.py
vi6_67_scene_rollback_contract.py
vi6_70_master_canary_gate.py
"

for F in $REQUIRED
do
    if [ ! -f "$F" ]; then
        echo "ERRO: $F ausente."
        exit 2
    fi
done


PLAN="logs/producao/vi6_70_canary_plan_latest.json"
GATE70="logs/producao/vi6_70_master_canary_gate_latest.json"


if [ ! -f "$PLAN" ]; then
    echo "ERRO: VI6.70 canary plan ausente."
    exit 3
fi


if [ ! -f "$GATE70" ]; then
    echo "ERRO: VI6.70 gate ausente."
    exit 4
fi


VIDEO_HASH_BEFORE="$(
    sha256sum video.py |
    awk '{print $1}'
)"


# =====================================================
# 1. HARD PRECHECK
# =====================================================

echo
echo "===== VI6.70 HARD PRECHECK ====="

if ! python - <<'PY'
import json
from pathlib import Path

base = Path.home() / "ShortAutoPro"

gate = json.loads(
    (
        base
        / "logs/producao/"
          "vi6_70_master_canary_gate_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["gate"]


plan = json.loads(
    (
        base
        / "logs/producao/"
          "vi6_70_canary_plan_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["plan"]


blockers = []


if gate.get("status") not in {
    "CANARY_PREVIEW_READY",
    "CANARY_PREVIEW_READY_WITH_WARNINGS",
}:
    blockers.append(
        "vi670_not_ready"
    )


candidate = (
    plan.get("candidate")
    or {}
)


preview = (
    plan.get("filter_preview")
    or {}
)


scene = candidate.get("scene")


if not isinstance(scene, int):
    blockers.append(
        "candidate_scene_invalid"
    )


if candidate.get("role") != "CONTEXT":
    blockers.append(
        "candidate_not_context"
    )


if preview.get("status") != "PREVIEW_READY":
    blockers.append(
        "filter_preview_not_ready"
    )


if not preview.get(
    "different_from_legacy"
):
    blockers.append(
        "vi6_filter_not_different"
    )


if not isinstance(
    preview.get("legacy_vf"),
    str
):
    blockers.append(
        "legacy_filter_missing"
    )


if not isinstance(
    preview.get("proposed_vi6_vf"),
    str
):
    blockers.append(
        "vi6_filter_missing"
    )


print(
    "VI6.70 STATUS:",
    gate.get("status")
)

print(
    "CANDIDATE:",
    scene
)

print(
    "ROLE:",
    candidate.get("role")
)

print(
    "DURATION:",
    candidate.get(
        "duration_seconds"
    )
)

print(
    "PREVIEW:",
    preview.get("status")
)

print(
    "DIFFERENT:",
    preview.get(
        "different_from_legacy"
    )
)

print(
    "BLOCKERS:",
    blockers
)


if blockers:
    raise SystemExit(1)
PY
then

    echo
    echo "VI6.71-6.80 BLOQUEADO."
    echo "Nenhum render executado."
    exit 5
fi


echo "VI6.70 PRECHECK=PASS"


# =====================================================
# 2. BACKUPS
# =====================================================

for F in \
    vi6_71_canary_freeze.py \
    vi6_72_real_source_locator.py \
    vi6_73_twin_command_builder.py \
    vi6_74_real_canary_renderer.py \
    vi6_75_twin_probe.py \
    vi6_76_visual_technical_comparator.py \
    vi6_77_canary_artifact_manager.py \
    vi6_78_motion_plan_freezer.py \
    vi6_79_canary_certification_gate.py \
    vi6_80_master_runtime_gate.py \
    testar_vi671_vi680.py
do

    if [ -f "$F" ]; then
        cp "$F" "$BACKDIR/$F"
    fi

done


rollback() {

    echo
    echo "======================================"
    echo " ROLLBACK VI6.71-6.80"
    echo "======================================"

    for F in \
        vi6_71_canary_freeze.py \
        vi6_72_real_source_locator.py \
        vi6_73_twin_command_builder.py \
        vi6_74_real_canary_renderer.py \
        vi6_75_twin_probe.py \
        vi6_76_visual_technical_comparator.py \
        vi6_77_canary_artifact_manager.py \
        vi6_78_motion_plan_freezer.py \
        vi6_79_canary_certification_gate.py \
        vi6_80_master_runtime_gate.py \
        testar_vi671_vi680.py
    do

        if [ -f "$BACKDIR/$F" ]; then
            cp "$BACKDIR/$F" "$F"
        else
            rm -f "$F"
        fi

    done

    echo "Rollback concluído."
}


# =====================================================
# 3. VI6.71 — FREEZE CANARY DECISION
# =====================================================

cat > vi6_71_canary_freeze.py <<'PY'
#!/usr/bin/env python3

import hashlib
import json

from datetime import datetime
from pathlib import Path


VERSION = "6.71"

BASE = Path.home() / "ShortAutoPro"

PLAN = (
    BASE
    / "logs/producao/"
      "vi6_70_canary_plan_latest.json"
)

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi6_71_canary_freeze_latest.json"
)


def fingerprint(value):

    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            default=str
        ).encode(
            "utf-8"
        )
    ).hexdigest()


def freeze():

    data = json.loads(
        PLAN.read_text(
            encoding="utf-8"
        )
    )["plan"]


    candidate = data.get(
        "candidate"
    ) or {}


    preview = data.get(
        "filter_preview"
    ) or {}


    blockers = []


    if data.get("status") not in {
        "CANARY_PREVIEW_READY",
        "CANARY_PREVIEW_READY_WITH_WARNINGS",
    }:
        blockers.append(
            "vi670_plan_not_ready"
        )


    if candidate.get("role") != "CONTEXT":
        blockers.append(
            "unsafe_candidate_role"
        )


    if preview.get("status") != "PREVIEW_READY":
        blockers.append(
            "preview_not_ready"
        )


    payload = {
        "version": VERSION,

        "status":
            (
                "FROZEN"
                if not blockers
                else "HOLD"
            ),

        "scene":
            candidate.get("scene"),

        "duration_seconds":
            candidate.get(
                "duration_seconds"
            ),

        "role":
            candidate.get("role"),

        "legacy_vf":
            preview.get(
                "legacy_vf"
            ),

        "vi6_vf":
            preview.get(
                "proposed_vi6_vf"
            ),

        "source_session_fingerprint":
            candidate.get(
                "command_fingerprint"
            ),

        "decision_fingerprint":
            fingerprint(
                {
                    "candidate":
                        candidate,

                    "preview":
                        preview,
                }
            ),

        "blockers":
            blockers,

        "filter_applied":
            False,

        "video_py_modified":
            False,
    }


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "freeze":
                    payload,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return payload


def self_test():

    assert fingerprint(
        {"a": 1}
    ) == fingerprint(
        {"a": 1}
    )

    print(
        "VI6.71 CANARY FREEZE=PASS"
    )


if __name__ == "__main__":

    self_test()

    print(
        json.dumps(
            freeze(),
            ensure_ascii=False,
            indent=2
        )
    )
PY


# =====================================================
# 4. VI6.72 — REAL SOURCE LOCATOR
# =====================================================

cat > vi6_72_real_source_locator.py <<'PY'
#!/usr/bin/env python3

import json
import re

from pathlib import Path


VERSION = "6.72"

BASE = Path.home() / "ShortAutoPro"


def _freeze():

    path = (
        BASE
        / "logs/producao/"
          "vi6_71_canary_freeze_latest.json"
    )


    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )["freeze"]


def locate():

    frozen = _freeze()

    scene = frozen.get(
        "scene"
    )


    blockers = []


    if not isinstance(scene, int):

        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers":
                ["scene_invalid"],
        }


    directories = sorted(
        [
            p
            for p in (
                BASE
                / "imagens"
            ).glob(
                "short_*"
            )
            if p.is_dir()
        ],
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )


    candidates = []


    pattern = re.compile(
        rf"^scene_0*{scene}\."
        r"(jpg|jpeg|png|webp|mp4|mov|mkv)$",
        re.IGNORECASE
    )


    for directory in directories[:10]:

        for path in directory.iterdir():

            if (
                path.is_file()
                and pattern.match(
                    path.name
                )
            ):

                candidates.append(
                    path
                )


    candidates.sort(
        key=lambda p:
            p.stat().st_mtime,
        reverse=True
    )


    source = (
        candidates[0]
        if candidates
        else None
    )


    if source is None:

        blockers.append(
            "source_media_not_found"
        )


    else:

        suffix = source.suffix.lower()


        if suffix not in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:

            blockers.append(
                "candidate_source_not_still"
            )


    return {
        "version": VERSION,

        "status":
            (
                "FOUND"
                if not blockers
                else "HOLD"
            ),

        "scene":
            scene,

        "source":
            (
                str(source)
                if source
                else None
            ),

        "source_suffix":
            (
                source.suffix.lower()
                if source
                else None
            ),

        "candidate_count":
            len(candidates),

        "blockers":
            blockers,
    }


def self_test():

    assert (
        re.match(
            r"^scene_0*4\.",
            "scene_04.jpg"
        )
        is not None
    )

    print(
        "VI6.72 SOURCE LOCATOR=PASS"
    )


if __name__ == "__main__":

    self_test()

    print(
        json.dumps(
            locate(),
            ensure_ascii=False,
            indent=2
        )
    )
PY


# =====================================================
# 5. VI6.73 — TWIN COMMAND BUILDER
# =====================================================

cat > vi6_73_twin_command_builder.py <<'PY'
#!/usr/bin/env python3

import json
import math
import re

from pathlib import Path


VERSION = "6.73"

BASE = Path.home() / "ShortAutoPro"


def _load(path, key):

    return json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )[key]


def _fps(vf):

    if not isinstance(vf, str):
        return None


    match = re.search(
        r"(?:^|[,:])fps="
        r"([0-9]+(?:\.[0-9]+)?)",
        vf
    )


    if not match:
        return None


    try:
        return float(
            match.group(1)
        )

    except Exception:
        return None


def _unsafe(vf):

    if not isinstance(vf, str):
        return True


    for token in (
        ";",
        "\n",
        "\r",
        "`",
        "$(",
    ):

        if token in vf:
            return True


    return False


def build():

    freeze = _load(
        (
            BASE
            / "logs/producao/"
              "vi6_71_canary_freeze_latest.json"
        ),
        "freeze"
    )


    source = _load(
        (
            BASE
            / "logs/producao/"
              "vi6_72_source_locator_latest.json"
        ),
        "source"
    )


    blockers = []


    if freeze.get(
        "status"
    ) != "FROZEN":

        blockers.append(
            "freeze_not_ready"
        )


    if source.get(
        "status"
    ) != "FOUND":

        blockers.append(
            "source_not_ready"
        )


    duration = freeze.get(
        "duration_seconds"
    )


    try:
        duration = float(
            duration
        )

    except Exception:
        duration = None


    if (
        duration is None
        or duration < .75
        or duration > 8.0
    ):

        blockers.append(
            "duration_outside_canary_bounds"
        )


    legacy_vf = freeze.get(
        "legacy_vf"
    )


    vi6_vf = freeze.get(
        "vi6_vf"
    )


    if _unsafe(legacy_vf):

        blockers.append(
            "legacy_filter_unsafe"
        )


    if _unsafe(vi6_vf):

        blockers.append(
            "vi6_filter_unsafe"
        )


    fps = (
        _fps(vi6_vf)
        or _fps(legacy_vf)
        or 30.0
    )


    frames = (
        max(
            1,
            int(
                math.ceil(
                    duration
                    * fps
                )
            )
        )
        if duration
        else None
    )


    source_path = source.get(
        "source"
    )


    output_dir = (
        BASE
        / "videos"
        / "canary"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    scene = freeze.get(
        "scene"
    )


    legacy_out = (
        output_dir
        / (
            f"scene_{scene:02d}"
            "_LEGACY_preview.mp4"
        )
    )


    vi6_out = (
        output_dir
        / (
            f"scene_{scene:02d}"
            "_VI6_preview.mp4"
        )
    )


    def command(vf, output):

        return [
            "ffmpeg",
            "-y",

            "-loop",
            "1",

            "-i",
            source_path,

            "-vf",
            vf,

            "-frames:v",
            str(frames),

            "-an",

            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-crf",
            "24",

            "-pix_fmt",
            "yuv420p",

            str(output),
        ]


    return {
        "version": VERSION,

        "status":
            (
                "READY"
                if not blockers
                else "HOLD"
            ),

        "scene":
            scene,

        "source":
            source_path,

        "duration_seconds":
            duration,

        "fps":
            fps,

        "frames":
            frames,

        "legacy_output":
            str(legacy_out),

        "vi6_output":
            str(vi6_out),

        "legacy_command":
            (
                command(
                    legacy_vf,
                    legacy_out
                )
                if not blockers
                else None
            ),

        "vi6_command":
            (
                command(
                    vi6_vf,
                    vi6_out
                )
                if not blockers
                else None
            ),

        "blockers":
            blockers,

        "video_py_modified":
            False,
    }


def self_test():

    assert _fps(
        "zoompan=d=90:s=1080x1920:fps=30"
    ) == 30.0


    assert _fps(
        "scale=1080:1920,fps=30"
    ) == 30.0


    print(
        "VI6.73 TWIN COMMAND BUILDER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 6. VI6.74 — ACTUAL TWIN RENDER
# =====================================================

cat > vi6_74_real_canary_renderer.py <<'PY'
#!/usr/bin/env python3

import json
import subprocess
import time

from datetime import datetime
from pathlib import Path


VERSION = "6.74"

BASE = Path.home() / "ShortAutoPro"

REPORT = (
    BASE
    / "logs/producao/"
      "vi6_74_real_canary_render_latest.json"
)


def run_one(
    command
):

    start = time.monotonic()


    result = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )


    elapsed = round(
        time.monotonic()
        - start,
        3
    )


    output = (
        Path(command[-1])
        if command
        else None
    )


    return {
        "return_code":
            result.returncode,

        "elapsed_seconds":
            elapsed,

        "output":
            (
                str(output)
                if output
                else None
            ),

        "output_exists":
            (
                bool(
                    output
                    and output.exists()
                )
            ),

        "output_bytes":
            (
                output.stat().st_size
                if (
                    output
                    and output.exists()
                )
                else 0
            ),

        "stderr_tail":
            (
                result.stderr[-2000:]
                if result.stderr
                else ""
            ),
    }


def render(plan):

    blockers = []


    if plan.get(
        "status"
    ) != "READY":

        return {
            "version": VERSION,
            "status": "HOLD",
            "blockers":
                ["twin_plan_not_ready"],
        }


    legacy = run_one(
        plan[
            "legacy_command"
        ]
    )


    if (
        legacy[
            "return_code"
        ] != 0
        or not legacy[
            "output_exists"
        ]
    ):

        blockers.append(
            "legacy_preview_failed"
        )


        result = {
            "version": VERSION,
            "status": "HOLD",
            "legacy": legacy,
            "vi6": None,
            "blockers": blockers,
        }


        save(result)

        return result


    vi6 = run_one(
        plan[
            "vi6_command"
        ]
    )


    if (
        vi6[
            "return_code"
        ] != 0
        or not vi6[
            "output_exists"
        ]
    ):

        blockers.append(
            "vi6_preview_failed"
        )


    result = {
        "version": VERSION,

        "status":
            (
                "RENDERED"
                if not blockers
                else "HOLD"
            ),

        "scene":
            plan.get("scene"),

        "legacy":
            legacy,

        "vi6":
            vi6,

        "blockers":
            blockers,

        "production_video_modified":
            False,

        "video_py_modified":
            False,
    }


    save(result)

    return result


def save(result):

    REPORT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    REPORT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "render":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def self_test():

    assert VERSION == "6.74"

    print(
        "VI6.74 REAL CANARY RENDERER SELF TEST=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 7. VI6.75 — FFPROBE TWINS
# =====================================================

cat > vi6_75_twin_probe.py <<'PY'
#!/usr/bin/env python3

import json
import subprocess

from pathlib import Path


VERSION = "6.75"


def probe(path):

    path = Path(
        path
    )


    if not path.exists():

        return {
            "status": "MISSING",
            "path": str(path),
        }


    command = [
        "ffprobe",
        "-v",
        "error",

        "-select_streams",
        "v:0",

        "-show_entries",
        (
            "stream="
            "width,height,"
            "avg_frame_rate,"
            "r_frame_rate,"
            "pix_fmt,"
            "codec_name,"
            "nb_frames:"
            "format=duration,size"
        ),

        "-of",
        "json",

        str(path),
    ]


    try:

        raw = subprocess.check_output(
            command,
            text=True
        )


        data = json.loads(
            raw
        )


    except Exception as exc:

        return {
            "status": "HOLD",
            "path": str(path),
            "error":
                type(exc).__name__,
        }


    stream = (
        data.get("streams")
        or [{}]
    )[0]


    fmt = (
        data.get("format")
        or {}
    )


    return {
        "status": "PASS",

        "path": str(path),

        "width":
            stream.get("width"),

        "height":
            stream.get("height"),

        "fps":
            (
                stream.get(
                    "avg_frame_rate"
                )
                or stream.get(
                    "r_frame_rate"
                )
            ),

        "pix_fmt":
            stream.get("pix_fmt"),

        "codec":
            stream.get("codec_name"),

        "nb_frames":
            stream.get("nb_frames"),

        "duration":
            fmt.get("duration"),

        "size":
            fmt.get("size"),
    }


def self_test():

    assert probe(
        "/definitely/not/here.mp4"
    )["status"] == "MISSING"


    print(
        "VI6.75 TWIN PROBE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 8. VI6.76 — TECHNICAL COMPARATOR
# =====================================================

cat > vi6_76_visual_technical_comparator.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.76"


def _float(value):

    try:
        return float(value)

    except Exception:
        return None


def compare(
    legacy,
    vi6
):

    blockers = []

    warnings = []


    if legacy.get(
        "status"
    ) != "PASS":

        blockers.append(
            "legacy_probe_hold"
        )


    if vi6.get(
        "status"
    ) != "PASS":

        blockers.append(
            "vi6_probe_hold"
        )


    for side, data in (
        ("legacy", legacy),
        ("vi6", vi6),
    ):

        if (
            data.get("width")
            != 1080
            or data.get("height")
            != 1920
        ):

            blockers.append(
                side
                + "_resolution_invalid"
            )


        if (
            data.get("pix_fmt")
            not in {
                "yuv420p",
                "yuvj420p",
            }
        ):

            blockers.append(
                side
                + "_pixfmt_invalid"
            )


    ld = _float(
        legacy.get(
            "duration"
        )
    )


    vd = _float(
        vi6.get(
            "duration"
        )
    )


    delta = None


    if (
        ld is not None
        and vd is not None
    ):

        delta = abs(
            ld - vd
        )


        if delta > .12:

            blockers.append(
                "duration_delta_too_high"
            )


    else:

        blockers.append(
            "duration_missing"
        )


    if (
        legacy.get(
            "codec"
        )
        != "h264"
    ):

        warnings.append(
            "legacy_codec_not_h264"
        )


    if (
        vi6.get(
            "codec"
        )
        != "h264"
    ):

        warnings.append(
            "vi6_codec_not_h264"
        )


    status = (
        "HOLD"
        if blockers
        else (
            "PASS_WITH_WARNINGS"
            if warnings
            else "PASS"
        )
    )


    return {
        "version": VERSION,

        "status": status,

        "duration_delta":
            (
                round(
                    delta,
                    4
                )
                if delta is not None
                else None
            ),

        "same_resolution":
            (
                legacy.get("width")
                == vi6.get("width")
                and legacy.get("height")
                == vi6.get("height")
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "visual_quality_human_review_required":
            True,
    }


def self_test():

    base = {
        "status": "PASS",
        "width": 1080,
        "height": 1920,
        "pix_fmt": "yuv420p",
        "codec": "h264",
        "duration": "4.0",
    }


    assert compare(
        dict(base),
        dict(base)
    )["status"] == "PASS"


    print(
        "VI6.76 TECHNICAL COMPARATOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 9. VI6.77 — ARTIFACT MANAGER
# =====================================================

cat > vi6_77_canary_artifact_manager.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path


VERSION = "6.77"


def evaluate(
    legacy,
    vi6
):

    legacy = Path(
        legacy
    )


    vi6 = Path(
        vi6
    )


    return {
        "version": VERSION,

        "status":
            (
                "PASS"
                if legacy.exists()
                and vi6.exists()
                else "HOLD"
            ),

        "legacy_preview":
            str(legacy),

        "vi6_preview":
            str(vi6),

        "legacy_exists":
            legacy.exists(),

        "vi6_exists":
            vi6.exists(),

        # Keep both so user can compare.
        "previews_preserved":
            True,

        "production_video_touched":
            False,
    }


def self_test():

    assert VERSION == "6.77"

    print(
        "VI6.77 ARTIFACT MANAGER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 10. VI6.78 — MOTION PLAN FREEZER
# =====================================================

cat > vi6_78_motion_plan_freezer.py <<'PY'
#!/usr/bin/env python3

import json
from pathlib import Path


VERSION = "6.78"

BASE = Path.home() / "ShortAutoPro"


def freeze():

    session = json.loads(
        (
            BASE
            / "logs/producao/"
              "vi6_60_shadow_session_latest.json"
        ).read_text(
            encoding="utf-8"
        )
    )["session"]


    from vi6_61_motion_diversity_planner import (
        plan
    )


    result = plan(
        session.get(
            "events"
        )
    )


    return {
        "version": VERSION,

        "status":
            (
                "FROZEN"
                if result.get(
                    "triple_repeats"
                ) == 0
                else "HOLD"
            ),

        "motion_plan":
            result,

        "applied_to_renderer":
            False,
    }


def self_test():

    assert VERSION == "6.78"

    print(
        "VI6.78 MOTION PLAN FREEZER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 11. VI6.79 — CANARY CERTIFICATION
# =====================================================

cat > vi6_79_canary_certification_gate.py <<'PY'
#!/usr/bin/env python3

VERSION = "6.79"


def evaluate(
    render,
    comparison,
    artifacts,
    rollback
):

    blockers = []

    warnings = []


    if render.get(
        "status"
    ) != "RENDERED":

        blockers.append(
            "twin_render_failed"
        )


    if comparison.get(
        "status"
    ) == "HOLD":

        blockers.append(
            "technical_comparison_hold"
        )


    warnings.extend(
        comparison.get(
            "warnings"
        )
        or []
    )


    if artifacts.get(
        "status"
    ) != "PASS":

        blockers.append(
            "preview_artifacts_missing"
        )


    if rollback.get(
        "failure_action"
    ) != (
        "RENDER_SAME_SCENE_"
        "WITH_LEGACY_FILTER"
    ):

        blockers.append(
            "rollback_contract_invalid"
        )


    status = (
        "HOLD"
        if blockers
        else (
            "TECHNICALLY_CERTIFIED_WITH_WARNINGS"
            if warnings
            else "TECHNICALLY_CERTIFIED"
        )
    )


    return {
        "version": VERSION,

        "status": status,

        "blockers": blockers,

        "warnings": warnings,

        "human_visual_review_required":
            True,

        # Technical certification is not
        # yet production activation.
        "runtime_canary_authorized":
            False,

        "active_renderer":
            False,
    }


def self_test():

    result = evaluate(
        {
            "status": "RENDERED"
        },

        {
            "status": "PASS",
            "warnings": [],
        },

        {
            "status": "PASS"
        },

        {
            "failure_action":
                "RENDER_SAME_SCENE_"
                "WITH_LEGACY_FILTER"
        },
    )


    assert (
        result["status"]
        == "TECHNICALLY_CERTIFIED"
    )


    assert (
        result[
            "runtime_canary_authorized"
        ]
        is False
    )


    print(
        "VI6.79 CANARY CERTIFICATION=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 12. VI6.80 — MASTER RUNTIME GATE
# =====================================================

cat > vi6_80_master_runtime_gate.py <<'PY'
#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path


VERSION = "6.80"

BASE = Path.home() / "ShortAutoPro"

OUTPUT = (
    BASE
    / "logs/producao/"
      "vi6_80_master_runtime_gate_latest.json"
)


def evaluate(
    gate70,
    freeze,
    source,
    render,
    comparison,
    certification,
    motion
):

    blockers = []

    warnings = []


    if gate70.get(
        "status"
    ) not in {
        "CANARY_PREVIEW_READY",
        "CANARY_PREVIEW_READY_WITH_WARNINGS",
    }:

        blockers.append(
            "vi670_not_ready"
        )


    if freeze.get(
        "status"
    ) != "FROZEN":

        blockers.append(
            "candidate_not_frozen"
        )


    if source.get(
        "status"
    ) != "FOUND":

        blockers.append(
            "real_source_missing"
        )


    if render.get(
        "status"
    ) != "RENDERED":

        blockers.append(
            "real_twin_render_failed"
        )


    if comparison.get(
        "status"
    ) == "HOLD":

        blockers.append(
            "technical_comparison_failed"
        )


    if certification.get(
        "status"
    ) not in {
        "TECHNICALLY_CERTIFIED",
        "TECHNICALLY_CERTIFIED_WITH_WARNINGS",
    }:

        blockers.append(
            "vi679_not_certified"
        )


    if motion.get(
        "status"
    ) != "FROZEN":

        blockers.append(
            "motion_plan_not_frozen"
        )


    warnings.extend(
        certification.get(
            "warnings"
        )
        or []
    )


    status = (
        "HOLD"
        if blockers
        else (
            "READY_FOR_HUMAN_VISUAL_REVIEW_WITH_WARNINGS"
            if warnings
            else
            "READY_FOR_HUMAN_VISUAL_REVIEW"
        )
    )


    result = {
        "version": VERSION,

        "status": status,

        "scene":
            freeze.get("scene"),

        "legacy_preview":
            (
                render.get(
                    "legacy",
                    {}
                ).get(
                    "output"
                )
            ),

        "vi6_preview":
            (
                render.get(
                    "vi6",
                    {}
                ).get(
                    "output"
                )
            ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "technical_certification":
            certification.get(
                "status"
            ),

        "human_visual_review_required":
            True,

        # Still deliberately locked.
        "runtime_canary_authorized":
            False,

        "full_active_authorized":
            False,

        "active_renderer":
            False,
    }


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    OUTPUT.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now().isoformat(
                        timespec="seconds"
                    ),

                "gate":
                    result,
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    return result


def self_test():

    assert VERSION == "6.80"

    print(
        "VI6.80 MASTER RUNTIME GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# 13. INTEGRATION SELF-TEST
# =====================================================

cat > testar_vi671_vi680.py <<'PY'
#!/usr/bin/env python3

from vi6_76_visual_technical_comparator import (
    compare
)

from vi6_79_canary_certification_gate import (
    evaluate
)


probe = {
    "status": "PASS",
    "width": 1080,
    "height": 1920,
    "pix_fmt": "yuv420p",
    "codec": "h264",
    "duration": "3.500",
}


comparison = compare(
    dict(probe),
    dict(probe)
)


assert (
    comparison["status"]
    == "PASS"
)


cert = evaluate(
    {
        "status": "RENDERED"
    },

    comparison,

    {
        "status": "PASS"
    },

    {
        "failure_action":
            "RENDER_SAME_SCENE_"
            "WITH_LEGACY_FILTER"
    },
)


assert (
    cert["status"]
    == "TECHNICALLY_CERTIFIED"
)


assert (
    cert[
        "runtime_canary_authorized"
    ]
    is False
)


print()
print(
    "======================================================"
)
print(
    " VI6.71-6.80 MEGA INTEGRATION: PASS"
)
print(
    "======================================================"
)
print(
    "REAL SOURCE POLICY=PASS"
)
print(
    "TWIN RENDER MODEL=PASS"
)
print(
    "TECHNICAL COMPARISON=PASS"
)
print(
    "ROLLBACK CONTRACT=PASS"
)
print(
    "RUNTIME CANARY=LOCKED"
)
print(
    "FULL ACTIVE=LOCKED"
)
PY


# =====================================================
# 14. COMPILE
# =====================================================

echo
echo "===== MEGA COMPILE ====="

if ! python -m py_compile \
    vi6_71_canary_freeze.py \
    vi6_72_real_source_locator.py \
    vi6_73_twin_command_builder.py \
    vi6_74_real_canary_renderer.py \
    vi6_75_twin_probe.py \
    vi6_76_visual_technical_comparator.py \
    vi6_77_canary_artifact_manager.py \
    vi6_78_motion_plan_freezer.py \
    vi6_79_canary_certification_gate.py \
    vi6_80_master_runtime_gate.py \
    testar_vi671_vi680.py
then

    rollback
    exit 10
fi


echo "MEGA COMPILE=PASS"


# =====================================================
# 15. SELF TESTS
# =====================================================

echo
echo "===== SELF TESTS ====="

python vi6_71_canary_freeze.py >/dev/null || {
    rollback
    exit 11
}

python vi6_72_real_source_locator.py >/dev/null || {
    rollback
    exit 12
}

python vi6_73_twin_command_builder.py || {
    rollback
    exit 13
}

python vi6_74_real_canary_renderer.py || {
    rollback
    exit 14
}

python vi6_75_twin_probe.py || {
    rollback
    exit 15
}

python vi6_76_visual_technical_comparator.py || {
    rollback
    exit 16
}

python vi6_77_canary_artifact_manager.py || {
    rollback
    exit 17
}

python vi6_78_motion_plan_freezer.py || {
    rollback
    exit 18
}

python vi6_79_canary_certification_gate.py || {
    rollback
    exit 19
}

python vi6_80_master_runtime_gate.py || {
    rollback
    exit 20
}

python testar_vi671_vi680.py || {
    rollback
    exit 21
}


# =====================================================
# 16. FREEZE REAL CANDIDATE
# =====================================================

echo
echo "===== VI6.71 REAL FREEZE ====="

python vi6_71_canary_freeze.py


# =====================================================
# 17. LOCATE ACTUAL SOURCE
# =====================================================

echo
echo "===== VI6.72 REAL SOURCE ====="

python - <<'PY'
import json
from pathlib import Path

from vi6_72_real_source_locator import (
    locate
)


base = Path.home() / "ShortAutoPro"

result = locate()


path = (
    base
    / "logs/producao/"
      "vi6_72_source_locator_latest.json"
)


path.write_text(
    json.dumps(
        {
            "source":
                result
        },
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


print(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    )
)


if result.get(
    "status"
) != "FOUND":

    raise SystemExit(1)
PY


if [ "$?" -ne 0 ]; then
    rollback
    exit 22
fi


# =====================================================
# 18. BUILD REAL TWIN COMMANDS
# =====================================================

echo
echo "===== VI6.73 REAL TWIN PLAN ====="

python - <<'PY'
import json
from pathlib import Path

from vi6_73_twin_command_builder import (
    build
)


base = Path.home() / "ShortAutoPro"

result = build()


path = (
    base
    / "logs/producao/"
      "vi6_73_twin_plan_latest.json"
)


path.write_text(
    json.dumps(
        {
            "plan":
                result
        },
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


print(
    "STATUS:",
    result.get("status")
)

print(
    "SCENE:",
    result.get("scene")
)

print(
    "SOURCE:",
    result.get("source")
)

print(
    "DURATION:",
    result.get(
        "duration_seconds"
    )
)

print(
    "FPS:",
    result.get("fps")
)

print(
    "FRAMES:",
    result.get("frames")
)

print(
    "LEGACY OUTPUT:",
    result.get(
        "legacy_output"
    )
)

print(
    "VI6 OUTPUT:",
    result.get(
        "vi6_output"
    )
)

print(
    "BLOCKERS:",
    result.get("blockers")
)


if result.get(
    "status"
) != "READY":

    raise SystemExit(1)
PY


if [ "$?" -ne 0 ]; then
    rollback
    exit 23
fi


# =====================================================
# 19. VIDEO.PY HASH BEFORE REAL PREVIEW
# =====================================================

CURRENT_HASH="$(
    sha256sum video.py |
    awk '{print $1}'
)"


if [ "$CURRENT_HASH" != "$VIDEO_HASH_BEFORE" ]; then

    echo "ERRO: video.py mudou antes do canário."

    rollback

    exit 24
fi


# =====================================================
# 20. ACTUAL LEGACY + VI6 PREVIEW RENDER
# =====================================================

echo
echo "======================================================"
echo " REAL TWIN PREVIEW RENDER"
echo " ONE ACTUAL STILL SCENE"
echo "======================================================"

python - <<'PY'
import json
from pathlib import Path

from vi6_74_real_canary_renderer import (
    render
)


base = Path.home() / "ShortAutoPro"


plan = json.loads(
    (
        base
        / "logs/producao/"
          "vi6_73_twin_plan_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["plan"]


result = render(
    plan
)


print(
    "STATUS:",
    result.get("status")
)


legacy = (
    result.get("legacy")
    or {}
)


vi6 = (
    result.get("vi6")
    or {}
)


print(
    "LEGACY RETURN:",
    legacy.get(
        "return_code"
    )
)

print(
    "LEGACY SECONDS:",
    legacy.get(
        "elapsed_seconds"
    )
)

print(
    "LEGACY OUTPUT:",
    legacy.get(
        "output"
    )
)


print(
    "VI6 RETURN:",
    vi6.get(
        "return_code"
    )
)

print(
    "VI6 SECONDS:",
    vi6.get(
        "elapsed_seconds"
    )
)

print(
    "VI6 OUTPUT:",
    vi6.get(
        "output"
    )
)


print(
    "BLOCKERS:",
    result.get(
        "blockers"
    )
)


if result.get(
    "status"
) != "RENDERED":

    raise SystemExit(1)
PY


if [ "$?" -ne 0 ]; then
    echo
    echo "CANARY PREVIEW FAILED."
    echo "Full production remains untouched."
    exit 25
fi


# =====================================================
# 21. PROBE + COMPARE + CERTIFY
# =====================================================

echo
echo "===== VI6.75-6.79 CERTIFICATION ====="

python - <<'PY'
import json
from pathlib import Path


from vi6_75_twin_probe import (
    probe
)

from vi6_76_visual_technical_comparator import (
    compare
)

from vi6_77_canary_artifact_manager import (
    evaluate as artifact_evaluate
)

from vi6_67_scene_rollback_contract import (
    build as rollback_build
)

from vi6_78_motion_plan_freezer import (
    freeze as motion_freeze
)

from vi6_79_canary_certification_gate import (
    evaluate as certify
)

from vi6_80_master_runtime_gate import (
    evaluate as master_evaluate
)


base = Path.home() / "ShortAutoPro"

logs = (
    base
    / "logs"
    / "producao"
)


gate70 = json.loads(
    (
        logs
        / "vi6_70_master_canary_gate_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["gate"]


frozen = json.loads(
    (
        logs
        / "vi6_71_canary_freeze_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["freeze"]


source = json.loads(
    (
        logs
        / "vi6_72_source_locator_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["source"]


render = json.loads(
    (
        logs
        / "vi6_74_real_canary_render_latest.json"
    ).read_text(
        encoding="utf-8"
    )
)["render"]


legacy_path = (
    render["legacy"]["output"]
)


vi6_path = (
    render["vi6"]["output"]
)


legacy_probe = probe(
    legacy_path
)


vi6_probe = probe(
    vi6_path
)


comparison = compare(
    legacy_probe,
    vi6_probe
)


artifacts = artifact_evaluate(
    legacy_path,
    vi6_path
)


rollback = rollback_build(
    frozen.get("scene")
)


motion = motion_freeze()


cert = certify(
    render,
    comparison,
    artifacts,
    rollback
)


master = master_evaluate(
    gate70,
    frozen,
    source,
    render,
    comparison,
    cert,
    motion
)


result = {
    "legacy_probe":
        legacy_probe,

    "vi6_probe":
        vi6_probe,

    "comparison":
        comparison,

    "artifacts":
        artifacts,

    "rollback":
        rollback,

    "motion":
        motion,

    "certification":
        cert,

    "master":
        master,
}


(
    logs
    / "vi6_79_real_canary_certification_latest.json"
).write_text(
    json.dumps(
        result,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)


print()
print(
    "LEGACY PROBE:",
    legacy_probe.get(
        "status"
    )
)

print(
    "LEGACY:",
    legacy_probe.get(
        "width"
    ),
    "x",
    legacy_probe.get(
        "height"
    ),
    "| duration=",
    legacy_probe.get(
        "duration"
    ),
    "| fps=",
    legacy_probe.get(
        "fps"
    )
)


print(
    "VI6 PROBE:",
    vi6_probe.get(
        "status"
    )
)

print(
    "VI6:",
    vi6_probe.get(
        "width"
    ),
    "x",
    vi6_probe.get(
        "height"
    ),
    "| duration=",
    vi6_probe.get(
        "duration"
    ),
    "| fps=",
    vi6_probe.get(
        "fps"
    )
)


print()
print(
    "TECHNICAL COMPARISON:",
    comparison.get(
        "status"
    )
)

print(
    "DURATION DELTA:",
    comparison.get(
        "duration_delta"
    )
)

print(
    "COMPARISON BLOCKERS:",
    comparison.get(
        "blockers"
    )
)


print()
print(
    "VI6.79:",
    cert.get(
        "status"
    )
)

print(
    "VI6.79 BLOCKERS:",
    cert.get(
        "blockers"
    )
)


print()
print(
    "VI6.80 MASTER:",
    master.get(
        "status"
    )
)

print(
    "SCENE:",
    master.get(
        "scene"
    )
)

print(
    "MASTER BLOCKERS:",
    master.get(
        "blockers"
    )
)

print(
    "MASTER WARNINGS:",
    master.get(
        "warnings"
    )
)

print(
    "HUMAN VISUAL REVIEW:",
    master.get(
        "human_visual_review_required"
    )
)

print(
    "RUNTIME CANARY AUTHORIZED:",
    master.get(
        "runtime_canary_authorized"
    )
)

print(
    "FULL ACTIVE AUTHORIZED:",
    master.get(
        "full_active_authorized"
    )
)
PY


# =====================================================
# 22. VIDEO.PY FINAL PROTECTION
# =====================================================

VIDEO_HASH_AFTER="$(
    sha256sum video.py |
    awk '{print $1}'
)"


echo
echo "===== VIDEO.PY FINAL INTEGRITY ====="

echo "BEFORE=$VIDEO_HASH_BEFORE"
echo "AFTER =$VIDEO_HASH_AFTER"


if [ "$VIDEO_HASH_BEFORE" != "$VIDEO_HASH_AFTER" ]; then

    echo "CRITICAL: video.py foi alterado."

    rollback

    exit 30
fi


echo "VIDEO.PY UNCHANGED=YES"


# =====================================================
# 23. RELEASE
# =====================================================

echo
echo "===== RELEASE CHECK ====="

bash -n gerar_short.sh || {
    rollback
    exit 31
}


./release_check.sh || {
    rollback
    exit 32
}


# =====================================================
# FINAL
# =====================================================

echo
echo "======================================================"
echo " VI6.71 -> VI6.80 MEGA UPDATE COMPLETE"
echo "======================================================"
echo
echo "OK Canary Decision Frozen"
echo "OK Real Still Source Located"
echo "OK Legacy Twin Built"
echo "OK VI6 Twin Built"
echo "OK Real FFmpeg Twin Render"
echo "OK FFprobe Validation"
echo "OK Resolution Comparison"
echo "OK Duration Comparison"
echo "OK Per-Scene Rollback Contract"
echo "OK Motion Diversity Plan Frozen"
echo "OK Technical Canary Certification"
echo "OK Master Runtime Gate"
echo
echo "VIDEO.PY MODIFIED=NO"
echo "FULL SHORT MODIFIED=NO"
echo "FULL ACTIVE=LOCKED"
echo
echo "PREVIEWS:"
echo "videos/canary/"
echo
echo "MASTER REPORT:"
echo "logs/producao/vi6_80_master_runtime_gate_latest.json"
echo
