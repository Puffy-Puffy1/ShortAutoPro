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
