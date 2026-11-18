#!/usr/bin/env python3
"""Validated production profiles for the Termux-first ShortAutoPro Studio.

This module only configures the existing canonical pipeline. It does not create
or execute a second rendering path.
"""
from __future__ import annotations

import os
from typing import Any

SHORT_DURATIONS = (30, 45, 60)
LONG_DURATIONS_MINUTES = (10, 15, 20)
STYLES = {
    "documentary",
    "cinematic",
    "storytelling",
    "animation",
    "anime",
    "cartoon",
    "minimal",
    "educational",
    "horror",
    "mystery",
    "historical",
    "nature",
    "technology",
}


def _clean_text(value: Any, *, limit: int = 120) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) > limit:
        raise ValueError(f"texto excede {limit} caracteres")
    if any(ord(ch) < 32 for ch in text):
        raise ValueError("texto contém caracteres de controle")
    return text


def build_studio_config(
    video_format: str = "short",
    duration: int | None = None,
    *,
    theme: str = "",
    exact_topic: str = "",
    style: str = "documentary",
    cloud_ai: bool = False,
) -> dict[str, Any]:
    """Return a bounded, reproducible production configuration.

    Duration is seconds for Shorts and minutes for long-form videos.
    """
    kind = str(video_format or "short").strip().lower()
    if kind not in {"short", "long"}:
        raise ValueError("formato deve ser 'short' ou 'long'")

    selected_style = str(style or "documentary").strip().lower()
    if selected_style not in STYLES:
        raise ValueError("estilo não suportado")

    clean_theme = _clean_text(theme, limit=100)
    clean_exact_topic = _clean_text(exact_topic, limit=180)
    if clean_theme and clean_exact_topic:
        raise ValueError("escolha tema amplo ou assunto exato, não os dois")

    if kind == "short":
        seconds = 45 if duration is None else int(duration)
        if seconds not in SHORT_DURATIONS:
            raise ValueError("Shorts aceitam 30, 45 ou 60 segundos")
        scenes = {30: 8, 45: 12, 60: 16}[seconds]
        width, height, fps = 1080, 1920, 30
        min_words, max_words = 105, 125
        encoder_preset, crf = "veryfast", 20
        source_limit = 16000
        target_minutes = None
    else:
        minutes = 10 if duration is None else int(duration)
        if minutes not in LONG_DURATIONS_MINUTES:
            raise ValueError("vídeos longos aceitam 10, 15 ou 20 minutos")
        seconds = minutes * 60
        scenes = minutes * 3
        width, height, fps = 1280, 720, 24
        target_words = minutes * 140
        min_words = int(target_words * 0.92)
        max_words = int(target_words * 1.08)
        encoder_preset, crf = "ultrafast", 25
        source_limit = 60000
        target_minutes = minutes

    max_output_tokens = min(8192, max(1800, int(max_words * 1.75)))

    return {
        "format": kind,
        "duration_seconds": seconds,
        "duration_minutes": target_minutes,
        "orientation": "portrait" if height > width else "landscape",
        "width": width,
        "height": height,
        "fps": fps,
        "scene_count": scenes,
        "script_min_words": min_words,
        "script_max_words": max_words,
        "script_max_output_tokens": max_output_tokens,
        "source_max_chars": source_limit,
        "theme": clean_theme,
        "exact_topic": clean_exact_topic,
        "style": selected_style,
        "free_mode": not bool(cloud_ai),
        "render_preset": encoder_preset,
        "render_crf": crf,
    }



def script_length_valid(word_count: int, min_words: int, max_words: int) -> bool:
    """Validate script length against the active profile's inclusive range."""
    try:
        count = int(word_count)
        minimum = max(0, int(min_words))
        maximum = max(minimum, int(max_words))
    except (TypeError, ValueError):
        return False
    return minimum <= count <= maximum

def apply_studio_config(config: dict[str, Any]) -> None:
    """Apply a validated profile after config.sh has been loaded."""
    required = {
        "format", "duration_seconds", "width", "height", "fps",
        "scene_count", "script_min_words", "script_max_words",
        "script_max_output_tokens", "source_max_chars", "style",
        "render_preset", "render_crf",
    }
    missing = required.difference(config)
    if missing:
        raise ValueError("configuração incompleta: " + ",".join(sorted(missing)))

    values = {
        "SAP_STUDIO_FORMAT": str(config["format"]),
        "SAP_STUDIO_DURATION_SECONDS": str(int(config["duration_seconds"])),
        "SAP_STUDIO_WIDTH": str(int(config["width"])),
        "SAP_STUDIO_HEIGHT": str(int(config["height"])),
        "SAP_STUDIO_FPS": str(int(config["fps"])),
        "SAP_STUDIO_SCENE_COUNT": str(int(config["scene_count"])),
        "SAP_STUDIO_SCRIPT_MIN_WORDS": str(int(config["script_min_words"])),
        "SAP_STUDIO_SCRIPT_MAX_WORDS": str(int(config["script_max_words"])),
        "SAP_STUDIO_SCRIPT_MAX_OUTPUT_TOKENS": str(int(config["script_max_output_tokens"])),
        "SAP_STUDIO_SOURCE_MAX_CHARS": str(int(config["source_max_chars"])),
        "SAP_STUDIO_STYLE": str(config["style"]),
        "SAP_RENDER_V2_PRESET": str(config["render_preset"]),
        "SAP_RENDER_V2_CRF": str(int(config["render_crf"])),
        "SHORT_TARGET_DURATION_SECONDS": str(int(config["duration_seconds"])),
        "SHORT_QTD_CENAS": str(int(config["scene_count"])),
        "SAP_MIN_FREE_GB": "2.5" if config["format"] == "long" else "1.2",
        "SAP_STAGE_TIMEOUT_DEFAULT_SECONDS": "1800" if config["format"] == "long" else "600",
    }
    for key, value in values.items():
        os.environ[key] = value

    free_mode = bool(config.get("free_mode", True))
    os.environ["SAP_FREE_MODE"] = "1" if free_mode else "0"
    if free_mode:
        os.environ.pop("GEMINI_API_KEY", None)

    theme = _clean_text(config.get("theme", ""), limit=100)
    exact_topic = _clean_text(config.get("exact_topic", ""), limit=180)
    if theme:
        os.environ["SHORT_TEMA"] = theme
    if exact_topic:
        os.environ["SHORT_TOPIC_EXACT"] = exact_topic
    else:
        os.environ.pop("SHORT_TOPIC_EXACT", None)


__all__ = [
    "SHORT_DURATIONS",
    "LONG_DURATIONS_MINUTES",
    "STYLES",
    "build_studio_config",
    "script_length_valid",
    "apply_studio_config",
]
