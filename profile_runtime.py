#!/usr/bin/env python3
"""Resolve ShortAutoPro channel profiles into a safe runtime environment.

This module deliberately emits only an allow-listed set of environment
variables. Values are shell-quoted when --shell is requested, so a tracked
JSON profile cannot accidentally break the wrapper command line.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
PROFILES = BASE / "config" / "channel_profiles.json"


def read_profiles() -> dict[str, Any]:
    try:
        data = json.loads(PROFILES.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"ERRO: perfis não encontrados: {PROFILES}")
    except Exception as exc:
        raise SystemExit(f"ERRO: perfis inválidos: {exc}")
    if not isinstance(data, dict) or "default" not in data:
        raise SystemExit("ERRO: channel_profiles.json precisa conter o perfil default.")
    return data


def merge_dict(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def load_profile(name: str) -> dict[str, Any]:
    profiles = read_profiles()
    if name not in profiles:
        options = ", ".join(sorted(profiles))
        raise SystemExit(f"ERRO: perfil '{name}' não existe. Disponíveis: {options}")
    default = profiles.get("default")
    selected = profiles.get(name)
    if not isinstance(default, dict) or not isinstance(selected, dict):
        raise SystemExit("ERRO: perfil precisa ser um objeto JSON.")
    return merge_dict(default, selected)


def as_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def as_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def runtime_env(name: str) -> dict[str, str]:
    profile = load_profile(name)
    captions = profile.get("captions", {}) if isinstance(profile.get("captions"), dict) else {}
    audio = profile.get("audio", {}) if isinstance(profile.get("audio"), dict) else {}
    visual = profile.get("visual", {}) if isinstance(profile.get("visual"), dict) else {}
    narrative = profile.get("narrative", {}) if isinstance(profile.get("narrative"), dict) else {}

    language = str(profile.get("language", "pt-BR")).strip() or "pt-BR"
    whisper_language = "en" if language.lower().startswith("en") else "pt"

    env = {
        "SAP_CHANNEL_PROFILE": name,
        "SHORT_QTD_CENAS": str(as_int(profile.get("scene_count"), 12, 6, 20)),
        "SHORT_TARGET_DURATION_SECONDS": str(as_int(profile.get("target_duration_seconds"), 55, 25, 180)),
        "PIPER_MODEL": str(profile.get("voice", "pt_BR-faber-medium")).strip() or "pt_BR-faber-medium",
        "SHORT_LANGUAGE": language,
        "SHORT_WHISPER_LANGUAGE": whisper_language,
        "SAP_AUDIO_TARGET_LUFS": str(as_float(audio.get("target_lufs"), -14.0, -24.0, -10.0)),
        "SAP_AUDIO_TRUE_PEAK_DB": str(as_float(audio.get("true_peak_db"), -1.5, -3.0, -0.5)),
        "SAP_VISUAL_MIN_SCORE": str(as_float(visual.get("minimum_score"), 78.0, 50.0, 100.0)),
        "SAP_CAPTION_MAX_WORDS": str(as_int(captions.get("max_words_per_event"), 7, 2, 12)),
        "SAP_CAPTION_MAX_LINES": str(as_int(captions.get("max_lines"), 2, 1, 3)),
        "SAP_NARRATIVE_TONE": str(narrative.get("tone", "documentary")).strip() or "documentary",
        "SAP_HOOK_STYLE": str(narrative.get("hook_style", "high_curiosity")).strip() or "high_curiosity",
        "SAP_CTA_STYLE": str(narrative.get("cta_style", "subtle")).strip() or "subtle",
    }
    theme = str(profile.get("theme", "")).strip()
    if theme:
        env["SHORT_TEMA"] = theme
    return env


def main() -> int:
    parser = argparse.ArgumentParser(description="ShortAutoPro profile runtime")
    parser.add_argument("--profile", default=os.getenv("SAP_CHANNEL_PROFILE", "default"))
    parser.add_argument("--shell", action="store_true", help="emit export statements")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    args = parser.parse_args()

    env = runtime_env(args.profile)
    if args.shell:
        for key, value in env.items():
            print(f"export {key}={shlex.quote(value)}")
    else:
        print(json.dumps(env, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
