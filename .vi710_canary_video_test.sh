#!/data/data/com.termux/files/usr/bin/bash
set -u
set -o pipefail

cd "$HOME/ShortAutoPro" || exit 1

SHORT_ID="2026-09-01_1433"
BASE="$HOME/ShortAutoPro"
CANARY_DIR="$BASE/temp/vi710_canary"
MANIFEST="$BASE/temp/vi700_canary/portfolio_manifest.json"
HOOK_PY="$BASE/vi710_canary_hook.py"
SITE_PY="$BASE/sitecustomize.py"
SITE_BAK="$CANARY_DIR/sitecustomize.backup.py"
SITE_FLAG="$CANARY_DIR/sitecustomize.existed.flag"
HOOK_LOG="$CANARY_DIR/canary_trace.jsonl"
RUN_LOG="$CANARY_DIR/canary_render.log"
SUMMARY_JSON="$CANARY_DIR/canary_summary.json"
MARKER="$CANARY_DIR/render_start.marker"
VIDEOS_DIR="$BASE/videos"
EXPECTED_VIDEO="$VIDEOS_DIR/short_v6_${SHORT_ID}.mp4"
CANARY_COPY="$CANARY_DIR/short_v6_${SHORT_ID}_canary.mp4"
PROD_BAK="$CANARY_DIR/original_short_v6_${SHORT_ID}.bak.mp4"
MOTION_PLAN="roteiros/motion_plan_${SHORT_ID}.json"

echo
echo "=============================================="
echo " VI710 CANARY VIDEO TEST"
echo "=============================================="
echo "SHORT_ID=$SHORT_ID"

mkdir -p "$CANARY_DIR"

if [ ! -f "$MANIFEST" ]; then
    echo "ERRO: manifesto canary não encontrado:"
    echo "$MANIFEST"
    exit 2
fi

if [ ! -f "$MOTION_PLAN" ]; then
    echo "ERRO: motion_plan não encontrado:"
    echo "$MOTION_PLAN"
    exit 3
fi

VIDEO0="$(sha256sum video.py | awk '{print $1}')"
GERAR0="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO0="$(sha256sum roteiro.py | awk '{print $1}')"
EXEC0="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
MOTION0="$(sha256sum "$MOTION_PLAN" | awk '{print $1}')"
MEDIA0="$(
find imagens -type f -printf '%p|%s|%T@\n' 2>/dev/null |
sort | sha256sum | awk '{print $1}'
)"

cat > "$HOOK_PY" <<'PY'
#!/usr/bin/env python3
import inspect
import importlib
import json
import os
import re
from pathlib import Path

SCENE_RE = re.compile(r"scene[_-]?0*(\d+)\.", re.I)

DEFAULT_LOG = (
    Path.home()
    / "ShortAutoPro"
    / "temp"
    / "vi710_canary"
    / "canary_trace.jsonl"
)

SCENE_NAMES = {
    "scene", "scene_num", "scene_number", "numero_cena",
    "numero_da_cena", "cena", "n_cena", "num_cena",
    "indice_cena", "index_cena"
}

MEDIA_NAMES = {
    "media", "media_path", "path", "arquivo", "file",
    "image", "image_path", "imagem", "imagem_path",
    "source_path", "input_path", "img_path", "asset_path",
    "media_file", "input_file"
}

def _log(payload):
    path = Path(
        os.getenv(
            "VI710_CANARY_LOG",
            str(DEFAULT_LOG)
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
            ) + "\n"
        )

def _looks_like_media(value):
    if not isinstance(value, (str, Path)):
        return False
    s = str(value)
    name = Path(s).name
    if SCENE_RE.search(name):
        return True
    low = name.lower()
    return low.endswith(
        (
            ".jpg", ".jpeg", ".png", ".webp",
            ".mp4", ".webm", ".mov", ".mkv"
        )
    )

def _extract_from_name_map(mapping):
    scene = None
    media_key = None
    media_value = None

    for key, value in mapping.items():
        low = str(key).lower()

        if scene is None and low in SCENE_NAMES:
            try:
                scene = int(value)
            except Exception:
                pass

        if media_key is None and low in MEDIA_NAMES and _looks_like_media(value):
            media_key = key
            media_value = value

    if media_key is None:
        for key, value in mapping.items():
            if _looks_like_media(value):
                media_key = key
                media_value = value
                break

    if scene is None and media_value is not None:
        m = SCENE_RE.search(
            Path(str(media_value)).name
        )
        if m:
            try:
                scene = int(m.group(1))
            except Exception:
                pass

    return scene, media_key, media_value

def _bind_or_fallback(sig, args, kwargs):
    try:
        bound = sig.bind_partial(*args, **kwargs)
        mapping = dict(bound.arguments)
        return bound, mapping
    except Exception:
        mapping = {}
        for i, value in enumerate(args):
            mapping[f"_arg_{i}"] = value
        for key, value in kwargs.items():
            mapping[key] = value
        return None, mapping

def _replace_value(bound, args, kwargs, key, old_value, new_value):
    if bound is not None and key in bound.arguments:
        bound.arguments[key] = new_value
        return tuple(bound.args), dict(bound.kwargs)

    new_args = list(args)
    new_kwargs = dict(kwargs)

    if isinstance(key, str) and key.startswith("_arg_"):
        try:
            idx = int(key.split("_")[-1])
            new_args[idx] = new_value
            return tuple(new_args), new_kwargs
        except Exception:
            pass

    if key in new_kwargs:
        new_kwargs[key] = new_value
        return tuple(new_args), new_kwargs

    for i, value in enumerate(new_args):
        if str(value) == str(old_value):
            new_args[i] = new_value
            return tuple(new_args), new_kwargs

    return tuple(args), dict(kwargs)

def activate():
    base = importlib.import_module(
        "vi6_95_scene_executor"
    )

    if getattr(base, "_vi710_canary_patched", False):
        return {
            "patched": True,
            "reason": "already_patched"
        }

    runtime = importlib.import_module(
        "vi700_runtime_override"
    )

    original_execute = getattr(base, "execute")
    signature = inspect.signature(
        original_execute
    )

    def patched_execute(*args, **kwargs):
        enabled = (
            os.getenv(
                "VI700_CANARY_MODE",
                ""
            ).upper() == "ON"
            and runtime.canary_enabled()
        )

        bound, mapping = _bind_or_fallback(
            signature,
            args,
            kwargs
        )

        scene, media_key, media_value = _extract_from_name_map(
            mapping
        )

        original_media = (
            str(media_value)
            if media_value is not None
            else None
        )

        changed = False
        resolved_media = original_media
        note = None

        if enabled and scene is not None and original_media is not None:
            try:
                candidate = runtime.resolve_scene_media(
                    scene,
                    Path(original_media)
                )
                resolved_media = str(candidate)
                if resolved_media != original_media:
                    changed = True
                    call_args, call_kwargs = _replace_value(
                        bound,
                        args,
                        kwargs,
                        media_key,
                        original_media,
                        resolved_media
                    )
                    result = original_execute(
                        *call_args,
                        **call_kwargs
                    )
                    _log({
                        "scene": scene,
                        "changed": changed,
                        "original": original_media,
                        "resolved": resolved_media,
                        "mode": runtime.describe_scene(scene).get("mode"),
                        "enabled": True,
                    })
                    return result
            except BaseException as exc:
                note = (
                    type(exc).__name__
                    + ": "
                    + str(exc)[:300]
                )

        result = original_execute(
            *args,
            **kwargs
        )

        _log({
            "scene": scene,
            "changed": changed,
            "original": original_media,
            "resolved": resolved_media,
            "mode": (
                runtime.describe_scene(scene).get("mode")
                if scene is not None
                else None
            ),
            "enabled": enabled,
            "note": note,
        })
        return result

    setattr(
        base,
        "_vi710_original_execute",
        original_execute
    )
    setattr(
        base,
        "execute",
        patched_execute
    )
    setattr(
        base,
        "_vi710_canary_patched",
        True
    )

    return {
        "patched": True,
        "signature": str(signature),
        "module": "vi6_95_scene_executor",
    }

def preflight():
    result = activate()
    runtime = importlib.import_module(
        "vi700_runtime_override"
    )
    samples = {}

    base = (
        Path.home()
        / "ShortAutoPro"
        / "imagens"
        / "short_2026-09-01_1433"
    )

    for scene in [2, 3, 8, 9, 10, 11, 12]:
        current = base / f"scene_{scene:02d}.jpg"
        if scene == 7:
            current = base / f"scene_{scene:02d}.mp4"
        resolved = runtime.resolve_scene_media(
            scene,
            current
        )
        samples[scene] = {
            "current": str(current),
            "resolved": str(resolved),
            "active": str(current) != str(resolved),
            "mode": runtime.describe_scene(scene).get("mode"),
        }

    result["samples"] = samples
    return result
PY

if [ -f "$SITE_PY" ]; then
    cp -f "$SITE_PY" "$SITE_BAK"
    echo "1" > "$SITE_FLAG"
else
    echo "0" > "$SITE_FLAG"
fi

cleanup_sitecustomize() {
    if [ -f "$SITE_FLAG" ] && [ "$(cat "$SITE_FLAG")" = "1" ] && [ -f "$SITE_BAK" ]; then
        cp -f "$SITE_BAK" "$SITE_PY"
    else
        rm -f "$SITE_PY"
    fi
}
trap cleanup_sitecustomize EXIT

cat > "$SITE_PY" <<'PY'
import os
import sys

if os.getenv("VI700_CANARY_MODE", "").upper() == "ON":
    try:
        from vi710_canary_hook import activate
        activate()
    except BaseException as exc:
        print(
            "VI710 SITECUSTOMIZE HOOK ERROR:",
            type(exc).__name__,
            str(exc)[:400],
            file=sys.stderr
        )
PY

echo
echo "===== PRE-FLIGHT ====="
python - <<'PY'
import json
import os
from pathlib import Path

os.environ["VI700_CANARY_MODE"] = "ON"
os.environ["VI700_PORTFOLIO_CANARY"] = "ON"
os.environ["VI700_PORTFOLIO_MANIFEST"] = str(
    Path.home()
    / "ShortAutoPro"
    / "temp/vi700_canary/portfolio_manifest.json"
)

import vi710_canary_hook as h

data = h.preflight()
print(
    json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )
)
PY

: > "$HOOK_LOG"
date +%s > "$MARKER"

if [ -f "$EXPECTED_VIDEO" ]; then
    cp -f "$EXPECTED_VIDEO" "$PROD_BAK"
    echo
    echo "BACKUP VIDEO ORIGINAL:"
    echo "$PROD_BAK"
fi

echo
echo "===== CANARY RENDER ====="

export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"
export VI700_CANARY_MODE="ON"
export VI700_PORTFOLIO_CANARY="ON"
export VI700_PORTFOLIO_MANIFEST="$MANIFEST"
export VI710_CANARY_LOG="$HOOK_LOG"
export SHORT_ID="$SHORT_ID"
export SHORTAUTO_SHORT_ID="$SHORT_ID"
export SHORTAUTO_FORCE_SHORT_ID="$SHORT_ID"
export PYTHONUNBUFFERED="1"

python video.py 2>&1 | tee "$RUN_LOG"
RENDER_STATUS=${PIPESTATUS[0]}

echo
echo "RENDER STATUS=$RENDER_STATUS"

python - <<'PY'
import json
import os
import shutil
import subprocess
from pathlib import Path

BASE = Path.home() / "ShortAutoPro"
SHORT_ID = "2026-09-01_1433"
CANARY_DIR = BASE / "temp" / "vi710_canary"
HOOK_LOG = CANARY_DIR / "canary_trace.jsonl"
MARKER = CANARY_DIR / "render_start.marker"
VIDEOS_DIR = BASE / "videos"
EXPECTED_VIDEO = VIDEOS_DIR / f"short_v6_{SHORT_ID}.mp4"
CANARY_COPY = CANARY_DIR / f"short_v6_{SHORT_ID}_canary.mp4"
SUMMARY_JSON = CANARY_DIR / "canary_summary.json"
PROD_BAK = CANARY_DIR / f"original_short_v6_{SHORT_ID}.bak.mp4"

marker_ts = 0
try:
    marker_ts = int(MARKER.read_text().strip())
except Exception:
    pass

changed_scenes = []
all_events = []

if HOOK_LOG.exists():
    for line in HOOK_LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
            all_events.append(item)
            if item.get("changed") and item.get("scene") not in changed_scenes:
                changed_scenes.append(item.get("scene"))
        except Exception:
            pass

video_candidates = []
if VIDEOS_DIR.exists():
    for p in VIDEOS_DIR.glob("*.mp4"):
        try:
            if int(p.stat().st_mtime) >= marker_ts:
                video_candidates.append(p)
        except Exception:
            pass

produced = None
if EXPECTED_VIDEO.exists():
    try:
        if int(EXPECTED_VIDEO.stat().st_mtime) >= marker_ts:
            produced = EXPECTED_VIDEO
    except Exception:
        pass

if produced is None and video_candidates:
    produced = sorted(
        video_candidates,
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )[0]

ffprobe_data = {}
if produced and produced.exists():
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(produced),
        ]
        raw = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        ffprobe_data = json.loads(raw.decode("utf-8", errors="ignore"))
    except Exception as exc:
        ffprobe_data = {
            "error": f"{type(exc).__name__}: {exc}"
        }

duration = None
width = None
height = None
fps = None

try:
    if "format" in ffprobe_data:
        duration = ffprobe_data["format"].get("duration")

    for st in ffprobe_data.get("streams", []):
        if st.get("codec_type") == "video":
            width = st.get("width")
            height = st.get("height")
            fps = st.get("avg_frame_rate") or st.get("r_frame_rate")
            break
except Exception:
    pass

if produced and produced.exists():
    shutil.copy2(produced, CANARY_COPY)

summary = {
    "produced_video": str(produced) if produced else None,
    "copied_canary": str(CANARY_COPY) if CANARY_COPY.exists() else None,
    "changed_scenes": sorted(changed_scenes),
    "expected_active": [3, 8, 9, 10, 11],
    "duration": duration,
    "width": width,
    "height": height,
    "fps": fps,
    "hook_events": len(all_events),
    "ffprobe": ffprobe_data,
}

SUMMARY_JSON.write_text(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)

print()
print("===== CANARY SUMMARY =====")
print(
    json.dumps(
        summary,
        ensure_ascii=False,
        indent=2
    )
)

if PROD_BAK.exists() and EXPECTED_VIDEO.exists():
    try:
        shutil.copy2(PROD_BAK, EXPECTED_VIDEO)
        print()
        print("VIDEO ORIGINAL RESTAURADO:", EXPECTED_VIDEO)
    except Exception as exc:
        print()
        print(
            "ERRO AO RESTAURAR VÍDEO ORIGINAL:",
            type(exc).__name__,
            str(exc)
        )
PY

VIDEO1="$(sha256sum video.py | awk '{print $1}')"
GERAR1="$(sha256sum gerar_short.sh | awk '{print $1}')"
ROTEIRO1="$(sha256sum roteiro.py | awk '{print $1}')"
EXEC1="$(sha256sum vi6_95_scene_executor.py | awk '{print $1}')"
MOTION1="$(sha256sum "$MOTION_PLAN" | awk '{print $1}')"
MEDIA1="$(
find imagens -type f -printf '%p|%s|%T@\n' 2>/dev/null |
sort | sha256sum | awk '{print $1}'
)"

echo
echo "===== VI710 INTEGRITY ====="
echo "VIDEO=$([ "$VIDEO0" = "$VIDEO1" ] && echo PASS || echo FAIL)"
echo "GERAR=$([ "$GERAR0" = "$GERAR1" ] && echo PASS || echo FAIL)"
echo "ROTEIRO=$([ "$ROTEIRO0" = "$ROTEIRO1" ] && echo PASS || echo FAIL)"
echo "EXECUTOR=$([ "$EXEC0" = "$EXEC1" ] && echo PASS || echo FAIL)"
echo "MOTION_PLAN=$([ "$MOTION0" = "$MOTION1" ] && echo PASS || echo FAIL)"
echo "MEDIA=$([ "$MEDIA0" = "$MEDIA1" ] && echo PASS || echo FAIL)"

echo
echo "===== OUTPUTS ====="
echo "RUN LOG: $RUN_LOG"
echo "HOOK LOG: $HOOK_LOG"
echo "SUMMARY: $SUMMARY_JSON"
echo "CANARY COPY: $CANARY_COPY"

if [ "$RENDER_STATUS" -ne 0 ]; then
    echo
    echo "CANARY RENDER: FAIL"
    exit "$RENDER_STATUS"
fi

echo
echo "CANARY RENDER: PASS"
